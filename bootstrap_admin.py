"""
bootstrap_admin.py — Register the first IT Admin for a given domain.

WHY THIS EXISTS
---------------
Chicken-and-egg problem: only an it_admin can add users via WhatsApp,
but the first admin cannot add themselves that way.
This script writes directly to PostgreSQL and must be run server-side
by the deployment team during initial setup.

After the first admin is added, they manage all other users via WhatsApp:
  ADD USER, DEACTIVATE USER, LIST USERS, AUDIT, DENY REPORT

USAGE
-----
    # DISCOM (default domain)
    python bootstrap_admin.py --wa +919000000099 --name "IT Admin" --emp EMP-099

    # Supply chain domain
    python bootstrap_admin.py --wa +919001000099 --name "SC IT Admin" \\
                              --emp SC-099 --domain supplychain

    # Finance domain
    python bootstrap_admin.py --wa +919002000099 --name "Finance IT Admin" \\
                              --emp FIN-099 --domain finance

    # Check DB connectivity only
    python bootstrap_admin.py --check
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from rbac.db import DATABASE_URL, init_db
from rbac.user_registry import add_user, get_user


def _masked_url(url: str) -> str:
    return re.sub(r"(:)[^:@]+(@)", r"\1****\2", url)


def check_connection() -> bool:
    try:
        init_db()
        print(f"  Connected : {_masked_url(DATABASE_URL)}")
        print("  Tables    : OK")
        return True
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first IT Admin for a DotClaw domain.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--wa",     metavar="NUMBER", help="WhatsApp number (e.g. +919000000099)")
    parser.add_argument("--name",   metavar="NAME",   help="Full name")
    parser.add_argument("--emp",    metavar="ID",     default="", help="Employee ID (optional)")
    parser.add_argument("--domain", metavar="DOMAIN", default="discom",
                        help="Domain: discom | supplychain | finance  (default: discom)")
    parser.add_argument("--check",  action="store_true",
                        help="Check DB connection only; do not insert.")
    args = parser.parse_args()

    print(f"\nDotClaw RBAC Bootstrap  [domain: {args.domain}]")
    print("=" * 45)

    print("\nChecking database connection...")
    if not check_connection():
        print("\nVerify DATABASE_URL in .env and that PostgreSQL is running.", file=sys.stderr)
        sys.exit(1)

    if args.check:
        print("\nConnection check passed.")
        sys.exit(0)

    if not args.wa or not args.name:
        parser.error("--wa and --name are required unless using --check.")

    existing = get_user(args.wa)
    if existing:
        print(
            f"\nUser {args.wa} already exists:\n"
            f"  Name: {existing['name']}  Domain: {existing.get('domain')}  "
            f"Role: {existing['role']}  Active: {existing['active']}"
        )
        print("No changes made.")
        sys.exit(0)

    try:
        user = add_user(
            args.wa, args.name, "it_admin", args.domain,
            employee_id=args.emp,
            registered_by="bootstrap",
        )
        print(f"\nIT Admin registered successfully:")
        print(f"  WA number : {user['wa_number']}")
        print(f"  Name      : {user['name']}")
        print(f"  Domain    : {user['domain']}")
        print(f"  Role      : {user['role']}")
        print(f"  Emp ID    : {user.get('employee_id') or 'N/A'}")
        print(
            f"\nThis number can now send admin commands via WhatsApp for the "
            f"'{args.domain}' domain."
        )
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
