import pytest

from config import Config
from services import image_jobs
from services.image_service import parse_image_mix


def test_parse_image_mix():
    assert parse_image_mix("base:2,lora:2,pollinations:1", 5) == ["base", "base", "lora", "lora", "pollinations"]
    assert parse_image_mix("lora:1", 3) == ["lora", "base", "base"]          # missing slots -> base
    assert parse_image_mix("base:9", 5) == ["base"] * 5                       # extra slots cut
    assert parse_image_mix("magic:2,lora:x,pollinations:1", 2) == ["pollinations", "base"]  # bad parts ignored


@pytest.fixture()
def gemini(monkeypatch):
    import json
    from types import SimpleNamespace

    from services import ai_service

    payload = {
        "subtopics": [{"title": f"T{i}", "brief": "B.", "image_prompt": f"labeled prompt {i}"} for i in range(5)],
        "explanation": "One. Two. Three.",
        "image_prompts": [f"labeled prompt {i}" for i in range(5)],
    }
    monkeypatch.setattr(ai_service.client.models, "generate_content",
                        lambda model, contents: SimpleNamespace(text=json.dumps(payload)))


def test_mixed_mode_response(client, auth_headers, gemini, monkeypatch):
    enqueued = []
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "mixed")
    monkeypatch.setattr(Config, "IMAGE_MIX", "base:2,lora:2,pollinations:1")
    monkeypatch.setattr(image_jobs, "enqueue", lambda image_id, **kw: enqueued.append((image_id, kw)))

    data = client.post("/generate", json={"topic": "Earth", "level": "college", "mode": "exam"},
                       headers=auth_headers).get_json()

    assert data["image_sources"] == ["sana_base", "sana_base", "sana_lora", "sana_lora", "pollinations"]
    images = data["images"]
    assert all("/generated/" in u for u in images[:4])
    assert "/image-proxy?url=https%3A%2F%2Fimage.pollinations.ai%2F" in images[4]
    assert len(enqueued) == 4

    base_kw, lora_kw = enqueued[0][1], enqueued[2][1]
    assert base_kw["lora_path"] == "" and base_kw["backend"] == "local"
    assert lora_kw["lora_path"] == Config.SANA_MIX_LORA_PATH
    assert "edudiag" not in base_kw["prompt"] and "labeled" not in base_kw["prompt"]
    assert lora_kw["prompt"].startswith("edudiag, college level, exam style clean labeled textbook diagram")


def test_other_modes_report_sources(client, auth_headers, gemini, monkeypatch):
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "pollinations")
    data = client.post("/generate", json={"topic": "Earth"}, headers=auth_headers).get_json()
    assert data["image_sources"] == ["pollinations"] * 5

    monkeypatch.setattr(Config, "IMAGE_BACKEND", "local")
    monkeypatch.setattr(Config, "SANA_LORA_PATH", "")
    monkeypatch.setattr(Config, "SANA_NUM_IMAGES", 3)
    monkeypatch.setattr(image_jobs, "enqueue", lambda image_id, **kw: None)
    data = client.post("/generate", json={"topic": "Earth"}, headers=auth_headers).get_json()
    assert data["image_sources"] == ["sana_base"] * 3 + ["placeholder"] * 2


def test_worker_passes_per_job_lora(monkeypatch):
    from PIL import Image

    from services.image_backends import sana_local

    seen = []

    def fake_generate(*args, settings=None):
        seen.append(settings)
        return Image.new("RGB", (8, 8)), {}

    monkeypatch.setattr(sana_local, "generate", fake_generate)
    for image_id, lora in (("a" * 32, ""), ("b" * 32, "models_store/lora/x.safetensors"), ("c" * 32, None)):
        image_jobs.enqueue(image_id, prompt="p", negative_prompt="n", height=8, width=8, steps=1, guidance=1.0,
                           seed=1, lora_path=lora, backend="local")
    image_jobs._queue.join()
    assert seen[0].lora_path == ""
    assert seen[1].lora_path.endswith("models_store/lora/x.safetensors")
    assert seen[2] is None
