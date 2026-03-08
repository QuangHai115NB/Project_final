from flask import Blueprint, request, jsonify, current_app
import os
from werkzeug.utils import secure_filename

from src.services.pdf_extractor import extract_text_from_pdf
from src.services.text_preprocess import clean_text

api_bp = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_EXTENSIONS = {"pdf"}

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.post("/analyze")
def analyze_cv():
    """
    form-data:
      - cv_pdf: file (PDF)
      - job_description: text (optional, chưa dùng ở round 1)
    """
    if "cv_pdf" not in request.files:
        return jsonify({"error": "Missing file field 'cv_pdf'"}), 400

    f = request.files["cv_pdf"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not _allowed_file(f.filename):
        return jsonify({"error": "Only PDF files are supported"}), 400

    upload_dir = current_app.config.get("UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(f.filename)
    save_path = os.path.join(upload_dir, safe_name)
    f.save(save_path)

    raw_text, meta = extract_text_from_pdf(save_path)
    cleaned = clean_text(raw_text)

    preview = cleaned[:700].strip()

    return jsonify({
        "file": safe_name,
        "meta": meta,
        "stats": {
            "char_count": len(cleaned),
            "word_count": len(cleaned.split()),
        },
        "preview": preview
    }), 200