"""
Question generation service.
MVP: Manual question creation through UI.
Future: LLM-powered automatic question generation from cards.
"""

from typing import List, Dict


def generate_questions_from_card(theme: str, summary: str) -> List[Dict]:
    """
    Generate questions from a card's theme and summary.

    MVP implementation: Returns empty list (manual creation required).
    Future: Will use LLM to generate relevant exam questions.

    Args:
        theme: Card theme
        summary: Card summary

    Returns:
        List of question dictionaries with keys:
        question_text, answer_200, rubric, source_slide
    """
    # MVP: Return empty list - questions are created manually
    # Future implementation will use LLM to generate questions
    return []


def generate_rubric(question: str, answer: str) -> str:
    """
    Generate grading rubric for a question.

    MVP implementation: Returns empty string (manual creation required).
    Future: Will use LLM to create detailed rubric.

    Args:
        question: Question text
        answer: Model answer

    Returns:
        Rubric text
    """
    # MVP: Empty rubric
    return ""
