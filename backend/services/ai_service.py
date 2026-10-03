import os
import json
import re
import html
import requests
from dotenv import load_dotenv
from google import genai
from config import Config
from services.plan_rules import build_rule_plan
from services.prompt_builder import build_gemini_prompt

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
WIKI_HEADERS = {
    "User-Agent": "text-to-image-learning-app/1.0 (educational project)"
}

def generate_content(topic, level, mode="learn", plan=None):
    if not Config.GEMINI_API_KEY:
        return _fallback(topic)

    if plan is None:
        plan = build_rule_plan(topic, level, mode)
    prompt = build_gemini_prompt(plan)

    try:
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt
        )
        text = (response.text or "").strip()
        payload = _extract_json(text)

        raw_subtopics = payload.get("subtopics") or []
        explanation = (payload.get("explanation") or "").strip()
        image_prompts = payload.get("image_prompts") or []

        subtopics = _normalize_subtopics(raw_subtopics, topic)
        image_prompts = [str(item).strip() for item in image_prompts if str(item).strip()][:5]
        if not image_prompts:
            image_prompts = [item["image_prompt"] for item in subtopics]

        if not subtopics:
            return _fallback(topic)
        if len(image_prompts) < len(subtopics):
            image_prompts.extend(
                [item["image_prompt"] for item in subtopics[len(image_prompts):]]
            )
        if not explanation:
            explanation = f"{topic} is an important concept explained for {level} learners."

        return subtopics, explanation, image_prompts[: len(subtopics)]

    except Exception as e:
        print("AI ERROR:", e)
        return _fallback(topic)


def _extract_json(text):
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _fallback(topic):
    page = _get_wikipedia_page(topic)
    summary = page.get("extract", "")
    canonical_title = page.get("title", topic)
    subtopics = _fallback_subtopics(topic, canonical_title, summary)

    if summary:
        explanation = summary
    else:
        explanation = (
            f"{topic} is a foundational concept worth learning step by step. "
            f"Begin by understanding what {topic} means and why it is important. "
            f"Then learn the key parts and how those parts interact in real scenarios. "
            f"Finally, focus on practical applications and common mistakes to build long-term clarity."
        )

    image_prompts = [item["image_prompt"] for item in subtopics]
    return subtopics, explanation, image_prompts


def _fallback_subtopics(topic, canonical_title, canonical_summary):
    titles = [
        f"Definition of {topic}",
        f"Core Components of {topic}",
        f"How {topic} Works",
        f"Applications of {topic}",
        f"Common Challenges in {topic}",
    ]

    default_briefs = [
        _to_two_sentences(canonical_summary) or f"{canonical_title} is an important concept with practical significance.",
        f"The core components of {canonical_title} can be understood through its architecture and key functional units.",
        f"{canonical_title} works through an operational flow where each stage contributes to the final behavior.",
        f"{canonical_title} is applied in practical systems with measurable impact in real-world tasks.",
        f"Common challenges in {canonical_title} include misconceptions, implementation pitfalls, and tuning issues.",
    ]

    image_styles = [
        "clean definition infographic with labeled terms",
        "technical component diagram with labeled parts",
        "step-by-step workflow illustration with arrows and labels",
        "real-world application collage in classroom textbook style",
        "comparison chart showing mistakes vs correct understanding",
    ]

    sections = _get_wikipedia_sections(canonical_title)
    subtopics = []
    for i, title in enumerate(titles):
        wiki_text = _pick_section_brief(sections, i)
        if not wiki_text:
            wiki_text = _to_two_sentences(canonical_summary) if i == 0 else _get_aspect_summary(canonical_title, i)
        brief = _to_two_sentences(wiki_text) if wiki_text else default_briefs[i]
        brief = _limit_chars(brief, 280)
        subtopics.append(
            {
                "title": title,
                "brief": brief,
                "image_prompt": (
                    f"{topic}, {title}. "
                    f"{image_styles[i]}, high clarity, educational labels, no scenery, no animals."
                ),
            }
        )
    return subtopics


def _to_two_sentences(text):
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join([s for s in sentences if s][:2]).strip()


def _limit_chars(text, max_chars):
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{cut}..."


def _normalize_subtopics(raw_subtopics, topic):
    normalized = []
    for idx, item in enumerate(raw_subtopics[:5]):
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            brief = str(item.get("brief") or "").strip()
            image_prompt = str(item.get("image_prompt") or "").strip()
        else:
            title = str(item).strip()
            brief = ""
            image_prompt = ""

        if not title:
            continue

        if not brief:
            brief = f"Briefly explains {title.lower()} within the context of {topic}."
        if not image_prompt:
            image_prompt = f"Educational labeled diagram focused on {title} in {topic}"

        normalized.append(
            {
                "title": title,
                "brief": brief,
                "image_prompt": image_prompt,
            }
        )

    return normalized


def _get_wikipedia_summary(topic):
    page = _get_wikipedia_page(topic)
    extract = page.get("extract", "")
    if not extract:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    return " ".join(sentences[:4]).strip()


def _get_wikipedia_page(topic):
    """
    Resolve a canonical Wikipedia page and return title + extract.
    """
    if not topic.strip():
        return {"title": "", "extract": ""}

    try:
        title = topic.strip().replace(" ", "_")
        response = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=WIKI_HEADERS,
            timeout=8,
        )

        if response.status_code == 404:
            search_resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": topic,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                },
                headers=WIKI_HEADERS,
                timeout=8,
            )
            if search_resp.ok:
                data = search_resp.json()
                if isinstance(data, list) and len(data) > 1 and data[1]:
                    best_title = str(data[1][0]).replace(" ", "_")
                    response = requests.get(
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/{best_title}",
                        headers=WIKI_HEADERS,
                        timeout=8,
                    )

        if not response.ok:
            return {"title": topic, "extract": ""}

        data = response.json()
        return {
            "title": (data.get("title") or topic).strip(),
            "extract": (data.get("extract") or "").strip(),
        }
    except Exception:
        return {"title": topic, "extract": ""}


def _get_wikipedia_sections(topic):
    try:
        title = topic.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/mobile-sections/{title}"
        resp = requests.get(url, headers=WIKI_HEADERS, timeout=10)
        if not resp.ok:
            return []
        data = resp.json()
        sections = []
        lead = data.get("lead", {}).get("sections", [])
        remaining = data.get("remaining", {}).get("sections", [])
        for sec in (lead + remaining):
            heading = str(sec.get("line") or "").strip()
            text = _strip_html(sec.get("text") or "")
            if heading and text:
                sections.append({"heading": heading.lower(), "text": text})
        return sections
    except Exception:
        return []


def _strip_html(raw_text):
    text = re.sub(r"<[^>]+>", " ", str(raw_text))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _pick_section_brief(sections, subtopic_index):
    if not sections:
        return ""
    keyword_sets = {
        0: ["definition", "overview", "introduction", "description"],
        1: ["architecture", "structure", "design", "component"],
        2: ["operation", "working", "mechanism", "function", "process"],
        3: ["application", "use", "usage", "industry", "example"],
        4: ["limitation", "challenge", "issue", "problem", "criticism", "error"],
    }
    keywords = keyword_sets.get(subtopic_index, [])
    for sec in sections:
        if any(key in sec["heading"] for key in keywords):
            return sec["text"]
    return ""


def _get_aspect_summary(canonical_title, subtopic_index):
    aspect_queries = {
        0: canonical_title,
        1: f"{canonical_title} architecture components",
        2: f"{canonical_title} working mechanism process",
        3: f"{canonical_title} applications use cases",
        4: f"{canonical_title} limitations challenges",
    }
    query = aspect_queries.get(subtopic_index, canonical_title)
    snippet = _get_search_snippet(query, canonical_title, subtopic_index)
    if snippet:
        return snippet
    page_title = _search_relevant_wikipedia_title(query, canonical_title)
    if not page_title:
        return ""
    summary = _get_wikipedia_summary(page_title)
    if not _is_relevant_summary(summary, canonical_title):
        return ""
    return summary


def _search_relevant_wikipedia_title(query, canonical_title):
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 5,
            },
            headers=WIKI_HEADERS,
            timeout=8,
        )
        if not resp.ok:
            return ""
        results = resp.json().get("query", {}).get("search", [])
        base_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", canonical_title) if len(t) > 2]
        for item in results:
            title = str(item.get("title") or "")
            lower_title = title.lower()
            if not base_tokens or all(tok in lower_title for tok in base_tokens):
                return title
        return ""
    except Exception:
        return ""


def _get_search_snippet(query, canonical_title, subtopic_index):
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 5,
            },
            headers=WIKI_HEADERS,
            timeout=8,
        )
        if not resp.ok:
            return ""
        results = resp.json().get("query", {}).get("search", [])
        base_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", canonical_title) if len(t) > 2]
        aspect_keywords = {
            0: ["is", "defined", "refers", "definition"],
            1: ["component", "architecture", "network", "layer", "structure"],
            2: ["process", "works", "operation", "mechanism", "training", "algorithm"],
            3: ["application", "used", "use", "industry", "task", "vision", "language"],
            4: ["challenge", "limitation", "problem", "cost", "error", "bias", "overfitting"],
        }
        wanted = aspect_keywords.get(subtopic_index, [])

        for item in results:
            title = str(item.get("title") or "").lower()
            snippet = _strip_html(item.get("snippet") or "")
            if not snippet:
                continue
            lower_snippet = snippet.lower()
            topic_match = (not base_tokens) or all(tok in title or tok in lower_snippet for tok in base_tokens)
            aspect_match = (not wanted) or any(key in lower_snippet for key in wanted)
            if topic_match and aspect_match:
                return snippet

        # Fallback: return first topic-matching snippet even if aspect keyword was not found.
        for item in results:
            title = str(item.get("title") or "").lower()
            snippet = _strip_html(item.get("snippet") or "")
            if not snippet:
                continue
            lower_snippet = snippet.lower()
            if (not base_tokens) or all(tok in title or tok in lower_snippet for tok in base_tokens):
                return snippet
        return ""
    except Exception:
        return ""


def _is_relevant_summary(summary, canonical_title):
    if not summary:
        return False
    base_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", canonical_title) if len(t) > 2]
    lower_summary = summary.lower()
    if not base_tokens:
        return True
    return any(tok in lower_summary for tok in base_tokens)