from __future__ import annotations
import pdfplumber
from typing import Tuple, Dict, Any

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, Dict[str, Any]]:
    text_parts = []
    num_pages = 0

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            # Thêm marker để debug nếu text bị lẫn cột
            text_parts.append(f"\n\n--- Page {i+1} ---\n{page_text}")

    full_text = "\n".join(text_parts).strip()

    meta = {
        "num_pages": num_pages,
        "source": "pdfplumber",
    }
    return full_text, meta