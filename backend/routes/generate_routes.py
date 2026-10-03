from flask import Blueprint, request, jsonify, Response
from urllib.parse import quote, unquote, urlparse
import time
import requests
from services.ai_service import generate_content
from services.image_service import generate_images_with_sources, is_pollinations_url
from services.input_analyzer import analyze_input
from middleware.auth_middleware import token_required
from models.history_model import save_history
from config import Config

generate_bp = Blueprint('generate', __name__)
REQUEST_HEADERS = {"User-Agent": "text-to-image-learning-app/1.0"}


def _normalize_explanation(topic, explanation):
    text = (explanation or "").strip()
    if "This is a safe fallback explanation." in text:
        return (
            f"{topic} is a foundational concept worth learning step by step. "
            "Start with the basic idea, then focus on the important parts and how each part works together. "
            "Once the core process is clear, connect it to real-world use cases so it becomes easier to remember. "
            "Finally, review common mistakes learners make so you can avoid confusion and build strong understanding."
        )
    return text


def _proxy_url(image_url):
    encoded = quote(image_url, safe="")
    return f"{request.host_url.rstrip('/')}/image-proxy?url={encoded}"


def _build_svg_placeholder(target):
    parsed = urlparse(target)
    path = parsed.path or ""
    label = "Image unavailable"
    if "/prompt/" in path:
        raw = path.split("/prompt/", 1)[1]
        decoded = unquote(raw)
        label = unquote(decoded)[:140]
    label = label.replace("&", "and").replace("<", "").replace(">", "")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="768" height="512">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#10204a"/><stop offset="100%" stop-color="#1e3a8a"/>
</linearGradient></defs>
<rect width="100%" height="100%" fill="url(#g)"/>
<text x="50%" y="46%" dominant-baseline="middle" text-anchor="middle" fill="#e2e8f0" font-size="24" font-family="Arial">Image generation unavailable</text>
<text x="50%" y="56%" dominant-baseline="middle" text-anchor="middle" fill="#bfdbfe" font-size="16" font-family="Arial">{label}</text>
</svg>"""
    return svg.encode("utf-8")


def _extract_prompt_from_target(target):
    try:
        parsed = urlparse(target)
        path = parsed.path or ""
        if "/prompt/" not in path:
            return ""
        raw = path.split("/prompt/", 1)[1]
        return unquote(unquote(raw)).strip()
    except Exception:
        return ""


def _fetch_wikimedia_image(prompt_text):
    prompt_text = (prompt_text or "").strip()
    parts = [p.strip() for p in prompt_text.split(",") if p.strip()]
    primary = " ".join(parts[:2]) if parts else prompt_text
    backup = parts[0] if parts else prompt_text

    def search_commons(raw_query):
        tokens = [t for t in raw_query.replace("-", " ").split() if t.isalpha()]
        query = " ".join(tokens[:6]).strip() or " ".join(raw_query.split()[:6]).strip()
        if not query:
            return None
        meta = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"{query} diagram filetype:bitmap",
                "gsrlimit": 5,
                "gsrnamespace": 6,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
            headers=REQUEST_HEADERS,
            timeout=8,
        )
        if not meta.ok:
            return None
        pages = (meta.json().get("query", {}).get("pages", {}) or {}).values()
        for page in pages:
            infos = page.get("imageinfo") or []
            if not infos or not infos[0].get("url"):
                continue
            candidate = infos[0]["url"]
            path = urlparse(candidate).path.lower()
            if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                img = requests.get(candidate, headers=REQUEST_HEADERS, timeout=10)
                if img.ok and img.content and img.headers.get("Content-Type", "").startswith("image/"):
                    return img.content, img.headers.get("Content-Type", "image/jpeg")
        return None

    try:
        return search_commons(primary) or search_commons(backup)
    except Exception:
        return None


@generate_bp.route("/generate", methods=["POST"])
@token_required
def generate(user_id):
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 415

        data = request.get_json() or {}
        topic = data.get("topic", "").strip()
        level = data.get("level", "school").strip().lower()
        mode = data.get("mode", "learn").strip().lower()

        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        if len(topic) > Config.MAX_TOPIC_LENGTH:
            return jsonify({"error": f"Topic must be <= {Config.MAX_TOPIC_LENGTH} chars"}), 400
        if level not in {"school", "college"}:
            return jsonify({"error": "Invalid level"}), 400
        if mode not in {"learn", "exam"}:
            return jsonify({"error": "Invalid mode"}), 400

        started = time.perf_counter()
        analysis = analyze_input(topic, level, mode)
        plan = analysis["plan"]

        content_started = time.perf_counter()
        subtopics, explanation, image_prompts = generate_content(topic, level, mode, plan)
        content_ms = int((time.perf_counter() - content_started) * 1000)
        explanation = _normalize_explanation(topic, explanation)

        raw_images, image_sources = generate_images_with_sources(image_prompts, mode, level=level, plan=plan)
        images = [_proxy_url(url) if is_pollinations_url(url) else url for url in raw_images]

        save_history(user_id, topic, level, mode, subtopics, explanation, images)
        print(
            f"GENERATE topic={topic!r} level={level} mode={mode} analyzer={analysis['source']} "
            f"analysis_ms={analysis['analysis_ms']} content_ms={content_ms} "
            f"image_backend={Config.IMAGE_BACKEND} total_ms={int((time.perf_counter() - started) * 1000)}"
        )
        return jsonify({
            "topic": topic,
            "level": level,
            "mode": mode,
            "subtopics": subtopics,
            "images": images,
            "explanation": explanation,
            "analysis": analysis,
            "image_sources": image_sources
        })

    except Exception as exc:
        print("GENERATE ERROR:", str(exc))
        return jsonify({"error": "Internal server error"}), 500


@generate_bp.route("/analyze", methods=["POST"])
@token_required
def analyze(user_id):
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    data = request.get_json() or {}
    topic = str(data.get("topic", "")).strip()
    level = str(data.get("level", "school")).strip().lower()
    mode = str(data.get("mode", "learn")).strip().lower()

    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    if len(topic) > Config.MAX_TOPIC_LENGTH:
        return jsonify({"error": f"Topic must be <= {Config.MAX_TOPIC_LENGTH} chars"}), 400
    if level not in {"school", "college"}:
        return jsonify({"error": "Invalid level"}), 400
    if mode not in {"learn", "exam"}:
        return jsonify({"error": "Invalid mode"}), 400

    return jsonify(analyze_input(topic, level, mode))


@generate_bp.route("/image-proxy", methods=["GET"])
def image_proxy():
    target = (request.args.get("url") or "").strip()
    if not target:
        return jsonify({"error": "Missing url"}), 400

    allowed_hosts = ("https://image.pollinations.ai/", "https://picsum.photos/")
    if not any(target.startswith(prefix) for prefix in allowed_hosts):
        return jsonify({"error": "URL not allowed"}), 400

    try:
        resp = requests.get(target, headers=REQUEST_HEADERS, timeout=Config.IMAGE_PROXY_TIMEOUT_SECONDS)
        if resp.ok and resp.content:
            return Response(
                resp.content,
                status=200,
                content_type=resp.headers.get("Content-Type", "image/jpeg"),
            )
    except Exception:
        pass

    prompt_text = _extract_prompt_from_target(target)
    wiki_img = _fetch_wikimedia_image(prompt_text)
    if wiki_img:
        content, content_type = wiki_img
        return Response(content, status=200, content_type=content_type)

    return Response(_build_svg_placeholder(target), status=200, content_type="image/svg+xml")