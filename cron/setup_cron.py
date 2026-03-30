#!/usr/bin/env python3
"""
cron/setup_cron.py — Generic DotClaw cron job installer

Supports three install targets:
  crontab   : writes to the OS crontab (default, works everywhere)
  systemd   : generates a systemd .service + .timer unit pair (production Linux)
  docker    : prints a docker-compose cron service block (containerised deployments)

Usage
-----
Install the daily AT&C push at 7 AM:
    python cron/setup_cron.py install \
        --name  dotclaw-daily-atc \
        --script /home/user/dotclaw/cron/daily_atc_push.py \
        --schedule "0 7 * * *" \
        --desc "Daily AT&C WhatsApp push to all DISCOM users"

Install using systemd (production recommended):
    python cron/setup_cron.py install \
        --name  dotclaw-daily-atc \
        --script /home/user/dotclaw/cron/daily_atc_push.py \
        --schedule "0 7 * * *" \
        --target systemd

List all DotClaw cron jobs:
    python cron/setup_cron.py list

Remove a job:
    python cron/setup_cron.py remove --name dotclaw-daily-atc

Run a job immediately (outside of schedule):
    python cron/setup_cron.py run --name dotclaw-daily-atc

Predefined jobs (install with --preset):
    python cron/setup_cron.py install --preset atc-daily
    python cron/setup_cron.py install --preset atc-daily --target systemd
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON       = sys.executable
LOG_DIR      = os.path.join(PROJECT_ROOT, "logs")

# ---------------------------------------------------------------------------
# Predefined jobs — add new DotClaw cron tasks here
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "atc-daily": {
        "name":     "dotclaw-daily-atc",
        "script":   os.path.join(PROJECT_ROOT, "cron", "daily_atc_push.py"),
        "schedule": "0 7 * * *",
        "desc":     "Daily AT&C WhatsApp push to all DISCOM users at 7 AM",
    },
    "atc-evening": {
        "name":     "dotclaw-evening-atc",
        "script":   os.path.join(PROJECT_ROOT, "cron", "daily_atc_push.py"),
        "schedule": "0 18 * * *",
        "desc":     "Evening AT&C WhatsApp push at 6 PM",
    },
    # Add more presets here:
    # "sc-daily": {
    #     "name":     "dotclaw-daily-sc",
    #     "script":   os.path.join(PROJECT_ROOT, "cron", "daily_sc_push.py"),
    #     "schedule": "0 7 * * *",
    #     "desc":     "Daily supply chain push at 7 AM",
    # },
}

# Tag all dotclaw crontab entries for easy discovery
CRON_TAG = "# dotclaw-managed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cron_line(name: str, script: str, schedule: str) -> str:
    log_file = os.path.join(LOG_DIR, f"{name}.log")
    return (
        f"{schedule} {PYTHON} {script} "
        f">> {log_file} 2>&1  {CRON_TAG} name={name}"
    )


def _read_crontab() -> str:
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def _write_crontab(content: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
        f.write(content)
        tmp = f.name
    subprocess.run(["crontab", tmp], check=True)
    os.unlink(tmp)


def _list_crontab_jobs() -> list[dict]:
    jobs = []
    for line in _read_crontab().splitlines():
        if CRON_TAG in line:
            name = ""
            for part in line.split():
                if part.startswith("name="):
                    name = part[5:]
            jobs.append({"name": name, "line": line})
    return jobs


# ---------------------------------------------------------------------------
# Systemd unit generators
# ---------------------------------------------------------------------------

def _systemd_service(name: str, script: str, desc: str) -> str:
    log_file = os.path.join(LOG_DIR, f"{name}.log")
    return f"""[Unit]
Description={desc}
After=network.target postgresql.service

[Service]
Type=oneshot
User={os.getenv('USER', 'dotclaw')}
WorkingDirectory={PROJECT_ROOT}
ExecStart={PYTHON} {script}
StandardOutput=append:{log_file}
StandardError=append:{log_file}
EnvironmentFile={os.path.join(PROJECT_ROOT, '.env')}

[Install]
WantedBy=multi-user.target
"""


def _systemd_timer(name: str, schedule: str, desc: str) -> str:
    # Convert cron expression to OnCalendar systemd syntax
    # Simple mapping for common cases; complex expressions need manual adjustment
    parts = schedule.split()
    if len(parts) == 5:
        minute, hour, dom, month, dow = parts
        if dom == "*" and month == "*" and dow == "*":
            on_calendar = f"*-*-* {hour.zfill(2)}:{minute.zfill(2)}:00"
        else:
            on_calendar = schedule  # leave as-is; user may need to adjust
    else:
        on_calendar = schedule

    return f"""[Unit]
Description={desc} — Timer
Requires={name}.service

[Timer]
OnCalendar={on_calendar}
Persistent=true
Unit={name}.service

[Install]
WantedBy=timers.target
"""


def install_systemd(name: str, script: str, schedule: str, desc: str) -> None:
    systemd_dir = Path("/etc/systemd/system")
    if not systemd_dir.exists():
        print(f"ERROR: /etc/systemd/system not found. Are you on a systemd Linux system?")
        sys.exit(1)

    svc_path   = systemd_dir / f"{name}.service"
    timer_path = systemd_dir / f"{name}.timer"

    svc_content   = _systemd_service(name, script, desc)
    timer_content = _systemd_timer(name, schedule, desc)

    print(f"\n  Writing {svc_path}")
    svc_path.write_text(svc_content)
    print(f"  Writing {timer_path}")
    timer_path.write_text(timer_content)

    print("\n  Reloading systemd daemon...")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", f"{name}.timer"], check=True)

    print(f"\n  Installed! Check with: systemctl status {name}.timer")
    print(f"  Logs: {os.path.join(LOG_DIR, name + '.log')}")


# ---------------------------------------------------------------------------
# Docker block generator (prints only — user adds to docker-compose.yml)
# ---------------------------------------------------------------------------

def print_docker_block(name: str, script: str, schedule: str, desc: str) -> None:
    rel_script = os.path.relpath(script, PROJECT_ROOT)
    print(f"""
# Add this to your docker-compose.yml services block:
# {desc}

  {name}:
    image: python:3.11-slim
    restart: unless-stopped
    environment:
      - DATABASE_URL=${{DATABASE_URL}}
      - OT_API_BASE=${{OT_API_BASE}}
      - OT_API_TOKEN=${{OT_API_TOKEN}}
      - WHATSAPP_API_TOKEN=${{WHATSAPP_API_TOKEN}}
      - WHATSAPP_PHONE_NUMBER_ID=${{WHATSAPP_PHONE_NUMBER_ID}}
    volumes:
      - .:/app
    working_dir: /app
    command: >
      sh -c "pip install -r requirements.txt -q &&
             while true; do
               python {rel_script}
               sleep 86400
             done"
    # Note: For production use a proper cron container like mcuadros/ofelia
    # or configure supercronic. The above is for development only.
""")
    print("For production Docker, use supercronic:")
    print(f"  Schedule: {schedule}")
    print(f"  Command:  {PYTHON} {rel_script}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_install(args) -> None:
    if args.preset:
        if args.preset not in PRESETS:
            print(f"Unknown preset '{args.preset}'. Available: {list(PRESETS.keys())}")
            sys.exit(1)
        p = PRESETS[args.preset]
        name, script, schedule, desc = p["name"], p["script"], p["schedule"], p["desc"]
    else:
        if not all([args.name, args.script, args.schedule]):
            print("Provide --name, --script, --schedule  or  --preset <name>")
            sys.exit(1)
        name     = args.name
        script   = os.path.abspath(args.script)
        schedule = args.schedule
        desc     = args.desc or f"DotClaw job: {name}"

    if not os.path.exists(script):
        print(f"ERROR: Script not found: {script}")
        sys.exit(1)

    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"\nInstalling cron job: {name}")
    print(f"  Script  : {script}")
    print(f"  Schedule: {schedule}  (cron expression)")
    print(f"  Desc    : {desc}")
    print(f"  Target  : {args.target}")
    print(f"  Log dir : {LOG_DIR}")

    if args.target == "systemd":
        install_systemd(name, script, schedule, desc)

    elif args.target == "docker":
        print_docker_block(name, script, schedule, desc)

    else:  # crontab (default)
        existing = _read_crontab()
        # Remove existing entry for same name if present
        lines = [l for l in existing.splitlines()
                 if not (CRON_TAG in l and f"name={name}" in l)]
        new_line = _cron_line(name, script, schedule)
        lines.append(new_line)
        _write_crontab("\n".join(lines) + "\n")
        print(f"\n  Added to crontab:")
        print(f"  {new_line}")
        print(f"\n  Verify: crontab -l | grep dotclaw")
        print(f"  Logs  : tail -f {os.path.join(LOG_DIR, name + '.log')}")


def cmd_list(args) -> None:
    jobs = _list_crontab_jobs()
    # Also check systemd
    systemd_timers = []
    try:
        result = subprocess.run(
            ["systemctl", "list-timers", "--all", "--no-pager"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "dotclaw" in line:
                systemd_timers.append(line.strip())
    except Exception:
        pass

    print("\nDotClaw cron jobs:")
    print("=" * 60)

    if jobs:
        print("\n  [crontab]")
        for j in jobs:
            print(f"    {j['name']}")
            print(f"    {j['line']}")
    else:
        print("\n  [crontab] — no jobs found")

    if systemd_timers:
        print("\n  [systemd timers]")
        for t in systemd_timers:
            print(f"    {t}")

    if not jobs and not systemd_timers:
        print("\n  No DotClaw cron jobs found.")

    print()


def cmd_remove(args) -> None:
    if not args.name:
        print("Provide --name")
        sys.exit(1)

    existing = _read_crontab()
    lines = [l for l in existing.splitlines()
             if not (CRON_TAG in l and f"name={args.name}" in l)]

    if len(lines) == len(existing.splitlines()):
        # Also try systemd
        svc   = Path(f"/etc/systemd/system/{args.name}.service")
        timer = Path(f"/etc/systemd/system/{args.name}.timer")
        if timer.exists():
            subprocess.run(["systemctl", "disable", "--now", f"{args.name}.timer"], check=False)
            timer.unlink(missing_ok=True)
            svc.unlink(missing_ok=True)
            subprocess.run(["systemctl", "daemon-reload"], check=False)
            print(f"Removed systemd timer: {args.name}")
            return
        print(f"Job '{args.name}' not found in crontab or systemd.")
        return

    _write_crontab("\n".join(lines) + "\n")
    print(f"Removed '{args.name}' from crontab.")


def cmd_run(args) -> None:
    """Run a job immediately, outside its schedule."""
    if not args.name:
        print("Provide --name")
        sys.exit(1)

    # Find in crontab
    for job in _list_crontab_jobs():
        if job["name"] == args.name:
            # Extract script path from the cron line
            parts = job["line"].split()
            # Format: schedule(5 parts) python script ...
            script = parts[6] if len(parts) > 6 else None
            if script and os.path.exists(script):
                print(f"Running {args.name} now...")
                subprocess.run([PYTHON, script], check=True)
                return

    # Try presets
    if args.name.replace("dotclaw-", "") in PRESETS or args.name in PRESETS:
        key = args.name.replace("dotclaw-", "") if args.name.startswith("dotclaw-") else args.name
        preset = PRESETS.get(key)
        if preset:
            print(f"Running {preset['name']} now...")
            subprocess.run([PYTHON, preset["script"]], check=True)
            return

    print(f"Could not find script for job '{args.name}'. Use --script to specify directly.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DotClaw cron job manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # install
    p_install = sub.add_parser("install", help="Install a cron job")
    p_install.add_argument("--preset",   help=f"Use a predefined job: {list(PRESETS.keys())}")
    p_install.add_argument("--name",     help="Job name (e.g. dotclaw-daily-atc)")
    p_install.add_argument("--script",   help="Absolute path to Python script")
    p_install.add_argument("--schedule", help="Cron expression (e.g. '0 7 * * *')")
    p_install.add_argument("--desc",     default="", help="Human-readable description")
    p_install.add_argument("--target",   choices=["crontab", "systemd", "docker"],
                           default="crontab", help="Install target (default: crontab)")

    # list
    sub.add_parser("list", help="List all DotClaw cron jobs")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a cron job")
    p_remove.add_argument("--name", required=True)

    # run
    p_run = sub.add_parser("run", help="Run a job immediately")
    p_run.add_argument("--name", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    {"install": cmd_install,
     "list":    cmd_list,
     "remove":  cmd_remove,
     "run":     cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
