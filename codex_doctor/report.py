from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from .schemas import Event, NetworkProbe
from .state_machine import diagnose
from .storage import Storage

if TYPE_CHECKING:
    from .current_status import CurrentStatus


def generate_report(session_id: str | None = None, last: bool = False) -> str:
    storage = Storage()
    session = storage.get_latest_session() if last or not session_id else None
    if session is not None:
        session_id = session["id"]
    if not session_id:
        return "# Codex Session Health\n\nNo session has been recorded yet.\n"

    event_rows = list(reversed(storage.list_recent_events(session_id=session_id, limit=500)))
    events = [_event_from_row(row) for row in event_rows]
    probe_row = storage.latest_probe(session_id)
    probe = _probe_from_row(probe_row) if probe_row else None
    diagnosis = diagnose(events, probe=probe)
    counts = Counter(event.event_type for event in events)
    latest_tool = next((event for event in reversed(events) if event.tool_name), None)

    lines = [
        "# Codex Session Health",
        "",
        "## Summary",
        "",
        f"- Session: {session_id}",
        f"- Main bottleneck: {diagnosis.state}",
        f"- Confidence: {diagnosis.confidence.value}",
        f"- Diagnosis: {diagnosis.title}",
    ]
    if session:
        lines.extend(
            [
                f"- Working directory: {session['cwd'] or 'unknown'}",
                f"- Status: {session['status'] or 'unknown'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            diagnosis.explanation,
            "",
            "## Event Counts",
            "",
            "| Event | Count |",
            "|---|---:|",
        ]
    )
    for name, count in counts.most_common():
        lines.append(f"| {name} | {count} |")

    lines.extend(["", "## Current Tool", ""])
    if latest_tool:
        lines.extend(
            [
                f"- Tool: {latest_tool.tool_name}",
                f"- Input hash: {latest_tool.tool_input_hash or 'n/a'}",
                f"- Input snippet: `{(latest_tool.tool_input_snippet or 'n/a')[:120]}`",
            ]
        )
    else:
        lines.append("No tool event was recorded.")

    lines.extend(["", "## Network", ""])
    if probe:
        lines.extend(
            [
                f"- OpenAI probe: {'healthy' if probe.ok else 'failed'}",
                f"- HTTP: {probe.http_code or 'n/a'}",
                f"- DNS: {_fmt_ms(probe.dns_ms)}",
                f"- Connect: {_fmt_ms(probe.connect_ms)}",
                f"- TLS: {_fmt_ms(probe.tls_ms)}",
                f"- TTFB: {_fmt_ms(probe.ttfb_ms)}",
                f"- Total: {_fmt_ms(probe.total_ms)}",
            ]
        )
    else:
        lines.append("No network probe was recorded for this session.")

    lines.extend(
        [
            "",
            "## Suggestions",
            "",
            "1. If state is TOOL_RUNNING, ask Codex to run narrower commands first.",
            "2. If state is API_OR_MODEL_WAITING, reduce context or reasoning effort for simple edits.",
            "3. If state is APPROVAL_WAITING, check the Codex UI for a permission prompt.",
            "4. If state is NETWORK_SUSPECTED, inspect proxy, DNS, VPN, or firewall settings.",
            "5. Add project-specific fast test commands to AGENTS.md.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, session_id: str | None = None, last: bool = False) -> Path:
    path.write_text(generate_report(session_id=session_id, last=last), encoding="utf-8")
    return path


def generate_current_report(status: CurrentStatus, *, lang: str = "zh") -> str:
    from .messages import describe_status

    message = describe_status(status, lang=lang)
    lines = [
        "# Codex Session Health",
        "",
        "## Summary",
        "",
        f"- Session: {status.session_id}",
        f"- Source: {status.source}",
        f"- State: {status.diagnosis.state}",
        f"- Confidence: {status.diagnosis.confidence.value}",
    ]
    if status.project_path:
        lines.append(f"- Project: {status.project_path}")
    lines.extend(
        [
            "",
            "## Diagnosis",
            "",
            f"- Current: {message.current}",
            f"- Reason: {message.reason}",
            f"- Suggestion: {message.action}",
            "",
            "## Evidence",
            "",
            status.diagnosis.explanation,
        ]
    )
    if status.diagnosis.evidence:
        lines.extend(["", "| Key | Value |", "|---|---|"])
        for key, value in status.diagnosis.evidence.items():
            lines.append(f"| {key} | `{value}` |")

    lines.extend(["", "## Network", ""])
    if status.network_probe:
        probe = status.network_probe
        lines.extend(
            [
                f"- OpenAI probe: {'healthy' if probe.ok else 'failed'}",
                f"- Error: {probe.error_type or 'n/a'}",
                f"- HTTP: {probe.http_code or 'n/a'}",
                f"- DNS: {_fmt_ms(probe.dns_ms)}",
                f"- Connect: {_fmt_ms(probe.connect_ms)}",
                f"- TLS: {_fmt_ms(probe.tls_ms)}",
                f"- TTFB: {_fmt_ms(probe.ttfb_ms)}",
                f"- Total: {_fmt_ms(probe.total_ms)}",
            ]
        )
    else:
        lines.append("Network probe was skipped.")

    if status.app_events:
        lines.extend(["", "## Recent Visible Codex Events", ""])
        for event in status.app_events[-12:]:
            lines.append(f"- {event.ts.isoformat()} `{event.label}`")

    lines.extend(
        [
            "",
            "## Privacy Boundary",
            "",
            "This report uses observable local runtime state only. It does not reveal hidden model reasoning.",
            "",
        ]
    )
    return "\n".join(lines)


def write_current_report(path: Path, status: CurrentStatus, *, lang: str = "zh") -> Path:
    path.write_text(generate_current_report(status, lang=lang), encoding="utf-8")
    return path


def _fmt_ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1000:.2f}s"


def _event_from_row(row) -> Event:
    import json
    from datetime import datetime

    return Event(
        id=row["id"],
        ts=datetime.fromisoformat(row["ts"]),
        source=row["source"],
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        event_type=row["event_type"],
        cwd=row["cwd"],
        model=row["model"],
        permission_mode=row["permission_mode"],
        tool_name=row["tool_name"],
        tool_input_hash=row["tool_input_hash"],
        tool_input_snippet=row["tool_input_snippet"],
        success=None if row["success"] is None else bool(row["success"]),
        duration_ms=row["duration_ms"],
        raw_redacted=json.loads(row["raw_redacted_json"] or "{}"),
    )


def _probe_from_row(row) -> NetworkProbe:
    import json
    from datetime import datetime

    return NetworkProbe(
        id=row["id"],
        session_id=row["session_id"],
        ts=datetime.fromisoformat(row["ts"]),
        target=row["target"],
        ok=bool(row["ok"]),
        http_code=row["http_code"],
        dns_ms=row["dns_ms"],
        connect_ms=row["connect_ms"],
        tls_ms=row["tls_ms"],
        ttfb_ms=row["ttfb_ms"],
        total_ms=row["total_ms"],
        error_type=row["error_type"],
        error_message=row["error_message"],
        proxy_summary=json.loads(row["proxy_summary"] or "{}"),
    )
