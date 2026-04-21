from __future__ import annotations

import io

from flask import Blueprint, g, request, send_file

from src.api.http import response
from src.core.dependencies import require_auth
from src.services.documents import (
    create_match_report,
    delete_match_report,
    download_match_report,
    get_match_detail,
    list_match_reports,
)

match_bp = Blueprint("match_routes", __name__)


@match_bp.post("/matches")
@require_auth
def create_match():
    body = request.get_json(silent=True) or {}
    payload = create_match_report(
        user_id=g.user_id,
        cv_id=body.get("cv_id"),
        jd_id=body.get("jd_id"),
    )
    return response(payload, 201)


@match_bp.get("/matches")
@require_auth
def list_matches():
    payload = list_match_reports(
        user_id=g.user_id,
        limit=request.args.get("limit", 10, type=int),
        offset=request.args.get("offset", 0, type=int),
    )
    return response(payload)


@match_bp.get("/matches/<int:match_id>")
@require_auth
def get_match(match_id: int):
    return response(get_match_detail(user_id=g.user_id, match_id=match_id))


@match_bp.delete("/matches/<int:match_id>")
@require_auth
def delete_match(match_id: int):
    return response(delete_match_report(user_id=g.user_id, match_id=match_id))


@match_bp.get("/matches/download/<int:match_id>")
@require_auth
def download_match(match_id: int):
    docx_bytes, filename = download_match_report(user_id=g.user_id, match_id=match_id)
    return send_file(
        io.BytesIO(docx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )
