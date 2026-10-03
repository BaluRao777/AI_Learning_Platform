from flask import Blueprint, request, jsonify
import re
from models.user_model import create_user, get_user_by_email
from utils.hash_helper import hash_password, check_password
from utils.jwt_helper import create_token

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    data = request.get_json() or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed = hash_password(password)
    user_id = create_user(email, hashed)

    if not user_id:
        return jsonify({"error": "User already exists"}), 400

    return jsonify({"message": "Signup successful"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    data = request.get_json() or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_user_by_email(email)

    if not user or not check_password(password, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user["id"])
    return jsonify({"token": token, "user": {"id": user["id"], "email": user["email"]}})