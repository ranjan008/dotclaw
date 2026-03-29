"""
rbac/db.py — PostgreSQL database setup for the DotClaw RBAC layer.

Uses a SimpleConnectionPool so every request grabs a connection from the
pool, executes, commits/rolls-back, and returns it — no connection leaks.

Required env var:
    DATABASE_URL=postgresql://user:password@host:5432/dotclaw_rbac

Tables:
    users       — WA number → role + organisational scope
    audit_log   — every query attempt (allowed or denied)
"""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras
import psycopg2.pool

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://dotclaw:dotclaw@localhost:5432/dotclaw_rbac",
)

# DDL — executed once on startup via init_db()
_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    wa_number       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    employee_id     TEXT,
    role            TEXT NOT NULL,
    circle          TEXT,
    division        TEXT,
    sub_division    TEXT,
    allowed_feeders TEXT,
    allowed_zones   TEXT,
    allowed_dts     TEXT,
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
    skill       TEXT,
    query       TEXT,
    allowed     INTEGER NOT NULL,
    deny_reason TEXT
);
"""

# --------------------------------------------------------------------------- #
# Connection pool (lazily initialised)
# --------------------------------------------------------------------------- #

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    return _pool


class _ManagedConn:
    """
    Context manager that borrows a connection from the pool, auto-commits on
    success and auto-rolls-back on exception, then returns the connection.

    Usage:
        with get_conn() as conn:
            conn.execute(...)   # via cursor helper below
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
        return False  # do not suppress exceptions


def get_conn() -> _ManagedConn:
    """Return a context manager that yields a pooled psycopg2 connection."""
    return _ManagedConn()


# --------------------------------------------------------------------------- #
# Convenience query helpers (mirror the sqlite3 conn.execute() pattern)
# --------------------------------------------------------------------------- #

def execute(conn, sql: str, params: tuple = ()) -> psycopg2.extensions.cursor:
    """Run a single DML statement; returns cursor (rowcount available)."""
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def fetchone(conn, sql: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT and return the first row as a dict, or None."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None


def fetchall(conn, sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return all rows as a list of dicts."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


# --------------------------------------------------------------------------- #
# Schema initialisation
# --------------------------------------------------------------------------- #

def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    with get_conn() as conn:
        execute(conn, _CREATE_USERS)
        execute(conn, _CREATE_AUDIT)
