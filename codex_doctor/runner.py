from __future__ import annotations

import os
import pty
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .process_monitor import sample_process_tree
from .schemas import Event, Session
from .storage import Storage


def run_codex(args: list[str]) -> int:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI was not found on PATH.")

    storage = Storage()
    session = storage.create_session(Session(cwd=str(Path.cwd()), codex_args=" ".join(args)))
    env = os.environ.copy()
    env["CODEX_DOCTOR_SESSION"] = session.id
    command = [codex, *args]

    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, env=env)
    os.close(slave_fd)
    storage.insert_event(
        Event(
            source="wrapper",
            session_id=session.id,
            event_type="SessionStart",
            cwd=str(Path.cwd()),
            raw_redacted={"command": ["codex", *args]},
        )
    )

    last_sample = 0.0
    try:
        while process.poll() is None:
            readable, _, _ = select.select([master_fd, sys.stdin], [], [], 0.2)
            if master_fd in readable:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    data = b""
                if data:
                    os.write(sys.stdout.fileno(), data)
                    storage.insert_event(
                        Event(
                            source="wrapper",
                            session_id=session.id,
                            event_type="TerminalOutput",
                            cwd=str(Path.cwd()),
                            raw_redacted={"bytes": len(data)},
                        )
                    )
            if sys.stdin in readable:
                incoming = os.read(sys.stdin.fileno(), 4096)
                if incoming:
                    os.write(master_fd, incoming)
            if time.monotonic() - last_sample > 1:
                last_sample = time.monotonic()
                storage.insert_process_sample(sample_process_tree(process.pid, session.id))
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        code = process.wait()
        storage.insert_event(
            Event(
                source="wrapper",
                session_id=session.id,
                event_type="Stop",
                cwd=str(Path.cwd()),
                success=code == 0,
                raw_redacted={"returncode": code},
            )
        )
        storage.end_session(session.id, status="done" if code == 0 else "error")
    return int(code or 0)
