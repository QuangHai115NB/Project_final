from __future__ import annotations

import base64

from werkzeug.datastructures import FileStorage

from src.core.errors import ValidationError
from src.db.database import SessionLocal
from src.db.repository import AppSettingRepository


PAYMENT_QR_KEY = "payment_qr_data_url"
PAYMENT_PLANS = [
    {"id": "premium_1m", "label": "1 tháng", "months": 1, "price": 20000},
    {"id": "premium_3m", "label": "3 tháng", "months": 3, "price": 50000},
]
ALLOWED_QR_MIMES = {"image/png", "image/jpeg", "image/webp"}
MAX_QR_BYTES = 2 * 1024 * 1024


def _payment_info(qr_data_url: str | None = None) -> dict:
    return {
        "plans": PAYMENT_PLANS,
        "payment_qr_data_url": qr_data_url,
        "transfer_template": "CVR-{user_id}-{months}M",
        "manual_note": "Sau khi chuyển khoản, admin kiểm tra giao dịch và cộng số ngày premium thủ công.",
    }


def get_payment_info() -> dict:
    db = SessionLocal()
    try:
        qr_data_url = AppSettingRepository(db).get(PAYMENT_QR_KEY)
        return _payment_info(qr_data_url)
    finally:
        db.close()


def upload_payment_qr(file_storage: FileStorage | None) -> dict:
    if not file_storage or not file_storage.filename:
        raise ValidationError("Vui lòng chọn ảnh QR")
    if file_storage.mimetype not in ALLOWED_QR_MIMES:
        raise ValidationError("Ảnh QR phải là PNG, JPG hoặc WebP")

    data = file_storage.read()
    if not data:
        raise ValidationError("Ảnh QR rỗng")
    if len(data) > MAX_QR_BYTES:
        raise ValidationError("Ảnh QR không được vượt quá 2MB")

    encoded = base64.b64encode(data).decode("ascii")
    data_url = f"{file_storage.mimetype};base64,{encoded}"
    data_url = f"data:{data_url}"

    db = SessionLocal()
    try:
        AppSettingRepository(db).set(PAYMENT_QR_KEY, data_url)
        return {"message": "Đã cập nhật mã QR thanh toán", **_payment_info(data_url)}
    finally:
        db.close()


def delete_payment_qr() -> dict:
    db = SessionLocal()
    try:
        AppSettingRepository(db).set(PAYMENT_QR_KEY, None)
        return {"message": "Đã xóa mã QR thanh toán", **_payment_info(None)}
    finally:
        db.close()
