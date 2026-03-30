"""
Mock Partner ID Validation Service

Validates partner IDs against mock Zepto/Blinkit records.
In production, this would call actual platform APIs.
"""

import re
from typing import Dict


# Partner ID patterns by platform
PLATFORM_PATTERNS = {
    "zepto": r"^ZPT\d{6}$",
    "blinkit": r"^BLK\d{6}$",
}


def validate_partner_id(partner_id: str, platform: str) -> Dict[str, any]:
    """
    Validate a partner ID against platform records (mock).

    Args:
        partner_id: The partner ID to validate (e.g., ZPT123456)
        platform: The platform name (zepto or blinkit)

    Returns:
        {"valid": bool, "message": str}
    """
    platform = platform.lower()

    # Check platform is supported
    if platform not in PLATFORM_PATTERNS:
        return {
            "valid": False,
            "message": f"Unsupported platform: {platform}"
        }

    # Check format matches platform pattern
    pattern = PLATFORM_PATTERNS[platform]
    if not re.match(pattern, partner_id):
        expected_prefix = "ZPT" if platform == "zepto" else "BLK"
        return {
            "valid": False,
            "message": f"Invalid format. Expected {expected_prefix} followed by 6 digits"
        }

    # Mock validation rules based on ID suffix
    suffix = partner_id[-3:]

    if suffix == "000":
        return {
            "valid": False,
            "message": f"Partner ID not found in {platform.capitalize()} records"
        }

    if suffix == "999":
        return {
            "valid": False,
            "message": f"Partner account suspended in {platform.capitalize()}"
        }

    # All other valid formats are verified
    return {
        "valid": True,
        "message": f"Partner ID verified with {platform.capitalize()}"
    }
