"""
rbac/seed_users.py — Seed the user registry with demo users covering all roles.

Run once:
    python rbac/seed_users.py
"""

from .db import init_db
from .user_registry import add_user

DEMO_USERS = [
    # -------------------------------------------------------------------------
    # Corporate / global access
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000001",
        name="Anil Sharma",
        role="cmd",
        employee_id="EMP-001",
        circle="",
        division="",
    ),
    dict(
        wa_number="+919000000002",
        name="Priya Mehta",
        role="director_ops",
        employee_id="EMP-002",
    ),
    dict(
        wa_number="+919000000003",
        name="Suresh Nair",
        role="mis_finance",
        employee_id="EMP-003",
    ),
    # -------------------------------------------------------------------------
    # Circle SE — Circle-North
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000010",
        name="Ramesh Pillai",
        role="circle_se",
        employee_id="EMP-010",
        circle="Circle-North",
        allowed_feeders=["FDR-001","FDR-002","FDR-003","FDR-004","FDR-005"],
        allowed_zones=["Zone-A","Zone-B"],
    ),
    # -------------------------------------------------------------------------
    # Division EE — Division-3 (subset of Circle-North)
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000020",
        name="Kavita Rao",
        role="division_ee",
        employee_id="EMP-020",
        circle="Circle-North",
        division="Division-3",
        allowed_feeders=["FDR-001","FDR-002","FDR-003"],
        allowed_zones=["Zone-A"],
        allowed_dts=["DT-001","DT-002"],
    ),
    # -------------------------------------------------------------------------
    # Sub-division AE
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000030",
        name="Mohan Das",
        role="sub_division_ae",
        employee_id="EMP-030",
        circle="Circle-North",
        division="Division-3",
        sub_division="SubDiv-3A",
        allowed_feeders=["FDR-001","FDR-002"],
        allowed_zones=["Zone-A"],
        allowed_dts=["DT-001"],
    ),
    # -------------------------------------------------------------------------
    # Junior Engineer — single feeder assignment
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000040",
        name="Raju Verma",
        role="junior_engineer",
        employee_id="EMP-040",
        circle="Circle-North",
        division="Division-3",
        sub_division="SubDiv-3A",
        allowed_feeders=["FDR-002"],
        allowed_zones=["Zone-A"],
        allowed_dts=["DT-001"],
    ),
    # -------------------------------------------------------------------------
    # Revenue Protection Officer
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000050",
        name="Deepa Krishnan",
        role="revenue_protection",
        employee_id="EMP-050",
        circle="Circle-North",
        division="Division-3",
        allowed_feeders=["FDR-001","FDR-002","FDR-003"],
        allowed_zones=["Zone-A"],
        allowed_dts=["DT-001","DT-002","DT-003"],
    ),
    # -------------------------------------------------------------------------
    # IT Admin
    # -------------------------------------------------------------------------
    dict(
        wa_number="+919000000099",
        name="IT Admin",
        role="it_admin",
        employee_id="EMP-099",
    ),
]


def seed() -> None:
    init_db()
    for u in DEMO_USERS:
        try:
            add_user(
                u["wa_number"],
                u["name"],
                u["role"],
                employee_id=u.get("employee_id", ""),
                circle=u.get("circle", ""),
                division=u.get("division", ""),
                sub_division=u.get("sub_division", ""),
                allowed_feeders=u.get("allowed_feeders", []),
                allowed_zones=u.get("allowed_zones", []),
                allowed_dts=u.get("allowed_dts", []),
                registered_by="seed",
            )
            print(f"  + {u['role']:<22}  {u['name']}  ({u['wa_number']})")
        except Exception as exc:
            print(f"  ! skipped {u['wa_number']}: {exc}")


if __name__ == "__main__":
    print("Seeding DotClaw RBAC user registry...")
    seed()
    print("Done.")
