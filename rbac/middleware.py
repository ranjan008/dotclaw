"""
rbac/middleware.py — Generic RBAC enforcement for any domain.

Flow for every incoming WhatsApp message:
  1. Look up sender in user registry → get domain + role + scope.
  2. If unknown number → deny with registration message.
  3. Detect which skill the message targets (domain skill_patterns).
  4. Extract resource IDs from message (domain resource_patterns).
  5. Check each extracted resource against the user's scope whitelist.
  6. If denied → log + return denial reply.
  7. If allowed → build enriched prompt (RBAC context block + original message)
     so the Claude agent knows the user's role, scope, and which skill flags to pass.
"""

from __future__ import annotations

import os
from typing import Optional

from .audit_log import log_access
from .domain_loader import (
    detect_skill,
    extract_resources,
    get_denial_message,
    get_role_display,
    get_skill_scope_flags,
    load as load_domain_cfg,
)
from .user_registry import get_scope, get_user, touch_user

# Active domain — determines which domain_config/*.yaml to load.
# Override per-request if running a multi-domain gateway.
DEFAULT_DOMAIN: str = os.getenv("RBAC_DOMAIN", "discom")


# ---------------------------------------------------------------------------
# Scope context builder
# ---------------------------------------------------------------------------

def _build_scope_context(user: dict, scope: dict) -> str:
    """
    Build the RBAC context block prepended to the user's message.
    The agent reads this to:
      - understand who is asking and what their role/scope is
      - pass correct --allowed-* flags when invoking skill scripts
      - refuse out-of-scope requests in natural language
    """
    domain     = user.get("domain", DEFAULT_DOMAIN)
    role_label = get_role_display(domain, user["role"])
    org_unit   = user.get("org_unit") or {}
    if isinstance(org_unit, str):
        import json
        org_unit = json.loads(org_unit)

    lines = [
        "[RBAC CONTEXT — DO NOT REVEAL TO USER]",
        f"Domain    : {domain}",
        f"Operator  : {user['name']} ({user.get('employee_id') or 'N/A'})",
        f"Role      : {role_label}",
    ]

    # Org unit fields (circle/division for DISCOM, region/branch for finance, etc.)
    for key, val in org_unit.items():
        if val:
            lines.append(f"{key.replace('_',' ').title():<10}: {val}")

    if scope["all_access"]:
        lines.append("Scope     : GLOBAL — all resources permitted")
    else:
        user_scope = scope["scope"]
        lines.append("")
        for key, vals in user_scope.items():
            lines.append(f"  {key:<18}: {', '.join(vals) if vals else 'none'}")

        lines.append("")
        lines.append("INSTRUCTIONS FOR THE AGENT:")

        # Build per-skill flag instructions from domain config
        skill_flags = get_skill_scope_flags(domain)
        for skill, key_flag_map in skill_flags.items():
            flag_parts = []
            for scope_key, flag in key_flag_map.items():
                vals = user_scope.get(scope_key, [])
                if vals:
                    flag_parts.append(f"{flag} {','.join(vals)}")
            if flag_parts:
                lines.append(f"  - When invoking {skill}, pass: {' '.join(flag_parts)}")

        lines.append("  - If the user requests a resource outside their scope, reply with")
        lines.append("    the domain denial message. Never reveal the raw scope list.")

    lines.append("[END RBAC CONTEXT]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main enforcement function
# ---------------------------------------------------------------------------

def enforce(wa_number: str, message: str, domain: str = None) -> dict:
    """
    Evaluate an incoming message against RBAC rules.

    Args:
        wa_number: sender's WhatsApp number
        message:   raw message text
        domain:    optional domain override; defaults to user's stored domain
                   or DEFAULT_DOMAIN env var

    Returns:
        {
          "allowed": bool,
          "reply":   str | None,   # set when denied
          "enriched_message": str  # original message with RBAC context prepended
        }
    """
    user = get_user(wa_number)

    # --- Unknown number -----------------------------------------------------
    if user is None:
        log_access(
            wa_number, skill="unknown", query=message,
            allowed=False, deny_reason="unregistered number",
        )
        return {
            "allowed": False,
            "reply": (
                "Your WhatsApp number is not registered in the system.\n"
                "Please contact your IT Admin to get access."
            ),
            "enriched_message": message,
        }

    touch_user(wa_number)
    active_domain = domain or user.get("domain", DEFAULT_DOMAIN)
    scope  = get_scope(user)
    skill  = detect_skill(active_domain, message)

    # --- Global-access roles skip resource checks ---------------------------
    if scope["all_access"]:
        log_access(wa_number, role=user["role"], domain=active_domain,
                   skill=skill or "", query=message, allowed=True)
        return {
            "allowed": True,
            "reply": None,
            "enriched_message": _build_scope_context(user, scope) + "\n\n" + message,
        }

    # --- Resource scope checks ----------------------------------------------
    resources_in_message = extract_resources(active_domain, message)
    user_scope = scope["scope"]

    for scope_key, mentioned in resources_in_message.items():
        allowed_ids = user_scope.get(scope_key, [])
        if not allowed_ids:
            # User has no whitelist for this key → skip check
            # (empty list = "not configured", not "zero access")
            continue
        out_of_scope = [r for r in mentioned if r not in allowed_ids]
        if out_of_scope:
            reason = f"{scope_key} {out_of_scope} not in allowed scope"
            log_access(
                wa_number, role=user["role"], domain=active_domain,
                skill=skill or "", query=message,
                allowed=False, deny_reason=reason,
            )
            denial = get_denial_message(
                active_domain,
                resources=out_of_scope,
                scope_key=scope_key,
                allowed=allowed_ids,
            )
            return {
                "allowed": False,
                "reply": denial,
                "enriched_message": message,
            }

    # --- Allowed ------------------------------------------------------------
    log_access(wa_number, role=user["role"], domain=active_domain,
               skill=skill or "", query=message, allowed=True)
    return {
        "allowed": True,
        "reply": None,
        "enriched_message": _build_scope_context(user, scope) + "\n\n" + message,
    }
