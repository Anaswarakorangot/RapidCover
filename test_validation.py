
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath('backend'))

from app.services.partner_validation import validate_partner_id

# Test BLK format
print("Testing BLK123456 for blinkit:")
print(validate_partner_id("BLK123456", "blinkit"))

# Test BKT format (expected to fail in current code)
print("\nTesting BKT123456 for blinkit:")
print(validate_partner_id("BKT123456", "blinkit"))
