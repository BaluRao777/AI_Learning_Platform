"""SANA prompt construction, shared by the app, the dataset captions
(training/dataset/caption.py) and the evaluation prompts so that training
and inference use exactly the same wording.

Caption / prompt format:
    {trigger}, {level words}, {look words}, {description}[, educational illustration, clean background, minimal text]
"""
import hashlib
import re

NEGATIVE_PROMPT = "blurry, photo of people, watermark, garbled text, low quality"
PROMPT_SUFFIX = "educational illustration, clean background, minimal text"

LEVEL_WORDS = {
    "simple": "school level",
    "detailed": "college level",
}

# look tag -> style words (must match training/dataset/caption.py)
LOOK_WORDS = {
    "infographic": "learn style colourful infographic",
    "textbook_diagram": "exam style clean labeled textbook diagram",
    "cross_section": "exam style clean labeled textbook diagram",
    "process_flow": "process flow diagram",
}

# Style words for the BASE model (no LoRA). "labeled" makes SANA draw text it cannot
# render, so it is dropped here. The LoRA keeps LOOK_WORDS, because its training
# captions contain "labeled".
BASE_MODEL_LOOK_WORDS = {
    "infographic": "learn style colourful infographic",
    "textbook_diagram": "exam style clean textbook diagram",
    "cross_section": "exam style clean textbook diagram",
    "process_flow": "process flow diagram",
}

_LABEL_WORDS = re.compile(r"\b(?:with\s+labels|labell?ed)\b\s*", re.I)

# plan["image_style"]["type"] -> look tag
_TYPE_TO_LOOK = {
    "colourful infographic": "infographic",
    "labeled textbook diagram": "textbook_diagram",
    "cross-section": "cross_section",
    "process flow": "process_flow",
}


def style_tags(level=None, mode=None, plan=None):
    """Return (complexity, look) for a request."""
    style = (plan or {}).get("image_style") or {}
    complexity = style.get("complexity")
    if complexity not in LEVEL_WORDS:
        complexity = "detailed" if level == "college" else "simple"
    look = _TYPE_TO_LOOK.get(style.get("type"))
    if look is None:
        look = "textbook_diagram" if mode == "exam" else "infographic"
    return complexity, look


def style_phrase(complexity, look):
    return f"{LEVEL_WORDS[complexity]}, {LOOK_WORDS[look]}"


def build_caption(description, complexity, look, trigger="edudiag"):
    """Training caption: `edudiag, {level words}, {look words}, {description}`."""
    parts = [trigger] if trigger else []
    parts += [style_phrase(complexity, look), " ".join(str(description).split())]
    return ", ".join(parts)


def strip_label_words(text):
    """Remove "labeled" / "labelled" / "with labels" from a prompt."""
    text = _LABEL_WORDS.sub("", text)
    return re.sub(r"\s+([,.:;])", r"\1", " ".join(text.split()))


def build_sana_prompt(image_prompt, level=None, mode=None, plan=None, trigger=""):
    """Inference prompt. Pass trigger="" when no LoRA is loaded.

    With a trigger (LoRA loaded) the prompt matches the training captions exactly.
    Without one (base model) the label words are removed.
    """
    complexity, look = style_tags(level, mode, plan)
    description = " ".join(str(image_prompt).split())[:400].rstrip(" .,")
    if trigger:
        return f"{build_caption(description, complexity, look, trigger)}, {PROMPT_SUFFIX}"
    description = strip_label_words(description).lstrip(" ,:;").rstrip(" .,")
    style = f"{LEVEL_WORDS[complexity]}, {BASE_MODEL_LOOK_WORDS[look]}"
    return f"{style}, {description}, {PROMPT_SUFFIX}"


def seed_for_prompt(prompt):
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)
