import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)


def _model_ref(value):
    """A Hugging Face model id, or a local model folder (absolute, or relative to the project root)."""
    value = (value or "").strip()
    if value and not os.path.isabs(value):
        local = os.path.join(PROJECT_ROOT, value)
        if os.path.isdir(local):
            return local
    return value


def _strip_comment(value):
    # Allows "KEY=value   # comment" lines copied from .env.example.
    return value.split(" #", 1)[0].strip()


def _env_bool(name, default):
    raw = os.getenv(name)
    if raw is None or not _strip_comment(raw):
        return default
    return _strip_comment(raw).lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    try:
        return int(_strip_comment(os.getenv(name, "")))
    except ValueError:
        return default


def _env_float(name, default):
    try:
        return float(_strip_comment(os.getenv(name, "")))
    except ValueError:
        return default


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = ENV == "development"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))

    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    # Pollinations renders on demand; 12 s was often too short.
    IMAGE_PROXY_TIMEOUT_SECONDS = _env_int("IMAGE_PROXY_TIMEOUT_SECONDS", 30)
    MAX_TOPIC_LENGTH = int(os.getenv("MAX_TOPIC_LENGTH", "120"))
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # ---- Input Analysis Layer (Qwen) ----
    ANALYZER_ENABLED = _env_bool("ANALYZER_ENABLED", False)
    QWEN_MODEL_ID = _model_ref(os.getenv("QWEN_MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct"))
    QWEN_LOAD_IN_4BIT = _env_bool("QWEN_LOAD_IN_4BIT", True)
    QWEN_UNLOAD_AFTER_USE = _env_bool("QWEN_UNLOAD_AFTER_USE", True)
    QWEN_MAX_NEW_TOKENS = _env_int("QWEN_MAX_NEW_TOKENS", 512)
    QWEN_MAX_TIME_SECONDS = _env_int("QWEN_MAX_TIME_SECONDS", 60)

    # ---- Image backend ----
    IMAGE_BACKEND = (os.getenv("IMAGE_BACKEND", "pollinations") or "pollinations").strip().lower()
    SANA_MODEL_ID = _model_ref(os.getenv("SANA_MODEL_ID", "Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers"))
    SANA_LORA_PATH = (os.getenv("SANA_LORA_PATH", "") or "").strip()
    SANA_LORA_SCALE = _env_float("SANA_LORA_SCALE", 1.0)
    SANA_FUSED_TRANSFORMER_PATH = (os.getenv("SANA_FUSED_TRANSFORMER_PATH", "") or "").strip()
    SANA_TEXT_ENCODER_4BIT = _env_bool("SANA_TEXT_ENCODER_4BIT", True)
    SANA_OFFLOAD = (os.getenv("SANA_OFFLOAD", "model") or "model").strip().lower()
    SANA_HEIGHT = _env_int("SANA_HEIGHT", 512)
    SANA_WIDTH = _env_int("SANA_WIDTH", 512)
    SANA_STEPS = _env_int("SANA_STEPS", 20)
    SANA_GUIDANCE = _env_float("SANA_GUIDANCE", 4.5)
    SANA_NUM_IMAGES = _env_int("SANA_NUM_IMAGES", 5)
    SANA_TRIGGER = (os.getenv("SANA_TRIGGER", "edudiag") or "").strip()
    GENERATED_IMAGES_DIR = (os.getenv("GENERATED_IMAGES_DIR", "generated_images") or "generated_images").strip()

    # ---- Mixed comparison mode (IMAGE_BACKEND=mixed) ----
    # Ordered "source:count" list; sources: base (SANA base), lora (SANA + LoRA), pollinations.
    IMAGE_MIX = (os.getenv("IMAGE_MIX", "base:2,lora:1,pollinations:2") or "").split(" #", 1)[0].strip()
    SANA_MIX_LORA_PATH = (
        os.getenv("SANA_MIX_LORA_PATH", "models_store/lora/pytorch_lora_weights.safetensors") or ""
    ).split(" #", 1)[0].strip()

    # ---- Remote image server (workstation) ----
    SANA_REMOTE_URL = (os.getenv("SANA_REMOTE_URL", "") or "").strip()
    SANA_REMOTE_TOKEN = (os.getenv("SANA_REMOTE_TOKEN", "") or "").strip()

    # ---- Optional ----
    IMAGE_FALLBACK_TO_POLLINATIONS = _env_bool("IMAGE_FALLBACK_TO_POLLINATIONS", False)

    @classmethod
    def token_expiry(cls):
        return timedelta(hours=cls.JWT_EXPIRES_HOURS)
