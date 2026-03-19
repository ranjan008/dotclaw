#!/usr/bin/env python3
"""
AT&C Analytics Skill — run_atc.py
Fetches MDMS AT&C loss data and prints an executive-style summary with
week-over-week delta and top loss feeder highlights.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"))

API_BASE = os.getenv("OT_API_BASE", "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")


def fetch_atc(days: int) -> list:
    url = f"{API_BASE}/mdms/atc"
    params = {"days": days}
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 401:
        print("ERROR: Unauthorized — check OT_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def print_report(data: list) -> None:
    if not data:
        print("No AT&C data available.")
        return

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    start_date = data[0]["date"]
    end_date = data[-1]["date"]
    days = len(data)

    latest = data[-1]
    first = data[0]
    avg_loss = sum(d["atc_loss_percent"] for d in data) / days

    # Week-over-week delta (last day vs first day)
    wow_delta = latest["atc_loss_percent"] - first["atc_loss_percent"]
    if len(data) >= 2:
        wow_label = "IMPROVING" if wow_delta < 0 else "WORSENING"
        wow_str = f"{wow_delta:+.1f} pp  [{wow_label}]"
    else:
        wow_str = "N/A (need >= 2 days)"

    sep = "=" * 60
    div = "  " + chr(0x2500) * 54

    print(sep)
    print("  AT&C LOSS ANALYTICS — EXECUTIVE SUMMARY")
    print(f"  Report Period : {start_date} to {end_date}  ({days} days)")
    print(f"  Generated     : {now_str} UTC")
    print(sep)

    print()
    print("  PERIOD OVERVIEW")
    print(div)
    print(f"  Avg AT&C Loss     : {avg_loss:.2f}%")
    print(f"  Latest Day Loss   : {latest['atc_loss_percent']}%   ({latest['date']})")
    print(f"  First Day Loss    : {first['atc_loss_percent']}%   ({first['date']})")
    print(f"  Week-over-Week    : {wow_str}")

    print()
    print("  DAILY TREND")
    print(div)
    print(f"  {'Date':<12} {'Input(MU)':<11} {'Billed(MU)':<12} Loss%")
    for row in data:
        print(
            f"  {row['date']:<12} {row['units_input_mu']:<11.2f} "
            f"{row['units_billed_mu']:<12.2f} {row['atc_loss_percent']}%"
        )

    # Top 3 loss feeders from latest day
    top_feeders = sorted(
        latest.get("top_loss_feeders", []),
        key=lambda x: x.get("loss_percent", 0),
        reverse=True,
    )[:3]

    print()
    print("  TOP 3 LOSS FEEDERS (latest day)")
    print(div)
    for rank, f in enumerate(top_feeders, 1):
        tag = "  [ACTION REQUIRED]" if rank == 1 else ""
        print(f"  #{rank}  {f['feeder']:<8} :  {f['loss_percent']}%{tag}")

    worst = top_feeders[0]["feeder"] if top_feeders else "N/A"
    print()
    print(sep)
    print(f"  RECOMMENDATION: Review {worst} for commercial loss drivers")
    print("  (meter bypass, DT losses). Field verification advised.")
    print(sep)


def main():
    parser = argparse.ArgumentParser(description="AT&C Loss Analytics Report")
    parser.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    args = parser.parse_args()

    data = fetch_atc(args.days)
    print_report(data)


if __name__ == "__main__":
    main()
