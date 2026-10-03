"""Process-wide GPU lock and lazy model registry.

Only one heavy model is allowed on the GPU at a time (the laptop has 4 GB of
VRAM). Every local model (Qwen analyzer, SANA pipeline) is loaded through
`use_model`, which holds the GPU lock for the whole load + inference and
evicts any other model first.

torch is imported lazily so the app still starts on machines without it
(ANALYZER_ENABLED=false, IMAGE_BACKEND=pollinations).
"""
import gc
import threading
import time
from contextlib import contextmanager

GPU_LOCK = threading.RLock()

_models = {}      # name -> loaded object
_unloaders = {}   # name -> optional callable(obj) run before the object is dropped
_stats = {}       # name -> {"load_s": float, "loads": int}


def free_gpu_memory():
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def is_loaded(name):
    return name in _models


def loaded_models():
    return list(_models.keys())


def load_stats(name):
    return dict(_stats.get(name, {}))


def unload(name):
    with GPU_LOCK:
        obj = _models.pop(name, None)
        unloader = _unloaders.pop(name, None)
        if obj is None:
            return False
        try:
            if unloader:
                unloader(obj)
        except Exception as exc:
            print(f"MODEL MANAGER: unloader for {name} failed: {exc}")
        del obj
        free_gpu_memory()
        print(f"MODEL MANAGER: unloaded {name}")
        return True


def unload_all(except_name=None):
    with GPU_LOCK:
        for name in list(_models.keys()):
            if name != except_name:
                unload(name)


@contextmanager
def use_model(name, loader, unloader=None, exclusive=True):
    """Yield the model registered under `name`, loading it if needed.

    The GPU lock is held for the whole `with` block. With exclusive=True
    every other registered model is unloaded before this one is loaded.
    """
    with GPU_LOCK:
        if name not in _models:
            if exclusive:
                unload_all(except_name=name)
            started = time.perf_counter()
            _models[name] = loader()
            if unloader:
                _unloaders[name] = unloader
            elapsed = time.perf_counter() - started
            stats = _stats.setdefault(name, {"load_s": 0.0, "loads": 0})
            stats["load_s"] = round(elapsed, 3)
            stats["loads"] += 1
            print(f"MODEL MANAGER: loaded {name} in {elapsed:.1f}s")
        yield _models[name]
