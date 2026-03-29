"""
bootstrap_admin.py — One-time CLI tool to register the FIRST IT Admin.

WHY THIS EXISTS
---------------
There is a chicken-and-egg problem with RBAC:
  - Only an it_admin can add users via WhatsApp.
  - The first it_admin cannot add themselves via WhatsApp (no one is in the DB yet).

This script bypasses WhatsApp entirely and writes the first admin directly
into the PostgreSQL database.  It must be run ONCE by the server-side IT team
during initial deployment.  After that, the admin can manage all other users
through WhatsApp admin commands.

PREREQUISITES
-------------
1. PostgreSQL is running and DATABASE_URL is set in .env
2. Tables have been created (this script calls init_db() automatically)
3. Python env has psycopg2-binary installed  (pip install -r requirements.txt)

USAGE
-----
    python bootstrap_admin.py --wa +919000000099 --name "IT Admin" --emp EMP-099

    # With explicit DATABASE_URL override:
    DATABASE_URL=postgresql://user:pass@host:5432/db python bootstrap_admin.py \
        --wa +919000000099 --name "IT Admin" --emp EMP-099

    # Dry-run (check DB connection without inserting):
    python bootstrap_admin.py --check

AFTER FIRST ADMIN IS ADDED
---------------------------
The IT Admin can then manage all other users via WhatsApp:

    ADD USER +919XXXXXXXXXX name=Rajesh_Kumar role=division_ee
             circle=Circle-North division=Division-3
             feeders=FDR-001,FDR-002,FDR-003 zones=Zone-A

    DEACTIVATE USER +919XXXXXXXXXX

    LIST USERS division=Division-3

    AUDIT +919XXXXXXXXXX last=48

    DENY REPORT last=24
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

# Load .env before importing rbac modules (they read DATABASE_URL at import time)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from rbac.db import DATABASE_URL, init_db
from rbac.user_registry import add_user, get_user


# --------------------------------------------------------------------------- #
# Connection health check
# --------------------------------------------------------------------------- #

def check_connection() -> bool:
    """Attempt to connect to PostgreSQL and initialise tables."""
    try:
        init_db()
        print(f"  Connected to: {_masked_url(DATABASE_URL)}")
        print("  Tables: OK")
        return True
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return False


def _masked_url(url: str) -> str:
    """Hide password in the URL for display."""
    import re
    return re.sub(r"(:)[^:@]+(@)", r"\1****\2", url)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first IT Admin into the DotClaw RBAC database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--wa",
        metavar="NUMBER",
        help="WhatsApp number of the IT Admin (e.g. +919000000099)",
    )
    parser.add_argument(
        "--name",
        metavar="NAME",
        help="Full name of the IT Admin (e.g. 'IT Admin')",
    )
    parser.add_argument(
        "--emp",
        metavar="ID",
        default="",
        help="Employee ID (optional)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check DB connectivity; do not insert.",
    )
    args = parser.parse_args()

    print("\nDotClaw RBAC Bootstrap")
    print("=" * 40)

    # -- Connection check --
    print("\nChecking database connection...")
    if not check_connection():
        print(
            "\nFailed to connect. Verify DATABASE_URL in .env and that PostgreSQL is running.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.check:
        print("\nConnection check passed. Use --wa and --name to register the first admin.")
        sys.exit(0)

    # -- Validate args --
    if not args.wa or not args.name:
        parser.error("--wa and --name are required unless using --check.")

    # -- Guard: already exists? --
    existing = get_user(args.wa)
    if existing:
        print(
            f"\nUser {args.wa} already exists in the database:\n"
            f"  Name: {existing['name']}  Role: {existing['role']}  Active: {existing['active']}"
        )
        print("\nNo changes made.")
        sys.exit(0)

    # -- Insert --
    try:
        user = add_user(
            args.wa,
            args.name,
            "it_admin",
            employee_id=args.emp,
            registered_by="bootstrap",
        )
        print(f"\nIT Admin registered successfully:")
        print(f"  WA number   : {user['wa_number']}")
        print(f"  Name        : {user['name']}")
        print(f"  Employee ID : {user.get('employee_id') or 'N/A'}")
        print(f"  Role        : {user['role']}")
        print(f"  Registered  : {user['registered_at']}")
        print(
            "\nThis number can now send admin commands via WhatsApp:\n"
            "  ADD USER, DEACTIVATE USER, LIST USERS, AUDIT, DENY REPORT"
        )
    except Exception as exc:
        print(f"\nError registering admin: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
