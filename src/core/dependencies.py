"""
Dependencies / Middleware
--------------------------
Decorator `@require_auth` bảo vệ route, inject `current_user` vào request context.

Cách dùng:
    @doc_bp.get("/cvs")
    @require_auth
    def list_cvs():
        user = g.current_user   # User object từ DB
        ...
"""
from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request

from src.core.jwt_handler import decode_access_token
from src.db.database import SessionLocal
from src.db.models import User


def require_auth(f):
    """
    Decorator kiểm tra Authorization: Bearer <access_token>.
    Nếu hợp lệ → inject g.current_user và g.user_id.
    Nếu không  → trả 401.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if not payload:
            return jsonify({"error": "Token không hợp lệ hoặc đã hết hạn"}), 401

        user_id = int(payload["sub"])

        # Lấy user từ DB (đảm bảo user vẫn tồn tại và đã verify)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({"error": "User không tồn tại"}), 401
            if not user.is_verified:
                return jsonify({"error": "Tài khoản chưa xác thực email"}), 403

            g.current_user = user
            g.user_id      = user_id
        finally:
            db.close()

        return f(*args, **kwargs)
    return decorated


def require_verified(f):
    """
    Tương tự require_auth nhưng chỉ kiểm tra is_verified.
    Dùng khi route cần cả xác thực lẫn verify email.
    (require_auth đã check is_verified nên thường không cần dùng riêng)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(g, "current_user", None):
            return jsonify({"error": "Chưa xác thực"}), 401
        if not g.current_user.is_verified:
            return jsonify({"error": "Email chưa được xác thực"}), 403
        return f(*args, **kwargs)
    return decorated