# Upgrade report

Written 2026-10-02. Everything was executed on the **workstation** (Ubuntu 24.04, RTX 6000 Ada).
Nothing in this report was run on the laptop. Every number below was measured in this run; where
something was not measured it says so.

## Blockers and open items (read first)

1. **Gemini does not work with the key in `backend/.env` on this machine.**
   - `gemini-2.5-flash-lite` (the default `GEMINI_MODEL`) returns `404 NOT_FOUND: This model ... is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite`.
   - `gemini-3.5-flash-lite` and `gemini-3.5-flash` return `403 PERMISSION_DENIED: Your project has been denied access. Please contact support.`
   - Consequence: every `/generate` text (baseline and after the upgrade) came from the existing Wikipedia fallback, which ignores level and mode. **The Phase 1 acceptance check "the 4 combinations produce visibly different explanations" has not passed and could not be tested with real Gemini output.** What is verified: the plans differ, the Gemini prompts differ, and (with Gemini mocked in tests) mode and level reach Gemini.
   - Needed from the owner: a working Gemini key/project, and probably `GEMINI_MODEL=gemini-3.5-flash-lite` in `.env` (that model name comes from Google's error message; it was not verified to work). Then run `python backend/scripts/capture_responses.py docs/after_phase1 <jwt file>` and `python backend/scripts/make_comparison.py`.
2. **The fine-tuned LoRA is worse than the base model** in the evaluation (section 9). Do not deploy it as it is.
3. **Phase 6 and all laptop work are not done** (no laptop access from this session).

## 1. Summary by phase

| Phase | Status | Notes |
|---|---|---|
| 0 Inspect, back up, baseline | Done on the workstation | Backup zip in `backups/`. Baseline saved for Earth and Photosynthesis x 4 combinations (`docs/baseline/`); all 8 are Wikipedia-fallback text because of the Gemini blocker. Frontend was not started with `npm start`; it was compiled with `react-scripts build` (succeeds, with pre-existing lint warnings). |
| 1 Input Analysis Layer | Code done and tested; one acceptance check blocked | Qwen runs in 4-bit and returned valid plans for 31 of 32 requests through the live app. Text-difference check blocked by Gemini (above). |
| 2 Local image generation | Done and tested on the workstation with the base model | 40 of 40 images rendered through the job queue at 512x512 with laptop-style settings; images and history survive a backend restart. Not tested in a browser; the polling code compiles but was not exercised in the UI. Not run on the laptop. |
| 3 Dataset | Done | 4,225 images, licences recorded per image. |
| 4 LoRA fine-tuning | Done (one run, no tuning) | Adapter produced. Loss shows no clear decrease. |
| 5 Evaluation | Done | LoRA scores below base. |
| 6 Laptop deployment | **Not done** | Needs the laptop. |
| Tests | 54 pytest tests pass | No GPU, Gemini or real database needed. |
| Docs | Written | ARCHITECTURE, SETUP_LAPTOP_WINDOWS (unexecuted), SETUP_WORKSTATION_UBUNTU, DEMO_SCRIPT, DATASET_CARD, TRAINING_LOG, EVAL_REPORT, this report. |

## 2. Files

**Added – backend**

| File | Why |
|---|---|
| `backend/services/model_manager.py` | GPU lock, lazy load/unload, one model at a time |
| `backend/services/plan_rules.py` | Rule-based teaching plan and strict plan validation |
| `backend/services/input_analyzer.py` | Qwen analysis with fallback to rules |
| `backend/services/prompt_builder.py` | Gemini prompt built from the plan |
| `backend/services/image_backends/pollinations_backend.py` | Original URL builder, moved unchanged |
| `backend/services/image_backends/sana_prompt.py` | Single definition of the SANA prompt / caption format |
| `backend/services/image_backends/sana_local.py` | SANA pipeline loader and generation |
| `backend/services/image_backends/sana_remote.py` | Client for the workstation image server |
| `backend/services/image_jobs.py` | Queue, worker thread, job status |
| `backend/routes/generated_routes.py` | `/generated/<id>.png`, `/generated/<id>/status` |
| `backend/image_server/sana_server.py` | Standalone image server for remote mode |
| `backend/requirements-ai.txt` | Extra dependencies for the local AI features |
| `backend/tests/*` (5 test files + conftest) | Section 11 tests |
| `backend/scripts/smoke_local_ai.py`, `capture_responses.py`, `analyzer_matrix.py`, `make_comparison.py` | GPU smoke test and evidence capture |

**Added – training**: `training/dataset/{common,download_ai2d,download_wikimedia,filter,caption,build_metadata,stats}.py`,
`training/{common,train_sana_lora_lowmem,validate_checkpoints,plot_loss,fuse_lora}.py`, `training/train_lora.sh`,
`training/eval/{build_prompts,generate,score}.py`, `training/eval/prompts.json`.

**Modified**

| File | Change |
|---|---|
| `backend/config.py` | New `.env` fields with safe defaults (features off) |
| `backend/.env.example` | New settings documented |
| `backend/app.py` | Registers the new blueprint; `/generated/` exempt from the rate limiter |
| `backend/routes/generate_routes.py` | Analyzer → plan → Gemini → image dispatcher; `analysis` key; `POST /analyze`; one log line per request |
| `backend/services/ai_service.py` | `generate_content(topic, level, mode="learn", plan=None)`; only the prompt text changed |
| `backend/services/image_service.py` | Now a dispatcher; pollinations output identical (tested) |
| `frontend/src/services/api.js` | 120 s timeout for `generateContent` only |
| `frontend/src/components/ImageCard.js` | Status polling for `/generated/` URLs (exported as a hook) |
| `frontend/src/pages/History.js` | Thumbnails use the same polling hook; same `<img>` attributes and styles |
| `.gitignore`, `README.md` | Ignore generated data and weights; pointer to the docs |

Not touched: `backend/.env`, `database/schema.sql`, both original `requirements.txt` files, `utils/prompt_builder.py`.

**Side effects on this machine's database:** a test account `upgrade-test@example.com` (user id 26) and about 18
history rows were created in `backend/database/app.db` while capturing evidence. They were left in place.

## 3. Corrections to the plan

| Plan | What was found / used |
|---|---|
| Model ids `Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers`, `Qwen/Qwen2.5-1.5B-Instruct`, `Qwen/Qwen2.5-VL-7B-Instruct` | All exist on Hugging Face, ungated, tagged Apache-2.0 (checked through the HF API). |
| `examples/dreambooth/train_dreambooth_lora_sana.py` | Name correct at diffusers v0.40.0. It preloads all images as float32 and was OOM-killed on 3,803 images, so it is run through `training/train_sana_lora_lowmem.py` (uint8 cache; same training loop). |
| "validation: 4 fixed prompts every 500 steps" | The script supports one prompt. Done after training from the saved checkpoints (`validate_checkpoints.py`). |
| Default `ANALYZER_ENABLED=true` in the plan's `.env` block | The code default (when `.env` lacks the line) is `false`, so that an unchanged `.env` behaves like the original app. `.env.example` shows `true`. |
| `analyze_input` returns the plan | It returns `{source, plan, analysis_ms, ...}`; the route takes `plan` from it. |
| 512x512 with the 1024 px model | SANA's resolution binning would silently render 1024 px and downscale. Binning is switched off below 1024 px so 512 really is 512. |
| SANA "complex human instruction" | Disabled at inference for base and LoRA, because the training script trains on plain captions. |
| Greedy decoding for Qwen | Greedy, plus `repetition_penalty=1.1` after a runaway-list output was observed. |
| Worker start guard | Worker starts lazily on the first job; never in the debug reloader's parent process. |
| ScienceQA "known to be CC BY-NC-SA" | Official site says CC BY-NC-SA; the HF mirror is tagged cc-by-sa-4.0. Not used. TQA (CC BY-NC 3.0) not used either. |
| `gemini-2.5-flash-lite` | No longer available to this key (see Blockers). Default left unchanged because the replacement could not be verified. |
| Unknown URLs | The app's original catch-all error handler turns 404 into 500. Left unchanged; the traversal test accepts either. |

## 4. Laptop environment

**Not measured.** No command was run on the laptop. The Python 3.13 vs 3.11 decision is still open
(`docs/SETUP_LAPTOP_WINDOWS.md` describes both paths).

## 5. Workstation environment

Ubuntu 24.04.4, kernel 7.0.0-34; Xeon Silver 4509Y; 62 GiB RAM; NVIDIA RTX 6000 Ada Generation 48 GB, driver 595.84.
conda env `sana_train`, Python 3.11; torch 2.14.1+cu130 (CUDA 13.0 build), `torch.cuda.is_available()` = True;
diffusers 0.40.0, transformers 5.18.0, peft 0.21.2, accelerate 1.15.0, bitsandbytes 0.50.2, Flask 3.1.3. Node v24.15.0.

## 6. Input Analysis Layer (workstation measurements)

- Model `Qwen/Qwen2.5-1.5B-Instruct`, 4-bit NF4 (bitsandbytes), bf16 compute. Peak VRAM about 1,200 MB.
- Load time: 54.3 s on first use (includes downloading the model); 1.1-1.7 s when already cached on disk.
- Inference with the model already loaded: 4.4 s for one plan (smoke test).
- Through the live app with `QWEN_UNLOAD_AFTER_USE=true` (load + generate + unload per request), 8 topics x 4
  combinations: mean 7.5 s, median 6.8 s, min 5.7 s, max 14.4 s (`docs/after_phase1/analyzer_matrix_unload_true.json`).
- Fallback rate: 1 of 32 (3.1%) fell back to rules (Earth / college / exam: the model produced an endless list and
  no valid JSON). Of the 31 Qwen plans, 12 had one field repaired from the rule plan (subtopic list shorter than 5).
- When image jobs are running, the analyzer waits for the GPU: `analysis_ms` of about 20-34 s was logged for
  back-to-back `/generate` requests.
- In the mocked tests the fallback path is exercised directly (Qwen raising, Qwen returning partial JSON).

## 7. Dataset

See `docs/dataset/DATASET_CARD.md`. 4,225 images: AI2D 1,440 (CC BY-SA per the AWS Open Data registry),
Wikimedia Commons 2,785 (per-file PD / CC0 / CC BY / CC BY-SA). Split 3,803 / 211 / 211.
Tags: simple 2,728, detailed 1,497; textbook_diagram 3,105, infographic 827, process_flow 285, cross_section 8.

## 8. Training

See `docs/training/TRAINING_LOG.md`. `MAX_STEPS=4000 bash training/train_lora.sh`; rank 32, lr 1e-4, batch 4,
1024 px, bf16; 4,000 steps in 1 h 58 min 53 s. Loss: first-50-step mean 0.3858, last-50-step mean 0.3507, final
step 0.4662, no clear downward trend. Adapter: `training/output/sana_edu_lora/pytorch_lora_weights.safetensors`,
34,439,360 bytes. Fused transformer: `training/output/sana_edu_fused_transformer/`, 3,061 MB, loads and generates.

## 9. Evaluation

See `docs/eval/EVAL_REPORT.md` and `docs/eval/grids/`. CLIP ViT-L/14 similarity, 80 prompts, mean ± std:

| Resolution | Base | LoRA | Prompts where LoRA is higher | s/image base | s/image LoRA |
|---|---|---|---|---|---|
| 1024 | 0.2762 ± 0.0327 | 0.2545 ± 0.0412 | 24 of 80 | 2.04 | 2.12 |
| 512 | 0.2515 ± 0.0395 | 0.2087 ± 0.0465 | 12 of 80 | 0.60 | 0.77 |

Honest observation: the LoRA moved the style towards sparse labelled line diagrams, but subjects are often lost and
the label-like text is unreadable; at 512 px it is clearly worse. The base model is the better choice today.

## 10. Laptop runtime

**Not measured.** For orientation only, the same laptop-style settings on the workstation GPU
(4-bit text encoder, model CPU offload, 512x512, 20 steps, base model):

- SANA load: 116 s on first use (includes download); 4.8-6.3 s from disk cache.
- Per image: 2.5-6.1 s. 40 images from 8 requests finished within 73 s of the last request.
- Peak VRAM (torch allocated): 3,164 MB. Peak process RAM: 9,250 MB.
- No out-of-memory error occurred, so the sequential-offload retry path was not exercised on real hardware.

These do not predict laptop speed. The RAM figure does suggest the 8 GB laptop will rely on the page file.

Remote mode (image server and backend on the workstation, 127.0.0.1): 5 images at 1024x1024 in 36 s including
a 10.7 s model load; 3.2-5.2 s per image; peak VRAM 9,159 MB. Wrong or missing token returns 401.

## 11. Known limitations

- SANA cannot render legible text; diagrams have no readable labels.
- The LoRA is not an improvement (section 9).
- Text does not differ by level/mode until Gemini works (Blockers).
- One model on the GPU at a time: back-to-back requests make Qwen and SANA reload repeatedly.
- Job status is in memory; a restart during generation leaves those images as "failed".
- `/generated/*` has no auth and no rate limit (by design; ids are random 128-bit values).
- The remote image server is plain HTTP with a shared token; LAN use only.
- Dataset: machine-written captions, some non-diagram images, unbalanced tags, CC BY-SA share-alike terms.
- UI polling was compiled but not tested in a browser.

## 12. Run instructions

Workstation: `docs/SETUP_WORKSTATION_UBUNTU.md` (all commands were executed).
Laptop: `docs/SETUP_LAPTOP_WINDOWS.md` (not executed).

Quick start on the workstation:

```bash
conda activate sana_train
cd backend && python -m pytest tests -q
ANALYZER_ENABLED=true IMAGE_BACKEND=local python app.py     # or put the lines below in .env
cd ../frontend && npm start
```

## 13. Lines to add to `backend/.env`

`.env` was not edited. Without these lines the app behaves like the original. Put comments on their own lines.

```ini
# probably needed once the key works (model name from Google's error message, not verified)
GEMINI_MODEL=gemini-3.5-flash-lite

ANALYZER_ENABLED=true
QWEN_MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct
QWEN_LOAD_IN_4BIT=true
QWEN_UNLOAD_AFTER_USE=true
QWEN_MAX_NEW_TOKENS=512

IMAGE_BACKEND=local
SANA_MODEL_ID=Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers
SANA_LORA_PATH=
SANA_LORA_SCALE=1.0
SANA_FUSED_TRANSFORMER_PATH=
SANA_TEXT_ENCODER_4BIT=true
SANA_OFFLOAD=model
SANA_HEIGHT=512
SANA_WIDTH=512
SANA_STEPS=20
SANA_GUIDANCE=4.5
SANA_NUM_IMAGES=5
SANA_TRIGGER=edudiag
GENERATED_IMAGES_DIR=generated_images

SANA_REMOTE_URL=
SANA_REMOTE_TOKEN=
IMAGE_FALLBACK_TO_POLLINATIONS=false
```

Keep `SANA_LORA_PATH` empty (base model) until a better adapter exists. On the workstation use
`QWEN_UNLOAD_AFTER_USE=false`, `SANA_TEXT_ENCODER_4BIT=false`, `SANA_OFFLOAD=none`.
