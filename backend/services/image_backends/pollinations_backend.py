"""Original Pollinations URL builder, moved here unchanged from image_service.py."""
from urllib.parse import quote
import hashlib


def generate_images(prompts, mode):
    images = []
    style_hint = (
        "textbook diagram style, educational, labeled elements, clean white background, no artistic scenery"
        if mode == "exam"
        else "educational infographic style, clear labels, classroom-friendly, no random nature scenery, no animals"
    )

    for prompt in prompts:
        concise_prompt = " ".join(str(prompt).split())[:180]
        safe_prompt = f"{concise_prompt}. {style_hint}. focus strictly on the described concept."
        prompt_hash = hashlib.sha256(safe_prompt.encode("utf-8")).hexdigest()[:12]
        encoded_prompt = quote(safe_prompt, safe="")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={prompt_hash}&width=640&height=420"
        images.append(url)

    return images
