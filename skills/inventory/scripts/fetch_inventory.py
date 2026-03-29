#!/usr/bin/env python3
"""Supply Chain Skill — fetch_inventory.py: Stock levels from SC API."""

import argparse, os, sys
from collections import defaultdict
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
load_dotenv(os.path.join(_root, ".env"))

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

STATUS_ICON = {"ok": "OK", "low": "LOW ⚠️", "critical": "CRITICAL 🚨"}


def fetch_inventory(plant=None, warehouse=None):
    params = {}
    if plant:     params["plant"]     = plant
    if warehouse: params["warehouse"] = warehouse
    r = requests.get(f"{API_BASE}/sc/inventory",
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     params=params, timeout=10)
    if r.status_code == 401: print("ERROR: Unauthorized", file=sys.stderr); sys.exit(1)
    r.raise_for_status()
    return r.json()


def print_report(items, plant_filter=None):
    sep = "=" * 60
    div = "  " + "─" * 54
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = f"PLANT: {plant_filter}" if plant_filter else "ALL PLANTS"

    critical = [i for i in items if i["status"] == "critical"]
    low      = [i for i in items if i["status"] == "low"]

    print(sep)
    print(f"  INVENTORY REPORT — {title}")
    print(f"  Generated : {now}   Items: {len(items)}")
    print(sep)

    grouped = defaultdict(list)
    for i in items:
        grouped[i["plant"]].append(i)

    for plant, stock in sorted(grouped.items()):
        print(f"\n  {plant}")
        print(div)
        print(f"  {'SKU':<14} {'Description':<22} {'WH':<12} {'On Hand':>8} {'Unit':<5} Status")
        for i in stock:
            print(f"  {i['sku']:<14} {i['description']:<22} {i['warehouse']:<12} "
                  f"{i['on_hand']:>8,} {i['unit']:<5} {STATUS_ICON.get(i['status'], i['status'])}")

    print()
    if critical or low:
        print(f"  ⚠️  {len(critical)} CRITICAL + {len(low)} LOW items require attention.")
        for i in critical:
            print(f"     🚨 {i['sku']} — {i['description']} ({i['on_hand']} {i['unit']} left, "
                  f"reorder at {i['reorder_level']})")
    else:
        print("  All stock levels are healthy.")
    print(sep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plant",              default=None)
    p.add_argument("--warehouse",          default=None)
    p.add_argument("--allowed-plants",     default="", help="RBAC scope")
    p.add_argument("--allowed-warehouses", default="", help="RBAC scope")
    args = p.parse_args()

    items = fetch_inventory(plant=args.plant, warehouse=args.warehouse)

    allowed_plants = [x.strip().upper() for x in args.allowed_plants.split(",") if x.strip()]
    if allowed_plants:
        items = [i for i in items if i["plant"].upper() in allowed_plants]

    allowed_wh = [x.strip().upper() for x in args.allowed_warehouses.split(",") if x.strip()]
    if allowed_wh:
        items = [i for i in items if i["warehouse"].upper() in allowed_wh]

    print_report(items, plant_filter=args.plant)


if __name__ == "__main__":
    main()
