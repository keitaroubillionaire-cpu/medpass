"""
Past exam parser service.
Extracts questions and answers from past exam PDFs and images using Google Gemini API.
"""

import os
import json
import base64
from typing import List, Dict

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
client = None
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    client = genai.GenerativeModel("gemini-2.0-flash")


# Supported image formats
SUPPORTED_IMAGE_TYPES = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp'
}


PAST_EXAM_PARSE_PROMPT = """あなたは医学部の定期試験の過去問を解析する専門家です。
以下の過去問PDFから抽出したテキストを分析し、個々の問題と解答を抽出してください。

## 抽出ルール
1. 問題文と解答（あれば）を正確に抽出
2. 問題番号があれば記録
3. 解答がない場合は空文字列
4. 問題のテーマ（何について問われているか）を20字以内で推定
5. 各問題の重要度を推定（1-3）:
   - 3: 頻出・基本的な内容
   - 2: 標準的な問題
   - 1: 発展的・マイナーな内容

## 出力形式
以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{
  "questions": [
    {
      "question_number": "問1",
      "question_text": "問題文",
      "answer": "解答（あれば）",
      "theme": "推定テーマ",
      "importance": 2
    }
  ]
}

## 過去問テキスト
"""


PAST_EXAM_IMAGE_PROMPT = """あなたは医学部の定期試験の過去問を解析する専門家です。
この過去問の画像から、個々の問題と解答を抽出してください。

## 抽出ルール
1. 問題文と解答（あれば）を正確に抽出
2. 問題番号があれば記録
3. 解答がない場合は空文字列
4. 問題のテーマ（何について問われているか）を20字以内で推定
5. 各問題の重要度を推定（1-3）:
   - 3: 頻出・基本的な内容
   - 2: 標準的な問題
   - 1: 発展的・マイナーな内容

## 出力形式
以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{
  "questions": [
    {
      "question_number": "問1",
      "question_text": "問題文",
      "answer": "解答（あれば）",
      "theme": "推定テーマ",
      "importance": 2
    }
  ]
}"""


def parse_past_exam_pdf(pdf_text: str) -> List[Dict]:
    """
    Parse past exam text and extract questions using Gemini API.

    Args:
        pdf_text: Text extracted from past exam PDF

    Returns:
        List of question dictionaries with keys:
        question_number, question_text, answer, theme, importance
    """
    if not client:
        return []

    if not pdf_text or len(pdf_text.strip()) < 50:
        return []

    try:
        response = client.generate_content(PAST_EXAM_PARSE_PROMPT + pdf_text)

        # Parse response
        response_text = response.text.strip()

        # Handle markdown code blocks
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
        questions = data.get("questions", [])

        result = []
        for q in questions:
            if "question_text" in q and q["question_text"]:
                result.append({
                    "question_number": str(q.get("question_number", ""))[:50],
                    "question_text": str(q.get("question_text", ""))[:2000],
                    "answer": str(q.get("answer", ""))[:2000],
                    "theme": str(q.get("theme", ""))[:100],
                    "importance": max(1, min(3, int(q.get("importance", 2))))
                })

        return result

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in past exam parsing: {e}")
        return []


def match_question_to_card(question_theme: str, cards: list) -> int:
    """
    Try to match a question theme to an existing card.

    Args:
        question_theme: The theme extracted from the question
        cards: List of Card objects

    Returns:
        Card ID if matched, None otherwise
    """
    if not question_theme or not cards:
        return None

    theme_lower = question_theme.lower()

    # Simple keyword matching
    for card in cards:
        card_theme_lower = card.theme.lower()
        # Check if themes overlap significantly
        if theme_lower in card_theme_lower or card_theme_lower in theme_lower:
            return card.id

        # Check for common keywords
        theme_words = set(theme_lower.split())
        card_words = set(card_theme_lower.split())
        common_words = theme_words & card_words
        if len(common_words) >= 2:
            return card.id

    return None


def parse_past_exam_image(image_bytes: bytes, media_type: str) -> List[Dict]:
    """
    Parse past exam image and extract questions using Gemini Vision API.

    Args:
        image_bytes: Raw image bytes
        media_type: MIME type of the image (e.g., 'image/png')

    Returns:
        List of question dictionaries with keys:
        question_number, question_text, answer, theme, importance
    """
    if not client:
        return []

    try:
        # Create image part for Gemini
        image_part = {
            "mime_type": media_type,
            "data": image_bytes
        }

        response = client.generate_content([
            PAST_EXAM_IMAGE_PROMPT,
            image_part
        ])

        # Parse response
        response_text = response.text.strip()

        # Handle markdown code blocks
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
        questions = data.get("questions", [])

        result = []
        for q in questions:
            if "question_text" in q and q["question_text"]:
                result.append({
                    "question_number": str(q.get("question_number", ""))[:50],
                    "question_text": str(q.get("question_text", ""))[:2000],
                    "answer": str(q.get("answer", ""))[:2000],
                    "theme": str(q.get("theme", ""))[:100],
                    "importance": max(1, min(3, int(q.get("importance", 2))))
                })

        return result

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in past exam image parsing: {e}")
        return []


def get_media_type(filename: str) -> str:
    """Get MIME type from filename extension."""
    ext = os.path.splitext(filename.lower())[1]
    return SUPPORTED_IMAGE_TYPES.get(ext, None)


def is_supported_image(filename: str) -> bool:
    """Check if file is a supported image format."""
    return get_media_type(filename) is not None


def is_api_configured() -> bool:
    """Check if Gemini API is configured."""
    return client is not None
