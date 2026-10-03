"""Generate the 4 fixed validation prompts for every saved checkpoint.

    python training/validate_checkpoints.py [--run sana_edu_lora] [--size 1024]

The diffusers example script supports only a single validation prompt, so the
per-checkpoint validation required by the plan (school/learn, school/exam,
college/learn, college/exam every 500 steps) is produced here from the saved
checkpoints, with fixed seeds. Step 0 is the base model without LoRA.

Output: docs/training/validation/step_<N>/<level>_<mode>.png and step_<N>.jpg (2x2 sheet)
"""
import argparse
import os
import re

from PIL import Image

from common import COMBOS, DOCS_DIR, OUTPUT_DIR, build_prompts, generate, settings

VALIDATION_SUBJECT = "the water cycle showing evaporation from the sea, clouds forming, rain falling on mountains and rivers flowing back to the sea"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="sana_edu_lora")
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()

    run_dir = os.path.join(OUTPUT_DIR, args.run)
    steps = sorted(int(m.group(1)) for m in (re.match(r"checkpoint-(\d+)$", d) for d in os.listdir(run_dir)) if m)
    out_root = os.path.join(DOCS_DIR, "training", "validation")
    for step in [0] + steps:
        lora = "" if step == 0 else os.path.join(run_dir, f"checkpoint-{step}")
        step_dir = os.path.join(out_root, f"step_{step:05d}")
        os.makedirs(step_dir, exist_ok=True)
        sheet = Image.new("RGB", (1024, 1024), "white")
        for index, (level, mode) in enumerate(COMBOS):
            plain, with_trigger, seed = build_prompts(VALIDATION_SUBJECT, level, mode)
            image, _ = generate(with_trigger if lora else plain, seed, args.size, settings(lora_path=lora))
            image.save(os.path.join(step_dir, f"{level}_{mode}.png"))
            sheet.paste(image.resize((512, 512), Image.LANCZOS), ((index % 2) * 512, (index // 2) * 512))
        sheet.save(os.path.join(out_root, f"step_{step:05d}.jpg"), quality=90)
        print("validated step", step, flush=True)


if __name__ == "__main__":
    main()
