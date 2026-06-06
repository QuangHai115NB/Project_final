from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

try:
    from src.services.semantic_matcher import find_skill_context_in_cv

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


def compute_structure_score(
        cv_sections: Dict[str, str],
        cv_skills: Set[str],
        required_skills: Set[str],
) -> Tuple[float, Dict]:
    import re as _re

    skills_no_evidence = []

    if SEMANTIC_AVAILABLE:
        for skill in list(required_skills & cv_skills)[:10]:
            ctx = find_skill_context_in_cv(skill, cv_sections)
            if ctx["in_skills_section"] and not ctx["has_evidence"]:
                skills_no_evidence.append(skill)

    bullet_items = _extract_cv_bullets(cv_sections)

    metric_pattern = _re.compile(
        r"(\d+%|\d+\+|[$â‚¬Â£]\d+|\d+\s*(users|clients|ms|seconds|apis|services|modules|records|requests))",
        _re.IGNORECASE,
    )

    metric_bullets = [
        item for item in bullet_items
        if metric_pattern.search(item["text"])
    ]
    metricless_bullets = [
        item for item in bullet_items
        if not metric_pattern.search(item["text"])
    ]

    total = len(bullet_items)
    metric_count = len(metric_bullets)

    penalty = 0
    penalty += len(skills_no_evidence) * 4
    if total > 0:
        metric_ratio = metric_count / total
        if metric_ratio == 0:
            penalty += 15
        elif metric_ratio < 0.3:
            penalty += 7

    score = max(0.0, 100.0 - penalty)

    return score, {
        "total_bullets": total,
        "metric_count": metric_count,
        "metric_bullet_excerpts": [
            {
                "section": item["section"],
                "bullet_index": item["bullet_index"],
                "excerpt": item["excerpt"],
            }
            for item in metric_bullets
        ],
        "metricless_bullet_excerpts": [
            {
                "section": item["section"],
                "bullet_index": item["bullet_index"],
                "excerpt": item["excerpt"],
                "reason": "No measurable result or scale found.",
            }
            for item in metricless_bullets[:5]
        ],
        "skills_no_evidence": skills_no_evidence[:5],
        "penalty_applied": penalty,
    }


def _extract_cv_bullets(cv_sections: Dict[str, str]) -> List[Dict]:
    bullets = []
    bullet_markers = ("-", "â€¢", "â—", "â–ª", "*")
    fallback_markers = ("Ã¢â‚¬Â¢", "Ã¢â€”Â", "Ã¢â€“Âª")

    def starts_with_marker(value: str) -> bool:
        return value.startswith(bullet_markers) or value.startswith(fallback_markers)

    def strip_marker(value: str) -> str:
        cleaned = value.strip()
        for marker in bullet_markers + fallback_markers:
            if cleaned.startswith(marker):
                return cleaned[len(marker):].strip()
        return cleaned

    def is_likely_role_heading(value: str) -> bool:
        return bool(re.search(r"(19|20)\d{2}", value)) and any(
            marker in value for marker in ("â€”", "â€“", "-", "(")
        )

    def flush(section_name: str, index: int, parts: List[str]):
        text = _truncate(" ".join(part.strip() for part in parts if part.strip()), 240)
        if len(text.split()) < 4:
            return
        bullets.append({
            "section": section_name,
            "bullet_index": index,
            "excerpt": _truncate(text),
            "text": text,
        })

    for section_name in ("Experience", "Projects"):
        content = cv_sections.get(section_name, "")
        current_parts = []
        index = 0
        for raw_line in content.split("\n"):
            stripped = raw_line.strip()
            if not stripped:
                continue

            if starts_with_marker(stripped):
                if current_parts:
                    flush(section_name, index, current_parts)
                index += 1
                current_parts = [strip_marker(stripped)]
            elif current_parts:
                if is_likely_role_heading(stripped):
                    flush(section_name, index, current_parts)
                    current_parts = []
                    continue
                current_parts.append(strip_marker(stripped))

        if current_parts:
            flush(section_name, index, current_parts)
    return bullets


def _truncate(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

