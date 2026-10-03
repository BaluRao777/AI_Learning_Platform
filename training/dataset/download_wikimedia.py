"""Download freely licensed science diagrams from Wikimedia Commons. Resumable.

Uses only the official MediaWiki API (https://commons.wikimedia.org/w/api.php)
with a descriptive User-Agent and a polite request rate. Only files whose
licence is Public Domain, CC0, CC BY or CC BY-SA are kept (anything with NC or
ND, or with an unknown licence, is skipped). Author, licence and the file's
description-page URL are stored per image.

Output: training/data/raw/wikimedia/images/*  +  training/data/raw/wikimedia/records.jsonl
"""
import argparse
import hashlib
import html
import json
import os
import re
import time

import requests

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "text-to-image-edu-project/1.0 (academic student project; contact sct.emails@gmail.com)"}
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "wikimedia")
IMAGES_DIR = os.path.join(ROOT, "images")
RECORDS = os.path.join(ROOT, "records.jsonl")

# Root categories (verified to exist on 2026-10-02) and a per-root cap to keep subjects balanced.
ROOT_CATEGORIES = {
    "Biology diagrams": 700,
    "Anatomy diagrams": 300,
    "Zoology diagrams": 250,
    "Diagrams of animal anatomy": 200,
    "Biochemistry diagrams": 250,
    "Life cycle diagrams": 200,
    "Food web diagrams": 60,
    "Earth science diagrams": 400,
    "Diagrams of volcanoes": 100,
    "Rock cycle diagrams": 60,
    "Physics diagrams": 700,
    "Optics diagrams": 300,
    "Chemistry diagrams": 400,
    "Science diagrams": 200,
}
MAX_DEPTH = 2
THUMB_WIDTH = 1024
MIN_SIDE = 512
ALLOWED_MIME = {"image/png", "image/jpeg", "image/svg+xml"}
LICENSE_OK = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by([ -]sa)?[ -]\d)", re.I)
LICENSE_BAD = re.compile(r"\b(nc|nd)\b", re.I)


def api_get(params):
    for attempt in range(6):
        resp = requests.get(API, params={**params, "format": "json", "maxlag": 5}, headers=HEADERS, timeout=60)
        if resp.status_code == 200 and "error" not in resp.json():
            return resp.json()
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Commons API kept failing for {params}")


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def license_allowed(short_name):
    return bool(short_name) and bool(LICENSE_OK.match(short_name)) and not LICENSE_BAD.search(short_name)


def subcategories(category):
    names, cont = [], {}
    while True:
        data = api_get({"action": "query", "list": "categorymembers", "cmtitle": f"Category:{category}",
                        "cmtype": "subcat", "cmlimit": 200, **cont})
        names += [m["title"].split(":", 1)[1] for m in data["query"]["categorymembers"]]
        cont = data.get("continue") or {}
        if not cont:
            return names


def files_in(category):
    cont = {}
    while True:
        data = api_get({"action": "query", "generator": "categorymembers", "gcmtitle": f"Category:{category}",
                        "gcmtype": "file", "gcmlimit": 100, "prop": "imageinfo",
                        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": THUMB_WIDTH, **cont})
        for page in (data.get("query", {}).get("pages", {}) or {}).values():
            info = (page.get("imageinfo") or [None])[0]
            if info:
                yield page["title"], info
        cont = data.get("continue") or {}
        if not cont:
            return


def candidate(title, info, root, category):
    if info.get("mime") not in ALLOWED_MIME:
        return None
    meta = info.get("extmetadata") or {}
    short = strip_html((meta.get("LicenseShortName") or {}).get("value"))
    if not license_allowed(short):
        return None
    is_svg = info["mime"] == "image/svg+xml"
    width, height = info.get("width") or 0, info.get("height") or 0
    thumb_w, thumb_h = info.get("thumbwidth") or 0, info.get("thumbheight") or 0
    if is_svg or width > THUMB_WIDTH:
        url, out_w, out_h = info.get("thumburl"), thumb_w, thumb_h
    else:
        url, out_w, out_h = info.get("url"), width, height
    if not url or min(out_w, out_h) < MIN_SIDE or max(out_w, out_h) > 4 * min(out_w, out_h):
        return None
    ext = ".jpg" if url.lower().split("?")[0].endswith((".jpg", ".jpeg")) else ".png"
    return {
        "file_name": f"wm_{hashlib.sha1(title.encode('utf-8')).hexdigest()[:16]}{ext}",
        "source": "wikimedia_commons",
        "source_url": info.get("descriptionurl"),
        "license": short,
        "author": strip_html((meta.get("Artist") or {}).get("value"))[:200] or "unknown",
        "title": title,
        "root_category": root,
        "category": category,
        "download_url": url,
    }


def crawl():
    seen_titles, seen_categories, records = set(), set(), []
    for root, cap in ROOT_CATEGORIES.items():
        frontier, kept = [(root, 0)], 0
        while frontier and kept < cap:
            category, depth = frontier.pop(0)
            if category in seen_categories:
                continue
            seen_categories.add(category)
            for title, info in files_in(category):
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                record = candidate(title, info, root, category)
                if record:
                    records.append(record)
                    kept += 1
                    if kept >= cap:
                        break
            if depth < MAX_DEPTH:
                frontier += [(name, depth + 1) for name in subcategories(category)]
            time.sleep(0.2)
        print(f"{root}: {kept} candidates")
    return records


def download(records):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    done = []
    for index, record in enumerate(records):
        target = os.path.join(IMAGES_DIR, record["file_name"])
        if not os.path.exists(target):
            for attempt in range(4):
                resp = requests.get(record["download_url"], headers=HEADERS, timeout=60)
                if resp.status_code == 200 and resp.content:
                    with open(target, "wb") as fh:
                        fh.write(resp.content)
                    break
                time.sleep(10 * (attempt + 1) if resp.status_code == 429 else 2)
            time.sleep(0.5)
        if os.path.exists(target):
            done.append(record)
        if index % 200 == 0:
            print(f"downloaded {len(done)}/{index + 1}", flush=True)
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recrawl", action="store_true", help="ignore the cached candidate list")
    args = parser.parse_args()
    os.makedirs(ROOT, exist_ok=True)
    cache = os.path.join(ROOT, "candidates.jsonl")
    if os.path.exists(cache) and not args.recrawl:
        records = [json.loads(line) for line in open(cache, encoding="utf-8")]
    else:
        records = crawl()
        with open(cache, "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in records)
    print("candidates:", len(records))
    done = download(records)
    with open(RECORDS, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in done)
    print("images:", len(done))


if __name__ == "__main__":
    main()
