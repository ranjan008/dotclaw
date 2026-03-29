#!/usr/bin/env python3
"""Finance Skill — fetch_branch_perf.py: Branch performance vs targets."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_branch_perf(branch=None):
    params = {"branch": branch} if branch else {}
    r = requests.get(f"{API_BASE}/fin/branches/performance",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    if r.status_code == 404: print(f"ERROR: Branch {branch} not found.", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def _pct_flag(pct):
    if pct >= 100: return "✅"
    if pct >= 95:  return "✅"
    if pct >= 85:  return "⚠️"
    return "🚨"


def print_report(branches):
    sep = "=" * 60
    div = "  " + "─" * 54
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(sep)
    print("  BRANCH PERFORMANCE DASHBOARD")
    print(f"  Generated : {now}")
    print(sep)

    for b in branches:
        npa_ok = b["npa_actual_pct"] <= b["npa_target_pct"]
        below_95 = sum([
            b["casa_pct"] < 95, b["loan_pct"] < 95,
            b["fee_pct"] < 95,
            (b["new_accounts_actual"] / b["new_accounts_target"] * 100) < 95
        ])

        print(f"\n  {b['branch_id']} — {b.get('branch_name','')}")
        print(div)
        print(f"  {'Metric':<26} {'Target':>10} {'Actual':>10} {'Ach%':>7}  ")
        print(div)
        print(f"  {'CASA Balance (Cr)':<26} {b['casa_target']:>10.1f} {b['casa_actual']:>10.1f} "
              f"{b['casa_pct']:>6.1f}%  {_pct_flag(b['casa_pct'])}")
        print(f"  {'Loan O/S (Cr)':<26} {b['loan_target']:>10.1f} {b['loan_actual']:>10.1f} "
              f"{b['loan_pct']:>6.1f}%  {_pct_flag(b['loan_pct'])}")
        npa_str = "✅ Within limit" if npa_ok else "🚨 EXCEEDED"
        print(f"  {'NPA %':<26} {b['npa_target_pct']:>9.2f}% {b['npa_actual_pct']:>9.2f}%  {npa_str}")
        print(f"  {'Fee Income (Cr)':<26} {b['fee_income_target_cr']:>10.1f} "
              f"{b['fee_income_actual_cr']:>10.1f} {b['fee_pct']:>6.1f}%  {_pct_flag(b['fee_pct'])}")
        new_acc_pct = b["new_accounts_actual"] / b["new_accounts_target"] * 100
        print(f"  {'New Accounts':<26} {b['new_accounts_target']:>10,} "
              f"{b['new_accounts_actual']:>10,} {new_acc_pct:>6.1f}%  {_pct_flag(new_acc_pct)}")
        print()
        if below_95 == 0:
            print(f"  Overall: All metrics on track. ✅")
        else:
            print(f"  Overall: {below_95} metric(s) below 95% — management attention needed.")

    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",           default=None)
    p.add_argument("--allowed-branches", default="", help="RBAC scope")
    args = p.parse_args()

    branches = fetch_branch_perf(branch=args.branch)

    allowed = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed:
        branches = [b for b in branches if b["branch_id"].upper() in allowed]

    print_report(branches)


if __name__ == "__main__":
    main()
