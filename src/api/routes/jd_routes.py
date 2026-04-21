from __future__ import annotations

from flask import Blueprint, g, request

from src.api.http import response
from src.core.dependencies import require_auth
from src.services.documents import create_jd_record, delete_jd_record, list_jd_records

jd_bp = Blueprint("jd_routes", __name__)


@jd_bp.post("/jds/upload")
@require_auth
def upload_jd():
    payload = create_jd_record(
        user_id=g.user_id,
        title=request.form.get("title", "").strip(),
        jd_text=request.form.get("jd_text", "").strip(),
        file_storage=request.files.get("jd_file"),
    )
    return response(payload, 201)


@jd_bp.get("/jds")
@require_auth
def list_jds():
    return response(list_jd_records(user_id=g.user_id))


@jd_bp.delete("/jds/delete/<int:jd_id>")
@require_auth
def delete_jd(jd_id: int):
    return response(delete_jd_record(user_id=g.user_id, jd_id=jd_id))
