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
from src.services.cv_annotation_builder import build_annotated_cv


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
    requirements = jd_report.get("requirements", {})
    status = semantic.get("status", "")
    if meta.get("semantic_available") is False:
        return False
    if semantic.get("model_loaded") is not True:
        return False
    if status != "ok":
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


def _short_list(items: List[Any], limit: int = 5) -> str:
    values = [str(item) for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit})"
    return ", ".join(values[:limit]) + suffix


def _score_explanation(score: float, weight: float | None, reasons_vi: List[str], reasons_en: List[str]) -> dict:
    normalized_score = round(float(score or 0.0), 2)
    if normalized_score >= 99.5:
        return {
            "score": normalized_score,
            "weight": weight,
            "lost_points": 0.0,
            "summary_vi": "Khong bi tru diem o hang muc nay.",
            "summary_en": "No points were deducted in this dimension.",
            "reasons_vi": [],
            "reasons_en": [],
        }
    if not reasons_vi:
        if normalized_score >= 99.5:
            reasons_vi = ["Không bị trừ điểm đáng kể ở hạng mục này."]
            reasons_en = ["No meaningful deduction in this dimension."]
        else:
            reasons_vi = ["Điểm bị giảm do chưa đủ tín hiệu rõ trong dữ liệu CV/JD đã phân tích."]
            reasons_en = ["Score is reduced because the analyzed CV/JD data does not provide enough clear signals."]

    lost_points = max(0.0, round(100.0 - normalized_score, 2))
    return {
        "score": normalized_score,
        "weight": weight,
        "lost_points": lost_points,
        "summary_vi": f"Mất khoảng {lost_points:.0f} điểm so với mức tối đa 100 ở hạng mục này.",
        "summary_en": f"About {lost_points:.0f} points below the maximum 100 for this dimension.",
        "reasons_vi": reasons_vi,
        "reasons_en": reasons_en,
    }


ISSUE_SCORE_KEYS = {
    "missing_sections": "section_score",
    "missing_recommended_sections": "section_score",
    "generic_phrases": "section_score",
    "cv_length": "section_score",
    "contact_info": "section_score",
    "missing_required_skills": "skill_score",
    "missing_preferred_skills": "skill_score",
    "keyword_gap": "keyword_score",
    "education_requirement_gap": "semantic_score",
    "uncovered_responsibilities": "semantic_score",
    "weak_experience_alignment": "semantic_score",
    "seniority_gap": "experience_score",
    "skill_no_evidence": "jd_structure_score",
    "missing_metrics": "jd_structure_score",
}


def _filter_issues_for_perfect_scores(issues: List[dict], score_breakdown: Dict[str, float]) -> List[dict]:
    filtered = []
    for issue in issues or []:
        score_key = ISSUE_SCORE_KEYS.get(issue.get("code", ""))
        if score_key and float(score_breakdown.get(score_key, 0) or 0) >= 99.5:
            continue
        filtered.append(issue)
    return filtered


def _build_score_explanations(
    score_breakdown: Dict[str, float],
    score_weights: Dict[str, float],
    rule_report: dict,
    jd_report: dict,
    parsed_sections: dict,
    semantic_is_active: bool,
) -> Dict[str, dict]:
    skills = jd_report.get("skills", {})
    education = jd_report.get("education", {})
    keywords = jd_report.get("keywords", {})
    semantic = jd_report.get("semantic", {})
    requirements = jd_report.get("requirements", {})
    experience = jd_report.get("experience", {})
    structure = jd_report.get("structure", {})
    cv_checks = rule_report or {}
    bullet_analysis = cv_checks.get("bullet_analysis", {}) or {}

    section_reasons_vi = []
    section_reasons_en = []
    missing_required = parsed_sections.get("missing_required_sections", []) or cv_checks.get("missing_sections", [])
    missing_recommended = [
        sec for sec in cv_checks.get("issues", [])
        if sec.get("code") == "missing_recommended_sections"
    ]
    if missing_required:
        section_reasons_vi.append(f"Thiếu section bắt buộc: {_short_list(missing_required)}.")
        section_reasons_en.append(f"Missing required CV sections: {_short_list(missing_required)}.")
    if missing_recommended:
        details = missing_recommended[0].get("details", [])
        section_reasons_vi.append(f"Thiếu section nên có: {_short_list(details)}.")
        section_reasons_en.append(f"Missing recommended sections: {_short_list(details)}.")
    cv_length = cv_checks.get("cv_length", {})
    if cv_length.get("status") and cv_length.get("status") != "good":
        section_reasons_vi.append(f"Độ dài CV chưa hợp lý: {cv_length.get('word_count', 0)} từ, trạng thái {cv_length.get('status')}.")
        section_reasons_en.append(f"CV length is not ideal: {cv_length.get('word_count', 0)} words, status {cv_length.get('status')}.")
    missing_contact = [key for key, value in (cv_checks.get("contact_info", {}) or {}).items() if not value]
    if missing_contact:
        section_reasons_vi.append(f"Thiếu thông tin liên hệ/hồ sơ: {_short_list(missing_contact)}.")
        section_reasons_en.append(f"Missing contact/profile information: {_short_list(missing_contact)}.")

    skill_reasons_vi = []
    skill_reasons_en = []
    missing_req = skills.get("missing_required", []) or []
    missing_pref = skills.get("missing_preferred", []) or []
    if missing_req:
        skill_reasons_vi.append(f"Thiếu kỹ năng bắt buộc trong JD: {_short_list(missing_req)}.")
        skill_reasons_en.append(f"Missing required JD skills: {_short_list(missing_req)}.")
    if missing_pref:
        skill_reasons_vi.append(f"Thiếu kỹ năng ưu tiên: {_short_list(missing_pref)}.")
        skill_reasons_en.append(f"Missing preferred skills: {_short_list(missing_pref)}.")
    if skills.get("required_coverage_pct") is not None:
        skill_reasons_vi.append(f"Mức bao phủ kỹ năng bắt buộc hiện là {float(skills.get('required_coverage_pct') or 0):.0f}%.")
        skill_reasons_en.append(f"Required skill coverage is {float(skills.get('required_coverage_pct') or 0):.0f}%.")
    if education.get("missing"):
        skill_reasons_vi.append(f"Education chua cover yeu cau bang cap/nganh hoc: {_short_list(education.get('missing', []))}.")
        skill_reasons_en.append(f"Education requirements are not clearly covered: {_short_list(education.get('missing', []))}.")
    elif education.get("covered"):
        skill_reasons_vi.append(f"Education da cover yeu cau bang cap/nganh hoc: {_short_list(education.get('covered', []), limit=2)}.")
        skill_reasons_en.append(f"Education covers degree/field requirements: {_short_list(education.get('covered', []), limit=2)}.")

    semantic_reasons_vi = []
    semantic_reasons_en = []
    if not semantic_is_active:
        semantic_reasons_vi.append("Model semantic không khả dụng hoặc không có kết quả hợp lệ; trọng số semantic được phân bổ lại khi tính điểm tổng.")
        semantic_reasons_en.append("Semantic model is unavailable or returned no valid result; its weight is redistributed in the final score.")
    else:
        if semantic.get("jd_coverage_score") is not None:
            semantic_reasons_vi.append(f"CV bao phủ khoảng {float(semantic.get('jd_coverage_score') or 0):.0f}% yêu cầu chính trong JD đã lọc.")
            semantic_reasons_en.append(f"The CV covers about {float(semantic.get('jd_coverage_score') or 0):.0f}% of filtered JD requirements.")
        if semantic.get("requirement_coverage_score") is not None:
            semantic_reasons_vi.append(f"CV cover khoang {float(semantic.get('requirement_coverage_score') or 0):.0f}% requirement theo dung section.")
            semantic_reasons_en.append(f"The CV covers about {float(semantic.get('requirement_coverage_score') or 0):.0f}% of requirements in the right sections.")
        missing_requirements = requirements.get("missing", []) or []
        if missing_requirements:
            details_vi = []
            details_en = []
            for item in missing_requirements[:3]:
                requirement = item.get("requirement", "")
                category = item.get("category", "requirement")
                evidence_score = float(item.get("score", 0) or 0)
                details_vi.append(f"{requirement} [{category}, evidence {evidence_score:.0f}/100]")
                details_en.append(f"{requirement} [{category}, evidence {evidence_score:.0f}/100]")
            semantic_reasons_vi.append("Bi tru vi cac requirement nay chua co evidence du manh o section phu hop: " + _short_list(details_vi, 3) + ".")
            semantic_reasons_en.append("Deducted because these requirements lack strong evidence in the expected sections: " + _short_list(details_en, 3) + ".")
        unmatched = _clean_unmatched_jd_lines(semantic.get("unmatched_jd_lines", []), limit=3)
        if unmatched:
            semantic_reasons_vi.append("Một số yêu cầu JD chưa có bằng chứng rõ trong Experience/Projects: " + _short_list([item["jd_line"] for item in unmatched], 3) + ".")
            semantic_reasons_en.append("Some JD requirements lack clear Experience/Projects evidence: " + _short_list([item["jd_line"] for item in unmatched], 3) + ".")

    keyword_reasons_vi = []
    keyword_reasons_en = []
    missing_keywords = keywords.get("missing", []) or []
    if missing_keywords:
        keyword_reasons_vi.append(f"Thiếu từ khóa kỹ thuật quan trọng: {_short_list(missing_keywords)}.")
        keyword_reasons_en.append(f"Missing important technical keywords: {_short_list(missing_keywords)}.")
    if keywords.get("tfidf_similarity") is not None:
        keyword_reasons_vi.append(f"Độ tương đồng từ khóa TF-IDF với JD đã lọc là {float(keywords.get('tfidf_similarity') or 0):.0f}%.")
        keyword_reasons_en.append(f"TF-IDF keyword similarity against the filtered JD is {float(keywords.get('tfidf_similarity') or 0):.0f}%.")

    experience_reasons_vi = []
    experience_reasons_en = []
    cv_years = float(experience.get("cv_years", 0) or 0)
    jd_years = float(experience.get("jd_years", 0) or 0)
    if jd_years > 0:
        experience_reasons_vi.append(f"JD yêu cầu khoảng {jd_years:g} năm kinh nghiệm; CV thể hiện khoảng {cv_years:g} năm.")
        experience_reasons_en.append(f"JD asks for about {jd_years:g} years; the CV shows about {cv_years:g} years.")
    if experience.get("jd_seniority") != "unknown" and experience.get("cv_seniority") != "unknown" and experience.get("jd_seniority") != experience.get("cv_seniority"):
        experience_reasons_vi.append(f"Level trong JD là {experience.get('jd_seniority')}, CV đang thể hiện {experience.get('cv_seniority')}.")
        experience_reasons_en.append(f"JD seniority is {experience.get('jd_seniority')}; CV indicates {experience.get('cv_seniority')}.")

    evidence_reasons_vi = []
    evidence_reasons_en = []
    no_evidence = structure.get("skills_no_evidence", []) or []
    if no_evidence:
        evidence_reasons_vi.append(f"Một số skill có trong Skills nhưng thiếu bằng chứng trong Experience/Projects: {_short_list(no_evidence)}.")
        evidence_reasons_en.append(f"Some Skills entries lack Experience/Projects evidence: {_short_list(no_evidence)}.")
    total_bullets = int(structure.get("total_bullets", bullet_analysis.get("total_bullets", 0)) or 0)
    metric_count = int(structure.get("metric_count", bullet_analysis.get("metric_bullets", 0)) or 0)
    if total_bullets > 0:
        evidence_reasons_vi.append(f"Có {metric_count}/{total_bullets} dòng mô tả chứa số liệu đo lường.")
        evidence_reasons_en.append(f"{metric_count}/{total_bullets} bullets include measurable metrics.")
    metricless = structure.get("metricless_bullet_excerpts", []) or []
    if metricless:
        evidence_reasons_vi.append("Một số dòng mô tả chưa có kết quả đo được, ví dụ: " + _short_list([item.get("excerpt", "") for item in metricless], 2) + ".")
        evidence_reasons_en.append("Some bullets still lack measurable outcomes, for example: " + _short_list([item.get("excerpt", "") for item in metricless], 2) + ".")

    return {
        "section_score": _score_explanation(score_breakdown.get("section_score", 0), score_weights.get("section_score"), section_reasons_vi, section_reasons_en),
        "skill_score": _score_explanation(score_breakdown.get("skill_score", 0), score_weights.get("skill_score"), skill_reasons_vi, skill_reasons_en),
        "semantic_score": _score_explanation(score_breakdown.get("semantic_score", 0), score_weights.get("semantic_score"), semantic_reasons_vi, semantic_reasons_en),
        "keyword_score": _score_explanation(score_breakdown.get("keyword_score", 0), score_weights.get("keyword_score"), keyword_reasons_vi, keyword_reasons_en),
        "experience_score": _score_explanation(score_breakdown.get("experience_score", 0), score_weights.get("experience_score"), experience_reasons_vi, experience_reasons_en),
        "jd_structure_score": _score_explanation(score_breakdown.get("jd_structure_score", score_breakdown.get("structure_score", 0)), score_weights.get("jd_structure_score"), evidence_reasons_vi, evidence_reasons_en),
    }


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
    all_issues = _filter_issues_for_perfect_scores(all_issues, score_breakdown)
    top_priorities = [
        issue["code"]
        for issue in all_issues
        if issue.get("severity") in {"high", "medium"}
    ][:5]
    score_explanations = _build_score_explanations(
        score_breakdown=score_breakdown,
        score_weights=score_weights,
        rule_report=rule_report,
        jd_report=jd_report,
        parsed_sections=parsed_sections,
        semantic_is_active=semantic_is_active,
    )

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
    structured_cv = build_annotated_cv(cv_text, parsed_sections, all_issues)

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
        "score_explanations": score_explanations,
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
        "structured_cv": structured_cv,
        "scoring": {
            "scoring_version": SCORING_VERSION,
            "skill_taxonomy_version": SKILL_TAXONOMY_VERSION,
            "semantic_status": semantic_detail.get("status", "unavailable"),
            "semantic_available": semantic_is_active,
            "raw_final_score": scorecard.get("raw_final_score", final_score),
            "base_component_weights": FINAL_SCORE_COMPONENT_WEIGHTS,
            "weights_used": score_weights,
            "disabled_dimensions": scorecard["disabled_dimensions"],
        },
        "snapshots": {
            "cv_excerpt": cv_text[:500],
            "jd_excerpt": jd_text[:500],
            "jd_matching_excerpt": jd_report.get("meta", {}).get("jd_matching_excerpt", ""),
            "sections_found": parsed_sections.get("sections_found", []),
            "semantic_cv_source": semantic_detail.get("cv_source", ""),
            "semantic_cv_excerpt": semantic_detail.get("cv_text_analyzed_excerpt", ""),
            "selected_semantic_scorer": semantic_detail.get("selected_semantic_scorer", ""),
            "model_semantic_score": semantic_detail.get("model_semantic_score", 0),
            "tfidf_semantic_score": semantic_detail.get("tfidf_semantic_score", 0),
            "requirement_coverage_score": semantic_detail.get("requirement_coverage_score", 0),
            "requirements_analyzed": semantic_detail.get("requirements_analyzed", 0),
            "requirement_classification": jd_report.get("requirements", {}).get("requirements", [])[:10],
            "semantic_jd_lines_analyzed": semantic_detail.get("jd_lines_analyzed", 0),
            "semantic_cv_bullets_analyzed": semantic_detail.get("cv_bullets_analyzed", 0),
            "score_values": {key: round(float(value), 2) for key, value in score_values.items()},
        },
    }
