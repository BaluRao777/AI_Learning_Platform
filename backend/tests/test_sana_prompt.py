from services.image_backends.sana_prompt import build_caption, build_sana_prompt, strip_label_words

PLAN = {"image_style": {"type": "labeled textbook diagram", "complexity": "detailed", "notes": "n"}}


def test_base_model_prompt_has_no_label_words():
    prompt = build_sana_prompt("labeled textbook diagram: a leaf cell with labelled chloroplasts with labels",
                               "college", "exam", PLAN)
    assert "label" not in prompt.lower()
    assert prompt.startswith("college level, exam style clean textbook diagram, textbook diagram: a leaf cell")
    assert prompt.endswith("educational illustration, clean background, minimal text")


def test_lora_prompt_still_matches_training_caption():
    prompt = build_sana_prompt("a leaf cell", "college", "exam", PLAN, trigger="edudiag")
    assert prompt.startswith(build_caption("a leaf cell", "detailed", "textbook_diagram", "edudiag"))
    assert "exam style clean labeled textbook diagram" in prompt


def test_strip_label_words():
    assert strip_label_words("a labeled heart , with labels") == "a heart,"
    assert strip_label_words("labels and arrows") == "labels and arrows"
