from __future__ import annotations

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.repository import UserRepository
from src.services.storage import BUCKET_AVATAR, create_public_url, delete_avatar, upload_avatar


def _clean_optional(value: str | None, *, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if max_length is not None and len(cleaned) > max_length:
        raise ValidationError(f"Field exceeds maximum length of {max_length} characters")
    return cleaned


def serialize_user_profile(user) -> dict:
    avatar_url = create_public_url(BUCKET_AVATAR, user.avatar_path) if user.avatar_path else None
    return {
        "id": user.id,
        "email": user.email,
        "is_verified": user.is_verified,
        "full_name": user.full_name,
        "phone": user.phone,
        "headline": user.headline,
        "bio": user.bio,
        "avatar_url": avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def update_profile(user_id: int, payload: dict) -> dict:
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")

        user = repo.update_profile(
            user,
            full_name=_clean_optional(payload.get("full_name"), max_length=255),
            phone=_clean_optional(payload.get("phone"), max_length=50),
            headline=_clean_optional(payload.get("headline"), max_length=255),
            bio=_clean_optional(payload.get("bio"), max_length=1000),
        )
        return {
            "message": "Cập nhật thông tin cá nhân thành công",
            "user": serialize_user_profile(user),
        }
    finally:
        db.close()


def update_avatar(user_id: int, file_storage) -> dict:
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")

        _, storage_path = upload_avatar(file_storage, user_id)
        old_avatar = user.avatar_path
        user = repo.update_avatar(user, storage_path)

        if old_avatar:
            try:
                delete_avatar(old_avatar)
            except Exception:
                pass

        return {
            "message": "Cập nhật avatar thành công",
            "user": serialize_user_profile(user),
        }
    finally:
        db.close()


def remove_avatar(user_id: int) -> dict:
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")

        old_avatar = user.avatar_path
        user = repo.update_avatar(user, None)
        if old_avatar:
            try:
                delete_avatar(old_avatar)
            except Exception:
                pass

        return {
            "message": "Đã xóa avatar",
            "user": serialize_user_profile(user),
        }
    finally:
        db.close()
