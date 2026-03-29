"""
rbac/user_registry.py — Generic CRUD for the DotClaw user registry.

Roles and scope keys are now domain-driven (loaded from domain_config/*.yaml).
org_unit and scope are stored as JSONB, so any domain hierarchy fits without
schema changes.
"""

from __future__ import annotations

import re
from typing import Optional

from .db import execute, fetchall, fetchone, get_conn, init_db, json_param
from .domain_loader import (
    get_global_roles,
    get_valid_roles,
    load as load_domain_cfg,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_wa(number: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", number)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def _split(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_user(
    wa_number: str,
    name: str,
    role: str,
    domain: str = "discom",
    *,
    employee_id: str = "",
    org_unit: dict = None,
    scope: dict = None,
    registered_by: str = "admin",
) -> dict:
    """
    Insert a new user.

    Args:
        wa_number:    WhatsApp number, e.g. '+919000000099'
        name:         Full name
        role:         Role string — must exist in domain_config/<domain>.yaml
        domain:       Domain identifier, e.g. 'discom', 'supplychain', 'finance'
        employee_id:  Optional employee ID
        org_unit:     Dict of org hierarchy, e.g. {"circle": "North", "division": "Div-3"}
        scope:        Dict of permitted resource IDs, e.g. {"feeders": ["FDR-001"]}
        registered_by: WA number of admin who registered this user

    Returns the created user dict.
    """
    init_db()
    valid = get_valid_roles(domain)
    if role not in valid:
        raise ValueError(f"Unknown role '{role}' for domain '{domain}'. Valid: {sorted(valid)}")

    wa = _normalise_wa(wa_number)

    with get_conn() as conn:
        execute(
            conn,
            """
            INSERT INTO users
              (wa_number, name, employee_id, role, domain, org_unit, scope,
               active, registered_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
            """,
            (
                wa, name, employee_id, role, domain,
                json_param(org_unit or {}),
                json_param(scope or {}),
                registered_by,
            ),
        )
    return get_user(wa)


def get_user(wa_number: str) -> Optional[dict]:
    """Return active user dict or None."""
    init_db()
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        return fetchone(
            conn,
            "SELECT * FROM users WHERE wa_number = %s AND active = 1",
            (wa,),
        )


def deactivate_user(wa_number: str) -> bool:
    init_db()
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        cur = execute(conn, "UPDATE users SET active = 0 WHERE wa_number = %s", (wa,))
    return cur.rowcount > 0


def touch_user(wa_number: str) -> None:
    wa = _normalise_wa(wa_number)
    with get_conn() as conn:
        execute(conn, "UPDATE users SET last_active = NOW() WHERE wa_number = %s", (wa,))


def list_users(
    *,
    domain: str = None,
    circle: str = None,     # convenience alias → org_unit->>'circle'
    division: str = None,   # convenience alias → org_unit->>'division'
    role: str = None,
    active_only: bool = True,
) -> list[dict]:
    clauses = ["1=1"]
    params: list = []
    if active_only:
        clauses.append("active = 1")
    if domain:
        clauses.append("domain = %s")
        params.append(domain)
    if circle:
        clauses.append("org_unit->>'circle' = %s")
        params.append(circle)
    if division:
        clauses.append("org_unit->>'division' = %s")
        params.append(division)
    if role:
        clauses.append("role = %s")
        params.append(role)
    sql = "SELECT * FROM users WHERE " + " AND ".join(clauses)
    init_db()
    with get_conn() as conn:
        return fetchall(conn, sql, tuple(params))


def get_scope(user: dict) -> dict:
    """
    Derive effective access scope for a user.

    Returns:
        {
          "all_access": bool,
          "scope":      dict,   # e.g. {"feeders": ["FDR-001"], "zones": ["Zone-A"]}
        }
    """
    domain = user.get("domain", "discom")
    role   = user.get("role", "")

    if role in get_global_roles(domain):
        return {"all_access": True, "scope": {}}

    raw_scope = user.get("scope") or {}
    # psycopg2 with RealDictCursor returns JSONB as a Python dict already
    if isinstance(raw_scope, str):
        import json
        raw_scope = json.loads(raw_scope)

    return {"all_access": False, "scope": raw_scope}
