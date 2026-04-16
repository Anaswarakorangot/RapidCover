import sqlite3

def add_columns():
    conn = sqlite3.connect('rapidcover.db')
    cursor = conn.cursor()
    columns_to_add = [
        ('bank_name', 'VARCHAR(100)'),
        ('account_number', 'VARCHAR(30)'),
        ('ifsc_code', 'VARCHAR(20)'),
        ('kyc', 'JSON')
    ]
    
    cursor.execute('PRAGMA table_info(partners);')
    columns = [row[1] for row in cursor.fetchall()]
    
    for col_name, col_type in columns_to_add:
        if col_name not in columns:
            print(f"Adding column {col_name} to partners table...")
            cursor.execute(f"ALTER TABLE partners ADD COLUMN {col_name} {col_type};")
            # If KYC, initialize with JSON
            if col_name == 'kyc':
                cursor.execute("UPDATE partners SET kyc = '{\"aadhaar_number\": null, \"pan_number\": null, \"kyc_status\": \"skipped\"}';")
            
    conn.commit()
    conn.close()
    print("Done checking and adding columns.")

if __name__ == '__main__':
    add_columns()
