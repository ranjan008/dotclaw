"""
rbac/domain_loader.py — Load and query domain configuration from YAML files.

Each domain has a YAML file in domain_config/<domain>.yaml that defines:
  - roles and their global-access flag
  - org_unit_keys (hierarchy, e.g. circle/division for DISCOM)
  - scope_keys (resource types, e.g. feeders/zones for DISCOM)
  - resource_patterns (regex to extract resource IDs from message text)
  - skill_patterns (regex to detect which skill a message targets)
  - skill_scope_flags (CLI flags to pass to skill scripts)
  - denial_message template

All config is cached after first load (lru_cache).
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Optional

import yaml

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "domain_config")


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=16)
def load(domain: str) -> dict:
    """
    Load and cache domain config from domain_config/<domain>.yaml.
    Raises ValueError if the file does not exist.
    """
    path = os.path.abspath(os.path.join(_CONFIG_DIR, f"{domain}.yaml"))
    if not os.path.exists(path):
        available = _available_domains()
        raise ValueError(
            f"No config found for domain '{domain}'. "
            f"Available: {available}. Expected path: {path}"
        )
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def _available_domains() -> list[str]:
    if not os.path.isdir(_CONFIG_DIR):
        return []
    return [f[:-5] for f in os.listdir(_CONFIG_DIR) if f.endswith(".yaml")]


# --------------------------------------------------------------------------- #
# Role helpers
# --------------------------------------------------------------------------- #

def get_valid_roles(domain: str) -> set[str]:
    return set(load(domain)["roles"].keys())


def get_global_roles(domain: str) -> set[str]:
    return {
        role for role, cfg in load(domain)["roles"].items()
        if cfg.get("global_access", False)
    }


def get_role_display(domain: str, role: str) -> str:
    return load(domain)["roles"].get(role, {}).get("display", role)


# --------------------------------------------------------------------------- #
# Scope / org-unit key helpers
# --------------------------------------------------------------------------- #

def get_scope_keys(domain: str) -> list[str]:
    return load(domain).get("scope_keys", [])


def get_org_unit_keys(domain: str) -> list[str]:
    return load(domain).get("org_unit_keys", [])


# --------------------------------------------------------------------------- #
# Skill detection
# --------------------------------------------------------------------------- #

def detect_skill(domain: str, text: str) -> Optional[str]:
    """Return the first skill whose patterns match the message text."""
    lower = text.lower()
    for skill, patterns in load(domain).get("skill_patterns", {}).items():
        for pattern in patterns:
            if re.search(pattern, lower):
                return skill
    return None


# --------------------------------------------------------------------------- #
# Resource extraction
# --------------------------------------------------------------------------- #

def extract_resources(domain: str, text: str) -> dict[str, list[str]]:
    """
    Extract resource IDs from message text using domain resource_patterns.

    Returns e.g. {"feeders": ["FDR-001", "FDR-009"]} for DISCOM,
                 {"plants": ["PLANT-MUM"]} for supply chain.
    """
    result: dict[str, list[str]] = {}
    for key, pattern in load(domain).get("resource_patterns", {}).items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            result[key] = [m.upper() for m in matches]
    return result


# --------------------------------------------------------------------------- #
# Scope context builder helpers
# --------------------------------------------------------------------------- #

def get_skill_scope_flags(domain: str) -> dict[str, dict[str, str]]:
    """
    Returns mapping: skill → {scope_key → CLI flag}.
    Used by middleware to build per-skill flag instructions for the agent.
    """
    return load(domain).get("skill_scope_flags", {})


def get_denial_message(
    domain: str,
    *,
    resources: list[str],
    scope_key: str,
    allowed: list[str],
) -> str:
    template = load(domain).get(
        "denial_message",
        "You are not authorised to view: {resources}. Allowed {scope_key}: {allowed}.",
    )
    return (
        template
        .replace("{resources}", ", ".join(resources))
        .replace("{scope_key}", scope_key)
        .replace("{allowed}", ", ".join(allowed) or "none")
        .strip()
    )
