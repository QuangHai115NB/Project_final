"""
Supabase storage integration.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Tuple

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
ALLOW_PUBLIC_URL_FALLBACK = os.getenv("ALLOW_PUBLIC_URL_FALLBACK", "false").lower() in ("true", "1", "yes")

BUCKET_CV = "cv-uploads"
BUCKET_JD = "jd-uploads"
BUCKET_AVATAR = "user-avatars"


def _get_headers(use_service_key: bool = True) -> dict:
    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": "application/json",
    }


def _upload_file_to_storage(
    bucket: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: int,
) -> Tuple[bool, str, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    ext = os.path.splitext(filename)[1] or ".pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    storage_path = f"user_{user_id}/{bucket.replace('-', '_')}_{timestamp}_{unique_id}{ext}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    response = requests.post(upload_url, data=file_bytes, headers=headers, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Upload thất bại: {response.status_code} - {response.text}")

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
    return True, public_url, storage_path


def _upload_binary_to_storage(
    *,
    bucket: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: int,
) -> tuple[str, str]:
    _, public_url, storage_path = _upload_file_to_storage(
        bucket=bucket,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        user_id=user_id,
    )
    return public_url, storage_path


def _delete_file_from_storage(bucket: str, storage_path: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    delete_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }
    response = requests.delete(delete_url, headers=headers, timeout=15)
    return response.status_code in (200, 204, 404)


def _download_file_from_storage(bucket: str, storage_path: str) -> tuple[bytes, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL vÃ  SUPABASE_SERVICE_KEY pháº£i Ä‘Æ°á»£c set trong .env")

    download_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }
    response = requests.get(download_url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Táº£i file tháº¥t báº¡i: {response.status_code} - {response.text}")

    return response.content, response.headers.get("Content-Type", "application/octet-stream")


def _extract_file_content(file_storage, bucket: str, user_id: int) -> Tuple[bytes, str, str, str]:
    filename = file_storage.filename.lower()

    if filename.endswith(".pdf"):
        file_bytes = file_storage.read()
        file_storage.stream.seek(0)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            from src.services.pdf_extractor import extract_text_from_pdf

            raw_text, _ = extract_text_from_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)

        content_type = "application/pdf"
    elif filename.endswith(".txt"):
        file_bytes = file_storage.read()
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        content_type = "text/plain"
    else:
        raise ValueError("Chỉ hỗ trợ file PDF hoặc TXT")

    _, storage_url, storage_path = _upload_file_to_storage(
        bucket=bucket,
        file_bytes=file_bytes,
        filename=file_storage.filename,
        content_type=content_type,
        user_id=user_id,
    )
    return file_bytes, storage_url, storage_path, raw_text


def upload_cv(file_storage, user_id: int) -> Tuple[str, str, str]:
    _, storage_url, storage_path, text = _extract_file_content(file_storage, BUCKET_CV, user_id)
    return storage_url, storage_path, text


def upload_jd(file_storage, user_id: int) -> Tuple[str, str, str]:
    _, storage_url, storage_path, text = _extract_file_content(file_storage, BUCKET_JD, user_id)
    return storage_url, storage_path, text


def create_signed_url(bucket: str, storage_path: str, expires_in: int = 3600) -> str:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": "application/json",
    }
    payload = {"expiresIn": expires_in}

    response = requests.post(sign_url, json=payload, headers=headers, timeout=15)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Tạo signed URL thất bại: {response.status_code} - {response.text}")

    data = response.json()
    token_path = data.get("signedURL") or data.get("signedUrl") or data.get("url", "")
    if not token_path:
        raise RuntimeError("Supabase không trả về URL - kiểm tra quyền bucket")

    if token_path.startswith("/"):
        return f"{SUPABASE_URL}{token_path}"
    return token_path


def create_public_url(bucket: str, storage_path: str) -> str:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL phải được set trong .env")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"


def create_access_url(bucket: str, storage_path: str, expires_in: int = 3600) -> tuple[str, str]:
    try:
        return create_signed_url(bucket, storage_path, expires_in=expires_in), "signed"
    except Exception:
        if ALLOW_PUBLIC_URL_FALLBACK:
            return create_public_url(bucket, storage_path), "public"
        raise


def delete_cv(storage_path: str) -> bool:
    return _delete_file_from_storage(BUCKET_CV, storage_path)


def delete_jd(storage_path: str) -> bool:
    return _delete_file_from_storage(BUCKET_JD, storage_path)


def download_cv(storage_path: str) -> tuple[bytes, str]:
    return _download_file_from_storage(BUCKET_CV, storage_path)


def download_jd(storage_path: str) -> tuple[bytes, str]:
    return _download_file_from_storage(BUCKET_JD, storage_path)


def upload_avatar(file_storage, user_id: int) -> tuple[str, str]:
    if not file_storage or not file_storage.filename:
        raise ValueError("Avatar file is required")

    filename = file_storage.filename
    lowered = filename.lower()
    if not lowered.endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise ValueError("Avatar must be a PNG, JPG, JPEG, or WEBP image")

    file_bytes = file_storage.read()
    if not file_bytes:
        raise ValueError("Avatar file is empty")

    content_type = getattr(file_storage, "mimetype", None) or "application/octet-stream"
    return _upload_binary_to_storage(
        bucket=BUCKET_AVATAR,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        user_id=user_id,
    )


def delete_avatar(storage_path: str) -> bool:
    return _delete_file_from_storage(BUCKET_AVATAR, storage_path)
