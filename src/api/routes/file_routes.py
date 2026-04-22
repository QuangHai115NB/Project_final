from __future__ import annotations

from flask import Blueprint, Response, g

from src.api.http import response
from src.core.dependencies import require_auth
from src.services.documents import (
    get_cv_access_payload,
    get_cv_file_payload,
    get_jd_access_payload,
    get_jd_file_payload,
)

file_bp = Blueprint("file_routes", __name__)


@file_bp.get("/cvs/file/<int:cv_id>")
@require_auth
def get_cv_file(cv_id: int):
    return response(get_cv_access_payload(user_id=g.user_id, cv_id=cv_id))


@file_bp.get("/cvs/file/<int:cv_id>/content")
@require_auth
def download_cv_file(cv_id: int):
    payload = get_cv_file_payload(user_id=g.user_id, cv_id=cv_id)
    return Response(
        payload["file_bytes"],
        mimetype=payload["content_type"],
        headers={
            "Content-Disposition": f'inline; filename="{payload["filename"]}"',
            "Cache-Control": "no-store",
        },
    )


@file_bp.get("/jds/file/<int:jd_id>")
@require_auth
def get_jd_file(jd_id: int):
    return response(get_jd_access_payload(user_id=g.user_id, jd_id=jd_id))


@file_bp.get("/jds/file/<int:jd_id>/content")
@require_auth
def download_jd_file(jd_id: int):
    payload = get_jd_file_payload(user_id=g.user_id, jd_id=jd_id)
    return Response(
        payload["file_bytes"],
        mimetype=payload["content_type"],
        headers={
            "Content-Disposition": f'inline; filename="{payload["filename"]}"',
            "Cache-Control": "no-store",
        },
    )
