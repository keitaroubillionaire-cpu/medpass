"""
Card generation service using Claude API.
Extracts themes and summaries from lecture OCR text.
"""

import os
import json
from typing import List, Dict, Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize Anthropic client
client = None
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = """あなたは医学部の定期試験対策を支援するアシスタントです。
以下の授業スライドのOCRテキストから、試験に出題されそうな重要テーマを抽出してください。

## 抽出ルール
1. 各テーマは試験で1問として出題されうる単位で切り出す
2. 要約は200字以内で、そのテーマの要点を説明問題の模範解答として使える形で書く
3. 重要度は以下の基準で1-3の整数で判定:
   - 3: 必ず出る（太字、繰り返し説明、「重要」と明記）
   - 2: 出る可能性が高い（詳しく説明されている）
   - 1: 出るかもしれない（補足的な内容）
4. 1つの講義から5-15個程度のテーマを抽出

## 出力形式
以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{
  "cards": [
    {
      "theme": "テーマ名（20字以内）",
      "summary": "要約（200字以内）",
      "importance": 2
    }
  ]
}

## 授業スライドのOCRテキスト
"""


def extract_themes_from_content(content: str) -> List[Dict]:
    """
    Extract themes from lecture content using Claude API.

    Args:
        content: OCR text from lecture slides

    Returns:
        List of theme dictionaries with keys: theme, summary, importance
    """
    if not client:
        return []

    if not content or len(content.strip()) < 50:
        return []

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + content
                }
            ]
        )

        # Parse response
        response_text = message.content[0].text.strip()

        # Try to extract JSON from response
        # Handle cases where response might have markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json"):
                    in_json = True
                    continue
                elif line.startswith("```"):
                    in_json = False
                    continue
                if in_json:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        data = json.loads(response_text)
        cards = data.get("cards", [])

        # Validate and sanitize
        result = []
        for card in cards:
            if "theme" in card and "summary" in card:
                result.append({
                    "theme": str(card["theme"])[:200],
                    "summary": str(card.get("summary", ""))[:500],
                    "importance": max(1, min(3, int(card.get("importance", 2))))
                })

        return result

    except anthropic.APIError as e:
        print(f"Anthropic API error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in card generation: {e}")
        return []


def suggest_card_importance(theme: str, content: str) -> int:
    """
    Suggest importance level for a theme.

    Args:
        theme: The theme text
        content: Full lecture content for context

    Returns:
        Importance level (1-3)
    """
    # Simple heuristic: check if theme appears multiple times or with emphasis
    theme_lower = theme.lower()
    content_lower = content.lower()

    count = content_lower.count(theme_lower)

    if count >= 3 or "重要" in content or "必ず" in content:
        return 3
    elif count >= 2:
        return 2
    else:
        return 1


def is_api_configured() -> bool:
    """Check if Anthropic API is configured."""
    return client is not None
