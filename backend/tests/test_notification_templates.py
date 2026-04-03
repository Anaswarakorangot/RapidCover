"""
Tests for multilingual notification templates.
"""

import pytest
from app.models.trigger_event import TriggerType


class TestNotificationTemplates:
    """Tests for notification template service."""

    def test_english_templates_complete(self):
        """Test that all English templates are defined."""
        from app.services.notification_templates import NOTIFICATION_TEMPLATES

        required_types = [
            "claim_created",
            "claim_approved",
            "claim_paid",
            "claim_rejected",
            "trigger_forecast",
            "policy_expiring",
            "policy_renewed",
            "zone_reassignment_proposed",
            "zone_reassignment_accepted",
        ]

        en_templates = NOTIFICATION_TEMPLATES.get("en", {})

        for notification_type in required_types:
            assert notification_type in en_templates, f"Missing English template: {notification_type}"
            assert "title" in en_templates[notification_type]
            assert "body" in en_templates[notification_type]

    def test_hindi_templates_complete(self):
        """Test that all Hindi templates are defined."""
        from app.services.notification_templates import NOTIFICATION_TEMPLATES

        required_types = [
            "claim_created",
            "claim_approved",
            "claim_paid",
            "claim_rejected",
            "trigger_forecast",
            "policy_expiring",
            "policy_renewed",
            "zone_reassignment_proposed",
            "zone_reassignment_accepted",
        ]

        hi_templates = NOTIFICATION_TEMPLATES.get("hi", {})

        for notification_type in required_types:
            assert notification_type in hi_templates, f"Missing Hindi template: {notification_type}"
            assert "title" in hi_templates[notification_type]
            assert "body" in hi_templates[notification_type]

    def test_notification_uses_partner_language_pref(self):
        """Test that notification uses partner's language preference."""
        from app.services.notification_templates import render_notification

        # Render same notification in English and Hindi
        en_result = render_notification(
            "claim_created",
            language="en",
            amount=250,
            trigger_type=TriggerType.RAIN,
        )

        hi_result = render_notification(
            "claim_created",
            language="hi",
            amount=250,
            trigger_type=TriggerType.RAIN,
        )

        # Titles should be different
        assert "Claim Created" in en_result["title"]
        assert "दावा बनाया गया" in hi_result["title"]

        # Both should have amount in body
        assert "250" in en_result["body"]
        assert "250" in hi_result["body"]

    def test_notification_falls_back_to_english(self):
        """Test fallback to English for unsupported language."""
        from app.services.notification_templates import get_template, render_notification

        # Try to get template for unsupported language
        template = get_template("claim_created", "fr")  # French not supported

        # Should fall back to English
        assert "Claim Created" in template["title"]

        # Same for render
        result = render_notification("claim_created", "fr", amount=100, trigger_type=TriggerType.HEAT)
        assert "Claim Created" in result["title"]

    def test_preview_endpoint_renders_sample(self):
        """Test that preview endpoint renders sample data."""
        from app.services.notification_templates import preview_notification

        result = preview_notification("claim_created", "en")

        assert result["language"] == "en"
        assert result["type"] == "claim_created"
        assert "title" in result
        assert "body" in result
        assert "sample_rendered" in result

        # Sample rendered should have actual values (not placeholders)
        assert "{amount}" not in result["sample_rendered"]["body"]
        assert "{trigger_type}" not in result["sample_rendered"]["body"]

    def test_trigger_type_labels_english(self):
        """Test English trigger type labels."""
        from app.services.notification_templates import get_trigger_label

        assert get_trigger_label(TriggerType.RAIN, "en") == "Heavy Rain"
        assert get_trigger_label(TriggerType.HEAT, "en") == "Extreme Heat"
        assert get_trigger_label(TriggerType.AQI, "en") == "High AQI"
        assert get_trigger_label(TriggerType.SHUTDOWN, "en") == "Civic Shutdown"
        assert get_trigger_label(TriggerType.CLOSURE, "en") == "Store Closure"

    def test_trigger_type_labels_hindi(self):
        """Test Hindi trigger type labels."""
        from app.services.notification_templates import get_trigger_label

        assert get_trigger_label(TriggerType.RAIN, "hi") == "भारी बारिश"
        assert get_trigger_label(TriggerType.HEAT, "hi") == "अत्यधिक गर्मी"
        assert get_trigger_label(TriggerType.AQI, "hi") == "उच्च AQI"
        assert get_trigger_label(TriggerType.SHUTDOWN, "hi") == "नागरिक शटडाउन"
        assert get_trigger_label(TriggerType.CLOSURE, "hi") == "स्टोर बंद"

    def test_render_with_missing_variables(self):
        """Test that rendering handles missing template variables gracefully."""
        from app.services.notification_templates import render_notification

        # Don't provide all required variables
        result = render_notification("claim_created", "en")

        # Should not crash, should return template with unfilled placeholders or defaults
        assert "title" in result
        assert "body" in result

    def test_get_available_notification_types(self):
        """Test getting list of available notification types."""
        from app.services.notification_templates import get_available_notification_types

        types = get_available_notification_types()

        assert len(types) >= 9  # At least the 9 we defined
        assert "claim_created" in types
        assert "claim_approved" in types
        assert "claim_paid" in types
        assert "claim_rejected" in types

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        from app.services.notification_templates import get_supported_languages

        languages = get_supported_languages()

        assert "en" in languages
        assert "hi" in languages

    def test_template_variables_are_documented(self):
        """Test that preview includes available variables."""
        from app.services.notification_templates import preview_notification

        result = preview_notification("claim_created", "en")

        assert "available_variables" in result
        assert "amount" in result["available_variables"]
        assert "trigger_type" in result["available_variables"]

    def test_hindi_claim_paid_has_upi_ref(self):
        """Test that Hindi claim_paid template includes UPI reference."""
        from app.services.notification_templates import render_notification

        result = render_notification(
            "claim_paid",
            language="hi",
            amount=500,
            upi_ref="UPI123456789",
        )

        assert "UPI123456789" in result["body"]
        assert "500" in result["body"]

    def test_language_normalization(self):
        """Test that language codes are normalized."""
        from app.services.notification_templates import get_template

        # Different formats should all work
        assert get_template("claim_created", "EN")["title"] == get_template("claim_created", "en")["title"]
        assert get_template("claim_created", "HI")["title"] == get_template("claim_created", "hi")["title"]
        assert get_template("claim_created", "hindi")["title"] == get_template("claim_created", "hi")["title"]
