"""
rbac/seed_users.py — Seed demo users for all three domains.

Run:
    python -m rbac.seed_users
    python -m rbac.seed_users --domain discom
    python -m rbac.seed_users --domain supplychain
    python -m rbac.seed_users --domain finance
"""

from __future__ import annotations

import argparse
import sys

from .db import init_db
from .user_registry import add_user

# ---------------------------------------------------------------------------
# DISCOM seed users
# ---------------------------------------------------------------------------
DISCOM_USERS = [
    dict(wa="+919000000001", name="Anil Sharma",    role="cmd",            emp="EMP-001"),
    dict(wa="+919000000002", name="Priya Mehta",    role="director_ops",   emp="EMP-002"),
    dict(wa="+919000000003", name="Suresh Nair",    role="mis_finance",    emp="EMP-003"),
    dict(
        wa="+919000000010", name="Ramesh Pillai", role="circle_se", emp="EMP-010",
        org_unit={"circle": "Circle-North"},
        scope={"feeders": ["FDR-001","FDR-002","FDR-003","FDR-004","FDR-005"],
               "zones":   ["Zone-A","Zone-B"]},
    ),
    dict(
        wa="+919000000020", name="Kavita Rao", role="division_ee", emp="EMP-020",
        org_unit={"circle": "Circle-North", "division": "Division-3"},
        scope={"feeders": ["FDR-001","FDR-002","FDR-003"],
               "zones":   ["Zone-A"],
               "dts":     ["DT-001","DT-002"]},
    ),
    dict(
        wa="+919000000030", name="Mohan Das", role="sub_division_ae", emp="EMP-030",
        org_unit={"circle": "Circle-North", "division": "Division-3",
                  "sub_division": "SubDiv-3A"},
        scope={"feeders": ["FDR-001","FDR-002"], "zones": ["Zone-A"], "dts": ["DT-001"]},
    ),
    dict(
        wa="+919000000040", name="Raju Verma", role="junior_engineer", emp="EMP-040",
        org_unit={"circle": "Circle-North", "division": "Division-3",
                  "sub_division": "SubDiv-3A"},
        scope={"feeders": ["FDR-002"], "zones": ["Zone-A"], "dts": ["DT-001"]},
    ),
    dict(
        wa="+919000000050", name="Deepa Krishnan", role="revenue_protection", emp="EMP-050",
        org_unit={"circle": "Circle-North", "division": "Division-3"},
        scope={"feeders": ["FDR-001","FDR-002","FDR-003"],
               "zones":   ["Zone-A"],
               "dts":     ["DT-001","DT-002","DT-003"]},
    ),
    dict(wa="+919000000099", name="IT Admin",       role="it_admin",       emp="EMP-099"),
]

# ---------------------------------------------------------------------------
# Supply chain seed users
# ---------------------------------------------------------------------------
SUPPLYCHAIN_USERS = [
    dict(wa="+919001000001", name="Vikram Khanna",  role="vp_operations",  emp="SC-001"),
    dict(wa="+919001000002", name="Anita Desai",    role="cfo",            emp="SC-002"),
    dict(
        wa="+919001000010", name="Rahul Gupta", role="regional_head", emp="SC-010",
        org_unit={"region": "North"},
        scope={"plants":     ["PLANT-DEL","PLANT-NCR"],
               "warehouses": ["WH-DEL-01","WH-DEL-02"],
               "vendors":    ["VND-0010","VND-0011","VND-0012"]},
    ),
    dict(
        wa="+919001000020", name="Sunita Patel", role="plant_manager", emp="SC-020",
        org_unit={"region": "North", "plant": "PLANT-DEL"},
        scope={"plants":     ["PLANT-DEL"],
               "warehouses": ["WH-DEL-01"],
               "vendors":    ["VND-0010","VND-0011"]},
    ),
    dict(
        wa="+919001000030", name="Arjun Singh", role="warehouse_officer", emp="SC-030",
        org_unit={"region": "North", "plant": "PLANT-DEL", "warehouse": "WH-DEL-01"},
        scope={"warehouses": ["WH-DEL-01"],
               "categories": ["CAT-RAW","CAT-PKG"]},
    ),
    dict(
        wa="+919001000040", name="Meena Roy", role="procurement_officer", emp="SC-040",
        org_unit={"region": "North", "plant": "PLANT-DEL"},
        scope={"vendors":    ["VND-0010","VND-0011"],
               "categories": ["CAT-RAW","CAT-ELEC"]},
    ),
    dict(wa="+919001000099", name="SC IT Admin", role="it_admin", emp="SC-099"),
]

# ---------------------------------------------------------------------------
# Finance seed users
# ---------------------------------------------------------------------------
FINANCE_USERS = [
    dict(wa="+919002000001", name="Sanjay Kapoor",  role="md",             emp="FIN-001"),
    dict(wa="+919002000002", name="Rekha Sharma",   role="cfo",            emp="FIN-002"),
    dict(wa="+919002000003", name="Vivek Iyer",     role="compliance_officer", emp="FIN-003"),
    dict(
        wa="+919002000010", name="Pooja Menon", role="regional_manager", emp="FIN-010",
        org_unit={"region": "West"},
        scope={"branches":     ["BR-MUM-001","BR-MUM-002","BR-PUN-001"],
               "cost_centers": ["CC-0101","CC-0102","CC-0103"]},
    ),
    dict(
        wa="+919002000020", name="Kiran Nair", role="branch_manager", emp="FIN-020",
        org_unit={"region": "West", "branch": "BR-MUM-001"},
        scope={"branches":     ["BR-MUM-001"],
               "cost_centers": ["CC-0101"],
               "products":     ["PROD-HL","PROD-PL","PROD-SB"]},
    ),
    dict(
        wa="+919002000030", name="Dinesh Rao", role="auditor", emp="FIN-030",
        org_unit={"region": "West"},
        scope={"branches":     ["BR-MUM-001","BR-MUM-002"],
               "cost_centers": ["CC-0101","CC-0102"]},
    ),
    dict(
        wa="+919002000040", name="Smita Joshi", role="teller", emp="FIN-040",
        org_unit={"region": "West", "branch": "BR-MUM-001"},
        scope={"branches": ["BR-MUM-001"]},
    ),
    dict(wa="+919002000099", name="Finance IT Admin", role="it_admin", emp="FIN-099"),
]

DOMAIN_SEEDS = {
    "discom":       DISCOM_USERS,
    "supplychain":  SUPPLYCHAIN_USERS,
    "finance":      FINANCE_USERS,
}


def seed(domain: str = None) -> None:
    init_db()
    targets = {domain: DOMAIN_SEEDS[domain]} if domain else DOMAIN_SEEDS
    for dom, users in targets.items():
        print(f"\n  [{dom.upper()}]")
        for u in users:
            try:
                add_user(
                    u["wa"], u["name"], u["role"], dom,
                    employee_id=u.get("emp", ""),
                    org_unit=u.get("org_unit", {}),
                    scope=u.get("scope", {}),
                    registered_by="seed",
                )
                print(f"    + {u['role']:<25} {u['name']}  ({u['wa']})")
            except Exception as exc:
                print(f"    ! skipped {u['wa']}: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=list(DOMAIN_SEEDS.keys()),
                        help="Seed only a specific domain")
    args = parser.parse_args()

    print("Seeding DotClaw RBAC user registry...")
    seed(domain=args.domain)
    print("\nDone.")
