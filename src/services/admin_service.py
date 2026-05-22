from __future__ import annotations

import json
from datetime import datetime, timedelta

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.models import CVDocument, JDDocument, MatchHistory, User
from src.db.repository import CVRepository, JDRepository, MatchRepository, UserRepository
from src.services.auth.password_service import hash_password
from src.services.auth.profile_service import serialize_user_profile
from src.services.quota_service import effective_plan, usage_payload


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


def admin_overview() -> dict:
    db = SessionLocal()
    try:
        return {
            "users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "free_users": db.query(User).filter(User.plan == "free").count(),
            "premium_users": db.query(User).filter(User.plan == "premium").count(),
            "admins": db.query(User).filter(User.role == "admin").count(),
            "cvs": db.query(CVDocument).count(),
            "jds": db.query(JDDocument).count(),
            "matches": db.query(MatchHistory).count(),
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
                        item.premium_until is None or item.premium_until > datetime.utcnow()
                    ) else "free",
                    "premium_until": item.premium_until.isoformat() if item.premium_until else None,
                    "is_active": item.is_active,
                    "is_verified": item.is_verified,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
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
                "premium_until": user.premium_until.isoformat() if user.premium_until else None,
                "is_active": user.is_active,
            },
            "quota": usage_payload(db, user),
            "cvs": [
                {
                    "id": cv.id,
                    "title": cv.title,
                    "original_filename": cv.original_filename,
                    "created_at": cv.created_at.isoformat() if cv.created_at else None,
                }
                for cv in CVRepository(db).list_by_user(user_id)
            ],
            "jds": [
                {
                    "id": jd.id,
                    "title": jd.title,
                    "original_filename": jd.original_filename,
                    "created_at": jd.created_at.isoformat() if jd.created_at else None,
                }
                for jd in JDRepository(db).list_by_user(user_id)
            ],
            "matches": [
                {
                    "id": item.id,
                    "cv_title": item.cv_title,
                    "jd_title": item.jd_title,
                    "similarity_score": float(item.similarity_score) if item.similarity_score else 0,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
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
        premium_until = max(premium_until or datetime.utcnow(), datetime.utcnow()) + timedelta(days=int(payload["extend_days"]))

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


def admin_list_matches(*, limit: int = 20, offset: int = 0, user_id: int | None = None) -> dict:
    safe_limit, safe_offset = _pagination(limit, offset)
    db = SessionLocal()
    try:
        repo = MatchRepository(db)
        total = repo.count_all(user_id=user_id)
        rows = repo.list_all(limit=safe_limit, offset=safe_offset, user_id=user_id)
        return {
            "matches": [
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "user_email": row.user_email,
                    "cv_title": row.cv_title,
                    "jd_title": row.jd_title,
                    "similarity_score": float(row.similarity_score) if row.similarity_score else 0,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
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
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "report": report,
        }
    finally:
        db.close()
