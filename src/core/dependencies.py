from __future__ import annotations

from functools import wraps

from flask import g, request

from src.core.errors import AuthenticationError, PermissionDeniedError
from src.core.jwt_handler import decode_access_token
from src.db.database import SessionLocal
from src.db.repository import UserRepository


def require_auth(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if not payload:
            raise AuthenticationError("Token không hợp lệ hoặc đã hết hạn")

        user_id = int(payload["sub"])
        db = SessionLocal()
        try:
            user = UserRepository(db).get_by_id(user_id)
            if not user:
                raise AuthenticationError("User không tồn tại")
            if not user.is_verified:
                raise PermissionDeniedError("Tài khoản chưa xác thực email")

            g.current_user = user
            g.user_id = user_id
        finally:
            db.close()

        return func(*args, **kwargs)

    return decorated


def require_verified(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if not getattr(g, "current_user", None):
            raise AuthenticationError("Chưa xác thực")
        if not g.current_user.is_verified:
            raise PermissionDeniedError("Email chưa được xác thực")
        return func(*args, **kwargs)

    return decorated
