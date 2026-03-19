import os
from flask import Blueprint, request, jsonify, current_app, make_response
from werkzeug.utils import secure_filename
from src.db.database import SessionLocal
from src.db.models import User, CVDocument, JDDocument, MatchHistory
from src.services.pdf_extractor import extract_text_from_pdf
from src.services.text_preprocess import clean_text
from src.services.section_parser import parse_sections
from src.services.rule_checker import run_rule_checks
from src.services.jd_matcher import match_cv_to_jd
import json  # Để xử lý JSON cho report nếu cần
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
def upload_cv():
    db = SessionLocal()
    try:
        # Lấy user_id dưới dạng Integer
        user_id = request.form.get("user_id", type=int)
        title = request.form.get("title", "").strip()

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

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
def upload_jd():
    db = SessionLocal()
    try:
        user_id = request.form.get("user_id", type=int)
        title = request.form.get("title", "").strip()
        jd_text = request.form.get("jd_text", "").strip()

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

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
def create_match():
    db = SessionLocal()
    try:
        body = request.get_json(silent=True) or {}
        user_id = body.get("user_id")
        cv_id = body.get("cv_id")
        jd_id = body.get("jd_id")

        if not all([user_id, cv_id, jd_id]):
            return jsonify({"error": "user_id, cv_id, jd_id are required"}), 400

        # Truy vấn dữ liệu từ DB
        cv_record = db.query(CVDocument).filter(CVDocument.id == cv_id, CVDocument.user_id == user_id).first()
        jd_record = db.query(JDDocument).filter(JDDocument.id == jd_id, JDDocument.user_id == user_id).first()

        if not cv_record or not jd_record:
            return jsonify({"error": "CV or JD not found for this user"}), 404

        # Lấy nội dung text, đảm bảo không bị None
        cv_text = cv_record.content_text or ""
        jd_text = jd_record.content_text or ""

        # --- SỬA TẠI ĐÂY: Truyền TEXT vào hàm, không truyền ID ---
        parsed_sections = parse_sections(cv_text)
        rule_report = run_rule_checks(cv_text, parsed_sections)

        # Chú ý: Truyền cv_text và jd_text thay vì cv_id và jd_id
        jd_report = match_cv_to_jd(cv_text, jd_text)

        # Kiểm tra và ép kiểu numpy.float64 (như đã xử lý lần trước)
        if hasattr(jd_report, 'dtype') or isinstance(jd_report, (float, int)):
            score = float(jd_report)
            jd_report = {"similarity_score": score}
        elif isinstance(jd_report, dict):
            # Nếu là dict, đảm bảo score bên trong cũng là float chuẩn
            if "similarity_score" in jd_report:
                jd_report["similarity_score"] = float(jd_report["similarity_score"])

        current_score = jd_report.get("similarity_score", 0)

        report = {
            "cv_id": cv_record.id,
            "jd_id": jd_record.id,
            "sections_found": parsed_sections.get("sections_found", []),
            "jd_match": jd_report,
            "suggestions": ["Add missing sections", "Improve keywords"]
        }

        history = MatchHistory(
            user_id=user_id,
            cv_id=cv_id,
            jd_id=jd_id,
            similarity_score=current_score,
            report_json=json.dumps(report, ensure_ascii=False)  # Thêm ensure_ascii để đọc được tiếng Việt
        )
        db.add(history)
        db.commit()

        return jsonify({"message": "Match created", "match_id": history.id, "report": report}), 201

    except Exception as e:
        db.rollback()
        # In ra lỗi chi tiết để debug dễ hơn
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
