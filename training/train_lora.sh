#!/usr/bin/env bash
# Reproducible SANA 1.5 LoRA fine-tuning run (workstation, conda env `sana_train`).
#
#   bash training/train_lora.sh            # full run
#   MAX_STEPS=20 OUTPUT_NAME=smoke bash training/train_lora.sh   # quick smoke test
#
# Uses the official diffusers example (tag v0.40.0)
#   training/third_party/diffusers/examples/dreambooth/train_dreambooth_lora_sana.py
# through training/train_sana_lora_lowmem.py, which only changes how the preloaded images
# are stored in RAM (uint8 instead of float32); the training loop is the official one.
# Clone it first (see docs/SETUP_WORKSTATION_UBUNTU.md):
#   git clone --depth 1 --branch v0.40.0 https://github.com/huggingface/diffusers.git training/third_party/diffusers
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/train_sana_lora_lowmem.py"

MODEL_ID="${MODEL_ID:-Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers}"
DATASET_DIR="${DATASET_DIR:-$HERE/data/edu_diagrams/train}"
OUTPUT_NAME="${OUTPUT_NAME:-sana_edu_lora}"
OUTPUT_DIR="$HERE/output/$OUTPUT_NAME"
RESOLUTION="${RESOLUTION:-1024}"
RANK="${RANK:-32}"
LR="${LR:-1e-4}"
BATCH_SIZE="${BATCH_SIZE:-4}"
GRAD_ACCUM="${GRAD_ACCUM:-1}"
MAX_STEPS="${MAX_STEPS:-3000}"
CHECKPOINT_STEPS="${CHECKPOINT_STEPS:-500}"
WARMUP_STEPS="${WARMUP_STEPS:-100}"
SEED="${SEED:-42}"

mkdir -p "$OUTPUT_DIR"
{
  echo "date: $(date -Is)"
  echo "command: accelerate launch $SCRIPT (arguments below)"
  echo "model=$MODEL_ID dataset=$DATASET_DIR resolution=$RESOLUTION rank=$RANK lr=$LR batch=$BATCH_SIZE"
  echo "grad_accum=$GRAD_ACCUM max_steps=$MAX_STEPS checkpoint_steps=$CHECKPOINT_STEPS warmup=$WARMUP_STEPS seed=$SEED"
} > "$OUTPUT_DIR/run_config.txt"

# Validation is done after training by training/validate_checkpoints.py (4 fixed
# prompts for every checkpoint); the example script only supports one prompt.
accelerate launch --mixed_precision=bf16 "$SCRIPT" \
  --pretrained_model_name_or_path="$MODEL_ID" \
  --dataset_name="$DATASET_DIR" \
  --image_column="image" \
  --caption_column="text" \
  --instance_prompt="edudiag, educational diagram" \
  --output_dir="$OUTPUT_DIR" \
  --mixed_precision="bf16" \
  --resolution="$RESOLUTION" \
  --center_crop \
  --rank="$RANK" \
  --lora_alpha="$RANK" \
  --learning_rate="$LR" \
  --lr_scheduler="constant_with_warmup" \
  --lr_warmup_steps="$WARMUP_STEPS" \
  --train_batch_size="$BATCH_SIZE" \
  --gradient_accumulation_steps="$GRAD_ACCUM" \
  --gradient_checkpointing \
  --max_train_steps="$MAX_STEPS" \
  --checkpointing_steps="$CHECKPOINT_STEPS" \
  --dataloader_num_workers=4 \
  --seed="$SEED" \
  --report_to="tensorboard" \
  --logging_dir="logs" \
  2>&1 | tee "$OUTPUT_DIR/train.log"
