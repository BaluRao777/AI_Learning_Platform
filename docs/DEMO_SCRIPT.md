# 5-minute review demo

Prepare before the review: backend and frontend running, logged in, one browser tab on `/home`,
one terminal ready for the `/analyze` call, and the files below open in an image viewer.
Models should already be downloaded (`HF_HUB_OFFLINE=1`).

> The text part of the demo (steps 1 and 2) needs a working Gemini key. With the key that was in
> `backend/.env` during the upgrade, Gemini calls failed and every answer came from the Wikipedia
> fallback, which is the same for all four combinations. Fix the key first (see
> `docs/UPGRADE_REPORT.md`, section "Blockers").

## 0:00 – The problem (30 s)

Open `docs/after_phase1/COMPARISON.md`. Point at the baseline column: before the upgrade,
`mode` was never sent to the text model, so the four level/mode combinations gave the same answer.

## 0:30 – Same topic, four combinations (90 s)

In the UI generate **Photosynthesis** as school/learn, then college/exam.
Show the explanation text of both, and the images appearing one by one
("Generating image…" placeholder first, then the picture) without reloading the page.

## 2:00 – The Input Analysis Layer (60 s)

Show the plan the local Qwen model produced for a request:

```bash
TOKEN=<JWT from the browser's localStorage "token">
curl -s -X POST http://127.0.0.1:5000/analyze \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"topic":"Photosynthesis","level":"college","mode":"exam"}' | python -m json.tool
```

Point at `source` (`qwen` or `rules`), `depth`, `must_include`, `exam_focus`, `image_style`
and `analysis_ms`. Explain: this plan is what the Gemini prompt is built from, and if Qwen
fails the rule-based plan is used, so the request never fails.

## 3:00 – The fine-tuned image model (75 s)

- `docs/eval/grids/*.jpg`: left column base SANA 1.5, right column with the education LoRA,
  same prompt and seed. Show two or three topics, including one where the LoRA is not better.
- `docs/training/loss_curve.png`: the training loss.
- `docs/training/validation/step_*.jpg`: the same four prompts at each checkpoint.

## 4:15 – Numbers and limits (45 s)

Open `docs/eval/EVAL_REPORT.md` (CLIP table, time per image) and `docs/dataset/DATASET_CARD.md`
(sources and licences). State the limits plainly: the image model cannot write readable labels,
and the laptop runs one model at a time because of its 4 GB of VRAM.
