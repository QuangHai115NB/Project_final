import os
from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["UPLOAD_DIR"] = os.getenv("UPLOAD_DIR", "uploads")

    # Register API blueprint
    from src.api.routes import api_bp
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        # Tạm thời trả text cũng được, nhưng để đẹp ta render html
        return "CV Reviewer is running! Go to /api/analyze via POST."

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)