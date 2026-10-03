# End-to-end test report: new version (Qwen ON + Gemini + local SANA base, LoRA off)

Date: 2026-10-03. Machine: **workstation (RTX 6000 Ada)**, Ubuntu 24.04, conda env `sana_train`
(the `text_to_image` env does not exist on this machine; you told me to use `sana_train`).
**All timings and memory numbers below are workstation (RTX 6000 Ada) numbers, not laptop numbers.**
Everything in this report was run and observed; the evidence files are in this folder.

## Summary

| Step | Result |
|---|---|
| 1 Stop old servers | PASS (nothing was running) |
| 2 Gemini check | **FAIL with `backend/.env` as it is**; PASS with the model set for the process (see below) |
| 3 Local models smoke test | PASS |
| 4 Start the new version | Backend PASS. Frontend `npm start` **FAIL** (permission error); started with the equivalent node command instead. Startup log does not print the feature settings (no such log line exists) |
| 5 End-to-end API test | PASS for both requests |
| 6 Old path really off | PASS (0 Pollinations, 0 Wikipedia fallbacks) |
| Extra: landing-page intro removed | Done on your request (see last section) |

## Settings used

`backend/.env` was backed up to `backend/.env.backup` before editing. Only these lines were set:
`ANALYZER_ENABLED=true`, `IMAGE_BACKEND=local`, `SANA_LORA_PATH=` (empty, LoRA off),
`IMAGE_FALLBACK_TO_POLLINATIONS=false`. All four exist in `backend/config.py`.

Effective configuration (printed from `Config`, non-secret): Qwen `Qwen/Qwen2.5-1.5B-Instruct`, 4-bit, unload after
use; image backend `local`; SANA `Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers`; LoRA path empty; fused
transformer empty; 4-bit text encoder; offload `model`; 512x512; 20 steps; 5 images; Pollinations fallback off.
These are the laptop-safe defaults, so the code path is the one the laptop will use.

## Step 1: Stop old servers: PASS

No process was listening on ports 5000, 3000 or 7860, and no `app.py` / `react-scripts` process was running.

## Step 2: Gemini: FAIL as configured, PASS with the model override

`python backend/scripts/test_gemini.py` (key never printed):

```
GEMINI_MODEL = gemini-2.5-flash-lite
GEMINI_API_KEY set: yes (length 53)
ERROR: ClientError: 404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model models/gemini-2.5-flash-lite is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite ...', 'status': 'NOT_FOUND'}}
RESULT: FAIL
```

Cause: the new key **is** in `backend/.env`, but `backend/.env` has **no `GEMINI_MODEL` line**, so the code default
`gemini-2.5-flash-lite` (`backend/config.py:45`) is used. No other `.env` file exists under the project, and no
`GEMINI_*` variable is set in the shell. The file was re-checked after your second message: still no `GEMINI_MODEL`
line (it may have been saved to a different file or not saved).

With the model given for the process only (`GEMINI_MODEL=gemini-3.5-flash-lite python backend/scripts/test_gemini.py`):

```
GEMINI_MODEL = gemini-3.5-flash-lite
GEMINI_API_KEY set: yes (length 53)
REPLY: Gemini OK
RESULT: PASS
```

So the new key works. Because `GEMINI_MODEL` is not one of the four lines I was allowed to change, I did **not**
edit `.env`; Steps 3-6 were run with `GEMINI_MODEL=gemini-3.5-flash-lite` set as an environment variable on the
command line. **You need to add the line `GEMINI_MODEL=gemini-3.5-flash-lite` to `backend/.env`**, otherwise a normal
restart of the backend will fall back to Wikipedia text again.

Hard-coded model search: `gemini-2.5-flash-lite` appears only as the default in `backend/config.py:45`
(`os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")`) and in `backend/.env.example:2`. Nothing overrides
`GEMINI_MODEL`; `services/ai_service.py` uses `Config.GEMINI_MODEL`.

## Step 3: Local models smoke test: PASS (workstation, RTX 6000 Ada)

Command: `python backend/scripts/smoke_local_ai.py --topic Photosynthesis --level college --mode exam --size 512 --offload model --out docs/test_run/smoke.png`
(log: `smoke_log.txt`, image: `smoke.png`).

| Measurement | Value |
|---|---|
| Qwen 2.5-1.5B 4-bit load | 12.6 s |
| Qwen plan, first call (incl. load) / warm call | 18.2 s / 3.5 s |
| Qwen peak VRAM (torch allocated) | 1,200 MB |
| Plan source | `qwen`, no fields replaced by rules |
| VRAM after Qwen unload | 8 MB |
| SANA base load (4-bit text encoder, model offload) | 4.8 s |
| SANA 512x512, 20 steps | 4.18 s |
| SANA peak VRAM (torch allocated) | 3,156 MB |
| Peak process RAM | 8,196 MB |

No out-of-memory error, so none of the fallbacks (sequential offload, 384 px, 3 images) were needed.

## Step 4: Start the new version

**Backend: PASS.** `python backend/app.py` from the project root (log: `backend_log.txt`). Serving on
`http://127.0.0.1:5000` and `http://172.16.24.233:5000`, debug mode with the Werkzeug reloader
(`* Restarting with stat` once; two python processes, which is how the reloader works).

- The startup log does **not** show "analyzer enabled / image backend local / LoRA none": the code has no startup
  log line for these. They are confirmed instead by the effective configuration above and by the per-request log
  lines (`analyzer=qwen ... image_backend=local`).
- Models are not loaded twice: no model is loaded at startup; during the test the log shows exactly one
  `loaded qwen_analyzer` per request (2 total) and one `loaded sana_pipeline` per image batch (2 total), each
  followed by the matching unload. No `Detected change` / second restart occurred during the test.

**Frontend: `npm start` FAIL**, exact output (`frontend_npm_start_attempt.txt`):

```
> frontend@0.1.0 start
> react-scripts start

sh: 1: react-scripts: Permission denied
```

Cause: `frontend/node_modules` was copied from Windows and the launchers in `node_modules/.bin/` have no execute
permission. `node_modules` exists (919 packages), so `npm install` was not run. To give you a working UI without
changing files, the same dev server was started with
`node node_modules/react-scripts/bin/react-scripts.js start` (log: `frontend_log.txt`): HTTP 200 on port 3000,
"Compiled with warnings" (missing source map inside `@mediapipe/tasks-vision`, plus pre-existing lint warnings).

## Step 5: End-to-end API test: PASS (workstation, RTX 6000 Ada)

Logged in as the existing test account `upgrade-test@example.com` (HTTP 200). Evidence:
`photosynthesis_college_exam.json`, `photosynthesis_school_learn.json`, the images in
`photosynthesis_*_images/`, `contact_sheet.jpg` (top row college/exam, bottom row school/learn), `e2e_summary.json`.

| Check | Photosynthesis, college, exam | Photosynthesis, school, learn |
|---|---|---|
| HTTP status | 200 | 200 |
| `analysis.source` | `qwen` | `qwen` (subtopic list topped up from rules) |
| Qwen analysis time (incl. load and unload) | 14.6 s | 7.9 s |
| Gemini time (`content_ms`) | 4.5 s | 3.5 s |
| Text from Gemini, not Wikipedia | yes: no `AI ERROR` in the log, Gemini-style subtopics ("Light-Dependent Reactions") | yes ("Making Food with Sunlight") |
| Image URLs | 5 x `http://127.0.0.1:5000/generated/<id>.png`, 0 Pollinations | 5 x `/generated/`, 0 Pollinations |
| Image status | 5 / 5 `done`, no errors | 5 / 5 `done`, no errors |
| `/generate` response time | 19.1 s | 11.4 s |
| Time until all 5 images done | 49.5 s | 37.5 s |

The first request's analysis included the one-off Qwen load (4.7 s). Per-image SANA time: 2.8-4.9 s; SANA reload
after Qwen 5.1-8.3 s.

**Peak memory during Step 5** (sampled every second, `resource_samples.txt`):
backend process RAM **11,099 MB**; GPU memory used by the backend process (nvidia-smi, includes CUDA context)
**3,710 MiB**; torch peak allocated per image **3,164 MB**.

### Are the two answers clearly different? Yes.

College / exam (first part of the explanation):

> "Photosynthesis is the endergonic, anabolic process by which photoautotrophs convert carbon dioxide and water into
> glucose and molecular oxygen utilizing electromagnetic radiation. The overall mechanism comprises light-dependent
> reactions within the thylakoid membrane that generate ATP and NADPH, followed by light-independent carbon
> assimilation reactions occurring in the stroma. Q: Detail the enzymatic mechanism of Rubisco during the primary
> step of the Calvin cycle. A: ..."

It continues with three Q/A exam questions in total.

School / learn (the whole explanation):

> "Have you ever wondered how trees and flowers grow so big without eating anything? Plants make their own food
> using a superpower called photosynthesis, where they capture sunlight in their green leaves just like a solar
> panel. They mix this light energy with water from the dirt and carbon dioxide from the air to bake delicious
> glucose for their meals. As a wonderful bonus, they puff out fresh oxygen for us to breathe while they eat!"

Subtopics also differ completely (college: Light-Dependent Reactions, Carbon Fixation, ...; school: Making Food
with Sunlight, The Magic Green Stuff, ...). This is the level/mode difference that was missing before the upgrade.

**Images (by eye, `contact_sheet.jpg`):** the school/learn images are clear, colourful leaf illustrations. The
college/exam images are abstract diagram layouts full of unreadable pseudo-text and do not clearly show
photosynthesis.

## Step 6: Old path really off: PASS

Searched `backend_log.txt` for this run: `/image-proxy` requests **0** (the only route that fetches Pollinations),
lines mentioning `pollinations` **0**, `AI ERROR` (the Gemini failure that triggers the Wikipedia fallback) **0**,
lines mentioning `wikipedia` **0**, `GENERATE ERROR` **0**, tracebacks **0**, image jobs done **10**, failed **0**.
All 10 image URLs in the responses are `/generated/` URLs.

## Errors found and proposed fixes (not applied)

1. **`GEMINI_MODEL` missing from `backend/.env`**: add `GEMINI_MODEL=gemini-3.5-flash-lite` (your action).
   Optionally change the code default in `config.py:45` to `gemini-3.5-flash-lite` (asks for your approval).
2. **`npm start` permission error**: run once `chmod +x frontend/node_modules/.bin/*`, or delete
   `frontend/node_modules` and run `npm install` on this machine.
3. **No startup log of the feature flags**: proposal: print one line at startup, e.g.
   `CONFIG analyzer=on image_backend=local lora=none offload=model size=512`. Code change, needs your approval.
4. **College/exam images are full of garbled text**: the SANA style words for that look are
   "exam style clean labeled textbook diagram", and Gemini's image prompts start with "labeled textbook diagram";
   the word "labeled" pushes SANA to draw text it cannot render. Proposal: drop "labeled" from the inference style
   words and from the image prompts (prompt-only change; only safe while the LoRA stays off, because the LoRA's
   training captions contain that phrase). Needs your approval.
5. **Backend RAM 11.1 GB on the workstation**: well above the laptop's 8 GB. Expect page-file use on the laptop;
   increase the Windows page file to about 16 GB before testing there.
6. **Browser on another machine**: the frontend calls `http://127.0.0.1:5000` and the backend only allows the
   origin `http://localhost:3000`, so opening the UI from another computer will not work without config changes
   (see "How to open the app").

## Landing page change (requested during this task)

The cinematic intro (the `CinematicIntro` animation shown before the landing page) was removed:
`frontend/src/pages/Landing.js` now renders the landing page immediately. The hero text, buttons and the rest of
the page are unchanged. `frontend/src/components/CinematicIntro.js` is no longer used but was left in place. The dev
server recompiled with HTTP 200. This is a UI change you asked for explicitly; it was not part of the test steps.

## How to open the app

Both servers are left running (started with the `GEMINI_MODEL=gemini-3.5-flash-lite` environment override).

- On the workstation itself: **http://localhost:3000**
- From another computer on the LAN (workstation IP `172.16.24.233`): open `http://172.16.24.233:3000`, but API calls
  will fail until (a) `frontend/.env.local` contains `REACT_APP_API_BASE_URL=http://172.16.24.233:5000` and the
  frontend is restarted, and (b) `CORS_ORIGINS` in `backend/.env` includes `http://172.16.24.233:3000` and the
  backend is restarted.

---

## Update: fixes 1, 2 and 3 applied (approved), re-tested on the workstation (RTX 6000 Ada)

You also added `GEMINI_MODEL=gemini-3.5-flash-lite` to `backend/.env`. `test_gemini.py` run from `.env` only
(no override) now prints `GEMINI_MODEL = gemini-3.5-flash-lite` and `RESULT: PASS`. Both servers were restarted
**without** any environment override. Evidence: `docs/test_run/after_fixes/`.

| Fix | Change | Verified |
|---|---|---|
| 1 `npm start` permission error | `chmod +x frontend/node_modules/.bin/*` (165 launcher files; no code change) | `npm start` → `Compiled successfully!`, HTTP 200 on port 3000 |
| 2 Startup config log | `backend/app.py`: `log_startup_config()` prints one `CONFIG ...` line (never the key), only in the serving process | Printed once after `Restarting with stat`: `CONFIG analyzer=on qwen=Qwen/Qwen2.5-1.5B-Instruct qwen_4bit=True qwen_unload_after_use=True image_backend=local lora=none fused_transformer=none text_encoder_4bit=True offload=model size=512x512 steps=20 num_images=5 pollinations_fallback=False gemini_model=gemini-3.5-flash-lite gemini_key_set=yes` |
| 3 Garbled text in images | `sana_prompt.py`: for the base model (no LoRA) the style words are "exam style clean textbook diagram" and "labeled / labelled / with labels" is removed from the image prompt; with a LoRA the prompt is unchanged (matches its training captions). `prompt_builder.py`: Gemini is no longer told "labeled textbook diagram" and is told not to use the word "labeled" | 0 of 10 Gemini image prompts contain "label". College/exam images: 3 of 5 now have no text and 2 still show a small block of pseudo-text (before: all 5 were full of it). See `after_fixes/contact_sheet.jpg` |

Tests: 58 passed (4 new tests for fix 3).

Re-run of Step 5 after the fixes (`after_fixes/*.json`, `after_fixes/backend_log.txt`):

| Request | analysis.source | Gemini | `/generate` time | All 5 images done | Images |
|---|---|---|---|---|---|
| Photosynthesis, college, exam | qwen | yes (0 `AI ERROR`) | 19.4 s | 45.4 s | 5 `/generated/`, 5 done |
| Photosynthesis, school, learn | qwen | yes | 11.0 s | 39.0 s | 5 `/generated/`, 5 done |

Log: `/image-proxy` 0, `AI ERROR` 0, failed image jobs 0, tracebacks 0.

Remaining limitation: the college/exam images are cleaner but still abstract; they do not clearly depict the
specific mechanism (thylakoid, Calvin cycle). That is a limit of the base SANA model at 512 px.

---

## Update: mixed comparison mode (2 x SANA base, 2 x SANA + LoRA, 1 x Pollinations)

Requested by you. Workstation (RTX 6000 Ada) numbers. Evidence: `docs/test_run/mixed/`.

**What was added**

- New `IMAGE_BACKEND=mixed`. `IMAGE_MIX=base:2,lora:2,pollinations:1` sets the sources **in that order**
  (image 1-2 SANA base, 3-4 SANA + LoRA, 5 Pollinations). `SANA_MIX_LORA_PATH` points at the LoRA
  (copied to `backend/models_store/lora/pytorch_lora_weights.safetensors`, git-ignored).
  `local`, `remote` and `pollinations` modes are unchanged.
- Base and LoRA share **one** SANA pipeline; the adapter is switched on/off per image (`sana_local._apply_lora`),
  so there is no reload between base and LoRA images. Base images use the label-free prompt (fix 3); LoRA images
  use the trigger word and the exact training-caption wording. Base and LoRA use the same seed rule.
- `/generate` now also returns `image_sources` (e.g. `["sana_base","sana_base","sana_lora","sana_lora","pollinations"]`)
  in every mode. New key only; nothing removed. The UI does not show it yet.
- `CONFIG` startup line shows `image_mix=... mix_lora=...` in mixed mode.
- `.env`: backed up to `backend/.env.backup.before_mixed`, then `IMAGE_BACKEND=mixed`. Nothing else changed.
- Tests: 62 passed (4 new for mixed mode and per-job LoRA).

**Run results**

| Request | analysis | `/generate` time | 4 SANA images done | Sources | Jobs |
|---|---|---|---|---|---|
| Photosynthesis, college, exam | qwen | 18.5 s | 44.6 s | base, base, lora, lora, pollinations | 4/4 done |
| Photosynthesis, school, learn | qwen | 10.8 s | 30.6 s | base, base, lora, lora, pollinations | 4/4 done |

SANA loaded once per request (8.1 s / 4.9 s); per image 2.8-5.6 s; peak VRAM (torch) base 3,164 MB, with LoRA
active 3,197 MB. Log: `AI ERROR` 0, failed jobs 0, tracebacks 0.

**Pollinations:** first request returned a real image (JPEG). In the second request the existing `/image-proxy`
returned its "Image generation unavailable" SVG: Pollinations did not answer within the proxy's **12 s timeout**
(it renders on demand). Two retries through the proxy and one direct request then returned the image in 0.6-3.1 s
(`5_pollinations_retry.jpg`). In the browser, reloading the page retries the proxy.

**By eye (`mixed/contact_sheet.jpg`):** SANA base gives the clearest pictures (school/learn: leaf and sun-leaf
illustrations). The LoRA images are sparse line drawings; one of them is almost blank. This matches the
evaluation (LoRA scored below base). Pollinations images are reasonable but are 640x420 and carry a
"@pollinations.ai" watermark.

**Proposed, not applied (need your approval):**
1. Raise the `/image-proxy` timeout from 12 s to about 30 s (existing feature code in `generate_routes.py`), so the
   Pollinations slot falls back less often.
2. Show a small caption under each image in the UI ("SANA base", "SANA + LoRA", "Pollinations") using the new
   `image_sources` key. This is a UI change; without it the source is known only by position.

---

## Update: both follow-ups applied (approved)

1. **Image proxy timeout 12 s → 30 s.** New setting `IMAGE_PROXY_TIMEOUT_SECONDS` (default 30) in `config.py`,
   used by `/image-proxy` in `generate_routes.py`; documented in `.env.example`. Test added (63 tests pass).
   Live check (workstation): a new mixed request for "Water cycle / school / exam" returned the Pollinations image
   through the proxy as a real JPEG (21,173 bytes) in 2.8 s (`followups/`). One request is not proof that
   Pollinations will never exceed 30 s.
2. **Source captions under images (UI).** `ImageCard` accepts an optional `label` and shows it as a small line
   under the image (12 px, grey, same card). `Result.js` labels each image from `image_sources`:
   "SANA 1.5 (base)", "SANA 1.5 + LoRA", "SANA 1.5 (workstation)", "Pollinations.ai". Older history entries have
   no `image_sources` (the database stores only URLs), so they show "Pollinations.ai" or a generic "SANA 1.5"
   (base and LoRA cannot be told apart for them). History-page thumbnails are unchanged. The lightbox is unchanged.
   Verified: dev server "Compiled successfully!" and a production build "Compiled successfully." The captions
   were **not** checked visually in a browser.

---

## Update: mix changed to 2 x SANA base, 1 x SANA + LoRA, 2 x Pollinations

`IMAGE_MIX=base:2,lora:1,pollinations:2` added to `backend/.env` (backup `backend/.env.backup.before_mix_change`)
and made the code default. Live request "Photosynthesis / college / exam" (workstation, RTX 6000 Ada;
`docs/test_run/mix_212/`): `image_sources` = base, base, lora, pollinations, pollinations; `/generate` 27.5 s;
3 SANA images done after 63.6 s; 0 Gemini errors, 0 failed jobs, 0 tracebacks.

**The second Pollinations image failed.** Image 4 arrived (JPEG); image 5 was the "Image generation unavailable"
SVG. Cause, measured with direct requests: Pollinations' free anonymous service answers **HTTP 402 Payment
Required** when new images are requested too quickly. Two uncached requests sent back to back both got 402, as did
requests 5 s, 10 s and 30 s apart; one 20 s after a previous request got 200. It allows roughly one new image every
20-30+ seconds per IP. This is not the proxy timeout, and it cannot be fixed in our code without waiting or using a
paid Pollinations token.

**`backend/.env.example` was found reduced to 8 lines** (only the mixed-mode and proxy settings). The cause was not
found; the file was apparently missing at some point and recreated by later appends. It was rebuilt from the
pre-upgrade backup (`backups/pre_upgrade_20261002_171002.zip`) plus all settings added by the upgrade (35 keys,
Unix line endings, `GEMINI_MODEL=gemini-3.5-flash-lite`). It contains no secrets.
