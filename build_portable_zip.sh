#!/usr/bin/env bash
# Builds ../text_to_image_portable.zip: the whole project + bundled models, without secrets,
# database, caches or training data. Run on a machine that has the models in its Hugging Face cache.
#   bash build_portable_zip.sh
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$(dirname "$SRC")"
STAGE="$OUT_DIR/portable_build/text_to_image"
ZIP="$OUT_DIR/text_to_image_portable.zip"
HF="${HF_HOME:-$HOME/.cache/huggingface}/hub"

snapshot() {  # newest snapshot folder of a cached model
  ls -dt "$HF/models--$1/snapshots/"*/ | head -1
}

rm -rf "$OUT_DIR/portable_build"
mkdir -p "$STAGE"
# Excludes starting with "/" only match at the project root.
rsync -a \
  --exclude '/backend/.env' --exclude '/backend/.env.backup*' --exclude '/backend/database/*.db' \
  --exclude '/backend/generated_images/' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '*.pyc' \
  --exclude '/backups/' --exclude '/training/data/' --exclude '/training/output/' --exclude '/training/third_party/' \
  --exclude '/training/eval/outputs/' --exclude '/frontend/build/' --exclude '/frontend/.git/' \
  --exclude '/frontend/node_modules/.cache/' --exclude '/.venv/' --exclude '/models/' \
  --exclude '/setup_report.txt' --exclude '/RUN_COMMANDS.txt' --exclude '/setup_result.json' --exclude '/smoke.png' \
  "$SRC/" "$STAGE/"

mkdir -p "$STAGE/models"
# Symlinks to the cached files; zip follows them, so the archive holds plain files (works on Windows).
cp -rs "$(snapshot Qwen--Qwen2.5-1.5B-Instruct)" "$STAGE/models/Qwen2.5-1.5B-Instruct"
cp -rs "$(snapshot Efficient-Large-Model--SANA1.5_1.6B_1024px_diffusers)" "$STAGE/models/SANA1.5_1.6B_1024px_diffusers"
test -f "$STAGE/backend/models_store/lora/pytorch_lora_weights.safetensors"

rm -f "$ZIP"
(cd "$OUT_DIR/portable_build" && zip -q -r -n .safetensors:.png:.jpg:.jpeg:.mp4:.zip "$ZIP" text_to_image)
ls -lh "$ZIP"
