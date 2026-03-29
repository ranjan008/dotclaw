"""
rbac/admin_commands.py — Parse and execute admin commands sent over WhatsApp.

Only users with role 'it_admin' can run these commands.

Supported commands
------------------
ADD USER <number> name=<name> role=<role> [circle=X] [division=X]
         [feeders=FDR-001,FDR-002] [zones=Zone-A,Zone-B] [dts=DT-001]

DEACTIVATE USER <number>

LIST USERS [circle=X] [division=X] [role=X]

AUDIT <number> [last=<hours>]   (default 24h)

DENY REPORT [last=<hours>]      (denied access attempts)
"""

from __future__ import annotations

import re
import shlex
from typing import Optional

from .audit_log import get_denied, get_recent
from .user_registry import (
    ROLE_DISPLAY,
    VALID_ROLES,
    add_user,
    deactivate_user,
    list_users,
)


# --------------------------------------------------------------------------- #
# Helper parsers
# --------------------------------------------------------------------------- #

def _kv(text: str) -> dict[str, str]:
    """Parse 'key=value key2=value2 ...' into a dict."""
    return dict(m.groups() for m in re.finditer(r"(\w+)=([^\s]+)", text))


def _fmt_user(u: dict) -> str:
    role_label = ROLE_DISPLAY.get(u["role"], u["role"])
    parts = [
        f"  {u['name']} ({u.get('employee_id') or 'N/A'})",
        f"  WA: {u['wa_number']}",
        f"  Role: {role_label}",
    ]
    if u.get("circle"):
        parts.append(f"  Circle: {u['circle']}")
    if u.get("division"):
        parts.append(f"  Division: {u['division']}")
    if u.get("allowed_feeders"):
        parts.append(f"  Feeders: {u['allowed_feeders']}")
    if u.get("allowed_zones"):
        parts.append(f"  Zones: {u['allowed_zones']}")
    active_str = "ACTIVE" if u.get("active") else "INACTIVE"
    parts.append(f"  Status: {active_str}  |  Last active: {u.get('last_active') or 'never'}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #

def _cmd_add_user(body: str, registered_by: str) -> str:
    # Body format: <number> name=<name> role=<role> [key=val ...]
    tokens = body.split(None, 1)
    if not tokens:
        return "Usage: ADD USER <number> name=<name> role=<role> [circle=X] [division=X] [feeders=F1,F2] [zones=Z1,Z2]"

    wa_number = tokens[0]
    kv = _kv(tokens[1]) if len(tokens) > 1 else {}

    name = kv.get("name", "").replace("_", " ")
    role = kv.get("role", "")

    if not name:
        return "Error: 'name' is required. Example: name=Rajesh_Kumar"
    if not role:
        return f"Error: 'role' is required. Valid roles: {', '.join(sorted(VALID_ROLES))}"
    if role not in VALID_ROLES:
        return f"Error: unknown role '{role}'. Valid: {', '.join(sorted(VALID_ROLES))}"

    feeders = [f.strip() for f in kv.get("feeders", "").split(",") if f.strip()]
    zones   = [z.strip() for z in kv.get("zones", "").split(",") if z.strip()]
    dts     = [d.strip() for d in kv.get("dts", "").split(",") if d.strip()]

    try:
        user = add_user(
            wa_number,
            name,
            role,
            employee_id=kv.get("emp", ""),
            circle=kv.get("circle", ""),
            division=kv.get("division", ""),
            sub_division=kv.get("sub_division", ""),
            allowed_feeders=feeders,
            allowed_zones=zones,
            allowed_dts=dts,
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
        return f"User {wa_number} has been deactivated. Access revoked immediately."
    return f"User {wa_number} not found or already inactive."


def _cmd_list(body: str) -> str:
    kv = _kv(body)
    users = list_users(
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
    kv = _kv(body)
    hours = int(kv.get("last", 24))
    entries = get_recent(wa_number, hours=hours)
    if not entries:
        return f"No audit entries for {wa_number} in the last {hours}h."
    lines = [f"Audit log for {wa_number} — last {hours}h ({len(entries)} entries):"]
    for e in entries:
        status = "ALLOW" if e["allowed"] else "DENY"
        reason = f" [{e['deny_reason']}]" if e.get("deny_reason") else ""
        lines.append(f"  {e['ts']}  {status}  skill={e['skill'] or '-'}  {e['query'][:60]}{reason}")
    return "\n".join(lines)


def _cmd_deny_report(body: str) -> str:
    kv = _kv(body)
    hours = int(kv.get("last", 24))
    entries = get_denied(hours=hours)
    if not entries:
        return f"No denied access attempts in the last {hours}h."
    lines = [f"Denied access attempts — last {hours}h ({len(entries)}):"]
    for e in entries:
        lines.append(
            f"  {e['ts']}  {e['wa_number']}  role={e['role'] or '?'}  "
            f"skill={e['skill'] or '-'}  reason={e['deny_reason']}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main dispatcher
# --------------------------------------------------------------------------- #

_CMD_RE = re.compile(
    r"^(ADD USER|DEACTIVATE USER|LIST USERS|AUDIT|DENY REPORT)\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)


def is_admin_command(message: str) -> bool:
    return bool(_CMD_RE.match(message.strip()))


def handle(message: str, admin_wa: str) -> str:
    """
    Parse and execute an admin command.

    Args:
        message:  Raw WA message text from the admin.
        admin_wa: WA number of the admin (used as registered_by).

    Returns:
        Reply string to send back to the admin.
    """
    m = _CMD_RE.match(message.strip())
    if not m:
        return (
            "Unknown admin command. Supported:\n"
            "  ADD USER, DEACTIVATE USER, LIST USERS, AUDIT, DENY REPORT"
        )

    cmd  = m.group(1).upper()
    body = m.group(2).strip()

    if cmd == "ADD USER":
        return _cmd_add_user(body, registered_by=admin_wa)
    if cmd == "DEACTIVATE USER":
        return _cmd_deactivate(body)
    if cmd == "LIST USERS":
        return _cmd_list(body)
    if cmd == "AUDIT":
        return _cmd_audit(body)
    if cmd == "DENY REPORT":
        return _cmd_deny_report(body)

    return "Command recognised but not handled."
