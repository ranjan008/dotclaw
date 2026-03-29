#!/usr/bin/env python3
"""Finance Skill — fetch_compliance.py: Open compliance flags by branch."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

SEV_ICON = {"high": "🚨 HIGH  ", "medium": "⚠️  MEDIUM", "low": "ℹ️  LOW   "}


def fetch_compliance(branch=None, severity=None):
    params = {}
    if branch:   params["branch"]   = branch
    if severity: params["severity"] = severity
    r = requests.get(f"{API_BASE}/fin/compliance",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(flags, branch_filter=None):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = branch_filter or "ALL BRANCHES"
    high = [f for f in flags if f["severity"] == "high"]

    print(sep)
    print(f"  COMPLIANCE FLAGS — {title}")
    print(f"  Generated : {now}   Total: {len(flags)}")
    print(sep)

    if not flags:
        print("\n  No open compliance flags.\n")
        print(sep)
        return

    for f in sorted(flags, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 9)):
        icon = SEV_ICON.get(f["severity"], f["severity"].upper())
        print(f"\n  {icon}  {f['flag_id']}  {f['type']:<20}  {f.get('account','N/A')}")
        print(f"             Due: {f['due_date']}   {f['remarks']}")

    print()
    if high:
        print(f"  ⚠️  {len(high)} HIGH severity item(s) require immediate action.")
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",           default=None)
    p.add_argument("--severity",         choices=["high","medium","low"], default=None)
    p.add_argument("--allowed-branches", default="", help="RBAC scope")
    args = p.parse_args()

    flags = fetch_compliance(branch=args.branch, severity=args.severity)

    allowed = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed:
        flags = [f for f in flags if args.branch and args.branch.upper() in allowed]

    print_report(flags, branch_filter=args.branch)


if __name__ == "__main__":
    main()
