from collections import defaultdict, deque
import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.generate_routes import generate_bp
from routes.history_routes import history_bp
from routes.generated_routes import generated_bp
from config import Config

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": Config.CORS_ORIGINS}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.register_blueprint(auth_bp)
app.register_blueprint(generate_bp)
app.register_blueprint(history_bp)
app.register_blueprint(generated_bp)

_request_bucket = defaultdict(deque)


@app.before_request
def rate_limit():
    # Image polling for locally generated images must never trigger 429.
    if request.path.startswith("/generated/"):
        return None
    ip = request.remote_addr or "unknown"
    now = time.time()
    window_start = now - 60
    queue = _request_bucket[ip]
    while queue and queue[0] < window_start:
        queue.popleft()
    if len(queue) >= Config.RATE_LIMIT_PER_MINUTE:
        return jsonify({"error": "Too many requests"}), 429
    queue.append(now)


@app.errorhandler(Exception)
def unhandled_exception(error):
    print("UNHANDLED ERROR:", str(error))
    return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def home():
    return {"message": "Backend is running"}

def log_startup_config():
    """One line with the effective feature settings (never the API key)."""
    mix = (
        f"image_mix={Config.IMAGE_MIX} mix_lora={Config.SANA_MIX_LORA_PATH} "
        if Config.IMAGE_BACKEND == "mixed" else ""
    )
    print(
        "CONFIG "
        f"analyzer={'on' if Config.ANALYZER_ENABLED else 'off'} "
        f"qwen={Config.QWEN_MODEL_ID} qwen_4bit={Config.QWEN_LOAD_IN_4BIT} "
        f"qwen_unload_after_use={Config.QWEN_UNLOAD_AFTER_USE} "
        f"image_backend={Config.IMAGE_BACKEND} "
        f"{mix}"
        f"lora={Config.SANA_LORA_PATH or 'none'} "
        f"fused_transformer={Config.SANA_FUSED_TRANSFORMER_PATH or 'none'} "
        f"text_encoder_4bit={Config.SANA_TEXT_ENCODER_4BIT} offload={Config.SANA_OFFLOAD} "
        f"size={Config.SANA_WIDTH}x{Config.SANA_HEIGHT} steps={Config.SANA_STEPS} "
        f"num_images={Config.SANA_NUM_IMAGES} "
        f"pollinations_fallback={Config.IMAGE_FALLBACK_TO_POLLINATIONS} "
        f"gemini_model={Config.GEMINI_MODEL} gemini_key_set={'yes' if Config.GEMINI_API_KEY else 'no'}",
        flush=True,
    )


if __name__ == "__main__":
    # With debug on, the Werkzeug reloader runs this file twice; log only in the serving process.
    if not Config.DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        log_startup_config()
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, threaded=True)