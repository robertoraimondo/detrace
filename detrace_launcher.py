from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
import zipfile
from math import ceil
from pathlib import Path
from tkinter import messagebox


if getattr(sys, "frozen", False):
    INSTALL_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS"))
else:
    INSTALL_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = INSTALL_DIR

def user_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "DeTrace"
    return Path.home() / ".detrace"


DATA_DIR = user_data_dir()
APP_DIR = DATA_DIR / ".detrace-app"
VENV_DIR = DATA_DIR / ".detrace-runtime"
SETUP_MARKER = DATA_DIR / "setup-complete.txt"
REQ_FILE = APP_DIR / "requirements.txt"
WHEELHOUSE_DIR = APP_DIR / "wheelhouse"
MVSEP_REPO_DIR = APP_DIR / "tools" / "Music-Source-Separation-Training"
TRUE_MVSEP_MODEL_DIR = APP_DIR / "models" / "mvsep_true_accordion"
TRUE_MVSEP_CONFIG_FILE = TRUE_MVSEP_MODEL_DIR / "config.yaml"
TRUE_MVSEP_CHECKPOINT_FILE = TRUE_MVSEP_MODEL_DIR / "checkpoint.ckpt"
MIN_MVSEP_CONFIG_BYTES = 512
MIN_MVSEP_CHECKPOINT_BYTES = 50 * 1024 * 1024
MVSEP_REPO_ZIP_URL = "https://github.com/ZFTurbo/Music-Source-Separation-Training/archive/refs/heads/main.zip"
TRUE_MVSEP_URLS_FILE = "download-urls.txt"
REQUIRED_MODULES = ("imageio_ffmpeg", "lameenc", "soundfile", "librosa", "webview", "torchcodec")
CUDA_TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu128"
TORCH_MODULES = ("torch", "torchaudio")
MVSEP_REQUIRED_MODULES = ("ml_collections", "beartype", "rotary_embedding_torch", "loralib", "matplotlib")
MVSEP_REQUIRED_PACKAGES = (
    "ml-collections",
    "beartype==0.14.1",
    "rotary-embedding-torch==0.3.5",
    "loralib",
    "matplotlib",
)
WINDOW_ICON_REFS: list[tk.PhotoImage] = []


def cpu_worker_count() -> int:
    detected = os.cpu_count() or 1
    configured = os.environ.get("DETRACE_CPU_THREADS", "").strip()
    if configured:
        try:
            return max(1, min(detected, int(configured)))
        except ValueError:
            return detected
    return detected


def subprocess_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    return env


def run(args: list[str], cwd: Path = APP_DIR) -> subprocess.CompletedProcess[str]:
    startupinfo = None
    creationflags = 0
    actual_cwd = cwd if cwd.exists() else INSTALL_DIR
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        args,
        cwd=str(actual_cwd),
        text=True,
        capture_output=True,
        check=False,
        env=subprocess_environment(),
        startupinfo=startupinfo,
        creationflags=creationflags,
    )


def run_logged(args: list[str], ui: dict, cwd: Path = APP_DIR) -> subprocess.CompletedProcess[str]:
    ui_log(ui, f"> {' '.join(args)}")
    startupinfo = None
    creationflags = 0
    actual_cwd = cwd if cwd.exists() else INSTALL_DIR
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen(
        args,
        cwd=str(actual_cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=subprocess_environment(),
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        clean = line.rstrip()
        if clean:
            lines.append(clean)
            ui_log(ui, clean)
    returncode = process.wait()
    ui_log(ui, f"Exit code: {returncode}")
    return subprocess.CompletedProcess(args, returncode, "\n".join(lines), "")


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def setup_repair_requested() -> bool:
    return os.environ.get("DETRACE_FORCE_REPAIR_SETUP", "").strip().lower() in {"1", "true", "yes"}


def find_python() -> list[str] | None:
    if command_exists("python"):
        result = run(["python", "--version"])
        if result.returncode == 0:
            return ["python"]
    if command_exists("py"):
        result = run(["py", "-3", "--version"])
        if result.returncode == 0:
            return ["py", "-3"]
    return None


def install_python(ui: dict) -> list[str]:
    if not command_exists("winget"):
        raise RuntimeError(
            "Python is not installed and winget is not available. Install Python 3.11+ from python.org, then run DeTrace again."
        )

    ui_status(ui, "Installing Python 3.11 with winget...")
    ui_item(ui, "python", "Missing - installing")
    ui_log(ui, "Python was not found. Installing Python 3.11 with winget.")
    ui_busy(ui, True)
    result = run_logged(
        [
            "winget",
            "install",
            "--id",
            "Python.Python.3.11",
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        ui,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Python installation failed.")

    os.environ["Path"] = (
        os.environ.get("Path", "")
        + ";"
        + os.environ.get("LOCALAPPDATA", "")
        + r"\Programs\Python\Python311"
        + ";"
        + os.environ.get("LOCALAPPDATA", "")
        + r"\Programs\Python\Python311\Scripts"
    )
    python = find_python()
    if not python:
        raise RuntimeError("Python installed, but it is not available yet. Restart Windows or open DeTrace again.")
    ui_item(ui, "python", "Present")
    return python


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def check_module(runtime_python: Path, module: str) -> bool:
    if not runtime_python.exists():
        return False
    result = run(
        [
            str(runtime_python),
            "-c",
            f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec('{module}') else 1)",
        ]
    )
    return result.returncode == 0


def check_distribution_version(runtime_python: Path, package: str, version: str) -> bool:
    if not runtime_python.exists():
        return False
    result = run(
        [
            str(runtime_python),
            "-c",
            (
                "from importlib.metadata import version; "
                f"raise SystemExit(0 if version('{package}') == '{version}' else 1)"
            ),
        ]
    )
    return result.returncode == 0


def nvidia_gpu_available() -> bool:
    if os.name != "nt":
        return command_exists("nvidia-smi")
    result = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    return result.returncode == 0 and bool(result.stdout.strip())


def torch_cuda_ready(runtime_python: Path) -> bool:
    if not runtime_python.exists():
        return False
    result = run(
        [
            str(runtime_python),
            "-c",
            "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)",
        ]
    )
    return result.returncode == 0


def accelerator_ready(runtime_python: Path) -> bool:
    return not nvidia_gpu_available() or torch_cuda_ready(runtime_python)


def missing_required_modules(runtime_python: Path) -> list[str]:
    return [module for module in REQUIRED_MODULES if not check_module(runtime_python, module)]


def app_requirements_ready(runtime_python: Path) -> bool:
    return runtime_python.exists() and not missing_required_modules(runtime_python)


def valid_file(path: Path, minimum_size: int) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size >= minimum_size


def mvsep_ready() -> bool:
    return (MVSEP_REPO_DIR / "inference.py").exists()


def true_mvsep_config_ready() -> bool:
    if not valid_file(TRUE_MVSEP_CONFIG_FILE, MIN_MVSEP_CONFIG_BYTES):
        return False
    try:
        text = TRUE_MVSEP_CONFIG_FILE.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    required_stems = ("accordion", "piano")
    target_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("target_instrument:")]
    target_is_multi_stem = not target_lines or any(line in {"target_instrument: null", "target_instrument: none"} for line in target_lines)
    return all(stem in text for stem in required_stems) and target_is_multi_stem


def true_mvsep_ready() -> bool:
    return true_mvsep_config_ready() and valid_file(TRUE_MVSEP_CHECKPOINT_FILE, MIN_MVSEP_CHECKPOINT_BYTES)


def parse_true_mvsep_url_file(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "", ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "", ""

    config_url = ""
    checkpoint_url = ""
    positional: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            key = key.lower().replace("-", "_")
            if key in {"config", "config_url", "detrace_mvsep_true_config_url"}:
                config_url = value
            elif key in {"checkpoint", "checkpoint_url", "ckpt", "ckpt_url", "detrace_mvsep_true_ckpt_url"}:
                checkpoint_url = value
        else:
            positional.append(line)

    if not config_url and positional:
        config_url = positional[0]
    if not checkpoint_url and len(positional) > 1:
        checkpoint_url = positional[1]
    return config_url, checkpoint_url


def true_mvsep_download_urls() -> tuple[str, str]:
    config_url = os.environ.get("DETRACE_MVSEP_TRUE_CONFIG_URL", "").strip()
    checkpoint_url = os.environ.get("DETRACE_MVSEP_TRUE_CKPT_URL", "").strip()
    for url_file in (
        TRUE_MVSEP_MODEL_DIR / TRUE_MVSEP_URLS_FILE,
        BUNDLE_DIR / "models" / "mvsep_true_accordion" / TRUE_MVSEP_URLS_FILE,
    ):
        file_config_url, file_checkpoint_url = parse_true_mvsep_url_file(url_file)
        config_url = config_url or file_config_url
        checkpoint_url = checkpoint_url or file_checkpoint_url
    return config_url, checkpoint_url


def true_mvsep_download_configured() -> bool:
    config_url, checkpoint_url = true_mvsep_download_urls()
    return bool(config_url or checkpoint_url)


def missing_mvsep_modules(runtime_python: Path) -> list[str]:
    if not runtime_python.exists():
        return list(MVSEP_REQUIRED_MODULES)
    return [module for module in MVSEP_REQUIRED_MODULES if not check_module(runtime_python, module)]


def mvsep_dependencies_ready(runtime_python: Path) -> bool:
    return runtime_python.exists() and not missing_mvsep_modules(runtime_python)


def setup_marker_ready() -> bool:
    runtime_python = venv_python()
    return (
        SETUP_MARKER.exists()
        and runtime_python.exists()
        and (APP_DIR / "server.py").exists()
        and (APP_DIR / "desktop_window.py").exists()
        and app_requirements_ready(runtime_python)
        and mvsep_ready()
        and mvsep_dependencies_ready(runtime_python)
        and true_mvsep_ready()
        and accelerator_ready(runtime_python)
    )


def write_setup_marker() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_MARKER.write_text("DeTrace setup complete\n", encoding="utf-8")


def refresh_requirement_status(ui: dict, runtime_python: Path | None = None) -> None:
    ui_item(ui, "python", "Present" if find_python() else "Missing")
    ui_item(ui, "runtime", "Present" if venv_python().exists() else "Missing")
    ui_item(ui, "mvsep", "Present" if mvsep_ready() else "Missing")
    ui_item(ui, "true_mvsep", "Present" if true_mvsep_ready() else "Missing")

    if runtime_python and runtime_python.exists():
        ui_item(ui, "ffmpeg", "Present" if check_module(runtime_python, "imageio_ffmpeg") else "Missing")
        ui_item(
            ui,
            "codecs",
            "Present"
            if check_module(runtime_python, "lameenc") and check_module(runtime_python, "soundfile")
            else "Missing",
        )
        ui_item(ui, "chords", "Present" if check_module(runtime_python, "librosa") else "Missing")
        ui_item(ui, "desktop", "Present" if check_module(runtime_python, "webview") else "Missing")
        if nvidia_gpu_available():
            ui_item(ui, "gpu", "CUDA ready" if torch_cuda_ready(runtime_python) else "NVIDIA found - CUDA setup needed")
        else:
            ui_item(ui, "gpu", "No NVIDIA GPU detected")
    else:
        ui_item(ui, "ffmpeg", "Waiting for runtime")
        ui_item(ui, "codecs", "Waiting for runtime")
        ui_item(ui, "chords", "Waiting for runtime")
        ui_item(ui, "desktop", "Waiting for runtime")
        ui_item(ui, "gpu", "Waiting for runtime")


def ensure_cuda_torch(ui: dict, runtime_python: Path) -> None:
    if not nvidia_gpu_available():
        ui_item(ui, "gpu", "No NVIDIA GPU detected")
        ui_log(ui, "No NVIDIA GPU detected. DeTrace will use CPU acceleration settings.")
        return

    if torch_cuda_ready(runtime_python):
        ui_item(ui, "gpu", "CUDA ready")
        ui_log(ui, "CUDA-enabled PyTorch is already available.")
        return

    ui_status(ui, "Repairing PyTorch CUDA support...")
    ui_item(ui, "gpu", "Adding CUDA PyTorch")
    ui_log(ui, f"CUDA is not available in the current PyTorch install. Reinstalling only the needed PyTorch packages from {CUDA_TORCH_INDEX_URL}")
    ui_busy(ui, True)
    result = run_logged(
        [
            str(runtime_python),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-cache-dir",
            *TORCH_MODULES,
            "--index-url",
            CUDA_TORCH_INDEX_URL,
        ],
        ui,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "CUDA PyTorch installation failed.")
    if not torch_cuda_ready(runtime_python):
        raise RuntimeError("CUDA PyTorch installed, but torch.cuda.is_available() is still false.")
    ui_item(ui, "gpu", "CUDA ready")
    ui_log(ui, "CUDA PyTorch is ready. NVIDIA GPU acceleration is enabled.")


def prepare_for_forced_repair(ui: dict) -> None:
    if not setup_repair_requested():
        return
    ui_status(ui, "Repairing interrupted setup...")
    ui_log(ui, "Installer requested a clean runtime repair. Rebuilding the Python runtime.")
    ui_busy(ui, True)
    if SETUP_MARKER.exists():
        SETUP_MARKER.unlink(missing_ok=True)
        ui_log(ui, f"Removed setup marker: {SETUP_MARKER}")
    if VENV_DIR.exists():
        retire_runtime_for_repair(ui)
    ui_item(ui, "runtime", "Repairing")


def retire_runtime_for_repair(ui: dict) -> None:
    try:
        shutil.rmtree(VENV_DIR)
        ui_log(ui, f"Removed old runtime: {VENV_DIR}")
        return
    except Exception as exc:
        retired = DATA_DIR / f".detrace-runtime-retired-{int(time.time())}"
        try:
            VENV_DIR.rename(retired)
            ui_log(ui, f"Old runtime was busy, so it was moved to: {retired}")
            return
        except Exception as rename_exc:
            raise RuntimeError(
                "DeTrace could not rebuild the Python runtime because files are still in use. "
                "Close every DeTrace/Python window, or restart Windows, then run DeTraceSetup.exe again."
            ) from rename_exc


def ensure_runtime(ui: dict) -> Path:
    ui_status(ui, "Checking system requirements...")
    ui_log(ui, "Checking system requirements.")
    refresh_requirement_status(ui)
    ui_progress(ui, 10)

    python = find_python()
    if not python:
        python = install_python(ui)
    else:
        ui_log(ui, f"Using Python command: {' '.join(python)}")

    if not venv_python().exists():
        ui_status(ui, "Creating DeTrace runtime...")
        ui_item(ui, "runtime", "Missing - creating")
        ui_log(ui, f"Creating runtime at {VENV_DIR}")
        ui_busy(ui, True)
        result = run_logged([*python, "-m", "venv", str(VENV_DIR)], ui)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Could not create runtime.")
        ui_item(ui, "runtime", "Present")
    else:
        ui_log(ui, f"Runtime already exists at {VENV_DIR}")

    runtime_python = venv_python()
    refresh_requirement_status(ui, runtime_python)
    ui_progress(ui, 45)

    missing_modules = missing_required_modules(runtime_python)
    if missing_modules:
        ui_status(ui, "Installing missing requirements...")
        ui_log(ui, f"Missing Python modules: {', '.join(missing_modules)}")
        ui_busy(ui, True)
        commands = []
        if WHEELHOUSE_DIR.exists() and any(WHEELHOUSE_DIR.iterdir()):
            commands.append(
                [
                    str(runtime_python),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    str(WHEELHOUSE_DIR),
                    "-r",
                    str(REQ_FILE),
                ]
            )
        else:
            commands.append([str(runtime_python), "-m", "pip", "install", "-r", str(REQ_FILE)])
        for command in commands:
            result = run_logged(command, ui)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout or "Requirement installation failed.")
    else:
        ui_status(ui, "Requirements already installed.")
        ui_log(ui, "All DeTrace Python requirements are already installed. Skipping pip installation.")

    ensure_cuda_torch(ui, runtime_python)
    refresh_requirement_status(ui, runtime_python)
    ui_busy(ui, False)
    ui_progress(ui, 85)
    ensure_mvsep_support(ui, runtime_python)
    ensure_mvsep_true_accordion(ui)
    write_setup_marker()
    return runtime_python


def download_file(url: str, target: Path, ui: dict, label: str, item_key: str = "mvsep") -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    ui_log(ui, f"Downloading {label.lower()} from {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "DeTrace/1.0"})
    temp = target.with_suffix(target.suffix + ".download")
    with urllib.request.urlopen(request, timeout=60) as response, temp.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or "0")
        received = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            received += len(chunk)
            if total:
                percent = int((received / total) * 100)
                ui_item(ui, item_key, f"{label} {percent}%")
                ui_log(ui, f"{label}: {percent}% ({received // (1024 * 1024)} MB of {total // (1024 * 1024)} MB)")
            else:
                ui_log(ui, f"{label}: {received // (1024 * 1024)} MB downloaded")
    temp.replace(target)
    ui_log(ui, f"Saved {target}")


def install_mvsep_repo(ui: dict) -> None:
    if (MVSEP_REPO_DIR / "inference.py").exists():
        patch_mvsep_source_for_inference(ui)
        ui_log(ui, f"MVSep source already exists at {MVSEP_REPO_DIR}")
        return
    archive = APP_DIR / "tools" / "mvsep-source.zip"
    ui_item(ui, "mvsep", "Downloading source")
    download_file(MVSEP_REPO_ZIP_URL, archive, ui, "Source")

    extract_root = APP_DIR / "tools" / "mvsep-extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zip_file:
        ui_log(ui, "Extracting MVSep source archive.")
        zip_file.extractall(extract_root)

    candidates = [path for path in extract_root.iterdir() if path.is_dir()]
    if not candidates:
        raise RuntimeError("MVSep source archive did not contain a source folder.")
    MVSEP_REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
    if MVSEP_REPO_DIR.exists():
        shutil.copytree(candidates[0], MVSEP_REPO_DIR, dirs_exist_ok=True)
        ui_log(ui, f"Updated missing MVSep source files at {MVSEP_REPO_DIR}")
    else:
        shutil.move(str(candidates[0]), str(MVSEP_REPO_DIR))
        ui_log(ui, f"Installed MVSep source at {MVSEP_REPO_DIR}")
    patch_mvsep_source_for_inference(ui)
    shutil.rmtree(extract_root, ignore_errors=True)
    archive.unlink(missing_ok=True)


def patch_mvsep_source_for_inference(ui: dict) -> None:
    settings_file = MVSEP_REPO_DIR / "utils" / "settings.py"
    if not settings_file.exists():
        return
    text = settings_file.read_text(encoding="utf-8")
    if "_DeTraceWandbStub" in text:
        return
    old = "import wandb"
    new = (
        "try:\n"
        "    import wandb\n"
        "except Exception:\n"
        "    class _DeTraceWandbStub:\n"
        "        def __getattr__(self, _name):\n"
        "            def _noop(*_args, **_kwargs):\n"
        "                return None\n"
        "            return _noop\n"
        "    wandb = _DeTraceWandbStub()"
    )
    if old in text:
        settings_file.write_text(text.replace(old, new, 1), encoding="utf-8")
        ui_log(ui, "Patched MVSep source for inference-only WandB handling.")


def install_true_mvsep_model(ui: dict) -> None:
    config_url, checkpoint_url = true_mvsep_download_urls()
    if (config_url and not checkpoint_url) or (checkpoint_url and not config_url):
        raise RuntimeError(
            "True accordion model download is only partly configured. "
            "Set both DETRACE_MVSEP_TRUE_CONFIG_URL and DETRACE_MVSEP_TRUE_CKPT_URL, "
            f"or put both URLs in {TRUE_MVSEP_MODEL_DIR / TRUE_MVSEP_URLS_FILE}."
        )

    if not true_mvsep_config_ready():
        TRUE_MVSEP_CONFIG_FILE.unlink(missing_ok=True)
        if config_url:
            ui_item(ui, "true_mvsep", "Downloading config")
            download_file(config_url, TRUE_MVSEP_CONFIG_FILE, ui, "True model config", "true_mvsep")
        else:
            ui_log(ui, f"MVSep Mega 53-stem config not installed at {TRUE_MVSEP_CONFIG_FILE}")

    if not valid_file(TRUE_MVSEP_CHECKPOINT_FILE, MIN_MVSEP_CHECKPOINT_BYTES):
        TRUE_MVSEP_CHECKPOINT_FILE.unlink(missing_ok=True)
        if checkpoint_url:
            ui_item(ui, "true_mvsep", "Downloading checkpoint")
            download_file(
                checkpoint_url,
                TRUE_MVSEP_CHECKPOINT_FILE,
                ui,
                "True model checkpoint",
                "true_mvsep",
            )
        else:
            ui_log(ui, f"MVSep Mega 53-stem checkpoint not installed at {TRUE_MVSEP_CHECKPOINT_FILE}")

    if config_url or checkpoint_url:
        if not true_mvsep_ready():
            raise RuntimeError(
                "MVSep Mega 53-stem model download finished, but the files are not valid. "
                "Use a multi-stem config/checkpoint that outputs accordion and piano with target_instrument unset or null."
            )


def ensure_mvsep_true_accordion(ui: dict) -> None:
    if true_mvsep_ready():
        ui_item(ui, "true_mvsep", "Present")
        ui_log(ui, "MVSep Mega 53-stem model is installed.")
        return

    install_true_mvsep_model(ui)
    if true_mvsep_ready():
        ui_item(ui, "true_mvsep", "Present")
        ui_log(ui, "Installed MVSep Mega 53-stem model.")
    else:
        ui_item(ui, "true_mvsep", "Missing model files")
        ui_log(
            ui,
            "MVSep Mega 53-stem model is required. "
            f"Place config.yaml and checkpoint.ckpt in {TRUE_MVSEP_MODEL_DIR}, or set "
            "DETRACE_MVSEP_TRUE_CONFIG_URL and DETRACE_MVSEP_TRUE_CKPT_URL before setup."
        )


def ensure_mvsep_support(ui: dict, runtime_python: Path) -> None:
    if (MVSEP_REPO_DIR / "inference.py").exists():
        patch_mvsep_source_for_inference(ui)
    if (
        (MVSEP_REPO_DIR / "inference.py").exists()
        and mvsep_dependencies_ready(runtime_python)
    ):
        apply_app_environment()
        ui_item(ui, "mvsep", "Present")
        ui_log(ui, "MVSep source and inference dependencies are already installed.")
        return

    ui_status(ui, "Installing MVSep support...")
    ui_item(ui, "mvsep", "Installing")
    ui_busy(ui, True)
    install_mvsep_repo(ui)

    missing_modules = missing_mvsep_modules(runtime_python)
    if missing_modules:
        ui_item(ui, "mvsep", "Installing dependencies")
        ui_log(ui, f"Missing MVSep inference modules: {', '.join(missing_modules)}")
        command = [str(runtime_python), "-m", "pip", "install"]
        if WHEELHOUSE_DIR.exists() and any(WHEELHOUSE_DIR.iterdir()):
            command.extend(["--no-index", "--find-links", str(WHEELHOUSE_DIR)])
        command.extend(MVSEP_REQUIRED_PACKAGES)
        result = run_logged(command, ui)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "MVSep dependency installation failed.")
    else:
        ui_log(ui, "MVSep inference dependencies are already installed.")

    apply_app_environment()
    ui_item(ui, "mvsep", "Present")
    ui_log(ui, "MVSep support setup complete.")
    ui_progress(ui, 92)


def app_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    threads = str(cpu_worker_count())
    env.update(
        {
            "DETRACE_MVSEP_REPO": str(MVSEP_REPO_DIR),
            "OMP_NUM_THREADS": threads,
            "MKL_NUM_THREADS": threads,
            "NUMEXPR_NUM_THREADS": threads,
            "NUMBA_NUM_THREADS": threads,
            "TORCH_NUM_THREADS": threads,
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        }
    )
    if nvidia_gpu_available():
        env.setdefault("DETRACE_DEVICE", "cuda")
    if extra:
        env.update(extra)
    return env


def apply_app_environment() -> None:
    os.environ.update(app_environment())


def files_match(source: Path, target: Path) -> bool:
    if not target.exists() or not target.is_file():
        return False
    source_stat = source.stat()
    target_stat = target.stat()
    return source_stat.st_size == target_stat.st_size and int(source_stat.st_mtime) <= int(target_stat.st_mtime)


def copy_file(name: str, ui: dict | None = None) -> bool:
    source = BUNDLE_DIR / name
    target = APP_DIR / name
    if not source.exists():
        return False
    if files_match(source, target):
        if ui:
            ui_log(ui, f"{name} already current")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if ui:
        ui_log(ui, f"Updated {name}")
    return True


def copy_dir(name: str, ui: dict | None = None) -> int:
    source = BUNDLE_DIR / name
    target = APP_DIR / name
    if not source.exists():
        return 0
    copied = 0
    for source_file in source.rglob("*"):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(source)
        target_file = target / relative
        if files_match(source_file, target_file):
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied += 1
    if ui:
        ui_log(ui, f"{name} already current" if copied == 0 else f"Updated {copied} {name} file(s)")
    return copied


def ensure_app_files(ui: dict | None = None) -> None:
    if ui:
        ui_status(ui, "Preparing application files...")
        ui_log(ui, f"Preparing application files in {APP_DIR}")
        ui_progress(ui, 25)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    changed = 0
    for name in ("requirements.txt", "server.py", "desktop_window.py"):
        changed += 1 if copy_file(name, ui) else 0
    changed += copy_dir("assets", ui)
    changed += copy_dir("static", ui)
    changed += copy_dir("wheelhouse", ui)
    changed += copy_dir("models", ui)
    if ui:
        if changed:
            ui_log(ui, "Application files are ready.")
        else:
            ui_log(ui, "Application files are already current. Skipping file copy.")


def start_desktop(runtime_python: Path) -> None:
    env = app_environment()
    subprocess.Popen(
        [str(runtime_python), str(APP_DIR / "desktop_window.py")],
        cwd=str(APP_DIR),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def find_free_port(start: int = 5180) -> int:
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1


def start_web(runtime_python: Path) -> str:
    port = find_free_port()
    env = app_environment({"PORT": str(port)})
    subprocess.Popen(
        [str(runtime_python), str(APP_DIR / "server.py")],
        cwd=str(APP_DIR),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    return url


def fast_start_desktop_if_ready() -> bool:
    if not setup_marker_ready():
        return False
    try:
        ensure_app_files()
        start_desktop(venv_python())
        return True
    except Exception:
        return False


def ui_status(ui: dict, text: str) -> None:
    ui["root"].after(0, ui["status"].set, text)


def ui_item(ui: dict, key: str, value: str) -> None:
    ui["root"].after(0, ui["items"][key].set, value)


def ui_log(ui: dict, text: str) -> None:
    def apply() -> None:
        log_box = ui.get("log_box")
        if log_box is None:
            return
        log_box.configure(state="normal")
        log_box.insert("end", f"{text}\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    ui["root"].after(0, apply)


def ui_progress(ui: dict, value: int) -> None:
    def apply() -> None:
        track_width = max(ui["progress_track"].winfo_width(), 1)
        bar_width = max(int(track_width * (value / 100)), 1)
        ui["progress_bar"].configure(width=bar_width, bg="#0b6f7c")

    ui["root"].after(0, apply)


def ui_busy(ui: dict, busy: bool) -> None:
    def apply() -> None:
        ui["busy"] = busy
        if busy:
            animate_busy(ui)
        else:
            ui["progress_bar"].place_configure(x=0)
            ui["progress_bar"].configure(bg="#0b6f7c")

    ui["root"].after(0, apply)


def animate_busy(ui: dict) -> None:
    if not ui.get("busy"):
        return
    track_width = max(ui["progress_track"].winfo_width(), 1)
    bar_width = max(int(track_width * 0.28), 60)
    ui["busy_step"] = (ui.get("busy_step", 0) + 18) % (track_width + bar_width)
    x = ui["busy_step"] - bar_width
    ui["progress_bar"].configure(width=bar_width, bg="#f0a33a")
    ui["progress_bar"].place_configure(x=x)
    ui["root"].after(45, lambda: animate_busy(ui))


def main() -> None:
    if fast_start_desktop_if_ready():
        return

    root = tk.Tk()
    root.title("DeTrace")
    set_window_icon(root)
    root.resizable(True, True)
    root.configure(bg="#0c181c")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width = min(1180, max(760, screen_width - 80))
    height = min(920, max(620, screen_height - 80))
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(720, 560)
    if os.name == "nt":
        root.state("zoomed")

    status = tk.StringVar(value="Preparing DeTrace setup...")
    items = {
        "python": tk.StringVar(value="Queued"),
        "runtime": tk.StringVar(value="Queued"),
        "ffmpeg": tk.StringVar(value="Queued"),
        "codecs": tk.StringVar(value="Queued"),
        "chords": tk.StringVar(value="Queued"),
        "mvsep": tk.StringVar(value="Queued"),
        "true_mvsep": tk.StringVar(value="Queued"),
        "gpu": tk.StringVar(value="Queued"),
        "desktop": tk.StringVar(value="Queued"),
    }

    splash = tk.Frame(root, bg="#10242a")
    splash.columnconfigure(0, weight=1)
    splash.rowconfigure(0, weight=1)
    splash_content = tk.Frame(splash, bg="#10242a")
    splash_content.grid(row=0, column=0, sticky="nsew")
    splash_content.columnconfigure(0, weight=1)
    splash_content.rowconfigure(0, weight=1)

    launcher_art = None
    image_refs: list[tk.PhotoImage] = []
    logo_canvas = tk.Canvas(splash_content, bg="#10242a", borderwidth=0, highlightthickness=0)
    logo_canvas.grid(row=0, column=0, rowspan=3, sticky="nsew")
    try:
        launcher_art = load_launcher_art(screen_width, screen_height)
    except tk.TclError:
        launcher_art = None
    if launcher_art:
        image_refs.append(launcher_art)
        logo_image = logo_canvas.create_image(0, 0, image=launcher_art, anchor="center")

        def fit_logo_to_canvas(event: tk.Event) -> None:
            logo_canvas.coords(logo_image, event.width // 2, event.height // 2)

        logo_canvas.bind("<Configure>", fit_logo_to_canvas)
    else:
        logo_canvas.create_text(
            width // 2,
            height // 2,
            text="DeTrace",
            fill="#f8fbf9",
            font=("Segoe UI", 42, "bold"),
        )

    tk.Label(
        splash_content,
        text="Choose how you want to continue.",
        bg="#10242a",
        fg="#c8d7d7",
        font=("Segoe UI", 13, "bold"),
    ).grid(row=1, column=0, sticky="n", pady=(4, 18))

    splash_actions = tk.Frame(splash_content, bg="#10242a")
    splash_actions.grid(row=2, column=0, sticky="n", pady=(0, 30))
    splash_desktop_btn = tk.Button(
        splash_actions,
        text="Continue as Desktop",
        bg="#0b6f7c",
        fg="#ffffff",
        activebackground="#074e58",
        activeforeground="#ffffff",
        relief="flat",
        padx=22,
        pady=14,
        font=("Segoe UI", 11, "bold"),
    )
    splash_web_btn = tk.Button(
        splash_actions,
        text="Continue as Web",
        bg="#c95f4f",
        fg="#ffffff",
        activebackground="#9e4438",
        activeforeground="#ffffff",
        relief="flat",
        padx=22,
        pady=14,
        font=("Segoe UI", 11, "bold"),
    )
    splash_cancel_btn = tk.Button(
        splash_actions,
        text="Cancel",
        bg="#33454c",
        fg="#ffffff",
        activebackground="#223139",
        activeforeground="#ffffff",
        relief="flat",
        padx=22,
        pady=14,
        font=("Segoe UI", 11, "bold"),
        command=root.destroy,
    )
    splash_desktop_btn.pack(side="left", padx=(0, 10))
    splash_web_btn.pack(side="left", padx=(0, 10))
    splash_cancel_btn.pack(side="left")

    setup = tk.Frame(root, bg="#eef3f2")
    setup.rowconfigure(1, weight=1)
    setup.columnconfigure(0, weight=1)

    header = tk.Frame(setup, bg="#10242a")
    header.grid(row=0, column=0, sticky="ew")
    tk.Label(header, text="DeTrace", bg="#10242a", fg="#f8fbf9", font=("Segoe UI", 22, "bold")).pack(
        anchor="w", padx=34, pady=(24, 2)
    )
    tk.Label(header, text="Setup timeline", bg="#10242a", fg="#f0a33a", font=("Segoe UI", 11, "bold")).pack(
        anchor="w", padx=36, pady=(0, 4)
    )
    tk.Label(header, textvariable=status, bg="#10242a", fg="#c8d7d7", font=("Segoe UI", 10)).pack(
        anchor="w", padx=36, pady=(0, 24)
    )

    body = tk.Frame(setup, bg="#eef3f2")
    body.grid(row=1, column=0, sticky="nsew")
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    body_canvas = tk.Canvas(body, bg="#eef3f2", borderwidth=0, highlightthickness=0)
    body_scroll = tk.Scrollbar(body, orient="vertical", command=body_canvas.yview)
    body_canvas.configure(yscrollcommand=body_scroll.set)
    body_canvas.grid(row=0, column=0, sticky="nsew")
    body_scroll.grid(row=0, column=1, sticky="ns")

    content = tk.Frame(body_canvas, bg="#eef3f2")
    content_window = body_canvas.create_window((0, 0), window=content, anchor="nw")

    def resize_content(event: tk.Event) -> None:
        body_canvas.itemconfigure(content_window, width=event.width)

    def update_scroll_region(_event: tk.Event | None = None) -> None:
        body_canvas.configure(scrollregion=body_canvas.bbox("all"))

    body_canvas.bind("<Configure>", resize_content)
    content.bind("<Configure>", update_scroll_region)

    def mousewheel(event: tk.Event) -> None:
        body_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    body_canvas.bind_all("<MouseWheel>", mousewheel)

    progress_wrap = tk.Frame(content, bg="#eef3f2")
    progress_wrap.pack(fill="x", padx=24, pady=(18, 10))
    progress_track = tk.Frame(progress_wrap, bg="#d6dde3", height=12)
    progress_track.pack(fill="x")
    progress_bar = tk.Frame(progress_track, bg="#0b6f7c", width=1, height=12)
    progress_bar.place(x=0, y=0, relheight=1)

    checklist = tk.Frame(content, bg="#eef3f2")
    checklist.pack(fill="x", padx=24)
    labels = [
        ("1. Python", "python"),
        ("2. DeTrace runtime", "runtime"),
        ("3. FFmpeg codec/export support", "ffmpeg"),
        ("4. MP3/audio codecs", "codecs"),
        ("5. Chord detection engine", "chords"),
        ("6. MVSep support files", "mvsep"),
        ("7. MVSep Mega 53-stem model", "true_mvsep"),
        ("8. NVIDIA GPU acceleration", "gpu"),
        ("9. Desktop window support", "desktop"),
    ]
    for row, (label, key) in enumerate(labels):
        row_frame = tk.Frame(checklist, bg="#ffffff", highlightthickness=1, highlightbackground="#d6dde3")
        row_frame.grid(row=row, column=0, sticky="ew", pady=4)
        tk.Label(row_frame, text=label, anchor="w", bg="#ffffff", fg="#172026", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=14, pady=10
        )
        tk.Label(row_frame, textvariable=items[key], anchor="e", bg="#ffffff", fg="#0b6f7c", font=("Segoe UI", 10, "bold")).pack(
            side="right", padx=14, pady=10
        )
    checklist.columnconfigure(0, weight=1)

    log_wrap = tk.Frame(content, bg="#eef3f2")
    log_wrap.pack(fill="both", expand=True, padx=24, pady=(16, 18))
    tk.Label(log_wrap, text="Setup log", anchor="w", bg="#eef3f2", fg="#172026", font=("Segoe UI", 11, "bold")).pack(
        fill="x", pady=(0, 6)
    )
    log_frame = tk.Frame(log_wrap, bg="#11191d", highlightthickness=1, highlightbackground="#223139")
    log_frame.pack(fill="both", expand=True)
    log_scroll = tk.Scrollbar(log_frame)
    log_scroll.pack(side="right", fill="y")
    log_box = tk.Text(
        log_frame,
        bg="#11191d",
        fg="#d9f0ec",
        insertbackground="#d9f0ec",
        relief="flat",
        wrap="word",
        height=8,
        font=("Consolas", 10),
        yscrollcommand=log_scroll.set,
        state="disabled",
    )
    log_box.pack(side="left", fill="both", expand=True, padx=12, pady=10)
    log_scroll.configure(command=log_box.yview)

    actions = tk.Frame(content, bg="#eef3f2")
    desktop_btn = tk.Button(
        actions,
        text="Desktop App",
        bg="#0b6f7c",
        fg="#ffffff",
        activebackground="#074e58",
        activeforeground="#ffffff",
        relief="flat",
        padx=18,
        pady=12,
        font=("Segoe UI", 10, "bold"),
    )
    web_btn = tk.Button(
        actions,
        text="Web Browser",
        bg="#c95f4f",
        fg="#ffffff",
        activebackground="#9e4438",
        activeforeground="#ffffff",
        relief="flat",
        padx=18,
        pady=12,
        font=("Segoe UI", 10, "bold"),
    )

    ui = {
        "root": root,
        "status": status,
        "items": items,
        "progress_bar": progress_bar,
        "progress_track": progress_track,
        "busy": False,
        "busy_step": 0,
        "desktop_btn": desktop_btn,
        "web_btn": web_btn,
        "log_box": log_box,
    }

    splash.pack(fill="both", expand=True)
    root.update_idletasks()
    root.lift()
    root.focus_force()

    def set_buttons(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        root.after(0, desktop_btn.configure, {"state": state})
        root.after(0, web_btn.configure, {"state": state})

    def show_launch_choices() -> None:
        actions.pack(fill="x", padx=24, pady=(0, 18))
        if not desktop_btn.winfo_ismapped():
            desktop_btn.pack(side="left", padx=(0, 10))
        if not web_btn.winfo_ismapped():
            web_btn.pack(side="left")
        set_buttons(True)

    def prepare_setup() -> None:
        try:
            set_buttons(False)
            ensure_app_files(ui)
            refresh_requirement_status(ui, venv_python())
            if setup_marker_ready() and not setup_repair_requested():
                ui_progress(ui, 100)
                ui_status(ui, "Setup is complete. Choose Desktop App or Web Browser to launch DeTrace.")
                ui_log(ui, "Setup is complete. Waiting for launch mode selection.")
            else:
                ui_status(ui, "Choose Desktop App or Web Browser to install and launch DeTrace.")
                ui_log(ui, "Choose a launch mode to continue setup.")
        except Exception as exc:
            ui_busy(ui, False)
            ui_status(ui, "Setup preparation failed. Choose a launch mode to retry after fixing the issue.")
            ui_log(ui, str(exc))
        finally:
            root.after(0, show_launch_choices)

    def work(mode: str) -> None:
        try:
            set_buttons(False)
            ensure_app_files(ui)
            prepare_for_forced_repair(ui)
            runtime_python = ensure_runtime(ui)
            ui_status(ui, "Starting DeTrace desktop app..." if mode == "desktop" else "Starting DeTrace web server...")
            ui_log(ui, f"MVSep repo: {MVSEP_REPO_DIR}")
            ui_log(ui, f"MVSep Mega 53 config: {TRUE_MVSEP_CONFIG_FILE}")
            ui_log(ui, f"MVSep Mega 53 checkpoint: {TRUE_MVSEP_CHECKPOINT_FILE}")
            ui_log(ui, "Setup complete. Launching DeTrace.")
            ui_progress(ui, 100)
            if mode == "desktop":
                start_desktop(runtime_python)
                root.after(700, root.destroy)
            else:
                url = start_web(runtime_python)
                ui_status(ui, f"Web version is running at {url}")
                root.after(1600, root.destroy)
        except Exception as exc:
            ui_busy(ui, False)
            set_buttons(True)

            def fail() -> None:
                ui_status(ui, "Setup failed. Choose a launch mode to retry after fixing the issue.")
                show_launch_choices()
                messagebox.showerror("DeTrace setup failed", str(exc))

            root.after(0, fail)

    def start_from_splash(mode: str) -> None:
        splash_desktop_btn.configure(state="disabled")
        splash_web_btn.configure(state="disabled")
        splash_cancel_btn.configure(state="disabled")
        splash.pack_forget()
        setup.pack(fill="both", expand=True)
        root.update_idletasks()
        threading.Thread(target=work, args=(mode,), daemon=True).start()

    splash_desktop_btn.configure(command=lambda: start_from_splash("desktop"))
    splash_web_btn.configure(command=lambda: start_from_splash("web"))
    desktop_btn.configure(command=lambda: threading.Thread(target=work, args=("desktop",), daemon=True).start())
    web_btn.configure(command=lambda: threading.Thread(target=work, args=("web",), daemon=True).start())
    root.mainloop()


def load_launcher_art(max_width: int | None = None, max_height: int | None = None) -> tk.PhotoImage:
    image_path = BUNDLE_DIR / "static" / "detracelogo.png"
    if not image_path.exists():
        image_path = INSTALL_DIR / "static" / "detracelogo.png"
    image = tk.PhotoImage(file=str(image_path))
    if max_width and max_height:
        scale = max(
            1,
            ceil(max(
                image.width() / max_width,
                image.height() / max_height,
            )),
        )
        if scale > 1:
            image = image.subsample(scale, scale)
    return image


def set_window_icon(root: tk.Tk) -> None:
    ico_candidates = (
        BUNDLE_DIR / "assets" / "detrace-icon.ico",
        INSTALL_DIR / "assets" / "detrace-icon.ico",
    )
    for icon_path in ico_candidates:
        if icon_path.exists():
            try:
                root.iconbitmap(str(icon_path))
                root.iconbitmap(default=str(icon_path))
                return
            except tk.TclError:
                break

    png_candidates = (
        BUNDLE_DIR / "assets" / "detrace-icon.png",
        INSTALL_DIR / "assets" / "detrace-icon.png",
    )
    for icon_path in png_candidates:
        if icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, icon)
                WINDOW_ICON_REFS.append(icon)
            except tk.TclError:
                pass
            return


if __name__ == "__main__":
    main()
