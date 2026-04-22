# src/services/report_builder.py
"""
Report Builder — tổng hợp output từ tất cả các service
thành 1 JSON report hoàn chỉnh để trả về API và lưu DB.

Compatible với jd_matcher.py v2 output schema.
"""

import re
from typing import Any, Dict, List
from src.data.rules_config import (
    SCORE_LABELS,
    SCORE_COLOR_THRESHOLDS,
)
from src.data.skills_taxonomy import SKILL_TAXONOMY_VERSION
from src.services.scoring import (
    REPORT_SCHEMA_VERSION,
    SCORING_VERSION,
    FINAL_SCORE_COMPONENT_WEIGHTS,
    compute_scorecard,
)


def _score_label(score: float) -> str:
    for threshold, label in SCORE_LABELS:
        if score >= threshold:
            return label
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


def _get_score_color(score: float) -> str:
    if score >= SCORE_COLOR_THRESHOLDS["green"]:
        return "green"
    if score >= SCORE_COLOR_THRESHOLDS["amber"]:
        return "amber"
    return "red"


def _is_semantic_available(jd_report: Dict[str, Any], semantic_score: float) -> bool:
    meta = jd_report.get("meta", {})
    semantic = jd_report.get("semantic", {})
    status = semantic.get("status", "")
    if meta.get("semantic_available") is False:
        return False
    if status in {"disabled", "unavailable", "error"}:
        return False
    return semantic_score > 0


def _clean_display_line(value: Any) -> str:
    line = str(value or "")
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"^[\s\-*•●▪–—]+", "", line)
    line = re.sub(r"^\(?\s*(?:\d+|[a-zA-Z])[\).:-]\s*", "", line)
    line = re.sub(r"^[\s([{:;,.]+", "", line)
    line = re.sub(r"[\s)\]}:;,.]+$", "", line)
    line = re.sub(r"\s+([,.;:!?])", r"\1", line)
    line = re.sub(r"([(])\s+", r"\1", line)
    line = re.sub(r"\s+([)])", r"\1", line)
    if not re.search(r"[A-Za-zÀ-ỹ0-9]", line):
        return ""
    return line


def _clean_unmatched_jd_lines(items: List[Any], limit: int = 3) -> List[dict]:
    cleaned = []
    seen = set()
    for item in items or []:
        if isinstance(item, dict):
            source_line = item.get("jd_line") or item.get("excerpt") or ""
            score = item.get("best_cv_score")
        else:
            source_line = item
            score = None

        line = _clean_display_line(source_line)
        if len(line.split()) < 4:
            continue

        key = line.lower()
        if key in seen:
            continue
        seen.add(key)

        entry = {"jd_line": line}
        if score is not None:
            entry["best_cv_score"] = score
        cleaned.append(entry)
        if len(cleaned) >= limit:
            break
    return cleaned


def build_match_report(
    cv_record,
    jd_record,
    cv_text: str,
    jd_text: str,
    parsed_sections: dict,
    rule_report: dict,
    jd_report: dict,
) -> dict:
    """
    Tổng hợp report từ:
    - rule_report: từ rule_checker.py (structure, bullets, contact...)
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

    # ── Final score ─────────────────────────────────────────────────
    # final_score is a direct weighted sum of the returned breakdown.
    # If semantic matching is unavailable, its weight is redistributed
    # across the remaining active dimensions instead of silently scoring 0.
    score_values = {
        "section_score": section_score,
        "skill_score": skill_score,
        "semantic_score": semantic_score,
        "keyword_score": keyword_score,
        "experience_score": experience_score,
        "jd_structure_score": jd_structure_score,
    }
    semantic_is_active = _is_semantic_available(jd_report, semantic_score)
    scorecard = compute_scorecard(
        score_values,
        semantic_available=semantic_is_active,
    )
    score_weights = scorecard["final_score_weights"]
    final_score = scorecard["final_score"]

    # ── Merge issues từ tất cả sources ──────────────────────────────
    # jd_report v2 đã có suggested_fix trong từng issue
    all_issues = _merge_unique(
        jd_report.get("issues", [])
        + rule_report.get("issues", []),
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
        "structure_score": round(jd_structure_score, 2),
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
    unmatched_jd_lines = _clean_unmatched_jd_lines(
        semantic_detail.get("unmatched_jd_lines", []),
        limit=3,
    )

    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "summary": {
            "final_score": final_score,
            "label": _score_label(final_score),
            "color": _get_score_color(final_score),
            "cv_title": getattr(cv_record, "title", ""),
            "jd_title": getattr(jd_record, "title", ""),
            "total_issues": len(all_issues),
            "top_priorities": top_priorities,
        },
        "score_breakdown": score_breakdown,
        "score_axes": scorecard["score_axes"],
        "score_weights": score_weights,
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
            "unmatched_jd_lines": unmatched_jd_lines,
        },
        "cv_checks": rule_report,
        "jd_match": jd_report,
        "issues": all_issues,
        "suggestions": all_suggestions,
        "rewrite_examples": jd_report.get("rewrite_examples", []),
        "scoring": {
            "scoring_version": SCORING_VERSION,
            "skill_taxonomy_version": SKILL_TAXONOMY_VERSION,
            "semantic_status": semantic_detail.get("status", "unavailable"),
            "semantic_available": semantic_is_active,
            "base_component_weights": FINAL_SCORE_COMPONENT_WEIGHTS,
            "weights_used": score_weights,
            "disabled_dimensions": scorecard["disabled_dimensions"],
        },
        "snapshots": {
            "cv_excerpt": cv_text[:500],
            "jd_excerpt": jd_text[:500],
            "score_values": {key: round(float(value), 2) for key, value in score_values.items()},
        },
    }
