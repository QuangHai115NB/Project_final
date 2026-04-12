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
import json  # Để xử lý JSON cho report nếu cần
from src.services.languagetool_checker import check_english_language
from src.services.report_builder import build_match_report
from flask import send_file
from src.services.report_docx_generator import generate_match_report_docx
doc_bp = Blueprint("documents", __name__, url_prefix="/api")


# --- HÀM TRỢ GIÚP ---

def _extract_jd_text(file_storage, save_path):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        raw_text, _ = extract_text_from_pdf(save_path)
        return raw_text
    if filename.endswith(".txt"):
        file_storage.stream.seek(0)
        raw_bytes = file_storage.read()
        return raw_bytes.decode("utf-8", errors="ignore")
    return ""


def _save_uploaded_file(file_storage, subfolder: str):
    upload_root = current_app.config.get("UPLOAD_DIR", "uploads")
    folder_path = os.path.join(upload_root, subfolder)
    os.makedirs(folder_path, exist_ok=True)
    safe_name = secure_filename(file_storage.filename)
    save_path = os.path.join(folder_path, safe_name)
    file_storage.save(save_path)
    return safe_name, save_path


def remove_null_bytes(text: str) -> str:
    if text:
        return text.replace('\x00', '')
    return ""


def _ensure_user_exists(db, user_id):
    """Kiểm tra xem User có tồn tại trong DB không để tránh lỗi ForeignKey"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    return True


# --- API ROUTES ---

@doc_bp.post("/cvs/upload")
@require_auth
def upload_cv():
    db = SessionLocal()
    try:
        # Lấy user_id từ token đã xác thực, KHÔNG từ request
        user_id = g.user_id
        title = request.form.get("title", "").strip()

        # KIỂM TRA QUAN TRỌNG: User phải có trong bảng users
        if not _ensure_user_exists(db, user_id):
            return jsonify({"error": f"User ID {user_id} không tồn tại trong hệ thống. Vui lòng tạo user trước."}), 404

        file = request.files.get("cv_pdf")
        if not file or not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "CV must be a PDF file"}), 400

        safe_name, save_path = _save_uploaded_file(file, "cvs")
        raw_text, _ = extract_text_from_pdf(save_path)
        cleaned_text = remove_null_bytes(clean_text(raw_text))

        record = CVDocument(
            user_id=user_id,  # Truyền thẳng số nguyên vào đây
            title=title or safe_name,
            original_filename=safe_name,
            storage_path=save_path,
            content_text=cleaned_text
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return jsonify({
            "message": "CV uploaded successfully",
            "cv_id": record.id,
            "user_id": record.user_id
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.post("/jds/upload")
@require_auth
def upload_jd():
    db = SessionLocal()
    try:
        # Lấy user_id từ token đã xác thực
        user_id = g.user_id
        title = request.form.get("title", "").strip()
        jd_text = request.form.get("jd_text", "").strip()

        if not _ensure_user_exists(db, user_id):
            return jsonify({"error": f"User ID {user_id} không tồn tại."}), 404

        filename = "manual_jd.txt"
        save_path = ""

        if "jd_file" in request.files and request.files["jd_file"].filename:
            file = request.files["jd_file"]
            safe_name, save_path = _save_uploaded_file(file, "jds")
            extracted_text = _extract_jd_text(file, save_path)
            filename = safe_name
            jd_text = extracted_text or jd_text

        if not jd_text:
            return jsonify({"error": "Provide jd_text or upload jd_file"}), 400

        record = JDDocument(
            user_id=user_id,
            title=title or filename,
            original_filename=filename,
            storage_path=save_path,
            content_text=remove_null_bytes(jd_text)
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return jsonify({
            "message": "JD uploaded successfully",
            "jd_id": record.id
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@doc_bp.post("/matches")
@require_auth
def create_match():
    db = SessionLocal()
    try:
        body = request.get_json(silent=True) or {}
        # Lấy user_id từ token đã xác thực
        user_id = g.user_id
        cv_id = body.get("cv_id")
        jd_id = body.get("jd_id")

        if not all([user_id, cv_id, jd_id]):
            return jsonify({"error": "user_id, cv_id, jd_id are required"}), 400

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
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@doc_bp.put("/csv/update/<cv_id>")
@require_auth
def update_csv(cv_id):
    db = SessionLocal()
    try:
        cv_record = db.query(CVDocument).filter(CVDocument.id == cv_id).first()
        if not cv_record:
            return jsonify({"error": "CV not found"}), 404
        if cv_record.user_id != g.user_id:
            return jsonify({"error": "Unauthorized - Bạn không có quyền sửa CV này"}), 403

        cv_record.title = request.json.get("title", cv_record.title)
        cv_record.content_text = request.json.get("content_text", cv_record.content_text)

        db.commit()
        db.refresh(cv_record)
        return jsonify({"message": "CV updated successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# API để sửa CV
@doc_bp.put("/cvs/update/<cv_id>")
@require_auth
def update_cv(cv_id):
    db = SessionLocal()
    try:
        cv_record = db.query(CVDocument).filter(CVDocument.id == cv_id).first()
        if not cv_record:
            return jsonify({"error": "CV not found"}), 404
        if cv_record.user_id != g.user_id:
            return jsonify({"error": "Unauthorized - Bạn không có quyền sửa CV này"}), 403

        # Update dữ liệu CV
        cv_record.title = request.json.get("title", cv_record.title)
        cv_record.content_text = request.json.get("content_text", cv_record.content_text)

        db.commit()
        db.refresh(cv_record)

        return jsonify({"message": "CV updated successfully", "cv": cv_record.title}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# API để xóa CV
@doc_bp.delete("/cvs/delete/<cv_id>")
@require_auth
def delete_cv(cv_id):
    db = SessionLocal()
    try:
        cv_record = db.query(CVDocument).filter(CVDocument.id == cv_id).first()
        if not cv_record:
            return jsonify({"error": "CV not found"}), 404
        if cv_record.user_id != g.user_id:
            return jsonify({"error": "Unauthorized - Bạn không có quyền xóa CV này"}), 403

        db.delete(cv_record)
        db.commit()

        return jsonify({"message": "CV deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# API để sửa JD
@doc_bp.put("/jds/update/<jd_id>")
@require_auth
def update_jd(jd_id):
    db = SessionLocal()
    try:
        jd_record = db.query(JDDocument).filter(JDDocument.id == jd_id).first()
        if not jd_record:
            return jsonify({"error": "JD not found"}), 404
        if jd_record.user_id != g.user_id:
            return jsonify({"error": "Unauthorized - Bạn không có quyền sửa JD này"}), 403

        # Update dữ liệu JD
        jd_record.title = request.json.get("title", jd_record.title)
        jd_record.content_text = request.json.get("content_text", jd_record.content_text)

        db.commit()
        db.refresh(jd_record)

        return jsonify({"message": "JD updated successfully", "jd": jd_record.title}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# API để xóa JD
@doc_bp.delete("/jds/delete/<jd_id>")
@require_auth
def delete_jd(jd_id):
    db = SessionLocal()
    try:
        jd_record = db.query(JDDocument).filter(JDDocument.id == jd_id).first()
        if not jd_record:
            return jsonify({"error": "JD not found"}), 404
        if jd_record.user_id != g.user_id:
            return jsonify({"error": "Unauthorized - Bạn không có quyền xóa JD này"}), 403

        db.delete(jd_record)
        db.commit()

        return jsonify({"message": "JD deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# --- DOWNLOAD MATCH REPORT AS WORD (.docx) ---

@doc_bp.get("/matches/download/<match_id>")
@require_auth
def download_match_report(match_id):
    """
    Tải báo cáo so khớp CV-JD dưới dạng file Word (.docx).

    Header: Authorization: Bearer <access_token>
    Response: application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    import io
    from datetime import datetime

    db = SessionLocal()
    try:
        # Lấy match record kèm CV, JD
        match_record = db.query(MatchHistory).filter(
            MatchHistory.id == match_id,
            MatchHistory.user_id == g.user_id
        ).first()

        if not match_record:
            return jsonify({"error": "Match not found hoặc bạn không có quyền truy cập"}), 404

        # Parse report JSON
        try:
            report_json = json.loads(match_record.report_json)
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Report data bị lỗi, vui lòng tạo lại match"}), 500

        # Generate DOCX
        docx_bytes = generate_match_report_docx(match_record, report_json)

        # Tạo filename đẹp
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


# --- GET MATCH HISTORY LIST ---

@doc_bp.get("/matches")
@require_auth
def list_matches():
    """
    Lấy danh sách lịch sử so khớp của user hiện tại.

    Header: Authorization: Bearer <access_token>
    Query params (optional):
        limit: int (default 20)
        offset: int (default 0)
    """
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


# --- GET SINGLE MATCH DETAIL ---

@doc_bp.get("/matches/<match_id>")
@require_auth
def get_match_detail(match_id):
    """
    Lấy chi tiết một báo cáo match (report JSON đầy đủ).

    Header: Authorization: Bearer <access_token>
    """
    db = SessionLocal()
    try:
        match_record = db.query(MatchHistory).filter(
            MatchHistory.id == match_id,
            MatchHistory.user_id == g.user_id
        ).first()

        if not match_record:
            return jsonify({"error": "Match not found hoặc bạn không có quyền truy cập"}), 404

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
