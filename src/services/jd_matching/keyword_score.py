from __future__ import annotations

import re
from typing import Dict, Tuple

from src.data.rules_config import KEYWORD_BLACKLIST, KEYWORD_EXCLUDED_PATTERNS, MAX_KEYWORDS
from src.data.skills_taxonomy import extract_skills
from src.services.text_preprocess import normalize_for_matching


def _is_excluded_keyword(term: str) -> bool:
    lowered = term.strip().lower()
    if not lowered or lowered in KEYWORD_BLACKLIST or lowered.isdigit():
        return True
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in KEYWORD_EXCLUDED_PATTERNS)


def compute_keyword_score(
        cv_text: str,
        jd_text: str,
        limit: int = MAX_KEYWORDS,
) -> Tuple[float, Dict]:
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

        from src.services.jd_matching.pipeline import _safe_ratio

        kw_score = _safe_ratio(len(matched), len(keywords)) * 100.0 if keywords else 0.0

        return kw_score, {
            "keywords": keywords[:15],
            "matched": matched[:10],
            "missing": missing[:10],
            "tfidf_similarity": round(tfidf_sim, 2),
        }
    except Exception:
        return 0.0, {"keywords": [], "matched": [], "missing": [], "tfidf_similarity": 0.0}
