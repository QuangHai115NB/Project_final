from __future__ import annotations

from src.core.errors import AuthenticationError, ConflictError, NotFoundError, RateLimitError, ValidationError
from src.core.rate_limiter import (
    check_login_rate_limit,
    check_otp_rate_limit,
    record_login_failure,
    reset_login_failures,
    reset_otp_rate_limit,
)
from src.db.database import SessionLocal
from src.db.models import User
from src.db.repository import RefreshTokenRepository, UserRepository
from src.services.auth.email_service import send_register_otp, send_reset_password_otp
from src.services.auth.otp_service import generate_otp, verify_otp
from src.services.auth.password_service import hash_password, verify_password
from src.services.auth.token_service import issue_token_pair, revoke_refresh_token, rotate_refresh_token
from src.services.auth.validators import normalize_email, validate_email, validate_password


def register_user(email: str, password: str) -> dict:
    email = validate_email(email)
    validate_password(password)

    allowed, ttl = check_otp_rate_limit(email)
    if not allowed:
        raise RateLimitError(f"Gửi OTP quá nhiều lần. Vui lòng thử lại sau {ttl} giây")

    db = SessionLocal()
    try:
        user_repo = UserRepository(db)
        existing = user_repo.get_by_email(email)
        if existing:
            if existing.is_verified:
                raise ConflictError("Email này đã được đăng ký")
            existing.password_hash = hash_password(password)
            db.commit()
        else:
            user = User(email=email, password_hash=hash_password(password), is_verified=False)
            db.add(user)
            db.commit()

        otp = generate_otp(email, purpose="register")
        send_register_otp(email, otp)
        return {"message": "Mã OTP đã được gửi đến email của bạn. Vui lòng kiểm tra hộp thư."}
    finally:
        db.close()


def verify_email_otp(email: str, otp: str) -> dict:
    email = normalize_email(email)
    if not verify_otp(email, purpose="register", otp_input=otp):
        raise ValidationError("Mã OTP không đúng hoặc đã hết hạn")

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_email(email)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")
        user.is_verified = True
        db.commit()
        db.refresh(user)
        reset_otp_rate_limit(email)
        return {"message": "Xác thực email thành công!", **issue_token_pair(user)}
    finally:
        db.close()


def login_user(email: str, password: str) -> dict:
    email = normalize_email(email)
    allowed, ttl = check_login_rate_limit(email)
    if not allowed:
        raise RateLimitError(
            f"Tài khoản tạm thời bị khóa do đăng nhập sai quá nhiều lần. Thử lại sau {ttl} giây"
        )

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            record_login_failure(email)
            raise AuthenticationError("Email hoặc mật khẩu không đúng")
        if not user.is_verified:
            raise ValidationError("Tài khoản chưa xác thực email. Vui lòng kiểm tra hộp thư.")

        reset_login_failures(email)
        return {"message": "Đăng nhập thành công", **issue_token_pair(user)}
    finally:
        db.close()


def refresh_access_token(raw_refresh_token: str) -> dict:
    return rotate_refresh_token(raw_refresh_token)


def logout_user(raw_refresh_token: str) -> dict:
    return revoke_refresh_token(raw_refresh_token)


def forgot_password(email: str) -> dict:
    email = validate_email(email)

    allowed, ttl = check_otp_rate_limit(email)
    if not allowed:
        raise RateLimitError(f"Gửi OTP quá nhiều lần. Thử lại sau {ttl} giây")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email, User.is_verified == True).first()
        if user:
            otp = generate_otp(email, purpose="reset_pwd")
            send_reset_password_otp(email, otp)
        return {"message": "Nếu email tồn tại trong hệ thống, bạn sẽ nhận được mã OTP."}
    finally:
        db.close()


def reset_password(email: str, otp: str, new_password: str) -> dict:
    email = normalize_email(email)
    validate_password(new_password)

    if not verify_otp(email, purpose="reset_pwd", otp_input=otp):
        raise ValidationError("Mã OTP không đúng hoặc đã hết hạn")

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_email(email)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")

        user.password_hash = hash_password(new_password)
        db.commit()
        RefreshTokenRepository(db).revoke_all_for_user(user.id)
        reset_otp_rate_limit(email)
        return {"message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại."}
    finally:
        db.close()


def change_password(user_id: int, old_password: str, new_password: str) -> dict:
    validate_password(new_password)
    if old_password == new_password:
        raise ValidationError("Mật khẩu mới phải khác mật khẩu cũ")

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundError("Tài khoản không tồn tại")
        if not verify_password(old_password, user.password_hash):
            raise ValidationError("Mật khẩu cũ không đúng")

        user.password_hash = hash_password(new_password)
        db.commit()
        RefreshTokenRepository(db).revoke_all_for_user(user.id)
        return {"message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại trên các thiết bị khác."}
    finally:
        db.close()
