"""
Automatic admin seeding on startup.
Creates default admin user if none exists.
"""

from sqlalchemy.orm import Session
from app.models.admin import Admin
from app.database import get_db, engine, Base
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@rapidcover.in")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Admin User")


def seed_default_admin():
    """Create default admin if no admins exist."""
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)

        db = next(get_db())

        # Check if any admin exists
        admin_count = db.query(Admin).count()

        if admin_count == 0:
            # No admins exist, create default admin
            hashed_password = pwd_context.hash(DEFAULT_ADMIN_PASSWORD)

            admin = Admin(
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed_password,
                full_name=DEFAULT_ADMIN_NAME,
                is_active=True,
                is_superadmin=True,
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            print("\n" + "=" * 70)
            print("🔐 DEFAULT ADMIN CREATED")
            print("=" * 70)
            print(f"  Email:    {DEFAULT_ADMIN_EMAIL}")
            print(f"  Password: {DEFAULT_ADMIN_PASSWORD}")
            print(f"  Name:     {DEFAULT_ADMIN_NAME}")
            print("=" * 70)
            print("⚠️  IMPORTANT: Change the default password after first login!")
            print("=" * 70 + "\n")
        else:
            print(f"[Admin] Found {admin_count} admin(s) in database. Skipping default admin creation.")

    except Exception as e:
        print(f"[Admin] Error seeding default admin: {e}")
