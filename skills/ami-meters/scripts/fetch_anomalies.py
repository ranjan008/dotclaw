#!/usr/bin/env python3
"""
AMI Meter Anomalies Skill — fetch_anomalies.py
Fetches meter anomalies from the MDMS/AMI API, groups by DT cluster,
and prints a structured report with recommended field actions.
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

VALID_TYPES = {"tamper", "zero_read", "comm_failure"}

FIELD_ACTIONS = {
    "tamper": (
        "Dispatch field team for physical meter inspection and anti-tamper audit. "
        "Initiate FIR if bypass confirmed."
    ),
    "zero_read": (
        "Field inspection required — verify meter health, check for disconnection or "
        "display fault. Arrange meter replacement if faulty."
    ),
    "comm_failure": (
        "Check SIM/GPRS connectivity and meter communication module. "
        "Reset modem or replace communication unit if persistent."
    ),
    "mixed": (
        "Multiple anomaly types detected. Prioritise tamper events first, "
        "followed by zero-read verification, then communication restoration."
    ),
}


def fetch_anomalies(anomaly_type: str = None) -> list:
    url = f"{API_BASE}/mdms/meters/anomalies"
    params = {"type": anomaly_type} if anomaly_type else {}
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 401:
        print("ERROR: Unauthorized — check OT_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def get_action(types_in_cluster: set) -> str:
    if len(types_in_cluster) == 1:
        return FIELD_ACTIONS.get(next(iter(types_in_cluster)), FIELD_ACTIONS["mixed"])
    return FIELD_ACTIONS["mixed"]


def print_report(anomalies: list, type_filter: str = None) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    filter_label = type_filter.upper() if type_filter else "ALL"

    sep = "=" * 60
    div = "  " + chr(0x2500) * 54

    print(sep)
    print("  AMI METER ANOMALY REPORT")
    print(f"  Generated : {now_str} UTC")
    print(f"  Total Anomalies: {len(anomalies)}   Filter: {filter_label}")
    print(sep)

    if not anomalies:
        print("\n  No anomalies found matching the filter.\n")
        print(sep)
        return

    grouped = defaultdict(list)
    for a in anomalies:
        grouped[a.get("dt_id", "UNKNOWN")].append(a)

    type_counts: dict = defaultdict(int)

    for dt_id in sorted(grouped.keys()):
        cluster = grouped[dt_id]
        types_in_cluster = {a.get("anomaly_type", "") for a in cluster}

        for a in cluster:
            type_counts[a.get("anomaly_type", "unknown")] += 1

        print(f"\n  DT CLUSTER: {dt_id}  ({len(cluster)} anomal{'y' if len(cluster) == 1 else 'ies'})")
        print(div)
        print(f"  {'Meter ID':<12} {'Sector':<13} {'Type':<15} Days Silent")
        for a in cluster:
            print(
                f"  {a.get('meter_id', 'N/A'):<12} "
                f"{a.get('sector', 'N/A'):<13} "
                f"{a.get('anomaly_type', 'N/A').upper():<15} "
                f"{a.get('days_since_last_read', 0)}"
            )

        action = get_action(types_in_cluster)
        print()
        # Word-wrap the action at 54 chars
        words = action.split()
        line = "  Recommended Action: "
        for word in words:
            if len(line) + len(word) + 1 > 58:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line.rstrip())

    print()
    print(sep)
    print("  SUMMARY BY ANOMALY TYPE")
    print(div)
    for atype in sorted(type_counts.keys()):
        label = atype.upper().replace("_", " ")
        count = type_counts[atype]
        print(f"  {label:<14} : {count} meter{'s' if count != 1 else ''}")
    print(sep)


def main():
    parser = argparse.ArgumentParser(description="AMI Meter Anomaly Report")
    parser.add_argument(
        "--type",
        dest="anomaly_type",
        choices=sorted(VALID_TYPES),
        default=None,
        help="Filter by anomaly type (tamper, zero_read, comm_failure)",
    )
    args = parser.parse_args()

    anomalies = fetch_anomalies(anomaly_type=args.anomaly_type)
    print_report(anomalies, type_filter=args.anomaly_type)


if __name__ == "__main__":
    main()
