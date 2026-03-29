#!/usr/bin/env python3
"""Supply Chain Skill — fetch_po.py: Purchase order status from SC API."""

import argparse, os, sys
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

STATUS_ICON = {"delivered": "✅", "in_transit": "🚚", "delayed": "⚠️ DELAYED",
               "pending_approval": "⏳ PENDING APPROVAL", "approved": "✅ APPROVED"}


def fetch_po(po_id):
    r = requests.get(f"{API_BASE}/sc/orders/{po_id}",
                     headers={"Authorization": f"Bearer {API_TOKEN}"}, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    if r.status_code == 404: print(f"ERROR: {po_id} not found.", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(d):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_str = STATUS_ICON.get(d.get("status", ""), d.get("status", "").upper())
    delay = d.get("delay_days", 0)
    delay_str = (f"+{delay} day(s)" if delay > 0 else
                 f"{abs(delay)} day(s) early" if delay < 0 else "On schedule")

    print(sep)
    print(f"  PO STATUS — {d['po_id']}")
    print(f"  Retrieved : {now}")
    print(sep)
    print(f"  Vendor     : {d.get('vendor')} — {d.get('vendor_name')}")
    print(f"  Plant      : {d.get('plant')}")
    print(f"  Category   : {d.get('category')}")
    print(f"  Items      : {d.get('items')}")
    print(f"  Value      : ₹{d.get('value_lakh')} Lakh")
    print(f"  Status     : {status_str}")
    print(f"  Ordered    : {d.get('ordered_date')}")
    print(f"  Expected   : {d.get('expected_delivery')}")
    if d.get("actual_delivery"):
        print(f"  Delivered  : {d['actual_delivery']}")
    print(f"  Delay      : {delay_str}")
    print(f"  Remarks    : {d.get('remarks', '-')}")
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--po", required=True, help="PO number e.g. PO-1002")
    p.add_argument("--allowed-plants",  default="", help="RBAC scope: permitted plants")
    p.add_argument("--allowed-vendors", default="", help="RBAC scope: permitted vendors")
    args = p.parse_args()

    po_id = args.po.upper()
    data  = fetch_po(po_id)

    # RBAC scope check
    allowed_plants = [x.strip().upper() for x in args.allowed_plants.split(",") if x.strip()]
    if allowed_plants and data.get("plant", "").upper() not in allowed_plants:
        print(f"ACCESS DENIED: Plant {data.get('plant')} outside your scope.", file=sys.stderr)
        sys.exit(2)
    allowed_vendors = [x.strip().upper() for x in args.allowed_vendors.split(",") if x.strip()]
    if allowed_vendors and data.get("vendor", "").upper() not in allowed_vendors:
        print(f"ACCESS DENIED: Vendor {data.get('vendor')} outside your scope.", file=sys.stderr)
        sys.exit(2)

    print_report(data)


if __name__ == "__main__":
    main()
