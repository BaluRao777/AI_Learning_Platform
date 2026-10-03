"""Caption and tag the filtered images with a vision-language model. Resumable.

    python training/dataset/caption.py [--limit N] [--batch-size 8]

Model: Qwen/Qwen2.5-VL-7B-Instruct (Apache-2.0, id verified on Hugging Face 2026-10-02).
For every image the model returns:
    description              one sentence describing the concept shown
    complexity               simple | detailed
    look                     infographic | textbook_diagram | process_flow | cross_section
    is_educational_diagram   false for photos, logos, maps without teaching content, screenshots ...
    has_photo_of_people      true if the image is / contains a photograph of real people

Writes training/data/captions.jsonl (one line per image, including failures).
"""
import argparse
import json
import os
import re

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from common import CAPTIONS_JSONL, FILTERED_JSONL, raw_image_path, read_jsonl

MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
MAX_SIDE = 672
COMPLEXITIES = ("simple", "detailed")
LOOKS = ("infographic", "textbook_diagram", "process_flow", "cross_section")

BOILERPLATE = re.compile(
    r"^(this|the|a|an)\s+([\w-]+\s+){0,4}?(diagram|infographic|illustration|image|picture|drawing|chart|graphic|figure|view)s?\s+"
    r"(that\s+|which\s+)?(is\s+)?(illustrating|illustrates|showing|shows|depicting|depicts|explaining|explains|"
    r"representing|represents|highlighting|highlights|displaying|displays|of|demonstrating|demonstrates|comparing|compares|outlining|outlines)\s+",
    re.I,
)

TRAILING_STYLE = [
    re.compile(r",?\s+(drawn|shown|depicted|presented|rendered|illustrated)\s+in\s+(an?\s+)?[\w\s,-]*?(style|manner|format)\b.*$", re.I),
    re.compile(r",?\s+(and\s+)?label(l)?ed\s+(with\s+letters\s+)?for\s+educational\s+purposes.*$", re.I),
    re.compile(r",?\s+with\s+(clear\s+)?labels(\s+and\s+arrows\s+pointing\s+to\s+each\s+part)?\s*$", re.I),
]

PROMPT = """You are labelling images for an educational-diagram dataset. Look at the image and answer with ONLY a JSON object:
{
  "description": "ONE sentence (15-35 words) that starts directly with the subject and says what is drawn: the objects, their parts, arrows and layout. Example: 'the parts of a flower including petals, stamens, pistil and ovary, drawn in side view with the stem below'. Do not use the words diagram, infographic, illustration, image, simple or detailed. Do not mention labels, captions, text or letters.",
  "complexity": "simple" or "detailed",
  "look": "infographic" or "textbook_diagram" or "process_flow" or "cross_section",
  "is_educational_diagram": true or false,
  "has_photo_of_people": true or false
}
Definitions:
- complexity: "simple" = few large parts, suitable for school students; "detailed" = many parts or technical content, suitable for college students.
- look: "infographic" = colourful illustrated poster-like graphic; "textbook_diagram" = clean drawing of an object or system with its parts, mostly on a plain background; "process_flow" = stages, cycles or steps connected by arrows; "cross_section" = cutaway or sectional view showing the inside of something.
- is_educational_diagram: false for plain photographs, logos, charts of raw data, tables of text, screenshots, or anything that does not explain a concept visually.
- has_photo_of_people: true only if it contains a photograph of real people."""


def load_image(path):
    image = Image.open(path).convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    image = Image.alpha_composite(background, image).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return image


def parse(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    description = " ".join(str(data.get("description") or "").split())
    # Drop boilerplate openers such as "A detailed textbook diagram illustrating ..." so the
    # description carries content only (style is carried by the level/look words).
    description = BOILERPLATE.sub("", description)
    for pattern in TRAILING_STYLE:
        description = pattern.sub("", description)
    description = description.replace("textbook_diagram", "diagram").replace("process_flow", "flow").replace("cross_section", "cross-section")
    if description[:4] == "The ":
        description = "the " + description[4:]
    if (
        len(description) < 20
        or data.get("complexity") not in COMPLEXITIES
        or data.get("look") not in LOOKS
        or not isinstance(data.get("is_educational_diagram"), bool)
        or not isinstance(data.get("has_photo_of_people"), bool)
    ):
        return None
    return {
        "description": description.rstrip(". "),
        "complexity": data["complexity"],
        "look": data["look"],
        "is_educational_diagram": data["is_educational_diagram"],
        "has_photo_of_people": data["has_photo_of_people"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    done = {row["file_name"] for row in read_jsonl(CAPTIONS_JSONL)}
    todo = [r for r in read_jsonl(FILTERED_JSONL) if r["file_name"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"already captioned: {len(done)}, to do: {len(todo)}")
    if not todo:
        return

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    processor.tokenizer.padding_side = "left"
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(MODEL_ID, dtype=torch.bfloat16, device_map={"": 0})
    model.eval()

    with open(CAPTIONS_JSONL, "a", encoding="utf-8") as out:
        for start in range(0, len(todo), args.batch_size):
            batch = todo[start: start + args.batch_size]
            conversations = [
                [{"role": "user", "content": [{"type": "image", "image": load_image(raw_image_path(r))},
                                              {"type": "text", "text": PROMPT}]}]
                for r in batch
            ]
            inputs = processor.apply_chat_template(
                conversations, add_generation_prompt=True, tokenize=True, return_dict=True,
                return_tensors="pt", padding=True,
            ).to(model.device)
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=200, do_sample=False)
            texts = processor.batch_decode(output[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            for record, text in zip(batch, texts):
                parsed = parse(text)
                row = {"file_name": record["file_name"], "ok": parsed is not None}
                row.update(parsed or {"raw": text[:300]})
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            if (start // args.batch_size) % 25 == 0:
                print(f"{start + len(batch)}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
