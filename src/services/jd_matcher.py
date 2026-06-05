
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from src.data.rules_config import (
    JD_PREFERRED_MARKERS,
    KEYWORD_EXCLUDED_PATTERNS,
    KEYWORD_BLACKLIST,
    MAX_KEYWORDS,
)
from src.data.skills_taxonomy import CANONICAL_TO_CATEGORY, extract_skills
from src.services.scoring import compute_scorecard
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

#Neu co module sematic matcher thi dung khong thi fallback ve TF-IDF
# Import suggestion engine
try:
    from src.services.suggestion_engine import generate_bulk_suggestions

    SUGGESTION_ENGINE_AVAILABLE = True
except ImportError:
    SUGGESTION_ENGINE_AVAILABLE = False


# ─── Utility helpers ────────────────────────────────────────────────
# Tranh loi chia cho 0
def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator

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


def _extract_years_of_experience(text: str) -> int:
    return int(_extract_experience_months(text) // 12)

#Du doan level của CV/JD
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

#Kiem tra xem co tu khoa "uu tien" trong JD không
def _is_preferred_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in JD_PREFERRED_MARKERS)

#Xac định dòng đó thuộc phần nào JD
def _detect_jd_skill_section(line: str) -> str | None:
    normalized = re.sub(r"[^a-z\s/&-]", " ", (line or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip(" :-")
    if not normalized:
        return None

    section_markers = {
        "required": (
            "requirements",
            "requirement",
            "required qualifications",
            "minimum qualifications",
            "qualifications",
            "must have",
            "what you need",
        ),
        "preferred": (
            "preferred",
            "preferred qualifications",
            "nice to have",
            "nice to haves",
            "bonus",
            "plus",
        ),
        "responsibilities": (
            "responsibilities",
            "key responsibilities",
            "what you will do",
            "what you'll do",
            "your role",
            "job duties",
        ),
        "benefits": (
            "benefits",
            "why join us",
            "what we offer",
            "perks",
            "compensation and benefits",
        ),
    }
    for section_name, markers in section_markers.items():
        if normalized in markers:
            return section_name
        if any(normalized.startswith(marker) for marker in markers):
            return section_name
    return None

#Loai bo nhung tu khoa vo nghĩa khi lưu vào danh sách Skill
def _detect_jd_noise_section(line: str) -> str | None:
    normalized = re.sub(r"[^a-z\s/&-]", " ", (line or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip(" :-")
    if not normalized:
        return None

    noise_markers = (
        "about us",
        "about the company",
        "company overview",
        "overview",
        "who we are",
        "benefits",
        "salary",
        "compensation",
        "work environment",
        "working environment",
        "location",
        "address",
        "working hours",
        "working time",
        "how to apply",
        "application process",
        "recruitment process",
        "interview process",
    )
    if normalized in noise_markers:
        return "noise"
    if any(normalized.startswith(marker) for marker in noise_markers):
        return "noise"
    return None


def _is_jd_noise_line(line: str) -> bool:
    cleaned = re.sub(r"\s+", " ", str(line or "")).strip()
    if not cleaned:
        return True
    if _detect_jd_skill_section(cleaned) == "benefits" or _detect_jd_noise_section(cleaned):
        return True
    if re.search(r"\b(street|road|avenue|district|building|floor|city|province|ward)\b", cleaned, re.IGNORECASE):
        return True
    return any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in KEYWORD_EXCLUDED_PATTERNS)


def _line_has_jd_signal(line: str) -> bool:
    lowered = str(line or "").lower()
    if extract_skills(line).get("skills"):
        return True
    return bool(re.search(
        r"\b(required|requirement|must|need|experience|knowledge|responsible|responsibilities|"
        r"develop|build|design|implement|maintain|optimize|deploy|manage|collaborate)\b",
        lowered,
    ))


def _filter_jd_for_matching(jd_text: str) -> str:
    lines = split_lines(jd_text)
    if not lines:
        return jd_text or ""

    relevant_sections = {"required", "preferred", "responsibilities"}
    current_section = None
    saw_relevant_section = False
    kept = []

    for line in lines:
        detected = _detect_jd_skill_section(line)
        noise_section = _detect_jd_noise_section(line)

        if detected in relevant_sections:
            current_section = detected
            saw_relevant_section = True
            continue
        if detected == "benefits" or noise_section:
            current_section = "ignore"
            continue

        if current_section in relevant_sections:
            if not _is_jd_noise_line(line):
                kept.append(line)
            continue

        if not saw_relevant_section and not _is_jd_noise_line(line) and _line_has_jd_signal(line):
            kept.append(line)

    if kept:
        return "\n".join(kept)

    fallback = [
        line for line in lines
        if not _is_jd_noise_line(line)
    ]
    return "\n".join(fallback) if fallback else (jd_text or "")


EDUCATION_REQUIREMENT_PATTERNS = (
    r"\bbachelor'?s?\s+degree\b",
    r"\bb\.?\s*s\.?\b",
    r"\bbsc\b",
    r"\bb\.?\s*sc\.?\b",
    r"\bdegree\s+in\b",
    r"\bcomputer\s+science\b",
    r"\bsoftware\s+engineering\b",
    r"\binformation\s+technology\b",
    r"\binformation\s+systems\b",
)


def _is_education_requirement_line(line: str) -> bool:
    lowered = str(line or "").lower()
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in EDUCATION_REQUIREMENT_PATTERNS)


def _extract_education_requirements(jd_text: str) -> List[str]:
    requirements = []
    seen = set()
    for line in split_lines(jd_text):
        cleaned = re.sub(r"\s+", " ", line or "").strip()
        if not cleaned or not _is_education_requirement_line(cleaned):
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            requirements.append(cleaned)
    return requirements


def _education_text(cv_sections: Dict[str, str], cv_text: str) -> str:
    section_text = (cv_sections.get("Education", "") or "").strip()
    return section_text or (cv_text or "")


def _education_requirement_covered(requirement: str, education_text: str) -> bool:
    req = str(requirement or "").lower()
    edu = str(education_text or "").lower()
    if not req:
        return True
    if not edu:
        return False

    bachelor_required = bool(re.search(r"\b(bachelor'?s?\s+degree|b\.?\s*s\.?|bsc|b\.?\s*sc\.?)\b", req))
    degree_required = bachelor_required or "degree in" in req
    if degree_required and not re.search(r"\b(bachelor|b\.?\s*s\.?|bsc|b\.?\s*sc\.?|degree)\b", edu):
        return False

    field_markers = (
        "computer science",
        "software engineering",
        "information technology",
        "information systems",
    )
    requested_fields = [field for field in field_markers if field in req]
    if requested_fields and not any(field in edu for field in requested_fields):
        return False

    return True


def _compute_education_requirement_match(
        cv_sections: Dict[str, str],
        cv_text: str,
        jd_text: str,
) -> Dict:
    requirements = _extract_education_requirements(jd_text)
    education_text = _education_text(cv_sections, cv_text)
    covered = []
    missing = []
    for requirement in requirements:
        if _education_requirement_covered(requirement, education_text):
            covered.append(requirement)
        else:
            missing.append(requirement)

    return {
        "requirements": requirements,
        "covered": covered,
        "missing": missing,
        "coverage_pct": round(_safe_ratio(len(covered), len(requirements)) * 100, 1),
        "education_excerpt": _truncate(education_text, 260),
    }


def _filter_covered_education_unmatched_lines(unmatched_lines: List, education_detail: Dict) -> List:
    covered = set((education_detail or {}).get("covered", []))
    if not covered:
        return unmatched_lines or []
    return [
        item for item in unmatched_lines or []
        if not (
            _is_education_requirement_line(_unmatched_jd_text(item))
            and any(_same_normalized_line(_unmatched_jd_text(item), line) for line in covered)
        )
    ]


def _filter_covered_skill_unmatched_lines(unmatched_lines: List, cv_skills: Set[str]) -> List:
    filtered = []
    for item in unmatched_lines or []:
        line = _unmatched_jd_text(item)
        line_skills = set(extract_skills(line).get("skills", []))
        if line_skills and line_skills <= cv_skills:
            continue
        filtered.append(item)
    return filtered


SOFT_SKILL_MAP = {
    "logical reasoning": [
        "root cause analysis",
        "debugging",
        "problem solving",
        "troubleshooting",
        "requirement analysis",
        "algorithm optimization",
        "algorithmic optimization",
    ],
    "reasoning": [
        "root cause analysis",
        "debugging",
        "problem solving",
        "troubleshooting",
        "requirement analysis",
        "algorithm optimization",
    ],
    "english documentation": [
        "technical documentation",
        "api specification",
        "swagger",
        "openapi",
        "spring documentation",
        "documentation",
    ],
    "technical documentation": [
        "technical documentation",
        "api specification",
        "swagger",
        "openapi",
        "documentation",
    ],
    "communication": [
        "stakeholder",
        "collaborated",
        "cross-functional",
        "requirement analysis",
        "documentation",
    ],
}


DOMAIN_KNOWLEDGE_MAP = {
    "database design": [
        "database design",
        "relational database schemas",
        "database schemas",
        "erd",
        "normalized relational databases",
        "normalization",
        "sql migration",
        "migration scripts",
        "schema design",
    ],
    "database fundamentals": [
        "database design",
        "relational database schemas",
        "erd",
        "normalized relational databases",
        "sql migration",
        "schema design",
    ],
    "algorithmic efficiency": [
        "algorithmic efficiency",
        "algorithmic optimization",
        "algorithm optimization",
        "optimized algorithm",
        "data structures",
    ],
}


REQUIREMENT_SECTION_STRENGTH = {
    "Experience": 100,
    "Projects": 90,
    "Education": 100,
    "Skills": 65,
    "Summary": 45,
}


def _requirement_lines(jd_text: str) -> List[str]:
    lines = []
    seen = set()
    for line in split_lines(jd_text):
        if _detect_jd_skill_section(line) or _is_jd_noise_line(line):
            continue
        cleaned = re.sub(r"\s+", " ", line or "").strip(" -:*")
        if len(cleaned.split()) < 3:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            lines.append(cleaned)
    return lines


def _requirement_category(line: str) -> str:
    lowered = str(line or "").lower()
    if _is_education_requirement_line(line):
        return "education"

    if re.search(r"\b(\d+\+?\s*(years?|yrs?)|senior|junior|fresher|internship|experience)\b", lowered):
        if not extract_skills(line).get("skills"):
            return "experience"

    if any(term in lowered for term in SOFT_SKILL_MAP):
        return "soft_skill"
    if any(term in lowered for term in DOMAIN_KNOWLEDGE_MAP):
        return "domain_knowledge"

    skills = extract_skills(line).get("skills", [])
    categories = {CANONICAL_TO_CATEGORY.get(skill, "") for skill in skills}
    if categories & {"programming_languages", "frameworks_backend", "frameworks_frontend", "database", "cloud_devops", "testing_tools"}:
        return "technical_skill"
    if categories & {"architectures_concepts", "data_ai", "tools_management"}:
        return "domain_knowledge"
    if skills:
        return "technical_skill"
    return "responsibility"


def _section_texts(cv_sections: Dict[str, str], cv_text: str) -> Dict[str, str]:
    if not cv_sections:
        return {"Raw CV": cv_text or ""}
    return {
        "Summary": cv_sections.get("Summary", "") or "",
        "Skills": cv_sections.get("Skills", "") or "",
        "Experience": cv_sections.get("Experience", "") or "",
        "Projects": cv_sections.get("Projects", "") or "",
        "Education": cv_sections.get("Education", "") or "",
    }


def _contains_any(text: str, terms: List[str]) -> bool:
    normalized = normalize_for_matching(text)
    return any(normalize_for_matching(term) in normalized for term in terms)


def _requirement_alias_terms(line: str, category: str) -> List[str]:
    lowered = str(line or "").lower()
    terms = [line]
    for key, aliases in SOFT_SKILL_MAP.items():
        if key in lowered:
            terms.extend(aliases)
    for key, aliases in DOMAIN_KNOWLEDGE_MAP.items():
        if key in lowered:
            terms.extend(aliases)
    if category == "soft_skill":
        for aliases in SOFT_SKILL_MAP.values():
            if any(alias in lowered for alias in aliases):
                terms.extend(aliases)
    if category == "domain_knowledge":
        for aliases in DOMAIN_KNOWLEDGE_MAP.values():
            if any(alias in lowered for alias in aliases):
                terms.extend(aliases)
    return list(dict.fromkeys(term for term in terms if term))


def _section_matches_requirement(section_text: str, line: str, category: str, line_skills: Set[str]) -> bool:
    if not section_text:
        return False
    if category == "education":
        return _education_requirement_covered(line, section_text)
    section_skills = set(extract_skills(section_text).get("skills", []))
    if line_skills and line_skills <= section_skills:
        return True
    if line_skills and (line_skills & section_skills) and category in {"technical_skill", "domain_knowledge"}:
        return True
    if _contains_any(section_text, _requirement_alias_terms(line, category)):
        return True
    try:
        return _tfidf_similarity(section_text, line) >= 28.0
    except Exception:
        return False


def _score_requirement_evidence(line: str, category: str, section_text_map: Dict[str, str]) -> Dict:
    line_skills = set(extract_skills(line).get("skills", []))
    preferred_scopes = {
        "education": ["Education"],
        "technical_skill": ["Experience", "Projects", "Skills", "Education"],
        "domain_knowledge": ["Experience", "Projects", "Education", "Skills"],
        "soft_skill": ["Experience", "Projects", "Summary"],
        "experience": ["Experience", "Projects", "Summary"],
        "responsibility": ["Experience", "Projects"],
    }.get(category, ["Experience", "Projects", "Skills"])

    matched_sections = []
    best_score = 0.0
    best_section = ""
    for section in preferred_scopes:
        text = section_text_map.get(section, "")
        if _section_matches_requirement(text, line, category, line_skills):
            section_score = REQUIREMENT_SECTION_STRENGTH.get(section, 50)
            matched_sections.append(section)
            if section_score > best_score:
                best_score = float(section_score)
                best_section = section

    if len(matched_sections) > 1 and best_score < 100:
        best_score = min(100.0, best_score + 10.0)

    return {
        "requirement": line,
        "category": category,
        "score": round(best_score, 2),
        "covered": best_score >= 60,
        "best_section": best_section,
        "matched_sections": matched_sections,
        "skills": sorted(line_skills),
    }


def _compute_requirement_coverage(
        cv_sections: Dict[str, str],
        cv_text: str,
        jd_text: str,
) -> Dict:
    section_text_map = _section_texts(cv_sections, cv_text)
    requirements = []
    for line in _requirement_lines(jd_text):
        category = _requirement_category(line)
        requirements.append(_score_requirement_evidence(line, category, section_text_map))

    if not requirements:
        return {
            "score": 0.0,
            "requirements": [],
            "covered": [],
            "missing": [],
            "coverage_pct": 0.0,
        }

    score = sum(item["score"] for item in requirements) / len(requirements)
    covered = [item for item in requirements if item["covered"]]
    missing = [item for item in requirements if not item["covered"]]
    return {
        "score": round(score, 2),
        "requirements": requirements,
        "covered": covered,
        "missing": missing,
        "coverage_pct": round(len(covered) / max(len(requirements), 1) * 100.0, 1),
    }


def _filter_covered_requirement_unmatched_lines(unmatched_lines: List, requirement_detail: Dict) -> List:
    covered_lines = [item.get("requirement", "") for item in (requirement_detail or {}).get("covered", [])]
    if not covered_lines:
        return unmatched_lines or []
    return [
        item for item in unmatched_lines or []
        if not any(_same_normalized_line(_unmatched_jd_text(item), line) for line in covered_lines)
    ]


def _is_excluded_keyword(term: str) -> bool:
    lowered = term.strip().lower()
    if not lowered or lowered in KEYWORD_BLACKLIST or lowered.isdigit():
        return True
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in KEYWORD_EXCLUDED_PATTERNS)


# ─── Layer 1: Skill Matching ─────────────────────────────────────────
#Tách Skill làm 3 nhóm required, preferred, contextual
def _extract_jd_skills(jd_text: str) -> Dict[str, List[str]]:
    """
    Tách skills từ JD thành required vs preferred.
    Logic: line chứa "preferred/nice-to-have" → preferred, còn lại → required.
    """
    required: Set[str] = set()
    preferred: Set[str] = set()
    contextual: Set[str] = set()
    current_section = None

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
        cv_text: str,
        jd_text: str,
) -> Tuple[float, Dict]:
    """
    Layer 2: So sánh CV experience bullets vs JD responsibilities
    dùng sentence-transformers.

    Nếu model không available → fallback về TF-IDF similarity.

    Returns: (score_0_100, detail_dict)
    """
    experience_text, cv_source = _semantic_cv_text(cv_sections, cv_text)

    if SEMANTIC_AVAILABLE:
        result = match_bullets_to_jd(
            cv_experience_text=experience_text,
            jd_text=jd_text,
            threshold=0.6,
        )
        score = result.get("semantic_score", 0.0)
        result["cv_source"] = cv_source
        result["cv_text_analyzed_excerpt"] = _truncate(experience_text, 500)
        return score, result
    else:
        # Fallback TF-IDF
        score = _tfidf_similarity(experience_text, jd_text)
        return score, {
            "status": "fallback_tfidf",
            "semantic_score": score,
            "cv_source": cv_source,
            "cv_text_analyzed_excerpt": _truncate(experience_text, 500),
            "top_matches": [],
            "weak_matches": [],
            "unmatched_jd_lines": [],
        }


def _looks_like_copied_jd(text: str) -> bool:
    lowered = str(text or "").lower()
    markers = (
        "requirements:",
        "responsibilities:",
        "preferred:",
        "benefits:",
        "we are looking for",
        "what you will do",
        "what you'll do",
    )
    return any(marker in lowered for marker in markers)


def _semantic_cv_text(cv_sections: Dict[str, str], cv_text: str) -> Tuple[str, str]:
    available_sections = [
        sec for sec in ("Experience", "Projects")
        if (cv_sections.get(sec, "") or "").strip()
    ]
    experience_text = "\n".join(cv_sections.get(sec, "") for sec in available_sections).strip()
    if experience_text:
        return experience_text, " + ".join(available_sections)

    if not cv_sections:
        return cv_text, "raw_cv_text"

    summary_text = (cv_sections.get("Summary", "") or "").strip()
    if summary_text and not _looks_like_copied_jd(summary_text):
        return summary_text, "Summary"

    return "", "none"


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    a = normalize_for_matching(text_a)
    b = normalize_for_matching(text_b)
    if not a or not b:
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

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


def _unmatched_jd_text(item) -> str:
    if isinstance(item, dict):
        return str(item.get("jd_line") or item.get("excerpt") or item.get("text") or "")
    return str(item or "")


def _same_normalized_line(left: str, right: str) -> bool:
    normalized_left = normalize_for_matching(left)
    normalized_right = normalize_for_matching(right)
    if not normalized_left or not normalized_right:
        return False
    return normalized_left == normalized_right or normalized_left in normalized_right or normalized_right in normalized_left


def _unmatched_jd_evidence(items: List, limit: int = 3) -> List[str]:
    evidence = []
    for item in items or []:
        line = _unmatched_jd_text(item)
        line = re.sub(r"\s+", " ", str(line or "")).strip()
        if not line:
            continue
        evidence.append(line[:100])
        if len(evidence) >= limit:
            break
    return evidence


def _add_issue_localization(issue: Dict) -> None:
    code = issue.get("code", "")
    evidence = issue.get("evidence", [])
    details = _evidence_to_details(evidence)
    joined = ", ".join(details[:5])
    explanation_vi = issue.get("explanation", "")

    explanations_en = {
        "missing_required_skills": (
            f"The JD requires {len(evidence)} skills that are not clearly represented in the CV: {joined}."
        ),
        "missing_preferred_skills": (
            f"These nice-to-have skills are not shown yet: {joined}. Adding real experience with them can improve fit."
        ),
        "skill_no_evidence": (
            f"These skills appear in Skills but are not supported by Experience/Projects evidence: {joined}."
        ),
        "keyword_gap": (
            f"The CV does not naturally address important JD keywords: {joined}."
        ),
        "missing_metrics": (
            "Experience/Projects bullets do not include measurable outcomes such as users, APIs, response time, "
            "throughput, modules, or percentage improvements."
        ),
        "weak_experience_alignment": (
            "The Experience/Projects content does not align strongly with the JD responsibilities. Rewrite bullets "
            "to reflect similar work you have actually performed."
        ),
        "seniority_gap": (
            "The seniority level communicated by the CV does not match the level requested by the JD."
        ),
        "uncovered_responsibilities": (
            "Several JD responsibilities are not addressed by any Experience/Projects bullet."
        ),
    }

    issue["explanation_vi"] = explanation_vi
    issue["explanation_en"] = explanations_en.get(
        code,
        "Review this issue and update the CV using the evidence shown in the report.",
    )


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
    jd_skill_set = set(extract_skills(jd_text).get("skills", []))

    if not cv_norm or not jd_norm:
        return 0.0, {"keywords": [], "matched": [], "missing": [], "tfidf_similarity": 0.0}

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

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
            if weight <= 0 or len(term) < 3:
                continue
            if _is_excluded_keyword(term):
                continue
            if jd_skill_set and term not in jd_skill_set:
                continue
            keywords.append(term)
            if len(keywords) >= limit:
                break

        for skill in sorted(jd_skill_set):
            if _is_excluded_keyword(skill):
                continue
            if skill not in keywords:
                keywords.append(skill)
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
    Layer 4: Experience duration only.

    Returns: (score_0_100, detail_dict)
    """
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
        duration_score = min(100.0, (cv_months / jd_months) * 100.0) if cv_months > 0 else 35.0
    else:
        duration_score = 75.0 if cv_months > 0 else 60.0

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
    2. Tỷ lệ bullets có metric

    Returns: (score_0_100, detail_dict)
    """
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
    penalty += len(skills_no_evidence) * 8  # 8 điểm mỗi skill thiếu evidence
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


# ─── Error & Suggestion Generator ────────────────────────────────────

def _generate_errors_and_suggestions(
        skill_detail: Dict,
        keyword_detail: Dict,
        experience_detail: Dict,
        structure_detail: Dict,
        semantic_detail: Dict,
        education_detail: Dict,
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
                f"trong bất kỳ dòng mô tả nào của Experience/Projects: {', '.join(no_evidence)}. "
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
                f"CV chưa đáp ứng {len(missing_kw)} từ khóa quan trọng từ JD: "
                f"{', '.join(missing_kw[:5])}."
            ),
        })

    missing_education = education_detail.get("missing", []) if education_detail else []
    if missing_education:
        issues.append({
            "code": "education_requirement_gap",
            "error_type": "education_gap",
            "severity": "medium",
            "section": "Education",
            "evidence": missing_education[:3],
            "explanation": (
                "JD cÃ³ yÃªu cáº§u báº±ng cáº¥p/ngÃ nh há»c nhÆ°ng má»¥c Education trong CV chÆ°a thá»ƒ hiá»‡n rÃµ: "
                f"{', '.join(missing_education[:3])}."
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
            "evidence": metricless_excerpts[:3] or ["Không có dòng mô tả nào chứa số liệu đo lường."],
            "explanation": (
                f"Không có dòng mô tả nào trong {total_bullets} dòng mô tả chứa số liệu cụ thể "
                f"(%, số user, số API, thời gian...). "
                f"CV IT mạnh cần ít nhất 2-3 dòng mô tả có con số cụ thể."
            ),
        })

    # Experience content alignment is handled by semantic/keyword checks.
    exp_score = 100.0
    if exp_score < 45:
        issues.append({
            "code": "weak_experience_alignment",
            "error_type": "content_relevance",
            "severity": "high",
            "section": "Experience",
            "evidence": [
                f"Mức khớp nội dung kinh nghiệm với JD: {exp_score:.1f}/100",
                f"Số năm trong CV: {experience_detail.get('cv_years', 0)}; JD yêu cầu: {experience_detail.get('jd_years', 0)}",
                "Tiêu chí: dòng mô tả nên thể hiện đúng công việc chính trong JD, công nghệ liên quan, phạm vi bạn phụ trách và kết quả đạt được.",
            ],
            "explanation": (
                "Nội dung Experience/Projects chưa bám sát trách nhiệm trong JD. "
                "Hãy chọn 3-5 trách nhiệm quan trọng nhất trong JD rồi viết lại dòng mô tả để cho thấy bạn đã làm việc tương tự, dùng công nghệ phù hợp và có kết quả rõ ràng."
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
    education_covered = set((education_detail or {}).get("covered", []))
    unmatched_jd = [
        item for item in semantic_detail.get("unmatched_jd_lines", [])
        if not (
            _is_education_requirement_line(_unmatched_jd_text(item))
            and any(_same_normalized_line(_unmatched_jd_text(item), covered) for covered in education_covered)
        )
    ]
    unmatched_evidence = _unmatched_jd_evidence(unmatched_jd)
    if len(unmatched_evidence) >= 3:
        issues.append({
            "code": "uncovered_responsibilities",
            "error_type": "content_relevance",
            "severity": "medium",
            "section": "Experience",
            "evidence": unmatched_evidence,
            "explanation": (
                f"{len(unmatched_jd)} trách nhiệm trong JD chưa được CV đáp ứng "
                f"bởi bất kỳ dòng mô tả nào trong Experience/Projects."
            ),
        })

    # Keep compatibility with suggestion_engine, which reads details.
    for issue in issues:
        issue.setdefault("details", _evidence_to_details(issue.get("evidence", [])))
        _add_issue_localization(issue)

    # --- Generate suggested_fix cho từng issue ---
    if use_suggestion_engine and SUGGESTION_ENGINE_AVAILABLE:
        issues = generate_bulk_suggestions(
            errors=issues,
            cv_sections=cv_sections,
            jd_text=jd_text,
            max_api_calls=5,
        )
    else:
        # Thêm suggested_fix rule-based nếu không có suggestion engine
        from src.services.suggestion_engine import _get_rule_based_fix
        for issue in issues:
            localized_fix = _get_rule_based_fix(
                issue["code"], issue.get("evidence", []), issue.get("section", "")
            )
            issue["suggested_fix"] = localized_fix["meaning_vi"]
            issue["suggested_fix_en"] = localized_fix["fix_en"]
            issue["fix_meaning_vi"] = localized_fix["meaning_vi"]
            issue["fix_meaning_en"] = localized_fix["meaning_en"]

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
            "meaning_vi": (
                "Mẫu này nói rằng bạn đã phát triển một tính năng hoặc module bằng các công nghệ liên quan, "
                "có kết quả đo được và có phạm vi sử dụng rõ ràng."
            ),
            "meaning_en": (
                "This shows what you built, which relevant technologies you used, the measurable result, "
                "and the usage scale."
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
            "meaning_vi": (
                "Mẫu này giúp mô tả project theo hướng có mục tiêu, công nghệ, tính năng chính, cách triển khai "
                "và kết quả đạt được."
            ),
            "meaning_en": (
                "This frames a project with purpose, technology, key feature, deployment context, and outcome."
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
            "meaning_vi": (
                "Mẫu này dùng cho phần Summary để nêu số năm kinh nghiệm, lĩnh vực, công nghệ trọng tâm "
                "và kết quả nổi bật."
            ),
            "meaning_en": (
                "This summary states years of experience, domain, core technologies, and a concrete delivery record."
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
        use_suggestion_engine: có gọi Gemini API không

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
    jd_match_text = _filter_jd_for_matching(jd_text)

    # Extract skills
    cv_skill_info = extract_skills(cv_text)
    cv_skills = set(cv_skill_info.get("skills", []))
    jd_skill_info = _extract_jd_skills(jd_match_text)
    required_skills = set(jd_skill_info["required"])
    preferred_skills = set(jd_skill_info["preferred"])
    contextual_skills = set(jd_skill_info.get("contextual", []))

    # ── Layer 1: Skill Score ──
    skill_score, skill_detail = _compute_skill_score(
        cv_skills, required_skills, preferred_skills
    )

    # ── Layer 2: Semantic Score ──
    semantic_score, semantic_detail = (
        _compute_semantic_score(cv_sections, cv_text, jd_match_text)
        if use_semantic
        else (0.0, {"status": "disabled"})
    )
    education_detail = _compute_education_requirement_match(cv_sections, cv_text, jd_match_text)
    semantic_detail["unmatched_jd_lines"] = _filter_covered_education_unmatched_lines(
        semantic_detail.get("unmatched_jd_lines", []),
        education_detail,
    )
    semantic_detail["unmatched_jd_lines"] = _filter_covered_skill_unmatched_lines(
        semantic_detail.get("unmatched_jd_lines", []),
        cv_skills,
    )
    requirement_detail = _compute_requirement_coverage(cv_sections, cv_text, jd_match_text)
    if requirement_detail.get("score", 0.0) > semantic_score:
        semantic_score = float(requirement_detail.get("score", 0.0))
        semantic_detail["semantic_score"] = semantic_score
        semantic_detail["selected_semantic_scorer"] = "section_aware_requirement_coverage"
    semantic_detail["requirement_coverage_score"] = requirement_detail.get("score", 0.0)
    semantic_detail["requirement_coverage_pct"] = requirement_detail.get("coverage_pct", 0.0)
    semantic_detail["requirements_analyzed"] = len(requirement_detail.get("requirements", []))
    semantic_detail["unmatched_jd_lines"] = _filter_covered_requirement_unmatched_lines(
        semantic_detail.get("unmatched_jd_lines", []),
        requirement_detail,
    )

    # ── Layer 3: Keyword Score ──
    keyword_score, keyword_detail = _compute_keyword_score(cv_text, jd_match_text)

    # ── Layer 4: Experience Score ──
    experience_score, experience_detail = _compute_experience_score(
        cv_sections, cv_text, jd_match_text
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
    semantic_is_active = bool(
        use_semantic
        and semantic_detail.get("model_loaded") is True
        and semantic_detail.get("status") == "ok"
        and semantic_score > 0
    )
    scorecard = compute_scorecard(
        {
            "skill_score": skill_score,
            "semantic_score": semantic_score,
            "keyword_score": keyword_score,
            "experience_score": experience_score,
            "jd_structure_score": structure_score,
            "section_score": 0.0,
        },
        semantic_available=semantic_is_active,
    )
    final_score = scorecard["score_axes"]["overall_fit"]

    issues, suggestions = _generate_errors_and_suggestions(
        skill_detail=skill_detail,
        keyword_detail=keyword_detail,
        experience_detail=experience_detail,
        structure_detail=structure_detail,
        semantic_detail=semantic_detail,
        education_detail=education_detail,
        cv_sections=cv_sections,
        jd_text=jd_match_text,
        use_suggestion_engine=use_suggestion_engine,
    )

    # ── Rewrite examples ──
    missing_terms = (
            skill_detail.get("missing_required", [])[:2]
            + keyword_detail.get("missing", [])[:2]
    )
    rewrite_examples = _build_rewrite_examples(missing_terms, jd_match_text)

    return {
        "match_score": round(final_score, 2),
        "fit_score": round(final_score, 2),
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
            "contextual_skills": sorted(contextual_skills),
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
        "education": education_detail,
        "requirements": requirement_detail,
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
            "semantic_available": semantic_is_active,
            "suggestion_engine_available": SUGGESTION_ENGINE_AVAILABLE,
            "cv_skills_count": len(cv_skills),
            "required_skills_count": len(required_skills),
            "jd_filter_applied": jd_match_text.strip() != (jd_text or "").strip(),
            "jd_original_chars": len(jd_text or ""),
            "jd_matching_chars": len(jd_match_text or ""),
            "jd_matching_excerpt": jd_match_text[:500],
        },
    }
