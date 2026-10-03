"""Build the training dataset from filtered images + VLM captions.

    python training/dataset/build_metadata.py

Output (imagefolder layout understood by the diffusers LoRA script):
    training/data/edu_diagrams/train/*.png + train/metadata.jsonl   (file_name, text)
    training/data/edu_diagrams/val/...  test/...                    (90 / 5 / 5 split, seed 42)
    training/data/edu_diagrams/manifest.csv
        file_name, source, source_url, license, author, complexity, look, split

Images are composited on white, padded to a square (so the trainer's crop never
cuts a diagram) and resized to 1024x1024.

Caption format (identical to inference, see backend/services/image_backends/sana_prompt.py):
    edudiag, {level words}, {look words}, {description}
"""
import csv
import json
import os
import random
import shutil

from PIL import Image

from common import CAPTIONS_JSONL, DATA_DIR, DATASET_DIR, FILTERED_JSONL, raw_image_path, read_jsonl, sana_prompt

RESOLUTION = 1024
SEED = 42
TRIGGER = "edudiag"
SPLITS = (("train", 0.90), ("val", 0.05), ("test", 0.05))
MANIFEST_COLUMNS = ["file_name", "source", "source_url", "license", "author", "complexity", "look", "split"]

Image.MAX_IMAGE_PIXELS = 200_000_000


def to_square(path):
    image = Image.open(path).convert("RGBA")
    image = Image.alpha_composite(Image.new("RGBA", image.size, "white"), image).convert("RGB")
    side = max(image.size)
    canvas = Image.new("RGB", (side, side), "white")
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return canvas.resize((RESOLUTION, RESOLUTION), Image.LANCZOS)


def main():
    captions = {row["file_name"]: row for row in read_jsonl(CAPTIONS_JSONL)}
    dropped = {"no_caption": 0, "caption_failed": 0, "not_educational_diagram": 0, "photo_of_people": 0}
    rows = []
    for record in read_jsonl(FILTERED_JSONL):
        caption = captions.get(record["file_name"])
        if caption is None:
            dropped["no_caption"] += 1
        elif not caption["ok"]:
            dropped["caption_failed"] += 1
        elif caption["has_photo_of_people"]:
            dropped["photo_of_people"] += 1
        elif not caption["is_educational_diagram"]:
            dropped["not_educational_diagram"] += 1
        else:
            rows.append({**record, **caption})

    rows.sort(key=lambda r: r["file_name"])
    random.Random(SEED).shuffle(rows)
    n_val = n_test = round(len(rows) * 0.05)
    bounds = {"val": (0, n_val), "test": (n_val, n_val + n_test), "train": (n_val + n_test, len(rows))}

    if os.path.isdir(DATASET_DIR):
        shutil.rmtree(DATASET_DIR)
    manifest = []
    for split, (start, end) in bounds.items():
        split_dir = os.path.join(DATASET_DIR, split)
        os.makedirs(split_dir)
        with open(os.path.join(split_dir, "metadata.jsonl"), "w", encoding="utf-8") as meta:
            for row in rows[start:end]:
                file_name = os.path.splitext(row["file_name"])[0] + ".png"
                to_square(raw_image_path(row)).save(os.path.join(split_dir, file_name))
                text = sana_prompt.build_caption(row["description"], row["complexity"], row["look"], TRIGGER)
                meta.write(json.dumps({"file_name": file_name, "text": text}, ensure_ascii=False) + "\n")
                manifest.append({**{k: row.get(k, "") for k in MANIFEST_COLUMNS}, "file_name": file_name, "split": split})

    with open(os.path.join(DATASET_DIR, "manifest.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest)
    with open(os.path.join(DATA_DIR, "build_report.json"), "w", encoding="utf-8") as fh:
        json.dump({"kept": len(rows), "dropped": dropped,
                   "splits": {s: e - b for s, (b, e) in bounds.items()}}, fh, indent=2)
    print("kept", len(rows), "dropped", dropped, {s: e - b for s, (b, e) in bounds.items()})


if __name__ == "__main__":
    main()
