from __future__ import annotations

from datetime import datetime, timezone

from src.core.errors import AuthenticationError, NotFoundError
from src.core.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
)
from src.db.database import SessionLocal
from src.db.models import User
from src.db.repository import RefreshTokenRepository, UserRepository


def issue_token_pair(user: User) -> dict:
    access_token = create_access_token(user.id, user.email)
    raw_refresh, expires_at = create_refresh_token(user.id)

    db = SessionLocal()
    try:
        RefreshTokenRepository(db).add(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires_at,
        )
    finally:
        db.close()

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "Bearer",
    }


def rotate_refresh_token(raw_refresh_token: str) -> dict:
    payload = decode_refresh_token(raw_refresh_token)
    if not payload:
        raise AuthenticationError("Refresh token không hợp lệ hoặc đã hết hạn")

    user_id = int(payload["sub"])
    token_hash = hash_token(raw_refresh_token)

    db = SessionLocal()
    try:
        token_repo = RefreshTokenRepository(db)
        rt = token_repo.get_active(user_id=user_id, token_hash=token_hash)
        if not rt:
            raise AuthenticationError("Refresh token đã bị thu hồi hoặc không hợp lệ")

        now = datetime.now(timezone.utc)
        if rt.expires_at.replace(tzinfo=timezone.utc) < now:
            raise AuthenticationError("Refresh token đã hết hạn, vui lòng đăng nhập lại")

        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")

        token_repo.revoke(rt)
        return {
            "message": "Token đã được làm mới",
            **issue_token_pair(user),
        }
    finally:
        db.close()


def revoke_refresh_token(raw_refresh_token: str) -> dict:
    payload = decode_refresh_token(raw_refresh_token)
    if not payload:
        return {"message": "Đã đăng xuất"}

    db = SessionLocal()
    try:
        token_repo = RefreshTokenRepository(db)
        rt = token_repo.get_by_hash(hash_token(raw_refresh_token))
        if rt and not rt.is_revoked:
            token_repo.revoke(rt)
        return {"message": "Đã đăng xuất thành công"}
    finally:
        db.close()
