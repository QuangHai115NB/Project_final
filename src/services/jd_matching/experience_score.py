from __future__ import annotations

import re
from typing import Dict, Tuple


def _extract_experience_months(text: str) -> int:
    normalized = (text or "").lower()
    values = []
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(years?|yrs?|months?|mos?)", normalized):
        number = float(amount)
        if unit.startswith(("year", "yr")):
            values.append(int(number * 12))
        else:
            values.append(int(number))
    return max(values) if values else 0


def _detect_seniority(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(lead|principal|architect|staff)\b", lowered):
        return "lead"
    if re.search(r"\b(senior|sr\.)\b", lowered):
        return "senior"
    if re.search(r"\b(mid-level|mid level|middle)\b", lowered):
        return "mid"
    if re.search(r"\b(junior|fresher|entry)\b", lowered):
        return "junior"
    if re.search(r"\b(intern|internship)\b", lowered):
        return "intern"
    return "unknown"


def compute_experience_score(
        cv_sections: Dict[str, str],
        cv_text: str,
        jd_text: str,
) -> Tuple[float, Dict]:
    duration_text = "\n".join(
        cv_sections.get(sec, "") for sec in ("Experience", "Projects")
    ).strip() or cv_text

    cv_months = _extract_experience_months(duration_text)
    jd_months = _extract_experience_months(jd_text)
    cv_years = round(cv_months / 12.0, 2)
    jd_years = round(jd_months / 12.0, 2)
    seniority_cv = _detect_seniority(cv_text)
    seniority_jd = _detect_seniority(jd_text)

    if jd_months > 0:
        duration_score = min(100.0, (cv_months / jd_months) * 100.0)
    else:
        duration_score = 100.0

    return duration_score, {
        "cv_months": cv_months,
        "jd_months": jd_months,
        "cv_years": cv_years,
        "jd_years": jd_years,
        "years_score": round(duration_score, 2),
        "duration_score": round(duration_score, 2),
        "responsibility_score": None,
        "cv_seniority": seniority_cv,
        "jd_seniority": seniority_jd,
    }

