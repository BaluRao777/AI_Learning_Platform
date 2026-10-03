"""Background image jobs: one in-memory queue, one worker thread.

/generate enqueues jobs and returns at once; the worker renders each image
with the local SANA pipeline (or fetches it from the remote server) and
writes backend/{GENERATED_IMAGES_DIR}/{id}.png.

The worker is started lazily on the first enqueue. No model is loaded at
import time, and the Werkzeug reloader's parent process never serves
requests, so the worker and the models exist only once (in the serving
process). `should_start_worker()` additionally refuses to start in the
reloader parent.
"""
import os
import queue
import re
import threading
import time

from config import Config

ID_RE = re.compile(r"^[0-9a-f]{32}$")
STATUSES = ("pending", "running", "done", "failed")
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_jobs = {}
_jobs_lock = threading.Lock()
_queue = queue.Queue()
_worker = None
_worker_lock = threading.Lock()


def is_valid_id(image_id):
    return isinstance(image_id, str) and bool(ID_RE.match(image_id))


def images_dir():
    path = Config.GENERATED_IMAGES_DIR
    if not os.path.isabs(path):
        path = os.path.join(BACKEND_DIR, path)
    os.makedirs(path, exist_ok=True)
    return path


def image_path(image_id):
    if not is_valid_id(image_id):
        raise ValueError("invalid image id")
    return os.path.join(images_dir(), f"{image_id}.png")


def should_start_worker():
    """False only in the Werkzeug reloader's parent (watcher) process.

    app.run(debug=True) starts the app twice; only the child
    (WERKZEUG_RUN_MAIN=true) serves requests and may own the worker/models.
    """
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not Config.DEBUG:
        return True
    return os.environ.get("WERKZEUG_SERVER_FD") is None


def _ensure_worker():
    global _worker
    with _worker_lock:
        if _worker is not None and _worker.is_alive():
            return True
        if not should_start_worker():
            return False
        _worker = threading.Thread(target=_worker_loop, name="image-worker", daemon=True)
        _worker.start()
        return True


def enqueue(image_id, prompt, negative_prompt, height, width, steps, guidance, seed, fallback_url=None,
            lora_path=None, backend=None):
    """lora_path=None uses the configured model; "" forces the base model; a path forces that LoRA."""
    if not is_valid_id(image_id):
        raise ValueError("invalid image id")
    job = {
        "id": image_id,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "height": height,
        "width": width,
        "steps": steps,
        "guidance": guidance,
        "seed": seed,
        "backend": backend or Config.IMAGE_BACKEND,
        "lora_path": lora_path,
        "fallback_url": fallback_url,
        "status": "pending",
        "error": None,
        "created": time.time(),
    }
    with _jobs_lock:
        _jobs[image_id] = job
    _queue.put(image_id)
    _ensure_worker()
    return job


def get_job(image_id):
    with _jobs_lock:
        job = _jobs.get(image_id)
        return dict(job) if job else None


def get_status(image_id):
    """{"status", "error"}. Unknown id: done if the file exists, else failed (handles restarts)."""
    job = get_job(image_id)
    if job:
        return {"status": job["status"], "error": job["error"]}
    if is_valid_id(image_id) and os.path.isfile(image_path(image_id)):
        return {"status": "done", "error": None}
    return {"status": "failed", "error": "unknown image id"}


def queue_size():
    return _queue.qsize()


def _update(image_id, **fields):
    with _jobs_lock:
        if image_id in _jobs:
            _jobs[image_id].update(fields)


def _render(job):
    """Run one job with the configured backend and write the PNG atomically."""
    target = image_path(job["id"])
    tmp = f"{target}.tmp"
    args = (
        job["prompt"], job["negative_prompt"], job["height"], job["width"],
        job["steps"], job["guidance"], job["seed"],
    )
    info = {}
    if job["backend"] == "remote":
        from services.image_backends import sana_remote

        with open(tmp, "wb") as fh:
            fh.write(sana_remote.generate_png(*args))
    else:
        from dataclasses import replace

        from services.image_backends import sana_local

        settings = None
        if job.get("lora_path") is not None:
            settings = replace(
                sana_local.settings_from_config(),
                lora_path=sana_local.resolve_path(job["lora_path"]),
                fused_transformer_path="",
            )
        image, info = sana_local.generate(*args, settings=settings)
        image.save(tmp, format="PNG")
    os.replace(tmp, target)
    return info


def _worker_loop():
    while True:
        image_id = _queue.get()
        job = get_job(image_id)
        if not job:
            continue
        _update(image_id, status="running", started=time.time())
        started = time.perf_counter()
        try:
            info = _render(job)
            seconds = round(time.perf_counter() - started, 2)
            _update(image_id, status="done", seconds=seconds, info=info)
            print(f"IMAGE JOB done id={image_id} backend={job['backend']} total_s={seconds} info={info}")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:500]
            _update(image_id, status="failed", error=error)
            print(f"IMAGE JOB failed id={image_id} backend={job['backend']} error={error}")
        finally:
            _queue.task_done()
