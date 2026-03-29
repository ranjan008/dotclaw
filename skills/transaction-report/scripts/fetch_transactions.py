#!/usr/bin/env python3
"""Finance Skill — fetch_transactions.py: Daily transaction report by branch."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_transactions(branch=None, days=7):
    params = {"days": days}
    if branch: params["branch"] = branch
    r = requests.get(f"{API_BASE}/fin/transactions",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(rows, branch_filter=None, days=7):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = branch_filter or "ALL BRANCHES"

    print(sep)
    print(f"  TRANSACTION REPORT — {title}  (last {days} days)")
    print(f"  Generated : {now}")
    print(sep)
    print(f"\n  {'Date':<12} {'Credits':>8} {'Debits':>8} {'Volume(Cr)':>11} {'UPI':>6} {'NEFT':>6} {'Cash':>6}")
    print("  " + "─" * 54)

    total_cr = total_dr = total_vol = 0
    for r in rows:
        print(f"  {r['date']:<12} {r['credit_count']:>8,} {r['debit_count']:>8,} "
              f"{r['total_volume_cr']:>11.1f} {r['upi_count']:>6,} "
              f"{r['neft_rtgs_count']:>6,} {r['cash_count']:>6,}")
        total_cr  += r["credit_count"]
        total_dr  += r["debit_count"]
        total_vol += r["total_volume_cr"]

    print("  " + "─" * 54)
    print(f"  {'Total':<12} {total_cr:>8,} {total_dr:>8,} {total_vol:>11.1f}")
    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",           default=None)
    p.add_argument("--days",             type=int, default=7)
    p.add_argument("--allowed-branches", default="", help="RBAC scope")
    args = p.parse_args()

    rows = fetch_transactions(branch=args.branch, days=args.days)

    allowed = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed:
        rows = [r for r in rows if r["branch"].upper() in allowed]

    print_report(rows, branch_filter=args.branch, days=args.days)


if __name__ == "__main__":
    main()
