from flask import Blueprint, jsonify, request
from middleware.auth_middleware import token_required
from models.history_model import list_history

history_bp = Blueprint("history", __name__)

@history_bp.route("/history", methods=["GET"])
@token_required
def get_history(user_id):
    limit_raw = request.args.get("limit", "50")
    try:
        limit = min(max(int(limit_raw), 1), 100)
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400

    return jsonify(list_history(user_id, limit=limit))