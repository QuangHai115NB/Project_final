from flask import Blueprint

from src.api.routes import cv_bp, file_bp, jd_bp, match_bp

doc_bp = Blueprint("documents", __name__, url_prefix="/api")
doc_bp.register_blueprint(cv_bp)
doc_bp.register_blueprint(jd_bp)
doc_bp.register_blueprint(match_bp)
doc_bp.register_blueprint(file_bp)
