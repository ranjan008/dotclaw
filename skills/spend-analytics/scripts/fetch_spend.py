#!/usr/bin/env python3
"""Supply Chain Skill — fetch_spend.py: Procurement spend analytics."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_spend(plant=None, category=None):
    params = {}
    if plant:    params["plant"]    = plant
    if category: params["category"] = category
    r = requests.get(f"{API_BASE}/sc/spend",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(rows):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    total_budget = sum(r["budget_lakh"] for r in rows)
    total_actual = sum(r["actual_lakh"] for r in rows)
    net_variance = total_budget - total_actual
    overruns = [r for r in rows if r["variance_lakh"] < 0]

    print(sep)
    print("  PROCUREMENT SPEND ANALYTICS")
    print(f"  Generated : {now}")
    print(sep)
    print()
    print(f"  {'Plant':<12} {'Category':<12} {'Budget(L)':>10} {'Actual(L)':>10} {'Variance':>10}  POs")
    print("  " + "─" * 54)
    for r in rows:
        v = r["variance_lakh"]
        var_str = f"+{v:.1f} ✅" if v >= 0 else f"{v:.1f} 🚨"
        print(f"  {r['plant']:<12} {r['category']:<12} {r['budget_lakh']:>10.1f} "
              f"{r['actual_lakh']:>10.1f} {var_str:>12}  {r['po_count']}")

    print()
    print("  " + "─" * 54)
    var_icon = "✅" if net_variance >= 0 else "🚨"
    print(f"  {'Total':<12} {'':12} {total_budget:>10.1f} {total_actual:>10.1f} "
          f"  {net_variance:+.1f} {var_icon}")
    print()
    if overruns:
        print(f"  ⚠️  {len(overruns)} category(ies) are over budget:")
        for r in overruns:
            print(f"     🚨 {r['plant']} / {r['category']} over by ₹{abs(r['variance_lakh']):.1f}L")
    else:
        print("  All categories within budget. ✅")
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plant",              default=None)
    p.add_argument("--category",           default=None)
    p.add_argument("--allowed-plants",     default="", help="RBAC scope")
    p.add_argument("--allowed-categories", default="", help="RBAC scope")
    args = p.parse_args()

    rows = fetch_spend(plant=args.plant, category=args.category)

    allowed_plants = [x.strip().upper() for x in args.allowed_plants.split(",") if x.strip()]
    if allowed_plants:
        rows = [r for r in rows if r["plant"].upper() in allowed_plants]

    allowed_cats = [x.strip().upper() for x in args.allowed_categories.split(",") if x.strip()]
    if allowed_cats:
        rows = [r for r in rows if r["category"].upper() in allowed_cats]

    print_report(rows)


if __name__ == "__main__":
    main()
