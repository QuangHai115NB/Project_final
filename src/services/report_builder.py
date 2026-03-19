# src/services/report_builder.py

from typing import Any, Dict, List

from src.data.rules_config import SCORE_WEIGHTS


def _score_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    return "Weak"


def _merge_unique(items: List[dict], key_fields=("code", "title")) -> List[dict]:
    result = []
    seen = set()

    for item in items:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def _language_issue_wrapper(language_report: Dict[str, Any]) -> List[dict]:
    status = language_report.get("status")

    if status == "ok" and language_report.get("issue_count", 0) > 0:
        return [{
            "code": "language_issues",
            "severity": "medium",
            "title": "CV có lỗi chính tả / ngữ pháp tiếng Anh",
            "details": [issue["message"] for issue in language_report.get("issues", [])[:5]]
        }]

    if status in {"error", "unavailable"}:
        return [{
            "code": "language_check_warning",
            "severity": "low",
            "title": "Bộ kiểm tra ngôn ngữ chưa sẵn sàng hoàn toàn",
            "details": [language_report.get("warning", "LanguageTool is not available")]
        }]

    return []


def build_match_report(
    cv_record,
    jd_record,
    cv_text: str,
    jd_text: str,
    parsed_sections: dict,
    rule_report: dict,
    language_report: dict,
    jd_report: dict,
) -> dict:
    section_score = float(rule_report.get("structure_score", 0.0))
    skill_score = float(jd_report.get("skills", {}).get("score", 0.0))
    keyword_score = float(jd_report.get("keywords", {}).get("score", 0.0))
    experience_score = float(jd_report.get("experience", {}).get("score", 0.0))

    # Nếu tool ngôn ngữ unavailable thì không nên phạt
    if language_report.get("status") in {"unavailable", "error"}:
        language_score = 100.0
    else:
        language_score = float(language_report.get("score", 100.0))

    final_score = round(
        (section_score * SCORE_WEIGHTS["section"] / 100.0)
        + (skill_score * SCORE_WEIGHTS["skill"] / 100.0)
        + (keyword_score * SCORE_WEIGHTS["keyword"] / 100.0)
        + (experience_score * SCORE_WEIGHTS["experience"] / 100.0)
        + (language_score * SCORE_WEIGHTS["language"] / 100.0),
        2
    )

    issues = _merge_unique(
        rule_report.get("issues", [])
        + jd_report.get("issues", [])
        + _language_issue_wrapper(language_report)
    )

    suggestions = _merge_unique(
        rule_report.get("suggestions", [])
        + jd_report.get("suggestions", []),
        key_fields=("type", "message")
    )

    top_priorities = []
    for issue in issues:
        if issue.get("severity") in {"high", "medium"}:
            top_priorities.append(issue["title"])

    return {
        "summary": {
            "final_score": final_score,
            "label": _score_label(final_score),
            "cv_title": getattr(cv_record, "title", ""),
            "jd_title": getattr(jd_record, "title", ""),
            "total_issues": len(issues),
            "top_priorities": top_priorities[:5],
        },
        "score_breakdown": {
            "section_score": round(section_score, 2),
            "skill_score": round(skill_score, 2),
            "keyword_score": round(keyword_score, 2),
            "experience_score": round(experience_score, 2),
            "language_score": round(language_score, 2),
        },
        "section_analysis": {
            "sections_found": parsed_sections.get("sections_found", []),
            "missing_required_sections": parsed_sections.get("missing_required_sections", []),
        },
        "cv_checks": rule_report,
        "language_checks": language_report,
        "jd_match": jd_report,
        "issues": issues,
        "suggestions": suggestions,
        "rewrite_examples": jd_report.get("rewrite_examples", []),
        "snapshots": {
            "cv_excerpt": cv_text[:500],
            "jd_excerpt": jd_text[:500],
        }
    }