#!/usr/bin/env python3
"""Finance Skill — fetch_pl.py: Branch P&L report."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_pl(branch=None, days=7):
    params = {"days": days}
    if branch: params["branch"] = branch
    r = requests.get(f"{API_BASE}/fin/pl",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(rows, branch_filter=None, days=7):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = branch_filter or "ALL BRANCHES"

    t_rev = sum(r["revenue_cr"] for r in rows)
    t_exp = sum(r["expenses_cr"] for r in rows)
    t_nim = sum(r["nim_cr"] for r in rows)
    t_pat = sum(r["pat_cr"] for r in rows)

    print(sep)
    print(f"  P&L REPORT — {title}  (last {days} days)")
    print(f"  Generated : {now}")
    print(sep)
    print(f"\n  {'Date':<12} {'Revenue':>9} {'Expenses':>9} {'NIM':>7} {'PAT':>7} {'ROA%':>7}")
    print("  " + "─" * 54)
    for r in rows:
        print(f"  {r['date']:<12} {r['revenue_cr']:>9.1f} {r['expenses_cr']:>9.1f} "
              f"{r['nim_cr']:>7.1f} {r['pat_cr']:>7.1f} {r['roa_percent']:>6.2f}%")
    print("  " + "─" * 54)
    avg_roa = (t_pat / t_rev * 100 / days) if t_rev else 0
    print(f"  {'7-Day Total':<12} {t_rev:>9.1f} {t_exp:>9.1f} {t_nim:>7.1f} {t_pat:>7.1f} "
          f"{avg_roa:>6.2f}%")
    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",              default=None)
    p.add_argument("--days",                type=int, default=7)
    p.add_argument("--allowed-branches",    default="", help="RBAC scope")
    p.add_argument("--allowed-cost-centers",default="", help="RBAC scope")
    args = p.parse_args()

    rows = fetch_pl(branch=args.branch, days=args.days)

    allowed = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed:
        rows = [r for r in rows if r["branch"].upper() in allowed]

    print_report(rows, branch_filter=args.branch, days=args.days)


if __name__ == "__main__":
    main()
