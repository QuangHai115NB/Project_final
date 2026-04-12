"""
Auth Service
------------
Business logic cho toàn bộ luồng xác thực:

Luồng đăng ký:
  1. POST /auth/register      → tạo user (is_verified=False), gửi OTP
  2. POST /auth/verify-email  → xác thực OTP → is_verified=True

Luồng đăng nhập:
  POST /auth/login → trả access_token + refresh_token

Luồng quên mật khẩu:
  1. POST /auth/forgot-password     → gửi OTP đến email
  2. POST /auth/reset-password      → xác thực OTP + đổi mật khẩu

Luồng đổi mật khẩu (đã đăng nhập):
  POST /auth/change-password → xác thực mật khẩu cũ + đổi mới

Luồng refresh:
  POST /auth/refresh → dùng refresh_token → cấp access_token mới

Luồng logout:
  POST /auth/logout → revoke refresh_token
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import bcrypt

from src.core.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
)
from src.core.rate_limiter import (
    check_login_rate_limit,
    check_otp_rate_limit,
    record_login_failure,
    reset_login_failures,
    reset_otp_rate_limit,
)
from src.db.database import SessionLocal
from src.db.models import RefreshToken, User
from src.services.auth.email_service import send_register_otp, send_reset_password_otp
from src.services.auth.otp_service import generate_otp, verify_otp

# ── Helpers ────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_MIN_PWD_LEN = 8


def _validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def _validate_password(pwd: str) -> Optional[str]:
    """Trả về thông báo lỗi nếu password không hợp lệ, None nếu OK."""
    if len(pwd) < _MIN_PWD_LEN:
        return f"Mật khẩu phải có ít nhất {_MIN_PWD_LEN} ký tự"
    if not re.search(r"[A-Za-z]", pwd):
        return "Mật khẩu phải chứa ít nhất 1 chữ cái"
    if not re.search(r"\d", pwd):
        return "Mật khẩu phải chứa ít nhất 1 chữ số"
    return None


def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=12)).decode()


def _check_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


def _token_pair(user: User) -> dict:
    """Tạo cặp access + refresh token, lưu refresh hash vào DB."""
    access_token              = create_access_token(user.id, user.email)
    raw_refresh, expires_at   = create_refresh_token(user.id)

    db = SessionLocal()
    try:
        rt = RefreshToken(
            user_id    = user.id,
            token_hash = hash_token(raw_refresh),
            expires_at = expires_at,
        )
        db.add(rt)
        db.commit()
    finally:
        db.close()

    return {
        "access_token":  access_token,
        "refresh_token": raw_refresh,
        "token_type":    "Bearer",
    }


# ── Register ───────────────────────────────────────────────────────
def register_user(email: str, password: str) -> dict:
    """
    Bước 1: Đăng ký tài khoản mới.
    - Validate email + password
    - Kiểm tra email chưa dùng
    - Tạo user với is_verified=False
    - Sinh OTP + gửi email

    Returns: {"message": str} hoặc raise ValueError
    """
    email = email.strip().lower()

    if not _validate_email(email):
        raise ValueError("Email không hợp lệ")

    pwd_error = _validate_password(password)
    if pwd_error:
        raise ValueError(pwd_error)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.is_verified:
                raise ValueError("Email này đã được đăng ký")
            # Chưa verify → cho phép gửi lại OTP (không tạo user mới)
        else:
            user = User(
                email         = email,
                password_hash = _hash_password(password),
                is_verified   = False,
            )
            db.add(user)
            db.commit()

        # Kiểm tra rate limit trước khi gửi OTP
        allowed, ttl = check_otp_rate_limit(email)
        if not allowed:
            raise ValueError(f"Gửi OTP quá nhiều lần. Vui lòng thử lại sau {ttl} giây")

        otp = generate_otp(email, purpose="register")
        send_register_otp(email, otp)

        return {"message": "Mã OTP đã được gửi đến email của bạn. Vui lòng kiểm tra hộp thư."}
    finally:
        db.close()


# ── Verify Email ───────────────────────────────────────────────────
def verify_email_otp(email: str, otp: str) -> dict:
    """
    Bước 2: Xác thực OTP đăng ký.
    Nếu đúng → is_verified=True, trả về token pair để login luôn.
    """
    email = email.strip().lower()

    if not verify_otp(email, purpose="register", otp_input=otp):
        raise ValueError("Mã OTP không đúng hoặc đã hết hạn")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("Tài khoản không tồn tại")

        user.is_verified = True
        db.commit()
        db.refresh(user)

        reset_otp_rate_limit(email)
        return {
            "message": "Xác thực email thành công!",
            **_token_pair(user),
        }
    finally:
        db.close()


# ── Login ──────────────────────────────────────────────────────────
def login_user(email: str, password: str) -> dict:
    """
    Đăng nhập bằng email + password.
    Có rate-limit chống brute-force.
    """
    email = email.strip().lower()

    # Kiểm tra brute-force
    allowed, ttl = check_login_rate_limit(email)
    if not allowed:
        raise ValueError(f"Tài khoản tạm thời bị khóa do đăng nhập sai quá nhiều lần. Thử lại sau {ttl} giây")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        # Không tiết lộ email có tồn tại hay không (security best practice)
        if not user or not _check_password(password, user.password_hash):
            record_login_failure(email)
            raise ValueError("Email hoặc mật khẩu không đúng")

        if not user.is_verified:
            raise ValueError("Tài khoản chưa xác thực email. Vui lòng kiểm tra hộp thư.")

        reset_login_failures(email)
        return {
            "message": "Đăng nhập thành công",
            **_token_pair(user),
        }
    finally:
        db.close()


# ── Refresh Token ──────────────────────────────────────────────────
def refresh_access_token(raw_refresh_token: str) -> dict:
    """
    Dùng refresh token để lấy access token mới.
    - Verify JWT
    - Kiểm tra hash trong DB và chưa bị revoke
    - Revoke token cũ, phát token mới (rotation)
    """
    payload = decode_refresh_token(raw_refresh_token)
    if not payload:
        raise ValueError("Refresh token không hợp lệ hoặc đã hết hạn")

    user_id    = int(payload["sub"])
    token_hash = hash_token(raw_refresh_token)

    db = SessionLocal()
    try:
        rt = db.query(RefreshToken).filter(
            RefreshToken.user_id    == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        ).first()

        if not rt:
            raise ValueError("Refresh token đã bị thu hồi hoặc không hợp lệ")

        now = datetime.now(timezone.utc)
        if rt.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("Refresh token đã hết hạn, vui lòng đăng nhập lại")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Tài khoản không tồn tại")

        # Revoke token cũ
        rt.is_revoked = True
        db.commit()

        # Phát cặp token mới (refresh token rotation)
        return {
            "message": "Token đã được làm mới",
            **_token_pair(user),
        }
    finally:
        db.close()


# ── Logout ────────────────────────────────────────────────────────
def logout_user(raw_refresh_token: str) -> dict:
    """Revoke refresh token → đăng xuất khỏi thiết bị hiện tại."""
    payload = decode_refresh_token(raw_refresh_token)
    if not payload:
        # Token không hợp lệ → coi như đã logout
        return {"message": "Đã đăng xuất"}

    token_hash = hash_token(raw_refresh_token)
    db = SessionLocal()
    try:
        rt = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash
        ).first()
        if rt and not rt.is_revoked:
            rt.is_revoked = True
            db.commit()

        return {"message": "Đã đăng xuất thành công"}
    finally:
        db.close()


# ── Forgot Password ────────────────────────────────────────────────
def forgot_password(email: str) -> dict:
    """
    Gửi OTP đặt lại mật khẩu.
    Luôn trả thông báo thành công (không tiết lộ email có tồn tại hay không).
    """
    email = email.strip().lower()

    if not _validate_email(email):
        raise ValueError("Email không hợp lệ")

    allowed, ttl = check_otp_rate_limit(email)
    if not allowed:
        raise ValueError(f"Gửi OTP quá nhiều lần. Thử lại sau {ttl} giây")

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email       == email,
            User.is_verified == True,
        ).first()

        # Gửi OTP kể cả khi email không tồn tại → tránh user enumeration
        if user:
            otp = generate_otp(email, purpose="reset_pwd")
            send_reset_password_otp(email, otp)

        return {"message": "Nếu email tồn tại trong hệ thống, bạn sẽ nhận được mã OTP."}
    finally:
        db.close()


# ── Reset Password ─────────────────────────────────────────────────
def reset_password(email: str, otp: str, new_password: str) -> dict:
    """Xác thực OTP reset password + cập nhật mật khẩu mới."""
    email = email.strip().lower()

    pwd_error = _validate_password(new_password)
    if pwd_error:
        raise ValueError(pwd_error)

    if not verify_otp(email, purpose="reset_pwd", otp_input=otp):
        raise ValueError("Mã OTP không đúng hoặc đã hết hạn")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("Tài khoản không tồn tại")

        user.password_hash = _hash_password(new_password)
        db.commit()

        # Revoke tất cả refresh token cũ sau khi đổi mật khẩu
        db.query(RefreshToken).filter(
            RefreshToken.user_id    == user.id,
            RefreshToken.is_revoked == False,
        ).update({"is_revoked": True})
        db.commit()

        reset_otp_rate_limit(email)
        return {"message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại."}
    finally:
        db.close()


# ── Change Password (đã đăng nhập) ────────────────────────────────
def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    """Đổi mật khẩu khi đã đăng nhập — cần xác thực mật khẩu cũ."""
    pwd_error = _validate_password(new_password)
    if pwd_error:
        raise ValueError(pwd_error)

    if old_password == new_password:
        raise ValueError("Mật khẩu mới phải khác mật khẩu cũ")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Tài khoản không tồn tại")

        if not _check_password(old_password, user.password_hash):
            raise ValueError("Mật khẩu cũ không đúng")

        user.password_hash = _hash_password(new_password)
        db.commit()

        # Revoke tất cả refresh token cũ (bảo mật)
        db.query(RefreshToken).filter(
            RefreshToken.user_id    == user.id,
            RefreshToken.is_revoked == False,
        ).update({"is_revoked": True})
        db.commit()

        return {"message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại trên các thiết bị khác."}
    finally:
        db.close()