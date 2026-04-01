"""Check current policy state for auto-renewal eligibility."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

db_path = Path(__file__).parent / "rapidcover.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    SELECT id, partner_id, tier, status, auto_renew, is_active, expires_at
    FROM policies
    ORDER BY id DESC LIMIT 5
''')
rows = cursor.fetchall()

print("=" * 80)
print("CURRENT POLICIES")
print("=" * 80)
print(f"{'ID':<4} {'Partner':<8} {'Tier':<10} {'Status':<12} {'AutoRenew':<10} {'Active':<7} {'Expires At'}")
print("-" * 80)

now = datetime.utcnow()
renewal_window = now + timedelta(days=1)
grace_cutoff = now - timedelta(hours=48)

for row in rows:
    policy_id, partner_id, tier, status, auto_renew, is_active, expires_at = row
    print(f"{policy_id:<4} {partner_id:<8} {tier:<10} {status:<12} {str(bool(auto_renew)):<10} {str(bool(is_active)):<7} {expires_at}")

print("\n" + "=" * 80)
print("AUTO-RENEWAL ELIGIBILITY CHECK")
print("=" * 80)
print(f"Current time:     {now}")
print(f"Renewal window:   expires_at <= {renewal_window} (within 24h)")
print(f"Grace cutoff:     expires_at > {grace_cutoff} (not lapsed)")

print("\nCriteria for auto-renewal:")
print("  1. auto_renew = True")
print("  2. is_active = True")
print("  3. expires_at > grace_cutoff (not lapsed)")
print("  4. expires_at <= renewal_window (expiring soon)")

# Check eligible
cursor.execute('''
    SELECT id, auto_renew, is_active, expires_at
    FROM policies
    WHERE auto_renew = 1 AND is_active = 1
''')
candidates = cursor.fetchall()

print(f"\nPolicies with auto_renew=True and is_active=True: {len(candidates)}")

for row in candidates:
    policy_id, auto_renew, is_active, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None

    if expires_at:
        in_window = expires_at <= renewal_window
        not_lapsed = expires_at > grace_cutoff
        eligible = in_window and not_lapsed

        print(f"\n  Policy {policy_id}:")
        print(f"    expires_at: {expires_at}")
        print(f"    in_renewal_window (<=24h): {in_window}")
        print(f"    not_lapsed (>48h ago): {not_lapsed}")
        print(f"    ELIGIBLE: {eligible}")

conn.close()
