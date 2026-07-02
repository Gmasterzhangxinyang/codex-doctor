from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.prompt import Prompt

from . import __version__, config
from .codex_locator import find_codex_executable
from .install import hooks_installed, install_hooks, uninstall_hooks
from .network_probe import run_probe
from .one_shot import OneShotOptions, diagnose_once, render_diagnosis, render_terminal_report, write_report
from .storage import Storage

app = typer.Typer(help="One-shot diagnosis for why Codex appears stuck.")
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"codex-doctor {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = False,
    network: Annotated[
        bool,
        typer.Option("--network/--no-network", help="Run a one-time OpenAI network probe."),
    ] = True,
    stale_seconds: Annotated[
        int,
        typer.Option("--stale-seconds", help="Seconds without Codex events before treating it as stale."),
    ] = 45,
    lang: Annotated[str | None, typer.Option("--lang", help="Output language: zh or en.")] = None,
) -> None:
    _ = version
    if ctx.invoked_subcommand is None:
        _run_diagnosis(
            include_network=network,
            stale_seconds=stale_seconds,
            lang=lang,
        )


@app.command()
def install(
    project: Annotated[bool, typer.Option("--project", help="Install hooks for this project only.")] = False,
    force: Annotated[bool, typer.Option("--force", help="Do not create a hooks backup.")] = False,
    lang: Annotated[str | None, typer.Option("--lang", help="Default language: zh or en.")] = None,
) -> None:
    selected_lang = _resolve_install_language(lang)
    config.save_settings({"lang": selected_lang})
    scope = "project" if project else "user"
    path = install_hooks(scope=scope, force=force)

    console.print("[bold green]Codex Doctor installed.[/bold green]")
    console.print(f"Hooks written to: {path}")
    console.print(f"Language: {_language_label(selected_lang)}")
    console.print("")
    console.print("When Codex looks stuck, run: [bold]codex-doctor[/bold]")
    console.print("To save a Markdown report, run: [bold]codex-doctor report -o codex-report.md[/bold]")


@app.command()
def diagnose(
    network: Annotated[
        bool,
        typer.Option("--network/--no-network", help="Run a one-time OpenAI network probe."),
    ] = True,
    stale_seconds: Annotated[
        int,
        typer.Option("--stale-seconds", help="Seconds without Codex events before treating it as stale."),
    ] = 45,
    lang: Annotated[str | None, typer.Option("--lang", help="Output language: zh or en.")] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Also write a Markdown report."),
    ] = None,
) -> None:
    _run_diagnosis(
        include_network=network,
        stale_seconds=stale_seconds,
        lang=lang,
        output=output,
    )


@app.command()
def report(
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write report to file.")] = None,
    network: Annotated[
        bool,
        typer.Option("--network/--no-network", help="Run a one-time OpenAI network probe."),
    ] = True,
    stale_seconds: Annotated[
        int,
        typer.Option("--stale-seconds", help="Seconds without Codex events before treating it as stale."),
    ] = 45,
    lang: Annotated[str | None, typer.Option("--lang", help="Report language: zh or en.")] = None,
) -> None:
    resolved_lang = _normalize_lang(lang) if lang else _configured_lang()
    status = diagnose_once(
        OneShotOptions(
            lang=resolved_lang,
            include_network=network,
            stale_seconds=stale_seconds,
        )
    )
    if output:
        write_report(output, status, lang=resolved_lang)
        console.print(f"Report written to: {output}")
        return
    console.print(render_terminal_report(status, lang=resolved_lang))


@app.command()
def doctor() -> None:
    storage = Storage()
    probe = run_probe(timeout=10)
    storage.insert_probe(probe)
    codex = find_codex_executable()

    console.print("[bold]Codex Doctor Check[/bold]\n")
    console.print(f"Codex CLI: {'found at ' + codex if codex else 'not found'}")
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Hooks: {'installed' if hooks_installed() else 'not installed'}")
    console.print(f"Data dir: {storage.db_file.parent}")
    status = "reachable" if probe.ok else f"failed ({probe.error_type})"
    console.print(f"OpenAI probe: {status}")
    console.print(f"HTTP: {probe.http_code or 'n/a'}")
    console.print(f"Total: {probe.total_ms / 1000:.2f}s" if probe.total_ms else "Total: n/a")


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


def _run_diagnosis(
    *,
    include_network: bool = True,
    stale_seconds: int = 45,
    lang: str | None = None,
    output: Path | None = None,
) -> None:
    resolved_lang = _normalize_lang(lang) if lang else _configured_lang()
    status = diagnose_once(
        OneShotOptions(
            lang=resolved_lang,
            include_network=include_network,
            stale_seconds=stale_seconds,
        )
    )
    console.print(render_diagnosis(status, lang=resolved_lang))
    if output:
        write_report(output, status, lang=resolved_lang)
        console.print(f"Report written to: {output}")


def _resolve_install_language(lang: str | None) -> str:
    if lang:
        return _normalize_lang(lang)
    if sys.stdin.isatty():
        console.print("[bold]Codex Doctor Install[/bold]")
        return _prompt_language()
    return "zh"


def _prompt_language() -> str:
    console.print("1. 中文")
    console.print("2. English")
    choice = Prompt.ask("选择语言 / Choose language", choices=["1", "2", "zh", "en"], default="1")
    return "en" if choice in {"2", "en"} else "zh"


def _configured_lang() -> str:
    raw = config.load_settings().get("lang")
    if isinstance(raw, str):
        try:
            return _normalize_lang(raw)
        except typer.Exit:
            return "zh"
    return "zh"


def _normalize_lang(lang: str) -> str:
    normalized = lang.strip().lower()
    if normalized in {"zh", "cn", "chinese", "中文"}:
        return "zh"
    if normalized in {"en", "english"}:
        return "en"
    console.print("[red]Unsupported language. Use --lang zh or --lang en.[/red]")
    raise typer.Exit(2)


def _language_label(lang: str) -> str:
    return "中文" if lang == "zh" else "English"
