import os
from dotenv import load_dotenv
from flask import Flask, jsonify

from src.core.errors import AppError

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["UPLOAD_DIR"] = os.getenv("UPLOAD_DIR", "uploads")
    # Giới hạn kích thước upload file: 5MB
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    # Khởi tạo và kiểm tra kết nối DB
    from src.db.database import init_db
    init_db()

    from src.api.document_routes import doc_bp
    from src.api.auth_routes import auth_bp

    app.register_blueprint(auth_bp)  # /api/auth/*
    app.register_blueprint(doc_bp)

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error", exc_info=error)
        return jsonify({"error": str(error)}), 500

    @app.get("/")
    def home():
        return "CV Reviewer is running!"

    return app

if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    app.run(debug=debug)
