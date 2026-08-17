import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from sqlalchemy.orm import Session

from backend.app.models.sql_models import (
    User,
    PalmReading,
    TarotReading,
    AIInterpretation,
    GuidanceScore,
    Recommendation,
)

REPORTS_DIR = os.path.join("backend", "generated_reports")


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AetheriaTitle", fontSize=20, leading=24, spaceAfter=6,
        textColor=colors.HexColor("#3B2A5E"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=14, leading=18, spaceBefore=16, spaceAfter=8,
        textColor=colors.HexColor("#5C3A99"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="Body", fontSize=10.5, leading=15, textColor=colors.HexColor("#222222"),
    ))
    styles.add(ParagraphStyle(
        name="Muted", fontSize=9, leading=12, textColor=colors.HexColor("#777777"),
    ))
    return styles


def generate_user_report(db: Session, user: User) -> str:
    """
    Build a PDF report summarizing a user's palm readings, tarot readings,
    AI interpretations, guidance scores, and recommendations.
    Returns the absolute file path of the generated PDF.
    """
    _ensure_reports_dir()
    styles = _build_styles()

    filename = f"aetheria_report_user_{user.id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        file_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    story = []

    story.append(Paragraph("Aetheria — Palmistry &amp; Tarot Intelligence Report", styles["AetheriaTitle"]))
    story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}", styles["Muted"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#DDDDDD"), spaceBefore=10, spaceAfter=14))

    story.append(Paragraph("User Profile", styles["SectionHeading"]))
    user_table_data = [
        ["Name", user.full_name],
        ["Email", user.email],
        ["Role", user.role],
        ["Account Created", user.created_at.strftime("%d %b %Y") if user.created_at else "N/A"],
    ]
    user_table = Table(user_table_data, colWidths=[4 * cm, 11 * cm])
    user_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
    ]))
    story.append(user_table)

    palm_readings = (
        db.query(PalmReading).filter(PalmReading.user_id == user.id)
        .order_by(PalmReading.created_at.desc()).all()
    )
    story.append(Paragraph("Palm Readings", styles["SectionHeading"]))
    if not palm_readings:
        story.append(Paragraph("No palm readings on record.", styles["Muted"]))
    else:
        header_style = ParagraphStyle(name="TableHeader", fontSize=9.5, textColor=colors.white, fontName="Helvetica-Bold")
        rows = [[Paragraph(h, header_style) for h in ["Date", "Palm Shape", "Finger Structure", "Overall Confidence"]]]
        for pr in palm_readings:
            rows.append([
                pr.created_at.strftime("%d %b %Y") if pr.created_at else "N/A",
                pr.palm_shape or "-",
                pr.finger_structure or "-",
                f"{pr.overall_conf * 100:.1f}%",
            ])
        table = Table(rows, colWidths=[3 * cm, 3.5 * cm, 4 * cm, 4.5 * cm])
        table.setStyle(_default_table_style())
        story.append(table)

    tarot_readings = (
        db.query(TarotReading).filter(TarotReading.user_id == user.id)
        .order_by(TarotReading.created_at.desc()).all()
    )
    story.append(Paragraph("Tarot Readings", styles["SectionHeading"]))
    if not tarot_readings:
        story.append(Paragraph("No tarot readings on record.", styles["Muted"]))
    else:
        for reading in tarot_readings:
            story.append(Paragraph(
                f"<b>{reading.spread_name.title()} Spread</b> — "
                f"Focus: {reading.focus_intent or 'General'} "
                f"({reading.created_at.strftime('%d %b %Y') if reading.created_at else 'N/A'})",
                styles["Body"],
            ))
            card_rows = [["Position", "Card", "Orientation"]]
            for rc in reading.cards_drawn:
                card_rows.append([
                    rc.position_name,
                    rc.card.name if rc.card else "Unknown",
                    "Reversed" if rc.is_reversed else "Upright",
                ])
            if len(card_rows) > 1:
                card_table = Table(card_rows, colWidths=[4 * cm, 6 * cm, 4 * cm])
                card_table.setStyle(_default_table_style())
                story.append(card_table)
            story.append(Spacer(1, 8))

    story.append(Paragraph("AI Interpretations &amp; Guidance Scores", styles["SectionHeading"]))
    reading_refs = (
        [("palm", pr.id) for pr in palm_readings] + [("tarot", tr.id) for tr in tarot_readings]
    )
    found_any = False
    for reading_type, reading_id in reading_refs:
        interpretation = (
            db.query(AIInterpretation)
            .filter(AIInterpretation.reading_type == reading_type, AIInterpretation.reading_id == reading_id)
            .first()
        )
        score = (
            db.query(GuidanceScore)
            .filter(GuidanceScore.reading_type == reading_type, GuidanceScore.reading_id == reading_id)
            .first()
        )
        if not interpretation and not score:
            continue
        found_any = True
        story.append(Paragraph(f"<b>{reading_type.title()} Reading #{reading_id}</b>", styles["Body"]))
        if interpretation:
            story.append(Paragraph(interpretation.summary, styles["Body"]))
            story.append(Paragraph(f"<i>{interpretation.safety_disclaimer}</i>", styles["Muted"]))
        if score:
            story.append(Paragraph(f"Guidance Score: {score.final_score:.2f} / 100", styles["Muted"]))
        story.append(Spacer(1, 8))
    if not found_any:
        story.append(Paragraph("No AI interpretations recorded yet.", styles["Muted"]))

    recommendations = (
        db.query(Recommendation).filter(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at.desc()).all()
    )
    story.append(Paragraph("Recommendations", styles["SectionHeading"]))
    if not recommendations:
        story.append(Paragraph("No recommendations generated yet.", styles["Muted"]))
    else:
        rows = [["Category", "Title", "Status"]]
        for rec in recommendations:
            rows.append([rec.category.title(), rec.title, "Completed" if rec.is_completed else "Pending"])
        table = Table(rows, colWidths=[3.5 * cm, 8 * cm, 3.5 * cm])
        table.setStyle(_default_table_style())
        story.append(table)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#DDDDDD")))
    story.append(Paragraph(
        "This report is generated for entertainment and self-reflection purposes only "
        "and does not constitute professional, medical, legal, or financial advice.",
        styles["Muted"],
    ))

    doc.build(story)
    return os.path.abspath(file_path)


def _default_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5C3A99")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F5FB")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ])