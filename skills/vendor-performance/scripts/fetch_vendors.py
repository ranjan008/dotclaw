#!/usr/bin/env python3
"""Supply Chain Skill — fetch_vendors.py: Vendor performance scorecard."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

RATING_ICON = {"A": "✅ Excellent", "B": "👍 Good", "C": "⚠️ Average", "D": "🚨 Poor — PIP"}


def fetch_vendors(vendor=None):
    params = {"vendor": vendor} if vendor else {}
    r = requests.get(f"{API_BASE}/sc/vendors/performance",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    if r.status_code == 404: print(f"ERROR: Vendor {vendor} not found.", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(vendors):
    sep = "=" * 60
    div = "  " + "─" * 54
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(sep)
    print("  VENDOR PERFORMANCE SCORECARD")
    print(f"  Generated : {now}")
    print(sep)

    for v in vendors:
        rating_str = RATING_ICON.get(v.get("rating", ""), v.get("rating", "?"))
        print(f"\n  {v['vendor_id']} — {v['name']}")
        print(div)
        print(f"  Category   : {v.get('category')}")
        print(f"  Orders     : {v.get('orders_total')} total / {v.get('orders_on_time')} on-time")
        print(f"  OTD %      : {v.get('otd_percent')}%")
        print(f"  Quality    : {v.get('quality_score')} / 5.0")
        print(f"  Avg Delay  : {v.get('avg_delay_days')} days")
        print(f"  Rating     : {v.get('rating')}  —  {rating_str}")
        print(f"  Remarks    : {v.get('remarks', '-')}")

    print()
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vendor",               default=None)
    p.add_argument("--allowed-vendors",      default="", help="RBAC scope")
    p.add_argument("--allowed-categories",   default="", help="RBAC scope")
    args = p.parse_args()

    vendors = fetch_vendors(vendor=args.vendor)

    allowed_vendors = [x.strip().upper() for x in args.allowed_vendors.split(",") if x.strip()]
    if allowed_vendors:
        vendors = [v for v in vendors if v.get("vendor_id", "").upper() in allowed_vendors]

    allowed_cats = [x.strip().upper() for x in args.allowed_categories.split(",") if x.strip()]
    if allowed_cats:
        vendors = [v for v in vendors if v.get("category", "").upper() in allowed_cats]

    print_report(vendors)


if __name__ == "__main__":
    main()
