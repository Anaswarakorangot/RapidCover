#!/usr/bin/env python3
"""
Script to create the first admin user for RapidCover.

Usage:
  python create_admin.py

Creates an admin with:
  - Email: admin@rapidcover.in
  - Password: admin123
  - Full Name: Admin User
  - Is Superadmin: True
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.database import get_db, engine, Base
from app.models.admin import Admin
from passlib.context import CryptContext
from app.utils.time_utils import utcnow

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    """Create the first admin user."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = next(get_db())

    # Check if admin already exists
    existing = db.query(Admin).filter(Admin.email == "admin@rapidcover.in").first()
    if existing:
        print("[INFO] Admin user already exists: admin@rapidcover.in")
        print(f"[INFO] Full Name: {existing.full_name}")
        print(f"[INFO] Is Superadmin: {existing.is_superadmin}")
        print(f"[INFO] Created At: {existing.created_at}")
        return

    # Create new admin
    hashed_password = pwd_context.hash("admin123")
    admin = Admin(
        email="admin@rapidcover.in",
        hashed_password=hashed_password,
        full_name="Admin User",
        is_active=True,
        is_superadmin=True,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    print("[SUCCESS] Admin user created successfully!")
    print()
    print("Login credentials:")
    print("  Email:    admin@rapidcover.in")
    print("  Password: admin123")
    print()
    print("You can now login at: http://localhost:5173/login")
    print("After login, you'll be redirected to: http://localhost:5173/admin")

if __name__ == "__main__":
    create_admin()
