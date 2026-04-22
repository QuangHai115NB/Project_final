"""
Regression checks for backend fixes introduced during refactor.

Run:
    python test_backend_regressions.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

os.environ["DATABASE_URL"] = "sqlite:///test_backend_regressions.db"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-chars-minimum")
os.environ.setdefault("ALLOW_PUBLIC_URL_FALLBACK", "false")

from src.db.database import Base, SessionLocal, engine, init_db  # noqa: E402
from src.db.models import User  # noqa: E402
import src.services.auth.account_service as auth_account_service  # noqa: E402
from src.services.auth.password_service import verify_password  # noqa: E402
import src.services.storage as storage  # noqa: E402


def run_test(name: str, fn):
    print(f"\n{'=' * 60}")
    print(f"TEST: {name}")
    print("=" * 60)
    try:
        fn()
        print("PASS")
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_sqlite_init_db():
    init_db()
    inspector_db = SessionLocal()
    try:
        users = inspector_db.query(User).all()
        assert isinstance(users, list), "SQLite init should create usable tables"
    finally:
        inspector_db.close()


def test_register_updates_password_for_unverified_account():
    reset_db()

    sent_otps = []
    auth_account_service.check_otp_rate_limit = lambda email: (True, 0)
    auth_account_service.generate_otp = lambda email, purpose: "123456"
    auth_account_service.send_register_otp = lambda email, otp: sent_otps.append((email, otp))

    auth_account_service.register_user("student@example.com", "Oldpass123")
    auth_account_service.register_user("student@example.com", "Newpass456")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "student@example.com").first()
        assert user is not None, "User should exist after registration"
        assert verify_password("Newpass456", user.password_hash), "Password hash should update on re-register"
        assert not verify_password("Oldpass123", user.password_hash), "Old password should no longer be valid"
        assert len(sent_otps) == 2, "OTP should still be sent on both registration attempts"
    finally:
        db.close()


def test_storage_access_url_raises_without_public_fallback():
    original_signer = storage.create_signed_url
    storage.create_signed_url = lambda bucket, storage_path, expires_in=3600: (_ for _ in ()).throw(RuntimeError("sign failed"))
    try:
        try:
            storage.create_access_url("cv-uploads", "user_1/file.pdf")
        except RuntimeError as exc:
            assert str(exc) == "sign failed", "Signed URL errors should surface when public fallback is disabled"
        else:
            raise AssertionError("Expected signed URL creation to fail without public fallback")
    finally:
        storage.create_signed_url = original_signer


def test_storage_signed_url_accepts_supabase_signedurl_field():
    original_url = storage.SUPABASE_URL
    original_key = storage.SUPABASE_SERVICE_KEY
    original_post = storage.requests.post

    class DummyResponse:
        status_code = 200
        text = "ok"

        @staticmethod
        def json():
            return {"signedURL": "/storage/v1/object/sign/cv-uploads/user_1/file.pdf?token=abc"}

    storage.SUPABASE_URL = "https://example.supabase.co"
    storage.SUPABASE_SERVICE_KEY = "service-role-key"
    storage.requests.post = lambda *args, **kwargs: DummyResponse()
    try:
        url = storage.create_signed_url("cv-uploads", "user_1/file.pdf")
        assert url == (
            "https://example.supabase.co/storage/v1/object/sign/cv-uploads/user_1/file.pdf?token=abc"
        ), "Signed URL should support Supabase's signedURL response field"
    finally:
        storage.SUPABASE_URL = original_url
        storage.SUPABASE_SERVICE_KEY = original_key
        storage.requests.post = original_post


if __name__ == "__main__":
    tests = [
        ("SQLite init_db works", test_sqlite_init_db),
        ("Register updates password for unverified account", test_register_updates_password_for_unverified_account),
        ("Storage access respects disabled public fallback", test_storage_access_url_raises_without_public_fallback),
        ("Storage signed URL supports Supabase signedURL field", test_storage_signed_url_accepts_supabase_signedurl_field),
    ]

    for name, fn in tests:
        run_test(name, fn)

    engine.dispose()
    db_file = Path("test_backend_regressions.db")
    if db_file.exists():
        db_file.unlink()

    print(f"\n{'=' * 60}")
    print("Done.")
