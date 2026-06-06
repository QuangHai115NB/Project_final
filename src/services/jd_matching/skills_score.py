from __future__ import annotations

from typing import Dict, List, Set, Tuple

from src.data.skills_taxonomy import extract_skills
from src.services.text_preprocess import split_lines


def extract_jd_skills(jd_text: str) -> Dict[str, List[str]]:
    required: Set[str] = set()
    preferred: Set[str] = set()
    contextual: Set[str] = set()
    current_section = None

    from src.services.jd_matching.pipeline import _detect_jd_skill_section, _is_preferred_line

    for line in split_lines(jd_text):
        detected_section = _detect_jd_skill_section(line)
        if detected_section:
            current_section = detected_section
            continue

        line_skills = set(extract_skills(line).get("skills", []))
        if not line_skills:
            continue
        if current_section == "preferred" or _is_preferred_line(line):
            preferred.update(line_skills)
        elif current_section == "required":
            required.update(line_skills)
        elif current_section == "responsibilities":
            contextual.update(line_skills)
        elif current_section == "benefits":
            continue
        else:
            required.update(line_skills)

    if not required and not preferred and not contextual:
        required.update(extract_skills(jd_text).get("skills", []))

    preferred = preferred - required
    contextual = contextual - required - preferred
    return {
        "required": sorted(required),
        "preferred": sorted(preferred),
        "contextual": sorted(contextual),
    }


def compute_skill_score(
        cv_skills: Set[str],
        required_skills: Set[str],
        preferred_skills: Set[str],
) -> Tuple[float, Dict]:
    matched_required = sorted(required_skills & cv_skills)
    missing_required = sorted(required_skills - cv_skills)
    matched_preferred = sorted(preferred_skills & cv_skills)
    missing_preferred = sorted(preferred_skills - cv_skills)

    from src.services.jd_matching.pipeline import _safe_ratio

    required_ratio = _safe_ratio(len(matched_required), len(required_skills))
    preferred_ratio = _safe_ratio(len(matched_preferred), len(preferred_skills))

    score = (required_ratio * 75.0) + (preferred_ratio * 25.0)

    return score, {
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "required_coverage_pct": round(required_ratio * 100, 1),
        "preferred_coverage_pct": round(preferred_ratio * 100, 1),
    }
