import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["UPLOAD_DIR"] = os.getenv("UPLOAD_DIR", "uploads")

    # Khởi tạo và kiểm tra kết nối DB
    from src.db.database import init_db
    init_db()

    from src.api.routes import api_bp
    from src.api.document_routes import doc_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(doc_bp)

    @app.get("/")
    def home():
        return "CV Reviewer is running!"

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)