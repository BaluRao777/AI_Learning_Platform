"""Image service dispatcher.

IMAGE_BACKEND=pollinations -> original behaviour (Pollinations URLs).
IMAGE_BACKEND=local|remote -> background SANA jobs; returns
"{host}/generated/{id}.png" URLs that become ready later.
IMAGE_BACKEND=mixed -> comparison mode, IMAGE_MIX decides the sources in order
(default: 2 x SANA base, 1 x SANA + LoRA, 2 x Pollinations).
"""
import uuid

from config import Config
from services.image_backends import pollinations_backend

POLLINATIONS_PREFIX = "https://image.pollinations.ai/"
PLACEHOLDER_NAME = "placeholder.svg"


def is_pollinations_url(url):
    return str(url).startswith(POLLINATIONS_PREFIX)


def _host_url(base_url):
    if base_url:
        return base_url.rstrip("/")
    from flask import request

    return request.host_url.rstrip("/")


VALID_MIX_SOURCES = ("base", "lora", "pollinations")


def parse_image_mix(spec, count):
    """'base:2,lora:2,pollinations:1' -> ['base','base','lora','lora','pollinations'] (length = count).

    Unknown sources are ignored; missing slots are filled with 'base'; extra slots are cut.
    """
    slots = []
    for part in str(spec or "").split(","):
        name, _, number = part.strip().partition(":")
        name = name.strip().lower()
        try:
            amount = int(number)
        except ValueError:
            continue
        if name in VALID_MIX_SOURCES and amount > 0:
            slots += [name] * amount
    slots += ["base"] * max(0, count - len(slots))
    return slots[:count]


def generate_images(prompts, mode, level=None, plan=None, base_url=None):
    return generate_images_with_sources(prompts, mode, level, plan, base_url)[0]


def generate_images_with_sources(prompts, mode, level=None, plan=None, base_url=None):
    """Return (image_urls, sources). sources[i] says which model made image i."""
    if Config.IMAGE_BACKEND == "mixed":
        return _generate_mixed(list(prompts), mode, level, plan, base_url)
    if Config.IMAGE_BACKEND not in {"local", "remote"}:
        urls = pollinations_backend.generate_images(prompts, mode)
        return urls, ["pollinations"] * len(urls)
    urls = _generate_sana(prompts, mode, level, plan, base_url)
    if Config.IMAGE_BACKEND == "remote":
        source = "sana_remote"
    else:
        from services.image_backends import sana_local

        source = "sana_lora" if sana_local.settings_from_config().uses_finetune else "sana_base"
    return urls, [_source_of(url, source) for url in urls]


def _source_of(url, sana_source):
    if is_pollinations_url(url):
        return "pollinations"
    if url.endswith(PLACEHOLDER_NAME):
        return "placeholder"
    return sana_source


def _generate_mixed(prompts, mode, level, plan, base_url):
    """Comparison mode: e.g. 2 x SANA base, 2 x SANA + LoRA, 1 x Pollinations, in that order."""
    from services import image_jobs
    from services.image_backends import sana_prompt

    host = _host_url(base_url)
    slots = parse_image_mix(Config.IMAGE_MIX, len(prompts))
    urls, sources = [], []
    for image_prompt, source in zip(prompts, slots):
        if source == "pollinations":
            urls.append(pollinations_backend.generate_images([image_prompt], mode)[0])
            sources.append("pollinations")
            continue
        use_lora = source == "lora"
        plain_prompt = sana_prompt.build_sana_prompt(image_prompt, level=level, mode=mode, plan=plan)
        final_prompt = (
            sana_prompt.build_sana_prompt(image_prompt, level=level, mode=mode, plan=plan, trigger=Config.SANA_TRIGGER)
            if use_lora else plain_prompt
        )
        image_id = uuid.uuid4().hex
        image_jobs.enqueue(
            image_id,
            prompt=final_prompt,
            negative_prompt=sana_prompt.NEGATIVE_PROMPT,
            height=Config.SANA_HEIGHT,
            width=Config.SANA_WIDTH,
            steps=Config.SANA_STEPS,
            guidance=Config.SANA_GUIDANCE,
            seed=sana_prompt.seed_for_prompt(plain_prompt),
            lora_path=Config.SANA_MIX_LORA_PATH if use_lora else "",
            backend="local",
        )
        urls.append(f"{host}/generated/{image_id}.png")
        sources.append("sana_lora" if use_lora else "sana_base")
    return urls, sources


def _generate_sana(prompts, mode, level=None, plan=None, base_url=None):
    from services import image_jobs
    from services.image_backends import sana_local, sana_prompt

    host = _host_url(base_url)
    prompts = list(prompts)
    fallback_urls = (
        pollinations_backend.generate_images(prompts, mode)
        if Config.IMAGE_FALLBACK_TO_POLLINATIONS
        else [None] * len(prompts)
    )
    # The trigger word only makes sense when the fine-tuned weights are loaded.
    # In remote mode the server prepends its own trigger (it knows whether it
    # loaded a LoRA), so the prompt is sent without one.
    trigger = sana_local.active_trigger() if Config.IMAGE_BACKEND == "local" else ""
    num_generated = max(0, min(Config.SANA_NUM_IMAGES, len(prompts)))

    images = []
    for index, image_prompt in enumerate(prompts):
        if index >= num_generated:
            images.append(fallback_urls[index] or f"{host}/generated/{PLACEHOLDER_NAME}")
            continue
        # The seed is derived from the prompt without the trigger so base and
        # fine-tuned models get the same seed for the same request.
        plain_prompt = sana_prompt.build_sana_prompt(image_prompt, level=level, mode=mode, plan=plan)
        final_prompt = sana_prompt.build_sana_prompt(
            image_prompt, level=level, mode=mode, plan=plan, trigger=trigger
        )
        image_id = uuid.uuid4().hex
        image_jobs.enqueue(
            image_id,
            prompt=final_prompt,
            negative_prompt=sana_prompt.NEGATIVE_PROMPT,
            height=Config.SANA_HEIGHT,
            width=Config.SANA_WIDTH,
            steps=Config.SANA_STEPS,
            guidance=Config.SANA_GUIDANCE,
            seed=sana_prompt.seed_for_prompt(plain_prompt),
            fallback_url=fallback_urls[index],
        )
        images.append(f"{host}/generated/{image_id}.png")
    return images
