#!/usr/bin/env python3
"""
Delete all admins and recreate the default admin.
Run this to fix admin authentication issues.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import get_db
from app.models.admin import Admin

def reset_admins():
    """Delete all admins."""
    db = next(get_db())

    # Delete all admins
    deleted = db.query(Admin).delete()
    db.commit()

    print(f"[OK] Deleted {deleted} admin(s)")
    print("[OK] Restart the backend to create fresh admin with correct bcrypt")
    print()

if __name__ == "__main__":
    reset_admins()
