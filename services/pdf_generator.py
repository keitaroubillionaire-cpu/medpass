"""
PDF generation service using ReportLab.
Generates A4 summary prints for lectures (max 2 pages).
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_HEIGHT = PAGE_HEIGHT - 2 * MARGIN

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


def get_styles(scale: float = 1.0):
    """
    Get paragraph styles for the PDF.

    Args:
        scale: Font size scale factor (1.0 = normal, 0.8 = compact)
    """
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='JapaneseTitle',
        fontName=JAPANESE_FONT,
        fontSize=int(16 * scale),
        leading=int(20 * scale),
        spaceAfter=int(8 * scale),
        alignment=1  # Center
    ))

    styles.add(ParagraphStyle(
        name='JapaneseHeading',
        fontName=JAPANESE_FONT,
        fontSize=int(11 * scale),
        leading=int(14 * scale),
        spaceAfter=int(4 * scale),
        spaceBefore=int(8 * scale),
        textColor=colors.darkblue
    ))

    styles.add(ParagraphStyle(
        name='JapaneseBody',
        fontName=JAPANESE_FONT,
        fontSize=int(9 * scale),
        leading=int(12 * scale),
        spaceAfter=int(3 * scale)
    ))

    styles.add(ParagraphStyle(
        name='JapaneseSmall',
        fontName=JAPANESE_FONT,
        fontSize=int(7 * scale),
        leading=int(9 * scale),
        textColor=colors.gray
    ))

    return styles


def estimate_content_size(cards):
    """
    Estimate the content size to determine scale factor.
    Returns approximate line count.
    """
    lines = 3  # Title + subject info + spacer

    for card in cards:
        lines += 2  # Card title + spacer
        if card.summary:
            # Estimate lines for summary (about 40 chars per line)
            lines += max(1, len(card.summary) // 40 + 1)

        for question in card.questions:
            lines += 1  # Question
            if question.answer_200:
                lines += max(1, len(question.answer_200) // 40 + 1)
            if question.is_past_exam:
                lines += 1
            lines += 1  # Spacer

        lines += 1  # Card spacer

    return lines


def select_content_for_pages(cards, max_pages: int = 2, scale: float = 1.0):
    """
    Select cards and questions that fit within max_pages.
    Prioritizes by importance.

    Returns:
        Tuple of (selected_cards, truncated: bool, omitted_count: int)
    """
    # Estimate lines per page (approximately)
    lines_per_page = int(45 * scale)  # Adjusted for scale
    max_lines = lines_per_page * max_pages

    # Sort cards by importance (high to low)
    sorted_cards = sorted(cards, key=lambda c: c.importance, reverse=True)

    selected_cards = []
    current_lines = 3  # Header overhead
    omitted_count = 0
    truncated = False

    for card in sorted_cards:
        card_lines = 2  # Card title
        if card.summary:
            card_lines += max(1, len(card.summary) // 40 + 1)

        # Count question lines
        questions_to_include = []
        for question in card.questions:
            q_lines = 2  # Question + spacer
            if question.answer_200:
                q_lines += max(1, len(question.answer_200) // 40 + 1)
            if question.is_past_exam:
                q_lines += 1

            if current_lines + card_lines + q_lines <= max_lines:
                questions_to_include.append(question)
                card_lines += q_lines
            else:
                truncated = True

        if current_lines + card_lines <= max_lines:
            # Create a copy-like object with selected questions
            selected_cards.append({
                'card': card,
                'questions': questions_to_include
            })
            current_lines += card_lines
        else:
            omitted_count += 1
            truncated = True

    return selected_cards, truncated, omitted_count


def generate_lecture_pdf(lecture, cards, output_path: str, max_pages: int = 2):
    """
    Generate a PDF summary for a lecture.

    Args:
        lecture: Lecture model instance
        cards: List of Card model instances
        output_path: Path to save the PDF
        max_pages: Maximum number of pages (default 2)

    Returns:
        Tuple of (output_path, info_dict)
    """
    # Estimate content and determine scale
    estimated_lines = estimate_content_size(cards)
    lines_per_page = 45

    # Determine scale based on content
    if estimated_lines > lines_per_page * max_pages * 1.5:
        scale = 0.75  # Very compact
    elif estimated_lines > lines_per_page * max_pages:
        scale = 0.85  # Compact
    else:
        scale = 1.0   # Normal

    # Select content that fits
    selected_content, truncated, omitted_count = select_content_for_pages(
        cards, max_pages, scale
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )

    styles = get_styles(scale)
    story = []

    # Title
    title = Paragraph(f"{lecture.title}", styles['JapaneseTitle'])
    story.append(title)

    # Subject info
    info_parts = []
    if lecture.subject:
        info_parts.append(f"科目: {lecture.subject.name}")
    if lecture.slide_count:
        info_parts.append(f"スライド数: {lecture.slide_count}枚")
    info_parts.append(f"カード数: {len(selected_content)}/{len(cards)}")

    if truncated:
        info_parts.append("※一部省略")

    subject_info = Paragraph(" | ".join(info_parts), styles['JapaneseSmall'])
    story.append(subject_info)

    story.append(Spacer(1, 6 * mm * scale))

    # Cards and their questions
    for i, item in enumerate(selected_content, 1):
        card = item['card']
        questions = item['questions']

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
        if questions:
            story.append(Spacer(1, 2 * mm * scale))

            for j, question in enumerate(questions, 1):
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

                story.append(Spacer(1, 1.5 * mm * scale))

        story.append(Spacer(1, 3 * mm * scale))

    # Footer note if truncated
    if truncated:
        story.append(Spacer(1, 5 * mm))
        note = Paragraph(
            f"※ 2ページに収めるため、重要度の低い{omitted_count}件のカードを省略しました。",
            styles['JapaneseSmall']
        )
        story.append(note)

    # Build PDF
    doc.build(story)

    return output_path, {
        'total_cards': len(cards),
        'included_cards': len(selected_content),
        'omitted_cards': omitted_count,
        'truncated': truncated,
        'scale': scale
    }
