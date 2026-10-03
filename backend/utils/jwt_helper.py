import datetime

import jwt

from config import Config


def create_token(user_id):
    if not Config.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + Config.token_expiry(),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token):
    if not Config.JWT_SECRET:
        return None
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None