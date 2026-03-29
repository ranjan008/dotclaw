#!/usr/bin/env python3
"""Supply Chain Skill — fetch_deliveries.py: Shipment tracking from SC API."""

import argparse, os, sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_deliveries(plant=None, vendor=None):
    params = {}
    if plant:  params["plant"]  = plant
    if vendor: params["vendor"] = vendor
    r = requests.get(f"{API_BASE}/sc/deliveries",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(shipments):
    sep = "=" * 60
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    delayed = [s for s in shipments if s["delay_days"] > 0]

    print(sep)
    print("  DELIVERY TRACKING REPORT")
    print(f"  Generated : {now}   Shipments: {len(shipments)}")
    print(sep)

    if not shipments:
        print("\n  No active shipments.\n")
        print(sep)
        return

    for idx, s in enumerate(shipments, 1):
        delay = s.get("delay_days", 0)
        if s["status"] == "delivered":
            status_str = f"DELIVERED {abs(delay)} day(s) early" if delay < 0 else "DELIVERED on time"
        elif delay > 0:
            status_str = f"DELAYED (+{delay} day(s))  ⚠️"
        else:
            status_str = f"{s['status'].upper().replace('_',' ')} (on schedule)"

        print(f"\n  [{idx}] {s['shipment_id']}  →  {s['destination']}")
        print(f"      PO      : {s['po_id']}   Vendor : {s['vendor']}")
        print(f"      From    : {s['origin']}   ETA    : {s['eta']}")
        print(f"      Status  : {status_str}")
        print(f"      Vehicle : {s['vehicle']}   E-Way  : {s['eway_bill']}")

    print()
    if delayed:
        print(f"  ⚠️  {len(delayed)} delayed shipment(s) — immediate follow-up advised.")
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plant",              default=None)
    p.add_argument("--vendor",             default=None)
    p.add_argument("--allowed-plants",     default="", help="RBAC scope")
    p.add_argument("--allowed-warehouses", default="", help="RBAC scope")
    args = p.parse_args()

    shipments = fetch_deliveries(plant=args.plant, vendor=args.vendor)

    allowed_plants = [x.strip().upper() for x in args.allowed_plants.split(",") if x.strip()]
    if allowed_plants:
        shipments = [s for s in shipments if s["destination"].upper() in allowed_plants]

    print_report(shipments)


if __name__ == "__main__":
    main()
