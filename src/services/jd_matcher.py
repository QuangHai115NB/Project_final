from __future__ import annotations

from src.services.jd_matching import pipeline as _pipeline


def __getattr__(name: str):
    return getattr(_pipeline, name)


match_cv_to_jd = _pipeline.match_cv_to_jd

