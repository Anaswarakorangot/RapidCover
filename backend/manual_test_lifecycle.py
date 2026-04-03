"""
Test script for policy lifecycle features (4, 5, 6).
Run: python test_lifecycle.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

db_path = Path(__file__).parent / "rapidcover.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current policies
print("=" * 60)
print("CURRENT POLICIES")
print("=" * 60)
cursor.execute('SELECT id, partner_id, tier, status, expires_at, is_active FROM policies ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
if not rows:
    print("No policies found. Create a policy first via the UI.")
    conn.close()
    exit(1)

print(f"{'ID':<4} {'Partner':<8} {'Tier':<10} {'Status':<12} {'Expires At':<25} {'Active'}")
print("-" * 70)
for row in rows:
    print(f"{row[0]:<4} {row[1]:<8} {row[2]:<10} {row[3]:<12} {str(row[4]):<25} {row[5]}")

# Get the most recent active policy
cursor.execute('SELECT id FROM policies WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
result = cursor.fetchone()
if not result:
    print("\nNo active policy found. Create one first.")
    conn.close()
    exit(1)

policy_id = result[0]
print(f"\nUsing policy ID: {policy_id}")

print("\n" + "=" * 60)
print("TEST MENU")
print("=" * 60)
print("1. Set policy to expire in 1 day (test RENEWAL)")
print("2. Set policy to expired 12 hours ago (test GRACE PERIOD)")
print("3. Set policy to expired 3 days ago (test LAPSED)")
print("4. Reset policy to normal (7 days from now)")
print("0. Exit")

choice = input("\nEnter choice (1-4, 0 to exit): ").strip()

if choice == "1":
    new_expires = datetime.utcnow() + timedelta(days=1)
    cursor.execute("UPDATE policies SET expires_at = ?, status = 'ACTIVE' WHERE id = ?",
                   (new_expires.isoformat(), policy_id))
    conn.commit()
    print(f"\n✓ Policy {policy_id} set to expire in 1 day: {new_expires}")
    print("→ Refresh Policy page - you should see 'Renew' button")

elif choice == "2":
    new_expires = datetime.utcnow() - timedelta(hours=12)
    cursor.execute("UPDATE policies SET expires_at = ?, status = 'ACTIVE' WHERE id = ?",
                   (new_expires.isoformat(), policy_id))
    conn.commit()
    print(f"\n✓ Policy {policy_id} set to expired 12h ago: {new_expires}")
    print("→ Refresh Policy page - should show YELLOW 'Grace Period' badge")
    print("→ Should show 'Grace period: ~36h left'")
    print("→ Renew button should be available")

elif choice == "3":
    new_expires = datetime.utcnow() - timedelta(days=3)
    cursor.execute("UPDATE policies SET expires_at = ?, status = 'ACTIVE' WHERE id = ?",
                   (new_expires.isoformat(), policy_id))
    conn.commit()
    print(f"\n✓ Policy {policy_id} set to expired 3 days ago: {new_expires}")
    print("→ Refresh Policy page - should show RED 'Lapsed' badge")
    print("→ No Renew button (need to buy new policy)")

elif choice == "4":
    new_expires = datetime.utcnow() + timedelta(days=7)
    cursor.execute("UPDATE policies SET expires_at = ?, status = 'ACTIVE' WHERE id = ?",
                   (new_expires.isoformat(), policy_id))
    conn.commit()
    print(f"\n✓ Policy {policy_id} reset to expire in 7 days: {new_expires}")

elif choice == "0":
    print("Exiting...")
else:
    print("Invalid choice")

conn.close()
