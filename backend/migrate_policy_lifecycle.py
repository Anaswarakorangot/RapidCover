"""
One-time migration script to add policy lifecycle columns.

Run this once to update the existing database:
    python migrate_policy_lifecycle.py

This adds:
- status column (PolicyStatus enum, default 'ACTIVE')
- grace_ends_at column (nullable datetime)
- renewed_from_id column (nullable foreign key to policies.id)
"""

import sqlite3
from pathlib import Path

# Find the database
db_path = Path(__file__).parent / "rapidcover.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    print("No migration needed - database will be created with new schema on first run.")
    exit(0)

print(f"Migrating database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(policies)")
existing_columns = {row[1] for row in cursor.fetchall()}
print(f"Existing columns: {existing_columns}")

migrations_run = 0

# Add status column if not exists
if "status" not in existing_columns:
    print("Adding 'status' column...")
    # Use UPPERCASE enum value to match SQLAlchemy Enum
    cursor.execute("ALTER TABLE policies ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
    migrations_run += 1
else:
    # Fix existing values - convert lowercase to uppercase
    print("Fixing status column values (lowercase -> uppercase)...")
    cursor.execute("UPDATE policies SET status = 'ACTIVE' WHERE status = 'active'")
    cursor.execute("UPDATE policies SET status = 'GRACE_PERIOD' WHERE status = 'grace_period'")
    cursor.execute("UPDATE policies SET status = 'LAPSED' WHERE status = 'lapsed'")
    cursor.execute("UPDATE policies SET status = 'CANCELLED' WHERE status = 'cancelled'")
    # Also set NULL values to ACTIVE
    cursor.execute("UPDATE policies SET status = 'ACTIVE' WHERE status IS NULL")
    migrations_run += 1

# Add grace_ends_at column if not exists
if "grace_ends_at" not in existing_columns:
    print("Adding 'grace_ends_at' column...")
    cursor.execute("ALTER TABLE policies ADD COLUMN grace_ends_at DATETIME")
    migrations_run += 1

# Add renewed_from_id column if not exists
if "renewed_from_id" not in existing_columns:
    print("Adding 'renewed_from_id' column...")
    cursor.execute("ALTER TABLE policies ADD COLUMN renewed_from_id INTEGER REFERENCES policies(id)")
    migrations_run += 1

conn.commit()

# Verify the fix
cursor.execute("SELECT id, status FROM policies")
rows = cursor.fetchall()
if rows:
    print(f"\nCurrent policy statuses:")
    for row in rows:
        print(f"  Policy {row[0]}: {row[1]}")

conn.close()

if migrations_run > 0:
    print(f"\nMigration complete!")
else:
    print("\nNo migration needed - all columns already exist.")
