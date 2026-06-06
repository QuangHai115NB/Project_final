from __future__ import annotations

from flask import Blueprint, request

from src.api.http import json_body, response
from src.core.dependencies import require_admin
from src.services.admin_service import (
    admin_get_match,
    admin_get_user,
    admin_list_matches,
    admin_list_users,
    admin_overview,
    admin_update_user,
)
from src.services.billing_service import delete_payment_qr, get_payment_info, upload_payment_qr


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/overview")
@require_admin
def overview():
    return response(admin_overview(
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
        granularity=request.args.get("granularity", "day"),
    ))


@admin_bp.get("/users")
@require_admin
def list_users():
    return response(admin_list_users(
        limit=request.args.get("limit", 20, type=int),
        offset=request.args.get("offset", 0, type=int),
        search=request.args.get("search"),
    ))


@admin_bp.get("/users/<int:user_id>")
@require_admin
def get_user(user_id: int):
    return response(admin_get_user(user_id))


@admin_bp.put("/users/<int:user_id>")
@require_admin
def update_user(user_id: int):
    return response(admin_update_user(user_id, json_body()))


@admin_bp.get("/matches")
@require_admin
def list_matches():
    return response(admin_list_matches(
        limit=request.args.get("limit", 20, type=int),
        offset=request.args.get("offset", 0, type=int),
        user_id=request.args.get("user_id", type=int),
        search=request.args.get("search"),
    ))


@admin_bp.get("/matches/<int:match_id>")
@require_admin
def get_match(match_id: int):
    return response(admin_get_match(match_id))


@admin_bp.get("/payment-info")
@require_admin
def payment_info():
    return response(get_payment_info())


@admin_bp.post("/payment-qr")
@require_admin
def upload_qr():
    return response(upload_payment_qr(request.files.get("qr_image")))


@admin_bp.delete("/payment-qr")
@require_admin
def delete_qr():
    return response(delete_payment_qr())
