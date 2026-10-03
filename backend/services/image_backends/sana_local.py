"""Local SANA 1.5 pipeline: lazy loader + generate().

Loaded on the first job, inside the image worker thread, through
model_manager (GPU lock, evicts Qwen first). Designed for the laptop
(4 GB VRAM / 8 GB RAM): 4-bit text encoder, bf16 transformer + VAE,
CPU offload, VAE tiling/slicing, and one retry with sequential offload on
CUDA out-of-memory.
"""
import os
import time
from dataclasses import dataclass, replace

from config import Config
from services import model_manager

SANA_MODEL_NAME = "sana_pipeline"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The SANA 1024px checkpoints snap requests to ~1024px aspect-ratio bins when
# resolution binning is on, which would silently render 1024x1024 and then
# downscale. Binning is therefore only used at native resolution.
NATIVE_RESOLUTION = 1024


@dataclass(frozen=True)
class SanaSettings:
    model_id: str
    lora_path: str = ""
    lora_scale: float = 1.0
    fused_transformer_path: str = ""
    text_encoder_4bit: bool = True
    offload: str = "model"  # none | model | sequential

    @property
    def uses_finetune(self):
        return bool(self.lora_path or self.fused_transformer_path)


def _resolve(path):
    if not path:
        return ""
    return path if os.path.isabs(path) else os.path.join(BACKEND_DIR, path)


def resolve_path(path):
    return _resolve(path)


def settings_from_config():
    return SanaSettings(
        model_id=Config.SANA_MODEL_ID,
        lora_path=_resolve(Config.SANA_LORA_PATH),
        lora_scale=Config.SANA_LORA_SCALE,
        fused_transformer_path=_resolve(Config.SANA_FUSED_TRANSFORMER_PATH),
        text_encoder_4bit=Config.SANA_TEXT_ENCODER_4BIT,
        offload=Config.SANA_OFFLOAD,
    )


_active_settings = None  # settings the loaded pipeline was built with
_offload_override = None  # set to "sequential" after an OOM


def active_trigger():
    """Trigger word to prepend to prompts, or "" when no fine-tune is configured."""
    return Config.SANA_TRIGGER if settings_from_config().uses_finetune else ""


def load_pipeline(settings):
    import torch
    from diffusers import SanaPipeline, SanaTransformer2DModel

    dtype = torch.bfloat16
    kwargs = {"torch_dtype": dtype}

    if settings.fused_transformer_path:
        kwargs["transformer"] = SanaTransformer2DModel.from_pretrained(
            settings.fused_transformer_path, torch_dtype=dtype
        )

    if settings.text_encoder_4bit and torch.cuda.is_available():
        from transformers import AutoModel, BitsAndBytesConfig

        kwargs["text_encoder"] = AutoModel.from_pretrained(
            settings.model_id,
            subfolder="text_encoder",
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
            ),
            torch_dtype=dtype,
        )

    pipe = SanaPipeline.from_pretrained(settings.model_id, **kwargs)

    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()

    if not torch.cuda.is_available():
        pipe.to("cpu")
    elif settings.offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    elif settings.offload == "model":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")

    pipe.set_progress_bar_config(disable=True)
    return pipe


def _pipeline_key(settings):
    """Settings that require a new pipeline. The LoRA is not part of it: it is
    attached to / switched off on the loaded pipeline per image."""
    return replace(settings, lora_path="", lora_scale=1.0)


def _apply_lora(pipe, settings):
    """Enable the requested LoRA on the loaded pipeline, or switch adapters off for the base model."""
    loaded = getattr(pipe, "_edu_lora_path", "")
    wanted = "" if settings.fused_transformer_path else settings.lora_path
    if wanted and wanted != loaded:
        if loaded:
            pipe.unload_lora_weights()
        if os.path.isdir(wanted):
            pipe.load_lora_weights(wanted, adapter_name="edu")
        else:
            pipe.load_lora_weights(os.path.dirname(wanted), weight_name=os.path.basename(wanted), adapter_name="edu")
        pipe._edu_lora_path = wanted
        loaded = wanted
    if wanted:
        pipe.enable_lora()
        pipe.set_adapters(["edu"], [settings.lora_scale])
    elif loaded:
        pipe.disable_lora()


def _effective_settings(settings):
    if _offload_override and settings.offload != _offload_override:
        return replace(settings, offload=_offload_override)
    return settings


def _is_oom(exc):
    try:
        import torch

        if isinstance(exc, torch.OutOfMemoryError):
            return True
    except Exception:
        pass
    return "out of memory" in str(exc).lower()


def _generate_once(settings, prompt, negative_prompt, height, width, steps, guidance, seed):
    import torch

    global _active_settings
    key = _pipeline_key(settings)
    with model_manager.GPU_LOCK:
        if _active_settings is not None and _active_settings != key:
            model_manager.unload(SANA_MODEL_NAME)
        with model_manager.use_model(SANA_MODEL_NAME, lambda: load_pipeline(key)) as pipe:
            _active_settings = key
            _apply_lora(pipe, settings)
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            image = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                height=height,
                width=width,
                num_inference_steps=steps,
                guidance_scale=guidance,
                generator=torch.Generator(device="cpu").manual_seed(int(seed)),
                use_resolution_binning=max(height, width) >= NATIVE_RESOLUTION,
                # The LoRA is trained on plain captions (the diffusers training script does
                # not use SANA's "complex human instruction" prefix), so inference must not
                # add it either. Used for the base model too, to keep comparisons fair.
                complex_human_instruction=None,
            ).images[0]
            seconds = time.perf_counter() - started
            peak_vram_mb = (
                torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
            )
    info = {
        "seconds": round(seconds, 2),
        "peak_vram_mb": round(peak_vram_mb, 1),
        "offload": settings.offload,
        "lora": os.path.basename(settings.lora_path) if settings.lora_path else "none",
        "load_s": model_manager.load_stats(SANA_MODEL_NAME).get("load_s"),
    }
    return image, info


def generate(prompt, negative_prompt, height, width, steps, guidance, seed, settings=None):
    """Return (PIL.Image, info). Retries once with sequential offload on CUDA OOM."""
    global _offload_override
    settings = _effective_settings(settings or settings_from_config())
    try:
        return _generate_once(settings, prompt, negative_prompt, height, width, steps, guidance, seed)
    except Exception as exc:
        if not _is_oom(exc) or settings.offload == "sequential":
            raise
        print("SANA: CUDA out of memory, retrying once with sequential offload")
        model_manager.unload(SANA_MODEL_NAME)
        model_manager.free_gpu_memory()
        _offload_override = "sequential"
        settings = replace(settings, offload="sequential")
        return _generate_once(settings, prompt, negative_prompt, height, width, steps, guidance, seed)
