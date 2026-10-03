"""Generate the evaluation images with the base model and the LoRA model.

    python training/eval/generate.py [--lora training/output/sana_edu_lora] [--sizes 1024 512]

Identical prompts (plus the trigger word for the LoRA), seeds, steps and guidance for both models.
Output: training/eval/outputs/{base,lora}_{size}/{id:03d}.png and timings.json
"""
import argparse
import json
import os
import sys

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EVAL_DIR))

from common import DEFAULT_LORA_DIR, generate, settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lora", default=DEFAULT_LORA_DIR)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1024, 512])
    args = parser.parse_args()

    prompts = json.load(open(os.path.join(EVAL_DIR, "prompts.json")))
    out_root = os.path.join(EVAL_DIR, "outputs")
    timings = {}
    for model_name, model_settings, key in (("base", settings(), "prompt"),
                                            ("lora", settings(lora_path=args.lora), "lora_prompt")):
        for size in args.sizes:
            out_dir = os.path.join(out_root, f"{model_name}_{size}")
            os.makedirs(out_dir, exist_ok=True)
            generate(prompts[0][key], prompts[0]["seed"], size, model_settings)  # warm-up, not timed
            seconds = []
            for item in prompts:
                image, info = generate(item[key], item["seed"], size, model_settings)
                image.save(os.path.join(out_dir, f"{item['id']:03d}.png"))
                seconds.append(info["seconds"])
            timings[f"{model_name}_{size}"] = {"seconds": seconds, "peak_vram_mb": info["peak_vram_mb"]}
            print(model_name, size, "mean s/image", round(sum(seconds) / len(seconds), 2), flush=True)
    with open(os.path.join(out_root, "timings.json"), "w") as fh:
        json.dump(timings, fh)


if __name__ == "__main__":
    main()
