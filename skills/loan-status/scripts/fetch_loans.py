#!/usr/bin/env python3
"""Finance Skill — fetch_loans.py: Loan book and NPA status by branch/product."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_loans(branch=None, product=None):
    params = {}
    if branch:  params["branch"]  = branch
    if product: params["product"] = product
    r = requests.get(f"{API_BASE}/fin/loans",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(loans, branch_filter=None):
    sep = "=" * 60
    div = "  " + "─" * 54
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = branch_filter or "ALL BRANCHES"

    total_os = sum(l["outstanding_cr"] for l in loans)
    total_npa = sum(l["npa_cr"] for l in loans)
    total_npa_pct = (total_npa / total_os * 100) if total_os else 0

    print(sep)
    print(f"  LOAN BOOK STATUS — {title}")
    print(f"  Generated : {now}")
    print(sep)
    print(f"\n  {'Product':<18} {'Accounts':>9} {'O/S (Cr)':>10} {'NPA (Cr)':>10} "
          f"{'NPA%':>7}  EMI Delay")
    print(div)

    for l in loans:
        emi_flag = " ⚠️" if l["avg_emi_delay_days"] > 3 else ""
        npa_flag = " 🚨" if l["npa_pct"] > 2.5 else ""
        print(f"  {l['name']:<18} {l['accounts']:>9,} {l['outstanding_cr']:>10.1f} "
              f"{l['npa_cr']:>10.1f} {l['npa_pct']:>6.2f}%{npa_flag}  "
              f"{l['avg_emi_delay_days']:.1f} days{emi_flag}")

    print(div)
    npa_total_flag = " 🚨" if total_npa_pct > 2.5 else ""
    print(f"  {'TOTAL':<18} {'':>9} {total_os:>10.1f} {total_npa:>10.1f} "
          f"{total_npa_pct:>6.2f}%{npa_total_flag}")
    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--branch",            default=None)
    p.add_argument("--product",           default=None)
    p.add_argument("--allowed-branches",  default="", help="RBAC scope")
    p.add_argument("--allowed-products",  default="", help="RBAC scope")
    args = p.parse_args()

    loans = fetch_loans(branch=args.branch, product=args.product)

    allowed_br = [x.strip().upper() for x in args.allowed_branches.split(",") if x.strip()]
    if allowed_br:
        loans = [l for l in loans if l.get("branch", args.branch or "").upper() in allowed_br]

    allowed_pr = [x.strip().upper() for x in args.allowed_products.split(",") if x.strip()]
    if allowed_pr:
        loans = [l for l in loans if l["product"].upper() in allowed_pr]

    print_report(loans, branch_filter=args.branch)


if __name__ == "__main__":
    main()
