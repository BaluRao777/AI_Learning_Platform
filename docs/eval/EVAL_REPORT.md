# Evaluation report: base SANA 1.5 vs. SANA 1.5 + education LoRA

All numbers are copied from `docs/eval/results.json`, produced by `training/eval/score.py` on the workstation
(RTX 6000 Ada, bf16, no offload) on 2026-10-02. Nothing was cherry-picked: every one of the 80 prompts is
scored and every one appears in the grids.

## Result in one line

**The fine-tuned LoRA is worse than the base model on this evaluation**, both by CLIP score and by eye. It should not be
deployed as it is; the base model (empty `SANA_LORA_PATH`) gives better images.

## Setup

- 20 topics x 4 level/mode combinations = 80 prompts (`training/eval/prompts.json`), built with the app's prompt code.
- Same seed, 20 steps, guidance 4.5, same negative prompt for both models. The LoRA prompt additionally starts with the trigger word `edudiag`.
- LoRA: `training/output/sana_edu_lora/pytorch_lora_weights.safetensors` (step 4000, scale 1.0).
- CLIP: `openai/clip-vit-large-patch14`, cosine similarity between the image and the prompt without the trigger word. Prompts longer than 77 tokens are truncated by CLIP.
- The topics were written for the evaluation; they are common school-science subjects, so similar diagrams exist in the training set. They are not held out in a strict sense.

## CLIP text-image similarity (mean ± std over 80 prompts, higher is better)

| Resolution | Base | LoRA | LoRA − base (paired) | Prompts where LoRA scored higher |
|---|---|---|---|---|
| 1024 x 1024 | 0.2762 ± 0.0327 | 0.2545 ± 0.0412 | -0.0217 ± 0.0453 | 24 of 80 |
| 512 x 512 | 0.2515 ± 0.0395 | 0.2087 ± 0.0465 | -0.0428 ± 0.0497 | 12 of 80 |

### By level / mode (n = 20 each)

**1024 x 1024**

| level / mode | Base | LoRA |
|---|---|---|
| college/exam | 0.2662 ± 0.0340 | 0.2491 ± 0.0423 |
| college/learn | 0.2749 ± 0.0281 | 0.2545 ± 0.0384 |
| school/exam | 0.2682 ± 0.0294 | 0.2651 ± 0.0382 |
| school/learn | 0.2955 ± 0.0327 | 0.2493 ± 0.0465 |

**512 x 512**

| level / mode | Base | LoRA |
|---|---|---|
| college/exam | 0.2438 ± 0.0371 | 0.2183 ± 0.0395 |
| college/learn | 0.2609 ± 0.0387 | 0.2025 ± 0.0437 |
| school/exam | 0.2398 ± 0.0484 | 0.2034 ± 0.0574 |
| school/learn | 0.2617 ± 0.0292 | 0.2108 ± 0.0453 |

## Generation time on the workstation (seconds per image, 20 steps, mean ± std over 80 images)

| Resolution | Base | LoRA | Peak VRAM base (MB) | Peak VRAM LoRA (MB) |
|---|---|---|---|---|
| 1024 x 1024 | 2.04 ± 0.03 | 2.12 ± 0.07 | 9158 | 9192 |
| 512 x 512 | 0.60 ± 0.12 | 0.77 ± 0.18 | 9153 | 9186 |

Times exclude model loading and one warm-up image. These are workstation numbers, not laptop numbers.

## Largest differences per prompt (1024 x 1024)

| | topic | level / mode | base | LoRA |
|---|---|---|---|---|
| LoRA worst | Greenhouse effect | school / learn | 0.282 | 0.122 |
| LoRA worst | Rock cycle | school / learn | 0.331 | 0.191 |
| LoRA worst | Plate tectonics | school / learn | 0.331 | 0.201 |
| LoRA worst | Food chain | school / learn | 0.355 | 0.229 |
| LoRA worst | Greenhouse effect | college / exam | 0.270 | 0.162 |
| LoRA best | Neuron | college / exam | 0.203 | 0.272 |
| LoRA best | Plate tectonics | school / exam | 0.222 | 0.278 |
| LoRA best | Greenhouse effect | school / exam | 0.258 | 0.305 |
| LoRA best | Atom structure | college / learn | 0.244 | 0.290 |
| LoRA best | Solar system | school / exam | 0.279 | 0.324 |

## Grids

`docs/eval/grids/<topic>_<size>.jpg`: one file per topic and resolution (40 files). Rows are the four combinations,
left column base, right column LoRA, with each image's CLIP score printed above it.

## Observations from looking at the grids

These are from viewing `water_cycle_1024.jpg`, `human_heart_512.jpg` and the checkpoint validation sheets, not from all 40 grids.

- **Base model:** clean, colourful flat illustrations in which the subject is recognisable (a heart looks like a heart, the water-cycle images show sea, mountains and clouds). It often adds blocks of unreadable pseudo-text.
- **LoRA:** images look more like sparse textbook line diagrams on white, with leader lines and label-like marks, which is the style of the training data. But the subject is frequently lost or reduced to small fragments, and the labels are unreadable gibberish. In the heart grid at 512 px, none of the four LoRA images shows a recognisable heart.
- **512 px is worse than 1024 px for both models, and much worse for the LoRA** (trained only at 1024 px). The laptop default is 512 px, so the LoRA is weakest exactly where the laptop would use it.
- The LoRA did learn the *layout* of labelled diagrams, so the style change is real; the content fidelity dropped.

## Likely causes (not verified by experiments)

- The training loss did not decrease in a clear way (see `docs/training/TRAINING_LOG.md`), so 4,000 steps at rank 32 mainly shifted the style.
- Almost all training diagrams contain text labels, which SANA cannot reproduce, so the model learned to draw label-like noise.
- Captions are machine-written and partly inaccurate, and many training images are complex figures that a one-sentence caption cannot describe.

## What to try next (not done)

- Use the base model for the demo, or try a lower `SANA_LORA_SCALE` (for example 0.4-0.6) or an earlier checkpoint (`checkpoint-500` to `checkpoint-1500`) and re-run this evaluation.
- Train on a cleaner subset: images with little or no text, hand-checked captions, and a balanced set of looks.
- Add 512 px training if the laptop keeps generating at 512 px.
- CLIP measures prompt agreement, not teaching quality or style. A small human rating would be a better final measure.
