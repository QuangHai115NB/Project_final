"""
Route-level regression tests using Flask's test client.

Run:
    python test_api_routes.py
"""
from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

os.environ["DATABASE_URL"] = "sqlite:///test_api_routes.db"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-32-chars-minimum")
os.environ.setdefault("ALLOW_PUBLIC_URL_FALLBACK", "false")

from app import create_app  # noqa: E402
from src.db.database import Base, SessionLocal, engine  # noqa: E402
from src.db.models import CVDocument, JDDocument, User  # noqa: E402
from src.services.auth.password_service import hash_password  # noqa: E402
import src.services.auth.account_service as auth_account_service  # noqa: E402
import src.api.auth_routes as auth_routes  # noqa: E402
import src.services.documents.cv_service as cv_service  # noqa: E402
import src.services.documents.jd_service as jd_service  # noqa: E402


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


def create_verified_user(email: str = "api@example.com", password: str = "Password123") -> User:
    db = SessionLocal()
    try:
        user = User(email=email, password_hash=hash_password(password), is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def issue_access_token(email: str = "api@example.com", password: str = "Password123") -> str:
    auth_account_service.check_login_rate_limit = lambda email: (True, 0)
    auth_account_service.reset_login_failures = lambda email: None
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    payload = response.get_json()
    assert response.status_code == 200, payload
    return payload["access_token"]


app = create_app()
client = app.test_client()


def test_register_missing_field_returns_standard_error():
    response = client.post("/api/auth/register", json={"email": "user@example.com"})
    assert response.status_code == 400, response.get_json()
    assert response.get_json() == {"error": "Thiếu trường bắt buộc: password"}


def test_protected_route_requires_bearer_token():
    response = client.get("/api/auth/me")
    assert response.status_code == 401, response.get_json()
    assert "Authorization" in response.get_json()["error"]


def test_login_and_me_flow():
    reset_db()
    create_verified_user()
    token = issue_access_token()

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200, me_response.get_json()
    me_payload = me_response.get_json()
    assert me_payload["email"] == "api@example.com"
    assert me_payload["is_verified"] is True


def test_profile_update_flow():
    reset_db()
    create_verified_user()
    token = issue_access_token()

    response = client.put(
        "/api/auth/profile",
        json={
            "full_name": "Nguyen Hai",
            "phone": "0901234567",
            "headline": "Backend Developer",
            "bio": "Builds Flask APIs and matching pipelines.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["user"]["full_name"] == "Nguyen Hai"
    assert payload["user"]["phone"] == "0901234567"
    assert payload["user"]["headline"] == "Backend Developer"
    assert payload["user"]["bio"] == "Builds Flask APIs and matching pipelines."


def test_avatar_upload_and_delete_routes():
    reset_db()
    create_verified_user()
    token = issue_access_token()

    original_update_avatar = auth_routes.update_avatar
    original_remove_avatar = auth_routes.remove_avatar
    auth_routes.update_avatar = lambda user_id, file_storage: {
        "message": "avatar updated",
        "user": {
            "id": user_id,
            "email": "api@example.com",
            "is_verified": True,
            "full_name": None,
            "phone": None,
            "headline": None,
            "bio": None,
            "avatar_url": "https://storage.example/avatar.webp",
            "created_at": None,
        },
    }
    auth_routes.remove_avatar = lambda user_id: {
        "message": "avatar removed",
        "user": {
            "id": user_id,
            "email": "api@example.com",
            "is_verified": True,
            "full_name": None,
            "phone": None,
            "headline": None,
            "bio": None,
            "avatar_url": None,
            "created_at": None,
        },
    }
    try:
        upload_response = client.post(
            "/api/auth/avatar",
            data={"avatar": (BytesIO(b"fake-image"), "avatar.webp")},
            headers={"Authorization": f"Bearer {token}"},
            content_type="multipart/form-data",
        )
        upload_payload = upload_response.get_json()
        assert upload_response.status_code == 200, upload_payload
        assert upload_payload["user"]["avatar_url"] == "https://storage.example/avatar.webp"

        delete_response = client.delete(
            "/api/auth/avatar",
            headers={"Authorization": f"Bearer {token}"},
        )
        delete_payload = delete_response.get_json()
        assert delete_response.status_code == 200, delete_payload
        assert delete_payload["user"]["avatar_url"] is None
    finally:
        auth_routes.update_avatar = original_update_avatar
        auth_routes.remove_avatar = original_remove_avatar


def test_match_route_validation_is_preserved():
    reset_db()
    create_verified_user()
    token = issue_access_token()

    match_response = client.post(
        "/api/matches",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert match_response.status_code == 400, match_response.get_json()
    assert match_response.get_json() == {"error": "cv_id, jd_id are required"}


def test_cv_upload_route_with_mock_storage():
    reset_db()
    user = create_verified_user()
    token = issue_access_token()

    original_upload_cv = cv_service.storage_upload_cv
    cv_service.storage_upload_cv = lambda file_storage, user_id: (
        "https://storage.example/cv.pdf",
        f"user_{user_id}/cv.pdf",
        "SUMMARY\nPython backend engineer\nSKILLS\nPython, Flask\nEXPERIENCE\nBuilt APIs",
    )
    try:
        response = client.post(
            "/api/cvs/upload",
            data={
                "title": "Backend CV",
                "cv_pdf": (BytesIO(b"%PDF-1.4 fake"), "candidate.pdf"),
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="multipart/form-data",
        )
        payload = response.get_json()
        assert response.status_code == 201, payload
        assert payload["title"] == "Backend CV"

        db = SessionLocal()
        try:
            records = db.query(CVDocument).filter(CVDocument.user_id == user.id).all()
            assert len(records) == 1, "CV upload should persist a record"
            assert records[0].content_text.startswith("SUMMARY"), "Extracted text should be saved"
        finally:
            db.close()
    finally:
        cv_service.storage_upload_cv = original_upload_cv


def test_jd_upload_and_match_flow():
    reset_db()
    user = create_verified_user()
    token = issue_access_token()

    original_upload_cv = cv_service.storage_upload_cv
    original_upload_jd = jd_service.storage_upload_jd
    cv_service.storage_upload_cv = lambda file_storage, user_id: (
        "https://storage.example/cv.pdf",
        f"user_{user_id}/cv.pdf",
        "SUMMARY\nBackend Engineer\nSKILLS\nPython, Django, PostgreSQL, REST API\n"
        "EXPERIENCE\n- Developed REST APIs using Django and PostgreSQL for internal platform, supporting 1000 users.",
    )
    jd_service.storage_upload_jd = lambda file_storage, user_id: (
        "https://storage.example/jd.txt",
        f"user_{user_id}/jd.txt",
        "Backend Engineer\nRequirements:\n- Python\n- Django\n- PostgreSQL\n- REST API\n"
        "Responsibilities:\n- Build and maintain backend APIs.",
    )
    try:
        cv_response = client.post(
            "/api/cvs/upload",
            data={"cv_pdf": (BytesIO(b"%PDF-1.4 fake"), "candidate.pdf")},
            headers={"Authorization": f"Bearer {token}"},
            content_type="multipart/form-data",
        )
        jd_response = client.post(
            "/api/jds/upload",
            data={"jd_file": (BytesIO(b"backend jd"), "job.txt")},
            headers={"Authorization": f"Bearer {token}"},
            content_type="multipart/form-data",
        )
        assert cv_response.status_code == 201, cv_response.get_json()
        assert jd_response.status_code == 201, jd_response.get_json()

        match_response = client.post(
            "/api/matches",
            json={
                "cv_id": cv_response.get_json()["cv_id"],
                "jd_id": jd_response.get_json()["jd_id"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        payload = match_response.get_json()
        assert match_response.status_code == 201, payload
        assert payload["match_id"] > 0
        assert payload["report"]["summary"]["final_score"] >= 0

        db = SessionLocal()
        try:
            assert db.query(JDDocument).filter(JDDocument.user_id == user.id).count() == 1
        finally:
            db.close()
    finally:
        cv_service.storage_upload_cv = original_upload_cv
        jd_service.storage_upload_jd = original_upload_jd


if __name__ == "__main__":
    tests = [
        ("Register missing field returns standard error", test_register_missing_field_returns_standard_error),
        ("Protected route requires bearer token", test_protected_route_requires_bearer_token),
        ("Login and /me flow works", test_login_and_me_flow),
        ("Profile update flow works", test_profile_update_flow),
        ("Avatar upload and delete routes work", test_avatar_upload_and_delete_routes),
        ("Match route validation is preserved", test_match_route_validation_is_preserved),
        ("CV upload route works with mock storage", test_cv_upload_route_with_mock_storage),
        ("JD upload and match flow works with mock storage", test_jd_upload_and_match_flow),
    ]

    for name, fn in tests:
        run_test(name, fn)

    engine.dispose()
    db_file = Path("test_api_routes.db")
    if db_file.exists():
        db_file.unlink()

    print(f"\n{'=' * 60}")
    print("Done.")
