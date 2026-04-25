import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import db_path, settings_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created REAL NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    start_ts REAL,
    end_ts REAL,
    flagged_for_agent INTEGER DEFAULT 0,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created REAL NOT NULL,
    name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'shadow',
    spec TEXT NOT NULL
);
"""


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


@contextmanager
def connect():
    path = db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_event(source: str, kind: str, payload: dict) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO events (ts, source, kind, payload) VALUES (?, ?, ?, ?)",
            (time.time(), source, kind, json.dumps(payload)),
        )


def recent_events(limit: int = 100) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT ts, source, kind, payload FROM events ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"ts": r["ts"], "source": r["source"], "kind": r["kind"], "payload": json.loads(r["payload"])}
        for r in rows
    ]


def load_settings() -> dict:
    p: Path = settings_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_settings(settings: dict) -> None:
    settings_path().write_text(json.dumps(settings, indent=2))
