from __future__ import annotations

import json

from werkzeug.utils import secure_filename

from src.core.errors import NotFoundError, ValidationError
from src.db.database import SessionLocal
from src.db.repository import CVRepository, JDRepository, MatchRepository, UserRepository
from src.services.jd_matcher import match_cv_to_jd
from src.services.report_builder import build_match_report
from src.services.report_docx_generator import generate_match_report_docx
from src.services.report_pdf_generator import generate_match_report_pdf
from src.services.rule_checker import run_rule_checks
from src.services.section_parser import parse_sections
from src.services.text_preprocess import clean_text
from src.services.quota_service import ensure_can_create_match
from src.services.time_service import to_app_datetime, utc_iso


def _pagination(limit: int = 10, offset: int = 0, max_limit: int = 50) -> tuple[int, int]:
    safe_limit = max(1, min(limit or 10, max_limit))
    safe_offset = max(0, offset or 0)
    return safe_limit, safe_offset


def create_match_report(*, user_id: int, cv_id: int, jd_id: int) -> dict:
    if not all([user_id, cv_id, jd_id]):
        raise ValidationError("cv_id, jd_id are required")

    db = SessionLocal()
    try:
        cv_repo = CVRepository(db)
        jd_repo = JDRepository(db)
        match_repo = MatchRepository(db)
        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundError("User không tồn tại")
        ensure_can_create_match(db, user)

        cv_record = cv_repo.get_for_user(cv_id, user_id)
        jd_record = jd_repo.get_for_user(jd_id, user_id)
        if not cv_record or not jd_record:
            raise NotFoundError("CV or JD not found for this user")

        cv_text = clean_text(cv_record.content_text or "")
        jd_text = clean_text(jd_record.content_text or "")
        if not cv_text:
            raise ValidationError("CV content is empty. Please re-upload the CV.")
        if not jd_text:
            raise ValidationError("JD content is empty. Please re-upload the JD.")

        parsed_sections = parse_sections(cv_text)
        rule_report = run_rule_checks(cv_text, parsed_sections)
        jd_report = match_cv_to_jd(
            cv_text=cv_text,
            jd_text=jd_text,
            parsed_cv=parsed_sections,
        )
        report = build_match_report(
            cv_record=cv_record,
            jd_record=jd_record,
            cv_text=cv_text,
            jd_text=jd_text,
            parsed_sections=parsed_sections,
            rule_report=rule_report,
            jd_report=jd_report,
        )
        history = match_repo.create(
            user_id=user_id,
            cv_id=cv_id,
            jd_id=jd_id,
            similarity_score=float(report["summary"]["final_score"]),
            report_json=json.dumps(report, ensure_ascii=False),
        )
        return {
            "message": "Match created successfully",
            "match_id": history.id,
            "report": report,
        }
    finally:
        db.close()


def list_match_reports(*, user_id: int, limit: int = 10, offset: int = 0) -> dict:
    safe_limit, safe_offset = _pagination(limit, offset)
    db = SessionLocal()
    try:
        repo = MatchRepository(db)
        total = repo.count_by_user(user_id)
        matches = repo.list_by_user(user_id, limit=safe_limit, offset=safe_offset)
        return {
            "matches": [
                {
                    "id": item.id,
                    "cv_title": item.cv_title,
                    "jd_title": item.jd_title,
                    "similarity_score": float(item.similarity_score) if item.similarity_score else 0,
                    "created_at": utc_iso(item.created_at),
                }
                for item in matches
            ],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "total": total,
                "has_next": safe_offset + safe_limit < total,
                "has_prev": safe_offset > 0,
            },
        }
    finally:
        db.close()


def get_match_detail(*, user_id: int, match_id: int) -> dict:
    db = SessionLocal()
    try:
        record = MatchRepository(db).get_for_user(match_id, user_id)
        if not record:
            raise NotFoundError("Match not found")
        try:
            report_json = json.loads(record.report_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValidationError("Report data bị lỗi") from exc

        return {
            "id": record.id,
            "cv_id": record.cv_id,
            "jd_id": record.jd_id,
            "similarity_score": float(record.similarity_score) if record.similarity_score else 0,
            "user_review": record.user_review or "",
            "created_at": utc_iso(record.created_at),
            "report": report_json,
        }
    finally:
        db.close()


def update_match_review(*, user_id: int, match_id: int, user_review: str | None) -> dict:
    cleaned = (user_review or "").strip()
    if len(cleaned) > 2000:
        raise ValidationError("Review không được vượt quá 2000 ký tự")

    db = SessionLocal()
    try:
        repo = MatchRepository(db)
        record = repo.get_for_user(match_id, user_id)
        if not record:
            raise NotFoundError("Match not found")
        record = repo.update_user_review(record, cleaned or None)
        return {
            "message": "Đã lưu đánh giá",
            "match_id": record.id,
            "user_review": record.user_review or "",
        }
    finally:
        db.close()


def delete_match_report(*, user_id: int, match_id: int) -> dict:
    db = SessionLocal()
    try:
        repo = MatchRepository(db)
        record = repo.get_for_user(match_id, user_id)
        if not record:
            raise NotFoundError("Match not found")
        repo.delete(record)
        return {"message": "Match report deleted successfully"}
    finally:
        db.close()


def download_match_report(*, user_id: int, match_id: int) -> tuple[bytes, str]:
    db = SessionLocal()
    try:
        record = MatchRepository(db).get_for_user(match_id, user_id)
        if not record:
            raise NotFoundError("Match not found")
        try:
            report_json = json.loads(record.report_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValidationError("Report data bị lỗi") from exc

        docx_bytes = generate_match_report_docx(record, report_json)
        cv_title = report_json.get("summary", {}).get("cv_title", f"CV-{record.cv_id}")
        jd_title = report_json.get("summary", {}).get("jd_title", f"JD-{record.jd_id}")
        date_str = to_app_datetime(record.created_at).strftime("%Y%m%d") if record.created_at else ""
        safe_name = secure_filename(f"{cv_title}_vs_{jd_title}_{date_str}.docx")
        if len(safe_name) > 200:
            safe_name = f"match_report_{record.id}.docx"
        return docx_bytes, safe_name
    finally:
        db.close()


def download_match_report_pdf(*, user_id: int, match_id: int) -> tuple[bytes, str]:
    db = SessionLocal()
    try:
        record = MatchRepository(db).get_for_user(match_id, user_id)
        if not record:
            raise NotFoundError("Match not found")
        try:
            report_json = json.loads(record.report_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValidationError("Report data bi loi") from exc

        pdf_bytes = generate_match_report_pdf(record, report_json)
        cv_title = report_json.get("summary", {}).get("cv_title", f"CV-{record.cv_id}")
        jd_title = report_json.get("summary", {}).get("jd_title", f"JD-{record.jd_id}")
        date_str = to_app_datetime(record.created_at).strftime("%Y%m%d") if record.created_at else ""
        safe_name = secure_filename(f"{cv_title}_vs_{jd_title}_{date_str}.pdf")
        if len(safe_name) > 200:
            safe_name = f"match_report_{record.id}.pdf"
        return pdf_bytes, safe_name
    finally:
        db.close()
