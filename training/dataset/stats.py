"""Dataset statistics + caption samples, written from the real files.

    python training/dataset/stats.py

Writes docs/dataset/stats.json and docs/dataset/caption_samples.md (50 random captions).
"""
import collections
import csv
import json
import os
import random

from common import DATA_DIR, DATASET_DIR, DOCS_DIR, FILTER_REPORT, read_jsonl


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DATASET_DIR, "manifest.csv"), encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    captions = {}
    for split in ("train", "val", "test"):
        for row in read_jsonl(os.path.join(DATASET_DIR, split, "metadata.jsonl")):
            captions[(split, row["file_name"])] = row["text"]

    def count(key):
        return dict(collections.Counter(row[key] for row in manifest).most_common())

    stats = {
        "total_images": len(manifest),
        "per_source": count("source"),
        "per_license": count("license"),
        "per_complexity": count("complexity"),
        "per_look": count("look"),
        "per_complexity_and_look": dict(collections.Counter(
            f"{row['complexity']} / {row['look']}" for row in manifest).most_common()),
        "per_split": count("split"),
        "filter_report": json.load(open(FILTER_REPORT)),
        "build_report": json.load(open(os.path.join(DATA_DIR, "build_report.json"))),
        "caption_words_mean": round(sum(len(t.split()) for t in captions.values()) / max(1, len(captions)), 1),
    }
    with open(os.path.join(DOCS_DIR, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))

    sample = random.Random(0).sample(manifest, min(50, len(manifest)))
    with open(os.path.join(DOCS_DIR, "caption_samples.md"), "w", encoding="utf-8") as fh:
        fh.write("# Caption samples (50 random images, seed 0)\n\n")
        fh.write("Printed by `training/dataset/stats.py` for manual spot-checking.\n\n")
        fh.write("| # | file | split | source | license | caption |\n|---|---|---|---|---|---|\n")
        for index, row in enumerate(sample, 1):
            text = captions[(row["split"], row["file_name"])].replace("|", "/")
            fh.write(f"| {index} | `{row['file_name']}` | {row['split']} | {row['source']} | {row['license']} | {text} |\n")


if __name__ == "__main__":
    main()
