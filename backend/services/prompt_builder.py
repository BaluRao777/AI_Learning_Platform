"""Builds the Gemini prompt from a teaching plan.

The JSON output schema is identical to the original prompt in ai_service.py
(5 subtopics with title/brief/image_prompt, explanation, image_prompts), so
the existing parsing and normalization keep working unchanged.
"""

_AUDIENCE = {
    "school": "school students (age 10-15)",
    "college": "college / university students",
}

_PURPOSE = {
    "learn": "learning the topic for the first time and building real understanding",
    "exam": "revising for an exam and scoring marks",
}


def _bullets(items):
    return "\n".join(f"  - {item}" for item in items) if items else "  - (none)"


def build_gemini_prompt(plan):
    level = plan["level"]
    mode = plan["mode"]
    length = int(plan["explanation_length_sentences"])
    min_length = max(3, length - 2)
    style = plan["image_style"]
    # The image model cannot render text, so do not ask Gemini for "labeled" images.
    image_type = style["type"].replace("labeled ", "")

    exam_block = ""
    exam_rule = ""
    if mode == "exam":
        exam_block = f"""
Exam focus (exam mode):
{_bullets(plan.get("exam_focus") or [])}
"""
        exam_rule = (
            "- This is EXAM mode: inside the \"explanation\" text itself, first give the key definitions, "
            "then add 1-3 likely exam questions each followed by a short answer, written as "
            "\"Q: ... A: ...\". The app only displays the explanation and subtopics, so the exam "
            "content must appear there.\n"
        )

    return f"""
You are an expert teacher assistant.
Return strictly valid JSON and no markdown.

Topic: "{plan["topic"]}"
Subject area: "{plan["subject_area"]}"
Audience: "{_AUDIENCE[level]}" (level: {level})
Purpose: "{_PURPOSE[mode]}" (mode: {mode})
Depth: "{plan["depth"]}"
Tone: "{plan["tone"]}"
Explanation style: "{plan["explanation_style"]}"

Must include:
{_bullets(plan["must_include"])}

Avoid:
{_bullets(plan["avoid"])}

Subtopic focus (one subtopic per focus area, in this order):
{_bullets(plan["subtopic_focus"])}
{exam_block}
Image style for every image_prompt: "{image_type}", {style["complexity"]} ({style["notes"]})

JSON schema:
{{
  "subtopics": [
    {{
      "title": "string",
      "brief": "string",
      "image_prompt": "string"
    }}
  ],
  "explanation": "string",
  "image_prompts": ["string", "string", "string", "string", "string"]
}}

Rules:
- Keep exactly 5 subtopics.
- Each subtopic must contain title, brief (1-2 sentences), and image_prompt.
- Write every brief and the explanation at "{plan["depth"]}" depth for the audience above.
- explanation must be {min_length}-{length} sentences.
{exam_rule}- image_prompts must map 1:1 with subtopics and be educational visual scene prompts.
- Each image_prompt must describe ONE concept visually as a {style["complexity"]} {image_type}: name the objects, shapes, arrows and colours to draw. Use minimal or no text inside the image (the image model cannot render legible words), so do not use the word "labeled" and do not ask for labels, captions or written words.
"""
