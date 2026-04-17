"""
Device Fingerprinting Service for Fraud Detection
-------------------------------------------------

Generates unique device fingerprints from browser headers to detect:
- Multiple accounts from same device
- Account takeovers (device switches)
- Suspicious device patterns

Uses SHA-256 hashing of:
- User-Agent (browser + OS info)
- Accept-Language (user language preferences)
- Accept-Encoding (supported compression)
- IP Address (client network)

Production enhancement: Add canvas fingerprinting, WebGL, screen resolution via frontend.
"""

import hashlib
from typing import Optional
from fastapi import Request


def generate_device_fingerprint(request: Request) -> str:
    """
    Generate unique device fingerprint from browser headers.

    Args:
        request: FastAPI Request object with headers and client info

    Returns:
        16-character hex fingerprint (first 16 chars of SHA-256 hash)

    Example:
        >>> fingerprint = generate_device_fingerprint(request)
        >>> # Returns: "a3f5e7b9c2d1f8e4"
    """
    # Collect fingerprint components
    components = [
        request.headers.get("user-agent", "unknown"),
        request.headers.get("accept-language", ""),
        request.headers.get("accept-encoding", ""),
        request.client.host if request.client else "unknown",
    ]

    # Join and hash
    raw = "|".join(components)
    fingerprint_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # Return first 16 characters for readability
    return fingerprint_hash[:16]


def verify_device_consistency(
    current_fingerprint: str,
    registration_fingerprint: Optional[str]
) -> tuple[bool, str]:
    """
    Check if device fingerprint matches registration device.

    Args:
        current_fingerprint: Current device fingerprint
        registration_fingerprint: Fingerprint from partner registration

    Returns:
        Tuple of (is_consistent, reason_message)

    Fraud Detection Logic:
        - Same device → Low risk
        - Different device → Flag for review
        - Multiple rapid switches → High risk

    Example:
        >>> consistent, reason = verify_device_consistency("a3f5e7b9", "a3f5e7b9")
        >>> # Returns: (True, "Same device as registration")
    """
    if not registration_fingerprint:
        return (True, "No baseline fingerprint to compare (first login)")

    if current_fingerprint == registration_fingerprint:
        return (True, "Same device as registration")

    return (
        False,
        f"Device mismatch (current: {current_fingerprint[:8]}... vs registration: {registration_fingerprint[:8]}...)"
    )


def extract_device_info(request: Request) -> dict:
    """
    Extract human-readable device information for logging.

    Args:
        request: FastAPI Request object

    Returns:
        Dict with browser, OS, IP, language

    Example:
        >>> info = extract_device_info(request)
        >>> # Returns: {
        >>>     "browser": "Chrome 120.0.0.0",
        >>>     "os": "Windows 10",
        >>>     "ip": "192.168.1.100",
        >>>     "language": "en-US"
        >>> }
    """
    user_agent = request.headers.get("user-agent", "")
    language = request.headers.get("accept-language", "")
    ip_address = request.client.host if request.client else "unknown"

    # Simple UA parsing (production should use user-agents library)
    browser = "Unknown Browser"
    if "Chrome" in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser = "Safari"

    os = "Unknown OS"
    if "Windows" in user_agent:
        os = "Windows"
    elif "Mac OS" in user_agent:
        os = "macOS"
    elif "Android" in user_agent:
        os = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        os = "iOS"
    elif "Linux" in user_agent:
        os = "Linux"

    return {
        "browser": browser,
        "os": os,
        "ip": ip_address,
        "language": language.split(",")[0] if language else "unknown",
        "user_agent": user_agent,
    }
