from __future__ import annotations

import re
from typing import Dict, Tuple

from src.services.text_preprocess import normalize_for_matching

try:
    from src.services.semantic_matcher import match_bullets_to_jd

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


def compute_semantic_score(
        cv_sections: Dict[str, str],
        cv_text: str,
        jd_text: str,
) -> Tuple[float, Dict]:
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

