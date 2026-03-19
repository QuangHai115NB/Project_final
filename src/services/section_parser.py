# src/services/section_parser.py

import re
from src.data.rules_config import SECTION_HEADERS, REQUIRED_CV_SECTIONS
from src.services.text_preprocess import clean_text


def _normalize_header(line: str) -> str:
    value = line.strip().lower().rstrip(":")
    value = re.sub(r"[^a-z\s]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _detect_section_header(line: str):
    normalized = _normalize_header(line)
    if not normalized:
        return None

    # Header thường ngắn
    if len(normalized.split()) > 5:
        return None

    for section, aliases in SECTION_HEADERS.items():
        if normalized in aliases:
            return section

    for section, aliases in SECTION_HEADERS.items():
        if any(normalized.startswith(alias) for alias in aliases):
            return section

    return None


def parse_sections(text: str) -> dict:
    lines = [line.strip() for line in clean_text(text).split("\n")]
    sections = {}
    current_section = None
    buffer = []

    def flush_buffer(section_name, items):
        if not section_name or not items:
            return
        content = "\n".join(x for x in items if x.strip()).strip()
        if not content:
            return

        if section_name in sections:
            sections[section_name] += "\n" + content
        else:
            sections[section_name] = content

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        detected = _detect_section_header(line)
        if detected:
            flush_buffer(current_section, buffer)
            current_section = detected
            buffer = []
        else:
            if current_section:
                buffer.append(line)

    flush_buffer(current_section, buffer)

    return {
        "sections": sections,
        "sections_found": list(sections.keys()),
        "missing_required_sections": [
            section for section in REQUIRED_CV_SECTIONS if section not in sections
        ]
    }