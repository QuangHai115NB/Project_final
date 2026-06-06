from __future__ import annotations

from datetime import datetime

from src.core.errors import PermissionDeniedError
from src.db.models import User
from src.db.repository import CVRepository, JDRepository, MatchRepository
from src.services.time_service import local_day_start_utc, utc_iso, utc_now


FREE_CV_LIMIT = 3
FREE_JD_LIMIT = 3
FREE_DAILY_MATCH_LIMIT = 1


def is_premium(user: User) -> bool:
    if user.plan != "premium":
        return False
    if user.premium_until is None:
        return True
    return user.premium_until > utc_now()


def effective_plan(user: User) -> str:
    return "premium" if is_premium(user) else "free"


def _today_start_utc() -> datetime:
    return local_day_start_utc()


def usage_payload(db, user: User) -> dict:
    cv_count = CVRepository(db).count_by_user(user.id)
    jd_count = JDRepository(db).count_by_user(user.id)
    matches_today = MatchRepository(db).count_by_user_since(user.id, _today_start_utc())
    plan = effective_plan(user)
    return {
        "plan": plan,
        "premium_until": utc_iso(user.premium_until),
        "limits": {
            "cv": None if plan == "premium" else FREE_CV_LIMIT,
            "jd": None if plan == "premium" else FREE_JD_LIMIT,
            "daily_matches": None if plan == "premium" else FREE_DAILY_MATCH_LIMIT,
        },
        "usage": {
            "cv": cv_count,
            "jd": jd_count,
            "matches_today": matches_today,
        },
    }


def ensure_can_upload_cv(db, user: User) -> None:
    if effective_plan(user) == "premium":
        return
    if CVRepository(db).count_by_user(user.id) >= FREE_CV_LIMIT:
        raise PermissionDeniedError("Gói free chỉ được tải tối đa 3 CV. Vui lòng nâng cấp tài khoản.")


def ensure_can_upload_jd(db, user: User) -> None:
    if effective_plan(user) == "premium":
        return
    if JDRepository(db).count_by_user(user.id) >= FREE_JD_LIMIT:
        raise PermissionDeniedError("Gói free chỉ được tải tối đa 3 JD. Vui lòng nâng cấp tài khoản.")


def ensure_can_create_match(db, user: User) -> None:
    if effective_plan(user) == "premium":
        return
    if MatchRepository(db).count_by_user_since(user.id, _today_start_utc()) >= FREE_DAILY_MATCH_LIMIT:
        raise PermissionDeniedError("Gói free chỉ được so khớp 1 lần mỗi ngày. Vui lòng nâng cấp tài khoản.")
