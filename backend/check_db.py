import sqlite3
from datetime import datetime

def check_db():
    conn = sqlite3.connect('rapidcover.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Partners ---")
    cursor.execute("SELECT id, name, phone, zone_id FROM partners")
    for row in cursor.fetchall():
        print(dict(row))
        
    print("\n--- Policies ---")
    cursor.execute("SELECT id, partner_id, tier, is_active, starts_at, expires_at FROM policies")
    for row in cursor.fetchall():
        print(dict(row))
        
    print("\n--- Claims ---")
    cursor.execute("SELECT id, policy_id, amount, status, fraud_score FROM claims")
    for row in cursor.fetchall():
        print(dict(row))
        
    print("\n--- Zones ---")
    cursor.execute("SELECT id, name, code FROM zones LIMIT 5")
    for row in cursor.fetchall():
        print(dict(row))
    
    conn.close()

if __name__ == "__main__":
    check_db()
