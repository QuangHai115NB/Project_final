"""
Rate Limiter (Redis-based)
--------------------------
Chống spam OTP bằng cách giới hạn số lần gửi OTP theo IP + email.

Chiến lược:
- Mỗi email chỉ được yêu cầu OTP tối đa MAX_OTP_REQUESTS lần / WINDOW_SECONDS
- Nếu vượt quá → trả 429, kèm thời gian chờ còn lại
"""
from __future__ import annotations

import os
from typing import Tuple

import redis

# ── Kết nối Redis ──────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ── Config ─────────────────────────────────────────────────────────
MAX_OTP_REQUESTS = int(os.getenv("MAX_OTP_REQUESTS", 3))   # tối đa 3 lần
WINDOW_SECONDS   = int(os.getenv("OTP_WINDOW_SECONDS", 300))  # trong 5 phút
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))  # 5 lần login sai
LOGIN_BLOCK_SECONDS = int(os.getenv("LOGIN_BLOCK_SECONDS", 900))  # block 15 phút


# ── OTP Rate Limit ─────────────────────────────────────────────────
def check_otp_rate_limit(email: str) -> Tuple[bool, int]:
    """
    Kiểm tra xem email này có bị rate-limit không.

    Returns:
        (is_allowed, ttl_seconds)
        - is_allowed=True  → cho phép gửi OTP
        - is_allowed=False → bị chặn, ttl là số giây còn lại phải chờ
    """
    r   = get_redis()
    key = f"otp_rate:{email.lower()}"

    current = r.get(key)
    if current is None:
        # Lần đầu — tạo counter
        pipe = r.pipeline()
        pipe.set(key, 1, ex=WINDOW_SECONDS)
        pipe.execute()
        return True, 0

    count = int(current)
    if count >= MAX_OTP_REQUESTS:
        ttl = r.ttl(key)
        return False, max(ttl, 0)

    r.incr(key)
    return True, 0


def reset_otp_rate_limit(email: str) -> None:
    """Xóa rate-limit sau khi OTP được xác thực thành công."""
    get_redis().delete(f"otp_rate:{email.lower()}")


# ── Login Brute-force Protection ───────────────────────────────────
def check_login_rate_limit(email: str) -> Tuple[bool, int]:
    """
    Chặn brute-force login: sau MAX_LOGIN_ATTEMPTS lần sai → block LOGIN_BLOCK_SECONDS.

    Returns: (is_allowed, ttl_seconds)
    """
    r   = get_redis()
    key = f"login_fail:{email.lower()}"

    current = r.get(key)
    if current is None:
        return True, 0

    count = int(current)
    if count >= MAX_LOGIN_ATTEMPTS:
        ttl = r.ttl(key)
        return False, max(ttl, 0)

    return True, 0


def record_login_failure(email: str) -> int:
    """
    Ghi nhận 1 lần login thất bại.
    Trả về số lần thất bại hiện tại.
    """
    r   = get_redis()
    key = f"login_fail:{email.lower()}"

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, LOGIN_BLOCK_SECONDS)
    results = pipe.execute()
    return int(results[0])


def reset_login_failures(email: str) -> None:
    """Xóa counter login fail sau khi đăng nhập thành công."""
    get_redis().delete(f"login_fail:{email.lower()}")