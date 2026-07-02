from __future__ import annotations

from dataclasses import dataclass

from .current_status import CurrentStatus


@dataclass(frozen=True)
class StatusMessage:
    current: str
    reason: str
    action: str


def describe_status_zh(
    status: CurrentStatus,
    *,
    duration_seconds: float | None = None,
) -> StatusMessage:
    state = status.diagnosis.state
    age = _duration_text(duration_seconds)

    if state == "NETWORK_SUSPECTED":
        error = status.diagnosis.evidence.get("probe_error") or "网络探针失败"
        return StatusMessage(
            current=f"最近 {age}没有看到新的可见进展。",
            reason=f"OpenAI 网络探针失败：{error}，可能是网络、代理、VPN、防火墙或 DNS 问题。",
            action="先检查网络/VPN/代理；网络恢复后再继续当前任务。",
        )

    if state == "API_OR_MODEL_WAITING":
        return StatusMessage(
            current=f"最近 {age}没有新的可见进展。",
            reason="本机到 OpenAI 网络可达；可见证据更像是 API/模型等待或 Codex App 重连。",
            action="通常可以继续等；如果持续很久，重发请求或新开会话。",
        )

    if state == "TOOL_RUNNING":
        tool = status.diagnosis.evidence.get("tool")
        count = status.diagnosis.evidence.get("open_tool_calls")
        tool_text = f"工具 {tool}" if tool else "本地工具或命令"
        count_text = f"，还有 {count} 个工具调用" if isinstance(count, int) and count > 1 else ""
        return StatusMessage(
            current=f"可见事件显示 Codex {age}进入过本地工具阶段。",
            reason=f"检测到{tool_text} 已经启动{count_text}没看到完成输出；这只是本地日志线索。",
            action="检查对应终端/命令是否还在运行；如果已结束，可能是日志事件尚未完整写入。",
        )

    if state == "APPROVAL_WAITING":
        return StatusMessage(
            current=f"可见事件显示 Codex {age}请求过权限确认。",
            reason="检测到权限请求后没有后续进展。",
            action="回到 Codex App，检查是否有需要点击批准的提示。",
        )

    if state == "SANDBOX_OR_PERMISSION_BLOCKED":
        return StatusMessage(
            current="可见工具结果里出现权限或沙盒相关错误。",
            reason="工具结果里出现 permission/sandbox 相关错误。",
            action="检查命令权限、工作目录、沙盒策略，必要时改用允许的路径或授权方式。",
        )

    if state == "CONTEXT_COMPACTING":
        return StatusMessage(
            current=f"可见事件显示 Codex {age}开始过上下文压缩。",
            reason="检测到上下文压缩开始，但还没看到压缩完成。",
            action="一般等它压缩完成；如果太久，可以新开更短上下文的会话。",
        )

    if state in {"MODEL_STREAMING", "CODEX_THINKING_NO_TOOL", "PROMPT_SUBMITTED"}:
        return StatusMessage(
            current=f"最近 {age}只看到模型/消息相关事件。",
            reason="没有看到明确的工具运行、权限请求或沙盒错误；只能判断仍有可见活动或等待。",
            action="继续观察最近事件时间；如果长时间不更新，再看网络探针和是否需要重发请求。",
        )

    if state == "IDLE":
        return StatusMessage(
            current="暂时没有检测到 Codex 活动。",
            reason="没有找到最近的 Codex App 事件或 hook/wrapper 会话。",
            action="开始一个 Codex App 请求后再观察。",
        )

    if state == "DONE":
        return StatusMessage(
            current="Codex 这轮已经结束。",
            reason="检测到会话结束事件。",
            action="不需要处理。",
        )

    return StatusMessage(
        current=f"当前可见状态是 {state}。",
        reason=status.diagnosis.title,
        action="结合最近事件时间、网络探针和终端命令状态判断。",
    )


def describe_status_en(
    status: CurrentStatus,
    *,
    duration_seconds: float | None = None,
) -> StatusMessage:
    state = status.diagnosis.state
    age = _duration_text_en(duration_seconds)

    if state == "NETWORK_SUSPECTED":
        error = status.diagnosis.evidence.get("probe_error") or "network probe failed"
        return StatusMessage(
            current=f"No new visible progress was observed{age}.",
            reason=f"The OpenAI network probe failed: {error}. Network, proxy, VPN, firewall, or DNS may be blocking it.",
            action="Check network/VPN/proxy settings, then retry the Codex request.",
        )

    if state == "API_OR_MODEL_WAITING":
        return StatusMessage(
            current=f"No new visible progress was observed{age}.",
            reason="The OpenAI network probe is reachable; visible evidence points to API/model waiting or reconnect.",
            action="Wait a bit longer; if it keeps hanging, retry the request or start a new session.",
        )

    if state == "TOOL_RUNNING":
        tool = status.diagnosis.evidence.get("tool")
        count = status.diagnosis.evidence.get("open_tool_calls")
        tool_text = f"tool {tool}" if tool else "a local tool or command"
        if isinstance(count, int) and count > 1:
            reason = f"Detected {count} tool calls; {tool_text} is one without completion output yet."
        else:
            reason = f"Detected {tool_text} started, but no completion output has appeared yet."
        return StatusMessage(
            current=f"Visible events show Codex entered local tool execution{age}.",
            reason=reason,
            action="Check whether the terminal/tool is still running; if it finished, the local log may be incomplete.",
        )

    if state == "APPROVAL_WAITING":
        return StatusMessage(
            current=f"Visible events show an approval request{age}.",
            reason="A permission request was detected without later progress.",
            action="Return to Codex App and check whether an approval prompt is waiting.",
        )

    if state == "SANDBOX_OR_PERMISSION_BLOCKED":
        return StatusMessage(
            current="Visible tool output contains sandbox or permission errors.",
            reason="A tool result contains permission or sandbox-related errors.",
            action="Check command permissions, workspace path, sandbox policy, or use an allowed location.",
        )

    if state == "CONTEXT_COMPACTING":
        return StatusMessage(
            current=f"Visible events show context compaction started{age}.",
            reason="Context compaction started, but no completion event has appeared yet.",
            action="Usually wait; if it takes too long, start a shorter-context session.",
        )

    if state in {"MODEL_STREAMING", "CODEX_THINKING_NO_TOOL", "PROMPT_SUBMITTED"}:
        return StatusMessage(
            current=f"Recent visible events are model/message related{age}.",
            reason="No clear tool run, approval request, or sandbox error is visible.",
            action="Watch the latest event age; if it stops updating, check network and consider retrying.",
        )

    if state == "IDLE":
        return StatusMessage(
            current="No current Codex activity was detected.",
            reason="No recent Codex App event or hook/wrapper session was found.",
            action="Start a Codex App request, then run codex-doctor again.",
        )

    if state == "DONE":
        return StatusMessage(
            current="This Codex turn appears finished.",
            reason="A session stop event was detected.",
            action="No action needed.",
        )

    return StatusMessage(
        current=f"Codex state is {state}.",
        reason=status.diagnosis.title,
        action="If this state persists, check network, permissions, or local command execution.",
    )


def describe_status(
    status: CurrentStatus,
    *,
    lang: str = "zh",
    duration_seconds: float | None = None,
) -> StatusMessage:
    if lang == "en":
        return describe_status_en(status, duration_seconds=duration_seconds)
    return describe_status_zh(status, duration_seconds=duration_seconds)


def _duration_text(duration_seconds: float | None) -> str:
    if duration_seconds is None:
        return "一段时间内"
    return f"已经 {duration_seconds:.0f} 秒"


def _duration_text_en(duration_seconds: float | None) -> str:
    if duration_seconds is None:
        return ""
    return f" for {duration_seconds:.0f}s"
