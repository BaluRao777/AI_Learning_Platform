"""Call POST /analyze for N topics x 4 combinations and summarise source, timing and rejected fields.

Usage: python backend/scripts/analyzer_matrix.py <token_file> [out.json]
"""
import json
import os
import statistics
import sys
import time

import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")
TOPICS = ["Earth", "Photosynthesis", "Newton's laws of motion", "Human heart", "Acids and bases",
          "French Revolution", "Binary search", "Supply and demand"]
COMBOS = [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]


def main():
    token = open(sys.argv[1]).read().strip()
    rows = []
    for topic in TOPICS:
        for level, mode in COMBOS:
            resp = requests.post(f"{BASE}/analyze", json={"topic": topic, "level": level, "mode": mode},
                                 headers={"Authorization": f"Bearer {token}"}, timeout=600)
            data = resp.json()
            rows.append({"topic": topic, "level": level, "mode": mode, **data})
            print(topic, level, mode, data.get("source"), data.get("analysis_ms"), data.get("fields_from_rules"),
                  data.get("error", ""), flush=True)
            time.sleep(2.2)  # stay under the 30 requests/minute limiter
    qwen = [r for r in rows if r.get("source") == "qwen"]
    times = [r["analysis_ms"] for r in rows]
    summary = {
        "requests": len(rows),
        "qwen": len(qwen),
        "rules_fallback": len(rows) - len(qwen),
        "fallback_rate": round(1 - len(qwen) / len(rows), 3),
        "analysis_ms_mean": round(statistics.mean(times)),
        "analysis_ms_median": round(statistics.median(times)),
        "analysis_ms_min": min(times),
        "analysis_ms_max": max(times),
        "plans_with_any_field_from_rules": sum(1 for r in qwen if r.get("fields_from_rules")),
    }
    print(json.dumps(summary, indent=2))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "rows": rows}, fh, indent=2)


if __name__ == "__main__":
    main()
