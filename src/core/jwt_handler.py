"""
JWT Handler
-----------
- Access token:  15 phút (ngắn, stateless)
- Refresh token: 7 ngày  (lưu hash vào DB để có thể revoke)
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

# ── Lấy config từ env ──────────────────────────────────────────────
JWT_SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM      = "HS256"
ACCESS_TOKEN_MINUTES  = int(os.getenv("ACCESS_TOKEN_MINUTES", 15))
REFRESH_TOKEN_DAYS    = int(os.getenv("REFRESH_TOKEN_DAYS", 7))


# ── Tạo token ──────────────────────────────────────────────────────
def create_access_token(user_id: int, email: str) -> str:
    """Tạo JWT access token, hết hạn sau ACCESS_TOKEN_MINUTES phút."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub":   str(user_id),
        "email": email,
        "type":  "access",
        "iat":   now,
        "exp":   now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """
    Tạo JWT refresh token.
    Trả về (raw_token, expires_at) để caller lưu hash vào DB.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=REFRESH_TOKEN_DAYS)
    payload = {
        "sub":  str(user_id),
        "type": "refresh",
        "iat":  now,
        "exp":  expires_at,
    }
    raw = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return raw, expires_at


def hash_token(raw_token: str) -> str:
    """SHA-256 hash của token — cái này được lưu vào DB."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ── Giải mã token ──────────────────────────────────────────────────
def decode_token(token: str) -> Optional[dict]:
    """
    Giải mã và verify token.
    Trả về payload dict nếu hợp lệ, None nếu lỗi/hết hạn.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def decode_refresh_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None