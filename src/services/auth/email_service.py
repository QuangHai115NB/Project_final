"""
Email Service (Gmail SMTP)
--------------------------
Gửi email OTP qua Gmail SMTP với App Password.

Setup Gmail:
1. Bật 2-Step Verification trong tài khoản Google
2. Vào: Google Account → Security → 2-Step Verification → App passwords
3. Tạo App Password cho "Mail" → copy 16 ký tự vào SMTP_PASSWORD trong .env

Biến môi trường cần có:
    SMTP_HOST     = smtp.gmail.com
    SMTP_PORT     = 587
    SMTP_USER     = your_email@gmail.com
    SMTP_PASSWORD = xxxx xxxx xxxx xxxx   (App Password 16 ký tự)
    EMAIL_FROM    = CV Reviewer <your_email@gmail.com>
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ─────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", f"CV Reviewer <{SMTP_USER}>")
APP_NAME      = os.getenv("APP_NAME", "CV Reviewer")


# ── Core sender ────────────────────────────────────────────────────
def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Gửi email HTML qua Gmail SMTP (TLS).
    Raise Exception nếu gửi thất bại.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


# ── Template builder ───────────────────────────────────────────────
def _otp_html(otp: str, purpose_text: str, ttl_minutes: int = 5) -> str:
    return f"""
<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 2px 8px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:#2563eb;padding:28px 36px;">
            <h1 style="margin:0;color:#fff;font-size:22px;">{APP_NAME}</h1>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px;">
            <p style="margin:0 0 16px;color:#374151;font-size:15px;">
              Mã xác thực <strong>{purpose_text}</strong> của bạn là:
            </p>

            <!-- OTP box -->
            <div style="text-align:center;margin:24px 0;">
              <span style="display:inline-block;background:#eff6ff;
                           border:2px solid #2563eb;border-radius:10px;
                           padding:16px 40px;font-size:36px;font-weight:700;
                           letter-spacing:10px;color:#1d4ed8;">
                {otp}
              </span>
            </div>

            <p style="margin:0;color:#6b7280;font-size:13px;text-align:center;">
              Mã có hiệu lực trong <strong>{ttl_minutes} phút</strong>.
              Không chia sẻ mã này với bất kỳ ai.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;padding:20px 36px;
                     border-top:1px solid #e5e7eb;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">
              Nếu bạn không yêu cầu mã này, hãy bỏ qua email này.<br>
              © {APP_NAME}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ── Public API ─────────────────────────────────────────────────────
def send_register_otp(to_email: str, otp: str) -> None:
    """Gửi OTP xác thực đăng ký tài khoản."""
    _send_email(
        to_email=to_email,
        subject=f"[{APP_NAME}] Mã xác thực đăng ký tài khoản",
        html_body=_otp_html(otp, purpose_text="đăng ký tài khoản"),
    )


def send_reset_password_otp(to_email: str, otp: str) -> None:
    """Gửi OTP đặt lại mật khẩu."""
    _send_email(
        to_email=to_email,
        subject=f"[{APP_NAME}] Mã xác thực đặt lại mật khẩu",
        html_body=_otp_html(otp, purpose_text="đặt lại mật khẩu"),
    )