from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from . import config
from .schemas import Diagnosis, Event, NetworkProbe, Session


class Storage:
    def __init__(self, db_file: Path | None = None, jsonl_file: Path | None = None) -> None:
        if db_file is None or jsonl_file is None:
            data_dir = config.ensure_user_data_dir()
            self.db_file = db_file if db_file is not None else data_dir / "codex-doctor.db"
            self.jsonl_file = jsonl_file if jsonl_file is not None else data_dir / "events.jsonl"
        else:
            self.db_file = db_file
            self.jsonl_file = jsonl_file
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_file.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    cwd TEXT,
                    codex_args TEXT,
                    codex_version TEXT,
                    model TEXT,
                    status TEXT,
                    total_duration_ms INTEGER
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    ts TEXT NOT NULL,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    turn_id TEXT,
                    cwd TEXT,
                    model TEXT,
                    permission_mode TEXT,
                    tool_name TEXT,
                    tool_input_hash TEXT,
                    tool_input_snippet TEXT,
                    success INTEGER,
                    duration_ms INTEGER,
                    raw_redacted_json TEXT
                );

                CREATE TABLE IF NOT EXISTS network_probes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    ts TEXT NOT NULL,
                    target TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    http_code INTEGER,
                    dns_ms REAL,
                    connect_ms REAL,
                    tls_ms REAL,
                    ttfb_ms REAL,
                    total_ms REAL,
                    error_type TEXT,
                    error_message TEXT,
                    proxy_summary TEXT
                );

                CREATE TABLE IF NOT EXISTS process_samples (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    ts TEXT NOT NULL,
                    root_pid INTEGER,
                    child_count INTEGER,
                    cpu_percent REAL,
                    memory_rss_mb REAL,
                    disk_read_mb REAL,
                    disk_write_mb REAL,
                    active_children_json TEXT
                );

                CREATE TABLE IF NOT EXISTS diagnoses (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    ts TEXT NOT NULL,
                    state TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    title TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    evidence_json TEXT NOT NULL
                );
                """
            )

    def create_session(self, session: Session) -> Session:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (id, started_at, ended_at, cwd, codex_args, codex_version, model, status, total_duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.cwd,
                    session.codex_args,
                    session.codex_version,
                    session.model,
                    session.status,
                    session.total_duration_ms,
                ),
            )
        return session

    def end_session(self, session_id: str, status: str = "done") -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT started_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
            total = None
            ended = Event(event_type="internal").ts
            if row:
                from datetime import datetime

                started = datetime.fromisoformat(row["started_at"])
                total = int((ended - started).total_seconds() * 1000)
            conn.execute(
                "UPDATE sessions SET ended_at = ?, status = ?, total_duration_ms = ? WHERE id = ?",
                (ended.isoformat(), status, total, session_id),
            )

    def append_jsonl(self, payload: dict[str, Any]) -> None:
        with self.jsonl_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def insert_event(self, event: Event) -> Event:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (id, session_id, ts, source, event_type, turn_id, cwd, model, permission_mode, tool_name,
                 tool_input_hash, tool_input_snippet, success, duration_ms, raw_redacted_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.session_id,
                    event.ts.isoformat(),
                    event.source,
                    event.event_type,
                    event.turn_id,
                    event.cwd,
                    event.model,
                    event.permission_mode,
                    event.tool_name,
                    event.tool_input_hash,
                    event.tool_input_snippet,
                    None if event.success is None else int(event.success),
                    event.duration_ms,
                    json.dumps(event.raw_redacted, ensure_ascii=False, default=str),
                ),
            )
        self.append_jsonl(event.model_dump(mode="json"))
        return event

    def insert_probe(self, probe: NetworkProbe) -> NetworkProbe:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO network_probes
                (id, session_id, ts, target, ok, http_code, dns_ms, connect_ms, tls_ms, ttfb_ms, total_ms,
                 error_type, error_message, proxy_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    probe.id,
                    probe.session_id,
                    probe.ts.isoformat(),
                    probe.target,
                    int(probe.ok),
                    probe.http_code,
                    probe.dns_ms,
                    probe.connect_ms,
                    probe.tls_ms,
                    probe.ttfb_ms,
                    probe.total_ms,
                    probe.error_type,
                    probe.error_message,
                    json.dumps(probe.proxy_summary, ensure_ascii=False, default=str),
                ),
            )
        return probe

    def insert_diagnosis(self, diagnosis: Diagnosis) -> Diagnosis:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO diagnoses
                (id, session_id, ts, state, confidence, title, explanation, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    diagnosis.id,
                    diagnosis.session_id,
                    diagnosis.ts.isoformat(),
                    diagnosis.state,
                    diagnosis.confidence.value,
                    diagnosis.title,
                    diagnosis.explanation,
                    json.dumps(diagnosis.evidence, ensure_ascii=False, default=str),
                ),
            )
        return diagnosis

    def insert_process_sample(self, sample: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO process_samples
                (id, session_id, ts, root_pid, child_count, cpu_percent, memory_rss_mb, disk_read_mb,
                 disk_write_mb, active_children_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample["id"],
                    sample.get("session_id"),
                    sample["ts"],
                    sample.get("root_pid"),
                    sample.get("child_count"),
                    sample.get("cpu_percent"),
                    sample.get("memory_rss_mb"),
                    sample.get("disk_read_mb"),
                    sample.get("disk_write_mb"),
                    json.dumps(sample.get("active_children", []), ensure_ascii=False, default=str),
                ),
            )

    def get_latest_session(self) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1").fetchone()

    def list_recent_events(self, session_id: str | None = None, limit: int = 20) -> list[sqlite3.Row]:
        query = "SELECT * FROM events"
        params: list[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return list(conn.execute(query, params).fetchall())

    def latest_probe(self, session_id: str | None = None) -> sqlite3.Row | None:
        query = "SELECT * FROM network_probes"
        params: list[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY ts DESC LIMIT 1"
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def latest_process_sample(self, session_id: str | None = None) -> sqlite3.Row | None:
        query = "SELECT * FROM process_samples"
        params: list[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY ts DESC LIMIT 1"
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def list_diagnoses(self, session_id: str | None = None, limit: int = 20) -> list[sqlite3.Row]:
        query = "SELECT * FROM diagnoses"
        params: list[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return list(conn.execute(query, params).fetchall())
