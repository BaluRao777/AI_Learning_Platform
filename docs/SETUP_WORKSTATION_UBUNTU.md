# Workstation setup (Ubuntu 24.04, RTX 6000 Ada 48 GB)

Every command below was run on the workstation during the upgrade unless marked otherwise.
Run them from the project root.

## 1. Environment

```bash
conda create -y -n sana_train python=3.11
conda activate sana_train
pip install torch torchvision          # installed torch 2.14.1+cu130 (driver 595.84)
pip install -r requirements.txt        # original backend requirements (Flask etc.)
pip install diffusers transformers accelerate peft bitsandbytes datasets pillow tensorboard \
            sentencepiece protobuf safetensors imagehash psutil pytest matplotlib huggingface_hub ftfy
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Versions used: diffusers 0.40.0, transformers 5.18.0, peft 0.21.2, accelerate 1.15.0, bitsandbytes 0.50.2.

The official training example is not in the pip package; clone the matching tag:

```bash
git clone --depth 1 --branch v0.40.0 https://github.com/huggingface/diffusers.git training/third_party/diffusers
```

## 2. Tests and smoke test

```bash
cd backend && python -m pytest tests -q && cd ..
python backend/scripts/smoke_local_ai.py --size 512 --offload model
```

## 3. Dataset (Phase 3)

```bash
python training/dataset/download_ai2d.py        # AI2D from the official AI2 S3 bucket (~1 GB)
python training/dataset/download_wikimedia.py   # licence-filtered Commons diagrams (slow: rate limited)
python training/dataset/filter.py               # size / aspect / duplicate / corrupt filter
python training/dataset/caption.py              # Qwen2.5-VL-7B captions + tags (resumable)
python training/dataset/build_metadata.py       # 1024x1024 images, metadata.jsonl, manifest.csv, 90/5/5 split
python training/dataset/stats.py                # docs/dataset/stats.json + caption_samples.md
```

## 4. LoRA training (Phase 4)

```bash
bash training/train_lora.sh                     # writes training/output/sana_edu_lora/
python training/plot_loss.py                    # docs/training/loss_curve.png + loss.csv
python training/validate_checkpoints.py         # docs/training/validation/step_*/
python training/fuse_lora.py                    # optional fused transformer for the laptop
tensorboard --logdir training/output/sana_edu_lora/logs
```

Hyper-parameters are environment variables of `train_lora.sh` (`RANK`, `LR`, `BATCH_SIZE`,
`MAX_STEPS`, ...). The exact values of a run are saved to `run_config.txt` in the output folder.

## 5. Evaluation (Phase 5)

```bash
python training/eval/build_prompts.py           # 80 prompts
python training/eval/generate.py                # base vs LoRA at 1024 and 512, same seeds
python training/eval/score.py                   # CLIP scores, timings, docs/eval/grids/
```

## 6. Image server for the laptop (remote mode)

```bash
cd backend
export SANA_REMOTE_TOKEN="<choose a long random secret>"
# optional: serve the fine-tuned model
export SANA_LORA_PATH="$(pwd)/../training/output/sana_edu_lora/pytorch_lora_weights.safetensors"
python image_server/sana_server.py              # listens on 0.0.0.0:7860
```

- Find the workstation's LAN address: `hostname -I` (or `ip -4 addr show`).
- Check from the laptop: open `http://<workstation-ip>:7860/health`.
- Firewall: if `ufw` is active, allow the port for the local network only, for example
  `sudo ufw allow from 192.168.1.0/24 to any port 7860 proto tcp` (run by the owner; not run during the upgrade).
- The server is plain HTTP protected only by the shared token. Use it on a trusted LAN only.
- On the laptop set `IMAGE_BACKEND=remote`, `SANA_REMOTE_URL=http://<workstation-ip>:7860`,
  `SANA_REMOTE_TOKEN=<same secret>`.

During the upgrade remote mode was tested on the workstation itself (backend and image
server on the same machine over 127.0.0.1). It was not tested from the laptop over the LAN.

## 7. What to copy to the laptop

Copy the project folder without `frontend/node_modules/`, `backend/generated_images/`,
`backend/.env`, `training/data/`, `training/third_party/` and model caches. For Phase 6 copy

```
training/output/sana_edu_lora/pytorch_lora_weights.safetensors  ->  backend/models_store/lora/
training/output/sana_edu_fused_transformer/                     ->  backend/models_store/fused/   (optional)
```
