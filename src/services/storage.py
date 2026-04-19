"""
Supabase Storage Service
-----------------------
Upload, download, delete files on Supabase Storage.

Flow:
  1. File uploaded to backend → extract text (giữ nguyên)
  2. Upload file lên Supabase Storage → lấy URL
  3. Lưu URL + text vào database (thay vì local path)

Buckets:
  - cv-uploads: lưu CV files
  - jd-uploads: lưu JD files

Security: Dùng SUPABASE_SERVICE_KEY (server-side only).
RLS policies trên Supabase đảm bảo chỉ authenticated user mới truy cập.
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from typing import Tuple

import requests

# ── Config ────────────────────────────────────────────────────────
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Storage bucket names
BUCKET_CV = "cv-uploads"
BUCKET_JD = "jd-uploads"

# ── HTTP helpers ───────────────────────────────────────────────

def _get_headers(use_service_key: bool = True) -> dict:
    """Get headers for Supabase API requests."""
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
    """
    Upload file lên Supabase Storage.

    Args:
        bucket: Tên bucket (cv-uploads / jd-uploads)
        file_bytes: Nội dung file
        filename: Tên file gốc (đã sanitize)
        content_type: MIME type (application/pdf, text/plain...)
        user_id: ID của user để tổ chức folder

    Returns:
        (success: bool, file_url: str, storage_path: str)
        - file_url: Public URL để lưu vào DB
        - storage_path: Path trong bucket (để xóa sau này)
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    # Tạo unique path: user_{id}/cv_{uuid}_{timestamp}.pdf
    ext = os.path.splitext(filename)[1] or ".pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    storage_path = f"user_{user_id}/{bucket.replace('-', '_')}_{timestamp}_{unique_id}{ext}"

    # Supabase Storage REST API: POST /storage/v1/object/{bucket}/{path}
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    response = requests.post(
        upload_url,
        data=file_bytes,
        headers=headers,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Upload thất bại: {response.status_code} - {response.text}"
        )

    # Public URL để lưu vào DB
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"

    return True, public_url, storage_path


def _delete_file_from_storage(bucket: str, storage_path: str) -> bool:
    """
    Xóa file khỏi Supabase Storage.

    Args:
        bucket: Tên bucket
        storage_path: Path đã lưu (user_{id}/file.ext)

    Returns:
        True nếu xóa thành công
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    delete_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }

    response = requests.delete(delete_url, headers=headers, timeout=15)

    # 200, 204, 404 đều coi là thành công (404 = file không tồn tại)
    return response.status_code in (200, 204, 404)


def _download_file_from_storage(bucket: str, storage_path: str) -> bytes:
    """
    Tải file từ Supabase Storage (dùng cho download .docx nếu cần).

    Args:
        bucket: Tên bucket
        storage_path: Path trong bucket

    Returns:
        File bytes
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL và SUPABASE_SERVICE_KEY phải được set trong .env")

    download_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }

    response = requests.get(download_url, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Download thất bại: {response.status_code} - {response.text}"
        )

    return response.content


def _extract_file_content(
    file_storage,
    bucket: str,
    user_id: int,
) -> Tuple[bytes, str, str, str]:
    """
    Extract content từ uploaded file và upload lên Supabase Storage.

    Args:
        file_storage: Flask file storage object
        bucket: Tên bucket
        user_id: User ID

    Returns:
        (file_bytes, storage_url, storage_path, text_content)
    """
    filename = file_storage.filename.lower()

    # ① Đọc nội dung file
    if filename.endswith(".pdf"):
        # Lưu tạm vào memory để extract text
        file_bytes = file_storage.read()
        file_storage.stream.seek(0)  # Reset stream để upload lại

        # Extract text từ PDF (giữ nguyên logic cũ)
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

    # ② Upload lên Supabase Storage
    safe_filename = file_storage.filename
    success, storage_url, storage_path = _upload_file_to_storage(
        bucket=bucket,
        file_bytes=file_bytes,
        filename=safe_filename,
        content_type=content_type,
        user_id=user_id,
    )

    return file_bytes, storage_url, storage_path, raw_text


# ── High-level wrappers ─────────────────────────────────────────

def upload_cv(file_storage, user_id: int) -> Tuple[str, str, str]:
    """
    Upload CV file lên Supabase Storage + extract text.

    Args:
        file_storage: Flask uploaded file
        user_id: User ID từ JWT token

    Returns:
        (storage_url, storage_path, text_content)

    Raises:
        ValueError: Nếu file không hợp lệ
        RuntimeError: Nếu upload thất bại
    """
    _, storage_url, storage_path, text = _extract_file_content(
        file_storage, BUCKET_CV, user_id
    )
    return storage_url, storage_path, text


def upload_jd(file_storage, user_id: int) -> Tuple[str, str, str]:
    """
    Upload JD file lên Supabase Storage + extract text.

    Args:
        file_storage: Flask uploaded file (PDF hoặc TXT)
        user_id: User ID từ JWT token

    Returns:
        (storage_url, storage_path, text_content)
    """
    _, storage_url, storage_path, text = _extract_file_content(
        file_storage, BUCKET_JD, user_id
    )
    return storage_url, storage_path, text


def create_signed_url(bucket: str, storage_path: str, expires_in: int = 3600) -> str:
    """
    Tạo signed URL để truy cập file private trên Supabase Storage.

    Args:
        bucket: Tên bucket (cv-uploads / jd-uploads)
        storage_path: Path trong bucket (user_{id}/file.ext)
        expires_in: Thời gian hết hạn (giây), mặc định 1 giờ

    Returns:
        Signed URL đầy đủ
    """
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
        raise RuntimeError(
            f"Tạo signed URL thất bại: {response.status_code} - {response.text}"
        )

    data = response.json()
    token_path = data.get("url", "")
    if not token_path:
        raise RuntimeError("Supabase không trả về URL — kiểm tra quyền bucket")

    # URL trả về dạng: /storage/v1/object/sign/{bucket}/path?token=...
    # Hoặc đã là full URL nếu dùng project URL
    if token_path.startswith("/"):
        return f"{SUPABASE_URL}{token_path}"
    # Trường hợp đã là full URL
    return token_path


def create_public_url(bucket: str, storage_path: str) -> str:
    """Return the direct public object URL for buckets configured as public."""
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL phải được set trong .env")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"


def create_access_url(bucket: str, storage_path: str, expires_in: int = 3600) -> tuple[str, str]:
    """
    Prefer a signed URL for private buckets, but fall back to the public URL
    so existing demo buckets still work if signing is unavailable.
    """
    try:
        return create_signed_url(bucket, storage_path, expires_in=expires_in), "signed"
    except Exception:
        return create_public_url(bucket, storage_path), "public"


def delete_cv(storage_path: str) -> bool:
    """Xóa CV file khỏi Supabase Storage."""
    return _delete_file_from_storage(BUCKET_CV, storage_path)


def delete_jd(storage_path: str) -> bool:
    """Xóa JD file khỏi Supabase Storage."""
    return _delete_file_from_storage(BUCKET_JD, storage_path)
