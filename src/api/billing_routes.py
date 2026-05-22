from __future__ import annotations

from flask import Blueprint

from src.api.http import response
from src.core.dependencies import require_auth
from src.services.billing_service import get_payment_info


billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


@billing_bp.get("/payment-info")
@require_auth
def payment_info():
    return response(get_payment_info())
