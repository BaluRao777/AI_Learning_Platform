"""Filter raw images: corrupt files, small images, extreme aspect ratios, duplicates.

    python training/dataset/filter.py

Reads   training/data/raw/<source>/records.jsonl
Writes  training/data/filtered.jsonl  and  training/data/filter_report.json

"Photos of people" and non-diagram images cannot be detected reliably with
simple image statistics, so they are flagged by the vision-language model in
caption.py and dropped in build_metadata.py.
"""
import collections
import json
import os

import imagehash
from PIL import Image

from common import FILTER_REPORT, FILTERED_JSONL, RAW_DIR, SOURCES, raw_image_path, read_jsonl, write_jsonl

MIN_SIDE = 512
MAX_ASPECT = 3.0
PHASH_DISTANCE = 4  # perceptual hashes within this Hamming distance are duplicates

Image.MAX_IMAGE_PIXELS = 200_000_000


def main():
    kept, hashes = [], []
    report = collections.defaultdict(collections.Counter)
    for source in SOURCES:
        for record in read_jsonl(os.path.join(RAW_DIR, source, "records.jsonl")):
            counter = report[source]
            counter["raw"] += 1
            path = raw_image_path(record)
            try:
                with Image.open(path) as image:
                    image.load()
                    width, height = image.size
                    phash = imagehash.phash(image.convert("RGB"))
            except Exception:
                counter["dropped_corrupt"] += 1
                continue
            if min(width, height) < MIN_SIDE:
                counter["dropped_small"] += 1
                continue
            if max(width, height) / min(width, height) > MAX_ASPECT:
                counter["dropped_aspect"] += 1
                continue
            if any(phash - other <= PHASH_DISTANCE for other in hashes):
                counter["dropped_duplicate"] += 1
                continue
            hashes.append(phash)
            counter["kept"] += 1
            kept.append({**record, "width": width, "height": height, "phash": str(phash)})
    write_jsonl(FILTERED_JSONL, kept)
    summary = {source: dict(counter) for source, counter in report.items()}
    summary["total_kept"] = len(kept)
    summary["settings"] = {"min_side": MIN_SIDE, "max_aspect": MAX_ASPECT, "phash_distance": PHASH_DISTANCE}
    with open(FILTER_REPORT, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
