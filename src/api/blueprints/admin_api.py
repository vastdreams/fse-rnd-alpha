from flask import Blueprint, jsonify

admin_api_bp = Blueprint("admin_api", __name__)


@admin_api_bp.get("/ping")
def ping():
    return jsonify({"status": "ok", "origin": "admin_api"}), 200
