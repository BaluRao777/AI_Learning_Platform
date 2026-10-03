"""Standalone SANA image server for the workstation (IMAGE_BACKEND=remote on the laptop).

Run from the backend folder:

    SANA_REMOTE_TOKEN=<shared secret> python image_server/sana_server.py

Optional environment (same names as the app): SANA_MODEL_ID, SANA_LORA_PATH,
SANA_LORA_SCALE, SANA_FUSED_TRANSFORMER_PATH, SANA_TRIGGER,
SANA_SERVER_HOST (default 0.0.0.0), SANA_SERVER_PORT (default 7860).

POST /generate_image {prompt, negative_prompt, height, width, steps, guidance, seed} -> PNG bytes
Requires header X-Token: <SANA_REMOTE_TOKEN>.

The pipeline runs in bf16 fully on the GPU (no offload, no 4-bit), so it
needs a large GPU. If fine-tuned weights are loaded, the server prepends the
trigger word itself; clients send prompts without it.
"""
import hmac
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, Response, jsonify, request  # noqa: E402

from config import Config  # noqa: E402
from services.image_backends import sana_local  # noqa: E402

MAX_SIDE = 1024
MAX_STEPS = 50
MAX_PROMPT_CHARS = 2000

app = Flask(__name__)


def server_settings():
    base = sana_local.settings_from_config()
    return sana_local.SanaSettings(
        model_id=base.model_id,
        lora_path=base.lora_path,
        lora_scale=base.lora_scale,
        fused_transformer_path=base.fused_transformer_path,
        text_encoder_4bit=False,
        offload="none",
    )


def _authorized():
    token = request.headers.get("X-Token", "")
    return bool(Config.SANA_REMOTE_TOKEN) and hmac.compare_digest(token, Config.SANA_REMOTE_TOKEN)


def _int_field(data, name, default, low, high):
    value = data.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not (low <= value <= high):
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return value


@app.route("/health", methods=["GET"])
def health():
    settings = server_settings()
    return jsonify({"status": "ok", "model": settings.model_id, "fine_tuned": settings.uses_finetune})


@app.route("/generate_image", methods=["POST"])
def generate_image():
    if not _authorized():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    try:
        prompt = str(data.get("prompt") or "").strip()
        if not prompt or len(prompt) > MAX_PROMPT_CHARS:
            raise ValueError("prompt is required (max 2000 chars)")
        height = _int_field(data, "height", 1024, 256, MAX_SIDE)
        width = _int_field(data, "width", 1024, 256, MAX_SIDE)
        steps = _int_field(data, "steps", 20, 1, MAX_STEPS)
        seed = _int_field(data, "seed", 0, 0, 2**32 - 1)
        guidance = float(data.get("guidance", 4.5))
        if not (0.0 <= guidance <= 20.0):
            raise ValueError("guidance must be in [0, 20]")
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    settings = server_settings()
    if settings.uses_finetune and Config.SANA_TRIGGER:
        prompt = f"{Config.SANA_TRIGGER}, {prompt}"
    try:
        image, info = sana_local.generate(
            prompt, str(data.get("negative_prompt") or ""), height, width, steps, guidance, seed,
            settings=settings,
        )
    except Exception as exc:
        print(f"SANA SERVER error: {type(exc).__name__}: {exc}")
        return jsonify({"error": f"{type(exc).__name__}: {exc}"[:300]}), 500

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    print(f"SANA SERVER generated {width}x{height} steps={steps} info={info}")
    resp = Response(buffer.getvalue(), status=200, content_type="image/png")
    resp.headers["X-Generation-Seconds"] = str(info["seconds"])
    return resp


if __name__ == "__main__":
    if not Config.SANA_REMOTE_TOKEN:
        sys.exit("Refusing to start: set SANA_REMOTE_TOKEN (shared secret) first.")
    app.run(
        host=os.getenv("SANA_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SANA_SERVER_PORT", "7860")),
        debug=False,
        threaded=True,
    )
