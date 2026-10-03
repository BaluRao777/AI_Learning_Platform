# Training log: SANA 1.5 education LoRA

Real run on the workstation, 2026-10-02.

| Item | Value |
|---|---|
| Base model | `Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers`, bf16 (not an FP8 checkpoint) |
| Trainer | Official diffusers example `examples/dreambooth/train_dreambooth_lora_sana.py`, tag v0.40.0, run through `training/train_sana_lora_lowmem.py` |
| Command | `MAX_STEPS=4000 bash training/train_lora.sh` |
| Dataset | `training/data/edu_diagrams/train` (3,803 images, 1024x1024, caption column `text`) |
| Resolution / batch / accumulation | 1024 / 4 / 1 |
| LoRA rank / alpha | 32 / 32 |
| Learning rate / schedule | 1e-4, constant with 100 warm-up steps |
| Mixed precision | bf16, gradient checkpointing on |
| Steps | 4,000 (about 4.2 passes over the training split) |
| Checkpoints | every 500 steps (`checkpoint-500` ... `checkpoint-4000`) |
| Seed | 42 |
| Started / finished | 19:44:47 / 21:44:57 (+05:30) |
| Training-loop time | 1 h 58 min 53 s (1.78 s per step, from the progress bar) |
| GPU | NVIDIA RTX 6000 Ada Generation (48 GB), driver 595.84 |
| Libraries | torch 2.14.1+cu130, diffusers 0.40.0, transformers 5.18.0, peft 0.21.2, accelerate 1.15.0 |
| Output adapter | `training/output/sana_edu_lora/pytorch_lora_weights.safetensors`, 34,439,360 bytes |
| Fused transformer | `training/output/sana_edu_fused_transformer/` (3,061 MB); loads and generates; mean absolute pixel difference vs. runtime LoRA 1.41 on a 0-255 scale |

## Loss

From TensorBoard, exported by `training/plot_loss.py` to `docs/training/loss.csv` and `loss_curve.png`:

- mean of the first 50 steps: **0.3858**
- mean of the last 50 steps: **0.3507**
- loss at the final step: **0.4662**

The per-step loss is very noisy (roughly 0.1 to 1.4) and the 50-step running mean stays between about 0.33 and
0.43 for the whole run. **There is no clear downward trend**; the difference between the first and last 50 steps is
within the noise. A flat flow-matching loss is common for LoRA fine-tuning because each step samples a random
noise level, so the loss alone does not show whether the adapter learned something; the validation images and
`docs/eval/EVAL_REPORT.md` do.

## Validation images

`docs/training/validation/step_<N>/` holds four fixed prompts (water cycle; school/learn, school/exam,
college/learn, college/exam) with fixed seeds for step 0 (base model) and every checkpoint, and `step_<N>.jpg`
is the 2x2 sheet. They were generated after training by `training/validate_checkpoints.py`, because the official
script supports only one validation prompt.

## Deviations from the plan

1. **Low-memory wrapper.** The first launch with the unmodified script was killed by the kernel OOM killer
   (the script preloads all images as float32, about 48 GB for this dataset; the machine has 62 GB).
   `train_sana_lora_lowmem.py` keeps the preloaded images as uint8 and applies the same normalisation per item.
   The training loop, model, loss and optimiser are the official ones.
2. **Validation after training** instead of during training (see above).
3. **4,000 steps = 4.2 passes**, slightly below the "5-10 passes" guideline, because the dataset (3,803 training
   images) is larger than the plan's step range assumed.
4. Hyper-parameters were not tuned. Only this one configuration was trained.
