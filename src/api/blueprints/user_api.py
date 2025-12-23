from flask import Blueprint, jsonify

user_api_bp = Blueprint("user_api", __name__)


@user_api_bp.get("/ping")
def ping():
    return jsonify({"status": "ok", "origin": "user_api"}), 200
