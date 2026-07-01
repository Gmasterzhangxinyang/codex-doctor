from __future__ import annotations

import time

from .report import _event_from_row, _probe_from_row
from .state_machine import diagnose
from .storage import Storage


def watch(session: str = "latest", refresh_seconds: float = 1.0) -> None:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    storage = Storage()

    def render():
        selected = storage.get_latest_session() if session == "latest" else None
        session_id = selected["id"] if selected else session
        rows = list(reversed(storage.list_recent_events(session_id=session_id, limit=30)))
        events = [_event_from_row(row) for row in rows]
        probe_row = storage.latest_probe(session_id=session_id)
        probe = _probe_from_row(probe_row) if probe_row else None
        process = storage.latest_process_sample(session_id=session_id)
        diagnosis = diagnose(events, probe=probe, process_sample=dict(process) if process else None)

        table = Table.grid(expand=True)
        table.add_column(ratio=1)
        table.add_row(f"[bold]Session[/bold]: {session_id}")
        table.add_row(f"[bold]Status[/bold]: {diagnosis.state}")
        table.add_row(f"[bold]Confidence[/bold]: {diagnosis.confidence.value}")
        table.add_row("")
        table.add_row(f"[bold]Diagnosis[/bold]: {diagnosis.title}")
        table.add_row(diagnosis.explanation)
        table.add_row("")
        if probe:
            network = "OK" if probe.ok else f"FAILED ({probe.error_type})"
            table.add_row(f"[bold]Network[/bold]: {network} HTTP={probe.http_code or 'n/a'}")
        if process:
            table.add_row(
                "[bold]Process[/bold]: "
                f"CPU={process['cpu_percent']} MEM={process['memory_rss_mb']}MB "
                f"children={process['child_count']}"
            )
        table.add_row("")
        table.add_row("[bold]Last events[/bold]:")
        for event in events[-8:]:
            suffix = f" {event.tool_name}" if event.tool_name else ""
            table.add_row(f"{event.ts.strftime('%H:%M:%S')} {event.event_type}{suffix}")
        return Panel(table, title="Codex Doctor")

    try:
        with Live(render(), console=console, refresh_per_second=4) as live:
            while True:
                live.update(render())
                time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        console.print("Stopped.")
