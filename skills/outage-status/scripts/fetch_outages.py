#!/usr/bin/env python3
"""
Outage Status Skill — fetch_outages.py
Retrieves active outages from the OMS API and prints a formatted zone-grouped report.
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"))

API_BASE = os.getenv("OT_API_BASE", "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

CREW_LABELS = {
    "on_site":         "On Site",
    "dispatched":      "Dispatched",
    "work_in_progress":"Work in Progress",
    "pending":         "Pending Dispatch",
}


def fetch_outages(zone: str = None) -> list:
    url = f"{API_BASE}/oms/outages"
    params = {"zone": zone} if zone else {}
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 401:
        print("ERROR: Unauthorized — check OT_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def parse_duration(start_iso: str) -> str:
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - start
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m"
    except Exception:
        return "unknown"


def format_start(start_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return start_iso


def print_report(outages: list, zone_filter: str = None) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    total_consumers = sum(o.get("consumers_affected", 0) for o in outages)

    sep = "=" * 60
    print(sep)
    print("  OMS — ACTIVE OUTAGE REPORT")
    print(f"  Generated : {now_str} UTC")
    if zone_filter:
        print(f"  Zone Filter: {zone_filter}")
    print(f"  Total Outages: {len(outages)}  |  Total Consumers Affected: {total_consumers:,}")
    print(sep)

    if not outages:
        print("\n  No active outages found.\n")
        print(sep)
        return

    grouped = defaultdict(list)
    for o in outages:
        grouped[o.get("zone", "Unknown")].append(o)

    for zone, zone_outages in sorted(grouped.items()):
        print(f"\n  ZONE: {zone}  ({len(zone_outages)} outage{'s' if len(zone_outages) > 1 else ''})")
        print("  " + chr(0x2500) * 54)
        for idx, o in enumerate(zone_outages, 1):
            feeder      = o.get("feeder_id", "N/A")
            otype       = o.get("outage_type", "unknown").upper()
            start_str   = format_start(o.get("start_time", ""))
            duration    = parse_duration(o.get("start_time", ""))
            consumers   = o.get("consumers_affected", 0)
            crew        = CREW_LABELS.get(o.get("crew_status", ""), o.get("crew_status", "N/A"))
            desc        = o.get("fault_description", "")

            print(f"  [{idx}] Feeder   : {feeder}")
            print(f"      Type     : {otype}")
            print(f"      Started  : {start_str}  ({duration} ago)")
            print(f"      Consumers: {consumers:,}")
            print(f"      Crew     : {crew}")
            if desc:
                print(f"      Note     : {desc}")
            if idx < len(zone_outages):
                print()

    print()
    print(sep)


def main():
    parser = argparse.ArgumentParser(description="Fetch active outages from OMS")
    parser.add_argument("--zone", help="Filter by zone (e.g. Zone-A)", default=None)
    parser.add_argument(
        "--allowed-zones",
        default="",
        help="Comma-separated whitelist of permitted zones (RBAC scope). "
             "Empty means no restriction.",
    )
    parser.add_argument(
        "--allowed-feeders",
        default="",
        help="Comma-separated whitelist of permitted feeder IDs (RBAC scope).",
    )
    args = parser.parse_args()

    outages = fetch_outages(zone=args.zone)

    # RBAC scope filter — silently drop rows outside the user's allowed scope
    allowed_zones   = [z.strip() for z in args.allowed_zones.split(",")   if z.strip()]
    allowed_feeders = [f.strip().upper() for f in args.allowed_feeders.split(",") if f.strip()]

    if allowed_zones:
        outages = [o for o in outages if o.get("zone", "") in allowed_zones]
    if allowed_feeders:
        outages = [o for o in outages if o.get("feeder_id", "").upper() in allowed_feeders]

    print_report(outages, zone_filter=args.zone)


if __name__ == "__main__":
    main()
