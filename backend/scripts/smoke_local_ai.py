"""Manual GPU smoke test for the local AI stack.

    python backend/scripts/smoke_local_ai.py [--topic Earth] [--size 512] [--offload model] [--no-4bit] [--out smoke.png]

Loads Qwen, prints a teaching plan, unloads it, loads SANA, generates one
image, and prints timings, peak VRAM and peak RAM. Uses the same code paths
as the app (input_analyzer, sana_local, model_manager).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil  # noqa: E402
import torch  # noqa: E402

from config import Config  # noqa: E402
from services import input_analyzer, model_manager  # noqa: E402
from services.image_backends import sana_local, sana_prompt  # noqa: E402


def rss_mb():
    return round(psutil.Process().memory_info().rss / (1024 * 1024))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="Photosynthesis")
    parser.add_argument("--level", default="school")
    parser.add_argument("--mode", default="learn")
    parser.add_argument("--size", type=int, default=Config.SANA_HEIGHT)
    parser.add_argument("--steps", type=int, default=Config.SANA_STEPS)
    parser.add_argument("--offload", default=Config.SANA_OFFLOAD, choices=["none", "model", "sequential"])
    parser.add_argument("--no-4bit", action="store_true", help="load the SANA text encoder in bf16")
    parser.add_argument("--images", type=int, default=1)
    parser.add_argument("--out", default="smoke.png")
    args = parser.parse_args()

    print("torch", torch.__version__, "| cuda available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("gpu:", torch.cuda.get_device_name(0))

    # ---- Qwen ----
    Config.ANALYZER_ENABLED = True
    Config.QWEN_UNLOAD_AFTER_USE = False
    first = input_analyzer.analyze_input(args.topic, args.level, args.mode)
    qwen_vram = torch.cuda.max_memory_allocated() / 2**20 if torch.cuda.is_available() else 0
    second = input_analyzer.analyze_input(args.topic, "college", "exam")
    print(json.dumps(first, indent=2))
    print(f"QWEN source={first['source']} load_s={first.get('model_load_s')} "
          f"first_call_ms={first['analysis_ms']} warm_call_ms={second['analysis_ms']} "
          f"peak_vram_mb={qwen_vram:.0f} rss_mb={rss_mb()}")
    model_manager.unload(input_analyzer.QWEN_MODEL_NAME)
    if torch.cuda.is_available():
        print(f"after Qwen unload: vram_allocated_mb={torch.cuda.memory_allocated() / 2**20:.0f}")

    # ---- SANA ----
    base = sana_local.settings_from_config()
    settings = sana_local.SanaSettings(
        model_id=base.model_id, lora_path=base.lora_path, lora_scale=base.lora_scale,
        fused_transformer_path=base.fused_transformer_path,
        text_encoder_4bit=not args.no_4bit, offload=args.offload,
    )
    trigger = Config.SANA_TRIGGER if settings.uses_finetune else ""
    image_prompt = "a green leaf absorbing sunlight, water and carbon dioxide and releasing oxygen"
    plain = sana_prompt.build_sana_prompt(image_prompt, args.level, args.mode, first["plan"])
    prompt = sana_prompt.build_sana_prompt(image_prompt, args.level, args.mode, first["plan"], trigger=trigger)
    print("SANA prompt:", prompt)

    peak_rss = rss_mb()
    total_started = time.perf_counter()
    for index in range(args.images):
        image, info = sana_local.generate(
            prompt, sana_prompt.NEGATIVE_PROMPT, args.size, args.size, args.steps, Config.SANA_GUIDANCE,
            sana_prompt.seed_for_prompt(plain) + index, settings=settings,
        )
        peak_rss = max(peak_rss, rss_mb())
        print(f"SANA image {index + 1}: {info} size={image.size} rss_mb={rss_mb()}")
    total = time.perf_counter() - total_started
    image.save(args.out)
    print(f"SANA total_s={total:.1f} for {args.images} image(s) incl. load; peak_rss_mb={peak_rss}; saved {args.out}")


if __name__ == "__main__":
    main()
