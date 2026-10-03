"""Serves locally generated images.

GET /generated/<id>.png      the PNG, or an SVG placeholder while pending / after failure
GET /generated/<id>/status   {"status": "pending|running|done|failed", "error": null|"..."}

No auth: the <img> tag cannot send the JWT, and ids are unguessable uuid4
hex strings. Ids are validated with a strict regex to prevent path traversal.
"""
import os

from flask import Blueprint, Response, jsonify, redirect, send_file

from routes.generate_routes import _build_svg_placeholder, _proxy_url
from services import image_jobs
from services.image_service import PLACEHOLDER_NAME

generated_bp = Blueprint("generated", __name__)


def _pending_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="768" height="512">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#10204a"/><stop offset="100%" stop-color="#1e3a8a"/>
</linearGradient></defs>
<rect width="100%" height="100%" fill="url(#g)"/>
<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#e2e8f0" font-size="24" font-family="Arial">Generating image…</text>
</svg>"""
    return svg.encode("utf-8")


def _svg_response(body, status_header):
    resp = Response(body, status=200, content_type="image/svg+xml")
    resp.headers["X-Image-Status"] = status_header
    resp.headers["Cache-Control"] = "no-store"
    return resp


@generated_bp.route("/generated/<name>", methods=["GET"])
def generated_image(name):
    if name == PLACEHOLDER_NAME:
        return _svg_response(_build_svg_placeholder(""), "failed")
    if not name.endswith(".png") or not image_jobs.is_valid_id(name[:-4]):
        return jsonify({"error": "Not found"}), 404
    image_id = name[:-4]

    path = image_jobs.image_path(image_id)
    if os.path.isfile(path):
        resp = send_file(path, mimetype="image/png")
        resp.headers["Cache-Control"] = "public, max-age=86400"
        resp.headers["X-Image-Status"] = "done"
        return resp

    job = image_jobs.get_job(image_id)
    if job and job["status"] in {"pending", "running"}:
        return _svg_response(_pending_svg(), "pending")
    if job and job.get("fallback_url"):
        resp = redirect(_proxy_url(job["fallback_url"]), code=302)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    return _svg_response(_build_svg_placeholder(""), "failed")


@generated_bp.route("/generated/<image_id>/status", methods=["GET"])
def generated_status(image_id):
    if not image_jobs.is_valid_id(image_id):
        return jsonify({"error": "Not found"}), 404
    resp = jsonify(image_jobs.get_status(image_id))
    resp.headers["Cache-Control"] = "no-store"
    return resp
