"""
Card generation service.
MVP: Manual card creation through UI.
Future: LLM-powered automatic card generation from lecture content.
"""

from typing import List, Dict


def extract_themes_from_content(content: str) -> List[Dict]:
    """
    Extract themes from lecture content.

    MVP implementation: Returns empty list (manual creation required).
    Future: Will use LLM to analyze content and extract key themes.

    Args:
        content: OCR text from lecture slides

    Returns:
        List of theme dictionaries with keys: theme, summary, importance
    """
    # MVP: Return empty list - cards are created manually
    # Future implementation will parse content and generate themes
    return []


def suggest_card_importance(theme: str, content: str) -> int:
    """
    Suggest importance level for a theme.

    MVP implementation: Returns default value of 2.
    Future: Will analyze frequency and context to determine importance.

    Args:
        theme: The theme text
        content: Full lecture content for context

    Returns:
        Importance level (1-3)
    """
    # MVP: Default importance
    return 2
