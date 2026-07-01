from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from . import __version__
from .install import hooks_installed, install_hooks, uninstall_hooks
from .network_probe import run_probe
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
    codex = shutil.which("codex")
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
