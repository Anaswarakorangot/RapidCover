"""
Multilingual notification templates for RapidCover.

Supports English (en) and Hindi (hi) with fallback to English.
"""

from typing import Optional
from app.models.trigger_event import TriggerType


# Notification templates by language
NOTIFICATION_TEMPLATES = {
    "en": {
        "claim_created": {
            "title": "Claim Created - RapidCover",
            "body": "A claim of Rs. {amount} has been created for {trigger_type}.",
        },
        "claim_approved": {
            "title": "Claim Approved! - RapidCover",
            "body": "Your claim of Rs. {amount} has been approved! Payment coming soon.",
        },
        "claim_paid": {
            "title": "Payment Received! - RapidCover",
            "body": "💰 Rs. {amount} has been credited to your UPI account. Ref: {upi_ref}",
        },
        "claim_rejected": {
            "title": "Claim Update - RapidCover",
            "body": "Your claim of Rs. {amount} could not be processed. Contact support for details.",
        },
        "trigger_forecast": {
            "title": "Weather Alert - RapidCover",
            "body": "{trigger_type} predicted in your area. Your coverage is active.",
        },
        "policy_expiring": {
            "title": "Policy Expiring - RapidCover",
            "body": "Your policy expires in {days} days. Renew now to stay protected.",
        },
        "policy_renewed": {
            "title": "Policy Renewed - RapidCover",
            "body": "Your policy has been renewed for Rs. {amount}/week. Stay safe!",
        },
        "zone_reassignment_proposed": {
            "title": "Zone Change Proposed - RapidCover",
            "body": "You've been proposed for reassignment to {zone_name}. Accept within 24 hours.",
        },
        "zone_reassignment_accepted": {
            "title": "Zone Changed - RapidCover",
            "body": "You are now covered in {zone_name}. Premium adjusted by Rs. {adjustment}.",
        },
    },
    "hi": {
        "claim_created": {
            "title": "दावा बनाया गया - RapidCover",
            "body": "Rs. {amount} का दावा {trigger_type} के लिए बनाया गया है।",
        },
        "claim_approved": {
            "title": "दावा स्वीकृत! - RapidCover",
            "body": "Rs. {amount} का आपका दावा स्वीकृत हो गया है! भुगतान जल्द आ रहा है।",
        },
        "claim_paid": {
            "title": "भुगतान प्राप्त! - RapidCover",
            "body": "💰 Rs. {amount} आपके UPI खाते में जमा हो गए हैं। Ref: {upi_ref}",
        },
        "claim_rejected": {
            "title": "दावा अपडेट - RapidCover",
            "body": "Rs. {amount} का आपका दावा प्रोसेस नहीं हो सका। विवरण के लिए सहायता से संपर्क करें।",
        },
        "trigger_forecast": {
            "title": "मौसम चेतावनी - RapidCover",
            "body": "आपके क्षेत्र में {trigger_type} की संभावना है। आपका कवरेज सक्रिय है।",
        },
        "policy_expiring": {
            "title": "पॉलिसी समाप्त हो रही है - RapidCover",
            "body": "आपकी पॉलिसी {days} दिनों में समाप्त हो रही है। सुरक्षित रहने के लिए अभी नवीनीकृत करें।",
        },
        "policy_renewed": {
            "title": "पॉलिसी नवीनीकृत - RapidCover",
            "body": "आपकी पॉलिसी Rs. {amount}/सप्ताह के लिए नवीनीकृत हो गई है। सुरक्षित रहें!",
        },
        "zone_reassignment_proposed": {
            "title": "ज़ोन परिवर्तन प्रस्तावित - RapidCover",
            "body": "आपको {zone_name} में स्थानांतरित करने का प्रस्ताव है। 24 घंटे में स्वीकार करें।",
        },
        "zone_reassignment_accepted": {
            "title": "ज़ोन बदल गया - RapidCover",
            "body": "अब आप {zone_name} में कवर हैं। प्रीमियम Rs. {adjustment} से समायोजित।",
        },
    },
}

# Trigger type labels by language
TRIGGER_TYPE_LABELS = {
    "en": {
        TriggerType.RAIN: "Heavy Rain",
        TriggerType.HEAT: "Extreme Heat",
        TriggerType.AQI: "High AQI",
        TriggerType.SHUTDOWN: "Civic Shutdown",
        TriggerType.CLOSURE: "Store Closure",
        "rain": "Heavy Rain",
        "heat": "Extreme Heat",
        "aqi": "High AQI",
        "shutdown": "Civic Shutdown",
        "closure": "Store Closure",
    },
    "hi": {
        TriggerType.RAIN: "भारी बारिश",
        TriggerType.HEAT: "अत्यधिक गर्मी",
        TriggerType.AQI: "उच्च AQI",
        TriggerType.SHUTDOWN: "नागरिक शटडाउन",
        TriggerType.CLOSURE: "स्टोर बंद",
        "rain": "भारी बारिश",
        "heat": "अत्यधिक गर्मी",
        "aqi": "उच्च AQI",
        "shutdown": "नागरिक शटडाउन",
        "closure": "स्टोर बंद",
    },
}

# Default language fallback
DEFAULT_LANGUAGE = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "hi"]


def get_template(
    notification_type: str,
    language: str = "en",
) -> dict:
    """
    Get notification template for a given type and language.

    Falls back to English if language not found or template missing.

    Args:
        notification_type: Type of notification (claim_created, claim_approved, etc.)
        language: Language code (en, hi)

    Returns:
        Dict with 'title' and 'body' template strings
    """
    # Normalize language code
    lang = language.lower()[:2] if language else DEFAULT_LANGUAGE

    # Try requested language
    if lang in NOTIFICATION_TEMPLATES:
        templates = NOTIFICATION_TEMPLATES[lang]
        if notification_type in templates:
            return templates[notification_type]

    # Fallback to English
    if DEFAULT_LANGUAGE in NOTIFICATION_TEMPLATES:
        templates = NOTIFICATION_TEMPLATES[DEFAULT_LANGUAGE]
        if notification_type in templates:
            return templates[notification_type]

    # Ultimate fallback
    return {
        "title": "RapidCover Notification",
        "body": "You have a new notification.",
    }


def get_trigger_label(
    trigger_type,
    language: str = "en",
) -> str:
    """
    Get localized trigger type label.

    Args:
        trigger_type: TriggerType enum or string
        language: Language code

    Returns:
        Localized trigger label string
    """
    lang = language.lower()[:2] if language else DEFAULT_LANGUAGE

    # Try requested language
    if lang in TRIGGER_TYPE_LABELS:
        labels = TRIGGER_TYPE_LABELS[lang]
        if trigger_type in labels:
            return labels[trigger_type]

    # Fallback to English
    if DEFAULT_LANGUAGE in TRIGGER_TYPE_LABELS:
        labels = TRIGGER_TYPE_LABELS[DEFAULT_LANGUAGE]
        if trigger_type in labels:
            return labels[trigger_type]

    # Ultimate fallback
    return str(trigger_type).replace("_", " ").title()


def render_notification(
    notification_type: str,
    language: str = "en",
    **kwargs,
) -> dict:
    """
    Render a notification with template variables filled in.

    Args:
        notification_type: Type of notification
        language: Language code
        **kwargs: Template variables (amount, trigger_type, upi_ref, etc.)

    Returns:
        Dict with rendered 'title' and 'body' strings
    """
    template = get_template(notification_type, language)

    # If trigger_type is provided, convert to localized label
    if "trigger_type" in kwargs:
        trigger_type = kwargs["trigger_type"]
        kwargs["trigger_type"] = get_trigger_label(trigger_type, language)

    # Safely format templates
    try:
        title = template["title"].format(**kwargs) if template.get("title") else "RapidCover"
    except KeyError:
        title = template.get("title", "RapidCover")

    try:
        body = template["body"].format(**kwargs) if template.get("body") else ""
    except KeyError:
        body = template.get("body", "")

    return {
        "title": title,
        "body": body,
        "language_used": language,
    }


def preview_notification(
    notification_type: str,
    language: str = "en",
) -> dict:
    """
    Preview a notification template with sample data.

    Args:
        notification_type: Type of notification
        language: Language code

    Returns:
        Dict with template, sample rendered version, and metadata
    """
    template = get_template(notification_type, language)

    # Sample data for preview
    sample_data = {
        "amount": 250,
        "trigger_type": TriggerType.RAIN,
        "upi_ref": "UPI202604031234567890",
        "days": 3,
        "zone_name": "Koramangala",
        "adjustment": 15,
    }

    rendered = render_notification(notification_type, language, **sample_data)

    return {
        "language": language,
        "type": notification_type,
        "title": template.get("title", ""),
        "body": template.get("body", ""),
        "sample_rendered": {
            "title": rendered["title"],
            "body": rendered["body"],
        },
        "available_variables": list(sample_data.keys()),
    }


def get_available_notification_types() -> list[str]:
    """Return list of available notification types."""
    return list(NOTIFICATION_TEMPLATES.get(DEFAULT_LANGUAGE, {}).keys())


def get_supported_languages() -> list[str]:
    """Return list of supported language codes."""
    return SUPPORTED_LANGUAGES
