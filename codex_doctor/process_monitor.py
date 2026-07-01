from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4


def sample_process_tree(pid: int, session_id: str | None = None) -> dict:
    try:
        import psutil
    except Exception as exc:
        return {
            "id": uuid4().hex,
            "session_id": session_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "root_pid": pid,
            "child_count": 0,
            "cpu_percent": None,
            "memory_rss_mb": None,
            "disk_read_mb": None,
            "disk_write_mb": None,
            "active_children": [],
            "error": f"psutil unavailable: {exc}",
        }

    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
        cpu = sum(process.cpu_percent(interval=None) for process in processes if process.is_running())
        memory = sum(process.memory_info().rss for process in processes if process.is_running()) / 1024 / 1024
        disk_read = 0.0
        disk_write = 0.0
        active_children = []
        for process in processes:
            try:
                io = cast(Any, process).io_counters()
                disk_read += io.read_bytes / 1024 / 1024
                disk_write += io.write_bytes / 1024 / 1024
            except Exception:
                pass
            if process.pid != pid:
                active_children.append(
                    {
                        "pid": process.pid,
                        "name": process.name(),
                        "status": process.status(),
                        "cmdline": " ".join(process.cmdline())[:300],
                    }
                )
        return {
            "id": uuid4().hex,
            "session_id": session_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "root_pid": pid,
            "child_count": max(0, len(processes) - 1),
            "cpu_percent": cpu,
            "memory_rss_mb": memory,
            "disk_read_mb": disk_read,
            "disk_write_mb": disk_write,
            "active_children": active_children,
        }
    except Exception as exc:
        return {
            "id": uuid4().hex,
            "session_id": session_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "root_pid": pid,
            "child_count": 0,
            "cpu_percent": None,
            "memory_rss_mb": None,
            "disk_read_mb": None,
            "disk_write_mb": None,
            "active_children": [],
            "error": str(exc),
        }
