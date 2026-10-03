"""Fuse the LoRA into the base SANA transformer and save it (optional laptop deployment).

    python training/fuse_lora.py [--lora training/output/sana_edu_lora] [--out training/output/sana_edu_fused_transformer]

The fused transformer folder can be used with SANA_FUSED_TRANSFORMER_PATH so the
laptop does not need peft at runtime. After saving, the folder is loaded again
through the app's loader and one image is generated as a test.
"""
import argparse
import os

import torch
from diffusers import SanaPipeline

from common import DEFAULT_LORA_DIR, MODEL_ID, OUTPUT_DIR, build_prompts, generate, sana_local, settings
from services import model_manager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lora", default=DEFAULT_LORA_DIR)
    parser.add_argument("--out", default=os.path.join(OUTPUT_DIR, "sana_edu_fused_transformer"))
    args = parser.parse_args()

    pipe = SanaPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16, text_encoder=None, tokenizer=None, vae=None)
    pipe.load_lora_weights(args.lora)
    pipe.fuse_lora(lora_scale=1.0)
    pipe.unload_lora_weights()
    pipe.transformer.save_pretrained(args.out)
    del pipe
    size_mb = sum(os.path.getsize(os.path.join(args.out, f)) for f in os.listdir(args.out)) / 2**20
    print(f"saved fused transformer to {args.out} ({size_mb:.0f} MB)")

    plain, with_trigger, seed = build_prompts("the layers of the Earth shown as a cutaway globe", "school", "exam")
    fused_image, info = generate(with_trigger, seed, 1024, settings(fused_transformer_path=args.out))
    fused_image.save(os.path.join(OUTPUT_DIR, "fused_test.png"))
    model_manager.unload(sana_local.SANA_MODEL_NAME)
    lora_image, _ = generate(with_trigger, seed, 1024, settings(lora_path=args.lora))
    lora_image.save(os.path.join(OUTPUT_DIR, "fused_test_lora_reference.png"))

    import numpy as np

    diff = np.abs(np.asarray(fused_image, dtype=np.int16) - np.asarray(lora_image, dtype=np.int16)).mean()
    print(f"fused transformer generated an image in {info['seconds']}s; "
          f"mean abs pixel difference vs runtime LoRA (0-255 scale): {diff:.2f}")


if __name__ == "__main__":
    main()
