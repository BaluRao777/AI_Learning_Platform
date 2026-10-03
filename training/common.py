"""Shared helpers for training-side scripts (validation, evaluation, fusing).

Generation goes through the app's own loader (backend/services/image_backends/sana_local.py)
so evaluation uses exactly the code path the application uses.
"""
import os
import sys

TRAINING_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TRAINING_DIR)
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
DOCS_DIR = os.path.join(PROJECT_DIR, "docs")
OUTPUT_DIR = os.path.join(TRAINING_DIR, "output")
DEFAULT_LORA_DIR = os.path.join(OUTPUT_DIR, "sana_edu_lora")
MODEL_ID = os.environ.get("SANA_MODEL_ID", "Efficient-Large-Model/SANA1.5_1.6B_1024px_diffusers")
TRIGGER = "edudiag"
COMBOS = [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]

sys.path.insert(0, BACKEND_DIR)

from services.image_backends import sana_local, sana_prompt  # noqa: E402
from services.plan_rules import build_rule_plan  # noqa: E402


def settings(lora_path="", fused_transformer_path=""):
    """Full-precision workstation settings: bf16, everything on the GPU."""
    return sana_local.SanaSettings(
        model_id=MODEL_ID, lora_path=lora_path, lora_scale=1.0,
        fused_transformer_path=fused_transformer_path, text_encoder_4bit=False, offload="none",
    )


def build_prompts(image_prompt, level, mode):
    """Return (plain_prompt, lora_prompt, seed) using the rule-based plan for the combination."""
    plan = build_rule_plan("", level, mode)
    plain = sana_prompt.build_sana_prompt(image_prompt, level, mode, plan)
    with_trigger = sana_prompt.build_sana_prompt(image_prompt, level, mode, plan, trigger=TRIGGER)
    return plain, with_trigger, sana_prompt.seed_for_prompt(plain)


def generate(prompt, seed, size, model_settings, steps=20, guidance=4.5):
    return sana_local.generate(prompt, sana_prompt.NEGATIVE_PROMPT, size, size, steps, guidance, seed,
                               settings=model_settings)
