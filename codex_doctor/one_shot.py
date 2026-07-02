from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

from rich.panel import Panel
from rich.table import Table

from .current_status import CurrentStatus, diagnose_current
from .messages import describe_status
from .report import generate_current_report, write_current_report


@dataclass(frozen=True)
class OneShotOptions:
    lang: str = "zh"
    include_network: bool = True
    stale_seconds: int = 45
    network_timeout: int = 5


def diagnose_once(options: OneShotOptions) -> CurrentStatus:
    return diagnose_current(
        include_network=options.include_network,
        stale_seconds=options.stale_seconds,
        network_timeout=options.network_timeout,
        probe_when_active=True,
    )


def render_diagnosis(status: CurrentStatus, *, lang: str = "zh") -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    message = describe_status(status, lang=lang)

    if lang == "en":
        table.add_row(f"[bold]Visible state[/bold]: {status.diagnosis.state}")
        table.add_row(f"[bold]Confidence[/bold]: {status.diagnosis.confidence.value}")
    else:
        table.add_row(f"[bold]可见状态[/bold]: {status.diagnosis.state}")
        table.add_row(f"[bold]可信度[/bold]: {status.diagnosis.confidence.value}")
    project = _project_display(status)
    if project:
        label = "Project" if lang == "en" else "项目"
        table.add_row(f"[bold]{label}[/bold]: {project}")
    table.add_row(f"[bold]Session[/bold]: {status.session_id}")
    table.add_row(f"[bold]Source[/bold]: {status.source}")

    table.add_row("")
    if lang == "en":
        table.add_row(f"[bold]What is visible[/bold]: {message.current}")
        table.add_row(f"[bold]Likely explanation[/bold]: {message.reason}")
        table.add_row(f"[bold]Next check[/bold]: {message.action}")
    else:
        table.add_row(f"[bold]可见线索[/bold]: {message.current}")
        table.add_row(f"[bold]可能解释[/bold]: {message.reason}")
        table.add_row(f"[bold]下一步[/bold]: {message.action}")

    if status.network_probe:
        probe = status.network_probe
        network = "OK" if probe.ok else f"FAILED ({probe.error_type})"
        total = f"{probe.total_ms / 1000:.2f}s" if probe.total_ms else "n/a"
        table.add_row("")
        table.add_row(f"[bold]Network[/bold]: {network} HTTP={probe.http_code or 'n/a'} total={total}")

    evidence_rows = _evidence_rows(status, lang=lang)
    if evidence_rows:
        table.add_row("")
        table.add_row("[bold]Evidence[/bold]:" if lang == "en" else "[bold]证据[/bold]:")
        for row in evidence_rows:
            table.add_row(row)

    if status.app_events:
        table.add_row("")
        table.add_row("[bold]Recent visible events[/bold]:" if lang == "en" else "[bold]最近可见事件[/bold]:")
        for event in status.app_events[-8:]:
            table.add_row(f"{event.ts.strftime('%H:%M:%S')} {event.label}")

    if status.storage_error:
        table.add_row("")
        table.add_row(f"[bold red]Storage[/bold red]: {status.storage_error}")

    return Panel(table, title="Codex Session Health")


def render_terminal_report(status: CurrentStatus, *, lang: str = "zh") -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    message = describe_status(status, lang=lang)

    if lang == "en":
        table.add_row(f"[bold]Visible state[/bold]: {status.diagnosis.state}")
        table.add_row(f"[bold]Confidence[/bold]: {status.diagnosis.confidence.value}")
        table.add_row(f"[bold]What is visible[/bold]: {message.current}")
        table.add_row(f"[bold]Likely explanation[/bold]: {message.reason}")
        table.add_row(f"[bold]Next check[/bold]: {message.action}")
    else:
        table.add_row(f"[bold]可见状态[/bold]: {status.diagnosis.state}")
        table.add_row(f"[bold]可信度[/bold]: {status.diagnosis.confidence.value}")
        table.add_row(f"[bold]可见线索[/bold]: {message.current}")
        table.add_row(f"[bold]可能解释[/bold]: {message.reason}")
        table.add_row(f"[bold]下一步[/bold]: {message.action}")

    project = _project_display(status)
    if project:
        table.add_row(f"[bold]项目[/bold]: {project}")

    if status.network_probe:
        probe = status.network_probe
        if probe.ok:
            network_text = f"可达，HTTP={probe.http_code or 'n/a'}"
        else:
            network_text = f"失败，类型={probe.error_type or 'unknown'}"
        if probe.total_ms:
            network_text += f"，耗时={probe.total_ms / 1000:.2f}s"
        table.add_row(f"[bold]网络[/bold]: {network_text}")

    if status.app_events:
        latest = status.app_events[-1]
        table.add_row(
            f"[bold]最近事件[/bold]: {latest.ts.strftime('%H:%M:%S')} "
            f"{latest.label} ({_event_age(latest.ts)})"
        )

    evidence_rows = _evidence_rows(status, lang=lang)
    if evidence_rows:
        table.add_row("")
        table.add_row("[bold]证据[/bold]:")
        for row in evidence_rows:
            table.add_row(row)

    return Panel(table, title="Codex Session Health")


def build_report(status: CurrentStatus, *, lang: str = "zh") -> str:
    return generate_current_report(status, lang=lang)


def write_report(path: Path, status: CurrentStatus, *, lang: str = "zh") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_current_report(path, status, lang=lang)


def _project_name(status: CurrentStatus) -> str | None:
    if not status.project_path:
        return None
    return status.project_path.name or str(status.project_path)


def _project_display(status: CurrentStatus) -> str | None:
    if not status.project_path:
        return None
    name = _project_name(status)
    path = str(status.project_path)
    return f"{name} ({path})" if name and name != path else path


def _evidence_rows(status: CurrentStatus, *, lang: str) -> list[str]:
    evidence = status.diagnosis.evidence
    rows: list[str] = []
    age = evidence.get("age_seconds") or evidence.get("elapsed_seconds")
    if isinstance(age, int | float):
        label = "Age" if lang == "en" else "距最近线索"
        rows.append(f"- {label}: {age:.0f}s")
    tool = evidence.get("tool")
    if isinstance(tool, str):
        label = "Tool" if lang == "en" else "工具"
        rows.append(f"- {label}: {tool}")
    open_calls = evidence.get("open_tool_calls")
    if isinstance(open_calls, int):
        label = "Open tool calls" if lang == "en" else "未见完成输出的工具调用"
        rows.append(f"- {label}: {open_calls}")
    last_event = evidence.get("last_event")
    if isinstance(last_event, str):
        label = "Last event" if lang == "en" else "最后事件"
        rows.append(f"- {label}: {last_event}")
    probe_error = evidence.get("probe_error")
    if isinstance(probe_error, str):
        label = "Network error" if lang == "en" else "网络错误"
        rows.append(f"- {label}: {probe_error}")
    return rows


def _event_age(ts) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    seconds = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())
    return f"{seconds:.0f}s ago"
