from __future__ import annotations

from typing import Dict, Iterable


REPORT_SCHEMA_VERSION = "2.0"
SCORING_VERSION = "2026-04-fit-centric-v1"

FINAL_SCORE_COMPONENT_WEIGHTS = {
    "skill_score": 40.0,
    "semantic_score": 20.0,
    "keyword_score": 10.0,
    "experience_score": 20.0,
    "jd_structure_score": 5.0,
    "section_score": 5.0,
}

AXIS_WEIGHT_PROFILES = {
    "overall_fit": {
        "skill_score": 45.0,
        "semantic_score": 25.0,
        "keyword_score": 10.0,
        "experience_score": 20.0,
    },
    "evidence_strength": {
        "semantic_score": 70.0,
        "jd_structure_score": 30.0,
    },
    "cv_quality": {
        "section_score": 70.0,
        "jd_structure_score": 30.0,
    },
}


def normalize_weights(base_weights: Dict[str, float], disabled_keys: Iterable[str] | None = None) -> Dict[str, float]:
    disabled = set(disabled_keys or [])
    active = {
        key: float(weight)
        for key, weight in base_weights.items()
        if key not in disabled and float(weight) > 0
    }
    total = sum(active.values())
    if total <= 0:
        return {}
    return {
        key: round(weight * 100.0 / total, 2)
        for key, weight in active.items()
    }


def weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    return round(
        sum(float(scores.get(key, 0.0)) * float(weight) / 100.0 for key, weight in weights.items()),
        2,
    )


def compute_scorecard(
    score_values: Dict[str, float],
    *,
    semantic_available: bool,
) -> Dict[str, object]:
    disabled_keys = []
    if not semantic_available:
        disabled_keys.append("semantic_score")

    final_weights = normalize_weights(FINAL_SCORE_COMPONENT_WEIGHTS, disabled_keys)
    final_score = min(100.0, max(0.0, weighted_score(score_values, final_weights)))

    axes = {
        "overall_fit": weighted_score(
            score_values,
            normalize_weights(AXIS_WEIGHT_PROFILES["overall_fit"], disabled_keys),
        ),
        "skill_coverage": round(float(score_values.get("skill_score", 0.0)), 2),
        "evidence_strength": weighted_score(
            score_values,
            normalize_weights(AXIS_WEIGHT_PROFILES["evidence_strength"], disabled_keys),
        ),
        "cv_quality": weighted_score(
            score_values,
            normalize_weights(AXIS_WEIGHT_PROFILES["cv_quality"], disabled_keys),
        ),
    }

    return {
        "final_score": final_score,
        "final_score_weights": final_weights,
        "score_axes": axes,
        "disabled_dimensions": disabled_keys,
    }
