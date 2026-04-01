"""
Policy certificate PDF generation service.

Generates professional insurance certificates with:
- Partner details
- Policy information
- Coverage details
- Covered triggers
"""

from io import BytesIO
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.policy import Policy, PolicyTier
from app.models.partner import Partner


# Covered triggers by tier
COVERED_TRIGGERS = {
    PolicyTier.FLEX: [
        "Heavy Rain/Flood (>55mm/hr)",
        "Extreme Heat (>43C)",
        "Dangerous AQI (>400)",
    ],
    PolicyTier.STANDARD: [
        "Heavy Rain/Flood (>55mm/hr)",
        "Extreme Heat (>43C)",
        "Dangerous AQI (>400)",
        "Civic Shutdown/Curfew/Bandh",
    ],
    PolicyTier.PRO: [
        "Heavy Rain/Flood (>55mm/hr)",
        "Extreme Heat (>43C)",
        "Dangerous AQI (>400)",
        "Civic Shutdown/Curfew/Bandh",
        "Dark Store Force Majeure Closure",
    ],
}


def get_certificate_filename(policy: Policy) -> str:
    """Generate a filename for the certificate PDF."""
    return f"RapidCover_Certificate_{policy.id}_{policy.tier.value}.pdf"


def generate_certificate_pdf(
    policy: Policy,
    partner: Partner,
    zone_name: Optional[str] = None,
) -> bytes:
    """
    Generate a professional insurance certificate PDF.

    Args:
        policy: The policy to generate certificate for
        partner: The partner owning the policy
        zone_name: Optional zone name for display

    Returns:
        PDF content as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1 * inch,
        leftMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1e40af'),
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.gray,
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#1e40af'),
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.gray,
    )

    elements = []

    # Header
    elements.append(Paragraph("RAPIDCOVER", title_style))
    elements.append(Paragraph("Insurance Certificate", subtitle_style))
    elements.append(Spacer(1, 20))

    # Certificate number box
    cert_number = f"Certificate No: RC-{policy.id:08d}"
    elements.append(Paragraph(f"<b>{cert_number}</b>", ParagraphStyle(
        'CertNo',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        borderColor=colors.HexColor('#1e40af'),
        borderWidth=1,
        borderPadding=10,
    )))
    elements.append(Spacer(1, 30))

    # Partner Details Section
    elements.append(Paragraph("INSURED PARTNER DETAILS", section_style))
    partner_data = [
        ["Name:", partner.name],
        ["Phone:", partner.phone],
        ["Platform:", partner.platform.upper() if partner.platform else "N/A"],
        ["Partner ID:", partner.partner_id or "N/A"],
        ["Operating Zone:", zone_name or "N/A"],
    ]
    partner_table = Table(partner_data, colWidths=[2 * inch, 4 * inch])
    partner_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    elements.append(partner_table)
    elements.append(Spacer(1, 20))

    # Policy Details Section
    elements.append(Paragraph("POLICY DETAILS", section_style))

    # Format dates
    starts_at = policy.starts_at.strftime("%d %B %Y, %I:%M %p") if policy.starts_at else "N/A"
    expires_at = policy.expires_at.strftime("%d %B %Y, %I:%M %p") if policy.expires_at else "N/A"

    policy_data = [
        ["Policy ID:", f"POL-{policy.id:06d}"],
        ["Plan Tier:", policy.tier.value.upper()],
        ["Weekly Premium:", f"Rs. {policy.weekly_premium:.2f}"],
        ["Coverage Period:", f"{starts_at} to {expires_at}"],
        ["Auto-Renewal:", "Enabled" if policy.auto_renew else "Disabled"],
    ]
    policy_table = Table(policy_data, colWidths=[2 * inch, 4 * inch])
    policy_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    elements.append(policy_table)
    elements.append(Spacer(1, 20))

    # Coverage Limits Section
    elements.append(Paragraph("COVERAGE LIMITS", section_style))
    coverage_data = [
        ["Maximum Daily Payout:", f"Rs. {policy.max_daily_payout:.2f}"],
        ["Maximum Days per Week:", f"{policy.max_days_per_week} days"],
        ["Maximum Weekly Payout:", f"Rs. {policy.max_daily_payout * policy.max_days_per_week:.2f}"],
    ]
    coverage_table = Table(coverage_data, colWidths=[2.5 * inch, 3.5 * inch])
    coverage_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f9ff')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1e40af')),
    ]))
    elements.append(coverage_table)
    elements.append(Spacer(1, 20))

    # Covered Triggers Section
    elements.append(Paragraph("COVERED TRIGGER EVENTS", section_style))
    triggers = COVERED_TRIGGERS.get(policy.tier, [])
    for i, trigger in enumerate(triggers, 1):
        elements.append(Paragraph(f"{i}. {trigger}", normal_style))
    elements.append(Spacer(1, 30))

    # Terms box
    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        alignment=TA_LEFT,
    )
    terms_text = """
    <b>Terms & Conditions:</b> This certificate confirms active parametric insurance coverage.
    Payouts are automatically triggered when covered events are detected in your operating zone.
    No claim forms required. All payouts are subject to daily and weekly limits.
    Coverage is valid only during the specified policy period.
    Grace period of 48 hours applies after expiry for renewal without coverage gap.
    """
    elements.append(Paragraph(terms_text, terms_style))
    elements.append(Spacer(1, 30))

    # Footer
    generated_at = datetime.utcnow().strftime("%d %B %Y at %I:%M %p UTC")
    elements.append(Paragraph(f"Certificate generated on {generated_at}", footer_style))
    elements.append(Paragraph("RapidCover - Parametric Income Insurance for Q-Commerce Partners", footer_style))
    elements.append(Paragraph("www.rapidcover.in | support@rapidcover.in", footer_style))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
