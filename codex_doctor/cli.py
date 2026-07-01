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
from .notifications import notify
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
) -> None:
    scope = "project" if project else "user"
    path = install_hooks(scope=scope, force=force)
    console.print("[bold green]Codex Doctor installed.[/bold green]")
    console.print(f"Hooks written to: {path}")
    console.print("\nNext:")
    console.print("1. Start Codex: [bold]codex-doctor run[/bold]")
    console.print("2. Or keep using Codex directly and watch: [bold]codex-doctor watch[/bold]")
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


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
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


@app.command()
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


@app.command(name="monitor")
def monitor_app(
    notify_user: Annotated[
        bool, typer.Option("--notify", help="Send macOS notification when Codex looks stuck.")
    ] = False,
    interval: Annotated[float, typer.Option("--interval", help="Polling interval in seconds.")] = 5.0,
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
    try:
        while True:
            status = diagnose_current(include_network=network, stale_seconds=stale_seconds)
            console.clear()
            console.print(render_status(status))
            key = (status.session_id, status.diagnosis.state, status.diagnosis.title)
            if notify_user and _should_notify(status) and key != last_notification_key:
                notify("Codex Doctor", f"{status.diagnosis.state}: {status.diagnosis.title}")
                last_notification_key = key
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("Stopped.")


@app.command()
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


@app.command()
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


def _should_notify(status: CurrentStatus) -> bool:
    return status.diagnosis.state in {
        "NETWORK_SUSPECTED",
        "API_OR_MODEL_WAITING",
        "SANDBOX_OR_PERMISSION_BLOCKED",
        "APPROVAL_WAITING",
    }
