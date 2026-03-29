"""
rbac/user_registry.py — CRUD for the DotClaw user registry.

Roles (lowest → highest privilege):
  junior_engineer, revenue_protection, mis_finance,
  sub_division_ae, division_ee, circle_se,
  director_ops, cmd, it_admin
"""

from __future__ import annotations

import re
from typing import Optional

from .db import execute, fetchall, fetchone, get_conn, init_db

# --------------------------------------------------------------------------- #
# Role definitions
# --------------------------------------------------------------------------- #

VALID_ROLES = {
    "junior_engineer",
    "revenue_protection",
    "mis_finance",
    "sub_division_ae",
    "division_ee",
    "circle_se",
    "director_ops",
    "cmd",
    "it_admin",
}

# Roles that can see ALL feeders / zones without a whitelist
GLOBAL_ACCESS_ROLES = {"cmd", "director_ops", "it_admin", "mis_finance"}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _normalise_wa(number: str) -> str:
    """Strip spaces / dashes; ensure leading +."""
    cleaned = re.sub(r"[\s\-()]", "", number)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def _split(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _join(items: list[str]) -> str:
    return ",".join(i.upper() for i in items)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def add_user(
    wa_number: str,
    name: str,
    role: str,
    *,
    employee_id: str = "",
    circle: str = "",
    division: str = "",
    sub_division: str = "",
    allowed_feeders: list[str] = None,
    allowed_zones: list[str] = None,
    allowed_dts: list[str] = None,
    registered_by: str = "admin",
) -> dict:
    """Insert a new user. Returns the created user record."""
    init_db()
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role '{role}'. Valid roles: {sorted(VALID_ROLES)}")

    wa = _normalise_wa(wa_number)

    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO users
              (wa_number, name, employee_id, role, circle, division, sub_division,
               allowed_feeders, allowed_zones, allowed_dts, active, registered_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)
            """,
            (
                wa, name, employee_id, role,
                circle, division, sub_division,
                _join(allowed_feeders or []),
                _join(allowed_zones  or []),
                _join(allowed_dts    or []),
                registered_by,
            ),
        )
    return get_user(wa)


def get_user(wa_number: str) -> Optional[dict]:
    """Return user dict or None if not found / inactive."""
    init_db()
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        return fetchone(
            conn,
            "SELECT * FROM users WHERE wa_number = %s AND active = 1",
            (wa,),
        )


def deactivate_user(wa_number: str) -> bool:
    """Mark a user inactive. Returns True if a record was updated."""
    init_db()
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        cur = execute(conn, "UPDATE users SET active = 0 WHERE wa_number = %s", (wa,))
    return cur.rowcount > 0


def touch_user(wa_number: str) -> None:
    """Update last_active timestamp."""
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        execute(conn, "UPDATE users SET last_active = NOW() WHERE wa_number = %s", (wa,))


def list_users(
    *,
    circle: str = None,
    division: str = None,
    role: str = None,
    active_only: bool = True,
) -> list[dict]:
    """Return users matching optional filters."""
    init_db()
    clauses = ["1=1"]
    params: list = []
    if active_only:
        clauses.append("active = 1")
    if circle:
        clauses.append("circle = %s")
        params.append(circle)
    if division:
        clauses.append("division = %s")
        params.append(division)
    if role:
        clauses.append("role = %s")
        params.append(role)
    sql = "SELECT * FROM users WHERE " + " AND ".join(clauses)
    with get_conn() as conn:
        return fetchall(conn, sql, tuple(params))


def get_scope(user: dict) -> dict:
    """
    Derive the effective access scope for a user.

    Returns:
        {
          "all_access": bool,           # True for CMD / director / IT admin
          "allowed_feeders": list[str],
          "allowed_zones":   list[str],
          "allowed_dts":     list[str],
        }
    """
    role = user.get("role", "")
    if role in GLOBAL_ACCESS_ROLES:
        return {
            "all_access": True,
            "allowed_feeders": [],
            "allowed_zones": [],
            "allowed_dts": [],
        }
    return {
        "all_access": False,
        "allowed_feeders": _split(user.get("allowed_feeders")),
        "allowed_zones":   _split(user.get("allowed_zones")),
        "allowed_dts":     _split(user.get("allowed_dts")),
    }
