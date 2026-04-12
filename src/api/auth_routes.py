"""
Auth Routes  —  /api/auth/*
----------------------------
POST /api/auth/register          Đăng ký tài khoản mới
POST /api/auth/verify-email      Xác thực OTP đăng ký
POST /api/auth/login             Đăng nhập
POST /api/auth/refresh           Làm mới access token
POST /api/auth/logout            Đăng xuất (revoke refresh token)
POST /api/auth/forgot-password   Gửi OTP quên mật khẩu
POST /api/auth/reset-password    Đặt lại mật khẩu bằng OTP
POST /api/auth/change-password   Đổi mật khẩu (cần đăng nhập)
GET  /api/auth/me                Lấy thông tin user hiện tại
"""
from flask import Blueprint, jsonify, request, g

from src.core.dependencies import require_auth
from src.services.auth.auth_service import (
    change_password,
    forgot_password,
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    reset_password,
    verify_email_otp,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ── Helpers ────────────────────────────────────────────────────────
def _json_body(*required_fields):
    """Lấy JSON body và validate các trường bắt buộc."""
    body = request.get_json(silent=True) or {}
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        return None, jsonify({"error": f"Thiếu trường bắt buộc: {', '.join(missing)}"}), 400
    return body, None, None


# ── Endpoints ──────────────────────────────────────────────────────

@auth_bp.post("/register")
def register():
    """
    Body: { "email": str, "password": str }
    → Tạo tài khoản + gửi OTP xác thực email
    """
    body, err, code = _json_body("email", "password")
    if err:
        return err, code

    try:
        result = register_user(body["email"], body["password"])
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"REGISTER ERROR: {e}")  # thêm dòng này
        import traceback;
        traceback.print_exc()  # thêm dòng này
        return jsonify({"error": str(e)}), 500

@auth_bp.post("/verify-email")
def verify_email():
    """
    Body: { "email": str, "otp": str }
    → Xác thực OTP → trả access_token + refresh_token
    """
    body, err, code = _json_body("email", "otp")
    if err:
        return err, code

    try:
        result = verify_email_otp(body["email"], body["otp"])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.post("/login")
def login():
    """
    Body: { "email": str, "password": str }
    → Trả access_token + refresh_token
    """
    body, err, code = _json_body("email", "password")
    if err:
        return err, code

    try:
        result = login_user(body["email"], body["password"])
        return jsonify(result), 200
    except ValueError as e:
        # 429 nếu bị block do brute-force
        status = 429 if "bị khóa" in str(e) else 401
        return jsonify({"error": str(e)}), status


@auth_bp.post("/refresh")
def refresh():
    """
    Body: { "refresh_token": str }
    → Trả access_token mới + refresh_token mới (rotation)
    """
    body, err, code = _json_body("refresh_token")
    if err:
        return err, code

    try:
        result = refresh_access_token(body["refresh_token"])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.post("/logout")
def logout():
    """
    Body: { "refresh_token": str }
    → Revoke refresh token
    Không cần access token (user có thể đã hết hạn access nhưng vẫn muốn logout)
    """
    body = request.get_json(silent=True) or {}
    refresh_token = body.get("refresh_token", "")

    result = logout_user(refresh_token)
    return jsonify(result), 200


@auth_bp.post("/forgot-password")
def forgot_pwd():
    """
    Body: { "email": str }
    → Gửi OTP đặt lại mật khẩu (luôn trả 200 để tránh user enumeration)
    """
    body, err, code = _json_body("email")
    if err:
        return err, code

    try:
        result = forgot_password(body["email"])
        return jsonify(result), 200
    except ValueError as e:
        status = 429 if "Thử lại sau" in str(e) else 400
        return jsonify({"error": str(e)}), status


@auth_bp.post("/reset-password")
def reset_pwd():
    """
    Body: { "email": str, "otp": str, "new_password": str }
    → Xác thực OTP + cập nhật mật khẩu mới
    """
    body, err, code = _json_body("email", "otp", "new_password")
    if err:
        return err, code

    try:
        result = reset_password(body["email"], body["otp"], body["new_password"])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.post("/change-password")
@require_auth
def change_pwd():
    """
    Header: Authorization: Bearer <access_token>
    Body:   { "old_password": str, "new_password": str }
    → Đổi mật khẩu khi đã đăng nhập
    """
    body, err, code = _json_body("old_password", "new_password")
    if err:
        return err, code

    try:
        result = change_password(g.user_id, body["old_password"], body["new_password"])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.get("/me")
@require_auth
def me():
    """
    Header: Authorization: Bearer <access_token>
    → Trả thông tin user hiện tại
    """
    user = g.current_user
    return jsonify({
        "id":          user.id,
        "email":       user.email,
        "is_verified": user.is_verified,
        "created_at":  user.created_at.isoformat() if user.created_at else None,
    }), 200