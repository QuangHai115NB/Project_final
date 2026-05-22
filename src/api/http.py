from __future__ import annotations

from flask import jsonify, request

from src.core.errors import ValidationError


def json_body(*required_fields: str) -> dict:
    body = request.get_json(silent=True) or {}
    missing = [field for field in required_fields if not body.get(field)]
    if missing:
        raise ValidationError(f"Thiếu trường bắt buộc: {', '.join(missing)}")
    return body


def response(payload: dict, status_code: int = 200):
    return jsonify(payload), status_code

#File này là file helper cho tầng API trong Flask. Hàm json_body() dùng để lấy JSON body từ request và kiểm tra các
# trường bắt buộc, nếu thiếu thì ném lỗi ValidationError. Hàm response() dùng để chuyển dữ liệu Python dict thành JSON
# response và trả kèm HTTP status code. File này giúp các route viết ngắn hơn, đồng nhất hơn và tránh lặp lại logic xử
# lý request/response ở nhiều nơi.