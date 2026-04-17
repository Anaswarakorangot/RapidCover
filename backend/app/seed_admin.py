"""
Automatic admin seeding on startup.
Creates default admin user if none exists.
"""

from sqlalchemy.orm import Session
from app.models.admin import Admin
from app.database import get_db, engine, Base
from passlib.context import CryptContext
import os
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@rapidcover.in")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Admin User")


def seed_default_admin():
    """Create default admin if no admins exist."""
    try:
        db = next(get_db())

        # Check if any admin exists
        admin_count = db.query(Admin).count()

        if admin_count == 0:
            # No admins exist, create default admin
            hashed_password = pwd_context.hash(DEFAULT_ADMIN_PASSWORD)

            admin = Admin(
                email=DEFAULT_ADMIN_EMAIL.lower().strip(),
                hashed_password=hashed_password,
                full_name=DEFAULT_ADMIN_NAME,
                is_active=True,
                is_superadmin=True,
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            msg = (
                "\n" + "=" * 70 + "\n"
                "🔐 DEFAULT ADMIN CREATED\n"
                "=" * 70 + "\n"
                f"  Email:    {DEFAULT_ADMIN_EMAIL}\n"
                f"  Password: {DEFAULT_ADMIN_PASSWORD}\n"
                f"  Name:     {DEFAULT_ADMIN_NAME}\n"
                "=" * 70 + "\n"
                "⚠️  IMPORTANT: Change the default password after first login!\n"
                "=" * 70 + "\n"
            )
            print(msg)
            logger.info(f"Created default admin: {DEFAULT_ADMIN_EMAIL}")
        else:
            logger.info(f"Found {admin_count} admin(s) in database. Skipping default admin creation.")

    except Exception as e:
        logger.error(f"Error seeding default admin: {str(e)}", exc_info=True)


