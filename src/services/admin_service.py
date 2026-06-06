from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.models import CVDocument, JDDocument, MatchHistory, User
from src.db.repository import CVRepository, JDRepository, MatchRepository, UserRepository
from src.services.auth.password_service import hash_password
from src.services.auth.profile_service import serialize_user_profile
from src.services.quota_service import effective_plan, usage_payload
from src.services.time_service import utc_iso, utc_now


UTC = timezone.utc


def _pagination(limit: int = 20, offset: int = 0, max_limit: int = 100) -> tuple[int, int]:
    return max(1, min(limit or 20, max_limit)), max(0, offset or 0)


def _parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise ValidationError("premium_until không hợp lệ") from exc


def _admin_timezone():
    timezone_name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Bangkok"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == "Asia/Bangkok":
            return timezone(timedelta(hours=7), name="Asia/Bangkok")
        return timezone.utc


def _timezone_name(value) -> str:
    return getattr(value, "key", None) or value.tzname(None) or "UTC"


def _parse_date(value: str | None, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} khong hop le") from exc


def _period_bounds(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "day",
) -> dict:
    if granularity not in {"day", "month", "year"}:
        raise ValidationError("granularity khong hop le")

    timezone = _admin_timezone()
    today = datetime.now(timezone).date()
    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")

    if parsed_start is None or parsed_end is None:
        if granularity == "day":
            parsed_end = parsed_end or today
            parsed_start = parsed_start or (parsed_end - timedelta(days=13))
        elif granularity == "month":
            parsed_end = parsed_end or today
            parsed_start = parsed_start or date(parsed_end.year, 1, 1)
        else:
            parsed_end = parsed_end or today
            parsed_start = parsed_start or date(parsed_end.year - 4, 1, 1)

    if parsed_start > parsed_end:
        raise ValidationError("start_date phai nho hon hoac bang end_date")

    start_local = datetime.combine(parsed_start, time.min, tzinfo=timezone)
    end_local = datetime.combine(parsed_end + timedelta(days=1), time.min, tzinfo=timezone)
    return {
        "timezone": timezone,
        "timezone_name": _timezone_name(timezone),
        "start_date": parsed_start,
        "end_date": parsed_end,
        "start_utc": start_local.astimezone(UTC).replace(tzinfo=None),
        "end_utc": end_local.astimezone(UTC).replace(tzinfo=None),
        "granularity": granularity,
    }


def _bucket_key(value: datetime, *, timezone: ZoneInfo, granularity: str) -> str:
    local_value = value.replace(tzinfo=UTC).astimezone(timezone)
    if granularity == "year":
        return str(local_value.year)
    if granularity == "month":
        return f"{local_value.year:04d}-{local_value.month:02d}"
    return local_value.date().isoformat()


def _next_month(value: date) -> date:
    return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)


def _empty_buckets(start_date: date, end_date: date, granularity: str) -> dict:
    buckets = {}
    if granularity == "year":
        for year in range(start_date.year, end_date.year + 1):
            buckets[str(year)] = {"matches": 0, "score_sum": 0.0}
        return buckets

    if granularity == "month":
        current = date(start_date.year, start_date.month, 1)
        end_month = date(end_date.year, end_date.month, 1)
        while current <= end_month:
            buckets[f"{current.year:04d}-{current.month:02d}"] = {"matches": 0, "score_sum": 0.0}
            current = _next_month(current)
        return buckets

    current = start_date
    while current <= end_date:
        buckets[current.isoformat()] = {"matches": 0, "score_sum": 0.0}
        current += timedelta(days=1)
    return buckets


def seed_admin_from_env(email: str | None, password: str | None) -> None:
    if not email or not password:
        return

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_email(email.strip().lower())
        if user:
            user.role = "admin"
            user.is_verified = True
            user.is_active = True
            user.plan = "premium"
            user.password_hash = hash_password(password)
        else:
            user = User(
                email=email.strip().lower(),
                password_hash=hash_password(password),
                is_verified=True,
                is_active=True,
                role="admin",
                plan="premium",
            )
            db.add(user)
        db.commit()
    finally:
        db.close()


def admin_overview(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "day",
) -> dict:
    db = SessionLocal()
    try:
        now = utc_now()
        period = _period_bounds(start_date=start_date, end_date=end_date, granularity=granularity)
        buckets = _empty_buckets(period["start_date"], period["end_date"], period["granularity"])
        activity_rows = db.query(
            MatchHistory.created_at,
            MatchHistory.similarity_score,
        ).filter(
            MatchHistory.created_at >= period["start_utc"],
            MatchHistory.created_at < period["end_utc"],
        ).all()
        for row in activity_rows:
            if not row.created_at:
                continue
            key = _bucket_key(row.created_at, timezone=period["timezone"], granularity=period["granularity"])
            if key not in buckets:
                continue
            buckets[key]["matches"] += 1
            buckets[key]["score_sum"] += float(row.similarity_score or 0)

        top_user_rows = db.query(
            User.id,
            User.email,
            func.count(MatchHistory.id).label("match_count"),
            func.avg(MatchHistory.similarity_score).label("avg_score"),
            func.max(MatchHistory.created_at).label("latest_match_at"),
        ).join(
            MatchHistory, MatchHistory.user_id == User.id
        ).filter(
            MatchHistory.created_at >= period["start_utc"],
            MatchHistory.created_at < period["end_utc"],
        ).group_by(
            User.id, User.email
        ).order_by(
            func.count(MatchHistory.id).desc(),
            func.max(MatchHistory.created_at).desc(),
        ).limit(8).all()

        matches_by_period = [
            {
                "date": date_key,
                "period": date_key,
                "matches": data["matches"],
                "avg_score": round(data["score_sum"] / data["matches"], 1) if data["matches"] else 0,
            }
            for date_key, data in buckets.items()
        ]

        total_users = db.query(User).count()
        premium_users = db.query(User).filter(
            User.plan == "premium",
            (User.premium_until == None) | (User.premium_until > now),
        ).count()
        period_user_count = db.query(User).filter(
            User.created_at >= period["start_utc"],
            User.created_at < period["end_utc"],
        ).count()
        period_cv_count = db.query(CVDocument).filter(
            CVDocument.created_at >= period["start_utc"],
            CVDocument.created_at < period["end_utc"],
        ).count()
        period_jd_count = db.query(JDDocument).filter(
            JDDocument.created_at >= period["start_utc"],
            JDDocument.created_at < period["end_utc"],
        ).count()
        period_match_count = sum(item["matches"] for item in matches_by_period)

        return {
            "users": period_user_count,
            "total_users": total_users,
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "free_users": total_users - premium_users,
            "premium_users": premium_users,
            "admins": db.query(User).filter(User.role == "admin").count(),
            "cvs": period_cv_count,
            "total_cvs": db.query(CVDocument).count(),
            "jds": period_jd_count,
            "total_jds": db.query(JDDocument).count(),
            "matches": period_match_count,
            "total_matches": db.query(MatchHistory).count(),
            "matches_by_day": matches_by_period,
            "matches_by_period": matches_by_period,
            "period": {
                "start_date": period["start_date"].isoformat(),
                "end_date": period["end_date"].isoformat(),
                "granularity": period["granularity"],
                "timezone": period["timezone_name"],
            },
            "top_users": [
                {
                    "user_id": row.id,
                    "email": row.email,
                    "match_count": int(row.match_count or 0),
                    "avg_score": round(float(row.avg_score or 0), 1),
                    "latest_match_at": utc_iso(row.latest_match_at),
                }
                for row in top_user_rows
            ],
        }
    finally:
        db.close()


def admin_list_users(*, limit: int = 20, offset: int = 0, search: str | None = None) -> dict:
    safe_limit, safe_offset = _pagination(limit, offset)
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        total = repo.count_users(search=search)
        users = repo.list_users_with_usage(limit=safe_limit, offset=safe_offset, search=search)
        return {
            "users": [
                {
                    "id": item.id,
                    "email": item.email,
                    "full_name": item.full_name,
                    "role": item.role,
                    "plan": item.plan,
                    "effective_plan": "premium" if item.plan == "premium" and (
                        item.premium_until is None or item.premium_until > utc_now()
                    ) else "free",
                    "premium_until": utc_iso(item.premium_until),
                    "is_active": item.is_active,
                    "is_verified": item.is_verified,
                    "created_at": utc_iso(item.created_at),
                    "cv_count": item.cv_count,
                    "jd_count": item.jd_count,
                    "match_count": item.match_count,
                }
                for item in users
            ],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "total": total,
                "has_next": safe_offset + safe_limit < total,
                "has_prev": safe_offset > 0,
            },
        }
    finally:
        db.close()


def admin_get_user(user_id: int) -> dict:
    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundError("User không tồn tại")
        return {
            "user": {
                **serialize_user_profile(user),
                "role": user.role,
                "plan": user.plan,
                "effective_plan": effective_plan(user),
                "premium_until": utc_iso(user.premium_until),
                "is_active": user.is_active,
            },
            "quota": usage_payload(db, user),
            "cvs": [
                {
                    "id": cv.id,
                    "title": cv.title,
                    "original_filename": cv.original_filename,
                    "created_at": utc_iso(cv.created_at),
                }
                for cv in CVRepository(db).list_by_user(user_id)
            ],
            "jds": [
                {
                    "id": jd.id,
                    "title": jd.title,
                    "original_filename": jd.original_filename,
                    "created_at": utc_iso(jd.created_at),
                }
                for jd in JDRepository(db).list_by_user(user_id)
            ],
            "matches": [
                {
                    "id": item.id,
                    "cv_title": item.cv_title,
                    "jd_title": item.jd_title,
                    "similarity_score": float(item.similarity_score) if item.similarity_score else 0,
                    "created_at": utc_iso(item.created_at),
                }
                for item in MatchRepository(db).list_by_user(user_id, limit=20, offset=0)
            ],
        }
    finally:
        db.close()


def admin_update_user(user_id: int, payload: dict) -> dict:
    allowed_roles = {"user", "admin"}
    allowed_plans = {"free", "premium"}
    role = payload.get("role")
    plan = payload.get("plan")
    if role is not None and role not in allowed_roles:
        raise ValidationError("role không hợp lệ")
    if plan is not None and plan not in allowed_plans:
        raise ValidationError("plan không hợp lệ")

    premium_until = _parse_datetime(payload.get("premium_until"))
    if payload.get("extend_days"):
        premium_until = max(premium_until or utc_now(), utc_now()) + timedelta(days=int(payload["extend_days"]))

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User không tồn tại")
        user = repo.set_admin_managed_fields(
            user,
            role=role,
            plan=plan,
            premium_until=premium_until,
            is_active=payload.get("is_active"),
        )
        return {"message": "Đã cập nhật người dùng", "user": admin_get_user(user.id)["user"]}
    finally:
        db.close()


def admin_list_matches(
    *,
    limit: int = 20,
    offset: int = 0,
    user_id: int | None = None,
    search: str | None = None,
) -> dict:
    safe_limit, safe_offset = _pagination(limit, offset)
    db = SessionLocal()
    try:
        repo = MatchRepository(db)
        total = repo.count_all(user_id=user_id, search=search)
        rows = repo.list_all(limit=safe_limit, offset=safe_offset, user_id=user_id, search=search)
        return {
            "matches": [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "user_email": row.user_email,
                    "cv_title": row.cv_title,
                    "jd_title": row.jd_title,
                    "similarity_score": float(row.similarity_score) if row.similarity_score else 0,
                    "created_at": utc_iso(row.created_at),
                }
                for row in rows
            ],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "total": total,
                "has_next": safe_offset + safe_limit < total,
                "has_prev": safe_offset > 0,
            },
        }
    finally:
        db.close()


def admin_get_match(match_id: int) -> dict:
    db = SessionLocal()
    try:
        record = MatchRepository(db).get_by_id(match_id)
        if not record:
            raise NotFoundError("Match không tồn tại")
        try:
            report = json.loads(record.report_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError("Report data bị lỗi") from exc
        return {
            "id": record.id,
            "user_id": record.user_id,
            "user_email": record.user.email if record.user else None,
            "cv_id": record.cv_id,
            "jd_id": record.jd_id,
            "cv_title": record.cv.title if record.cv else None,
            "jd_title": record.jd.title if record.jd else None,
            "similarity_score": float(record.similarity_score) if record.similarity_score else 0,
            "user_review": record.user_review or "",
            "created_at": utc_iso(record.created_at),
            "report": report,
        }
    finally:
        db.close()
