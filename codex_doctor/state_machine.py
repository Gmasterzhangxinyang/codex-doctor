from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .constants import APPROVAL_WAIT_SECONDS, NETWORK_WAIT_SECONDS
from .schemas import Confidence, Diagnosis, Event, NetworkProbe


class CodexState(str, Enum):
    IDLE = "IDLE"
    SESSION_STARTED = "SESSION_STARTED"
    PROMPT_SUBMITTED = "PROMPT_SUBMITTED"
    CODEX_THINKING_NO_TOOL = "CODEX_THINKING_NO_TOOL"
    NETWORK_SUSPECTED = "NETWORK_SUSPECTED"
    API_OR_MODEL_WAITING = "API_OR_MODEL_WAITING"
    MODEL_STREAMING = "MODEL_STREAMING"
    TOOL_PLANNED = "TOOL_PLANNED"
    APPROVAL_WAITING = "APPROVAL_WAITING"
    TOOL_RUNNING = "TOOL_RUNNING"
    TOOL_FINISHED = "TOOL_FINISHED"
    FILE_EDITING = "FILE_EDITING"
    CONTEXT_COMPACTING = "CONTEXT_COMPACTING"
    SANDBOX_OR_PERMISSION_BLOCKED = "SANDBOX_OR_PERMISSION_BLOCKED"
    DONE = "DONE"
    ERROR = "ERROR"


SANDBOX_PATTERNS = (
    "permission denied",
    "operation not permitted",
    "sandbox denied",
    "network disabled",
    "requires approval",
    "not permitted by sandbox",
)


def _age_seconds(ts: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds()


def _latest(events: list[Event], *types: str) -> Event | None:
    for event in reversed(events):
        if event.event_type in types:
            return event
    return None


def _post_for_tool(events: list[Event], pre_tool: Event) -> Event | None:
    for event in events:
        if event.ts <= pre_tool.ts:
            continue
        if event.event_type == "PostToolUse":
            return event
    return None


def diagnose(
    events: list[Event],
    probe: NetworkProbe | None = None,
    process_sample: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> Diagnosis:
    if not events:
        return Diagnosis(
            state=CodexState.IDLE.value,
            confidence=Confidence.LOW,
            title="No Codex activity recorded yet.",
            explanation="Codex Doctor has not seen hook, wrapper, or process events for this session.",
        )

    session_id = events[-1].session_id
    last = events[-1]

    sandbox_event = _sandbox_event(events)
    if sandbox_event:
        return Diagnosis(
            session_id=session_id,
            state=CodexState.SANDBOX_OR_PERMISSION_BLOCKED.value,
            confidence=Confidence.HIGH,
            title="Codex appears blocked by sandbox or permission policy.",
            explanation="A tool result contains a sandbox or permission error.",
            evidence={"event_id": sandbox_event.id, "snippet": sandbox_event.tool_input_snippet},
        )

    pre_compact = _latest(events, "PreCompact")
    post_compact = _latest(events, "PostCompact")
    if pre_compact and (not post_compact or post_compact.ts < pre_compact.ts):
        return Diagnosis(
            session_id=session_id,
            state=CodexState.CONTEXT_COMPACTING.value,
            confidence=Confidence.HIGH,
            title="Codex is compacting context.",
            explanation="A PreCompact hook was recorded and no later PostCompact hook has arrived.",
            evidence={"pre_compact_ts": pre_compact.ts.isoformat()},
        )

    permission = _latest(events, "PermissionRequest")
    if permission and permission.ts >= last.ts and _age_seconds(permission.ts, now) >= APPROVAL_WAIT_SECONDS:
        return Diagnosis(
            session_id=session_id,
            state=CodexState.APPROVAL_WAITING.value,
            confidence=Confidence.HIGH,
            title="Codex is waiting for your approval.",
            explanation="A PermissionRequest hook was recorded with no later progress event.",
            evidence={"tool": permission.tool_name, "elapsed_seconds": _age_seconds(permission.ts, now)},
        )

    pre_tool = _latest(events, "PreToolUse")
    if pre_tool and not _post_for_tool(events, pre_tool):
        evidence: dict[str, Any] = {
            "tool": pre_tool.tool_name,
            "elapsed_seconds": _age_seconds(pre_tool.ts, now),
        }
        if process_sample:
            evidence.update(
                {
                    "cpu_percent": process_sample.get("cpu_percent"),
                    "memory_rss_mb": process_sample.get("memory_rss_mb"),
                    "child_count": process_sample.get("child_count"),
                }
            )
        return Diagnosis(
            session_id=session_id,
            state=CodexState.TOOL_RUNNING.value,
            confidence=Confidence.HIGH,
            title="Codex is waiting for a local tool to finish.",
            explanation="A PreToolUse hook was recorded and no matching PostToolUse hook has arrived.",
            evidence=evidence,
        )

    if last.event_type == "Stop":
        return Diagnosis(
            session_id=session_id,
            state=CodexState.DONE.value,
            confidence=Confidence.HIGH,
            title="Codex session finished.",
            explanation="A Stop hook was recorded.",
            evidence={"stop_ts": last.ts.isoformat()},
        )

    prompt = _latest(events, "UserPromptSubmit")
    if prompt:
        elapsed = _age_seconds(prompt.ts, now)
        if elapsed >= NETWORK_WAIT_SECONDS:
            if probe and not probe.ok:
                return Diagnosis(
                    session_id=session_id,
                    state=CodexState.NETWORK_SUSPECTED.value,
                    confidence=Confidence.MEDIUM,
                    title="Codex may be blocked by network or proxy.",
                    explanation="No tool event appeared after the prompt, and the OpenAI probe failed.",
                    evidence={"elapsed_seconds": elapsed, "probe_error": probe.error_type},
                )
            if probe and probe.ok:
                return Diagnosis(
                    session_id=session_id,
                    state=CodexState.API_OR_MODEL_WAITING.value,
                    confidence=Confidence.MEDIUM,
                    title="Network looks healthy. Codex is likely waiting for API or model response.",
                    explanation="No tool event appeared after the prompt, but api.openai.com was reachable.",
                    evidence={"elapsed_seconds": elapsed, "http_code": probe.http_code},
                )
            return Diagnosis(
                session_id=session_id,
                state=CodexState.CODEX_THINKING_NO_TOOL.value,
                confidence=Confidence.LOW,
                title="Codex is thinking and has not started a tool.",
                explanation="A prompt was submitted, but no tool or probe evidence is available yet.",
                evidence={"elapsed_seconds": elapsed},
            )
        return Diagnosis(
            session_id=session_id,
            state=CodexState.PROMPT_SUBMITTED.value,
            confidence=Confidence.LOW,
            title="Prompt submitted.",
            explanation="Codex Doctor is waiting for more observable activity before classifying the delay.",
            evidence={"elapsed_seconds": elapsed},
        )

    return Diagnosis(
        session_id=session_id,
        state=CodexState.SESSION_STARTED.value,
        confidence=Confidence.LOW,
        title="Codex session started.",
        explanation="Codex Doctor has session activity but no prompt or tool event yet.",
        evidence={"last_event": last.event_type},
    )


def _sandbox_event(events: list[Event]) -> Event | None:
    for event in reversed(events):
        haystack = " ".join(
            str(part or "")
            for part in [
                event.tool_input_snippet,
                event.raw_redacted,
                event.event_type,
            ]
        ).lower()
        if any(pattern in haystack for pattern in SANDBOX_PATTERNS):
            return event
    return None
