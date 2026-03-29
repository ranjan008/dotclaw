"""
rbac/db.py — SQLite database setup for the DotClaw RBAC layer.

Creates two tables:
  - users       : WA number → role + organisational scope
  - audit_log   : every query attempt (allowed or denied)
"""

import os
import sqlite3

# DB file lives at project root by default; can be overridden via env var
_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "rbac.db")
DB_PATH = os.getenv("RBAC_DB_PATH", os.path.abspath(_DEFAULT_DB))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    wa_number       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    employee_id     TEXT,
    role            TEXT NOT NULL,
    circle          TEXT,
    division        TEXT,
    sub_division    TEXT,
    allowed_feeders TEXT,   -- comma-separated, e.g. "FDR-001,FDR-002"
    allowed_zones   TEXT,   -- comma-separated, e.g. "Zone-A,Zone-B"
    allowed_dts     TEXT,   -- comma-separated DT cluster IDs for AMI scope
    active          INTEGER NOT NULL DEFAULT 1,
    registered_by   TEXT DEFAULT 'admin',
    registered_at   TEXT DEFAULT (datetime('now')),
    last_active     TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL DEFAULT (datetime('now')),
    wa_number       TEXT NOT NULL,
    role            TEXT,
    skill           TEXT,
    query           TEXT,
    allowed         INTEGER NOT NULL,  -- 1 = permitted, 0 = denied
    deny_reason     TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    """Return a connection with row_factory set to dict-like Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
