"""Download AI2D (AI2 Diagrams) from the official AI2 public S3 bucket. Resumable.

Source : https://registry.opendata.aws/allenai-diagrams/  (s3://ai2-public-datasets/diagrams/ai2d-all.zip)
License: CC BY-SA (as stated on the AWS Open Data registry page, checked 2026-10-02)
Paper  : Kembhavi et al., "A Diagram Is Worth A Dozen Images", 2016

Output : training/data/raw/ai2d/images/*.png  +  training/data/raw/ai2d/records.jsonl
"""
import json
import os
import zipfile

import requests

URL = "https://ai2-public-datasets.s3.us-west-2.amazonaws.com/diagrams/ai2d-all.zip"
SOURCE_PAGE = "https://registry.opendata.aws/allenai-diagrams/"
LICENSE = "CC BY-SA"
AUTHOR = "Allen Institute for AI (AI2D; Kembhavi et al. 2016)"

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "ai2d")
ZIP_PATH = os.path.join(ROOT, "ai2d-all.zip")
IMAGES_DIR = os.path.join(ROOT, "images")


def download():
    os.makedirs(ROOT, exist_ok=True)
    total = int(requests.head(URL, timeout=30).headers["Content-Length"])
    have = os.path.getsize(ZIP_PATH) if os.path.exists(ZIP_PATH) else 0
    if have == total:
        print("zip already downloaded")
        return
    headers = {"Range": f"bytes={have}-"} if have else {}
    with requests.get(URL, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        mode = "ab" if have and resp.status_code == 206 else "wb"
        with open(ZIP_PATH, mode) as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    print("downloaded", os.path.getsize(ZIP_PATH), "of", total, "bytes")


def extract():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    records = []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        for name in sorted(archive.namelist()):
            parts = name.split("/")
            if "__MACOSX" in parts or parts[-1].startswith("._"):
                continue
            if len(parts) < 2 or parts[-2] != "images" or not name.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            file_name = f"ai2d_{parts[-1]}"
            target = os.path.join(IMAGES_DIR, file_name)
            if not os.path.exists(target):
                with archive.open(name) as src, open(target, "wb") as dst:
                    dst.write(src.read())
            records.append({
                "file_name": file_name,
                "source": "ai2d",
                "source_url": SOURCE_PAGE,
                "license": LICENSE,
                "author": AUTHOR,
            })
    with open(os.path.join(ROOT, "records.jsonl"), "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
    print("images:", len(records))


if __name__ == "__main__":
    download()
    extract()
