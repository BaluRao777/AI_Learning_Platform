# Laptop setup (Windows, RTX 2050 4 GB VRAM, 8 GB RAM)

> **Status: not executed.** The upgrade was carried out on the Ubuntu workstation. None of the
> commands on this page have been run on the laptop yet, so nothing here is a measured or
> verified result. The CUDA wheel index below is the standard PyTorch one; check
> https://pytorch.org/get-started/locally/ for the current command before running it.

All commands are PowerShell, run from the project root.

## 1. Python environment

Try the existing env first (Python 3.13):

```powershell
conda activate text_to_image
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r backend\requirements-ai.txt
python -c "import torch, bitsandbytes, diffusers, transformers, accelerate, peft; print(torch.__version__, torch.cuda.is_available())"
```

If any import fails, or `torch.cuda.is_available()` prints `False`, create a separate env:

```powershell
conda create -y -n text_to_image_ai python=3.11
conda activate text_to_image_ai
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
pip install -r backend\requirements-ai.txt
```

Record which of the two paths worked in `docs/UPGRADE_REPORT.md` (section 4).

## 2. Lines to add to `backend\.env`

See section 13 of `docs/UPGRADE_REPORT.md`. Start with the features off
(`ANALYZER_ENABLED=false`, `IMAGE_BACKEND=pollinations`) and confirm the app behaves as before.

## 3. Windows settings (do these yourself)

- Increase the page file to about 16 GB: *System > About > Advanced system settings >
  Performance > Settings > Advanced > Virtual memory > Change*. SANA needed about 9 GB of
  process memory on the workstation, which is more than the laptop's 8 GB of RAM.
- Close browser tabs and other programs before a demo.

## 4. Run

```powershell
# terminal 1
conda activate text_to_image        # or text_to_image_ai
python backend\app.py

# terminal 2
cd frontend
npm start
```

The first run with `ANALYZER_ENABLED=true` or `IMAGE_BACKEND=local` downloads the models
(Qwen about 3 GB, SANA about 12 GB). After that, run truly offline with

```powershell
$env:HF_HUB_OFFLINE = "1"
python backend\app.py
```

## 5. Tests and smoke test

```powershell
cd backend; python -m pytest tests -q; cd ..
python backend\scripts\smoke_local_ai.py --size 512 --offload model
```

The smoke test prints Qwen load and inference time, SANA load time, per-image time, peak VRAM
and peak RAM. Copy those numbers into `docs/UPGRADE_REPORT.md` (section 10).

## 6. Switching the image backend

| `IMAGE_BACKEND` | Behaviour |
|---|---|
| `pollinations` | Original behaviour. No GPU needed. |
| `local` | SANA on the laptop GPU. Set `SANA_LORA_PATH` or `SANA_FUSED_TRANSFORMER_PATH` for the fine-tuned model. |
| `remote` | The workstation renders the images. Set `SANA_REMOTE_URL` and `SANA_REMOTE_TOKEN`. |

## 7. If 512x512 runs out of memory

Try in this order and note what was needed: `SANA_OFFLOAD=sequential` (the app also switches to
this automatically after one out-of-memory error) → `SANA_HEIGHT=384` and `SANA_WIDTH=384` →
`SANA_NUM_IMAGES=3`.

## 8. Phase 6 (fine-tuned model)

1. Copy `pytorch_lora_weights.safetensors` to `backend\models_store\lora\`.
2. In `.env`: `IMAGE_BACKEND=local`, `SANA_LORA_PATH=models_store/lora/pytorch_lora_weights.safetensors`, `SANA_TRIGGER=edudiag`.
3. Run the smoke test again, then generate Earth and Photosynthesis in the 4 combinations:
   `python backend\scripts\capture_responses.py docs\after_phase6 <file containing your JWT>`.
