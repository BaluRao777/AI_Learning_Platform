"""Save /generate responses as evidence files.

Usage: python backend/scripts/capture_responses.py <out_dir> <token_file> [topic ...]
Calls the running backend for each topic x 4 level/mode combinations.
"""
import json
import os
import sys
import time

import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")
COMBOS = [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]


def main():
    out_dir, token_file, topics = sys.argv[1], sys.argv[2], sys.argv[3:] or ["Earth", "Photosynthesis"]
    token = open(token_file).read().strip()
    os.makedirs(out_dir, exist_ok=True)
    for topic in topics:
        for level, mode in COMBOS:
            started = time.perf_counter()
            resp = requests.post(
                f"{BASE}/generate",
                json={"topic": topic, "level": level, "mode": mode},
                headers={"Authorization": f"Bearer {token}"},
                timeout=300,
            )
            elapsed = round(time.perf_counter() - started, 2)
            name = f"{topic.lower().replace(' ', '_')}_{level}_{mode}.json"
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                json.dump({"http_status": resp.status_code, "seconds": elapsed, "response": resp.json()}, fh, indent=2)
            print(name, resp.status_code, f"{elapsed}s")
            time.sleep(1)


if __name__ == "__main__":
    main()
