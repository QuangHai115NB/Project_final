import os
from flask import Blueprint, request, jsonify, current_app, make_response, g
from werkzeug.utils import secure_filename
from src.core.dependencies import require_auth
from src.db.database import SessionLocal
from src.db.models import User, CVDocument, JDDocument, MatchHistory
from src.services.pdf_extractor import extract_text_from_pdf
from src.services.text_preprocess import clean_text
from src.services.section_parser import parse_sections
from src.services.rule_checker import run_rule_checks
from src.services.jd_matcher import match_cv_to_jd
import json
from src.services.languagetool_checker import check_english_language
from src.services.report_builder import build_match_report
from flask import send_file
from src.services.report_docx_generator import generate_match_report_docx
from src.services.storage import (
    upload_cv as storage_upload_cv,
    upload_jd as storage_upload_jd,
    delete_cv as storage_delete_cv,
    delete_jd as storage_delete_jd,
)
doc_bp = Blueprint("documents", __name__, url_prefix="/api")


# --- HÀM TRỢ GIÚP ---

def remove_null_bytes(text: str) -> str:
    if text:
        return text.replace('\x00', '')
    return ""


# --- API ROUTES: CV ---

@doc_bp.post("/cvs/upload")
@require_auth
def upload_cv():
    """
    Upload CV PDF lên Supabase Storage.

    Body (form-data):
      - cv_pdf: File PDF bắt buộc
      - title: Tiêu đề CV (tùy chọn)

    Returns:
      { cv_id, user_id, title, storage_url, message }
    """
    db = SessionLocal()
    try:
        user_id = g.user_id
        title = request.form.get("title", "").strip()

        if not _ensure_user_exists(db, user_id):
            return jsonify({"error": "User không tồn tại"}), 404

        file = request.files.get("cv_pdf")
        if not file or not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "CV must be a PDF file"}), 400

        # Upload lên Supabase Storage + extract text
        storage_url, storage_path, raw_text = storage_upload_cv(file, user_id)
        cleaned_text = remove_null_bytes(clean_text(raw_text))

        record = CVDocument(
            user_id=user_id,
            title=title or secure_filename(file.filename),
            original_filename=secure_filename(file.filename),
            storage_path=storage_path,  # Lưu path trong bucket (để xóa sau)
            content_text=cleaned_text,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return jsonify({
            "message": "CV uploaded successfully",
            "cv_id": record.id,
            "user_id": record.user_id,
            "title": record.title,
            "storage_url": storage_url,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.get("/cvs")
@require_auth
def list_cvs():
    """
    Lấy danh sách CV của user hiện tại.

    Returns:
      { cvs: [ { id, title, original_filename, storage_url, created_at } ] }
    """
    db = SessionLocal()
    try:
        cvs = db.query(CVDocument).filter(
            CVDocument.user_id == g.user_id
        ).order_by(CVDocument.created_at.desc()).all()

        return jsonify({
            "cvs": [
                {
                    "id": cv.id,
                    "title": cv.title,
                    "original_filename": cv.original_filename,
                    "storage_path": cv.storage_path,
                    "content_text": cv.content_text[:500] if cv.content_text else "",
                    "created_at": cv.created_at.isoformat() if cv.created_at else None,
                }
                for cv in cvs
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.delete("/cvs/delete/<cv_id>")
@require_auth
def delete_cv(cv_id):
    """
    Xóa CV: xóa file khỏi Supabase Storage + xóa record trong DB.
    """
    db = SessionLocal()
    try:
        cv_record = db.query(CVDocument).filter(
            CVDocument.id == cv_id,
            CVDocument.user_id == g.user_id
        ).first()

        if not cv_record:
            return jsonify({"error": "CV not found"}), 404

        # Xóa file khỏi Supabase Storage
        if cv_record.storage_path:
            try:
                storage_delete_cv(cv_record.storage_path)
            except Exception:
                pass  # Không crash nếu xóa file thất bại

        db.delete(cv_record)
        db.commit()

        return jsonify({"message": "CV deleted successfully"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# --- API ROUTES: JD ---

@doc_bp.post("/jds/upload")
@require_auth
def upload_jd():
    """
    Upload JD: có thể upload file (PDF/TXT) hoặc dán text trực tiếp.
    File được lưu lên Supabase Storage.

    Body (form-data):
      - jd_text: Nội dung JD dạng text (tùy chọn)
      - jd_file: File PDF/TXT (tùy chọn, ưu tiên nếu có)
      - title: Tiêu đề JD (tùy chọn)
    """
    db = SessionLocal()
    try:
        user_id = g.user_id
        title = request.form.get("title", "").strip()
        jd_text_raw = request.form.get("jd_text", "").strip()

        if not _ensure_user_exists(db, user_id):
            return jsonify({"error": "User không tồn tại"}), 404

        storage_url = ""
        storage_path = ""
        filename = "manual_jd.txt"

        # Ưu tiên upload file nếu có
        if "jd_file" in request.files and request.files["jd_file"].filename:
            file = request.files["jd_file"]
            filename = secure_filename(file.filename)

            # Upload file lên Supabase Storage
            storage_url, storage_path, extracted_text = storage_upload_jd(file, user_id)

            # Ưu tiên text extracted từ file, fallback về jd_text form
            jd_text_raw = extracted_text or jd_text_raw

        if not jd_text_raw and not storage_url:
            return jsonify({"error": "Provide jd_text or upload jd_file"}), 400

        record = JDDocument(
            user_id=user_id,
            title=title or filename,
            original_filename=filename,
            storage_path=storage_path,
            content_text=remove_null_bytes(jd_text_raw),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return jsonify({
            "message": "JD uploaded successfully",
            "jd_id": record.id,
            "title": record.title,
            "storage_url": storage_url,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.get("/jds")
@require_auth
def list_jds():
    """
    Lấy danh sách JD của user hiện tại.

    Returns:
      { jds: [ { id, title, original_filename, storage_url, created_at } ] }
    """
    db = SessionLocal()
    try:
        jds = db.query(JDDocument).filter(
            JDDocument.user_id == g.user_id
        ).order_by(JDDocument.created_at.desc()).all()

        return jsonify({
            "jds": [
                {
                    "id": jd.id,
                    "title": jd.title,
                    "original_filename": jd.original_filename,
                    "storage_path": jd.storage_path,
                    "content_text": jd.content_text[:500] if jd.content_text else "",
                    "created_at": jd.created_at.isoformat() if jd.created_at else None,
                }
                for jd in jds
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.delete("/jds/delete/<jd_id>")
@require_auth
def delete_jd(jd_id):
    """
    Xóa JD: xóa file khỏi Supabase Storage + xóa record trong DB.
    """
    db = SessionLocal()
    try:
        jd_record = db.query(JDDocument).filter(
            JDDocument.id == jd_id,
            JDDocument.user_id == g.user_id
        ).first()

        if not jd_record:
            return jsonify({"error": "JD not found"}), 404

        # Xóa file khỏi Supabase Storage
        if jd_record.storage_path:
            try:
                storage_delete_jd(jd_record.storage_path)
            except Exception:
                pass

        db.delete(jd_record)
        db.commit()

        return jsonify({"message": "JD deleted successfully"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# --- API ROUTES: MATCH ---

@doc_bp.post("/matches")
@require_auth
def create_match():
    """
    So khớp CV với JD → tạo báo cáo.

    Body (JSON):
      { cv_id, jd_id }
    """
    db = SessionLocal()
    try:
        body = request.get_json(silent=True) or {}
        user_id = g.user_id
        cv_id = body.get("cv_id")
        jd_id = body.get("jd_id")

        if not all([user_id, cv_id, jd_id]):
            return jsonify({"error": "cv_id, jd_id are required"}), 400

        cv_record = db.query(CVDocument).filter(
            CVDocument.id == cv_id,
            CVDocument.user_id == user_id
        ).first()

        jd_record = db.query(JDDocument).filter(
            JDDocument.id == jd_id,
            JDDocument.user_id == user_id
        ).first()

        if not cv_record or not jd_record:
            return jsonify({"error": "CV or JD not found for this user"}), 404

        cv_text = (cv_record.content_text or "").strip()
        jd_text = (jd_record.content_text or "").strip()

        if not cv_text:
            return jsonify({"error": "CV content is empty. Please re-upload the CV."}), 400

        if not jd_text:
            return jsonify({"error": "JD content is empty. Please re-upload the JD."}), 400

        parsed_sections = parse_sections(cv_text)
        rule_report = run_rule_checks(cv_text, parsed_sections)
        language_report = check_english_language(cv_text)
        jd_report = match_cv_to_jd(cv_text=cv_text, jd_text=jd_text, parsed_cv=parsed_sections)

        report = build_match_report(
            cv_record=cv_record,
            jd_record=jd_record,
            cv_text=cv_text,
            jd_text=jd_text,
            parsed_sections=parsed_sections,
            rule_report=rule_report,
            language_report=language_report,
            jd_report=jd_report,
        )

        history = MatchHistory(
            user_id=user_id,
            cv_id=cv_id,
            jd_id=jd_id,
            similarity_score=float(report["summary"]["final_score"]),
            report_json=json.dumps(report, ensure_ascii=False)
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return jsonify({
            "message": "Match created successfully",
            "match_id": history.id,
            "report": report
        }), 201

    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.get("/matches")
@require_auth
def list_matches():
    """Lấy danh sách lịch sử so khớp của user."""
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    db = SessionLocal()
    try:
        matches = db.query(
            MatchHistory.id,
            MatchHistory.similarity_score,
            MatchHistory.created_at,
            CVDocument.title.label("cv_title"),
            JDDocument.title.label("jd_title"),
        ).join(
            CVDocument, MatchHistory.cv_id == CVDocument.id
        ).join(
            JDDocument, MatchHistory.jd_id == JDDocument.id
        ).filter(
            MatchHistory.user_id == g.user_id
        ).order_by(
            MatchHistory.created_at.desc()
        ).offset(offset).limit(limit).all()

        return jsonify({
            "matches": [
                {
                    "id": m.id,
                    "cv_title": m.cv_title,
                    "jd_title": m.jd_title,
                    "similarity_score": float(m.similarity_score) if m.similarity_score else 0,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in matches
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.get("/matches/<match_id>")
@require_auth
def get_match_detail(match_id):
    """Lấy chi tiết một báo cáo match."""
    db = SessionLocal()
    try:
        match_record = db.query(MatchHistory).filter(
            MatchHistory.id == match_id,
            MatchHistory.user_id == g.user_id
        ).first()

        if not match_record:
            return jsonify({"error": "Match not found"}), 404

        try:
            report_json = json.loads(match_record.report_json)
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Report data bị lỗi"}), 500

        return jsonify({
            "id": match_record.id,
            "cv_id": match_record.cv_id,
            "jd_id": match_record.jd_id,
            "similarity_score": float(match_record.similarity_score) if match_record.similarity_score else 0,
            "created_at": match_record.created_at.isoformat() if match_record.created_at else None,
            "report": report_json,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.get("/matches/download/<match_id>")
@require_auth
def download_match_report(match_id):
    """Tải báo cáo so khớp dưới dạng file Word (.docx)."""
    import io

    db = SessionLocal()
    try:
        match_record = db.query(MatchHistory).filter(
            MatchHistory.id == match_id,
            MatchHistory.user_id == g.user_id
        ).first()

        if not match_record:
            return jsonify({"error": "Match not found"}), 404

        try:
            report_json = json.loads(match_record.report_json)
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Report data bị lỗi"}), 500

        docx_bytes = generate_match_report_docx(match_record, report_json)

        cv_title = report_json.get("summary", {}).get("cv_title", f"CV-{match_record.cv_id}")
        jd_title = report_json.get("summary", {}).get("jd_title", f"JD-{match_record.jd_id}")
        date_str = match_record.created_at.strftime("%Y%m%d") if match_record.created_at else ""
        safe_name = secure_filename(f"{cv_title}_vs_{jd_title}_{date_str}.docx")
        if len(safe_name) > 200:
            safe_name = f"match_report_{match_record.id}.docx"

        return send_file(
            io.BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=safe_name,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi khi tạo file Word: {str(e)}"}), 500
    finally:
        db.close()


# --- HÀM TRỢ GIÚP (INTERNAL) ---

def _ensure_user_exists(db, user_id):
    """Kiểm tra User có tồn tại trong DB không."""
    user = db.query(User).filter(User.id == user_id).first()
    return user is not None