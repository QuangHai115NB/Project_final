from flask import Blueprint, g
from flask import request

from src.api.http import json_body, response
from src.core.dependencies import require_auth
from src.services.auth.auth_service import (
    change_password,
    forgot_password,
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    remove_avatar,
    reset_password,
    serialize_user_profile,
    update_avatar,
    update_profile,
    verify_email_otp,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    body = json_body("email", "password")
    return response(register_user(body["email"], body["password"]), 201)


@auth_bp.post("/verify-email")
def verify_email():
    body = json_body("email", "otp")
    return response(verify_email_otp(body["email"], body["otp"]))


@auth_bp.post("/login")
def login():
    body = json_body("email", "password")
    return response(login_user(body["email"], body["password"]))


@auth_bp.post("/refresh")
def refresh():
    body = json_body("refresh_token")
    return response(refresh_access_token(body["refresh_token"]))


@auth_bp.post("/logout")
def logout():
    body = json_body()
    return response(logout_user(body.get("refresh_token", "")))


@auth_bp.post("/forgot-password")
def forgot_pwd():
    body = json_body("email")
    return response(forgot_password(body["email"]))


@auth_bp.post("/reset-password")
def reset_pwd():
    body = json_body("email", "otp", "new_password")
    return response(reset_password(body["email"], body["otp"], body["new_password"]))


@auth_bp.post("/change-password")
@require_auth
def change_pwd():
    body = json_body("old_password", "new_password")
    return response(change_password(g.user_id, body["old_password"], body["new_password"]))


@auth_bp.get("/me")
@require_auth
def me():
    return response(serialize_user_profile(g.current_user))


@auth_bp.put("/profile")
@require_auth
def profile_update():
    body = json_body()
    return response(update_profile(g.user_id, body))


@auth_bp.post("/avatar")
@require_auth
def avatar_upload():
    return response(update_avatar(g.user_id, request.files.get("avatar")))


@auth_bp.delete("/avatar")
@require_auth
def avatar_delete():
    return response(remove_avatar(g.user_id))
