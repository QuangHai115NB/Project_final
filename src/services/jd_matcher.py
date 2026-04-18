
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data.rules_config import (
    JD_PREFERRED_MARKERS,
    KEYWORD_BLACKLIST,
    MAX_KEYWORDS,
)
from src.data.skills_taxonomy import extract_skills
from src.services.text_preprocess import normalize_for_matching, split_lines

# Import semantic matcher — graceful fallback nếu chưa cài
try:
    from src.services.semantic_matcher import (
        match_bullets_to_jd,
        find_skill_context_in_cv,
        compute_semantic_similarity,
    )

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Import suggestion engine
try:
    from src.services.suggestion_engine import generate_bulk_suggestions

    SUGGESTION_ENGINE_AVAILABLE = True
except ImportError:
    SUGGESTION_ENGINE_AVAILABLE = False


# ─── Utility helpers ────────────────────────────────────────────────

def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator


def _extract_years_of_experience(text: str) -> int:
    values = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)", text.lower())
    if not values:
        return 0
    return max(int(v) for v in values)


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


def _is_preferred_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in JD_PREFERRED_MARKERS)


# ─── Layer 1: Skill Matching ─────────────────────────────────────────

def _extract_jd_skills(jd_text: str) -> Dict[str, List[str]]:
    """
    Tách skills từ JD thành required vs preferred.
    Logic: line chứa "preferred/nice-to-have" → preferred, còn lại → required.
    """
    required: Set[str] = set()
    preferred: Set[str] = set()

    for line in split_lines(jd_text):
        line_skills = set(extract_skills(line).get("skills", []))
        if not line_skills:
            continue
        if _is_preferred_line(line):
            preferred.update(line_skills)
        else:
            required.update(line_skills)

    if not required and not preferred:
        required.update(extract_skills(jd_text).get("skills", []))

    preferred = preferred - required
    return {
        "required": sorted(required),
        "preferred": sorted(preferred),
    }


def _compute_skill_score(
        cv_skills: Set[str],
        required_skills: Set[str],
        preferred_skills: Set[str],
) -> Tuple[float, Dict]:
    """
    Layer 1 score: weighted skill coverage.

    Formula:
        skill_score = required_coverage * 75 + preferred_coverage * 25

    Tại sao không 100% required:
    Có trường hợp JD list quá nhiều skills, không ai có hết.

    Returns: (score_0_100, detail_dict)
    """
    matched_required = sorted(required_skills & cv_skills)
    missing_required = sorted(required_skills - cv_skills)
    matched_preferred = sorted(preferred_skills & cv_skills)
    missing_preferred = sorted(preferred_skills - cv_skills)

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


# ─── Layer 2: Semantic Similarity ────────────────────────────────────

def _compute_semantic_score(
        cv_sections: Dict[str, str],
        jd_text: str,
) -> Tuple[float, Dict]:
    """
    Layer 2: So sánh CV experience bullets vs JD responsibilities
    dùng sentence-transformers.

    Nếu model không available → fallback về TF-IDF similarity.

    Returns: (score_0_100, detail_dict)
    """
    experience_text = "\n".join(
        cv_sections.get(sec, "")
        for sec in ("Experience", "Projects", "Summary")
    ).strip()

    if not experience_text:
        experience_text = ""

    if SEMANTIC_AVAILABLE:
        result = match_bullets_to_jd(
            cv_experience_text=experience_text,
            jd_text=jd_text,
            threshold=0.42,
        )
        score = result.get("semantic_score", 0.0)
        return score, result
    else:
        # Fallback TF-IDF
        score = _tfidf_similarity(experience_text, jd_text)
        return score, {
            "status": "fallback_tfidf",
            "semantic_score": score,
            "top_matches": [],
            "weak_matches": [],
            "unmatched_jd_lines": [],
        }


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    a = normalize_for_matching(text_a)
    b = normalize_for_matching(text_b)
    if not a or not b:
        return 0.0
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vec.fit_transform([a, b])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100.0
    except Exception:
        return 0.0


def _truncate(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _extract_cv_bullets(cv_sections: Dict[str, str]) -> List[Dict]:
    """Return candidate bullets with section and ordinal for precise feedback."""
    bullets = []
    bullet_markers = ("-", "•", "●", "▪", "*")
    fallback_markers = ("â€¢", "â—", "â–ª")

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
            marker in value for marker in ("—", "–", "-", "(")
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
                # PDF extraction often wraps one bullet across multiple lines.
                current_parts.append(strip_marker(stripped))

        if current_parts:
            flush(section_name, index, current_parts)
    return bullets


def _evidence_to_details(evidence: List) -> List[str]:
    details = []
    for item in evidence or []:
        if isinstance(item, dict):
            details.append(str(item.get("excerpt") or item.get("term") or item))
        else:
            details.append(str(item))
    return details


# ─── Layer 3: Keyword Matching ───────────────────────────────────────

def _compute_keyword_score(
        cv_text: str,
        jd_text: str,
        limit: int = MAX_KEYWORDS,
) -> Tuple[float, Dict]:
    """
    Layer 3: TF-IDF keyword overlap.
    Trích ra top keywords từ JD, check bao nhiêu có trong CV.

    Returns: (score_0_100, detail_dict)
    """
    cv_norm = normalize_for_matching(cv_text)
    jd_norm = normalize_for_matching(jd_text)

    if not cv_norm or not jd_norm:
        return 0.0, {"keywords": [], "matched": [], "missing": [], "tfidf_similarity": 0.0}

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=500,
        )
        matrix = vectorizer.fit_transform([cv_norm, jd_norm])
        feature_names = vectorizer.get_feature_names_out()
        jd_vector = matrix[1].toarray().ravel()

        ranked = sorted(
            zip(feature_names, jd_vector), key=lambda x: x[1], reverse=True
        )

        keywords = []
        for term, weight in ranked:
            if weight <= 0 or len(term) < 3 or term in KEYWORD_BLACKLIST or term.isdigit():
                continue
            keywords.append(term)
            if len(keywords) >= limit:
                break

        matched = [kw for kw in keywords if kw in cv_norm]
        missing = [kw for kw in keywords if kw not in cv_norm]
        tfidf_sim = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100.0
        kw_score = _safe_ratio(len(matched), len(keywords)) * 100.0 if keywords else 0.0

        return kw_score, {
            "keywords": keywords[:15],
            "matched": matched[:10],
            "missing": missing[:10],
            "tfidf_similarity": round(tfidf_sim, 2),
        }
    except Exception:
        return 0.0, {"keywords": [], "matched": [], "missing": [], "tfidf_similarity": 0.0}


# ─── Layer 4: Experience Alignment ───────────────────────────────────

def _compute_experience_score(
        cv_sections: Dict[str, str],
        cv_text: str,
        jd_text: str,
) -> Tuple[float, Dict]:
    """
    Layer 4: Experience years + responsibility alignment.

    Formula:
        experience_score = years_score * 0.30 + responsibility_score * 0.70

    Returns: (score_0_100, detail_dict)
    """
    experience_text = "\n".join(
        cv_sections.get(sec, "") for sec in ("Experience", "Projects", "Summary")
    ).strip() or cv_text

    cv_years = _extract_years_of_experience(experience_text)
    jd_years = _extract_years_of_experience(jd_text)
    seniority_cv = _detect_seniority(cv_text)
    seniority_jd = _detect_seniority(jd_text)

    if jd_years > 0:
        years_score = min(100.0, (cv_years / jd_years) * 100.0) if cv_years > 0 else 35.0
    else:
        years_score = 70.0

    # Responsibility similarity (TF-IDF nếu không có semantic)
    responsibility_score = _tfidf_similarity(experience_text, jd_text)

    experience_score = (responsibility_score * 0.70) + (years_score * 0.30)

    return experience_score, {
        "cv_years": cv_years,
        "jd_years": jd_years,
        "years_score": round(years_score, 2),
        "responsibility_score": round(responsibility_score, 2),
        "cv_seniority": seniority_cv,
        "jd_seniority": seniority_jd,
    }


# ─── Layer 5: Bullet Quality & Evidence Check ────────────────────────

def _compute_structure_score(
        cv_sections: Dict[str, str],
        cv_skills: Set[str],
        required_skills: Set[str],
) -> Tuple[float, Dict]:
    """
    Layer 5: Bullet quality + skill evidence check.

    Kiểm tra:
    1. Skills có trong Skills section nhưng không có evidence trong Experience/Projects
    2. Tỷ lệ bullets có action verb
    3. Tỷ lệ bullets có metric

    Returns: (score_0_100, detail_dict)
    """
    from src.data.rules_config import ACTION_VERBS, WEAK_BULLET_PATTERNS
    import re as _re

    skills_no_evidence = []

    if SEMANTIC_AVAILABLE:
        for skill in list(required_skills & cv_skills)[:10]:
            ctx = find_skill_context_in_cv(skill, cv_sections)
            if ctx["in_skills_section"] and not ctx["has_evidence"]:
                skills_no_evidence.append(skill)

    # Bullet analysis
    bullet_items = _extract_cv_bullets(cv_sections)
    bullets = [item["text"] for item in bullet_items]

    metric_pattern = _re.compile(
        r"(\d+%|\d+\+|[$€£]\d+|\d+\s*(users|clients|ms|seconds|apis|services|modules|records|requests))",
        _re.IGNORECASE,
    )

    action_bullets = [
        item for item in bullet_items
        if item["text"].split() and item["text"].lower().split()[0] in ACTION_VERBS
    ]
    metric_bullets = [
        item for item in bullet_items
        if metric_pattern.search(item["text"])
    ]
    weak_bullets = [
        item for item in bullet_items
        if any(item["text"].lower().startswith(p) for p in WEAK_BULLET_PATTERNS)
    ]
    metricless_bullets = [
        item for item in bullet_items
        if not metric_pattern.search(item["text"])
    ]

    total = len(bullet_items)
    action_count = len(action_bullets)
    metric_count = len(metric_bullets)
    weak_count = len(weak_bullets)

    penalty = 0
    penalty += len(skills_no_evidence) * 8  # 8 điểm mỗi skill thiếu evidence
    if total > 0:
        action_ratio = action_count / total
        metric_ratio = metric_count / total
        if action_ratio < 0.5:
            penalty += 15
        elif action_ratio < 0.7:
            penalty += 7
        if metric_ratio == 0:
            penalty += 15
        elif metric_ratio < 0.3:
            penalty += 7
        if weak_count > 0:
            penalty += weak_count * 5

    score = max(0.0, 100.0 - penalty)

    return score, {
        "total_bullets": total,
        "action_verb_count": action_count,
        "metric_count": metric_count,
        "weak_bullet_count": weak_count,
        "weak_bullet_excerpts": [
            {
                "section": item["section"],
                "bullet_index": item["bullet_index"],
                "excerpt": item["excerpt"],
                "reason": "Starts with a weak/passive phrase.",
            }
            for item in weak_bullets
        ],
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


# ─── Error & Suggestion Generator ────────────────────────────────────

def _generate_errors_and_suggestions(
        skill_detail: Dict,
        keyword_detail: Dict,
        experience_detail: Dict,
        structure_detail: Dict,
        semantic_detail: Dict,
        cv_sections: Dict[str, str],
        jd_text: str,
        use_suggestion_engine: bool = True,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Tổng hợp tất cả issues và suggestions từ các layers.
    Mỗi issue có đầy đủ: code, error_type, severity, section, evidence, explanation, suggested_fix.
    """
    issues = []
    suggestions = []

    # --- Skill issues ---
    missing_req = skill_detail.get("missing_required", [])
    missing_pref = skill_detail.get("missing_preferred", [])

    if missing_req:
        issues.append({
            "code": "missing_required_skills",
            "error_type": "skill_gap",
            "severity": "high",
            "section": "Skills / Experience",
            "evidence": missing_req,
            "explanation": (
                f"JD yêu cầu {len(missing_req)} kỹ năng mà CV chưa thể hiện: "
                f"{', '.join(missing_req[:5])}."
            ),
        })

    if missing_pref:
        issues.append({
            "code": "missing_preferred_skills",
            "error_type": "skill_gap",
            "severity": "medium",
            "section": "Skills",
            "evidence": missing_pref,
            "explanation": (
                f"Các kỹ năng nice-to-have chưa có: {', '.join(missing_pref[:5])}. "
                f"Thêm vào sẽ tăng điểm phù hợp."
            ),
        })

    # --- Skills có trong Skills section nhưng không có evidence ---
    no_evidence = structure_detail.get("skills_no_evidence", [])
    if no_evidence:
        issues.append({
            "code": "skill_no_evidence",
            "error_type": "missing_evidence",
            "severity": "medium",
            "section": "Experience / Projects",
            "evidence": no_evidence,
            "explanation": (
                f"Các kỹ năng này có trong mục Skills nhưng không xuất hiện "
                f"trong bất kỳ bullet nào của Experience/Projects: {', '.join(no_evidence)}. "
                f"Recruiter sẽ nghi ngờ tính xác thực."
            ),
        })

    # --- Keyword gap ---
    missing_kw = keyword_detail.get("missing", [])
    if missing_kw:
        issues.append({
            "code": "keyword_gap",
            "error_type": "keyword_mismatch",
            "severity": "medium",
            "section": "Summary / Experience",
            "evidence": missing_kw[:8],
            "explanation": (
                f"CV chưa cover {len(missing_kw)} từ khóa quan trọng từ JD: "
                f"{', '.join(missing_kw[:5])}."
            ),
        })

    # --- Weak bullets ---
    weak_excerpts = structure_detail.get("weak_bullet_excerpts", [])
    weak_count = structure_detail.get("weak_bullet_count", 0)
    if weak_count > 0:
        issues.append({
            "code": "weak_bullets",
            "error_type": "language_quality",
            "severity": "medium",
            "section": "Experience / Projects",
            "evidence": weak_excerpts[:3],   # trích dẫn bullet cụ thể
            "explanation": (
                f"{weak_count} bullets bắt đầu bằng cụm từ thụ động "
                f"('Responsible for', 'Worked on', 'Helped with'...). "
                f"Recruiter sẽ nghi ngờ tính chủ động trong công việc."
            ),
        })

    # --- Missing metrics ---
    metric_count = structure_detail.get("metric_count", 0)
    total_bullets = structure_detail.get("total_bullets", 0)
    metricless_excerpts = structure_detail.get("metricless_bullet_excerpts", [])
    if total_bullets > 0 and metric_count == 0:
        issues.append({
            "code": "missing_metrics",
            "error_type": "content_quality",
            "severity": "medium",
            "section": "Experience / Projects",
            "evidence": metricless_excerpts[:3] or ["Không có bullet nào chứa số liệu đo lường."],
            "explanation": (
                f"Không có bullet nào trong {total_bullets} bullets chứa số liệu cụ thể "
                f"(%, số user, số API, thời gian...). "
                f"CV IT mạnh cần ít nhất 2-3 bullets có con số cụ thể."
            ),
        })

    # --- Experience alignment ---
    exp_score = experience_detail.get("responsibility_score", 0)
    if exp_score < 45:
        issues.append({
            "code": "weak_experience_alignment",
            "error_type": "content_relevance",
            "severity": "high",
            "section": "Experience",
            "evidence": [
                f"TF-IDF similarity với JD: {exp_score:.1f}/100",
                f"CV years: {experience_detail.get('cv_years', 0)}, JD requires: {experience_detail.get('jd_years', 0)}",
            ],
            "explanation": (
                "Nội dung Experience/Projects chưa bám sát trách nhiệm trong JD. "
                "Cần viết lại bullets để phản ánh đúng công việc JD yêu cầu."
            ),
        })

    # --- Seniority mismatch ---
    seniority_cv = experience_detail.get("cv_seniority", "unknown")
    seniority_jd = experience_detail.get("jd_seniority", "unknown")
    if seniority_jd != "unknown" and seniority_cv != "unknown" and seniority_jd != seniority_cv:
        issues.append({
            "code": "seniority_gap",
            "error_type": "level_mismatch",
            "severity": "low",
            "section": "Summary / Experience",
            "evidence": [f"CV level: {seniority_cv}", f"JD level: {seniority_jd}"],
            "explanation": (
                f"JD tìm {seniority_jd} nhưng CV đang thể hiện {seniority_cv}. "
                f"Cân nhắc điều chỉnh ngôn ngữ và scope dự án."
            ),
        })

    # --- Semantic: unmatched JD responsibilities ---
    unmatched_jd = semantic_detail.get("unmatched_jd_lines", [])
    if len(unmatched_jd) >= 3:
        issues.append({
            "code": "uncovered_responsibilities",
            "error_type": "content_relevance",
            "severity": "medium",
            "section": "Experience",
            "evidence": [item["jd_line"][:100] for item in unmatched_jd[:3]],
            "explanation": (
                f"{len(unmatched_jd)} trách nhiệm trong JD chưa được cover "
                f"bởi bất kỳ bullet nào trong Experience/Projects."
            ),
        })

    # Keep compatibility with suggestion_engine, which reads details.
    for issue in issues:
        issue.setdefault("details", _evidence_to_details(issue.get("evidence", [])))

    # --- Generate suggested_fix cho từng issue ---
    if use_suggestion_engine and SUGGESTION_ENGINE_AVAILABLE:
        issues = generate_bulk_suggestions(
            errors=issues,
            cv_sections=cv_sections,
            jd_text=jd_text,
            max_api_calls=3,
        )
    else:
        # Thêm suggested_fix rule-based nếu không có suggestion engine
        from src.services.suggestion_engine import _get_rule_based_fix
        for issue in issues:
            issue["suggested_fix"] = _get_rule_based_fix(
                issue["code"], issue.get("evidence", []), issue.get("section", "")
            )

    return issues, suggestions


# ─── Rewrite examples ────────────────────────────────────────────────

def _build_rewrite_examples(
        missing_terms: List[str],
        jd_text: str = "",
) -> List[Dict]:
    """
    Tạo 3 ví dụ rewrite cụ thể cho từng section.
    """
    focus = missing_terms[:3]
    if not focus:
        return []

    joined = ", ".join(focus)
    jd_domain = "backend systems"
    if "react" in jd_text.lower() or "frontend" in jd_text.lower():
        jd_domain = "frontend applications"
    elif "data" in jd_text.lower() or "ml" in jd_text.lower():
        jd_domain = "data pipelines"
    elif "mobile" in jd_text.lower() or "android" in jd_text.lower():
        jd_domain = "mobile applications"

    return [
        {
            "target_section": "Experience",
            "label": "Strong experience bullet",
            "template": (
                f"Developed [feature/module] for [system] using {joined}, "
                f"improving [metric] by [X%] and supporting [N] users/requests."
            ),
        },
        {
            "target_section": "Projects",
            "label": "Project bullet with impact",
            "template": (
                f"Built [project name] — a {jd_domain} leveraging {joined}. "
                f"Implemented [key feature], deployed on [platform], "
                f"achieving [measurable result]."
            ),
        },
        {
            "target_section": "Summary",
            "label": "Professional summary opener",
            "template": (
                f"Software Engineer with [X] years of experience in {jd_domain}, "
                f"specializing in {joined}. "
                f"Track record of delivering [outcome] in [context]."
            ),
        },
    ]


# ─── Main Entry Point ────────────────────────────────────────────────

def match_cv_to_jd(
        cv_text: str,
        jd_text: str,
        parsed_cv: dict = None,
        use_semantic: bool = True,
        use_suggestion_engine: bool = True,
) -> dict:
    """
    Main matching function — multi-layer pipeline.

    Args:
        cv_text: raw CV text
        jd_text: raw JD text
        parsed_cv: output của parse_sections() — dict với key "sections"
        use_semantic: có dùng sentence-transformers không
        use_suggestion_engine: có gọi Anthropic API không

    Returns structured dict với đầy đủ scores, issues, suggestions.

    Test case:
        Input CV có: Python, Django, PostgreSQL, Git
        Input JD yêu cầu: Python, Django, Docker, AWS, PostgreSQL, Redis

        Expected output:
        {
            "match_score": ~55-65,
            "skills": {
                "missing_required": ["docker", "aws", "redis"],
                "required_coverage_pct": 50.0,  # 3/6 matched
                ...
            },
            "issues": [
                {"code": "missing_required_skills", "severity": "high", ...},
                ...
            ],
            "score_breakdown": {
                "skill_score": ~50.0,
                "semantic_score": ~40-60,
                "keyword_score": ~45.0,
                "experience_score": ~50.0,
                "structure_score": ~70.0,
            }
        }
    """
    # Normalize input
    cv_sections = {}
    if isinstance(parsed_cv, dict):
        cv_sections = parsed_cv.get("sections", {})

    # Extract skills
    cv_skill_info = extract_skills(cv_text)
    cv_skills = set(cv_skill_info.get("skills", []))
    jd_skill_info = _extract_jd_skills(jd_text)
    required_skills = set(jd_skill_info["required"])
    preferred_skills = set(jd_skill_info["preferred"])

    # ── Layer 1: Skill Score ──
    skill_score, skill_detail = _compute_skill_score(
        cv_skills, required_skills, preferred_skills
    )

    # ── Layer 2: Semantic Score ──
    semantic_score, semantic_detail = (
        _compute_semantic_score(cv_sections, jd_text)
        if use_semantic
        else (0.0, {"status": "disabled"})
    )

    # ── Layer 3: Keyword Score ──
    keyword_score, keyword_detail = _compute_keyword_score(cv_text, jd_text)

    # ── Layer 4: Experience Score ──
    experience_score, experience_detail = _compute_experience_score(
        cv_sections, cv_text, jd_text
    )

    # ── Layer 5: Structure / Bullet Quality Score ──
    structure_score, structure_detail = _compute_structure_score(
        cv_sections, cv_skills, required_skills
    )

    # ── Final Score ──
    # Nếu semantic available, dùng 5-layer; không thì rebalance
    if SEMANTIC_AVAILABLE and use_semantic and semantic_score > 0:
        final_score = (
                skill_score * 0.35
                + semantic_score * 0.25
                + keyword_score * 0.15
                + experience_score * 0.15
                + structure_score * 0.10
        )
    else:
        # Không có semantic → phân bổ lại weight
        final_score = (
                skill_score * 0.45
                + keyword_score * 0.20
                + experience_score * 0.20
                + structure_score * 0.15
        )

    # ── Generate Issues & Suggestions ──
    issues, suggestions = _generate_errors_and_suggestions(
        skill_detail=skill_detail,
        keyword_detail=keyword_detail,
        experience_detail=experience_detail,
        structure_detail=structure_detail,
        semantic_detail=semantic_detail,
        cv_sections=cv_sections,
        jd_text=jd_text,
        use_suggestion_engine=use_suggestion_engine,
    )

    # ── Rewrite examples ──
    missing_terms = (
            skill_detail.get("missing_required", [])[:2]
            + keyword_detail.get("missing", [])[:2]
    )
    rewrite_examples = _build_rewrite_examples(missing_terms, jd_text)

    return {
        "match_score": round(final_score, 2),
        "score_breakdown": {
            "skill_score": round(skill_score, 2),
            "semantic_score": round(semantic_score, 2),
            "keyword_score": round(keyword_score, 2),
            "experience_score": round(experience_score, 2),
            "structure_score": round(structure_score, 2),
        },
        "skills": {
            "cv_skills": sorted(cv_skills),
            "required_skills": sorted(required_skills),
            "preferred_skills": sorted(preferred_skills),
            **skill_detail,
            "score": round(skill_score, 2),
        },
        "keywords": {
            **keyword_detail,
            "score": round(keyword_score, 2),
        },
        "experience": {
            **experience_detail,
            "score": round(experience_score, 2),
        },
        "semantic": {
            **semantic_detail,
            "score": round(semantic_score, 2),
        },
        "structure": {
            **structure_detail,
            "score": round(structure_score, 2),
        },
        "issues": issues,
        "suggestions": suggestions,
        "rewrite_examples": rewrite_examples,
        "meta": {
            "semantic_available": SEMANTIC_AVAILABLE and use_semantic,
            "suggestion_engine_available": SUGGESTION_ENGINE_AVAILABLE,
            "cv_skills_count": len(cv_skills),
            "required_skills_count": len(required_skills),
        },
    }
