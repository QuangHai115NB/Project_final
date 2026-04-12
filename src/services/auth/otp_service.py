"""
OTP Service (Redis-backed)
--------------------------
- Sinh OTP 6 chữ số ngẫu nhiên, bảo mật bằng secrets module
- Lưu vào Redis với TTL tự động expire (mặc định 5 phút)
- Hỗ trợ 2 loại OTP:
    * "register"  → xác thực email khi đăng ký
    * "reset_pwd" → xác thực khi quên mật khẩu
"""
from __future__ import annotations

import os
import secrets
from typing import Optional

from src.core.rate_limiter import get_redis

OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", 300))   # 5 phút


def _make_key(email: str, purpose: str) -> str:
    """Redis key theo pattern: otp:{purpose}:{email}"""
    return f"otp:{purpose}:{email.lower()}"


def generate_otp(email: str, purpose: str) -> str:
    """
    Sinh OTP 6 chữ số, lưu vào Redis với TTL.

    Args:
        email:   email của user
        purpose: "register" | "reset_pwd"

    Returns:
        Chuỗi OTP 6 chữ số (str, vẫn giữ leading zero nếu có)
    """
    otp = str(secrets.randbelow(900000) + 100000)  # đảm bảo luôn 6 chữ số
    key = _make_key(email, purpose)
    get_redis().set(key, otp, ex=OTP_TTL_SECONDS)
    return otp


def verify_otp(email: str, purpose: str, otp_input: str) -> bool:
    """
    Xác thực OTP nhập vào.
    Nếu đúng → xóa OTP ngay (dùng 1 lần duy nhất).
    Nếu sai  → giữ nguyên để user thử lại (trong TTL còn lại).

    Returns:
        True nếu OTP hợp lệ, False nếu sai/hết hạn/không tồn tại.
    """
    key       = _make_key(email, purpose)
    stored    = get_redis().get(key)

    if stored is None:
        return False  # Hết hạn hoặc chưa có OTP

    if secrets.compare_digest(str(stored), str(otp_input).strip()):
        get_redis().delete(key)  # Xóa sau khi dùng
        return True

    return False


def get_otp_ttl(email: str, purpose: str) -> Optional[int]:
    """Trả về số giây còn lại của OTP, None nếu không tồn tại."""
    key = _make_key(email, purpose)
    ttl = get_redis().ttl(key)
    return ttl if ttl > 0 else None


def invalidate_otp(email: str, purpose: str) -> None:
    """Hủy OTP thủ công (ví dụ khi user đổi email)."""
    get_redis().delete(_make_key(email, purpose))