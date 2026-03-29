#!/usr/bin/env python3
"""Finance Skill — fetch_accounts.py: Branch account summary from core banking API."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_accounts(branch=None):
    params = {"branch": branch} if branch else {}
    r = requests.get(f"{API_BASE}/fin/accounts/summary",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    if r.status_code == 404: print(f"ERROR: Branch {branch} not found.", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(branches):
    sep = "=" * 60
    div = "  " + "─" * 54
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(sep)
    print("  ACCOUNT SUMMARY")
    print(f"  Generated : {now}")
    print(sep)

    for b in branches:
        npa_flag = " 🚨" if b["npa_percent"] > 2.5 else (" ⚠️" if b["npa_percent"] > 2.0 else "")
        print(f"\n  {b['branch_id']} — {b['branch_name']}  ({b.get('region','')})")
        print(div)
        print(f"  CASA Accounts  : {b['casa_accounts']:,}   Balance : ₹{b['casa_balance_cr']:.1f} Cr")
        print(f"  FD Accounts    : {b['fd_accounts']:,}   Balance : ₹{b['fd_balance_cr']:.1f} Cr")
        print(f"  Loan Accounts  : {b['loan_accounts']:,}   O/S     : ₹{b['loan_outstanding_cr']:.1f} Cr")
        print(f"  NPA Accounts   : {b['npa_accounts']:,}   Amount  : ₹{b['npa_cr']:.1f} Cr  "
              f"({b['npa_percent']:.2f}%){npa_flag}")
        print(f"  CASA Ratio     : {b['casa_ratio']:.1f}%")

    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",           default=None)
    p.add_argument("--allowed-branches", default="", help="RBAC scope")
    args = p.parse_args()

    branches = fetch_accounts(branch=args.branch)

    allowed = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed:
        branches = [b for b in branches if b["branch_id"].upper() in allowed]

    print_report(branches)


if __name__ == "__main__":
    main()
