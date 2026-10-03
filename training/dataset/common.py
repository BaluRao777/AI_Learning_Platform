"""Shared paths and helpers for the dataset pipeline."""
import json
import os
import sys

TRAINING_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(TRAINING_DIR)
DATA_DIR = os.path.join(TRAINING_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
FILTERED_JSONL = os.path.join(DATA_DIR, "filtered.jsonl")
FILTER_REPORT = os.path.join(DATA_DIR, "filter_report.json")
CAPTIONS_JSONL = os.path.join(DATA_DIR, "captions.jsonl")
DATASET_DIR = os.path.join(DATA_DIR, "edu_diagrams")
DOCS_DIR = os.path.join(PROJECT_DIR, "docs", "dataset")

# The caption format lives in the backend so training and inference cannot drift apart.
sys.path.insert(0, os.path.join(PROJECT_DIR, "backend", "services", "image_backends"))
import sana_prompt  # noqa: E402,F401

SOURCES = ("ai2d", "wikimedia")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def raw_image_path(record):
    folder = "wikimedia" if record["source"] == "wikimedia_commons" else record["source"]
    return os.path.join(RAW_DIR, folder, "images", record["file_name"])
