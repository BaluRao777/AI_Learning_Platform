import json

import pytest

from services.input_analyzer import extract_first_json_object
from services.plan_rules import build_rule_plan, validate_plan

COMBOS = [("school", "learn"), ("school", "exam"), ("college", "learn"), ("college", "exam")]


def test_four_combinations_produce_different_plans():
    plans = [build_rule_plan("Earth", level, mode) for level, mode in COMBOS]
    serialized = {json.dumps(plan, sort_keys=True) for plan in plans}
    assert len(serialized) == 4
    for field in ("explanation_style", "tone", "explanation_length_sentences"):
        assert len({json.dumps(plan[field]) for plan in plans}) == 4, field
    assert len({json.dumps(plan["image_style"], sort_keys=True) for plan in plans}) == 4


def test_rule_plan_follows_the_table():
    assert build_rule_plan("Earth", "school", "learn")["depth"] == "basic"
    assert build_rule_plan("Earth", "college", "exam")["depth"] == "advanced"
    assert build_rule_plan("Earth", "school", "learn")["image_style"]["type"] == "colourful infographic"
    assert build_rule_plan("Earth", "school", "exam")["image_style"]["type"] == "labeled textbook diagram"
    assert build_rule_plan("Earth", "college", "learn")["image_style"]["complexity"] == "detailed"
    assert build_rule_plan("Earth", "school", "learn")["exam_focus"] == []
    assert build_rule_plan("Earth", "school", "exam")["exam_focus"]


def test_rule_plan_has_five_subtopic_focus_areas():
    for level, mode in COMBOS:
        assert len(build_rule_plan("Earth", level, mode)["subtopic_focus"]) == 5


def test_unknown_level_and_mode_fall_back_to_defaults():
    plan = build_rule_plan("Earth", "phd", "cram")
    assert (plan["level"], plan["mode"]) == ("school", "learn")


@pytest.mark.parametrize("bad", [None, "not json", 42, ["a"], {}])
def test_validation_rejects_bad_input_and_returns_rule_plan(bad):
    plan, rejected = validate_plan(bad, "Earth", "college", "exam")
    assert plan == build_rule_plan("Earth", "college", "exam")
    assert rejected


def test_validation_merges_valid_fields_and_defaults_invalid_ones():
    base = build_rule_plan("Earth", "school", "exam")
    raw = {
        "topic": "HACKED", "level": "college", "mode": "learn",  # must be ignored
        "subject_area": "earth science",
        "depth": "expert",                                      # not allowed
        "tone": 12,                                             # wrong type
        "explanation_style": "crisp definitions",
        "explanation_length_sentences": 99,                     # out of range
        "must_include": ["layers of the Earth"],
        "avoid": "nothing",                                     # wrong type
        "subtopic_focus": ["only", "two"],                      # too short
        "exam_focus": ["definitions"],
        "image_style": {"type": "oil painting", "complexity": "simple", "notes": "cutaway"},
    }
    plan, rejected = validate_plan(raw, "Earth", "school", "exam")

    assert (plan["topic"], plan["level"], plan["mode"]) == ("Earth", "school", "exam")
    assert plan["subject_area"] == "earth science"
    assert plan["explanation_style"] == "crisp definitions"
    assert plan["must_include"] == ["layers of the Earth"]
    assert plan["exam_focus"] == ["definitions"]
    assert plan["image_style"]["notes"] == "cutaway"
    for field in ("depth", "tone", "explanation_length_sentences", "avoid", "subtopic_focus"):
        assert plan[field] == base[field]
        assert field in rejected
    assert plan["image_style"]["type"] == base["image_style"]["type"]
    assert "image_style.type" in rejected


def test_validation_rejects_boolean_length_and_clears_exam_focus_in_learn_mode():
    raw = dict(build_rule_plan("Earth", "school", "learn"), explanation_length_sentences=True, exam_focus=["x"])
    plan, rejected = validate_plan(raw, "Earth", "school", "learn")
    assert plan["explanation_length_sentences"] == 5
    assert "explanation_length_sentences" in rejected
    assert plan["exam_focus"] == []


def test_validation_repairs_near_misses():
    base = build_rule_plan("Earth", "school", "learn")
    raw = dict(base)
    raw["subtopic_focus"] = ["a", "b", "c"]                       # 3 of 5 -> topped up from rules
    raw["must_include"] = [f"item {i}" for i in range(9)]         # too long -> truncated
    raw["image_style"] = {"type": "Colorful Infographic", "complexity": "simple", "notes": "n"}
    plan, rejected = validate_plan(raw, "Earth", "school", "learn")
    assert plan["subtopic_focus"] == ["a", "b", "c"] + base["subtopic_focus"][3:]
    assert "subtopic_focus (topped up)" in rejected
    assert len(plan["must_include"]) == 6
    assert plan["image_style"]["type"] == "colourful infographic"
    assert "image_style.type" not in rejected


def test_extract_first_json_object():
    assert extract_first_json_object('Sure! {"a": {"b": "}"}} trailing {"c": 1}') == {"a": {"b": "}"}}
    with pytest.raises(ValueError):
        extract_first_json_object("no json here")
    with pytest.raises(ValueError):
        extract_first_json_object('{"unterminated": ')
