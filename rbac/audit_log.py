"""
rbac/audit_log.py — Write and query the RBAC audit log.
"""

from __future__ import annotations

from .db import get_conn, init_db


def log_access(
    wa_number: str,
    *,
    role: str = "",
    skill: str = "",
    query: str = "",
    allowed: bool,
    deny_reason: str = "",
) -> None:
    """Append one row to audit_log."""
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (wa_number, role, skill, query, allowed, deny_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (wa_number, role, skill, query[:500], 1 if allowed else 0, deny_reason),
        )


def get_recent(wa_number: str, hours: int = 24) -> list[dict]:
    """Return recent audit entries for a WA number."""
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE wa_number = ?
              AND ts >= datetime('now', ? || ' hours')
            ORDER BY ts DESC
            """,
            (wa_number, f"-{hours}"),
        ).fetchall()
    return [dict(r) for r in rows]


def get_denied(hours: int = 24) -> list[dict]:
    """Return all denied access attempts in the last N hours."""
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE allowed = 0
              AND ts >= datetime('now', ? || ' hours')
            ORDER BY ts DESC
            """,
            (f"-{hours}",),
        ).fetchall()
    return [dict(r) for r in rows]
