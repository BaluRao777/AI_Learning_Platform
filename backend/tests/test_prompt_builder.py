from services.plan_rules import build_rule_plan
from services.prompt_builder import build_gemini_prompt

COMBOS = [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]


def _prompt(level, mode, topic="Earth"):
    return build_gemini_prompt(build_rule_plan(topic, level, mode))


def test_level_and_mode_appear_in_prompt():
    for level, mode in COMBOS:
        prompt = _prompt(level, mode)
        assert f"level: {level}" in prompt
        assert f"mode: {mode}" in prompt
        assert '"Earth"' in prompt
    assert "school students" in _prompt("school", "learn")
    assert "college" in _prompt("college", "learn")


def test_four_combinations_give_four_different_prompts():
    assert len({_prompt(level, mode) for level, mode in COMBOS}) == 4


def test_exam_mode_asks_for_questions_inside_explanation():
    for level in ("school", "college"):
        exam = _prompt(level, "exam")
        assert "likely exam questions" in exam
        assert "Q: ... A: ..." in exam
        assert "Exam focus" in exam
        learn = _prompt(level, "learn")
        assert "EXAM mode" not in learn
        assert "Exam focus" not in learn


def test_plan_fields_are_listed():
    plan = build_rule_plan("Earth", "college", "learn")
    prompt = build_gemini_prompt(plan)
    for item in plan["must_include"] + plan["avoid"] + plan["subtopic_focus"]:
        assert item in prompt
    assert plan["tone"] in prompt
    assert plan["image_style"]["type"] in prompt


def test_image_prompt_instructions_never_say_labeled():
    for level, mode in COMBOS:
        prompt = _prompt(level, mode)
        instructions = prompt.split("Image style for every image_prompt:", 1)[1]
        assert "labeled textbook diagram" not in instructions
        assert 'do not use the word "labeled"' in prompt


def test_explanation_length_follows_plan():
    assert "explanation must be 3-5 sentences" in _prompt("school", "learn")
    assert "explanation must be 8-10 sentences" in _prompt("college", "exam")


def test_output_schema_unchanged():
    for level, mode in COMBOS:
        prompt = _prompt(level, mode)
        assert "Return strictly valid JSON and no markdown." in prompt
        for key in ('"subtopics"', '"title"', '"brief"', '"image_prompt"', '"explanation"', '"image_prompts"'):
            assert key in prompt
        assert "Keep exactly 5 subtopics." in prompt
        assert "minimal or no text inside the image" in prompt
