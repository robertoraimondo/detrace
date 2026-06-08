from __future__ import annotations

import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "tools"
MVSEP_REPO_DIR = TOOLS_DIR / "Music-Source-Separation-Training"
MVSEP_MODEL_DIR = ROOT / "models" / "mvsep_accordion"
MVSEP_CONFIG_FILE = MVSEP_MODEL_DIR / "config.yaml"
MVSEP_CHECKPOINT_FILE = MVSEP_MODEL_DIR / "bs_mega_53stem_accordion_mvsep.ckpt"

MIN_MVSEP_CONFIG_BYTES = 512
MIN_MVSEP_CHECKPOINT_BYTES = 50 * 1024 * 1024

MVSEP_REPO_ZIP_URL = os.environ.get(
    "DETRACE_MVSEP_REPO_ZIP_URL",
    "https://github.com/ZFTurbo/Music-Source-Separation-Training/archive/refs/heads/main.zip",
)
MVSEP_CONFIG_URL = os.environ.get(
    "DETRACE_MVSEP_ACCORDION_CONFIG_URL",
    "https://huggingface.co/noblebarkrr/BS-Roformer-MVSep-Mega-53-stems/resolve/main/v1/"
    "bs_mega_53stem_accordion_mvsep_config.yaml",
)
MVSEP_CHECKPOINT_URL = os.environ.get(
    "DETRACE_MVSEP_ACCORDION_CKPT_URL",
    "https://huggingface.co/noblebarkrr/BS-Roformer-MVSep-Mega-53-stems/resolve/main/v1/"
    "bs_mega_53stem_accordion_mvsep.ckpt",
)


def valid_file(path: Path, min_bytes: int) -> bool:
    return path.is_file() and path.stat().st_size >= min_bytes


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".download")
    temp.unlink(missing_ok=True)
    print(f"Downloading {url} -> {target}", flush=True)
    with urllib.request.urlopen(url) as response, temp.open("wb") as output:
        shutil.copyfileobj(response, output)
    temp.replace(target)


def patch_mvsep_source_for_inference() -> None:
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
        print("Patched MVSep WandB import for inference-only deployment.", flush=True)


def install_mvsep_repo() -> None:
    if (MVSEP_REPO_DIR / "inference.py").exists():
        patch_mvsep_source_for_inference()
        print(f"MVSep source already exists at {MVSEP_REPO_DIR}", flush=True)
        return

    archive = TOOLS_DIR / "mvsep-source.zip"
    extract_root = TOOLS_DIR / "mvsep-extract"
    download_file(MVSEP_REPO_ZIP_URL, archive)

    shutil.rmtree(extract_root, ignore_errors=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zip_file:
        zip_file.extractall(extract_root)

    candidates = [path for path in extract_root.iterdir() if path.is_dir()]
    if not candidates:
        raise RuntimeError("MVSep source archive did not contain a source folder.")

    MVSEP_REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(candidates[0]), str(MVSEP_REPO_DIR))
    patch_mvsep_source_for_inference()
    shutil.rmtree(extract_root, ignore_errors=True)
    archive.unlink(missing_ok=True)
    print(f"Installed MVSep source at {MVSEP_REPO_DIR}", flush=True)


def install_mvsep_model() -> None:
    if not valid_file(MVSEP_CONFIG_FILE, MIN_MVSEP_CONFIG_BYTES):
        MVSEP_CONFIG_FILE.unlink(missing_ok=True)
        download_file(MVSEP_CONFIG_URL, MVSEP_CONFIG_FILE)
    else:
        print(f"MVSep config already exists at {MVSEP_CONFIG_FILE}", flush=True)

    if not valid_file(MVSEP_CHECKPOINT_FILE, MIN_MVSEP_CHECKPOINT_BYTES):
        MVSEP_CHECKPOINT_FILE.unlink(missing_ok=True)
        download_file(MVSEP_CHECKPOINT_URL, MVSEP_CHECKPOINT_FILE)
    else:
        print(f"MVSep checkpoint already exists at {MVSEP_CHECKPOINT_FILE}", flush=True)


def main() -> int:
    if os.environ.get("DETRACE_SKIP_MVSEP_SETUP", "").strip().lower() in {"1", "true", "yes"}:
        print("Skipping MVSep setup because DETRACE_SKIP_MVSEP_SETUP is set.", flush=True)
        return 0

    install_mvsep_repo()
    install_mvsep_model()

    if not (MVSEP_REPO_DIR / "inference.py").is_file():
        raise RuntimeError(f"Missing MVSep inference.py at {MVSEP_REPO_DIR}")
    if not valid_file(MVSEP_CONFIG_FILE, MIN_MVSEP_CONFIG_BYTES):
        raise RuntimeError(f"Missing MVSep config at {MVSEP_CONFIG_FILE}")
    if not valid_file(MVSEP_CHECKPOINT_FILE, MIN_MVSEP_CHECKPOINT_BYTES):
        raise RuntimeError(f"Missing MVSep checkpoint at {MVSEP_CHECKPOINT_FILE}")

    print("MVSep Accordion is ready for Render.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
