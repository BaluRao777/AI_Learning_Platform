"""Test setup: runs without a GPU, without Gemini and without touching the real database."""
import os
import sqlite3
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Must be set before config.py is imported (load_dotenv never overrides existing variables).
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-0123456789"
os.environ["FLASK_ENV"] = "production"
os.environ["ANALYZER_ENABLED"] = "false"
os.environ["IMAGE_BACKEND"] = "pollinations"
os.environ["RATE_LIMIT_PER_MINUTE"] = "30"

import pytest  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import database.db as db
    from config import Config

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    with open(os.path.join(BACKEND_DIR, "database", "schema.sql"), encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.execute("INSERT INTO users (email, password) VALUES ('tester@example.com', 'x')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    monkeypatch.setattr(Config, "ANALYZER_ENABLED", False)
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "pollinations")
    monkeypatch.setattr(Config, "GENERATED_IMAGES_DIR", str(tmp_path / "generated_images"))

    import app as app_module

    app_module._request_bucket.clear()
    app_module.app.config["TESTING"] = True
    return app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers():
    from utils.jwt_helper import create_token

    return {"Authorization": f"Bearer {create_token(1)}"}
