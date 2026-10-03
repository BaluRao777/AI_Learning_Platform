import hashlib
from urllib.parse import quote

from config import Config
from services import image_service


def original_generate_images(prompts, mode):
    """Verbatim copy of the pre-upgrade services/image_service.py."""
    images = []
    style_hint = (
        "textbook diagram style, educational, labeled elements, clean white background, no artistic scenery"
        if mode == "exam"
        else "educational infographic style, clear labels, classroom-friendly, no random nature scenery, no animals"
    )

    for prompt in prompts:
        concise_prompt = " ".join(str(prompt).split())[:180]
        safe_prompt = f"{concise_prompt}. {style_hint}. focus strictly on the described concept."
        prompt_hash = hashlib.sha256(safe_prompt.encode("utf-8")).hexdigest()[:12]
        encoded_prompt = quote(safe_prompt, safe="")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={prompt_hash}&width=640&height=420"
        images.append(url)

    return images


PROMPTS = [
    "Earth, Definition of Earth. clean definition infographic with labeled terms",
    "  layers   of the\nEarth  ",
    "x" * 400,
    "ünïcode & symbols / ? #",
    12345,
]


def test_pollinations_output_identical_to_original(monkeypatch):
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "pollinations")
    for mode in ("learn", "exam"):
        assert image_service.generate_images(PROMPTS, mode) == original_generate_images(PROMPTS, mode)
        # the new optional arguments must not change the output
        assert image_service.generate_images(
            PROMPTS, mode, level="college", plan={"image_style": {"type": "process flow"}}
        ) == original_generate_images(PROMPTS, mode)


def test_unknown_backend_value_behaves_like_pollinations(monkeypatch):
    monkeypatch.setattr(Config, "IMAGE_BACKEND", "something-else")
    assert image_service.generate_images(PROMPTS, "learn") == original_generate_images(PROMPTS, "learn")
