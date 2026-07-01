from __future__ import annotations

from dataclasses import dataclass

from .current_status import CurrentStatus


@dataclass(frozen=True)
class StatusMessage:
    current: str
    reason: str
    action: str

    def notification_text(self) -> str:
        return f"当前：{self.current} 原因：{self.reason} 建议：{self.action}"


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
            current=f"Codex {age}没有继续推进。",
            reason=f"OpenAI 网络探针失败：{error}，可能是网络、代理、VPN、防火墙或 DNS 问题。",
            action="先检查网络/VPN/代理；网络恢复后再继续当前任务。",
        )

    if state == "API_OR_MODEL_WAITING":
        return StatusMessage(
            current=f"Codex {age}没有新的可见进展。",
            reason="本机到 OpenAI 网络可达，更像是在等 API、模型响应或 Codex App 重连。",
            action="通常可以继续等；如果持续很久，重发请求或新开会话。",
        )

    if state == "TOOL_RUNNING":
        tool = status.diagnosis.evidence.get("tool")
        tool_text = f"工具 {tool}" if tool else "本地工具或命令"
        return StatusMessage(
            current=f"Codex {age}卡在本地工具执行阶段。",
            reason=f"检测到{tool_text} 已经启动，但还没看到完成输出。",
            action="看终端/工具是否还在跑；可能是测试、构建、shell 命令或文件操作耗时。",
        )

    if state == "APPROVAL_WAITING":
        return StatusMessage(
            current=f"Codex {age}停在权限确认阶段。",
            reason="检测到权限请求后没有后续进展。",
            action="回到 Codex App，检查是否有需要点击批准的提示。",
        )

    if state == "SANDBOX_OR_PERMISSION_BLOCKED":
        return StatusMessage(
            current="Codex 的本地命令被权限或沙盒拦住。",
            reason="工具结果里出现 permission/sandbox 相关错误。",
            action="检查命令权限、工作目录、沙盒策略，必要时改用允许的路径或授权方式。",
        )

    if state == "CONTEXT_COMPACTING":
        return StatusMessage(
            current=f"Codex {age}在处理长上下文。",
            reason="检测到上下文压缩开始，但还没看到压缩完成。",
            action="一般等它压缩完成；如果太久，可以新开更短上下文的会话。",
        )

    if state in {"MODEL_STREAMING", "CODEX_THINKING_NO_TOOL", "PROMPT_SUBMITTED"}:
        return StatusMessage(
            current=f"Codex {age}仍在模型侧思考或等待输出。",
            reason="暂时没看到工具运行、权限请求或沙盒错误；更像是模型/API 等待或上下文处理慢。",
            action="先等一会；如果持续不动，用 diagnose 看网络是否可达。",
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
        current=f"Codex 当前状态是 {state}。",
        reason=status.diagnosis.title,
        action="如果这个状态持续很久，再看网络、权限或本地命令是否卡住。",
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
            current=f"Codex has made no visible progress{age}.",
            reason=f"The OpenAI network probe failed: {error}. Network, proxy, VPN, firewall, or DNS may be blocking it.",
            action="Check network/VPN/proxy settings, then retry the Codex request.",
        )

    if state == "API_OR_MODEL_WAITING":
        return StatusMessage(
            current=f"Codex has no new visible progress{age}.",
            reason="The OpenAI network probe is reachable, so Codex is more likely waiting on API/model response or reconnect.",
            action="Wait a bit longer; if it keeps hanging, retry the request or start a new session.",
        )

    if state == "TOOL_RUNNING":
        tool = status.diagnosis.evidence.get("tool")
        tool_text = f"tool {tool}" if tool else "a local tool or command"
        return StatusMessage(
            current=f"Codex appears stuck in local tool execution{age}.",
            reason=f"Detected {tool_text} started, but no completion output has appeared yet.",
            action="Check whether the terminal/tool is still running; tests, builds, shell commands, or file operations may be taking time.",
        )

    if state == "APPROVAL_WAITING":
        return StatusMessage(
            current=f"Codex appears paused for approval{age}.",
            reason="A permission request was detected without later progress.",
            action="Return to Codex App and check whether an approval prompt is waiting.",
        )

    if state == "SANDBOX_OR_PERMISSION_BLOCKED":
        return StatusMessage(
            current="Codex local command appears blocked by sandbox or permissions.",
            reason="A tool result contains permission or sandbox-related errors.",
            action="Check command permissions, workspace path, sandbox policy, or use an allowed location.",
        )

    if state == "CONTEXT_COMPACTING":
        return StatusMessage(
            current=f"Codex is processing long-session context{age}.",
            reason="Context compaction started, but no completion event has appeared yet.",
            action="Usually wait; if it takes too long, start a shorter-context session.",
        )

    if state in {"MODEL_STREAMING", "CODEX_THINKING_NO_TOOL", "PROMPT_SUBMITTED"}:
        return StatusMessage(
            current=f"Codex is still thinking or waiting for output{age}.",
            reason="No tool run, approval request, or sandbox error is visible yet; model/API waiting or slow context processing is likely.",
            action="Wait a bit; if it stays stuck, run diagnose to check network reachability.",
        )

    if state == "IDLE":
        return StatusMessage(
            current="No current Codex activity was detected.",
            reason="No recent Codex App event or hook/wrapper session was found.",
            action="Start a Codex App request, then watch again.",
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
        return ""
    return f"已经 {duration_seconds:.0f} 秒"


def _duration_text_en(duration_seconds: float | None) -> str:
    if duration_seconds is None:
        return ""
    return f" for {duration_seconds:.0f}s"
