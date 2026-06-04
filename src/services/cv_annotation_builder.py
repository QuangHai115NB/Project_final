from __future__ import annotations

import re
from typing import Any


SECTION_ORDER = [
    "Contact",
    "Summary",
    "Skills",
    "Experience",
    "Projects",
    "Education",
    "Certifications",
]


ANCHOR_BY_ISSUE = {
    "missing_required_skills": "Skills",
    "missing_preferred_skills": "Skills",
    "keyword_gap": "Summary",
    "skill_no_evidence": "Skills",
    "weak_experience_alignment": "Experience",
    "uncovered_responsibilities": "Experience",
    "missing_sections": "CV",
    "missing_recommended_sections": "CV",
    "contact_info": "Contact",
    "cv_length": "CV",
}


def _clean_line(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _strip_bullet_marker(value: str) -> str:
    return re.sub(r"^[\s\-*\u2022\u25cf\u25aa\u2013\u2014]+", "", value or "").strip()


def _normalize(value: str) -> str:
    value = str(value or "").lower()
    value = re.sub(r"^[\s\-*\u2022\u25cf\u25aa\u2013\u2014]+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _annotation_tone(severity: str) -> str:
    return {
        "high": "red",
        "medium": "amber",
        "low": "blue",
    }.get(severity or "", "blue")


def _issue_title(issue: dict) -> str:
    return issue.get("title") or issue.get("code", "Issue").replace("_", " ").title()


def _format_evidence_text(item: Any) -> str:
    if isinstance(item, dict):
        return _clean_line(item.get("excerpt") or item.get("jd_line") or item.get("term") or "")
    return _clean_line(item)


def _ordered_sections(section_map: dict[str, str]) -> list[tuple[str, str]]:
    seen = set()
    ordered = []
    for section_name in SECTION_ORDER:
        content = section_map.get(section_name)
        if content:
            ordered.append((section_name, content))
            seen.add(section_name)
    for section_name, content in section_map.items():
        if section_name not in seen and content:
            ordered.append((section_name, content))
    return ordered


def _split_section_items(section_name: str, content: str) -> list[dict]:
    items = []
    bullet_index = 0

    for index, raw_line in enumerate(str(content or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        is_bullet = bool(re.match(r"^[\s\-*\u2022\u25cf\u25aa\u2013\u2014]+", raw_line))
        if is_bullet:
            bullet_index += 1

        items.append({
            "id": f"{section_name.lower()}_{len(items) + 1}",
            "type": "bullet" if is_bullet else "paragraph",
            "section": section_name,
            "line_index": index,
            "bullet_index": bullet_index if is_bullet else None,
            "text": _strip_bullet_marker(line) if is_bullet else line,
            "annotations": [],
        })

    return items


def _find_item_by_evidence(sections: list[dict], evidence: Any, fallback_section: str = "") -> dict | None:
    evidence_text = _format_evidence_text(evidence)
    evidence_norm = _normalize(evidence_text)
    target_section = fallback_section
    target_bullet = None

    if isinstance(evidence, dict):
        target_section = evidence.get("section") or fallback_section
        target_bullet = evidence.get("bullet_index")

    if target_section:
        for section in sections:
            if section["name"] != target_section:
                continue
            if target_bullet:
                for item in section["items"]:
                    if item.get("bullet_index") == target_bullet:
                        return item
            if evidence_norm:
                for item in section["items"]:
                    item_norm = _normalize(item.get("text", ""))
                    if evidence_norm and (evidence_norm in item_norm or item_norm in evidence_norm):
                        return item

    if evidence_norm:
        for section in sections:
            for item in section["items"]:
                item_norm = _normalize(item.get("text", ""))
                if evidence_norm and (evidence_norm in item_norm or item_norm in evidence_norm):
                    return item

    return None


def _find_item_containing_term(sections: list[dict], section_name: str, term: str) -> dict | None:
    term_norm = _normalize(term)
    if not term_norm:
        return None

    for section in sections:
        if section["name"] != section_name:
            continue
        for item in section["items"]:
            if term_norm in _normalize(item.get("text", "")):
                return item
    return None


def _build_annotation(issue: dict, index: int, item: dict | None, evidence_text: str = "") -> dict:
    code = issue.get("code", "issue")
    severity = issue.get("severity", "low")
    annotation = {
        "id": f"ann_{index}",
        "issue_code": code,
        "severity": severity,
        "tone": _annotation_tone(severity),
        "title": _issue_title(issue),
        "section": item.get("section") if item else issue.get("section") or ANCHOR_BY_ISSUE.get(code, "CV"),
        "item_id": item.get("id") if item else None,
        "anchor_text": evidence_text or (item.get("text") if item else ""),
        "suggested_fix": issue.get("suggested_fix_en") or issue.get("suggested_fix") or "",
        "confidence": 0.9 if item else 0.35,
    }
    return annotation


def build_annotated_cv(cv_text: str, parsed_sections: dict, issues: list[dict]) -> dict:
    section_map = parsed_sections.get("sections", {}) if isinstance(parsed_sections, dict) else {}
    sections = [
        {
            "name": section_name,
            "items": _split_section_items(section_name, content),
        }
        for section_name, content in _ordered_sections(section_map)
    ]

    if not sections and cv_text:
        sections = [{
            "name": "CV",
            "items": _split_section_items("CV", cv_text),
        }]

    annotations = []
    annotation_index = 1

    for issue in issues or []:
        code = issue.get("code", "")
        evidence_items = issue.get("evidence") or issue.get("details") or []
        fallback_section = issue.get("section") or ANCHOR_BY_ISSUE.get(code, "")

        matched_any = False
        for evidence in evidence_items[:5]:
            evidence_text = _format_evidence_text(evidence)
            item = _find_item_by_evidence(sections, evidence, fallback_section)

            if not item and code == "skill_no_evidence":
                item = _find_item_containing_term(sections, "Skills", evidence_text)

            if not item:
                continue

            annotation = _build_annotation(issue, annotation_index, item, evidence_text)
            annotations.append(annotation)
            item["annotations"].append(annotation["id"])
            annotation_index += 1
            matched_any = True

        if not matched_any:
            annotations.append(_build_annotation(issue, annotation_index, None))
            annotation_index += 1

    return {
        "source": "section_parser",
        "sections": sections,
        "annotations": annotations,
        "stats": {
            "section_count": len(sections),
            "annotation_count": len(annotations),
            "anchored_annotation_count": sum(1 for item in annotations if item.get("item_id")),
        },
    }
