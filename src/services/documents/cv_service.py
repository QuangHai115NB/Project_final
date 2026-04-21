from __future__ import annotations

from werkzeug.utils import secure_filename

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.repository import CVRepository, MatchRepository, UserRepository
from src.services.storage import (
    BUCKET_CV,
    create_access_url,
    delete_cv as storage_delete_cv,
    upload_cv as storage_upload_cv,
)
from src.services.text_preprocess import clean_text


def _remove_null_bytes(text: str) -> str:
    return text.replace("\x00", "") if text else ""


def _serialize_cv(record) -> dict:
    return {
        "id": record.id,
        "title": record.title,
        "original_filename": record.original_filename,
        "content_text": record.content_text[:500] if record.content_text else "",
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def create_cv_record(*, user_id: int, title: str, file_storage) -> dict:
    if not file_storage or not file_storage.filename.lower().endswith(".pdf"):
        raise ValidationError("CV must be a PDF file")

    db = SessionLocal()
    try:
        if not UserRepository(db).exists(user_id):
            raise NotFoundError("User không tồn tại")

        _, storage_path, raw_text = storage_upload_cv(file_storage, user_id)
        cleaned_text = _remove_null_bytes(clean_text(raw_text))
        safe_filename = secure_filename(file_storage.filename)
        record = CVRepository(db).create(
            user_id=user_id,
            title=title or safe_filename,
            original_filename=safe_filename,
            storage_path=storage_path,
            content_text=cleaned_text,
        )
        return {
            "message": "CV uploaded successfully",
            "cv_id": record.id,
            "user_id": record.user_id,
            "title": record.title,
        }
    finally:
        db.close()


def list_cv_records(*, user_id: int) -> dict:
    db = SessionLocal()
    try:
        records = CVRepository(db).list_by_user(user_id)
        return {"cvs": [_serialize_cv(record) for record in records]}
    finally:
        db.close()


def delete_cv_record(*, user_id: int, cv_id: int) -> dict:
    db = SessionLocal()
    try:
        cv_repo = CVRepository(db)
        match_repo = MatchRepository(db)
        record = cv_repo.get_for_user(cv_id, user_id)
        if not record:
            raise NotFoundError("CV not found")

        if record.storage_path:
            try:
                storage_delete_cv(record.storage_path)
            except Exception:
                pass

        match_repo.delete_for_cv(cv_id, user_id)
        cv_repo.delete(record)
        return {"message": "CV deleted successfully"}
    finally:
        db.close()


def get_cv_access_payload(*, user_id: int, cv_id: int, expires_in: int = 3600) -> dict:
    db = SessionLocal()
    try:
        record = CVRepository(db).get_for_user(cv_id, user_id)
        if not record:
            raise NotFoundError("CV not found")
        if not record.storage_path:
            raise NotFoundError("CV file not found in storage")

        url, mode = create_access_url(BUCKET_CV, record.storage_path, expires_in=expires_in)
        return {"url": url, "expires_in": expires_in, "mode": mode}
    finally:
        db.close()
