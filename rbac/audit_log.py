"""
rbac/audit_log.py — Write and query the RBAC audit log.
"""

from __future__ import annotations

from .db import execute, fetchall, get_conn, init_db


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
        execute(
            conn,
            """
            INSERT INTO audit_log (wa_number, role, skill, query, allowed, deny_reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (wa_number, role, skill, query[:500], 1 if allowed else 0, deny_reason),
        )


def get_recent(wa_number: str, hours: int = 24) -> list[dict]:
    """Return recent audit entries for a WA number."""
    init_db()
    with get_conn() as conn:
        return fetchall(
            conn,
            """
            SELECT * FROM audit_log
            WHERE wa_number = %s
              AND ts >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY ts DESC
            """,
            (wa_number, hours),
        )


def get_denied(hours: int = 24) -> list[dict]:
    """Return all denied access attempts in the last N hours."""
    init_db()
    with get_conn() as conn:
        return fetchall(
            conn,
            """
            SELECT * FROM audit_log
            WHERE allowed = 0
              AND ts >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY ts DESC
            """,
            (hours,),
        )
