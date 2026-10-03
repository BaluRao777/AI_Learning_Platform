"""One-step setup for the AI Learning Platform (portable bundle).

Run it through the launcher for your OS (it finds a suitable Python first):
    Windows:      setup.bat
    Linux/macOS:  bash setup.sh

or directly:  python setup_project.py [--yes] [--image-mode local|mixed|pollinations] [--smoke]

What it does:
  1. detects the operating system
  2. checks whether this computer can run the project (Python, Node.js, disk, RAM, NVIDIA GPU,
     internet, bundled models) and picks a profile: full GPU, small GPU (laptop) or basic (no local AI)
  3. creates a virtual environment in .venv and installs the right PyTorch build + pinned requirements
  4. prepares the frontend (bundled node_modules, or npm ci as a fallback)
  5. asks for the Gemini API key and writes backend/.env with this computer's absolute paths
  6. creates the database, runs the tests and checks the Gemini key
  7. writes RUN_COMMANDS.txt with the exact commands to start the backend and the frontend

Only the Python standard library is used, so this runs before anything is installed.
The API key is never printed or written anywhere except backend/.env.
"""
import argparse
import datetime
import getpass
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
VENV = os.path.join(ROOT, ".venv")
MODELS = os.path.join(ROOT, "models")
ENV_FILE = os.path.join(BACKEND, ".env")
ENV_EXAMPLE = os.path.join(BACKEND, ".env.example")
REPORT_FILE = os.path.join(ROOT, "setup_report.txt")
RUN_FILE = os.path.join(ROOT, "RUN_COMMANDS.txt")

TORCH_VERSION = "2.14.1"
TORCH_INDEX = "https://download.pytorch.org/whl/{tag}"
PY_MIN, PY_MAX = (3, 10), (3, 13)
NODE_MIN = 18
DISK_MIN_GB, DISK_WARN_GB = 10, 15
GPU_FULL_GB, GPU_MIN_GB = 16, 4

QWEN_DIR = os.path.join(MODELS, "Qwen2.5-1.5B-Instruct")
SANA_DIR = os.path.join(MODELS, "SANA1.5_1.6B_1024px_diffusers")
LORA_FILE = os.path.join(BACKEND, "models_store", "lora", "pytorch_lora_weights.safetensors")
REQUIRED_MODEL_FILES = [
    os.path.join(QWEN_DIR, "model.safetensors"),
    os.path.join(QWEN_DIR, "config.json"),
    os.path.join(QWEN_DIR, "tokenizer.json"),
    os.path.join(SANA_DIR, "model_index.json"),
    os.path.join(SANA_DIR, "transformer", "diffusion_pytorch_model.safetensors"),
    os.path.join(SANA_DIR, "text_encoder", "model-00001-of-00002.safetensors"),
    os.path.join(SANA_DIR, "text_encoder", "model-00002-of-00002.safetensors"),
    os.path.join(SANA_DIR, "vae", "diffusion_pytorch_model.safetensors"),
    LORA_FILE,
]

IS_WINDOWS = platform.system() == "Windows"
REPORT = []


# ----------------------------------------------------------------------------- helpers
def say(text=""):
    print(text, flush=True)
    REPORT.append(text)


def step(title):
    say("")
    say("=" * 70)
    say(title)
    say("=" * 70)


def fail(message):
    say("")
    say("SETUP STOPPED: " + message)
    write_report()
    sys.exit(1)


def ask(question, default="", yes_mode=False):
    if yes_mode:
        return default
    answer = input(f"{question} [{default}]: ").strip() if default else input(f"{question}: ").strip()
    return answer or default


def ask_yes_no(question, default=True, yes_mode=False):
    if yes_mode:
        return default
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{question} [{suffix}]: ").strip().lower()
    return default if not answer else answer in ("y", "yes")


def run(cmd, cwd=None, env=None, check=True, capture=False):
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    say(f"  $ {printable}")
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None)
    if check and result.returncode != 0:
        if capture and result.stdout:
            say(result.stdout[-3000:])
        fail(f"command failed with exit code {result.returncode}: {printable}")
    return result


def output_of(cmd):
    try:
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30).stdout
    except Exception:
        return ""


def venv_python():
    return os.path.join(VENV, "Scripts", "python.exe") if IS_WINDOWS else os.path.join(VENV, "bin", "python")


def npm_cmd():
    return shutil.which("npm.cmd" if IS_WINDOWS else "npm") or shutil.which("npm")


def total_ram_gb():
    try:
        if IS_WINDOWS:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024 ** 3
        if platform.system() == "Darwin":
            return int(output_of(["sysctl", "-n", "hw.memsize"]).strip()) / 1024 ** 3
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024 ** 2
    except Exception:
        pass
    return 0.0


def detect_gpu():
    """Return dict(name, vram_gb, driver, cuda, compute_cap) for the first NVIDIA GPU, or None."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    line = output_of([smi, "--query-gpu=name,memory.total,driver_version,compute_cap",
                      "--format=csv,noheader,nounits"]).strip().splitlines()
    if not line:
        return None
    parts = [p.strip() for p in line[0].split(",")]
    header = output_of([smi])
    cuda = re.search(r"CUDA Version:\s*([0-9]+\.[0-9]+)", header)
    try:
        return {
            "name": parts[0],
            "vram_gb": round(float(parts[1]) / 1024, 1),
            "driver": parts[2],
            "compute_cap": float(parts[3]) if len(parts) > 3 and parts[3] not in ("", "[N/A]") else 0.0,
            "cuda": float(cuda.group(1)) if cuda else 0.0,
        }
    except (ValueError, IndexError):
        return None


def torch_build_for(gpu):
    """Pick the PyTorch wheel index for this GPU/driver, or None for CPU."""
    if not gpu or gpu["cuda"] < 12.0:
        return None
    if gpu["compute_cap"] and gpu["compute_cap"] < 7.5:
        return "cu126"  # CUDA 13 builds no longer support GPUs older than Turing
    if gpu["cuda"] >= 13.2:
        return "cu132"
    if gpu["cuda"] >= 13.0:
        return "cu130"
    return "cu126"


def internet_ok():
    for url in ("https://pypi.org/simple/pip/", "https://download.pytorch.org/whl/"):
        try:
            urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15)
        except Exception:
            return False
    return True


def write_report():
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(REPORT) + "\n")


# ----------------------------------------------------------------------------- steps
def detect_os():
    step("STEP 1 - Operating system")
    system = platform.system()
    info = {
        "system": system,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_path": sys.executable,
    }
    if system == "Linux":
        try:
            with open("/etc/os-release") as fh:
                pretty = [l.split("=", 1)[1].strip().strip('"') for l in fh if l.startswith("PRETTY_NAME=")]
            info["distro"] = pretty[0] if pretty else ""
        except OSError:
            info["distro"] = ""
    say(f"  OS          : {system} {info['release']} ({info.get('distro') or info['version']})")
    say(f"  Architecture: {info['machine']}")
    say(f"  Python      : {info['python']} ({sys.executable})")
    if system not in ("Windows", "Linux", "Darwin"):
        fail(f"unsupported operating system: {system}")
    return info


def check_capability(os_info, args):
    step("STEP 2 - Can this computer run the project?")
    problems, warnings = [], []

    version = sys.version_info[:2]
    py_ok = PY_MIN <= version <= PY_MAX
    say(f"  [{'OK' if py_ok else 'FAIL'}] Python {platform.python_version()} (needs 3.10 - 3.13)")
    if not py_ok:
        problems.append("Install Python 3.11 (https://www.python.org/downloads/) and run setup again.")

    node = shutil.which("node")
    node_version = output_of([node, "-v"]).strip() if node else ""
    node_major = int(re.findall(r"\d+", node_version)[0]) if re.findall(r"\d+", node_version) else 0
    npm = npm_cmd()
    node_ok = bool(node) and node_major >= NODE_MIN and bool(npm)
    say(f"  [{'OK' if node_ok else 'FAIL'}] Node.js {node_version or 'not found'} + npm "
        f"{'found' if npm else 'not found'} (needs Node {NODE_MIN}+)")
    if not node_ok:
        problems.append("Install Node.js LTS (https://nodejs.org/) and run setup again.")

    free_gb = shutil.disk_usage(ROOT).free / 1024 ** 3
    disk_ok = free_gb >= DISK_MIN_GB
    say(f"  [{'OK' if free_gb >= DISK_WARN_GB else ('WARN' if disk_ok else 'FAIL')}] Free disk space "
        f"{free_gb:.0f} GB (needs about {DISK_WARN_GB} GB for the Python environment)")
    if not disk_ok:
        problems.append(f"Free at least {DISK_MIN_GB} GB of disk space.")
    elif free_gb < DISK_WARN_GB:
        warnings.append("Low disk space.")

    ram = total_ram_gb()
    say(f"  [{'OK' if ram >= 12 else 'WARN'}] RAM {ram:.1f} GB "
        f"(local image generation used about 9-11 GB on the workstation)")
    if ram and ram < 12:
        warnings.append("Less than 12 GB RAM: local AI will use the swap/page file and be slow. "
                        "On Windows, raise the page file to about 16 GB.")

    gpu = detect_gpu()
    if gpu:
        say(f"  [INFO] NVIDIA GPU: {gpu['name']}, {gpu['vram_gb']} GB VRAM, driver {gpu['driver']}, "
            f"CUDA {gpu['cuda']}, compute capability {gpu['compute_cap'] or 'unknown'}")
    else:
        say("  [INFO] No NVIDIA GPU found (nvidia-smi not available)")

    missing = [p for p in REQUIRED_MODEL_FILES if not os.path.isfile(p)]
    say(f"  [{'OK' if not missing else 'WARN'}] Bundled models "
        f"{'present' if not missing else 'MISSING: ' + ', '.join(os.path.relpath(m, ROOT) for m in missing)}")

    net = internet_ok()
    say(f"  [{'OK' if net else 'FAIL'}] Internet access to pypi.org and download.pytorch.org "
        f"(needed once, to install the Python packages)")
    if not net and not args.skip_install:
        problems.append("Connect to the internet (needed once to install the Python packages).")

    # ---- profile
    build = torch_build_for(gpu)
    if os_info["machine"].lower() not in ("x86_64", "amd64") and os_info["system"] != "Darwin":
        reason = f"architecture {os_info['machine']} is not supported for local AI"
        profile = "basic"
    elif missing:
        reason = "bundled model files are missing"
        profile = "basic"
    elif not gpu:
        reason = "no NVIDIA GPU"
        profile = "basic"
    elif build is None:
        reason = f"NVIDIA driver too old (CUDA {gpu['cuda']}, need 12.0 or newer)"
        profile = "basic"
    elif gpu["vram_gb"] < GPU_MIN_GB - 0.5:
        reason = f"GPU has only {gpu['vram_gb']} GB VRAM (need about {GPU_MIN_GB} GB)"
        profile = "basic"
    elif gpu["vram_gb"] >= GPU_FULL_GB:
        reason = f"{gpu['vram_gb']} GB VRAM"
        profile = "full"
    else:
        reason = f"{gpu['vram_gb']} GB VRAM: 4-bit models + CPU offload"
        profile = "small"

    labels = {
        "full": "FULL GPU   - local Qwen + local SANA, full precision, no offload",
        "small": "SMALL GPU  - local Qwen 4-bit + local SANA 4-bit text encoder, CPU offload, 512x512 (laptop mode)",
        "basic": "BASIC      - no local AI: Gemini text + Pollinations images (the original app)",
    }
    say("")
    say(f"  Profile: {labels[profile]}  ({reason})")
    if profile != "basic":
        say(f"  PyTorch build: torch {TORCH_VERSION} + {build}")

    for w in warnings:
        say(f"  WARNING: {w}")
    if problems:
        say("")
        say("  This computer cannot run the project yet:")
        for p in problems:
            say(f"   - {p}")
        fail("requirements not met (see above)")
    say("")
    say("  Result: this computer CAN run the project" +
        (" (local AI enabled)." if profile != "basic" else " in basic mode (no local AI)."))
    return {"profile": profile, "gpu": gpu, "torch_build": build, "ram_gb": round(ram, 1),
            "free_disk_gb": round(free_gb, 1)}


def create_environment(cap, args):
    step("STEP 3 - Python environment and packages")
    if not os.path.isfile(venv_python()):
        run([sys.executable, "-m", "venv", VENV])
    else:
        say(f"  Reusing existing environment: {VENV}")
    py = venv_python()
    if args.skip_install:
        say("  --skip-install given: package installation skipped.")
        return
    run([py, "-m", "pip", "install", "--upgrade", "pip"])

    if cap["profile"] == "basic":
        tag = None if platform.system() == "Darwin" else "cpu"
    else:
        tag = cap["torch_build"]
    torch_cmd = [py, "-m", "pip", "install", f"torch=={TORCH_VERSION}"]
    if tag:
        torch_cmd += ["--index-url", TORCH_INDEX.format(tag=tag)]
    if cap["profile"] != "basic":
        say(f"  Installing PyTorch {TORCH_VERSION} ({tag}) - this is a large download (2-4 GB).")
        run(torch_cmd)
    run([py, "-m", "pip", "install", "-r", os.path.join(ROOT, "requirements-portable.txt")])
    if cap["profile"] != "basic":
        run([py, "-m", "pip", "install", "-r", os.path.join(BACKEND, "requirements-ai-portable.txt")])
        check = run([py, "-c", "import torch, diffusers, transformers, bitsandbytes;"
                               "print(torch.__version__, torch.cuda.is_available())"], capture=True, check=False)
        say(f"  torch check: {check.stdout.strip()}")
        if check.returncode != 0 or not check.stdout.strip().endswith("True"):
            say("  WARNING: PyTorch cannot use the GPU. Switching to BASIC profile (no local AI).")
            cap["profile"] = "basic"


def prepare_frontend(args):
    step("STEP 4 - Frontend")
    launcher = os.path.join(FRONTEND, "node_modules", "react-scripts", "bin", "react-scripts.js")
    if os.path.isfile(launcher):
        say("  Using the bundled node_modules (no download needed).")
        if not IS_WINDOWS:
            bin_dir = os.path.join(FRONTEND, "node_modules", ".bin")
            for name in os.listdir(bin_dir):
                path = os.path.join(bin_dir, name)
                if os.path.isfile(path):
                    os.chmod(path, os.stat(path).st_mode | 0o111)
            say("  Made node_modules/.bin launchers executable.")
    elif args.skip_install:
        say("  WARNING: node_modules missing and --skip-install given; run 'npm ci' in frontend/ yourself.")
    else:
        say("  node_modules not found - installing with npm ci.")
        run([npm_cmd(), "ci"], cwd=FRONTEND)


def read_env(path):
    values = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                match = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
                if match:
                    values[match.group(1)] = match.group(2).strip('"').strip("'")
    return values


def portable_path(path):
    return path.replace("\\", "/")


def configure_env(cap, args):
    step("STEP 5 - Configuration (backend/.env)")
    existing = read_env(ENV_FILE)
    if existing:
        backup = f"{ENV_FILE}.backup.{datetime.datetime.now():%Y%m%d_%H%M%S}"
        shutil.copy2(ENV_FILE, backup)
        say(f"  Existing .env backed up to {os.path.relpath(backup, ROOT)}")

    # ---- Gemini key (never printed)
    key = os.environ.get("GEMINI_API_KEY", "") if args.api_key_from_env else ""
    if not key and not args.yes:
        say("  Get a key at https://aistudio.google.com/ (Get API key).")
        prompt = "  Enter your Gemini API key" + (" (Enter = keep the current one)" if existing.get("GEMINI_API_KEY") else "")
        key = getpass.getpass(prompt + ": ").strip()
    if not key:
        key = existing.get("GEMINI_API_KEY", "")
    if not key:
        say("  WARNING: no Gemini API key. Explanations will come from the Wikipedia fallback "
            "until you add GEMINI_API_KEY to backend/.env.")
    model = ask("  Gemini model", existing.get("GEMINI_MODEL") or "gemini-3.5-flash-lite", args.yes)

    # ---- image mode
    profile = cap["profile"]
    if profile == "basic":
        image_mode = "pollinations"
        say("  Image mode: pollinations (basic profile, no local GPU)")
    else:
        image_mode = args.image_mode or ask(
            "  Image mode: local = SANA base only (recommended) | "
            "mixed = 2 SANA base + 1 SANA LoRA + 2 Pollinations | pollinations = original",
            "local", args.yes)
        if image_mode not in ("local", "mixed", "pollinations"):
            image_mode = "local"

    full = profile == "full"
    settings = {
        "GEMINI_API_KEY": key,
        "GEMINI_MODEL": model,
        "JWT_SECRET": existing.get("JWT_SECRET") or secrets.token_urlsafe(48),
        "JWT_EXPIRES_HOURS": existing.get("JWT_EXPIRES_HOURS", "24"),
        "FLASK_ENV": "development",
        "HOST": "0.0.0.0",
        "PORT": "5000",
        "CORS_ORIGINS": "http://localhost:3000",
        "MAX_TOPIC_LENGTH": "120",
        "RATE_LIMIT_PER_MINUTE": "30",
        "ANALYZER_ENABLED": "false" if profile == "basic" else "true",
        "QWEN_MODEL_ID": f'"{portable_path(QWEN_DIR)}"',
        "QWEN_LOAD_IN_4BIT": "false" if full else "true",
        "QWEN_UNLOAD_AFTER_USE": "false" if full else "true",
        "QWEN_MAX_NEW_TOKENS": "512",
        "IMAGE_BACKEND": image_mode,
        "SANA_MODEL_ID": f'"{portable_path(SANA_DIR)}"',
        "SANA_LORA_PATH": "",
        "SANA_LORA_SCALE": "1.0",
        "SANA_FUSED_TRANSFORMER_PATH": "",
        "SANA_TEXT_ENCODER_4BIT": "false" if full else "true",
        "SANA_OFFLOAD": "none" if full else "model",
        "SANA_HEIGHT": "512",
        "SANA_WIDTH": "512",
        "SANA_STEPS": "20",
        "SANA_GUIDANCE": "4.5",
        "SANA_NUM_IMAGES": "5",
        "SANA_TRIGGER": "edudiag",
        "GENERATED_IMAGES_DIR": "generated_images",
        "SANA_REMOTE_URL": "",
        "SANA_REMOTE_TOKEN": "",
        "IMAGE_FALLBACK_TO_POLLINATIONS": "false",
        "IMAGE_MIX": "base:2,lora:1,pollinations:2",
        "SANA_MIX_LORA_PATH": f'"{portable_path(LORA_FILE)}"',
        "IMAGE_PROXY_TIMEOUT_SECONDS": "30",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    lines = [
        f"# Written by setup_project.py on {datetime.datetime.now():%Y-%m-%d %H:%M} for this computer.",
        f"# Profile: {profile}. Paths below are absolute paths on this computer.",
    ]
    lines += [f"{k}={v}" for k, v in settings.items()]
    with open(ENV_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    if not IS_WINDOWS:
        os.chmod(ENV_FILE, 0o600)
    say(f"  Wrote backend/.env (profile {profile}, image mode {image_mode}, "
        f"Gemini key {'set' if key else 'NOT set'}, model {model}).")
    say(f"  Model paths set to: {portable_path(MODELS)}")
    cap["image_mode"] = image_mode
    cap["gemini_key_set"] = bool(key)


def finish_checks(cap, args):
    step("STEP 6 - Database and checks")
    py = venv_python()
    run([py, "init_db.py"], cwd=BACKEND)
    problems = cap.setdefault("problems", [])
    start = run([py, "-c", "import app; print('backend imports OK')"], cwd=BACKEND, check=False, capture=True)
    say("  Backend start check: " + ("OK" if start.returncode == 0 else "FAILED"))
    if start.returncode != 0:
        say((start.stdout or "")[-2000:])
        problems.append("the backend cannot start (see the error above)")
    tests = run([py, "-m", "pytest", "tests", "-q"], cwd=BACKEND, check=False, capture=True)
    last = (tests.stdout or "").strip().splitlines()[-1:] or ["(no output)"]
    say(f"  Tests: {last[0]}")
    cap["tests"] = last[0]
    if tests.returncode != 0:
        say((tests.stdout or "")[-2000:])
        problems.append(f"tests failed ({last[0]})")
    if cap["gemini_key_set"]:
        gemini = run([py, os.path.join("scripts", "test_gemini.py")], cwd=BACKEND, check=False, capture=True)
        result = [l for l in (gemini.stdout or "").splitlines() if l.startswith(("RESULT", "ERROR"))]
        say("  Gemini: " + (" | ".join(result) if result else "(no result)"))
        cap["gemini"] = "PASS" if gemini.returncode == 0 else "FAIL"
        if gemini.returncode != 0:
            problems.append("the Gemini key/model check failed (fix GEMINI_API_KEY / GEMINI_MODEL in backend/.env)")
    else:
        cap["gemini"] = "not tested (no key)"
    if args.smoke and cap["profile"] != "basic":
        size = "512"
        offload = "none" if cap["profile"] == "full" else "model"
        smoke = [py, os.path.join("scripts", "smoke_local_ai.py"), "--size", size, "--offload", offload,
                 "--out", os.path.join(ROOT, "smoke.png")]
        if cap["profile"] == "full":
            smoke.append("--no-4bit")
        result = run(smoke, cwd=BACKEND, check=False, capture=True)
        for line in (result.stdout or "").splitlines():
            if line.startswith(("QWEN", "SANA image", "SANA total")):
                say("  " + line)
        cap["smoke"] = "PASS" if result.returncode == 0 else "FAIL"
        if result.returncode != 0:
            say((result.stdout or "")[-2000:])
            problems.append("the GPU smoke test failed")


def write_run_commands(os_info, cap):
    step("STEP 7 - Run commands")
    py = venv_python()
    if IS_WINDOWS:
        backend_cmd = f'cd /d "{BACKEND}"\n  "{py}" app.py'
        frontend_cmd = f'cd /d "{FRONTEND}"\n  npm start'
        shell = "Command Prompt (cmd)"
        tests_cmd = f'cd /d "{BACKEND}"\n  "{py}" -m pytest tests -q'
        smoke_cmd = f'cd /d "{BACKEND}"\n  "{py}" scripts\\smoke_local_ai.py --size 512'
    else:
        backend_cmd = f'cd "{BACKEND}"\n  "{py}" app.py'
        frontend_cmd = f'cd "{FRONTEND}"\n  npm start'
        shell = "a terminal"
        tests_cmd = f'cd "{BACKEND}"\n  "{py}" -m pytest tests -q'
        smoke_cmd = f'cd "{BACKEND}"\n  "{py}" scripts/smoke_local_ai.py --size 512'
    text = f"""HOW TO RUN THE PROJECT ON THIS COMPUTER
Generated by setup_project.py on {datetime.datetime.now():%Y-%m-%d %H:%M}
OS: {os_info['system']} {os_info['release']} ({os_info['machine']})
Profile: {cap['profile']}   Image mode: {cap.get('image_mode')}   Gemini key set: {cap.get('gemini_key_set')}

Open two windows of {shell}.

1) BACKEND (window 1)
  {backend_cmd}

  Wait for:  Running on http://127.0.0.1:5000
  The first line starting with CONFIG shows the active settings.

2) FRONTEND (window 2)
  {frontend_cmd}

3) OPEN IN THE BROWSER
  http://localhost:3000
  Sign up, log in, enter a topic and press Generate.

STOP: press Ctrl+C in each window.

OTHER COMMANDS
  Run the tests:
  {tests_cmd}

  GPU smoke test (local AI profiles only):
  {smoke_cmd}

CHANGE SETTINGS
  Edit backend/.env, then restart the backend.
  IMAGE_BACKEND=local         SANA base images (local GPU)
  IMAGE_BACKEND=mixed         2 SANA base + 1 SANA LoRA + 2 Pollinations (IMAGE_MIX)
  IMAGE_BACKEND=pollinations  original behaviour, no GPU needed
  ANALYZER_ENABLED=false      turn the local Qwen analyzer off
  Re-run the setup at any time:  {'setup.bat' if IS_WINDOWS else 'bash setup.sh'}
"""
    with open(RUN_FILE, "w", encoding="utf-8") as fh:
        fh.write(text)
    say(f"  Wrote {RUN_FILE}")
    say("")
    say(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="non-interactive: accept all defaults")
    parser.add_argument("--api-key-from-env", action="store_true",
                        help="read the Gemini key from the GEMINI_API_KEY environment variable")
    parser.add_argument("--image-mode", choices=["local", "mixed", "pollinations"])
    parser.add_argument("--skip-install", action="store_true", help="do not install Python/Node packages")
    parser.add_argument("--smoke", action="store_true", help="also load the models and generate one test image")
    args = parser.parse_args()

    say(f"AI Learning Platform - setup ({datetime.datetime.now():%Y-%m-%d %H:%M})")
    say(f"Project folder: {ROOT}")
    os_info = detect_os()
    cap = check_capability(os_info, args)
    if not ask_yes_no("\nContinue with the installation?", True, args.yes):
        fail("cancelled by the user")
    create_environment(cap, args)
    prepare_frontend(args)
    configure_env(cap, args)
    finish_checks(cap, args)
    write_run_commands(os_info, cap)
    problems = cap.get("problems") or []
    if problems:
        say("SETUP FINISHED WITH PROBLEMS:")
        for problem in problems:
            say(f"  - {problem}")
        say("See setup_report.txt for the full log.")
    else:
        say("SETUP COMPLETE - all checks passed. Commands are in RUN_COMMANDS.txt; this log is in setup_report.txt.")
    with open(os.path.join(ROOT, "setup_result.json"), "w", encoding="utf-8") as fh:
        json.dump({"os": os_info, **{k: v for k, v in cap.items() if k != "gpu"}, "gpu": cap.get("gpu")}, fh, indent=2)
    write_report()
    if problems:
        sys.exit(2)


if __name__ == "__main__":
    main()
