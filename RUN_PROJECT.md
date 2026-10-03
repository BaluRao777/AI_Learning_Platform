# RUN_PROJECT — how to set up and run this project on another system

Follow the steps in order. Commands are given for **Windows (PowerShell)** and **Linux (bash)**.
Run everything from the project root (the folder that contains `backend/` and `frontend/`).

> The Linux commands were run on the workstation during the upgrade. The Windows commands
> have **not** been run yet; if one fails, note the error.

---

## What is in the zip, and what is not

Included: all source code (`backend/`, `frontend/src`, `frontend/public`, `training/` scripts), `docs/`, this file.

**Not included – you must handle these yourself:**

| Not in the zip | What to do on the new system |
|---|---|
| `backend/.env` (contains your Gemini key) | Copy it by hand, or create it from `backend/.env.example` (Step 3) |
| `backend/database/app.db` (user accounts, history) | Create a fresh one with `python init_db.py` (Step 4), or copy the file by hand to keep old accounts |
| `frontend/node_modules/` | `npm install` (Step 5) |
| AI model weights (Qwen ~3 GB, SANA ~12 GB) | Downloaded automatically on first use (needs internet once) |
| Fine-tuned LoRA (`pytorch_lora_weights.safetensors`, 34 MB) | Optional, and currently **not recommended** (it scored worse than the base model). See Step 9 |
| Training dataset, training outputs, generated images | Stay on the workstation |

---

## Step 1 — Install the prerequisites (once)

- Python 3.11 (via Miniconda/Anaconda is easiest)
- Node.js LTS (includes npm)
- Only for local AI: an NVIDIA GPU with an up-to-date driver

Check:

```
python --version
node -v
npm -v
nvidia-smi
```

## Step 2 — Unzip and create the Python environment

**Windows (PowerShell)**

```powershell
Expand-Archive text_to_image_project.zip -DestinationPath .
cd text_to_image
conda create -y -n text_to_image_ai python=3.11
conda activate text_to_image_ai
pip install -r requirements.txt
```

**Linux**

```bash
unzip text_to_image_project.zip
cd text_to_image
conda create -y -n text_to_image_ai python=3.11
conda activate text_to_image_ai
pip install -r requirements.txt
```

This is enough to run the app in its original mode (Gemini text + Pollinations images).

## Step 3 — Create `backend/.env`

Copy your old `.env` into `backend/`, **or** create it:

**Windows:** `Copy-Item backend\.env.example backend\.env`
**Linux:** `cp backend/.env.example backend/.env`

Then open `backend/.env` and fill in at least:

```ini
GEMINI_API_KEY=your_key_here
JWT_SECRET=any_long_random_text
CORS_ORIGINS=http://localhost:3000
```

For the first run keep the new features **off**:

```ini
ANALYZER_ENABLED=false
IMAGE_BACKEND=pollinations
```

> **Important:** during the upgrade the Gemini key failed (404 for `gemini-2.5-flash-lite`,
> 403 "project has been denied access" for `gemini-3.5-flash-lite`). Until you have a working
> key, explanations come from the Wikipedia fallback and are the same for every level/mode.
> With a working key, also try `GEMINI_MODEL=gemini-3.5-flash-lite` (suggested by Google's
> error message; not verified).

## Step 4 — Create the database (skip if you copied `app.db`)

```
cd backend
python init_db.py
cd ..
```

## Step 5 — Install the frontend packages

```
cd frontend
npm install
cd ..
```

If the backend is not on `http://127.0.0.1:5000`, create `frontend/.env.local` containing
`REACT_APP_API_BASE_URL=http://<backend-address>:5000`.

## Step 6 — Run the project (two terminals)

**Terminal 1 – backend**

```
conda activate text_to_image_ai
cd backend
python app.py
```

Wait for `Running on http://127.0.0.1:5000`. Check: open http://127.0.0.1:5000 → `{"message": "Backend is running"}`.

**Terminal 2 – frontend**

```
cd frontend
npm start
```

The app opens at http://localhost:3000. Sign up, log in, enter a topic, generate.

**If this works, the basic project is running.** Steps 7–10 are optional.

---

## Step 7 — (Optional) Run the tests

```
conda activate text_to_image_ai
pip install pytest pillow
cd backend
python -m pytest tests -q
cd ..
```

Expected: `54 passed`. No GPU or Gemini key is needed.

## Step 8 — (Optional) Turn on the local AI features (needs an NVIDIA GPU)

Install a CUDA build of PyTorch first, then the AI packages:

**Windows**

```powershell
conda activate text_to_image_ai
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r backend\requirements-ai.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

**Linux**

```bash
conda activate text_to_image_ai
pip install torch
pip install -r backend/requirements-ai.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

The last line must print `True`. If it prints `False`, stop here and keep using Step 6.

Run the GPU smoke test (downloads the models the first time, about 15 GB):

```
python backend/scripts/smoke_local_ai.py --size 512 --offload model
```

It prints a teaching plan, saves `smoke.png`, and prints load time, time per image, peak VRAM and
peak RAM. **Write these numbers down** – they are the laptop measurements still missing from
`docs/UPGRADE_REPORT.md` (sections 4 and 10).

Then change these lines in `backend/.env` and restart the backend (Step 6):

```ini
ANALYZER_ENABLED=true
QWEN_LOAD_IN_4BIT=true
QWEN_UNLOAD_AFTER_USE=true

IMAGE_BACKEND=local
SANA_TEXT_ENCODER_4BIT=true
SANA_OFFLOAD=model
SANA_HEIGHT=512
SANA_WIDTH=512
SANA_STEPS=20
SANA_NUM_IMAGES=5
SANA_LORA_PATH=
```

After the first successful run you can work without internet:

- Windows: `$env:HF_HUB_OFFLINE = "1"; python app.py`
- Linux: `HF_HUB_OFFLINE=1 python app.py`

**On a 4 GB VRAM / 8 GB RAM laptop:**

- Increase the Windows page file to about 16 GB (System → About → Advanced system settings →
  Performance → Settings → Advanced → Virtual memory). SANA used about 9 GB of RAM on the workstation.
- Close browser tabs and other programs.
- If it runs out of memory, try in this order: `SANA_OFFLOAD=sequential` → `SANA_HEIGHT=384` and
  `SANA_WIDTH=384` → `SANA_NUM_IMAGES=3`.

## Step 9 — (Optional) Use the fine-tuned LoRA

Not recommended at the moment: in the evaluation it scored below the base model
(`docs/eval/EVAL_REPORT.md`). To try it anyway:

1. Copy from the workstation
   `training/output/sana_edu_lora/pytorch_lora_weights.safetensors`
   to `backend/models_store/lora/pytorch_lora_weights.safetensors` on this system.
2. In `backend/.env`:

```ini
IMAGE_BACKEND=local
SANA_LORA_PATH=models_store/lora/pytorch_lora_weights.safetensors
SANA_LORA_SCALE=1.0
SANA_TRIGGER=edudiag
```

3. Restart the backend. A lower `SANA_LORA_SCALE` (0.4–0.6) may look better; this was not tested.

## Step 10 — (Optional) Let the workstation generate the images (remote mode)

**On the workstation** (same network):

```bash
conda activate sana_train
cd backend
export SANA_REMOTE_TOKEN="choose-a-long-secret"
python image_server/sana_server.py          # port 7860
hostname -I                                  # shows the workstation's IP address
```

**On this system**, in `backend/.env`:

```ini
IMAGE_BACKEND=remote
SANA_REMOTE_URL=http://<workstation-ip>:7860
SANA_REMOTE_TOKEN=choose-a-long-secret
```

Check the connection by opening `http://<workstation-ip>:7860/health` in a browser, then restart the
backend. No GPU is needed on this system in remote mode. (Remote mode was tested only on the
workstation itself, not across the network.)

---

## Quick reference — all run commands

| Task | Command (from the project root) |
|---|---|
| Activate environment | `conda activate text_to_image_ai` |
| Create database | `cd backend` then `python init_db.py` |
| Start backend | `cd backend` then `python app.py` |
| Start frontend | `cd frontend` then `npm start` |
| Run tests | `cd backend` then `python -m pytest tests -q` |
| GPU smoke test | `python backend/scripts/smoke_local_ai.py --size 512 --offload model` |
| Show a teaching plan | `POST http://127.0.0.1:5000/analyze` with a JWT (see `docs/DEMO_SCRIPT.md`) |
| Save 8 evidence responses | `python backend/scripts/capture_responses.py docs/after_phase6 <file with your JWT>` |
| Rebuild the before/after comparison | `python backend/scripts/make_comparison.py` |
| Start image server (workstation) | `cd backend` then `SANA_REMOTE_TOKEN=... python image_server/sana_server.py` |

Switching modes = edit `backend/.env`, then restart the backend:

| Mode | `.env` |
|---|---|
| Original behaviour | `ANALYZER_ENABLED=false`, `IMAGE_BACKEND=pollinations` |
| Local Qwen analysis | `ANALYZER_ENABLED=true` |
| Local images | `IMAGE_BACKEND=local` |
| Images from the workstation | `IMAGE_BACKEND=remote` + `SANA_REMOTE_URL` + `SANA_REMOTE_TOKEN` |

## Common problems

| Problem | Fix |
|---|---|
| Explanations are the same for every level/mode | Gemini is failing; fix the key / `GEMINI_MODEL` (Step 3) |
| `Too many requests` | Wait a minute (30 requests per minute per IP) |
| Login fails after moving systems | The database is new: sign up again, or copy `app.db` |
| Frontend shows "Network Error" | Backend not running, or `REACT_APP_API_BASE_URL` is wrong |
| Images stay on "Generating image…" | Look at the backend terminal for `IMAGE JOB failed ...` |
| `torch.cuda.is_available()` is `False` | Wrong torch build or driver; reinstall torch with the CUDA index URL |
| First local-AI run is very slow | It is downloading about 15 GB of models; later runs are fast |

More detail: `docs/UPGRADE_REPORT.md`, `docs/SETUP_LAPTOP_WINDOWS.md`, `docs/SETUP_WORKSTATION_UBUNTU.md`, `docs/ARCHITECTURE.md`.
