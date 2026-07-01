from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .codex_locator import find_codex_executable
from .current_status import CurrentStatus, diagnose_current
from .install import hooks_installed, install_hooks, uninstall_hooks
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
) -> None:
    status = diagnose_current(
        include_network=network, stale_seconds=stale_seconds, probe_when_active=True
    )
    console.print(render_status(status))


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
        float,
        typer.Option("--after", help="Seconds before Codex Doctor reports a stuck active state."),
    ] = 45.0,
    test: Annotated[
        bool,
        typer.Option("--test", help="Send one test notification and exit."),
    ] = False,
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
        ok = _send_feedback_notification("Test notification from Codex Doctor.")
        if not ok:
            raise typer.Exit(1)
        return
    console.print(
        f"Codex Doctor is watching for stuck Codex App activity. Feedback after {after:.0f}s."
    )
    console.print("Press Ctrl+C to stop.")
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
                message = _notification_message(status)
                _send_feedback_notification(message)
                console.print(message)
                last_notification_key = key
            elif (
                _should_notify_stuck(status)
                and state_age >= after
                and key != stuck_notification_key
            ):
                message = _notification_message(status, duration_seconds=state_age)
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


def render_status(status: CurrentStatus) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_row(f"[bold]Session[/bold]: {status.session_id}")
    table.add_row(f"[bold]Source[/bold]: {status.source}")
    table.add_row(f"[bold]Status[/bold]: {status.diagnosis.state}")
    table.add_row(f"[bold]Confidence[/bold]: {status.diagnosis.confidence.value}")
    table.add_row("")
    table.add_row(f"[bold]Diagnosis[/bold]: {status.diagnosis.title}")
    table.add_row(status.diagnosis.explanation)
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


def _notification_message(status: CurrentStatus, *, duration_seconds: float | None = None) -> str:
    state = status.diagnosis.state
    if duration_seconds is not None:
        state = f"{state} for {duration_seconds:.0f}s"
    return f"{state}: {status.diagnosis.title}"


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
        "Notification self-test passed. Codex Doctor can alert you when Codex is stuck.",
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
