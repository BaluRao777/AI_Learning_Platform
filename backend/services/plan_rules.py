"""Deterministic rule-based teaching plan + strict plan validation.

The rule-based plan is both the fallback (Qwen disabled / failed) and the
source of defaults for any field Qwen leaves out or gets wrong.
"""
import copy

LEVELS = ("school", "college")
MODES = ("learn", "exam")
DEPTHS = ("basic", "intermediate", "advanced")
IMAGE_TYPES = (
    "labeled textbook diagram",
    "colourful infographic",
    "process flow",
    "cross-section",
)
IMAGE_COMPLEXITIES = ("simple", "detailed")

MIN_SENTENCES = 3
MAX_SENTENCES = 10
MAX_PHRASE_CHARS = 160
MAX_LIST_ITEMS = 6
SUBTOPIC_FOCUS_COUNT = 5

_RULES = {
    ("school", "learn"): {
        "depth": "basic",
        "tone": "friendly, curious and encouraging",
        "explanation_style": "simple words, analogies and everyday examples that spark curiosity",
        "explanation_length_sentences": 5,
        "must_include": [
            "a simple one-line meaning of the topic",
            "an analogy or everyday example a school student already knows",
            "why the topic matters in daily life",
        ],
        "avoid": ["jargon without explanation", "formulas and derivations", "long sentences"],
        "subtopic_focus": [
            "what it is",
            "main parts",
            "how it works in simple steps",
            "examples from everyday life",
            "fun facts and why it matters",
        ],
        "exam_focus": [],
        "image_style": {
            "type": "colourful infographic",
            "complexity": "simple",
            "notes": "bright friendly colours, large simple shapes",
        },
    },
    ("school", "exam"): {
        "depth": "basic",
        "tone": "clear, direct and exam-oriented",
        "explanation_style": "crisp definitions and key points followed by likely exam questions with short answers",
        "explanation_length_sentences": 6,
        "must_include": [
            "a textbook-style definition",
            "the key points a school exam expects",
            "1-2 likely exam questions with short answers",
        ],
        "avoid": ["long stories and analogies", "content beyond the school syllabus", "vague statements"],
        "subtopic_focus": [
            "definition",
            "key terms",
            "main parts or types",
            "important points to remember",
            "likely exam questions",
        ],
        "exam_focus": ["definitions", "key terms", "likely questions"],
        "image_style": {
            "type": "labeled textbook diagram",
            "complexity": "simple",
            "notes": "clean white background, few clear parts",
        },
    },
    ("college", "learn"): {
        "depth": "advanced",
        "tone": "academic but approachable",
        "explanation_style": "mechanisms and cause-effect reasoning with real-world applications, technical terms explained",
        "explanation_length_sentences": 8,
        "must_include": [
            "the underlying mechanism or principle",
            "cause-and-effect relationships",
            "a real-world application",
            "technical terms, each briefly explained",
        ],
        "avoid": ["oversimplified analogies", "unexplained jargon", "school-level generalities"],
        "subtopic_focus": [
            "underlying principles",
            "mechanism in detail",
            "cause-effect relationships",
            "real-world applications",
            "limitations and current developments",
        ],
        "exam_focus": [],
        "image_style": {
            "type": "process flow",
            "complexity": "detailed",
            "notes": "stages connected by arrows, technical look",
        },
    },
    ("college", "exam"): {
        "depth": "advanced",
        "tone": "precise, formal and exam-oriented",
        "explanation_style": "precise technical definitions, formulas or laws if relevant, comparisons, likely university-exam questions",
        "explanation_length_sentences": 10,
        "must_include": [
            "a precise technical definition",
            "formulas, laws or equations if relevant",
            "a comparison with a related concept",
            "2-3 likely university exam questions with short answers",
        ],
        "avoid": ["casual language", "analogies in place of definitions", "unnecessary background"],
        "subtopic_focus": [
            "formal definition",
            "governing laws or formulas",
            "classification and comparison",
            "derivation or mechanism highlights",
            "frequently asked exam questions",
        ],
        "exam_focus": ["definitions", "formulas and laws", "comparisons", "likely questions"],
        "image_style": {
            "type": "labeled textbook diagram",
            "complexity": "detailed",
            "notes": "clean white background, many precise parts",
        },
    },
}


def normalize_level(level):
    level = str(level or "").strip().lower()
    return level if level in LEVELS else "school"


def normalize_mode(mode):
    mode = str(mode or "").strip().lower()
    return mode if mode in MODES else "learn"


def build_rule_plan(topic, level, mode):
    level = normalize_level(level)
    mode = normalize_mode(mode)
    plan = copy.deepcopy(_RULES[(level, mode)])
    plan.update({
        "topic": str(topic or "").strip(),
        "subject_area": "general",
        "level": level,
        "mode": mode,
    })
    return _ordered(plan)


def _ordered(plan):
    keys = [
        "topic", "subject_area", "level", "mode", "depth", "tone",
        "explanation_style", "explanation_length_sentences", "must_include",
        "avoid", "subtopic_focus", "exam_focus", "image_style",
    ]
    return {key: plan[key] for key in keys}


def _clean_phrase(value):
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_PHRASE_CHARS:
        return None
    return text


def _clean_list(value, min_items, max_items):
    """List of short phrases. Over-long lists are truncated; any bad item rejects the list."""
    if not isinstance(value, list):
        return None
    items = []
    for item in value:
        phrase = _clean_phrase(item)
        if phrase is None:
            return None
        if phrase not in items:
            items.append(phrase)
    items = items[:max_items]
    if len(items) < min_items:
        return None
    return items


_IMAGE_TYPE_ALIASES = {
    "colorful infographic": "colourful infographic",
    "infographic": "colourful infographic",
    "labelled textbook diagram": "labeled textbook diagram",
    "textbook diagram": "labeled textbook diagram",
    "labeled diagram": "labeled textbook diagram",
    "process flow diagram": "process flow",
    "flow diagram": "process flow",
    "cross section": "cross-section",
}


def _clean_image_type(value):
    if not isinstance(value, str):
        return None
    text = " ".join(value.lower().split())
    text = _IMAGE_TYPE_ALIASES.get(text, text)
    return text if text in IMAGE_TYPES else None


def validate_plan(raw, topic, level, mode):
    """Merge an untrusted plan (e.g. Qwen output) onto the rule-based plan.

    Returns (plan, rejected_fields). topic/level/mode always come from the
    request, never from the model. Any field that is missing, of the wrong
    type, outside the allowed values or of the wrong length is replaced by
    the rule-based default and listed in rejected_fields.
    """
    base = build_rule_plan(topic, level, mode)
    if not isinstance(raw, dict):
        return base, ["<not an object>"]

    plan = copy.deepcopy(base)
    rejected = []

    def take(field, cleaned):
        if cleaned is None:
            rejected.append(field)
        else:
            plan[field] = cleaned

    take("subject_area", _clean_phrase(raw.get("subject_area")))
    take("tone", _clean_phrase(raw.get("tone")))
    take("explanation_style", _clean_phrase(raw.get("explanation_style")))

    depth = raw.get("depth")
    take("depth", depth if isinstance(depth, str) and depth in DEPTHS else None)

    length = raw.get("explanation_length_sentences")
    if isinstance(length, bool) or not isinstance(length, int) or not (MIN_SENTENCES <= length <= MAX_SENTENCES):
        rejected.append("explanation_length_sentences")
    else:
        plan["explanation_length_sentences"] = length

    take("must_include", _clean_list(raw.get("must_include"), 1, MAX_LIST_ITEMS))
    take("avoid", _clean_list(raw.get("avoid"), 0, MAX_LIST_ITEMS))
    # Exactly 5 focus areas are required. A shorter (but usable) list is topped up
    # from the rule-based plan instead of being thrown away.
    focus = _clean_list(raw.get("subtopic_focus"), 3, SUBTOPIC_FOCUS_COUNT)
    if focus is None:
        rejected.append("subtopic_focus")
    else:
        if len(focus) < SUBTOPIC_FOCUS_COUNT:
            rejected.append("subtopic_focus (topped up)")
            focus = focus + base["subtopic_focus"][len(focus):]
        plan["subtopic_focus"] = focus

    if plan["mode"] == "exam":
        take("exam_focus", _clean_list(raw.get("exam_focus"), 1, MAX_LIST_ITEMS))
    else:
        plan["exam_focus"] = []

    style = raw.get("image_style")
    if not isinstance(style, dict):
        rejected.append("image_style")
    else:
        image_type = _clean_image_type(style.get("type"))
        if image_type:
            plan["image_style"]["type"] = image_type
        else:
            rejected.append("image_style.type")
        if isinstance(style.get("complexity"), str) and style["complexity"] in IMAGE_COMPLEXITIES:
            plan["image_style"]["complexity"] = style["complexity"]
        else:
            rejected.append("image_style.complexity")
        notes = _clean_phrase(style.get("notes"))
        if notes is None:
            rejected.append("image_style.notes")
        else:
            plan["image_style"]["notes"] = notes

    return _ordered(plan), rejected
