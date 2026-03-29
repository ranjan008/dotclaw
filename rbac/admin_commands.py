"""
rbac/admin_commands.py — Parse and execute admin commands sent over WhatsApp.

Only users with role 'it_admin' (any domain) can run these commands.

Supported commands
------------------
ADD USER <number> name=<name> role=<role> domain=<domain>
         [<org_unit_key>=<value> ...]
         [<scope_key>=<id1,id2,...> ...]

DEACTIVATE USER <number>

LIST USERS [domain=<domain>] [circle=X] [division=X] [role=X]

AUDIT <number> [last=<hours>]

DENY REPORT [last=<hours>]

Examples
--------
DISCOM:
  ADD USER +91XXXXXXXXXX name=Raju_Verma role=junior_engineer domain=discom
           circle=Circle-North division=Division-3
           feeders=FDR-001,FDR-002 zones=Zone-A

Supply chain:
  ADD USER +91XXXXXXXXXX name=Neha_Singh role=warehouse_officer domain=supplychain
           region=North plant=PLANT-DEL
           plants=PLANT-DEL warehouses=WH-DEL-01,WH-DEL-02

Finance:
  ADD USER +91XXXXXXXXXX name=Arjun_Mehta role=branch_manager domain=finance
           region=West branch=BR-MUM-001
           branches=BR-MUM-001,BR-MUM-002
"""

from __future__ import annotations

import re

from .audit_log import get_denied, get_recent
from .domain_loader import (
    get_org_unit_keys,
    get_role_display,
    get_scope_keys,
    get_valid_roles,
)
from .user_registry import add_user, deactivate_user, list_users


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kv(text: str) -> dict[str, str]:
    """Parse 'key=value key2=value2' into a dict."""
    return dict(m.groups() for m in re.finditer(r"(\w+)=([^\s]+)", text))


def _fmt_user(u: dict) -> str:
    domain = u.get("domain", "?")
    try:
        role_label = get_role_display(domain, u["role"])
    except Exception:
        role_label = u["role"]

    org  = u.get("org_unit") or {}
    scp  = u.get("scope") or {}
    if isinstance(org, str):
        import json; org = json.loads(org)
    if isinstance(scp, str):
        import json; scp = json.loads(scp)

    parts = [
        f"  {u['name']} ({u.get('employee_id') or 'N/A'})",
        f"  WA     : {u['wa_number']}",
        f"  Domain : {domain}",
        f"  Role   : {role_label}",
    ]
    for k, v in org.items():
        if v:
            parts.append(f"  {k.replace('_',' ').title():<10}: {v}")
    for k, vals in scp.items():
        if vals:
            parts.append(f"  {k:<12}: {', '.join(vals) if isinstance(vals, list) else vals}")
    active_str = "ACTIVE" if u.get("active") else "INACTIVE"
    parts.append(f"  Status : {active_str}  |  Last: {u.get('last_active') or 'never'}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_add_user(body: str, registered_by: str) -> str:
    tokens = body.split(None, 1)
    if not tokens:
        return "Usage: ADD USER <number> name=<name> role=<role> domain=<domain> [key=val ...]"

    wa_number = tokens[0]
    kv = _kv(tokens[1]) if len(tokens) > 1 else {}

    name   = kv.get("name", "").replace("_", " ")
    role   = kv.get("role", "")
    domain = kv.get("domain", "discom")

    if not name:
        return "Error: 'name' is required. Example: name=Raju_Verma"
    if not role:
        return f"Error: 'role' is required."

    # Validate role against domain config
    try:
        valid_roles = get_valid_roles(domain)
    except ValueError as exc:
        return f"Error: {exc}"

    if role not in valid_roles:
        return f"Error: unknown role '{role}' for domain '{domain}'. Valid: {', '.join(sorted(valid_roles))}"

    # Split kv into org_unit and scope based on domain config
    try:
        org_keys   = set(get_org_unit_keys(domain))
        scope_keys = set(get_scope_keys(domain))
    except ValueError as exc:
        return f"Error loading domain config: {exc}"

    org_unit: dict[str, str]       = {}
    scope:    dict[str, list[str]] = {}

    for key, val in kv.items():
        if key in {"name", "role", "domain", "emp"}:
            continue
        if key in org_keys:
            org_unit[key] = val
        elif key in scope_keys:
            scope[key] = [v.strip().upper() for v in val.split(",") if v.strip()]

    try:
        user = add_user(
            wa_number,
            name,
            role,
            domain,
            employee_id=kv.get("emp", ""),
            org_unit=org_unit,
            scope=scope,
            registered_by=registered_by,
        )
        return f"User registered successfully:\n{_fmt_user(user)}"
    except Exception as exc:
        return f"Error registering user: {exc}"


def _cmd_deactivate(body: str) -> str:
    wa_number = body.strip().split()[0] if body.strip() else ""
    if not wa_number:
        return "Usage: DEACTIVATE USER <number>"
    ok = deactivate_user(wa_number)
    if ok:
        return f"User {wa_number} deactivated. Access revoked immediately."
    return f"User {wa_number} not found or already inactive."


def _cmd_list(body: str) -> str:
    kv = _kv(body)
    users = list_users(
        domain=kv.get("domain"),
        circle=kv.get("circle"),
        division=kv.get("division"),
        role=kv.get("role"),
    )
    if not users:
        return "No active users found matching the filter."
    lines = [f"Active users ({len(users)}):"]
    for u in users:
        lines.append("  ---")
        lines.append(_fmt_user(u))
    return "\n".join(lines)


def _cmd_audit(body: str) -> str:
    parts = body.strip().split()
    if not parts:
        return "Usage: AUDIT <number> [last=<hours>]"
    wa_number = parts[0]
    hours = int(_kv(body).get("last", 24))
    entries = get_recent(wa_number, hours=hours)
    if not entries:
        return f"No audit entries for {wa_number} in the last {hours}h."
    lines = [f"Audit log for {wa_number} — last {hours}h ({len(entries)} entries):"]
    for e in entries:
        status = "ALLOW" if e["allowed"] else "DENY"
        reason = f" [{e['deny_reason']}]" if e.get("deny_reason") else ""
        lines.append(
            f"  {e['ts']}  {status}  domain={e.get('domain') or '?'}  "
            f"skill={e['skill'] or '-'}  {e['query'][:60]}{reason}"
        )
    return "\n".join(lines)


def _cmd_deny_report(body: str) -> str:
    hours = int(_kv(body).get("last", 24))
    entries = get_denied(hours=hours)
    if not entries:
        return f"No denied access attempts in the last {hours}h."
    lines = [f"Denied attempts — last {hours}h ({len(entries)}):"]
    for e in entries:
        lines.append(
            f"  {e['ts']}  {e['wa_number']}  domain={e.get('domain') or '?'}  "
            f"role={e['role'] or '?'}  reason={e['deny_reason']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_CMD_RE = re.compile(
    r"^(ADD USER|DEACTIVATE USER|LIST USERS|AUDIT|DENY REPORT)\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)


def is_admin_command(message: str) -> bool:
    return bool(_CMD_RE.match(message.strip()))


def handle(message: str, admin_wa: str) -> str:
    m = _CMD_RE.match(message.strip())
    if not m:
        return (
            "Unknown command. Supported:\n"
            "  ADD USER, DEACTIVATE USER, LIST USERS, AUDIT, DENY REPORT"
        )
    cmd  = m.group(1).upper()
    body = m.group(2).strip()

    if cmd == "ADD USER":        return _cmd_add_user(body, registered_by=admin_wa)
    if cmd == "DEACTIVATE USER": return _cmd_deactivate(body)
    if cmd == "LIST USERS":      return _cmd_list(body)
    if cmd == "AUDIT":           return _cmd_audit(body)
    if cmd == "DENY REPORT":     return _cmd_deny_report(body)
    return "Command recognised but not handled."
