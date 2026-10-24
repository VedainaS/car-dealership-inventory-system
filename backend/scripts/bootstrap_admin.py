"""Promote an existing user to admin (local development / ops only).

Usage:
  1. Register a normal account through POST /api/auth/register.
  2. Run: python -m scripts.bootstrap_admin --email you@example.com

This script never creates users and cannot be called over HTTP, so the public
API cannot grant admin privileges.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models import User, UserRole


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a registered user to admin.")
    parser.add_argument("--email", required=True, help="Email of an existing user account")
    args = parser.parse_args()

    email = args.email.lower().strip()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found for email: {email}", file=sys.stderr)
            return 1
        user.role = UserRole.ADMIN
        db.commit()
        print(f"Promoted {email} to admin.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
