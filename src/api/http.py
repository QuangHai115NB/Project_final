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
