# src/services/semantic_matcher.py
"""
Semantic Matching Engine using sentence-transformers.
Dùng để so sánh experience bullets với JD responsibilities
ở mức độ ngữ nghĩa — cái mà TF-IDF không làm được.

Ví dụ TF-IDF fail:
  CV:  "Built a system to handle user authentication flows"
  JD:  "Develop login and registration features"
  => TF-IDF similarity: thấp (ít từ chung)
  => Semantic similarity: cao (~0.82) vì cùng ý nghĩa

Model dùng: all-MiniLM-L6-v2 (nhỏ, nhanh, đủ mạnh cho IT CV)
- Size: ~80MB
- Speed: ~2000 sentences/sec trên CPU
- Phù hợp production không cần GPU
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

from src.data.rules_config import KEYWORD_EXCLUDED_PATTERNS
from src.data.skills_taxonomy import extract_skills
from src.services.text_preprocess import normalize_for_matching

# Lazy import để tránh crash nếu chưa cài
_model = None
_model_load_failed = False
_model_name = "all-MiniLM-L6-v2"
_allow_model_download = os.getenv("SEMANTIC_MODEL_ALLOW_DOWNLOAD", "false").lower() in ("true", "1", "yes")


def _get_model():
    """Lazy load model — chỉ load 1 lần, giữ trong memory."""
    global _model, _model_load_failed
    if _model_load_failed:
        return None
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(
                _model_name,
                local_files_only=not _allow_model_download,
            )
        except Exception:
            _model_load_failed = True
            return None
    return _model


def _extract_bullets(text: str) -> List[str]:
    """
    Tách text thành danh sách bullet/câu có nghĩa.
    Lọc bỏ dòng quá ngắn (header, tên section...).
    """
    lines = []
    for raw in re.split(r"[\n]", text):
        line = raw.strip(" \t-•●▪*–")
        # Chỉ lấy câu đủ dài (>= 6 từ) để có semantic meaning
        if len(line.split()) >= 6:
            lines.append(line)
    return lines


def _extract_jd_responsibilities(jd_text: str) -> List[str]:
    """
    Tách JD thành danh sách responsibilities/requirements.
    Cố gắng lấy phần sau "Responsibilities" hoặc "Requirements".
    """
    # Thử tách theo section header
    lower = jd_text.lower()
    markers = [
        "responsibilities", "what you'll do", "your role",
        "requirements", "qualifications", "what we're looking for",
        "job duties", "key responsibilities"
    ]

    best_start = -1
    for marker in markers:
        idx = lower.find(marker)
        if idx != -1 and (best_start == -1 or idx < best_start):
            best_start = idx

    if best_start != -1:
        relevant_text = jd_text[best_start:]
    else:
        relevant_text = jd_text

    cleaned_lines = [
        line for line in _extract_bullets(relevant_text)
        if not _is_non_matching_jd_line(line)
    ]
    skill_lines = [
        line for line in cleaned_lines
        if extract_skills(line).get("skills")
    ]
    return skill_lines or cleaned_lines


def _is_non_matching_jd_line(line: str) -> bool:
    lowered = str(line or "").lower()
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in KEYWORD_EXCLUDED_PATTERNS)


def _fallback_semantic_result(
    cv_experience_text: str,
    jd_text: str,
    status: str,
    top_k: int = 5,
) -> Dict:
    """
    Lightweight fallback when sentence-transformers is unavailable.

    It is not true embedding semantics, but it is materially better than 0:
    TF-IDF line coverage + overall similarity + JD skill overlap.
    """
    cv_bullets = _extract_bullets(cv_experience_text)
    jd_lines = _extract_jd_responsibilities(jd_text)
    cv_norm = normalize_for_matching(cv_experience_text)
    jd_norm = normalize_for_matching(jd_text)

    if not cv_norm or not jd_norm:
        return {
            "avg_score": 0.0,
            "semantic_score": 0.0,
            "top_matches": [],
            "weak_matches": [],
            "unmatched_jd_lines": jd_lines[:10],
            "status": f"{status}_empty_input",
            "fallback": "tfidf_skill_overlap",
        }

    overall_score = 0.0
    line_coverage_score = 0.0
    avg_best_score = 0.0
    top_matches = []
    weak_matches = []
    unmatched_jd = []

    try:
        overall_matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([cv_norm, jd_norm])
        overall_score = float(sk_cosine(overall_matrix[0:1], overall_matrix[1:2])[0][0]) * 100.0
    except Exception:
        overall_score = 0.0

    if cv_bullets and jd_lines:
        try:
            cv_subset = cv_bullets[:30]
            jd_subset = jd_lines[:20]
            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(cv_subset + jd_subset)
            cv_matrix = matrix[:len(cv_subset)]
            jd_matrix = matrix[len(cv_subset):]
            sim_matrix = sk_cosine(cv_matrix, jd_matrix)

            for i, bullet in enumerate(cv_subset):
                best_jd_idx = int(sim_matrix[i].argmax())
                best_score = float(sim_matrix[i][best_jd_idx]) * 100.0
                entry = {
                    "cv_bullet": bullet[:200],
                    "best_jd_match": jd_subset[best_jd_idx][:200],
                    "score": round(best_score, 2),
                }
                if best_score >= 18:
                    top_matches.append(entry)
                else:
                    weak_matches.append(entry)

            jd_best_scores = []
            for j, jd_line in enumerate(jd_subset):
                max_cv_score = float(sim_matrix[:, j].max()) * 100.0
                jd_best_scores.append(max_cv_score)
                if max_cv_score < 18:
                    unmatched_jd.append({
                        "jd_line": jd_line[:200],
                        "best_cv_score": round(max_cv_score, 2),
                    })

            line_coverage_score = (
                sum(1 for score in jd_best_scores if score >= 18)
                / max(len(jd_best_scores), 1)
            ) * 100.0
            avg_best_score = sum(jd_best_scores) / max(len(jd_best_scores), 1)
        except Exception:
            line_coverage_score = 0.0
            avg_best_score = 0.0

    cv_skills = set(extract_skills(cv_experience_text).get("skills", []))
    jd_skills = set(extract_skills(jd_text).get("skills", []))
    skill_overlap_score = (
        len(cv_skills & jd_skills) / max(len(jd_skills), 1) * 100.0
        if jd_skills else 0.0
    )

    semantic_score = round(
        max(
            overall_score,
            (line_coverage_score * 0.45) + (avg_best_score * 0.25) + (skill_overlap_score * 0.30),
        ),
        2,
    )

    top_matches.sort(key=lambda x: x["score"], reverse=True)
    weak_matches.sort(key=lambda x: x["score"])

    return {
        "avg_score": round(avg_best_score or overall_score, 2),
        "semantic_score": min(semantic_score, 100.0),
        "top_matches": top_matches[:top_k],
        "weak_matches": weak_matches[:top_k],
        "unmatched_jd_lines": unmatched_jd[:5],
        "status": status,
        "fallback": "tfidf_skill_overlap",
        "overall_tfidf_score": round(overall_score, 2),
        "line_coverage_score": round(line_coverage_score, 2),
        "skill_overlap_score": round(skill_overlap_score, 2),
        "cv_bullets_analyzed": len(cv_bullets[:30]),
        "jd_lines_analyzed": len(jd_lines[:20]),
    }


def compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Tính semantic similarity giữa 2 đoạn text (0.0 - 100.0).
    Dùng mean pooling của sentence embeddings.

    Fallback về 0.0 nếu model không available.
    """
    model = _get_model()
    if model is None:
        return 0.0

    if not text_a or not text_b:
        return 0.0

    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

        emb_a = model.encode([text_a[:1000]], convert_to_numpy=True)
        emb_b = model.encode([text_b[:1000]], convert_to_numpy=True)
        score = float(sk_cosine(emb_a, emb_b)[0][0])
        # Cosine range: [-1, 1] → normalize về [0, 100]
        return round(max(0.0, score) * 100.0, 2)
    except Exception:
        return 0.0


def match_bullets_to_jd(
        cv_experience_text: str,
        jd_text: str,
        top_k: int = 5,
        threshold: float = 0.45,
) -> Dict:
    """
    So khớp từng bullet trong CV experience với JD responsibilities.

    Returns:
    {
        "avg_score": float,          # Điểm trung bình overall
        "top_matches": [...],        # Các bullet match tốt
        "weak_matches": [...],       # Bullet match kém với JD
        "unmatched_jd_lines": [...], # JD responsibilities không được cover
        "semantic_score": float      # Điểm dùng cho scoring engine
    }

    Input example:
        cv_experience_text = "Developed REST APIs using Spring Boot..."
        jd_text = "Build and maintain backend services..."
    """
    model = _get_model()

    # Fallback nếu không có model
    if model is None:
        return _fallback_semantic_result(
            cv_experience_text=cv_experience_text,
            jd_text=jd_text,
            status="fallback_model_unavailable",
            top_k=top_k,
        )

    cv_bullets = _extract_bullets(cv_experience_text)
    jd_lines = _extract_jd_responsibilities(jd_text)

    if not cv_bullets or not jd_lines:
        return _fallback_semantic_result(
            cv_experience_text=cv_experience_text,
            jd_text=jd_text,
            status="fallback_empty_input",
            top_k=top_k,
        )

    try:
        import numpy as np
        # Encode tất cả cùng lúc — hiệu quả hơn encode từng cái
        cv_embeddings = model.encode(cv_bullets[:30], convert_to_numpy=True)
        jd_embeddings = model.encode(jd_lines[:20], convert_to_numpy=True)

        # Ma trận similarity: [n_cv_bullets x n_jd_lines]
        sim_matrix = sk_cosine(cv_embeddings, jd_embeddings)

        # Với mỗi CV bullet, tìm JD line match tốt nhất
        top_matches = []
        weak_matches = []

        for i, bullet in enumerate(cv_bullets[:30]):
            best_jd_idx = int(np.argmax(sim_matrix[i]))
            best_score = float(sim_matrix[i][best_jd_idx])

            match_entry = {
                "cv_bullet": bullet[:200],
                "best_jd_match": jd_lines[best_jd_idx][:200],
                "score": round(best_score * 100, 2),
            }

            if best_score >= threshold:
                top_matches.append(match_entry)
            else:
                weak_matches.append(match_entry)

        # JD lines không được cover bởi bất kỳ CV bullet nào
        # (max similarity < threshold)
        unmatched_jd = []
        for j, jd_line in enumerate(jd_lines[:20]):
            max_cv_score = float(np.max(sim_matrix[:, j]))
            if max_cv_score < threshold:
                unmatched_jd.append({
                    "jd_line": jd_line[:200],
                    "best_cv_score": round(max_cv_score * 100, 2),
                })

        # Tính điểm: % CV bullets match được JD + quality của match
        match_rate = len(top_matches) / max(len(cv_bullets[:30]), 1)
        avg_top_score = (
            sum(m["score"] for m in top_matches) / len(top_matches)
            if top_matches else 0.0
        )

        # semantic_score = 70% match rate + 30% avg quality
        semantic_score = round(
            (match_rate * 70.0) + (avg_top_score * 0.3),
            2
        )

        if semantic_score <= 0:
            return _fallback_semantic_result(
                cv_experience_text=cv_experience_text,
                jd_text=jd_text,
                status="fallback_low_embedding_score",
                top_k=top_k,
            )

        # Sort: top matches theo score desc
        top_matches.sort(key=lambda x: x["score"], reverse=True)
        weak_matches.sort(key=lambda x: x["score"])

        return {
            "avg_score": round(
                sum(m["score"] for m in top_matches + weak_matches)
                / max(len(top_matches) + len(weak_matches), 1),
                2
            ),
            "semantic_score": min(semantic_score, 100.0),
            "top_matches": top_matches[:top_k],
            "weak_matches": weak_matches[:top_k],
            "unmatched_jd_lines": unmatched_jd[:5],
            "status": "ok",
            "cv_bullets_analyzed": len(cv_bullets[:30]),
            "jd_lines_analyzed": len(jd_lines[:20]),
        }

    except Exception as e:
        return _fallback_semantic_result(
            cv_experience_text=cv_experience_text,
            jd_text=jd_text,
            status=f"fallback_error: {str(e)}",
            top_k=top_k,
        )


def find_skill_context_in_cv(
        skill_name: str,
        cv_sections: Dict[str, str],
) -> Dict:
    """
    Kiểm tra xem skill có xuất hiện trong đúng section không.

    Ví dụ: "Docker" xuất hiện ở Skills nhưng không có trong
    Experience/Projects bullet nào → thiếu evidence.

    Returns:
    {
        "in_skills_section": bool,
        "in_experience_section": bool,
        "in_projects_section": bool,
        "has_evidence": bool,          # True nếu có ở exp/proj
        "evidence_bullets": [str]       # Các bullet chứa skill
    }
    """
    skill_lower = skill_name.lower()
    result = {
        "in_skills_section": False,
        "in_experience_section": False,
        "in_projects_section": False,
        "has_evidence": False,
        "evidence_bullets": [],
    }

    skills_text = cv_sections.get("Skills", "").lower()
    if skill_lower in skills_text:
        result["in_skills_section"] = True

    for section_name in ("Experience", "Projects"):
        section_text = cv_sections.get(section_name, "")
        if not section_text:
            continue

        for bullet in _extract_bullets(section_text):
            if skill_lower in bullet.lower():
                result["has_evidence"] = True
                if section_name == "Experience":
                    result["in_experience_section"] = True
                else:
                    result["in_projects_section"] = True
                result["evidence_bullets"].append(bullet[:200])

    return result
