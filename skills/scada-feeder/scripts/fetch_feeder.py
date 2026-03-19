#!/usr/bin/env python3
"""
SCADA Feeder Skill — fetch_feeder.py
Fetches live telemetry for a given feeder from the Mock OT API.
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

# Load .env from the project root (two levels above this script)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"))

API_BASE = os.getenv("OT_API_BASE", "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

CAPACITY_WARNING_THRESHOLD = 85.0

STATUS_LABELS = {
    "normal":   "NORMAL",
    "warning":  "WARNING",
    "overload": "OVERLOAD",
    "degraded": "DEGRADED",
}


def fetch_feeder(feeder_id: str) -> dict:
    url = f"{API_BASE}/scada/feeders/{feeder_id}/live"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 401:
        print("ERROR: Unauthorized — check OT_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 404:
        print(f"ERROR: Feeder '{feeder_id}' not found in SCADA system.", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def print_summary(data: dict) -> None:
    feeder_id       = data.get("feeder_id", "UNKNOWN")
    load_mw         = data.get("load_mw", 0)
    voltage_kv      = data.get("voltage_kv", 0)
    power_factor    = data.get("power_factor", 0)
    capacity_pct    = data.get("capacity_percent", 0)
    status          = data.get("status", "unknown").lower()
    timestamp       = data.get("timestamp", "N/A")
    status_label    = STATUS_LABELS.get(status, status.upper())

    sep = "=" * 60
    print(sep)
    print(f"  SCADA LIVE TELEMETRY — {feeder_id}")
    print(f"  Timestamp : {timestamp}")
    print(sep)
    print(f"  Load          : {load_mw} MW")
    print(f"  Voltage       : {voltage_kv} kV")
    print(f"  Power Factor  : {power_factor}")
    print(f"  Capacity Use  : {capacity_pct}%")
    print(f"  Status        : {status_label}")

    if capacity_pct > CAPACITY_WARNING_THRESHOLD:
        print()
        print(f"  *** CAPACITY WARNING: Feeder {feeder_id} is at {capacity_pct}% capacity.")
        print( "      Immediate load-shedding or feeder augmentation advised.")

    print(sep)


def main():
    parser = argparse.ArgumentParser(description="Fetch live SCADA data for a feeder")
    parser.add_argument("--feeder", required=True, help="Feeder ID (e.g. FDR-002)")
    args = parser.parse_args()

    data = fetch_feeder(args.feeder.upper())
    print_summary(data)


if __name__ == "__main__":
    main()
