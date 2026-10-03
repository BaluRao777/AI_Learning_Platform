from functools import wraps
from flask import request, jsonify
from utils.jwt_helper import decode_token


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return jsonify({"error": "Token missing"}), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Invalid authorization header"}), 401

        token = parts[1]
        data = decode_token(token)

        if not data:
            return jsonify({"error": "Invalid token"}), 401

        return f(data["user_id"], *args, **kwargs)

    return decorated