"""Input Analysis Layer: Qwen2.5-1.5B-Instruct turns (topic, level, mode)
into a structured teaching plan that controls what Gemini produces.

/generate must never fail because of Qwen: any exception, timeout or invalid
JSON falls back to the deterministic rule-based plan.
"""
import json
import time

from config import Config
from services import model_manager
from services.plan_rules import (
    DEPTHS,
    IMAGE_COMPLEXITIES,
    IMAGE_TYPES,
    build_rule_plan,
    validate_plan,
)

QWEN_MODEL_NAME = "qwen_analyzer"

_SCHEMA_TEXT = f"""{{
  "subject_area": "short phrase, e.g. biology / plant physiology",
  "depth": one of {list(DEPTHS)},
  "tone": "short phrase",
  "explanation_style": "short phrase",
  "explanation_length_sentences": integer 3-10,
  "must_include": ["2-5 short topic-specific items"],
  "avoid": ["1-4 short items"],
  "subtopic_focus": ["exactly 5 short topic-specific focus areas"],
  "exam_focus": ["exam mode only: 2-4 short items; [] in learn mode"],
  "image_style": {{
    "type": one of {list(IMAGE_TYPES)},
    "complexity": one of {list(IMAGE_COMPLEXITIES)},
    "notes": "short phrase"
  }}
}}"""

_GUIDANCE = """Guidance for the four combinations:
- school + learn: depth basic; simple words, analogies, everyday examples, curiosity; about 5 sentences; image: colourful infographic, simple.
- school + exam: depth basic; crisp definitions, key points, 1-2 likely exam questions with short answers; about 6 sentences; image: labeled textbook diagram, simple.
- college + learn: depth advanced; mechanisms, cause-effect, real-world applications, technical terms explained; about 8 sentences; image: process flow, detailed.
- college + exam: depth advanced; precise technical definitions, formulas/laws if relevant, comparisons, likely university-exam questions; about 10 sentences; image: labeled textbook diagram, detailed."""

SYSTEM_PROMPT = f"""You are an educational input analyst. Given a topic, a learner level and a learning mode, output ONLY a JSON teaching plan matching this schema, with no markdown and no extra text:

{_SCHEMA_TEXT}

{_GUIDANCE}

Make must_include, subtopic_focus and exam_focus specific to the given topic, not generic."""

_FEW_SHOT = [
    (
        {"topic": "Water cycle", "level": "school", "mode": "learn"},
        {
            "subject_area": "geography / earth science",
            "depth": "basic",
            "tone": "friendly and curious",
            "explanation_style": "simple words with everyday examples like puddles drying and rain",
            "explanation_length_sentences": 5,
            "must_include": ["evaporation", "condensation into clouds", "rain and collection in rivers and seas"],
            "avoid": ["technical terms like transpiration rates", "formulas"],
            "subtopic_focus": [
                "what the water cycle is",
                "evaporation from seas and lakes",
                "cloud formation",
                "rain and snow",
                "water returning to rivers and oceans",
            ],
            "exam_focus": [],
            "image_style": {"type": "colourful infographic", "complexity": "simple", "notes": "sun, clouds, rain and sea with arrows"},
        },
    ),
    (
        {"topic": "Ohm's law", "level": "college", "mode": "exam"},
        {
            "subject_area": "physics / electrical engineering",
            "depth": "advanced",
            "tone": "precise and formal",
            "explanation_style": "technical definition, formula with units, limitations and typical exam questions",
            "explanation_length_sentences": 10,
            "must_include": ["statement of Ohm's law", "V = IR with SI units", "ohmic vs non-ohmic conductors", "2-3 likely exam questions with answers"],
            "avoid": ["casual analogies", "school-level simplifications"],
            "subtopic_focus": [
                "formal statement and formula",
                "resistance and resistivity",
                "V-I characteristics",
                "ohmic versus non-ohmic devices",
                "numerical problems asked in exams",
            ],
            "exam_focus": ["definition", "formula and units", "V-I graph", "likely questions"],
            "image_style": {"type": "labeled textbook diagram", "complexity": "detailed", "notes": "circuit with resistor, ammeter and voltmeter"},
        },
    ),
]


def _user_message(topic, level, mode):
    return json.dumps({"topic": topic, "level": level, "mode": mode})


def build_messages(topic, level, mode):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for request, plan in _FEW_SHOT:
        messages.append({"role": "user", "content": json.dumps(request)})
        messages.append({"role": "assistant", "content": json.dumps(plan)})
    messages.append({"role": "user", "content": _user_message(topic, level, mode)})
    return messages


def extract_first_json_object(text):
    """Return the first balanced {...} object in text as a dict, else raise ValueError."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start: idx + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        return value
                    break
        start = text.find("{", start + 1)
    raise ValueError("no JSON object found in analyzer output")


def _load_qwen():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(Config.QWEN_MODEL_ID)
    kwargs = {}
    use_cuda = torch.cuda.is_available()
    if Config.QWEN_LOAD_IN_4BIT and use_cuda:
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        kwargs["device_map"] = {"": 0}
    elif use_cuda:
        kwargs["torch_dtype"] = torch.bfloat16
        kwargs["device_map"] = {"": 0}
    else:
        kwargs["torch_dtype"] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(Config.QWEN_MODEL_ID, **kwargs)
    model.eval()
    return {"model": model, "tokenizer": tokenizer}


def _run_qwen(topic, level, mode):
    import torch

    with model_manager.use_model(QWEN_MODEL_NAME, _load_qwen) as bundle:
        model, tokenizer = bundle["model"], bundle["tokenizer"]
        prompt = tokenizer.apply_chat_template(
            build_messages(topic, level, mode), tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
        with torch.no_grad():
            output = model.generate(
                **inputs,
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                repetition_penalty=1.1,  # still greedy; stops runaway list repetition
                max_new_tokens=Config.QWEN_MAX_NEW_TOKENS,
                max_time=Config.QWEN_MAX_TIME_SECONDS,
            )
        text = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        del inputs, output
    return text


def analyze_input(topic, level, mode):
    """Return {"source": "qwen"|"rules", "plan": {...}, "analysis_ms": int, ...}.

    Never raises.
    """
    started = time.perf_counter()
    result = {"source": "rules", "plan": build_rule_plan(topic, level, mode), "analysis_ms": 0}

    if Config.ANALYZER_ENABLED:
        try:
            raw_text = _run_qwen(topic, level, mode)
            raw_plan = extract_first_json_object(raw_text)
            plan, rejected = validate_plan(raw_plan, topic, level, mode)
            result["source"] = "qwen"
            result["plan"] = plan
            result["fields_from_rules"] = rejected
        except Exception as exc:
            print(f"ANALYZER WARNING: Qwen analysis failed, using rule-based plan: {type(exc).__name__}: {exc}")
            result["error"] = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            if Config.QWEN_UNLOAD_AFTER_USE:
                try:
                    model_manager.unload(QWEN_MODEL_NAME)
                except Exception as exc:
                    print(f"ANALYZER WARNING: unload failed: {exc}")
        load = model_manager.load_stats(QWEN_MODEL_NAME)
        if load:
            result["model_load_s"] = load.get("load_s")

    result["analysis_ms"] = int((time.perf_counter() - started) * 1000)
    return result
