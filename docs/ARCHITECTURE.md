# Architecture

## Request flow

```
React UI (unchanged look)
   │  POST /generate {topic, level, mode}
   ▼
Flask /generate                                   backend/routes/generate_routes.py
   │
   ├─(1) INPUT ANALYSIS LAYER                     backend/services/input_analyzer.py
   │       Qwen2.5-1.5B-Instruct, local, 4-bit (ANALYZER_ENABLED=true)
   │       input : topic + level + mode
   │       output: a validated "teaching plan" JSON
   │       fallback: deterministic rule-based plan      backend/services/plan_rules.py
   │
   ├─(2) GEMINI                                   backend/services/ai_service.py
   │       prompt built from the plan                   backend/services/prompt_builder.py
   │       output: subtopics, explanation, image_prompts (same JSON shape as before)
   │       fallback: the existing Wikipedia fallback (unchanged)
   │
   ├─(3) IMAGE SERVICE (IMAGE_BACKEND)            backend/services/image_service.py
   │       pollinations: original behaviour, unchanged  image_backends/pollinations_backend.py
   │       local : SANA 1.5 1.6B (+ education LoRA) on this machine's GPU   image_backends/sana_local.py
   │       remote: the same model served by the workstation over LAN       image_backends/sana_remote.py
   │       local/remote run as background jobs          backend/services/image_jobs.py
   │       /generate returns at once with URLs that become ready later
   │
   └─(4) save_history(...)                        unchanged schema; history.images stores the URLs
```

Response of `/generate`: the original keys (`topic, level, mode, subtopics, images, explanation`)
plus one new key, `analysis = {source, plan, analysis_ms, ...}`, which the frontend ignores.

## New endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /analyze` | JWT | Returns only the teaching plan (demo + tests). |
| `GET /generated/<id>.png` | none | The PNG; an SVG "Generating image…" placeholder (`X-Image-Status: pending`, `no-store`) while pending; the existing "Image generation unavailable" SVG if failed. |
| `GET /generated/<id>/status` | none | `{"status": "pending\|running\|done\|failed", "error": ...}` |
| `POST /generate_image` (workstation image server, port 7860) | `X-Token` | PNG bytes for a prompt. |

`<id>` is a uuid4 hex string validated with `^[0-9a-f]{32}$` before any file path is built.
`/generated/*` is exempt from the per-IP rate limiter so image polling never returns 429.

## GPU model management (`backend/services/model_manager.py`)

- One process-wide re-entrant GPU lock. Every local model is used inside `use_model(...)`,
  which holds the lock for load + inference and unloads any other model first.
  Qwen and SANA are therefore never on the GPU together.
- Models are loaded lazily: Qwen on the first analysed request, SANA on the first image job
  inside the worker thread. Nothing is loaded at import time, so the Werkzeug reloader
  (which imports the app twice in debug mode) never loads a model twice.
- One background worker thread, started on the first enqueue (never in the reloader parent).
- On CUDA out-of-memory SANA is unloaded and retried once with sequential CPU offload.

Consequence of the one-model rule: when requests arrive back to back, the analyzer waits
for the image currently being rendered, then SANA is unloaded for Qwen and reloaded
afterwards. This is the price of fitting in 4 GB of VRAM.

## Prompt consistency between training and inference

`backend/services/image_backends/sana_prompt.py` is the single definition of the caption format

    edudiag, {level words}, {look words}, {description}

It is imported by the app, by `training/dataset/build_metadata.py` (training captions) and by
the evaluation scripts. The trigger word is added only when fine-tuned weights are configured.
SANA's "complex human instruction" prompt prefix is disabled at inference because the
diffusers training script trains on plain captions.

## Why these models

| Component | Model | Why |
|---|---|---|
| Input analysis | `Qwen/Qwen2.5-1.5B-Instruct` (Apache-2.0) | Small enough for 4-bit on a 4 GB GPU (about 1.2 GB VRAM measured), follows a JSON schema with few-shot examples, has a chat template. |
| Text | Gemini (`GEMINI_MODEL`) | Already used by the project; now receives a plan-specific prompt. |
| Images | `Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers` (Apache-2.0 model card licence) | 1.6B transformer + 32x compression autoencoder: few-second generation and a small memory footprint; supported by diffusers `SanaPipeline` and by the official diffusers LoRA training example. |
| Captioning (dataset only) | `Qwen/Qwen2.5-VL-7B-Instruct` (Apache-2.0) | Runs on the workstation; produces the description and style tags. |
| Evaluation | `openai/clip-vit-large-patch14` | Standard text-image similarity. |

**FP8 decision:** FP8 checkpoints are not used. The laptop GPU (RTX 2050) has no FP8 hardware
support, so FP8 would give no speed-up there; training and deployment use bf16.

## Known design limits

- The job queue and job status are in memory. After a backend restart a finished image is
  still served from disk; an unfinished one is reported as failed.
- SANA cannot render legible text, so diagrams have no readable labels. The Gemini prompt
  asks for image prompts without text for this reason.
- Any unmatched URL returns HTTP 500 instead of 404 because of the app's original catch-all
  error handler (pre-existing behaviour, left unchanged).
