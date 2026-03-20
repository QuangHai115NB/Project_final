# src/services/report_builder.py
"""
Report Builder — tổng hợp output từ tất cả các service
thành 1 JSON report hoàn chỉnh để trả về API và lưu DB.

Compatible với jd_matcher.py v2 output schema.
"""

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
        key = tuple(item.get(field, "") for field in key_fields)
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
            "error_type": "language_quality",
            "severity": "medium",
            "section": "All",
            "evidence": [issue["message"] for issue in language_report.get("issues", [])[:5]],
            "explanation": f"CV có {language_report.get('issue_count', 0)} lỗi chính tả/ngữ pháp tiếng Anh.",
            "suggested_fix": (
                "Dùng Grammarly hoặc LanguageTool để sửa. "
                "Chú ý: tên công nghệ viết hoa đúng (Python, JavaScript), "
                "dùng past tense nhất quán trong Experience."
            ),
        }]
    if status in {"error", "unavailable"}:
        return [{
            "code": "language_check_warning",
            "error_type": "system",
            "severity": "low",
            "section": "N/A",
            "evidence": [language_report.get("warning", "LanguageTool not available")],
            "explanation": "Bộ kiểm tra ngôn ngữ chưa sẵn sàng.",
            "suggested_fix": "Kiểm tra thủ công hoặc dùng Grammarly.",
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
    """
    Tổng hợp report từ:
    - rule_report: từ rule_checker.py (structure, bullets, contact...)
    - language_report: từ languagetool_checker.py
    - jd_report: từ jd_matcher.py v2 (có score_breakdown mới)

    Safe access tất cả keys — không crash dù jd_report thiếu field.
    """

    # ── Lấy scores an toàn ──────────────────────────────────────────
    section_score = float(rule_report.get("structure_score", 0.0))

    # jd_matcher v2: skills score nằm trong skills.score
    skill_score = float(
        jd_report.get("skills", {}).get("score", 0.0)
    )

    # keyword score
    keyword_score = float(
        jd_report.get("keywords", {}).get("score", 0.0)
    )

    # experience score — v2 có thêm nhiều fields nhưng score vẫn ở đây
    experience_score = float(
        jd_report.get("experience", {}).get("score", 0.0)
    )

    # semantic score — mới trong v2, không có trong v1
    semantic_score = float(
        jd_report.get("semantic", {}).get("score", 0.0)
    )

    # structure score từ jd_matcher v2 (bullet quality)
    jd_structure_score = float(
        jd_report.get("structure", {}).get("score", 0.0)
    )

    # Language score
    if language_report.get("status") in {"unavailable", "error"}:
        language_score = 100.0
    else:
        language_score = float(language_report.get("score", 100.0))

    # ── Final score ─────────────────────────────────────────────────
    # Dùng score_breakdown từ jd_matcher v2 nếu có
    # (đã tính đúng với weight), còn không thì tự tính
    if "score_breakdown" in jd_report and jd_report.get("match_score", 0) > 0:
        # jd_report đã có final score — chỉ cần blend với rule/language
        jd_match_score = float(jd_report.get("match_score", 0.0))
        # Blend: jd_match_score đã cover skills/semantic/keyword/experience/structure
        # Thêm trọng số nhỏ cho section_score (rule checker) và language
        final_score = round(
            jd_match_score * 0.80
            + (section_score / 100.0 * SCORE_WEIGHTS["section"])
            + (language_score / 100.0 * SCORE_WEIGHTS["language"]),
            2
        )
        # Clamp 0-100
        final_score = min(100.0, max(0.0, final_score))
    else:
        # Fallback: tính theo weights cũ (compatible với v1 matcher)
        final_score = round(
            (section_score * SCORE_WEIGHTS["section"] / 100.0)
            + (skill_score * SCORE_WEIGHTS["skill"] / 100.0)
            + (keyword_score * SCORE_WEIGHTS["keyword"] / 100.0)
            + (experience_score * SCORE_WEIGHTS["experience"] / 100.0)
            + (language_score * SCORE_WEIGHTS["language"] / 100.0),
            2
        )

    # ── Merge issues từ tất cả sources ──────────────────────────────
    # jd_report v2 đã có suggested_fix trong từng issue
    all_issues = _merge_unique(
        rule_report.get("issues", [])
        + jd_report.get("issues", [])
        + _language_issue_wrapper(language_report),
        key_fields=("code",),  # Dùng chỉ "code" để dedup chính xác hơn
    )

    all_suggestions = _merge_unique(
        rule_report.get("suggestions", [])
        + jd_report.get("suggestions", []),
        key_fields=("type", "message"),
    )

    # Top priorities: high severity trước
    top_priorities = [
        issue["code"]
        for issue in all_issues
        if issue.get("severity") in {"high", "medium"}
    ][:5]

    # ── Score breakdown đầy đủ ───────────────────────────────────────
    score_breakdown = {
        # Từ rule_checker
        "section_score": round(section_score, 2),
        # Từ jd_matcher v2
        "skill_score": round(skill_score, 2),
        "keyword_score": round(keyword_score, 2),
        "experience_score": round(experience_score, 2),
        "semantic_score": round(semantic_score, 2),
        "jd_structure_score": round(jd_structure_score, 2),
        # Từ languagetool
        "language_score": round(language_score, 2),
        # jd_matcher v2 final (trước khi blend)
        "jd_match_score": round(float(jd_report.get("match_score", 0.0)), 2),
    }

    # ── Skill summary gọn ────────────────────────────────────────────
    skills_summary = {
        "cv_skills": jd_report.get("skills", {}).get("cv_skills", []),
        "required_skills": jd_report.get("skills", {}).get("required_skills", []),
        "matched_required": jd_report.get("skills", {}).get("matched_required", []),
        "missing_required": jd_report.get("skills", {}).get("missing_required", []),
        "matched_preferred": jd_report.get("skills", {}).get("matched_preferred", []),
        "missing_preferred": jd_report.get("skills", {}).get("missing_preferred", []),
        "required_coverage_pct": jd_report.get("skills", {}).get("required_coverage_pct", 0),
    }

    # ── Semantic detail (mới trong v2) ───────────────────────────────
    semantic_detail = jd_report.get("semantic", {})

    return {
        "summary": {
            "final_score": final_score,
            "label": _score_label(final_score),
            "cv_title": getattr(cv_record, "title", ""),
            "jd_title": getattr(jd_record, "title", ""),
            "total_issues": len(all_issues),
            "top_priorities": top_priorities,
        },
        "score_breakdown": score_breakdown,
        "skills_summary": skills_summary,
        "section_analysis": {
            "sections_found": parsed_sections.get("sections_found", []),
            "missing_required_sections": parsed_sections.get("missing_required_sections", []),
        },
        "semantic_analysis": {
            "status": semantic_detail.get("status", "unavailable"),
            "score": round(semantic_score, 2),
            "top_matches": semantic_detail.get("top_matches", [])[:3],
            "weak_matches": semantic_detail.get("weak_matches", [])[:3],
            "unmatched_jd_lines": semantic_detail.get("unmatched_jd_lines", [])[:3],
        },
        "cv_checks": rule_report,
        "language_checks": language_report,
        "jd_match": jd_report,
        "issues": all_issues,
        "suggestions": all_suggestions,
        "rewrite_examples": jd_report.get("rewrite_examples", []),
        "snapshots": {
            "cv_excerpt": cv_text[:500],
            "jd_excerpt": jd_text[:500],
        },
    }