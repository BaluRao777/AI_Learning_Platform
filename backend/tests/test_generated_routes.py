import os

import pytest

from config import Config
from services import image_jobs

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
GOOD_ID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize("bad", [
    "../../etc/passwd",
    "..%2F..%2Fapp.py",
    "0123456789ABCDEF0123456789ABCDEF",      # upper case
    "0123456789abcdef0123456789abcde",       # 31 chars
    "0123456789abcdef0123456789abcdef0",     # 33 chars
    "0123456789abcdef0123456789abcdeg",      # not hex
    "",
])
def test_id_regex_blocks_traversal(bad):
    assert not image_jobs.is_valid_id(bad)
    with pytest.raises(ValueError):
        image_jobs.image_path(bad)


@pytest.mark.parametrize("path", [
    "/generated/..%2F..%2Fapp.py",
    "/generated/..%2F..%2Fdatabase%2Fapp.db.png",
    "/generated/../app.py",
])
def test_traversal_urls_never_serve_a_file(client, path):
    # These decode to paths with slashes, so no route matches. The app's existing
    # catch-all error handler reports unmatched URLs as 500 instead of 404.
    resp = client.get(path)
    assert resp.status_code in (404, 500)
    assert resp.is_json and "error" in resp.get_json()


@pytest.mark.parametrize("path", [
    "/generated/0123456789abcdef0123456789abcdef.jpg",
    "/generated/0123456789ABCDEF0123456789ABCDEF.png",
    "/generated/short.png",
    "/generated/not-an-id/status",
])
def test_routes_reject_invalid_ids(client, path):
    assert client.get(path).status_code == 404


def _add_job(monkeypatch, status, **extra):
    job = {"id": GOOD_ID, "status": status, "error": None, "fallback_url": None}
    job.update(extra)
    monkeypatch.setitem(image_jobs._jobs, GOOD_ID, job)


def test_pending_returns_svg_and_header(client, monkeypatch):
    for status in ("pending", "running"):
        _add_job(monkeypatch, status)
        resp = client.get(f"/generated/{GOOD_ID}.png")
        assert resp.status_code == 200
        assert resp.content_type.startswith("image/svg+xml")
        assert resp.headers["X-Image-Status"] == "pending"
        assert resp.headers["Cache-Control"] == "no-store"
        assert "Generating image" in resp.get_data(as_text=True)
        assert client.get(f"/generated/{GOOD_ID}/status").get_json() == {"status": status, "error": None}


def test_done_returns_png(client, monkeypatch):
    _add_job(monkeypatch, "done")
    with open(image_jobs.image_path(GOOD_ID), "wb") as fh:
        fh.write(PNG_BYTES)
    resp = client.get(f"/generated/{GOOD_ID}.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    assert resp.get_data() == PNG_BYTES
    assert "max-age=86400" in resp.headers["Cache-Control"]


def test_failed_returns_unavailable_svg(client, monkeypatch):
    _add_job(monkeypatch, "failed", error="RuntimeError: boom")
    resp = client.get(f"/generated/{GOOD_ID}.png")
    assert resp.content_type.startswith("image/svg+xml")
    assert "Image generation unavailable" in resp.get_data(as_text=True)
    assert resp.headers["X-Image-Status"] == "failed"
    assert client.get(f"/generated/{GOOD_ID}/status").get_json() == {"status": "failed", "error": "RuntimeError: boom"}


def test_failed_with_fallback_redirects_to_image_proxy(client, monkeypatch):
    _add_job(monkeypatch, "failed", error="x", fallback_url="https://image.pollinations.ai/prompt/abc?seed=1")
    resp = client.get(f"/generated/{GOOD_ID}.png")
    assert resp.status_code == 302
    assert "/image-proxy?url=https%3A%2F%2Fimage.pollinations.ai%2F" in resp.headers["Location"]


def test_unknown_id_after_restart(client):
    # no job in memory: done if the file exists, failed otherwise
    assert client.get(f"/generated/{GOOD_ID}/status").get_json()["status"] == "failed"
    assert "Image generation unavailable" in client.get(f"/generated/{GOOD_ID}.png").get_data(as_text=True)
    with open(image_jobs.image_path(GOOD_ID), "wb") as fh:
        fh.write(PNG_BYTES)
    assert client.get(f"/generated/{GOOD_ID}/status").get_json() == {"status": "done", "error": None}
    assert client.get(f"/generated/{GOOD_ID}.png").content_type == "image/png"


def test_placeholder_route(client):
    resp = client.get("/generated/placeholder.svg")
    assert resp.status_code == 200 and resp.content_type.startswith("image/svg+xml")


def test_rate_limiter_does_not_block_generated_but_still_limits_others(client):
    for _ in range(Config.RATE_LIMIT_PER_MINUTE * 3):
        assert client.get(f"/generated/{GOOD_ID}/status").status_code == 200
        assert client.get(f"/generated/{GOOD_ID}.png").status_code == 200
    statuses = [client.get("/").status_code for _ in range(Config.RATE_LIMIT_PER_MINUTE + 1)]
    assert statuses[:-1] == [200] * Config.RATE_LIMIT_PER_MINUTE
    assert statuses[-1] == 429


def test_worker_renders_job_to_file(monkeypatch):
    from PIL import Image

    from services.image_backends import sana_local

    def fake_generate(prompt, negative_prompt, height, width, steps, guidance, seed, settings=None):
        return Image.new("RGB", (width, height), "white"), {"seconds": 0.0}

    monkeypatch.setattr(Config, "IMAGE_BACKEND", "local")
    monkeypatch.setattr(sana_local, "generate", fake_generate)
    image_id = "f" * 32
    image_jobs.enqueue(image_id, prompt="p", negative_prompt="n", height=64, width=64, steps=1, guidance=1.0, seed=1)
    image_jobs._queue.join()
    assert image_jobs.get_status(image_id) == {"status": "done", "error": None}
    assert os.path.isfile(image_jobs.image_path(image_id))

    def failing_generate(*args, **kwargs):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(sana_local, "generate", failing_generate)
    bad_id = "e" * 32
    image_jobs.enqueue(bad_id, prompt="p", negative_prompt="n", height=64, width=64, steps=1, guidance=1.0, seed=1)
    image_jobs._queue.join()
    status = image_jobs.get_status(bad_id)
    assert status["status"] == "failed" and "out of memory" in status["error"]


def test_image_proxy_uses_configured_timeout(client, monkeypatch):
    from types import SimpleNamespace

    from routes import generate_routes

    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["timeout"] = timeout
        return SimpleNamespace(ok=True, content=b"jpeg-bytes", headers={"Content-Type": "image/jpeg"})

    monkeypatch.setattr(Config, "IMAGE_PROXY_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(generate_routes.requests, "get", fake_get)
    resp = client.get("/image-proxy?url=https%3A%2F%2Fimage.pollinations.ai%2Fprompt%2Fleaf")
    assert resp.status_code == 200 and resp.get_data() == b"jpeg-bytes"
    assert seen["timeout"] == 30
