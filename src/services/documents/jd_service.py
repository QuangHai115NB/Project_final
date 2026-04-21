from __future__ import annotations

from werkzeug.utils import secure_filename

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.repository import JDRepository, MatchRepository, UserRepository
from src.services.storage import (
    BUCKET_JD,
    create_access_url,
    delete_jd as storage_delete_jd,
    upload_jd as storage_upload_jd,
)


def _remove_null_bytes(text: str) -> str:
    return text.replace("\x00", "") if text else ""


def _serialize_jd(record) -> dict:
    return {
        "id": record.id,
        "title": record.title,
        "original_filename": record.original_filename,
        "content_text": record.content_text[:500] if record.content_text else "",
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def create_jd_record(*, user_id: int, title: str, jd_text: str, file_storage=None) -> dict:
    db = SessionLocal()
    try:
        if not UserRepository(db).exists(user_id):
            raise NotFoundError("User không tồn tại")

        storage_path = ""
        filename = "manual_jd.txt"
        final_text = (jd_text or "").strip()

        if file_storage and file_storage.filename:
            filename = secure_filename(file_storage.filename)
            _, storage_path, extracted_text = storage_upload_jd(file_storage, user_id)
            final_text = extracted_text or final_text

        if not final_text and not storage_path:
            raise ValidationError("Provide jd_text or upload jd_file")

        record = JDRepository(db).create(
            user_id=user_id,
            title=title or filename,
            original_filename=filename,
            storage_path=storage_path,
            content_text=_remove_null_bytes(final_text),
        )
        return {
            "message": "JD uploaded successfully",
            "jd_id": record.id,
            "title": record.title,
        }
    finally:
        db.close()


def list_jd_records(*, user_id: int) -> dict:
    db = SessionLocal()
    try:
        records = JDRepository(db).list_by_user(user_id)
        return {"jds": [_serialize_jd(record) for record in records]}
    finally:
        db.close()


def delete_jd_record(*, user_id: int, jd_id: int) -> dict:
    db = SessionLocal()
    try:
        jd_repo = JDRepository(db)
        match_repo = MatchRepository(db)
        record = jd_repo.get_for_user(jd_id, user_id)
        if not record:
            raise NotFoundError("JD not found")

        if record.storage_path:
            try:
                storage_delete_jd(record.storage_path)
            except Exception:
                pass

        match_repo.delete_for_jd(jd_id, user_id)
        jd_repo.delete(record)
        return {"message": "JD deleted successfully"}
    finally:
        db.close()


def get_jd_access_payload(*, user_id: int, jd_id: int, expires_in: int = 3600) -> dict:
    db = SessionLocal()
    try:
        record = JDRepository(db).get_for_user(jd_id, user_id)
        if not record:
            raise NotFoundError("JD not found")
        if not record.storage_path:
            raise NotFoundError("JD file not found in storage")

        url, mode = create_access_url(BUCKET_JD, record.storage_path, expires_in=expires_in)
        return {"url": url, "expires_in": expires_in, "mode": mode}
    finally:
        db.close()
