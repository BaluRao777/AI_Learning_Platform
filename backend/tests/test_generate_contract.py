import json
from types import SimpleNamespace

import pytest

from config import Config
from services import ai_service, image_jobs

GEMINI_PAYLOAD = {
    "subtopics": [
        {"title": f"Title {i}", "brief": f"Brief {i}.", "image_prompt": f"image prompt {i}"} for i in range(5)
    ],
    "explanation": "Sentence one. Sentence two. Sentence three. Sentence four.",
    "image_prompts": [f"image prompt {i}" for i in range(5)],
}
ORIGINAL_KEYS = {"topic", "level", "mode", "subtopics", "images", "explanation"}


@pytest.fixture()
def gemini(monkeypatch):
    calls = []

    def fake_generate_content(model, contents):
        calls.append(contents)
        return SimpleNamespace(text="```json\n" + json.dumps(GEMINI_PAYLOAD) + "\n```")

    monkeypatch.setattr(ai_service.client.models, "generate_content", fake_generate_content)
    return calls


def _post(client, headers, **body):
    return client.post("/generate", json=body, headers=headers)


def test_generate_contract_with_flags_off(client, auth_headers, gemini):
    resp = _post(client, auth_headers, topic="Earth", level="college", mode="exam")
    assert resp.status_code == 200
    data = resp.get_json()

    assert ORIGINAL_KEYS <= set(data)
    assert (data["topic"], data["level"], data["mode"]) == ("Earth", "college", "exam")
    assert data["explanation"] == GEMINI_PAYLOAD["explanation"]
    assert len(data["subtopics"]) == 5
    assert all(set(item) == {"title", "brief", "image_prompt"} for item in data["subtopics"])
    assert len(data["images"]) == 5
    assert all("/image-proxy?url=https%3A%2F%2Fimage.pollinations.ai%2F" in url for url in data["images"])

    analysis = data["analysis"]
    assert analysis["source"] == "rules"
    assert isinstance(analysis["analysis_ms"], int)
    assert analysis["plan"]["level"] == "college" and analysis["plan"]["mode"] == "exam"


def test_mode_and_level_reach_gemini(client, auth_headers, gemini):
    for level, mode in [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]:
        assert _post(client, auth_headers, topic="Earth", level=level, mode=mode).status_code == 200
    assert len(set(gemini)) == 4
    assert "mode: exam" in gemini[1] and "level: school" in gemini[1]


def test_history_saved_with_same_shape(client, auth_headers, gemini):
    _post(client, auth_headers, topic="Earth", level="school", mode="learn")
    history = client.get("/history", headers=auth_headers).get_json()
    assert len(history) == 1
    assert {"id", "topic", "level", "mode", "subtopics", "images", "explanation", "timestamp"} <= set(history[0])
    assert len(history[0]["images"]) == 5


def test_validation_and_auth_unchanged(client, auth_headers, gemini):
    assert client.post("/generate", json={"topic": "Earth"}).status_code == 401
    assert _post(client, auth_headers, topic="").status_code == 400
    assert _post(client, auth_headers, topic="Earth", level="phd").status_code == 400
    assert _post(client, auth_headers, topic="Earth", mode="cram").status_code == 400
    assert _post(client, auth_headers, topic="x" * (Config.MAX_TOPIC_LENGTH + 1)).status_code == 400


def test_gemini_failure_uses_existing_fallback(client, auth_headers, monkeypatch):
    def boom(model, contents):
        raise RuntimeError("gemini down")

    fallback = (GEMINI_PAYLOAD["subtopics"], "Fallback explanation.", GEMINI_PAYLOAD["image_prompts"])
    monkeypatch.setattr(ai_service.client.models, "generate_content", boom)
    monkeypatch.setattr(ai_service, "_fallback", lambda topic: fallback)
    data = _post(client, auth_headers, topic="Earth", level="school", mode="exam").get_json()
    assert data["explanation"] == "Fallback explanation."


def test_generate_content_old_signature_still_works(gemini):
    subtopics, explanation, image_prompts = ai_service.generate_content("Earth", "school")
    assert len(subtopics) == 5 and len(image_prompts) == 5 and explanation
    assert "mode: learn" in gemini[0]


def test_qwen_failure_never_breaks_generate(client, auth_headers, gemini, monkeypatch):
    from services import input_analyzer

    def boom(topic, level, mode):
        raise RuntimeError("CUDA exploded")

    monkeypatch.setattr(Config, "ANALYZER_ENABLED", True)
    monkeypatch.setattr(input_analyzer, "_run_qwen", boom)
    data = _post(client, auth_headers, topic="Earth", level="school", mode="exam").get_json()
    assert data["analysis"]["source"] == "rules"
    assert ORIGINAL_KEYS <= set(data)


def test_qwen_plan_is_validated_and_used(client, auth_headers, gemini, monkeypatch):
    from services import input_analyzer

    qwen_output = 'Here is the plan: {"subject_area": "geology", "depth": "nonsense", "tone": "calm"}'
    monkeypatch.setattr(Config, "ANALYZER_ENABLED", True)
    monkeypatch.setattr(input_analyzer, "_run_qwen", lambda topic, level, mode: qwen_output)
    analysis = _post(client, auth_headers, topic="Earth", level="school", mode="learn").get_json()["analysis"]
    assert analysis["source"] == "qwen"
    assert analysis["plan"]["subject_area"] == "geology"
    assert analysis["plan"]["depth"] == "basic"          # invalid value replaced by the rule default
    assert "depth" in analysis["fields_from_rules"]
    assert 'Subject area: "geology"' in gemini[0]


def test_analyze_endpoint(client, auth_headers):
    assert client.post("/analyze", json={"topic": "Earth"}).status_code == 401
    assert client.post("/analyze", json={"topic": ""}, headers=auth_headers).status_code == 400
    resp = client.post("/analyze", json={"topic": "Earth", "level": "college", "mode": "exam"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data) >= {"source", "plan", "analysis_ms"}
    assert data["plan"]["depth"] == "advanced"


def test_local_backend_returns_generated_urls_without_proxy(client, auth_headers, gemini, monkeypatch):
    enqueued = []
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "local")
    monkeypatch.setattr(Config, "SANA_NUM_IMAGES", 3)
    monkeypatch.setattr(Config, "SANA_LORA_PATH", "")
    monkeypatch.setattr(Config, "SANA_FUSED_TRANSFORMER_PATH", "")
    monkeypatch.setattr(image_jobs, "enqueue", lambda image_id, **kwargs: enqueued.append((image_id, kwargs)))

    data = _post(client, auth_headers, topic="Earth", level="college", mode="exam").get_json()
    images = data["images"]
    assert len(images) == 5 == len(data["subtopics"])
    assert len(enqueued) == 3
    for url, (image_id, _) in zip(images[:3], enqueued):
        assert url.endswith(f"/generated/{image_id}.png") and "image-proxy" not in url
    assert all(url.endswith("/generated/placeholder.svg") for url in images[3:])

    prompt = enqueued[0][1]["prompt"]
    assert prompt.startswith("college level, exam style clean textbook diagram, image prompt 0")
    assert "labeled" not in prompt                         # base model: no label words
    assert "edudiag" not in prompt                         # no LoRA configured -> no trigger word
    assert prompt.endswith("educational illustration, clean background, minimal text")
    assert enqueued[0][1]["seed"] == enqueued[0][1]["seed"]

    monkeypatch.setattr(Config, "SANA_LORA_PATH", "models_store/lora/pytorch_lora_weights.safetensors")
    enqueued.clear()
    _post(client, auth_headers, topic="Earth", level="college", mode="exam")
    assert enqueued[0][1]["prompt"].startswith("edudiag, college level, exam style clean labeled textbook diagram")


def test_local_backend_fallback_fills_with_pollinations(client, auth_headers, gemini, monkeypatch):
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "local")
    monkeypatch.setattr(Config, "SANA_NUM_IMAGES", 2)
    monkeypatch.setattr(Config, "IMAGE_FALLBACK_TO_POLLINATIONS", True)
    monkeypatch.setattr(image_jobs, "enqueue", lambda image_id, **kwargs: None)
    images = _post(client, auth_headers, topic="Earth", level="school", mode="learn").get_json()["images"]
    assert all("/generated/" in url for url in images[:2])
    assert all("/image-proxy?url=" in url for url in images[2:])
