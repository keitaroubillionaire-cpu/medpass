"""
PDF text extraction service.
Extracts text from uploaded PDF files for lecture content.
"""

import io
from typing import Tuple

import pdfplumber


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, int]:
    """
    Extract text from PDF file bytes.

    Args:
        pdf_bytes: Raw PDF file bytes

    Returns:
        Tuple of (extracted_text, page_count)
    """
    text_parts = []
    page_count = 0

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- スライド {i} ---\n{page_text}")
    except Exception as e:
        raise ValueError(f"PDF読み込みエラー: {str(e)}")

    return "\n\n".join(text_parts), page_count


def extract_text_from_pdf_file(file_path: str) -> Tuple[str, int]:
    """
    Extract text from PDF file path.

    Args:
        file_path: Path to PDF file

    Returns:
        Tuple of (extracted_text, page_count)
    """
    with open(file_path, "rb") as f:
        return extract_text_from_pdf(f.read())
