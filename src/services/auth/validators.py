from __future__ import annotations

import re

from src.core.errors import ValidationError

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
MIN_PASSWORD_LENGTH = 8


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str:
    normalized = normalize_email(email)
    if not EMAIL_RE.match(normalized):
        raise ValidationError("Email không hợp lệ")
    return normalized


def validate_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự")
    if not re.search(r"[A-Za-z]", password):
        raise ValidationError("Mật khẩu phải chứa ít nhất 1 chữ cái")
    if not re.search(r"\d", password):
        raise ValidationError("Mật khẩu phải chứa ít nhất 1 chữ số")
    return password
