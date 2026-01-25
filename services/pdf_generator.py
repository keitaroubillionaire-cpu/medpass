"""
PDF generation service using ReportLab.
Generates A4 summary prints for lectures.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm

# Try to register Japanese fonts
JAPANESE_FONT = None
FONT_PATHS = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
]

for font_path in FONT_PATHS:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
            JAPANESE_FONT = "JapaneseFont"
            break
        except Exception:
            continue

# Fallback to Helvetica if no Japanese font found
if not JAPANESE_FONT:
    JAPANESE_FONT = "Helvetica"


def get_styles():
    """Get paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='JapaneseTitle',
        fontName=JAPANESE_FONT,
        fontSize=16,
        leading=20,
        spaceAfter=10,
        alignment=1  # Center
    ))

    styles.add(ParagraphStyle(
        name='JapaneseHeading',
        fontName=JAPANESE_FONT,
        fontSize=12,
        leading=16,
        spaceAfter=6,
        spaceBefore=10,
        textColor=colors.darkblue
    ))

    styles.add(ParagraphStyle(
        name='JapaneseBody',
        fontName=JAPANESE_FONT,
        fontSize=10,
        leading=14,
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        name='JapaneseSmall',
        fontName=JAPANESE_FONT,
        fontSize=8,
        leading=10,
        textColor=colors.gray
    ))

    return styles


def generate_lecture_pdf(lecture, cards, output_path: str, max_pages: int = 2):
    """
    Generate a PDF summary for a lecture.

    Args:
        lecture: Lecture model instance
        cards: List of Card model instances
        output_path: Path to save the PDF
        max_pages: Maximum number of pages (default 2)
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )

    styles = get_styles()
    story = []

    # Title
    title = Paragraph(f"{lecture.title}", styles['JapaneseTitle'])
    story.append(title)

    # Subject info
    if lecture.subject:
        subject_info = Paragraph(
            f"科目: {lecture.subject.name} | スライド数: {lecture.slide_count}枚",
            styles['JapaneseSmall']
        )
        story.append(subject_info)

    story.append(Spacer(1, 10 * mm))

    # Cards and their questions
    for i, card in enumerate(cards, 1):
        # Card header with importance indicator
        importance_stars = "★" * card.importance + "☆" * (3 - card.importance)
        card_title = Paragraph(
            f"{i}. {card.theme} [{importance_stars}]",
            styles['JapaneseHeading']
        )
        story.append(card_title)

        # Card summary
        if card.summary:
            summary = Paragraph(card.summary, styles['JapaneseBody'])
            story.append(summary)

        # Questions for this card
        if card.questions:
            story.append(Spacer(1, 3 * mm))

            for j, question in enumerate(card.questions, 1):
                # Question text
                q_text = Paragraph(
                    f"Q{j}: {question.question_text}",
                    styles['JapaneseBody']
                )
                story.append(q_text)

                # Answer (200 chars)
                if question.answer_200:
                    answer = Paragraph(
                        f"A: {question.answer_200}",
                        styles['JapaneseBody']
                    )
                    story.append(answer)

                # Past exam indicator
                if question.is_past_exam:
                    past_exam = Paragraph("【過去問】", styles['JapaneseSmall'])
                    story.append(past_exam)

                story.append(Spacer(1, 2 * mm))

        story.append(Spacer(1, 5 * mm))

    # Build PDF
    doc.build(story)

    return output_path
