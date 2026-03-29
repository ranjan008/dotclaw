"""
rbac/db.py — PostgreSQL setup for the DotClaw generic RBAC layer.

Schema changes from v1 (DISCOM-only):
  - Added  : domain TEXT column on users
  - Replaced: allowed_feeders/allowed_zones/allowed_dts → scope JSONB
  - Replaced: circle/division/sub_division              → org_unit JSONB
  - Result  : one schema works for any domain (DISCOM, supply chain, finance …)

Required env var:
    DATABASE_URL=postgresql://user:password@host:5432/dotclaw_rbac
"""

from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras
import psycopg2.pool

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://dotclaw:dotclaw@localhost:5432/dotclaw_rbac",
)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    wa_number       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    employee_id     TEXT,
    role            TEXT NOT NULL,
    domain          TEXT NOT NULL DEFAULT 'discom',
    org_unit        JSONB NOT NULL DEFAULT '{}',
    scope           JSONB NOT NULL DEFAULT '{}',
    active          INTEGER NOT NULL DEFAULT 1,
    registered_by   TEXT DEFAULT 'admin',
    registered_at   TIMESTAMPTZ DEFAULT NOW(),
    last_active     TIMESTAMPTZ
);
"""

_CREATE_AUDIT = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    wa_number   TEXT NOT NULL,
    role        TEXT,
    domain      TEXT,
    skill       TEXT,
    query       TEXT,
    allowed     INTEGER NOT NULL,
    deny_reason TEXT
);
"""

# ---------------------------------------------------------------------------
# Connection pool (lazily initialised)
# ---------------------------------------------------------------------------

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    return _pool


class _ManagedConn:
    """
    Context manager: borrow a connection from the pool, auto-commit on
    success, auto-rollback on exception, then return to pool.
    """

    def __init__(self) -> None:
        self._conn: psycopg2.extensions.connection | None = None

    def __enter__(self) -> psycopg2.extensions.connection:
        self._conn = _get_pool().getconn()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._conn is None:
            return False
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            _get_pool().putconn(self._conn)
        return False


def get_conn() -> _ManagedConn:
    return _ManagedConn()


# ---------------------------------------------------------------------------
# Query helpers (mirror the sqlite3 conn.execute pattern)
# ---------------------------------------------------------------------------

def execute(conn, sql: str, params: tuple = ()) -> psycopg2.extensions.cursor:
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def fetchone(conn, sql: str, params: tuple = ()) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def fetchall(conn, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def json_param(value: dict) -> psycopg2.extras.Json:
    """Wrap a dict as a psycopg2 Json parameter for JSONB columns."""
    return psycopg2.extras.Json(value)


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    with get_conn() as conn:
        execute(conn, _CREATE_USERS)
        execute(conn, _CREATE_AUDIT)
