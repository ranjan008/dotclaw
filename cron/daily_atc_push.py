#!/usr/bin/env python3
"""
cron/daily_atc_push.py — Daily AT&C Push to WhatsApp

Runs at 7 AM every day (configured via setup_cron.py).

What it does
------------
1. Reads ALL active users for the 'discom' domain from the RBAC registry.
2. For each user, fetches only the data permitted by their role + scope:
     - AT&C loss data  (MDMS)
     - Meter anomalies (AMI)
     - Live feeder load (SCADA) — for field roles
3. Builds a role-appropriate WhatsApp message (executive summary → field action list).
4. Sends directly to each user's WhatsApp number via Meta Graph API.
   In dev mode (no WHATSAPP_API_TOKEN set) it prints the messages to stdout.

Roles and what they receive
---------------------------
  cmd / director_ops / mis_finance  : Overall AT&C digest, top loss feeders, trend
  circle_se                         : Circle-level AT&C, feeder breakdown, anomaly count
  division_ee                       : Division feeders + meter anomaly summary + action
  sub_division_ae                   : Sub-division feeders + specific DT anomalies + priority meters
  junior_engineer                   : Their assigned feeder load/status + DT anomaly count
  revenue_protection                : Field action list — tamper + zero-read meters with IDs

Usage
-----
    python cron/daily_atc_push.py              # run now (all users)
    python cron/daily_atc_push.py --dry-run    # print messages, don't send
    python cron/daily_atc_push.py --user +91XXXXXXXXXX  # single user test
    python cron/daily_atc_push.py --role division_ee    # all users of a role
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

# Load .env from project root
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_root, ".env"))

sys.path.insert(0, _root)

from rbac.user_registry import get_scope, list_users

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE  = os.getenv("OT_API_BASE",  "http://localhost:5000")
API_TOKEN = os.getenv("OT_API_TOKEN", "OT-POC-TOKEN-2026")

WA_API_TOKEN    = os.getenv("WHATSAPP_API_TOKEN", "")
WA_PHONE_NUM_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WA_API_URL      = f"https://graph.facebook.com/v18.0/{WA_PHONE_NUM_ID}/messages"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("daily_atc_push")

TODAY = datetime.now(timezone.utc).strftime("%d %b %Y")


# ---------------------------------------------------------------------------
# Data fetchers (all scoped to what the user is allowed to see)
# ---------------------------------------------------------------------------

def _get(path: str, params: dict = None) -> list | dict:
    r = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        params=params or {},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fetch_atc(days: int = 7) -> list:
    return _get("/mdms/atc", {"days": days})


def fetch_anomalies(anomaly_type: str = None) -> list:
    params = {"type": anomaly_type} if anomaly_type else {}
    return _get("/mdms/meters/anomalies", params)


def fetch_feeder(feeder_id: str) -> dict | None:
    try:
        return _get(f"/scada/feeders/{feeder_id}/live")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Scoped data helpers
# ---------------------------------------------------------------------------

def _scope_atc(atc_rows: list, allowed_feeders: list[str]) -> list:
    """Filter top_loss_feeders in each ATC row to allowed feeders only."""
    if not allowed_feeders:
        return atc_rows
    result = []
    for row in atc_rows:
        filtered = [f for f in row.get("top_loss_feeders", [])
                    if f["feeder"].upper() in allowed_feeders]
        result.append({**row, "top_loss_feeders": filtered})
    return result


def _scope_anomalies(anomalies: list, allowed_dts: list[str]) -> list:
    if not allowed_dts:
        return anomalies
    return [a for a in anomalies if a["dt_id"].upper() in allowed_dts]


def _scope_feeders(feeder_ids: list[str]) -> list[dict]:
    results = []
    for fid in feeder_ids:
        data = fetch_feeder(fid)
        if data:
            results.append(data)
    return results


# ---------------------------------------------------------------------------
# Message builders (one per role group)
# ---------------------------------------------------------------------------

def _fmt_loss(pct: float) -> str:
    if pct >= 22:  return f"{pct}% 🚨"
    if pct >= 20:  return f"{pct}% ⚠️"
    return f"{pct}%"


def _fmt_feeder_load(f: dict) -> str:
    status = f.get("status", "")
    icon = {"overload": "🚨", "warning": "⚠️", "degraded": "⚠️"}.get(status, "✅")
    return f"{f['feeder_id']}: {f['capacity_percent']}% {icon}"


def build_executive_digest(user: dict, atc: list, anomalies: list) -> str:
    """CMD / Director / MIS-Finance — overall AT&C digest."""
    latest = atc[-1] if atc else {}
    first  = atc[0]  if atc else {}
    avg    = sum(r["atc_loss_percent"] for r in atc) / len(atc) if atc else 0
    wow    = latest.get("atc_loss_percent", 0) - first.get("atc_loss_percent", 0)
    trend  = "↓ Improving" if wow < 0 else "↑ Worsening"

    top3 = sorted(latest.get("top_loss_feeders", []),
                  key=lambda x: x["loss_percent"], reverse=True)[:3]
    top3_str = "  ".join(f"{f['feeder']} ({_fmt_loss(f['loss_percent'])})" for f in top3)

    tamper    = sum(1 for a in anomalies if a["anomaly_type"] == "tamper")
    zero_read = sum(1 for a in anomalies if a["anomaly_type"] == "zero_read")
    comm_fail = sum(1 for a in anomalies if a["anomaly_type"] == "comm_failure")

    lines = [
        f"*AT&C Daily Digest — {TODAY}*",
        f"Overall AT&C : {_fmt_loss(latest.get('atc_loss_percent', 0))}",
        f"7-Day Avg    : {avg:.1f}%   Trend: {trend} ({wow:+.1f} pp)",
        f"Top Feeders  : {top3_str}" if top3_str else "",
        f"Meter Alerts : {len(anomalies)} total  "
        f"(Tamper {tamper} ⚠️  |  Zero-read {zero_read}  |  Comm fail {comm_fail})",
    ]
    if top3:
        lines.append(f"Action       : Field audit at {top3[0]['feeder']} — {_fmt_loss(top3[0]['loss_percent'])} loss")

    return "\n".join(l for l in lines if l)


def build_circle_se_message(user: dict, atc: list, anomalies: list) -> str:
    """Circle SE — circle-level summary."""
    scope = get_scope(user)["scope"]
    allowed_feeders = scope.get("feeders", [])
    latest = atc[-1] if atc else {}
    top = sorted(latest.get("top_loss_feeders", []),
                 key=lambda x: x["loss_percent"], reverse=True)

    dt_counts: dict[str, int] = {}
    for a in anomalies:
        dt_counts[a["dt_id"]] = dt_counts.get(a["dt_id"], 0) + 1

    circle = (user.get("org_unit") or {}).get("circle", "Your Circle")
    lines = [
        f"*AT&C Update — {circle} — {TODAY}*",
        f"Feeders in scope: {', '.join(allowed_feeders) or 'all'}",
    ]
    if top:
        feeders_str = "  ".join(f"{f['feeder']} ({_fmt_loss(f['loss_percent'])})" for f in top[:5])
        lines.append(f"Loss by feeder: {feeders_str}")
    if dt_counts:
        dt_str = "  ".join(f"{dt}: {cnt}" for dt, cnt in sorted(dt_counts.items()))
        lines.append(f"DT anomalies  : {dt_str}")
        worst_feeder = top[0]["feeder"] if top else "-"
        lines.append(f"Action        : Prioritise {worst_feeder} — review DT cluster dispatch")
    return "\n".join(lines)


def build_division_ee_message(user: dict, atc: list, anomalies: list,
                               feeder_live: list[dict]) -> str:
    """Division EE — feeder status + anomaly summary + action."""
    org  = user.get("org_unit") or {}
    division = org.get("division", "Your Division")

    feeder_lines = "  ".join(_fmt_feeder_load(f) for f in feeder_live) if feeder_live else "—"
    tamper = [a for a in anomalies if a["anomaly_type"] == "tamper"]

    dt_counts: dict[str, int] = {}
    for a in anomalies:
        dt_counts[a["dt_id"]] = dt_counts.get(a["dt_id"], 0) + 1

    latest = atc[-1] if atc else {}
    top = sorted(latest.get("top_loss_feeders", []),
                 key=lambda x: x["loss_percent"], reverse=True)

    lines = [
        f"*Morning AT&C — {division} — {TODAY}*",
        f"Live feeders  : {feeder_lines}",
    ]
    if top:
        lines.append(f"AT&C today    : " +
                     "  ".join(f"{f['feeder']} {_fmt_loss(f['loss_percent'])}" for f in top))
    if anomalies:
        dt_str = "  ".join(f"{dt}({cnt})" for dt, cnt in sorted(dt_counts.items()))
        lines.append(f"Meter issues  : {len(anomalies)} total — {dt_str}")
    if tamper:
        worst_dt = sorted(dt_counts, key=dt_counts.get, reverse=True)[0]
        lines.append(f"⚠️  Action     : Dispatch field team to {worst_dt} — {len(tamper)} tamper case(s)")
    return "\n".join(lines)


def build_ae_message(user: dict, atc: list, anomalies: list,
                     feeder_live: list[dict]) -> str:
    """Sub-division AE — sub-division feeders + specific DT anomalies."""
    org = user.get("org_unit") or {}
    sub_div = org.get("sub_division", org.get("division", "Your Sub-Division"))

    feeder_lines = "  |  ".join(_fmt_feeder_load(f) for f in feeder_live) if feeder_live else "—"

    # Group anomalies by DT
    dt_groups: dict[str, list] = {}
    for a in anomalies:
        dt_groups.setdefault(a["dt_id"], []).append(a)

    lines = [
        f"*SubDiv Field Brief — {sub_div} — {TODAY}*",
        f"Feeders       : {feeder_lines}",
    ]

    if not anomalies:
        lines.append("Meter status  : All clear ✅")
    else:
        for dt, meters in sorted(dt_groups.items()):
            types = ", ".join(sorted({a["anomaly_type"] for a in meters}))
            lines.append(f"{dt} ({len(meters)} cases): {types}")
        # Priority meters (tamper, sorted by days silent)
        priority = sorted(
            [a for a in anomalies if a["anomaly_type"] == "tamper"],
            key=lambda x: x["days_since_last_read"], reverse=True
        )[:3]
        if priority:
            p_str = "  ".join(f"{a['meter_id']}({a['days_since_last_read']}d)" for a in priority)
            lines.append(f"Priority mtrs : {p_str}")
            lines.append(f"⚠️  Action     : Physical inspection — report to EE by EOD")

    return "\n".join(lines)


def build_je_message(user: dict, feeder_live: list[dict], anomalies: list) -> str:
    """Junior Engineer — their feeder status + DT anomaly count."""
    lines = [f"*Your Feeder Brief — {TODAY}*"]
    for f in feeder_live:
        status = f.get("status", "unknown").upper()
        icon = {"OVERLOAD": "🚨", "WARNING": "⚠️", "DEGRADED": "⚠️"}.get(status, "✅")
        lines += [
            f"Feeder  : {f['feeder_id']}",
            f"Load    : {f['load_mw']} MW  |  Voltage: {f['voltage_kv']} kV  |  PF: {f['power_factor']}",
            f"Capacity: {f['capacity_percent']}%  {icon} {status}",
        ]
        if f.get("capacity_percent", 0) >= 85:
            lines.append("Action  : Notify AE — load approaching/exceeding safe limit")

    dt_counts: dict[str, int] = {}
    for a in anomalies:
        dt_counts[a["dt_id"]] = dt_counts.get(a["dt_id"], 0) + 1
    if dt_counts:
        dt_str = "  ".join(f"{dt}({cnt})" for dt, cnt in dt_counts.items())
        lines.append(f"DT alerts: {dt_str} — report to AE for dispatch")

    return "\n".join(lines)


def build_rpo_message(user: dict, anomalies: list) -> str:
    """Revenue Protection Officer — tamper + zero-read field action list."""
    tamper    = sorted([a for a in anomalies if a["anomaly_type"] == "tamper"],
                       key=lambda x: x["days_since_last_read"], reverse=True)
    zero_read = sorted([a for a in anomalies if a["anomaly_type"] == "zero_read"],
                       key=lambda x: x["days_since_last_read"], reverse=True)

    lines = [f"*Field Action List — {TODAY}*"]

    if tamper:
        lines.append(f"\n🚨 TAMPER ({len(tamper)} meters):")
        for a in tamper[:5]:  # top 5 by days silent
            lines.append(f"   {a['meter_id']}  DT:{a['dt_id']}  {a['days_since_last_read']}d silent  ({a['sector']})")
        if len(tamper) > 5:
            lines.append(f"   ...and {len(tamper)-5} more")
        lines.append("   Action: Physical inspection + FIR if bypass confirmed")

    if zero_read:
        lines.append(f"\n⚠️  ZERO-READ ({len(zero_read)} meters):")
        for a in zero_read[:5]:
            lines.append(f"   {a['meter_id']}  DT:{a['dt_id']}  {a['days_since_last_read']}d silent")
        lines.append("   Action: Verify meter health, arrange replacement if faulty")

    if not tamper and not zero_read:
        lines.append("No tamper or zero-read cases today. ✅")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Message dispatcher — routes to the right builder by role
# ---------------------------------------------------------------------------

def build_message(user: dict,
                  atc: list, anomalies: list, feeder_live: list[dict]) -> Optional[str]:
    role = user.get("role", "")

    if role in ("cmd", "director_ops", "mis_finance", "it_admin"):
        return build_executive_digest(user, atc, anomalies)

    if role == "circle_se":
        return build_circle_se_message(user, atc, anomalies)

    if role == "division_ee":
        return build_division_ee_message(user, atc, anomalies, feeder_live)

    if role == "sub_division_ae":
        return build_ae_message(user, atc, anomalies, feeder_live)

    if role == "junior_engineer":
        return build_je_message(user, feeder_live, anomalies)

    if role == "revenue_protection":
        return build_rpo_message(user, anomalies)

    return None  # unknown role — skip


# ---------------------------------------------------------------------------
# WhatsApp sender
# ---------------------------------------------------------------------------

def send_wa(to: str, text: str, dry_run: bool = False) -> bool:
    """
    Send a WhatsApp message via Meta Graph API.
    Falls back to console log if credentials are not configured.
    """
    if dry_run or not WA_API_TOKEN or not WA_PHONE_NUM_ID:
        # Dev / dry-run mode
        print(f"\n{'─'*60}")
        print(f"  TO : {to}")
        print(f"{'─'*60}")
        print(text)
        return True

    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    try:
        r = requests.post(
            WA_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {WA_API_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        log.error("WA send failed to %s: %s", to, exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False,
        target_wa: str = None,
        target_role: str = None) -> None:

    log.info("Daily AT&C push starting — %s", TODAY)

    # 1. Fetch base data (full dataset — will be scoped per user)
    log.info("Fetching AT&C data from MDMS...")
    all_atc      = fetch_atc(days=7)
    log.info("Fetching meter anomalies from AMI...")
    all_anomalies = fetch_anomalies()

    # 2. Get target users from RBAC registry
    filters = {"domain": "discom", "active_only": True}
    if target_role:
        filters["role"] = target_role
    users = list_users(**filters)

    if target_wa:
        users = [u for u in users if u["wa_number"] == target_wa]

    log.info("Users to notify: %d", len(users))

    sent = skipped = failed = 0

    for user in users:
        wa  = user["wa_number"]
        role = user["role"]
        scope_data = get_scope(user)
        scope = scope_data["scope"]
        all_access = scope_data["all_access"]

        log.info("Processing %s (%s — %s)", user["name"], role, wa)

        # Scope the data
        if all_access:
            atc_scoped       = all_atc
            anomalies_scoped = all_anomalies
            feeders_scoped   = []
        else:
            allowed_feeders = scope.get("feeders", [])
            allowed_dts     = scope.get("dts", [])

            atc_scoped       = _scope_atc(all_atc, allowed_feeders)
            anomalies_scoped = _scope_anomalies(all_anomalies, allowed_dts)
            feeder_ids       = allowed_feeders[:3]  # cap live calls to 3 per user
            feeders_scoped   = _scope_feeders(feeder_ids)

        # Build message
        msg = build_message(user, atc_scoped, anomalies_scoped, feeders_scoped)
        if msg is None:
            log.warning("No message template for role '%s' — skipping %s", role, wa)
            skipped += 1
            continue

        # Send
        ok = send_wa(wa, msg, dry_run=dry_run)
        if ok:
            sent += 1
        else:
            failed += 1

    log.info("Push complete — sent: %d  skipped: %d  failed: %d", sent, skipped, failed)
    if failed:
        sys.exit(1)  # non-zero exit triggers cron failure alert


def main():
    parser = argparse.ArgumentParser(description="Daily AT&C WhatsApp push")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print messages to stdout instead of sending")
    parser.add_argument("--user", metavar="WA_NUMBER",
                        help="Push to a single user (for testing)")
    parser.add_argument("--role", metavar="ROLE",
                        help="Push to all users of a specific role")
    args = parser.parse_args()

    run(dry_run=args.dry_run, target_wa=args.user, target_role=args.role)


if __name__ == "__main__":
    main()
