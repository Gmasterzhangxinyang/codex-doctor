from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from . import __version__
from .codex_locator import find_codex_executable
from .current_status import CurrentStatus, diagnose_current
from .install import hooks_installed, install_hooks, uninstall_hooks
from .messages import describe_status
from .network_probe import run_probe
from .notifications import send_notification
from .report import generate_report, write_report
from .runner import run_codex
from .storage import Storage
from .tui import watch as watch_dashboard

app = typer.Typer(help="Diagnose why Codex is thinking.")
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"codex-doctor {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    _ = version


@app.command()
def install(
    user: Annotated[bool, typer.Option("--user", help="Install user hooks.")] = True,
    project: Annotated[bool, typer.Option("--project", help="Install project hooks.")] = False,
    force: Annotated[bool, typer.Option("--force", help="Do not create a backup.")] = False,
    notification_check: Annotated[
        bool,
        typer.Option(
            "--notification-check/--skip-notification-check",
            help="Verify macOS notifications before completing install.",
        ),
    ] = True,
) -> None:
    if notification_check:
        _check_notifications_or_exit()
    scope = "project" if project else "user"
    path = install_hooks(scope=scope, force=force)
    console.print("[bold green]Codex Doctor installed.[/bold green]")
    console.print(f"Hooks written to: {path}")
    console.print("\nNext:")
    console.print("1. Start stuck feedback: [bold]codex-doctor notify[/bold]")
    console.print("2. Make it faster: [bold]codex-doctor notify --after 20[/bold]")
    _ = user


@app.command()
def uninstall(
    project: Annotated[bool, typer.Option("--project", help="Uninstall project hooks.")] = False,
    purge_data: Annotated[bool, typer.Option("--purge-data", help="Delete stored local data.")] = False,
) -> None:
    scope = "project" if project else "user"
    path = uninstall_hooks(scope=scope, purge_data=purge_data)
    console.print(f"Codex Doctor hooks removed from: {path}")
    if purge_data:
        console.print("Local data purged.")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    hidden=True,
)
def run(ctx: typer.Context) -> None:
    args = list(ctx.args)
    if args and args[0] == "--":
        args = args[1:]
    try:
        code = run_codex(args)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    raise typer.Exit(code)


@app.command(hidden=True)
def watch(
    session: Annotated[str, typer.Option("--session", help="Session id or latest.")] = "latest",
    refresh: Annotated[float, typer.Option("--refresh", help="Refresh seconds.")] = 1.0,
) -> None:
    watch_dashboard(session=session, refresh_seconds=refresh)


@app.command(name="diagnose")
def diagnose_app(
    network: Annotated[
        bool, typer.Option("--network/--no-network", help="Run OpenAI network probe.")
    ] = True,
    stale_seconds: Annotated[
        int, typer.Option("--stale-seconds", help="Seconds without App events before treating as stale.")
    ] = 45,
    lang: Annotated[
        str,
        typer.Option("--lang", help="Output language: zh or en."),
    ] = "zh",
) -> None:
    lang = _normalize_lang(lang)
    status = diagnose_current(
        include_network=network, stale_seconds=stale_seconds, probe_when_active=True
    )
    console.print(render_status(status, lang=lang))


@app.command(name="monitor", hidden=True)
def monitor_app(
    notify_user: Annotated[
        bool, typer.Option("--notify", help="Send macOS notification when Codex looks stuck.")
    ] = False,
    notify_all: Annotated[
        bool,
        typer.Option(
            "--notify-all",
            help="Notify on every status change, including active App activity.",
        ),
    ] = False,
    interval: Annotated[float, typer.Option("--interval", help="Polling interval in seconds.")] = 5.0,
    stuck_after: Annotated[
        float,
        typer.Option(
            "--stuck-after",
            help="Seconds a non-idle state can persist before sending stuck feedback.",
        ),
    ] = 45.0,
    stale_seconds: Annotated[
        int, typer.Option("--stale-seconds", help="Seconds without App events before treating as stale.")
    ] = 45,
    network: Annotated[
        bool,
        typer.Option(
            "--network/--no-network",
            help="Run OpenAI network probe when activity looks stale or uncertain.",
        ),
    ] = True,
) -> None:
    last_notification_key = None
    current_state_key = None
    state_started_at = time.monotonic()
    stuck_notification_key = None
    try:
        while True:
            now = time.monotonic()
            status = diagnose_current(include_network=network, stale_seconds=stale_seconds)
            state_key = (status.session_id, status.diagnosis.state)
            if state_key != current_state_key:
                current_state_key = state_key
                state_started_at = now
                stuck_notification_key = None
            state_age = now - state_started_at
            console.clear()
            console.print(render_status(status))
            key = (status.session_id, status.diagnosis.state, status.diagnosis.title)
            should_notify = notify_user and _should_notify(status, notify_all=notify_all)
            should_notify_stuck = (
                notify_user
                and not notify_all
                and _should_notify_stuck(status)
                and state_age >= stuck_after
                and key != stuck_notification_key
            )
            if should_notify and key != last_notification_key:
                _send_feedback_notification(_notification_message(status))
                last_notification_key = key
            elif should_notify_stuck:
                _send_feedback_notification(
                    _notification_message(status, duration_seconds=state_age)
                )
                stuck_notification_key = key
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("Stopped.")


@app.command(name="notify")
def notify_when_stuck(
    after: Annotated[
        float | None,
        typer.Option("--after", help="Seconds before Codex Doctor reports a stuck active state."),
    ] = None,
    test: Annotated[
        bool,
        typer.Option("--test", help="Send one test notification and exit."),
    ] = False,
    lang: Annotated[
        str | None,
        typer.Option("--lang", help="Notification language: zh or en."),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive/--no-interactive",
            help="Prompt for language and threshold seconds when not provided.",
        ),
    ] = True,
    interval: Annotated[float, typer.Option("--interval", help="Polling interval in seconds.")] = 5.0,
    network: Annotated[
        bool,
        typer.Option(
            "--network/--no-network",
            help="Run OpenAI network probe when activity looks stale or uncertain.",
        ),
    ] = True,
) -> None:
    if test:
        test_lang = _normalize_lang(lang or "zh")
        ok = _send_feedback_notification(_test_message(test_lang))
        if not ok:
            raise typer.Exit(1)
        return
    lang, after = _resolve_notify_settings(lang=lang, after=after, interactive=interactive)
    console.print(_startup_message(lang, after))
    console.print(_stop_message(lang))
    last_notification_key = None
    current_state_key = None
    state_started_at = time.monotonic()
    stuck_notification_key = None
    try:
        while True:
            now = time.monotonic()
            status = diagnose_current(
                include_network=network,
                stale_seconds=max(1, int(after)),
            )
            state_key = (status.session_id, status.diagnosis.state)
            if state_key != current_state_key:
                current_state_key = state_key
                state_started_at = now
                stuck_notification_key = None
            state_age = now - state_started_at
            key = (status.session_id, status.diagnosis.state, status.diagnosis.title)
            if _should_notify(status) and key != last_notification_key:
                message = _notification_message(status, lang=lang)
                _send_feedback_notification(message)
                console.print(message)
                last_notification_key = key
            elif (
                _should_notify_stuck(status)
                and state_age >= after
                and key != stuck_notification_key
            ):
                message = _notification_message(status, lang=lang, duration_seconds=state_age)
                _send_feedback_notification(message)
                console.print(message)
                stuck_notification_key = key
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("Stopped.")


@app.command(hidden=True)
def report(
    last: Annotated[bool, typer.Option("--last", help="Use latest session.")] = False,
    session: Annotated[str | None, typer.Option("--session", help="Specific session id.")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write report to file.")] = None,
) -> None:
    if output:
        write_report(output, session_id=session, last=last or session is None)
        console.print(f"Report written to: {output}")
    else:
        console.print(generate_report(session_id=session, last=last or session is None))


@app.command(hidden=True)
def doctor() -> None:
    storage = Storage()
    probe = run_probe(timeout=10)
    storage.insert_probe(probe)
    codex = find_codex_executable()
    console.print("[bold]Codex Doctor Environment Check[/bold]\n")
    console.print(f"Codex CLI: {'found at ' + codex if codex else 'not found'}")
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Hooks: {'installed' if hooks_installed() else 'not installed'}")
    console.print(f"Data dir: {storage.db_file.parent}")
    status = "reachable" if probe.ok else f"failed ({probe.error_type})"
    console.print(f"OpenAI probe: {status}")
    console.print(f"HTTP: {probe.http_code or 'n/a'}")
    console.print(f"Total: {probe.total_ms / 1000:.2f}s" if probe.total_ms else "Total: n/a")
    console.print("Proxy:")
    for key, value in probe.proxy_summary.items():
        console.print(f"  {key}: {value}")
    if probe.ok:
        console.print("\nResult: Network is reachable. If Codex is slow, basic connectivity is unlikely.")
    else:
        console.print("\nResult: Network or proxy may be blocking Codex.")


def render_status(status: CurrentStatus, *, lang: str = "zh") -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_row(f"[bold]Session[/bold]: {status.session_id}")
    table.add_row(f"[bold]Source[/bold]: {status.source}")
    table.add_row(f"[bold]Status[/bold]: {status.diagnosis.state}")
    table.add_row(f"[bold]Confidence[/bold]: {status.diagnosis.confidence.value}")
    table.add_row("")
    message = describe_status(status, lang=lang)
    if lang == "en":
        table.add_row(f"[bold]Current[/bold]: {message.current}")
        table.add_row(f"[bold]Reason[/bold]: {message.reason}")
        table.add_row(f"[bold]Suggestion[/bold]: {message.action}")
    else:
        table.add_row(f"[bold]当前状况[/bold]: {message.current}")
        table.add_row(f"[bold]堵塞原因[/bold]: {message.reason}")
        table.add_row(f"[bold]建议[/bold]: {message.action}")
    table.add_row("")
    table.add_row(f"[bold]Raw[/bold]: {status.diagnosis.state} / {status.diagnosis.title}")
    if status.network_probe:
        probe = status.network_probe
        network = "OK" if probe.ok else f"FAILED ({probe.error_type})"
        total = f"{probe.total_ms / 1000:.2f}s" if probe.total_ms else "n/a"
        table.add_row("")
        table.add_row(f"[bold]Network[/bold]: {network} HTTP={probe.http_code or 'n/a'} total={total}")
    if status.app_events:
        table.add_row("")
        table.add_row("[bold]Recent App events[/bold]:")
        for event in status.app_events[-8:]:
            table.add_row(f"{event.ts.strftime('%H:%M:%S')} {event.label}")
    if status.storage_error:
        table.add_row("")
        table.add_row(f"[bold red]Storage[/bold red]: {status.storage_error}")
    return Panel(table, title="Codex Doctor Diagnose")


def _should_notify(status: CurrentStatus, *, notify_all: bool = False) -> bool:
    if notify_all:
        return status.diagnosis.state != "IDLE"
    return status.diagnosis.state in {
        "NETWORK_SUSPECTED",
        "API_OR_MODEL_WAITING",
        "SANDBOX_OR_PERMISSION_BLOCKED",
        "APPROVAL_WAITING",
    }


def _should_notify_stuck(status: CurrentStatus) -> bool:
    return status.diagnosis.state in {
        "MODEL_STREAMING",
        "TOOL_RUNNING",
        "CODEX_THINKING_NO_TOOL",
        "PROMPT_SUBMITTED",
        "CONTEXT_COMPACTING",
    }


def _notification_message(
    status: CurrentStatus,
    *,
    lang: str = "zh",
    duration_seconds: float | None = None,
) -> str:
    message = describe_status(status, lang=lang, duration_seconds=duration_seconds)
    if lang == "en":
        return f"Current: {message.current} Reason: {message.reason} Suggestion: {message.action}"
    return message.notification_text()


def _normalize_lang(lang: str) -> str:
    normalized = lang.strip().lower()
    if normalized in {"zh", "cn", "chinese", "中文"}:
        return "zh"
    if normalized in {"en", "english"}:
        return "en"
    console.print("[red]Unsupported language. Use --lang zh or --lang en.[/red]")
    raise typer.Exit(2)


def _resolve_notify_settings(
    *,
    lang: str | None,
    after: float | None,
    interactive: bool,
) -> tuple[str, float]:
    should_prompt = interactive and sys.stdin.isatty() and (lang is None or after is None)
    if should_prompt:
        console.print("[bold]Codex Doctor 启动设置 / Startup Settings[/bold]")
        resolved_lang = _prompt_language() if lang is None else _normalize_lang(lang)
        resolved_after = _prompt_after_seconds() if after is None else _normalize_after(after)
        return resolved_lang, resolved_after

    return _normalize_lang(lang or "zh"), _normalize_after(after if after is not None else 45.0)


def _prompt_language() -> str:
    console.print("1. 中文")
    console.print("2. English")
    choice = Prompt.ask("选择语言 / Choose language", choices=["1", "2", "zh", "en"], default="1")
    return "en" if choice in {"2", "en"} else "zh"


def _prompt_after_seconds() -> float:
    while True:
        value = IntPrompt.ask("超过多少秒提醒 / Notify after seconds", default=45)
        if value > 0:
            return float(value)
        console.print("[red]Seconds must be greater than 0.[/red]")


def _normalize_after(after: float) -> float:
    if after <= 0:
        console.print("[red]--after must be greater than 0 seconds.[/red]")
        raise typer.Exit(2)
    return float(after)


def _test_message(lang: str) -> str:
    if lang == "en":
        return "Test notification: Codex Doctor popups are working."
    return "测试通知：如果你看到这条，Codex Doctor 弹窗可用。"


def _startup_message(lang: str, after: float) -> str:
    if lang == "en":
        return (
            "Codex Doctor is watching Codex App. "
            f"It will notify when a likely stuck state lasts over {after:.0f}s."
        )
    return f"Codex Doctor 正在观察 Codex App。疑似卡住超过 {after:.0f} 秒会弹窗说明原因。"


def _stop_message(lang: str) -> str:
    if lang == "en":
        return "Press Ctrl+C to stop."
    return "按 Ctrl+C 停止。"


def _send_feedback_notification(message: str) -> bool:
    result = send_notification("Codex Doctor", message)
    if not result.ok:
        console.print(f"[yellow]Notification failed:[/yellow] {result.error}")
        console.print("Codex Doctor will still print stuck feedback in this terminal.")
        return False
    return True


def _check_notifications_or_exit() -> None:
    console.print("Checking macOS notifications...")
    result = send_notification(
        "Codex Doctor",
        "通知自检通过。Codex 卡住时，Codex Doctor 会提示当前状况和堵塞原因。",
    )
    if result.ok:
        console.print("[green]Notification self-test passed.[/green]")
        return
    console.print("[red]Notification self-test failed.[/red]")
    console.print(str(result.error or "unknown error"))
    console.print("\nInstall was not completed because notifications are the core feature.")
    console.print(
        "Enable notifications for your terminal app, disable Focus if needed, then run "
        "[bold]codex-doctor install[/bold] again."
    )
    console.print(
        "For headless/CI use only: [bold]codex-doctor install --skip-notification-check[/bold]"
    )
    raise typer.Exit(1)
