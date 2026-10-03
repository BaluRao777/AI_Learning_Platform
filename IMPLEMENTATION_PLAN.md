# IMPLEMENTATION PLAN — text_to_image Major Project Upgrade

> **For Claude Code.** Read this entire file before writing any code.
> This file is the single source of truth for the upgrade. Execute it phase by phase.

---

## 0. HOW THE PROJECT OWNER USES THIS FILE

1. Put this file in the project root: `text_to_image/IMPLEMENTATION_PLAN.md`.
2. Open Claude Code in the project root and say:
   `Read IMPLEMENTATION_PLAN.md completely and execute the phases that belong to this machine.`
3. Run Claude Code on the **laptop** for Phases 0, 1, 2, 6.
   Run Claude Code on the **workstation** for Phases 3, 4, 5.
   (Section 4 explains how to detect which machine you are on.)

---

## 1. GROUND RULES (NON-NEGOTIABLE)

1. **Inspect before editing.** Read every file you modify. Do not assume function names, paths or response shapes; verify them in the code.
2. **Do not break existing features.** Login, signup, JWT auth, `/generate`, `/history`, `/image-proxy`, rate limiting, the SQLite schema, the Wikipedia fallback, and the whole React UI (landing video, TubesCursor, pages) must keep working exactly as before.
3. **Backward compatibility via config.** Every new feature is controlled by `.env` flags. With the new flags turned off, the app must behave exactly like the original.
4. **No UI redesign.** Frontend changes are limited to the two small, non-visual changes listed in Phase 2 (request timeout and image polling).
5. **Do not change the database schema.** Do not modify `database/schema.sql` or existing columns. `history.images` already stores a JSON list of URLs; keep using it.
6. **Never print, log, commit or copy the contents of `backend/.env`.** It contains a real Gemini API key. Only edit `.env.example` and tell the owner which lines to add to `.env`.
7. **No fabrication.** Never claim something works, was trained, or is faster unless you actually ran it and saw the result. Report measured numbers only. If something fails, report the exact error and the blocker.
8. **Verify external facts at execution time.** Model IDs, script names, CLI flags and dataset licenses must be checked against the installed library versions / Hugging Face pages before use. If a name in this file is wrong, find the correct one and note the correction in the final report.
9. **Small, testable steps.** After each phase, run the app and the tests in Section 11. Commit (or back up) before starting the next phase.
10. **Ask the owner only if truly blocked** (missing credentials, hardware failure, a license decision). Otherwise decide sensibly and document the decision.

---

## 2. CURRENT PROJECT — VERIFIED FACTS

### 2.1 What the app does
A student logs in, enters a **topic**, picks a **level** (`school` | `college`) and a **mode** (`learn` | `exam`). The backend returns an explanation, 5 subtopics and 5 image URLs. Results are saved per user in history.

### 2.2 Stack
- **Frontend:** React (create-react-app, `npm start`), React Router, Axios, Framer Motion, Three.js / R3F / Drei, GSAP, Bootstrap, Lucide.
- **Backend:** Flask, Flask-CORS, SQLite, PyJWT, bcrypt, python-dotenv, `google-genai`, requests.
- **Text AI:** Gemini (`Config.GEMINI_MODEL`, default `gemini-2.5-flash-lite`), with a Wikipedia fallback in `services/ai_service.py`.
- **Images:** Pollinations.ai URLs built in `services/image_service.py`, fetched via `/image-proxy` in `routes/generate_routes.py`, with Wikimedia Commons and SVG placeholder fallbacks.

### 2.3 Key files
```
backend/app.py                     Flask app, blueprints, per-IP rate limit (RATE_LIMIT_PER_MINUTE, default 30)
backend/config.py                  Config class reading .env
backend/routes/generate_routes.py  POST /generate, GET /image-proxy
backend/services/ai_service.py     generate_content(topic, level) -> (subtopics, explanation, image_prompts)
backend/services/image_service.py  generate_images(prompts, mode) -> list of pollinations URLs
backend/models/history_model.py    save_history(...), list_history(...), get_existing(...) (unused)
backend/database/schema.sql        users, history tables
frontend/src/services/api.js       axios instance, timeout: 15000 ms, generateContent() -> POST /generate
frontend/src/pages/Home.js         calls generateContent({topic, level, mode}) then navigates to /result
frontend/src/components/ImageCard.js  <img src=...> with an onError SVG fallback
```

### 2.4 `/generate` response contract (must stay the same)
```json
{
  "topic": "string",
  "level": "school|college",
  "mode": "learn|exam",
  "subtopics": [ { "title": "...", "brief": "...", "image_prompt": "..." } ],
  "images": ["url", "url", "url", "url", "url"],
  "explanation": "string"
}
```
You may **add** new keys (e.g. `"analysis"`), but never remove or rename existing ones.

### 2.5 Root cause of the "same answer for every mode" problem
In `generate_routes.py` the call is `generate_content(topic, level)`. **`mode` is never sent to Gemini.** It is only used for the image style string. `level` is passed only as a one-line audience hint. Result: "Earth / school / exam" and "Earth / college / learn" give nearly identical text. Phase 1 fixes this.

### 2.6 Other facts that affect the design
- `backend/requirements.txt` in the repo is **empty (0 bytes)**. A working `requirements.txt` may exist at the project root on the laptop; check. Do not delete either. New AI dependencies go into a new file `backend/requirements-ai.txt`.
- Backend `__pycache__` shows **Python 3.13** on the laptop.
- `app.run(... debug=Config.DEBUG ...)` in development uses the **Werkzeug reloader**, which starts the app **twice**. Loading GPU models at import time would load them twice. Phase 2 handles this.
- The rate limiter counts **every** request per IP, 30 per minute. Image polling would hit it. Phase 2 handles this.
- The axios timeout is 15 s. Local AI will take longer. Phase 2 handles this.

---

## 3. TARGET ARCHITECTURE

```
React UI (unchanged look)
   │  POST /generate {topic, level, mode}
   ▼
Flask /generate
   │
   ├─(1) INPUT ANALYSIS LAYER  — Qwen2.5-1.5B-Instruct, local, 4-bit
   │       input: topic + level + mode
   │       output: a structured "teaching plan" JSON
   │       fallback: deterministic rule-based plan (if Qwen disabled/fails)
   │
   ├─(2) GEMINI  — receives a prompt BUILT FROM THE PLAN
   │       output: subtopics, explanation, image_prompts (same JSON shape as today)
   │       fallback: existing Wikipedia fallback
   │
   ├─(3) IMAGE SERVICE  (IMAGE_BACKEND = pollinations | local | remote)
   │       pollinations: original behaviour, unchanged
   │       local:  SANA 1.5 1.6B + education LoRA on this machine's GPU
   │       remote: same model served by the workstation over LAN
   │       local/remote run as a background job; /generate returns at once
   │       with image URLs that become ready later
   │
   └─(4) save_history(...)  — unchanged schema
```

**Why this is a real "model" contribution for the review:**
- A local LLM (Qwen) analyses each request and controls what Gemini produces.
- A local text-to-image model (SANA 1.5) is **fine-tuned with LoRA** on an educational-diagram dataset built for this project, and replaces the third-party image API.

---

## 4. MACHINES, ENVIRONMENTS AND HARDWARE CONSTRAINTS

### 4.1 Detect the machine first
Run `nvidia-smi` and check the OS.
- **Workstation:** Ubuntu 24.04, NVIDIA RTX 6000 Ada (48 GB VRAM), 64 GB RAM, Xeon Silver 4509Y. → Phases 3, 4, 5 (and it may run 1, 2 for testing).
- **Laptop:** Windows, NVIDIA RTX 2050 (**4 GB VRAM**), **8 GB system RAM**, conda env `text_to_image`, VS Code + PowerShell. → Phases 0, 1, 2, 6.

### 4.2 Laptop rules (8 GB RAM, 4 GB VRAM) — design every local component for this
- **Only one heavy model on the GPU at a time.** Implement a process-wide GPU lock and a model manager. Qwen and SANA must never be resident on the GPU together.
- **Qwen2.5-1.5B-Instruct in 4-bit** (bitsandbytes NF4). Unload it after use when `QWEN_UNLOAD_AFTER_USE=true` (default true on laptop).
- **SANA text encoder (Gemma-2-2B) in 4-bit.** In bf16 it would not fit in 8 GB RAM.
- **SANA transformer in bf16** with `enable_model_cpu_offload()`; fall back to `enable_sequential_cpu_offload()` if out of memory. Enable VAE tiling/slicing.
- **Default image size 512×512**, about 20 steps. 1024 is optional via `.env`.
- **FP8:** the RTX 2050 (Ampere) has no FP8 hardware, so FP8 gives no speed-up there. Do **not** use an FP8 checkpoint as the training base. Use bf16 for training and deployment. Mention this decision in the report.
- After the first download, run with `HF_HUB_OFFLINE=1` so it is truly local.
- Tell the owner (do not do it yourself): increase the Windows page file to about 16 GB, and close browser tabs before a demo.

### 4.3 Python environments
- **Laptop:** try to use the existing conda env `text_to_image` (Python 3.13). Verify that `torch` (CUDA build), `bitsandbytes`, `diffusers`, `transformers`, `accelerate`, `peft` install and import on Windows with Python 3.13 **and** that `torch.cuda.is_available()` is `True`. If any of these fail on 3.13, create a new env `text_to_image_ai` with Python 3.11, install both the original backend requirements and `requirements-ai.txt` into it, and update the run instructions. Record which path was taken.
- **Workstation:** create conda env `sana_train` with Python 3.11. Install a CUDA build of PyTorch that matches the installed driver, plus `diffusers` (recent version that includes SANA LoRA training), `transformers`, `accelerate`, `peft`, `bitsandbytes`, `datasets`, `pillow`, `tensorboard`, `open_clip_torch` or `transformers` CLIP.

### 4.4 Syncing code between machines
The owner will copy the project folder (or use git) between machines. Never copy `node_modules/`, `backend/generated_images/`, model weights, `.env`, or the dataset. Keep training code under `training/` so it is portable.

---

## 5. NEW CONFIGURATION (`.env.example` additions)

Add these to `backend/.env.example` with comments, and add matching fields to `Config` in `config.py` (with safe defaults so the app starts even if `.env` lacks them):

```ini
# ---- Input Analysis Layer (Qwen) ----
ANALYZER_ENABLED=true                 # false -> rule-based plan only
QWEN_MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct
QWEN_LOAD_IN_4BIT=true
QWEN_UNLOAD_AFTER_USE=true            # true on laptop, false on workstation
QWEN_MAX_NEW_TOKENS=512

# ---- Image backend ----
IMAGE_BACKEND=pollinations            # pollinations | local | remote
SANA_MODEL_ID=Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers
SANA_LORA_PATH=                       # e.g. models_store/lora/sana_edu_lora.safetensors ; empty = base model
SANA_LORA_SCALE=1.0
SANA_FUSED_TRANSFORMER_PATH=          # optional: path to LoRA-fused transformer (Phase 6)
SANA_TEXT_ENCODER_4BIT=true
SANA_OFFLOAD=model                    # none | model | sequential
SANA_HEIGHT=512
SANA_WIDTH=512
SANA_STEPS=20
SANA_GUIDANCE=4.5
SANA_NUM_IMAGES=5
SANA_TRIGGER=edudiag                  # LoRA trigger word (must match training captions)
GENERATED_IMAGES_DIR=generated_images

# ---- Remote image server (workstation) ----
SANA_REMOTE_URL=                      # e.g. http://192.168.1.50:7860
SANA_REMOTE_TOKEN=                    # shared secret

# ---- Optional ----
IMAGE_FALLBACK_TO_POLLINATIONS=false  # if local/remote fails, fall back to the old behaviour
```

Do not edit the owner's real `.env`. In the final report, list the lines they need to add.

---

## PHASE 0 — INSPECT, BACK UP, BASELINE (laptop)

1. Read all files listed in Section 2.3 plus `auth_middleware.py`, `history_routes.py`, `Result.js`, `History.js`, `HistoryList.js`, `InputForm.js`.
2. Confirm every fact in Section 2. If anything differs, note it and adapt.
3. Create a backup branch or a zip of `backend/` and `frontend/src/`.
4. Start the backend (`python backend/app.py` from the project root, in the conda env) and the frontend (`npm start` in `frontend/`). Generate "Photosynthesis / school / learn" and "Photosynthesis / college / exam". Save both JSON responses to `docs/baseline/` as evidence for the "before" comparison.
5. Write `backend/requirements-ai.txt` (do not touch the original requirements files).

---

## PHASE 1 — INPUT ANALYSIS LAYER (Qwen → Gemini)

### 1.1 New files
```
backend/services/model_manager.py     GPU lock + lazy load/unload helpers (shared with Phase 2)
backend/services/input_analyzer.py    Qwen analysis -> teaching plan
backend/services/plan_rules.py        deterministic rule-based plan (fallback + defaults)
backend/services/prompt_builder.py    builds the Gemini prompt from the plan
```
(`backend/utils/prompt_builder.py` exists but is empty. Leave it alone; put the new builder in `services/`.)

### 1.2 Teaching plan schema (output of the analyzer)
```json
{
  "topic": "Earth",
  "subject_area": "geography / earth science",
  "level": "school",
  "mode": "exam",
  "depth": "basic | intermediate | advanced",
  "tone": "short phrase",
  "explanation_style": "short phrase",
  "explanation_length_sentences": 6,
  "must_include": ["..."],
  "avoid": ["..."],
  "subtopic_focus": ["5 short focus areas"],
  "exam_focus": ["definitions", "key terms", "likely questions"],
  "image_style": {
    "type": "labeled textbook diagram | colourful infographic | process flow | cross-section",
    "complexity": "simple | detailed",
    "notes": "short phrase"
  }
}
```
Validate it with strict code (types, allowed values, list lengths). Any invalid or missing field is filled from the rule-based plan.

### 1.3 Rule-based plan (must produce clearly different plans for the 4 combinations)
| level / mode | depth | explanation style | images |
|---|---|---|---|
| school / learn | basic | simple words, analogies, everyday examples, curiosity | colourful infographic, simple |
| school / exam | basic | crisp definitions, key points, 1–2 likely exam questions with short answers | clean labeled textbook diagram, simple |
| college / learn | advanced | mechanisms, cause-effect, real-world applications, technical terms explained | detailed process/flow diagram |
| college / exam | advanced | precise technical definitions, formulas/laws if relevant, comparisons, likely university-exam questions | detailed labeled textbook diagram |

### 1.4 Qwen behaviour
- Load lazily on first use through `model_manager` (4-bit if `QWEN_LOAD_IN_4BIT`). Use the chat template.
- System prompt: "You are an educational input analyst. Given a topic, a learner level and a learning mode, output ONLY a JSON teaching plan matching this schema …" Include the schema and the rules from 1.3 as guidance, and 2 short few-shot examples (different combinations).
- Greedy decoding (`do_sample=False`), `max_new_tokens=QWEN_MAX_NEW_TOKENS`.
- Extract the first JSON object, validate, merge with the rule-based plan.
- Any exception, timeout or invalid JSON → log a warning and use the rule-based plan. `/generate` must never fail because of Qwen.
- Unload after use if `QWEN_UNLOAD_AFTER_USE=true` (delete model, `gc.collect()`, `torch.cuda.empty_cache()`).
- Record `analyzer_source` = `"qwen"` or `"rules"`, and the analysis time in ms.

### 1.5 Gemini prompt built from the plan
`prompt_builder.build_gemini_prompt(plan)` returns a prompt that:
- states the audience, purpose, depth, tone, style and length from the plan;
- lists `must_include`, `avoid`, `subtopic_focus`, and `exam_focus` (exam mode only);
- for **exam** mode, tells Gemini to put key definitions and 1–3 likely exam questions **with short answers inside the `explanation` text** (the UI only shows `explanation` and subtopics, so differences must appear there);
- tells Gemini that each `image_prompt` must describe a single concept visually in the plan's `image_style`, with **minimal or no text inside the image** (SANA cannot render legible text);
- keeps the **exact same JSON output schema** as the current prompt in `ai_service.py` (5 subtopics, title/brief/image_prompt, explanation, image_prompts).

### 1.6 Wiring (keep old signatures working)
- Change `generate_content(topic, level)` to `generate_content(topic, level, mode="learn", plan=None)`. If `plan` is `None`, build it with the rule-based planner, so existing callers still work. Keep the existing parsing, normalization and Wikipedia fallback exactly as they are; only the prompt text changes.
- Loosen the explanation length rule so that college/exam answers can be longer (e.g. up to 10 sentences), but keep `_normalize_explanation` behaviour intact.
- In `generate_routes.py`:
  1. `plan = analyze_input(topic, level, mode)` (Qwen or rules)
  2. `subtopics, explanation, image_prompts = generate_content(topic, level, mode, plan)`
  3. pass `level` and `plan` to the image service (Phase 2)
  4. add `"analysis": {"source": ..., "plan": plan, "analysis_ms": ...}` to the JSON response (new key, frontend ignores it).
- Add an authenticated `POST /analyze` endpoint that returns only the plan. This is for the project demo and for tests; no UI change.
- Log one line per request: topic, level, mode, analyzer source, timings. Never log the API key.

### 1.7 Phase 1 acceptance
- With `ANALYZER_ENABLED=false`: `/generate` works; plans come from rules; the 4 combinations produce visibly different explanations.
- With `ANALYZER_ENABLED=true` on the laptop: Qwen loads in 4-bit, returns valid plans for at least 8 test topics × 4 combinations (or falls back cleanly); measured analysis time is recorded.
- Save the 4 responses for "Earth" and "Photosynthesis" to `docs/after_phase1/` and write `docs/after_phase1/COMPARISON.md` showing baseline vs new text side by side.

---

## PHASE 2 — LOCAL IMAGE GENERATION (SANA 1.5) WITH ASYNC JOBS

### 2.1 New / changed files
```
backend/services/image_backends/__init__.py
backend/services/image_backends/pollinations_backend.py   moves the existing URL-building logic, unchanged output
backend/services/image_backends/sana_local.py             SANA pipeline loader + generate(prompt) -> PIL image
backend/services/image_backends/sana_remote.py            HTTP client for the workstation server
backend/services/image_jobs.py                            queue + single worker thread + job status
backend/routes/generated_routes.py                        GET /generated/<id>, GET /generated/<id>/status
backend/image_server/sana_server.py                       standalone server for the workstation (remote mode)
backend/services/image_service.py                         becomes a dispatcher; keeps generate_images(prompts, mode)
```

### 2.2 `image_service.generate_images(prompts, mode, level=None, plan=None)`
- `IMAGE_BACKEND=pollinations` → return exactly what the original function returned (same URLs, same style hints). `generate_routes.py` keeps wrapping these with `_proxy_url`.
- `IMAGE_BACKEND=local|remote` → for each of the first `SANA_NUM_IMAGES` prompts, create an image id (uuid4 hex), enqueue a job, and return the URL `"{host}/generated/{id}.png"`.
  - In `generate_routes.py`, apply `_proxy_url` **only** to pollinations URLs. Local URLs are returned as-is.
  - If fewer than 5 images are generated, fill the remaining slots so the list still has the same length as `subtopics` (reuse the pollinations URL if `IMAGE_FALLBACK_TO_POLLINATIONS=true`, otherwise a placeholder URL that serves the existing SVG placeholder).

### 2.3 SANA prompt construction
`final_prompt = f"{SANA_TRIGGER}, {style_phrase}, {image_prompt}, educational illustration, clean background, minimal text"`.
`style_phrase` comes from `plan["image_style"]` and level/mode (e.g. `"school level, simple colourful infographic"`, `"college level, detailed labeled textbook diagram"`). When no LoRA is loaded, omit the trigger word. Use a fixed negative prompt (e.g. `"blurry, photo of people, watermark, garbled text, low quality"`) if the pipeline supports it. Use a seed derived from a hash of the prompt so results are reproducible.

### 2.4 SANA local loader (`sana_local.py`)
- Load lazily on the **first job**, inside the worker thread, through `model_manager` with the GPU lock.
- Load `SANA_MODEL_ID` with diffusers `SanaPipeline` (verify the class name for the installed version).
  - transformer: bf16; if `SANA_FUSED_TRANSFORMER_PATH` is set, load that transformer instead.
  - text encoder: 4-bit via bitsandbytes when `SANA_TEXT_ENCODER_4BIT=true` (load the text encoder separately with a quantization config and pass it into the pipeline).
  - VAE: bf16, enable tiling/slicing.
  - offload per `SANA_OFFLOAD`.
  - If `SANA_LORA_PATH` is set and no fused transformer is used: `pipe.load_lora_weights(...)` with `SANA_LORA_SCALE`.
- Before loading SANA, make sure Qwen is unloaded (model manager).
- On CUDA out-of-memory: free memory, switch to sequential offload, retry once; if it still fails, mark the job failed with the error text.
- Record per-image generation time and peak VRAM (`torch.cuda.max_memory_allocated`).

### 2.5 Job queue (`image_jobs.py`)
- One background worker thread, one in-memory queue, statuses `pending | running | done | failed`.
- Output files: `backend/{GENERATED_IMAGES_DIR}/{id}.png` (create the folder; add it to `.gitignore`).
- Start the worker **only once**: if running under the Werkzeug reloader, start it only when `os.environ.get("WERKZEUG_RUN_MAIN") == "true"`, or when debug is off. Also guard model loading the same way so models never load twice.
- Status lookup for an unknown id: `done` if the file exists, otherwise `failed` (handles restarts).

### 2.6 Routes (`generated_routes.py`, register in `app.py`)
- `GET /generated/<id>.png`: if the file exists, send it (`Cache-Control: public, max-age=86400`). If pending/running, return the existing-style SVG placeholder with text "Generating image…" plus header `X-Image-Status: pending` and `Cache-Control: no-store`. If failed, return the existing "Image generation unavailable" SVG.
- `GET /generated/<id>/status`: `{"status": "...", "error": null|"..."}`.
- No auth on these two routes (the `<img>` tag cannot send the JWT); ids are unguessable uuids. Validate the id with a strict regex (`^[0-9a-f]{32}$`) to prevent path traversal.
- **Rate limit:** exempt paths starting with `/generated/` in `app.py`'s `rate_limit()` so polling never triggers 429. Do not change the limit for other routes.

### 2.7 The only two frontend changes allowed
1. `frontend/src/services/api.js`: give `generateContent` its own longer timeout (e.g. 120000 ms) via a per-request config. Leave the default 15000 for other calls.
2. `frontend/src/components/ImageCard.js`: if `src` contains `/generated/`, poll `GET {src without .png}/status` every 3 s (stop on `done`/`failed`, stop on unmount, max ~10 min). On `done`, set the image `src` to the PNG URL with a `?v=<timestamp>` cache-buster. Keep the existing look, sizes, hover effect and `onError` fallback. For non-generated URLs, behaviour is unchanged.
Check `Result.js`, `History.js`, `HistoryList.js` to confirm they render images via `ImageCard` or plain `<img>`; if a page uses a plain `<img>` for generated URLs, apply the same polling there with no visual change.

### 2.8 Remote mode
- `backend/image_server/sana_server.py`: small Flask app (port 7860, host 0.0.0.0) that loads the same SANA pipeline (bf16, no offload, 1024 allowed) and exposes `POST /generate_image {prompt, negative_prompt, height, width, steps, guidance, seed}` → PNG bytes. Requires header `X-Token: SANA_REMOTE_TOKEN`.
- `sana_remote.py` calls it from the worker thread (timeout 300 s) and saves the PNG locally, so the rest of the flow is identical to local mode.
- Document how to run it on the workstation and how to find the workstation's LAN IP.

### 2.9 Phase 2 acceptance
- `IMAGE_BACKEND=pollinations`: behaviour identical to baseline.
- `IMAGE_BACKEND=local` on the laptop with the **base** SANA model (no LoRA yet): `/generate` returns quickly; images appear progressively in the UI; no OOM crash with 5 images at 512×512; history still shows the images after a backend restart.
- Measured: per-image time, total time for 5 images, peak VRAM, peak RAM (from Task Manager/`psutil`), Qwen load time.
- If 512×512 still runs out of memory on the laptop, try in this order: sequential offload → 384×384 → `SANA_NUM_IMAGES=3`. Report what was needed.

---

## PHASE 3 — DATASET (workstation)

### 3.1 Goal
1,500–5,000 high-quality educational diagram images with captions, tagged by style (school/college look, learn/exam look), with a verified license for every image.

### 3.2 Sources (verify each license before use; record it per image)
Search and evaluate at execution time. Candidates to check:
- **AI2D** (Allen AI science diagrams) — check the current license on the official page / Hugging Face card.
- **TQA** (Textbook Question Answering, Allen AI) diagram images — check license.
- **ScienceQA** images — known to be non-commercial (CC BY-NC-SA); usable only because this is a non-commercial academic project; flag it.
- **Wikimedia Commons** science/biology/geography/physics diagram categories — download only files whose license is Public Domain, CC0, CC BY or CC BY-SA, and store author + license + source URL.
Prefer permissive licenses. Do not use any source whose license forbids training or redistribution. Do not scrape sites whose terms forbid it.

### 3.3 Pipeline (`training/dataset/`)
```
training/dataset/download_<source>.py    one script per source, resumable
training/dataset/filter.py               min side >= 512, remove duplicates (perceptual hash), remove photos of people, remove corrupt files
training/dataset/caption.py              VLM captions + style tags
training/dataset/build_metadata.py       writes metadata.jsonl + manifest.csv + train/val/test split (90/5/5)
training/dataset/stats.py                counts per source, per tag, per license
```
- Captioning: use a vision-language model on the workstation (e.g. `Qwen/Qwen2.5-VL-7B-Instruct`; verify the id). For each image produce: (a) a one-sentence description of the concept shown, (b) `complexity`: simple|detailed, (c) `look`: infographic|textbook_diagram|process_flow|cross_section.
- Map tags to style words: simple → `school level`, detailed → `college level`; infographic → `learn style colourful infographic`; textbook_diagram/cross_section → `exam style clean labeled textbook diagram`; process_flow → `process flow diagram`.
- Final caption format (must match inference in 2.3):
  `edudiag, {level words}, {look words}, {description}`
- Output layout compatible with the diffusers LoRA script (image folder + `metadata.jsonl` with `file_name` and `text` columns). Keep `manifest.csv` with `file_name, source, source_url, license, author, complexity, look, split`.
- Spot-check 50 random captions manually-style (print them with file names into `docs/dataset/caption_samples.md`).

### 3.4 Phase 3 acceptance
`docs/dataset/DATASET_CARD.md` with real numbers: total images, per-source counts, per-license counts, per-tag counts, split sizes, known issues.

---

## PHASE 4 — LoRA FINE-TUNING (workstation)

### 4.1 Base model
`Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers` in bf16. Verify the id on Hugging Face. Do **not** train on an FP8 checkpoint.

### 4.2 Script
Use the official diffusers SANA DreamBooth-LoRA example (`examples/dreambooth/train_dreambooth_lora_sana.py` — verify the exact name for the installed diffusers version; clone the matching diffusers tag if the example is not in the pip package). Wrap it in `training/train_lora.sh` so the run is reproducible. Do not write a custom trainer unless the example cannot be used; if so, explain why.

### 4.3 Starting hyper-parameters (adjust only with evidence)
```
resolution            1024 (native); also evaluate outputs at 512
mixed_precision       bf16
rank                  32 (try 16 if overfitting)
learning_rate         1e-4, constant with warmup ~100 steps
train_batch_size      4  (gradient_accumulation as needed)
gradient_checkpointing on
max_train_steps       ~2000–4000 (about 5–10 passes over the data; scale with dataset size)
checkpointing_steps   500
validation            4 fixed prompts every 500 steps (school/learn, school/exam, college/learn, college/exam)
seed                  42
caption column        text
```
Log to TensorBoard. Save the loss curve as `docs/training/loss_curve.png` and the validation images per checkpoint to `docs/training/validation/`.

### 4.4 Outputs
- `training/output/sana_edu_lora/pytorch_lora_weights.safetensors` (final) and intermediate checkpoints.
- `training/output/TRAINING_LOG.md`: exact command, library versions, GPU, steps, time taken, final loss.

### 4.5 Optional fused transformer for the laptop
Write `training/fuse_lora.py`: load the base transformer in bf16, load the LoRA, fuse it, save the fused transformer folder (`training/output/sana_edu_fused_transformer/`). This lets the laptop skip `peft` at runtime. Test that it loads and generates.

---

## PHASE 5 — EVALUATION (workstation)

1. Build `training/eval/prompts.json`: 20 held-out educational topics × the 4 level/mode combinations (80 prompts), using the same prompt construction as Section 2.3.
2. Generate with the **base model** and the **LoRA model** using identical seeds and settings, at 1024 and at 512.
3. Metrics:
   - CLIP text–image similarity (e.g. `openai/clip-vit-large-patch14`), mean ± std, base vs LoRA.
   - Generation time per image on the workstation.
4. Make side-by-side grids (`docs/eval/grids/*.png`): base | LoRA for each prompt.
5. Write `docs/eval/EVAL_REPORT.md` with the real numbers and honest observations, including cases where the LoRA is worse. Do not cherry-pick without saying so.

---

## PHASE 6 — DEPLOY THE FINE-TUNED MODEL ON THE LAPTOP

1. The owner copies `pytorch_lora_weights.safetensors` (and optionally the fused transformer folder) to `backend/models_store/lora/` (and `backend/models_store/fused/`) on the laptop. Add `backend/models_store/` to `.gitignore`.
2. Set in `.env`: `IMAGE_BACKEND=local`, `SANA_LORA_PATH=...` (or `SANA_FUSED_TRANSFORMER_PATH=...`), `SANA_TRIGGER=edudiag`.
3. Run the Phase 2 acceptance again with the LoRA. Generate the 4 combinations for "Earth" and "Photosynthesis" and save results to `docs/after_phase6/`.
4. Test the remote fallback: run `sana_server.py` on the workstation, set `IMAGE_BACKEND=remote` on the laptop, and generate once.
5. Measure on the laptop: Qwen load + inference time, Gemini time, SANA load time, per-image time, total time, peak VRAM, peak RAM.

---

## 11. TESTS

Create `backend/tests/` (pytest), runnable without a GPU (mock Qwen/SANA/Gemini where needed):
- `test_plan_rules.py`: the 4 combinations produce different plans; schema validation rejects bad JSON and merges defaults.
- `test_prompt_builder.py`: mode and level text appear in the Gemini prompt; exam mode asks for questions; output schema unchanged.
- `test_generate_contract.py`: `/generate` (with a test JWT, Gemini mocked) returns all original keys; `analysis` key present; works with `ANALYZER_ENABLED=false` and `IMAGE_BACKEND=pollinations`.
- `test_generated_routes.py`: id regex blocks traversal; pending → SVG + header; done → PNG; rate limiter does not block `/generated/`.
- `test_image_service_pollinations.py`: output identical to the original implementation for the same input.

Also a manual GPU smoke test script `backend/scripts/smoke_local_ai.py` that loads Qwen, prints a plan, unloads it, loads SANA, generates one 512 image, prints timings and peak VRAM.

---

## 12. DOCUMENTATION TO PRODUCE

- `docs/ARCHITECTURE.md` — the diagram in Section 3, data flow, and why each model was chosen.
- `docs/SETUP_LAPTOP_WINDOWS.md` — exact PowerShell commands: conda env, `pip install -r backend/requirements-ai.txt`, CUDA torch install command actually used, `.env` lines, page-file advice, how to start backend and frontend, how to switch `IMAGE_BACKEND`.
- `docs/SETUP_WORKSTATION_UBUNTU.md` — env creation, dataset build commands, training command, evaluation, fusing, running `sana_server.py`, firewall/port note.
- `docs/DEMO_SCRIPT.md` — a 5-minute review demo: show the same topic in the 4 combinations, show `/analyze` output, show base vs LoRA grids, show training loss curve and eval table.
- `docs/UPGRADE_REPORT.md` — the final report (Section 13).

---

## 13. FINAL REPORT (`docs/UPGRADE_REPORT.md`) — fill with real values only

```
1. Summary of what was implemented (by phase), and what was NOT completed
2. Files added / files modified (with one line each on why)
3. Corrections to this plan (wrong model ids, script names, flags) and what was used instead
4. Laptop environment: Python version, env name, torch/CUDA versions, GPU, driver
5. Workstation environment: same
6. Input Analysis Layer: Qwen model id, quantization, load time, avg analysis time, fallback rate in tests
7. Dataset: sources, licenses, counts, splits (from DATASET_CARD.md)
8. Training: command, steps, time, final loss, adapter path, size
9. Evaluation: CLIP base vs LoRA (mean ± std), timing, link to grids, honest observations
10. Laptop runtime: Qwen, Gemini, SANA load, per-image, total, peak VRAM, peak RAM
11. Known limitations (e.g. SANA cannot render legible text labels; laptop speed; NC-licensed data if used)
12. Exact run instructions (laptop + workstation)
13. .env lines the owner must add
```

---

## 14. FINAL WARNINGS

- Do not say "everything is complete" unless every acceptance check in this file passed on the real machines.
- Do not say "the LoRA was trained" unless a real run produced the adapter file.
- Do not say "SANA runs locally on the laptop" unless an image was actually generated on the RTX 2050.
- Do not state a license you did not verify.
- Do not state a speed or quality number you did not measure.
- If something is blocked, stop that part, explain the exact blocker, and continue with the parts that are not blocked.

The project owner values a **real, working, honestly reported implementation** over a fictional complete one.

---
**END OF IMPLEMENTATION PLAN**
