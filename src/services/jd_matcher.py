# src/services/jd_matcher.py

import re
from typing import Dict, List, Set

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data.rules_config import (
    JD_PREFERRED_MARKERS,
    KEYWORD_BLACKLIST,
    MAX_KEYWORDS,
)
from src.data.skills_taxonomy import extract_skills
from src.services.text_preprocess import normalize_for_matching, split_lines

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
    if "intern" in lowered:
        return "intern"
    if "junior" in lowered or "fresher" in lowered:
        return "junior"
    if "senior" in lowered:
        return "senior"
    if "lead" in lowered or "principal" in lowered or "architect" in lowered:
        return "lead"
    if "mid-level" in lowered or "mid level" in lowered:
        return "mid"
    return "unknown"


def _is_preferred_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in JD_PREFERRED_MARKERS)


def _extract_jd_skills(jd_text: str) -> Dict[str, List[str]]:
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


def _extract_top_keywords(cv_text: str, jd_text: str, limit: int = MAX_KEYWORDS) -> Dict[str, object]:
    cv_normalized = normalize_for_matching(cv_text)
    jd_normalized = normalize_for_matching(jd_text)

    if not cv_normalized or not jd_normalized:
        return {
            "keywords": [],
            "matched": [],
            "missing": [],
            "score": 0.0,
            "tfidf_similarity": 0.0
        }

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=500
    )

    matrix = vectorizer.fit_transform([cv_normalized, jd_normalized])
    feature_names = vectorizer.get_feature_names_out()
    jd_vector = matrix[1].toarray().ravel()

    ranked = sorted(
        zip(feature_names, jd_vector),
        key=lambda x: x[1],
        reverse=True
    )

    keywords = []
    for term, weight in ranked:
        if weight <= 0:
            continue
        if len(term) < 3:
            continue
        if term in KEYWORD_BLACKLIST:
            continue
        if term.isdigit():
            continue
        keywords.append(term)
        if len(keywords) >= limit:
            break

    matched = [kw for kw in keywords if kw in cv_normalized]
    missing = [kw for kw in keywords if kw not in cv_normalized]

    tfidf_similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100.0
    keyword_score = _safe_ratio(len(matched), len(keywords)) * 100.0 if keywords else 0.0

    return {
        "keywords": keywords,
        "matched": matched,
        "missing": missing,
        "score": round(keyword_score, 2),
        "tfidf_similarity": round(tfidf_similarity, 2),
    }


def _calculate_text_similarity(text_a: str, text_b: str) -> float:
    a = normalize_for_matching(text_a)
    b = normalize_for_matching(text_b)

    if not a or not b:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([a, b])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100.0


def _build_rewrite_examples(missing_terms: List[str]) -> List[dict]:
    focus = missing_terms[:3]
    if not focus:
        return []

    joined = ", ".join(focus)

    return [
        {
            "target_section": "Experience",
            "template": f"Developed and maintained [system/feature] using {joined} to support [business goal], improving [metric] by [X%]."
        },
        {
            "target_section": "Projects",
            "template": f"Built [project name] with {joined}; implemented [API/module], handled [scale/use case], and achieved [measurable result]."
        },
        {
            "target_section": "Summary",
            "template": f"Backend/Software Engineer with hands-on experience in {joined}, focusing on building scalable and maintainable systems."
        }
    ]


def match_cv_to_jd(cv_text: str, jd_text: str, parsed_cv: dict = None) -> dict:
    cv_sections = (parsed_cv or {}).get("sections", {}) if isinstance(parsed_cv, dict) else {}

    cv_skill_info = extract_skills(cv_text)
    cv_skills = set(cv_skill_info.get("skills", []))

    jd_skill_info = _extract_jd_skills(jd_text)
    required_skills = set(jd_skill_info["required"])
    preferred_skills = set(jd_skill_info["preferred"])

    matched_required = sorted(required_skills & cv_skills)
    missing_required = sorted(required_skills - cv_skills)

    matched_preferred = sorted(preferred_skills & cv_skills)
    missing_preferred = sorted(preferred_skills - cv_skills)

    required_ratio = _safe_ratio(len(matched_required), len(required_skills))
    preferred_ratio = _safe_ratio(len(matched_preferred), len(preferred_skills))
    skill_score = (required_ratio * 80.0) + (preferred_ratio * 20.0)

    keyword_result = _extract_top_keywords(cv_text, jd_text)

    experience_text = "\n".join(
        value for key, value in cv_sections.items()
        if key in {"Experience", "Projects", "Summary"}
    ).strip()

    if not experience_text:
        experience_text = cv_text

    responsibility_score = _calculate_text_similarity(experience_text, jd_text)

    cv_years = _extract_years_of_experience(experience_text)
    jd_years = _extract_years_of_experience(jd_text)
    seniority_cv = _detect_seniority(cv_text)
    seniority_jd = _detect_seniority(jd_text)

    if jd_years > 0:
        if cv_years > 0:
            years_score = min(100.0, (cv_years / jd_years) * 100.0)
        else:
            years_score = 35.0
    else:
        years_score = 70.0

    experience_score = (responsibility_score * 0.7) + (years_score * 0.3)

    match_score = (
        skill_score * 0.45
        + keyword_result["score"] * 0.20
        + experience_score * 0.20
        + keyword_result["tfidf_similarity"] * 0.15
    )

    issues = []
    suggestions = []

    if missing_required:
        issues.append({
            "code": "missing_required_skills",
            "severity": "high",
            "title": "Thiếu kỹ năng bắt buộc từ JD",
            "details": missing_required
        })
        suggestions.append({
            "type": "add_missing_skills",
            "target": "skills_and_experience",
            "message": (
                "Nếu bạn thực sự đã dùng các công nghệ này, hãy thêm chúng vào cả mục Skills "
                f"và bullet Experience/Projects: {', '.join(missing_required[:8])}."
            )
        })

    if missing_preferred:
        issues.append({
            "code": "missing_preferred_skills",
            "severity": "medium",
            "title": "Thiếu kỹ năng ưu tiên / nice-to-have",
            "details": missing_preferred
        })
        suggestions.append({
            "type": "enhance_optional_skills",
            "target": "skills",
            "message": (
                "Các kỹ năng nice-to-have sẽ giúp tăng điểm phù hợp nếu bạn có kinh nghiệm thực tế: "
                f"{', '.join(missing_preferred[:8])}."
            )
        })

    if keyword_result["missing"]:
        issues.append({
            "code": "keyword_gap",
            "severity": "medium",
            "title": "CV chưa cover đủ từ khóa quan trọng của JD",
            "details": keyword_result["missing"][:10]
        })
        suggestions.append({
            "type": "keyword_alignment",
            "target": "summary_and_experience",
            "message": (
                "Hãy viết lại Summary/Experience để chứa đúng thuật ngữ gần JD hơn, ví dụ: "
                + ", ".join(keyword_result["missing"][:8])
            )
        })

    if experience_score < 50:
        issues.append({
            "code": "weak_experience_alignment",
            "severity": "high",
            "title": "Mô tả kinh nghiệm chưa bám sát trách nhiệm trong JD",
            "details": [
                f"responsibility_score={round(responsibility_score, 2)}",
                f"years_score={round(years_score, 2)}"
            ]
        })
        suggestions.append({
            "type": "rewrite_experience",
            "target": "experience",
            "message": "Viết lại bullet theo trách nhiệm trong JD: bạn đã xây dựng gì, dùng công nghệ gì, tác động gì, kết quả gì."
        })

    if seniority_jd != "unknown" and seniority_cv != "unknown" and seniority_jd != seniority_cv:
        issues.append({
            "code": "seniority_gap",
            "severity": "low",
            "title": "Cấp độ CV và JD có dấu hiệu lệch nhau",
            "details": [f"cv={seniority_cv}", f"jd={seniority_jd}"]
        })

    rewrite_examples = _build_rewrite_examples(
        missing_required[:2] + keyword_result["missing"][:2]
    )

    return {
        "match_score": round(match_score, 2),
        "skills": {
            "score": round(skill_score, 2),
            "cv_skills": sorted(cv_skills),
            "required_skills": sorted(required_skills),
            "preferred_skills": sorted(preferred_skills),
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_preferred": matched_preferred,
            "missing_preferred": missing_preferred,
        },
        "keywords": keyword_result,
        "experience": {
            "score": round(experience_score, 2),
            "responsibility_score": round(responsibility_score, 2),
            "cv_years": cv_years,
            "jd_years": jd_years,
            "years_score": round(years_score, 2),
            "cv_seniority": seniority_cv,
            "jd_seniority": seniority_jd,
        },
        "issues": issues,
        "suggestions": suggestions,
        "rewrite_examples": rewrite_examples,
    }

