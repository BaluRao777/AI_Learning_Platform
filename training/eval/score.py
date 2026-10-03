"""CLIP text-image similarity, timing table and side-by-side grids for the evaluation.

    python training/eval/score.py

CLIP model: openai/clip-vit-large-patch14. Both models are scored against the same
text: the prompt WITHOUT the trigger word. Prompts longer than CLIP's 77 tokens are truncated.
Output: docs/eval/results.json, docs/eval/grids/*.jpg
"""
import json
import os
import statistics
import sys

import torch
from PIL import Image, ImageDraw
from transformers import CLIPModel, CLIPProcessor

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EVAL_DIR))

from common import DOCS_DIR  # noqa: E402

CLIP_ID = "openai/clip-vit-large-patch14"
CELL = 384


def mean_std(values):
    return {"mean": round(statistics.mean(values), 4), "std": round(statistics.stdev(values), 4), "n": len(values)}


def main():
    prompts = json.load(open(os.path.join(EVAL_DIR, "prompts.json")))
    out_root = os.path.join(EVAL_DIR, "outputs")
    timings = json.load(open(os.path.join(out_root, "timings.json")))
    sizes = sorted({int(k.split("_")[1]) for k in timings}, reverse=True)

    model = CLIPModel.from_pretrained(CLIP_ID).to("cuda").eval()
    processor = CLIPProcessor.from_pretrained(CLIP_ID)

    def clip_scores(folder):
        scores = []
        for start in range(0, len(prompts), 16):
            batch = prompts[start: start + 16]
            images = [Image.open(os.path.join(folder, f"{p['id']:03d}.png")).convert("RGB") for p in batch]
            inputs = processor(text=[p["prompt"] for p in batch], images=images, return_tensors="pt",
                               padding=True, truncation=True, max_length=77).to("cuda")
            with torch.no_grad():
                out = model(**inputs)
            image_embeds = torch.nn.functional.normalize(out.image_embeds, dim=-1)
            text_embeds = torch.nn.functional.normalize(out.text_embeds, dim=-1)
            scores += (image_embeds * text_embeds).sum(-1).tolist()
        return scores

    results = {"clip_model": CLIP_ID, "num_prompts": len(prompts), "by_size": {}}
    for size in sizes:
        base = clip_scores(os.path.join(out_root, f"base_{size}"))
        lora = clip_scores(os.path.join(out_root, f"lora_{size}"))
        diffs = [l - b for b, l in zip(base, lora)]
        entry = {
            "clip_base": mean_std(base),
            "clip_lora": mean_std(lora),
            "clip_diff_lora_minus_base": mean_std(diffs),
            "lora_better_count": sum(d > 0 for d in diffs),
            "seconds_per_image_base": mean_std(timings[f"base_{size}"]["seconds"]),
            "seconds_per_image_lora": mean_std(timings[f"lora_{size}"]["seconds"]),
            "peak_vram_mb_base": timings[f"base_{size}"]["peak_vram_mb"],
            "peak_vram_mb_lora": timings[f"lora_{size}"]["peak_vram_mb"],
            "by_combination": {},
            "per_prompt": [
                {"id": p["id"], "topic": p["topic"], "level": p["level"], "mode": p["mode"],
                 "clip_base": round(b, 4), "clip_lora": round(l, 4)}
                for p, b, l in zip(prompts, base, lora)
            ],
        }
        for level, mode in sorted({(p["level"], p["mode"]) for p in prompts}):
            idx = [i for i, p in enumerate(prompts) if (p["level"], p["mode"]) == (level, mode)]
            entry["by_combination"][f"{level}/{mode}"] = {
                "clip_base": mean_std([base[i] for i in idx]), "clip_lora": mean_std([lora[i] for i in idx])}
        results["by_size"][str(size)] = entry
        print(size, entry["clip_base"], entry["clip_lora"], "lora better on", entry["lora_better_count"])

        # One grid per topic: rows = 4 combinations, columns = base | LoRA. Every prompt is shown.
        grids_dir = os.path.join(DOCS_DIR, "eval", "grids")
        os.makedirs(grids_dir, exist_ok=True)
        topics = list(dict.fromkeys(p["topic"] for p in prompts))
        for topic in topics:
            rows = [p for p in prompts if p["topic"] == topic]
            header = 28
            grid = Image.new("RGB", (CELL * 2, header + (CELL + header) * len(rows)), "white")
            draw = ImageDraw.Draw(grid)
            draw.text((8, 8), f"{topic}  |  left: base SANA 1.5   right: + edu LoRA   ({size}px)", fill="black")
            for r, p in enumerate(rows):
                top = header + r * (CELL + header)
                draw.text((8, top + 8), f"{p['level']} / {p['mode']}   CLIP base {base[p['id']]:.3f}  LoRA {lora[p['id']]:.3f}", fill="black")
                for c, name in enumerate(("base", "lora")):
                    image = Image.open(os.path.join(out_root, f"{name}_{size}", f"{p['id']:03d}.png")).convert("RGB")
                    grid.paste(image.resize((CELL, CELL), Image.LANCZOS), (c * CELL, top + header))
            name = topic.lower().replace(" ", "_")
            grid.save(os.path.join(grids_dir, f"{name}_{size}.jpg"), quality=88)

    with open(os.path.join(DOCS_DIR, "eval", "results.json"), "w") as fh:
        json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
