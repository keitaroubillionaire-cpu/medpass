"""
Question generation service using Google Gemini API.
Generates exam questions from card themes and summaries.
"""

import os
import json
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


QUESTION_GENERATION_PROMPT = """あなたは医学部の定期試験問題を作成する専門家です。
以下のテーマと要約から、定期試験で出題されそうな記述式問題を作成してください。

## テーマ
{theme}

## 要約
{summary}

## 作成ルール
1. 200字程度で解答できる記述式問題を1問作成
2. 問題文は明確で、何を答えるべきかがわかりやすいこと
3. 模範解答は200字程度で、要点を押さえた内容
4. 採点基準は具体的なポイントを箇条書きで記載

## 出力形式
以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{{
  "question_text": "問題文",
  "answer_200": "模範解答（200字程度）",
  "rubric": "採点基準（箇条書き）"
}}
"""


def generate_question_from_card(theme: str, summary: str) -> Dict:
    """
    Generate a question from a card's theme and summary using Gemini API.

    Args:
        theme: Card theme
        summary: Card summary

    Returns:
        Dictionary with keys: question_text, answer_200, rubric
        Returns empty dict if generation fails
    """
    if not client:
        return {}

    if not theme:
        return {}

    try:
        prompt = QUESTION_GENERATION_PROMPT.format(
            theme=theme,
            summary=summary or "(要約なし)"
        )

        response = client.generate_content(prompt)

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

        return {
            "question_text": str(data.get("question_text", ""))[:1000],
            "answer_200": str(data.get("answer_200", ""))[:1000],
            "rubric": str(data.get("rubric", ""))[:1000]
        }

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error in question generation: {e}")
        return {}


def generate_multiple_questions(theme: str, summary: str, count: int = 3) -> List[Dict]:
    """
    Generate multiple questions from a card.

    Args:
        theme: Card theme
        summary: Card summary
        count: Number of questions to generate (1-5)

    Returns:
        List of question dictionaries
    """
    if not client:
        return []

    count = max(1, min(5, count))

    prompt = f"""あなたは医学部の定期試験問題を作成する専門家です。
以下のテーマと要約から、定期試験で出題されそうな記述式問題を{count}問作成してください。

## テーマ
{theme}

## 要約
{summary or "(要約なし)"}

## 作成ルール
1. 各問題は200字程度で解答できる記述式問題
2. 問題文は明確で、何を答えるべきかがわかりやすいこと
3. 模範解答は200字程度で、要点を押さえた内容
4. 採点基準は具体的なポイントを箇条書きで記載
5. 問題同士が重複しないよう、異なる観点から出題

## 出力形式
以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{{
  "questions": [
    {{
      "question_text": "問題文1",
      "answer_200": "模範解答1",
      "rubric": "採点基準1"
    }},
    {{
      "question_text": "問題文2",
      "answer_200": "模範解答2",
      "rubric": "採点基準2"
    }}
  ]
}}
"""

    try:
        response = client.generate_content(prompt)

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
            if "question_text" in q:
                result.append({
                    "question_text": str(q.get("question_text", ""))[:1000],
                    "answer_200": str(q.get("answer_200", ""))[:1000],
                    "rubric": str(q.get("rubric", ""))[:1000]
                })

        return result

    except Exception as e:
        print(f"Error generating multiple questions: {e}")
        return []


def is_api_configured() -> bool:
    """Check if Gemini API is configured."""
    return client is not None
