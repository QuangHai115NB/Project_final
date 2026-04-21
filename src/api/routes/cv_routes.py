from __future__ import annotations

from flask import Blueprint, g, request

from src.api.http import response
from src.core.dependencies import require_auth
from src.services.documents import create_cv_record, delete_cv_record, list_cv_records

cv_bp = Blueprint("cv_routes", __name__)


@cv_bp.post("/cvs/upload")
@require_auth
def upload_cv():
    payload = create_cv_record(
        user_id=g.user_id,
        title=request.form.get("title", "").strip(),
        file_storage=request.files.get("cv_pdf"),
    )
    return response(payload, 201)


@cv_bp.get("/cvs")
@require_auth
def list_cvs():
    return response(list_cv_records(user_id=g.user_id))


@cv_bp.delete("/cvs/delete/<int:cv_id>")
@require_auth
def delete_cv(cv_id: int):
    return response(delete_cv_record(user_id=g.user_id, cv_id=cv_id))
