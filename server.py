from __future__ import annotations
import importlib.util
import json
import math
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import uuid
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlparse

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
WORKSPACE = ROOT / "workspace"
UPLOADS = WORKSPACE / "uploads"
STEMS = WORKSPACE / "stems"
EXPORTS = WORKSPACE / "exports"
LOCAL_MODELS = ROOT / "models"

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "5180"))
MAX_UPLOAD = 250 * 1024 * 1024
COMBINED_ACCORDION_MODEL = "htdemucs_6s_accordion"
TRUE_ACCORDION_MODEL = "mvsep_true_accordion"
ALLOWED_MODELS = {"htdemucs", "htdemucs_6s", "mvsep_accordion", TRUE_ACCORDION_MODEL, COMBINED_ACCORDION_MODEL}
DEMUCS_MODELS = {"htdemucs", "htdemucs_6s"}
MODEL_STEMS = {
    "htdemucs": {"vocals", "drums", "bass", "other"},
    "htdemucs_6s": {"vocals", "drums", "bass", "guitar", "piano", "other"},
}
MVSEP_ACCORDION_MODEL = "mvsep_accordion"
TRUE_ACCORDION_SOURCE_STEMS = {"accordion", "piano"}
TRUE_ACCORDION_STEMS = {*TRUE_ACCORDION_SOURCE_STEMS, "other"}
def configured_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


TRUE_MODEL_STEM_RMS_THRESHOLD_DB = configured_float("DETRACE_TRUE_STEM_RMS_THRESHOLD_DB", -55.0)
DISPLAY_STEM_RMS_THRESHOLD_DB = configured_float("DETRACE_DISPLAY_STEM_RMS_THRESHOLD_DB", -46.0)
PASSING_CHORD_MAX_SECONDS = 1.6
CHORD_HOP_LENGTH = 2048
MIN_CHORD_SECONDS = 0.18
ACCORDION_BLEED_TARGETS = {"piano", "other"}
ACCORDION_REDUCTION_MARKER = "_accordion_reduced_v1.txt"
NO_ACCORDION_STEM_NAME = "no-accordion-mix.mp3"
ACTIVE_SERVER: ThreadingHTTPServer | None = None
ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
ACTIVE_PROCESSES_LOCK = threading.Lock()
CPU_SAMPLE: tuple[int, int, int] | None = None


def ensure_dirs() -> None:
    for path in (UPLOADS, STEMS, EXPORTS):
        path.mkdir(parents=True, exist_ok=True)


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in name).strip()
    return cleaned or "audio.mp3"


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def ffmpeg_executable() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def codec_status() -> bool:
    return module_available("imageio_ffmpeg") and module_available("lameenc")


def demucs_command() -> list[str] | None:
    if module_available("demucs"):
        return [sys.executable, "-m", "demucs.separate"]
    demucs_exe = shutil.which("demucs")
    if demucs_exe:
        return [demucs_exe]
    return None


def configured_path(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name, "").strip()
    return Path(value).expanduser() if value else fallback


def installed_app_dir() -> Path | None:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "DeTrace" / ".detrace-app"
    return Path.home() / ".detrace" / ".detrace-app"


def mvsep_default_path(relative_path: Path) -> Path:
    workspace_path = ROOT / relative_path
    app_dir = installed_app_dir()
    if workspace_path.exists() or app_dir is None:
        return workspace_path
    installed_path = app_dir / relative_path
    return installed_path if installed_path.exists() else workspace_path


def mvsep_settings() -> dict[str, Path]:
    model_dir = Path("models") / "mvsep_accordion"
    return {
        "repo": configured_path(
            "DETRACE_MVSEP_REPO",
            mvsep_default_path(Path("tools") / "Music-Source-Separation-Training"),
        ),
        "config": configured_path("DETRACE_MVSEP_ACCORDION_CONFIG", mvsep_default_path(model_dir / "config.yaml")),
        "checkpoint": configured_path(
            "DETRACE_MVSEP_ACCORDION_CKPT",
            mvsep_default_path(model_dir / "bs_mega_53stem_accordion_mvsep.ckpt"),
        ),
    }


def mvsep_true_settings() -> dict[str, Path]:
    model_dir = Path("models") / "mvsep_true_accordion"
    default_dir = mvsep_default_path(model_dir)
    return {
        "repo": configured_path(
            "DETRACE_MVSEP_REPO",
            mvsep_default_path(Path("tools") / "Music-Source-Separation-Training"),
        ),
        "config": configured_path("DETRACE_MVSEP_TRUE_CONFIG", default_dir / "config.yaml"),
        "checkpoint": configured_path("DETRACE_MVSEP_TRUE_CKPT", default_dir / "checkpoint.ckpt"),
    }


def mvsep_python() -> str:
    return os.environ.get("DETRACE_MVSEP_PYTHON", sys.executable)


def config_declares_true_accordion(config_path: Path) -> bool:
    if not config_path.is_file():
        return False
    try:
        text = config_path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    target_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("target_instrument:")]
    target_is_multi_stem = not target_lines or any(line in {"target_instrument: null", "target_instrument: none"} for line in target_lines)
    return all(stem in text for stem in TRUE_ACCORDION_SOURCE_STEMS) and target_is_multi_stem


def mvsep_accordion_status() -> bool:
    settings = mvsep_settings()
    return (
        settings["repo"].is_dir()
        and (settings["repo"] / "inference.py").is_file()
        and settings["config"].is_file()
        and settings["checkpoint"].is_file()
    )


def mvsep_true_status() -> bool:
    settings = mvsep_true_settings()
    return (
        settings["repo"].is_dir()
        and (settings["repo"] / "inference.py").is_file()
        and config_declares_true_accordion(settings["config"])
        and settings["checkpoint"].is_file()
    )


def cpu_worker_count() -> int:
    detected = os.cpu_count() or 1
    configured = os.environ.get("DETRACE_CPU_THREADS", "").strip()
    if configured:
        try:
            return max(1, min(detected, int(configured)))
        except ValueError:
            return detected
    return detected


def torch_cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def processing_device() -> str:
    configured = os.environ.get("DETRACE_DEVICE", "").strip().lower()
    if configured:
        if configured == "cuda" and not torch_cuda_available():
            return "cpu"
        return configured
    return "cuda" if torch_cuda_available() else "cpu"


def performance_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    threads = str(cpu_worker_count())
    env.setdefault("OMP_NUM_THREADS", threads)
    env.setdefault("MKL_NUM_THREADS", threads)
    env.setdefault("NUMEXPR_NUM_THREADS", threads)
    env.setdefault("NUMBA_NUM_THREADS", threads)
    env.setdefault("TORCH_NUM_THREADS", threads)
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    if extra:
        env.update(extra)
    return env


def format_gib(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value / (1024 ** 3):.1f} GB"


def windows_filetime_value(filetime) -> int:
    return (int(filetime.dwHighDateTime) << 32) + int(filetime.dwLowDateTime)


def cpu_percent() -> int | None:
    global CPU_SAMPLE
    if os.name != "nt":
        try:
            load = os.getloadavg()[0]
            return max(0, min(100, round((load / max(os.cpu_count() or 1, 1)) * 100)))
        except (AttributeError, OSError):
            return None

    try:
        import ctypes
        from ctypes import wintypes

        idle = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        sample = (
            windows_filetime_value(idle),
            windows_filetime_value(kernel),
            windows_filetime_value(user),
        )
        if CPU_SAMPLE is None:
            CPU_SAMPLE = sample
            return 0
        prev_idle, prev_kernel, prev_user = CPU_SAMPLE
        CPU_SAMPLE = sample
        idle_delta = sample[0] - prev_idle
        total_delta = (sample[1] - prev_kernel) + (sample[2] - prev_user)
        if total_delta <= 0:
            return 0
        return max(0, min(100, round((1 - idle_delta / total_delta) * 100)))
    except Exception:
        return None


def memory_status() -> dict[str, int | str | None]:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                used = int(status.ullTotalPhys - status.ullAvailPhys)
                total = int(status.ullTotalPhys)
                return {
                    "usedBytes": used,
                    "totalBytes": total,
                    "label": f"RAM {format_gib(used)} / {format_gib(total)}",
                }
        except Exception:
            pass
    return {"usedBytes": None, "totalBytes": None, "label": "RAM n/a"}


def gpu_status() -> dict[str, int | str | bool | None]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            name, used, total, utilization = [part.strip() for part in result.stdout.splitlines()[0].split(",", 3)]
            return {
                "available": True,
                "device": name,
                "usedMb": int(used),
                "totalMb": int(total),
                "utilization": int(utilization),
                "label": f"GPU {utilization}% {int(used)} / {int(total)} MB",
            }
    except Exception:
        pass

    return {
        "available": torch_cuda_available(),
        "device": processing_device(),
        "usedMb": None,
        "totalMb": None,
        "utilization": None,
        "label": "GPU CUDA ready" if torch_cuda_available() else "GPU inactive",
    }


def performance_status() -> dict:
    cpu = cpu_percent()
    total_threads = os.cpu_count() or 1
    return {
        "cpu": {
            "percent": cpu,
            "threads": cpu_worker_count(),
            "totalThreads": total_threads,
            "label": f"CPU {cpu if cpu is not None else 0}% | {cpu_worker_count()}/{total_threads} threads",
        },
        "ram": memory_status(),
        "gpu": gpu_status(),
    }


def tool_status() -> dict:
    return {
        "demucs": demucs_command() is not None,
        "mvsepAccordion": mvsep_accordion_status(),
        "mvsepTrueAccordion": mvsep_true_status(),
        "ffmpeg": ffmpeg_executable() is not None,
        "codecs": codec_status(),
        "chords": module_available("librosa"),
        "cuda": torch_cuda_available(),
        "device": processing_device(),
        "cpuThreads": cpu_worker_count(),
        "performance": performance_status(),
    }


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            text=True,
            capture_output=True,
            check=False,
        )
        return
    process.terminate()
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()


def terminate_active_processes() -> None:
    with ACTIVE_PROCESSES_LOCK:
        processes = list(ACTIVE_PROCESSES)
    for process in processes:
        terminate_process(process)


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        args,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=performance_environment(),
    )
    with ACTIVE_PROCESSES_LOCK:
        ACTIVE_PROCESSES.add(process)
    try:
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    finally:
        with ACTIVE_PROCESSES_LOCK:
            ACTIVE_PROCESSES.discard(process)


def stop_server() -> None:
    terminate_active_processes()
    if ACTIVE_SERVER is not None:
        ACTIVE_SERVER.shutdown()


def shutdown(handler: BaseHTTPRequestHandler) -> None:
    json_response(handler, 200, {"ok": True})
    threading.Thread(target=stop_server, daemon=True).start()


def install_tools(handler: BaseHTTPRequestHandler) -> None:
    before = tool_status()
    packages = []
    if not before["demucs"]:
        packages.append("demucs")
    if not before["ffmpeg"]:
        packages.append("imageio-ffmpeg")
    if not before["codecs"]:
        packages.extend(["lameenc", "soundfile"])
    if not before["chords"]:
        packages.append("librosa")

    if not packages:
        json_response(handler, 200, {"tools": before, "installed": [], "message": "All tools are already available."})
        return

    result = run_command([sys.executable, "-m", "pip", "install", *packages])
    after = tool_status()
    if result.returncode != 0:
        json_response(
            handler,
            500,
            {
                "error": "Tool installation failed.",
                "details": (result.stderr or result.stdout)[-4000:],
                "tools": after,
                "installed": [],
            },
        )
        return

    missing = [name for name, ready in after.items() if not ready]
    if missing:
        json_response(
            handler,
            500,
            {
                "error": f"Installed packages, but these tools are still unavailable: {', '.join(missing)}.",
                "details": (result.stderr or result.stdout)[-4000:],
                "tools": after,
                "installed": packages,
            },
        )
        return

    json_response(handler, 200, {"tools": after, "installed": packages})


def job_dir(job_id: str) -> Path:
    if not job_id.replace("-", "").isalnum():
        raise ValueError("Invalid job id")
    return STEMS / job_id


def chord_cache_path(job_id: str) -> Path:
    return job_dir(job_id) / "chords-v3.json"


def stem_audibility_cache_path(job_id: str) -> Path:
    return job_dir(job_id) / "_stem-audibility-v1.json"


def load_cached_chords(job_id: str) -> list[dict]:
    path = chord_cache_path(job_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return simplify_chords([item for item in data if isinstance(item, dict)])


def save_cached_chords(job_id: str, chords: list[dict]) -> None:
    path = chord_cache_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(simplify_chords(chords)), encoding="utf-8")


def load_stem_audibility_cache(job_id: str) -> dict:
    path = stem_audibility_cache_path(job_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_stem_audibility_cache(job_id: str, cache: dict) -> None:
    path = stem_audibility_cache_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache), encoding="utf-8")


def audio_rms_db(path: Path) -> float | None:
    ffmpeg = ffmpeg_executable()
    if ffmpeg is None:
        return None
    args = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "astats=metadata=1:reset=0",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    rms_values: list[float] = []
    for line in result.stderr.splitlines():
        if "RMS level dB:" not in line:
            continue
        value = line.rsplit(":", 1)[-1].strip()
        try:
            rms_values.append(float(value))
        except ValueError:
            pass
    return max(rms_values) if rms_values else None


def display_stem_has_audio(job_id: str, path: Path) -> tuple[bool, float | None]:
    try:
        stat = path.stat()
        key = path.relative_to(job_dir(job_id)).as_posix()
    except (OSError, ValueError):
        return True, None
    cache = load_stem_audibility_cache(job_id)
    cached = cache.get(key)
    signature = {"mtime": stat.st_mtime, "size": stat.st_size}
    if isinstance(cached, dict) and cached.get("mtime") == signature["mtime"] and cached.get("size") == signature["size"]:
        return bool(cached.get("audible", True)), cached.get("rmsDb")

    rms_db = audio_rms_db(path)
    audible = True if rms_db is None else rms_db >= DISPLAY_STEM_RMS_THRESHOLD_DB
    cache[key] = {**signature, "audible": audible, "rmsDb": rms_db}
    save_stem_audibility_cache(job_id, cache)
    return audible, rms_db


def collapse_repeated_chords(chords: list[dict]) -> list[dict]:
    merged = []
    for chord in chords:
        current = {
            **chord,
            "start": round(float(chord.get("start", 0)), 2),
            "end": round(float(chord.get("end", 0)), 2),
        }
        previous = merged[-1] if merged else None
        if previous and previous.get("chord") == current.get("chord"):
            previous["end"] = max(previous["end"], current["end"])
            continue
        merged.append(current)
    return merged


def simplify_chords(chords: list[dict]) -> list[dict]:
    merged = collapse_repeated_chords(chords)
    if len(merged) <= 2:
        return merged

    simplified = []
    index = 0
    while index < len(merged):
        chord = merged[index]
        duration = max(0.0, float(chord["end"]) - float(chord["start"]))
        previous = simplified[-1] if simplified else None
        next_chord = merged[index + 1] if index + 1 < len(merged) else None

        if duration < PASSING_CHORD_MAX_SECONDS:
            if previous and next_chord and previous.get("chord") == next_chord.get("chord"):
                previous["end"] = next_chord["end"]
                index += 2
                continue
            if next_chord:
                next_chord["start"] = chord["start"]
                index += 1
                continue
            if previous:
                previous["end"] = chord["end"]
                index += 1
                continue

        simplified.append(dict(chord))
        index += 1

    return collapse_repeated_chords(simplified)


def stem_display_name(path: Path) -> str:
    name = path.stem.strip()
    cleaned = name.replace("_", " ").replace("-", " ")
    words = " ".join(cleaned.split())
    if words.lower() in {"no accordion", "no accordion mix"}:
        return "No Accordion Mix"
    if "accordion" in words.lower():
        return "Accordion"
    return words.title() if words else name


def stem_sort_key(path: Path) -> tuple[int, str]:
    label = stem_display_name(path).lower()
    order = {"accordion": 0, "no accordion mix": 1}
    return (order.get(label, 2), label)


def find_stems(job_id: str) -> list[dict]:
    base = job_dir(job_id)
    files = sorted([*base.rglob("*.mp3"), *base.rglob("*.wav"), *base.rglob("*.flac")], key=stem_sort_key)
    files = [path for path in files if not any(part.startswith("_") for part in path.relative_to(base).parts)]
    stems = []
    for wav in files:
        if stem_display_name(wav).lower() == "no accordion mix":
            continue
        audible, rms_db = display_stem_has_audio(job_id, wav)
        if not audible:
            continue
        rel = wav.relative_to(WORKSPACE).as_posix()
        stem_id = wav.relative_to(job_dir(job_id)).as_posix()
        stems.append(
            {
                "id": stem_id,
                "name": stem_display_name(wav),
                "url": media_url(rel),
                "path": str(wav.relative_to(ROOT)),
                "rmsDb": rms_db,
            }
        )
    return stems


def cached_stem_names(job_id: str) -> set[str]:
    return {stem["name"].lower() for stem in find_stems(job_id)}


def clear_incomplete_model_cache(job_id: str, model: str) -> None:
    expected = MODEL_STEMS.get(model)
    if expected and expected.issubset(cached_stem_names(job_id)):
        return
    model_dir = job_dir(job_id) / model
    if model_dir.exists():
        shutil.rmtree(model_dir, ignore_errors=True)


def has_cached_model(job_id: str, model: str) -> bool:
    expected = MODEL_STEMS.get(model)
    if not expected:
        return False
    return expected.issubset(cached_stem_names(job_id))


def has_cached_accordion(job_id: str) -> bool:
    return "accordion" in cached_stem_names(job_id)


def true_model_dir(job_id: str) -> Path:
    return job_dir(job_id) / TRUE_ACCORDION_MODEL


def has_cached_true_accordion(job_id: str) -> bool:
    model_dir = true_model_dir(job_id)
    if not model_dir.exists():
        return False
    names = {stem_display_name(path).lower() for path in [*model_dir.rglob("*.mp3"), *model_dir.rglob("*.wav"), *model_dir.rglob("*.flac")]}
    return bool(names) and not names.issubset(TRUE_ACCORDION_STEMS)


def find_true_accordion_stems(job_id: str) -> list[dict]:
    base = true_model_dir(job_id)
    if not base.exists():
        return []
    files = sorted([*base.rglob("*.mp3"), *base.rglob("*.wav"), *base.rglob("*.flac")], key=stem_sort_key)
    stems = []
    for path in files:
        audible, rms_db = display_stem_has_audio(job_id, path)
        if not audible:
            continue
        rel = path.relative_to(WORKSPACE).as_posix()
        stems.append(
            {
                "id": path.relative_to(job_dir(job_id)).as_posix(),
                "name": stem_display_name(path),
                "url": media_url(rel),
                "path": str(path.relative_to(ROOT)),
                "rmsDb": rms_db,
            }
        )
    return stems


def media_url(relative_path: str) -> str:
    return f"/media/{quote(relative_path, safe='/')}"


def content_type(path: Path) -> str:
    audio_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
    }
    return audio_types.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"


def upload_for_job(job_id: str) -> Path | None:
    if not job_id.replace("-", "").isalnum():
        return None
    return next(UPLOADS.glob(f"{job_id}-*.mp3"), None)


def display_name(upload_path: Path, job_id: str) -> str:
    prefix = f"{job_id}-"
    if upload_path.name.startswith(prefix):
        return upload_path.name.removeprefix(prefix)
    return upload_path.name


def job_payload(upload_path: Path) -> dict:
    job_id = upload_path.name.split("-", 5)
    if len(job_id) >= 5:
        job_id = "-".join(job_id[:5])
    else:
        job_id = upload_path.stem
    stems = find_stems(job_id)
    return {
        "jobId": job_id,
        "filename": display_name(upload_path, job_id),
        "sourceUrl": media_url(upload_path.relative_to(WORKSPACE).as_posix()),
        "stems": stems,
        "chords": load_cached_chords(job_id),
        "analyzed": bool(stems),
        "uploadedAt": upload_path.stat().st_mtime,
    }


def list_jobs() -> list[dict]:
    uploads = sorted(UPLOADS.glob("*.mp3"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [job_payload(path) for path in uploads]


def clear_jobs(handler: BaseHTTPRequestHandler) -> None:
    for path in (UPLOADS, STEMS, EXPORTS):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    ensure_dirs()
    json_response(handler, 200, {"jobs": list_jobs(), "tools": tool_status()})


def get_job(handler: BaseHTTPRequestHandler, job_id: str) -> None:
    upload_path = upload_for_job(job_id)
    if not upload_path:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return
    json_response(handler, 200, {"job": job_payload(upload_path), "tools": tool_status()})


def upload(handler: BaseHTTPRequestHandler) -> None:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        json_response(handler, 400, {"error": "No upload body was received."})
        return
    if length > MAX_UPLOAD:
        json_response(handler, 413, {"error": "Upload is too large. Maximum size is 250 MB."})
        return

    filename = safe_name(unquote(handler.headers.get("X-Filename", "audio.mp3")))
    if not filename.lower().endswith(".mp3"):
        json_response(handler, 400, {"error": "Please upload an MP3 file."})
        return

    job_id = str(uuid.uuid4())
    target = UPLOADS / f"{job_id}-{filename}"
    with target.open("wb") as out:
        remaining = length
        while remaining:
            chunk = handler.rfile.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            out.write(chunk)
            remaining -= len(chunk)

    json_response(
        handler,
        200,
        {
            "jobId": job_id,
            "filename": filename,
            "sourceUrl": media_url(target.relative_to(WORKSPACE).as_posix()),
            "stems": [],
            "analyzed": False,
            "tools": tool_status(),
        },
    )


def separate(handler: BaseHTTPRequestHandler) -> None:
    payload = read_json(handler)
    job_id = payload.get("jobId", "")
    model = payload.get("model", COMBINED_ACCORDION_MODEL)
    if model not in ALLOWED_MODELS:
        json_response(handler, 400, {"error": "Unsupported separation model."})
        return
    upload_match = next(UPLOADS.glob(f"{job_id}-*.mp3"), None)
    if not upload_match:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return

    if model == MVSEP_ACCORDION_MODEL:
        separate_mvsep_accordion(handler, job_id, upload_match)
        return

    if model == TRUE_ACCORDION_MODEL:
        separate_true_accordion(handler, job_id, upload_match)
        return

    if model == COMBINED_ACCORDION_MODEL:
        separate_combined_accordion(handler, job_id, upload_match)
        return

    tools = tool_status()
    if model in DEMUCS_MODELS and not tools["demucs"]:
        json_response(
            handler,
            424,
            {
                "error": "Demucs is not installed. Use Install Tools, then analyze again.",
                "tools": tools,
            },
        )
        return
    out_dir = job_dir(job_id)
    if has_cached_model(job_id, model):
        json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tools, "cached": True})
        return
    clear_incomplete_model_cache(job_id, model)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_demucs(model, upload_match, out_dir)
    stems = find_stems(job_id)
    if result.returncode != 0 or not stems:
        details = result.stderr or result.stdout
        if "torchcodec" in details.lower():
            message = "TorchCodec is required for your installed torchaudio version. Run `python -m pip install torchcodec`, then restart the server."
        else:
            message = "Stem separation failed."
        json_response(
            handler,
            500,
            {
                "error": message,
                "details": details[-4000:],
                "tools": tools,
            },
        )
        return

    json_response(handler, 200, {"jobId": job_id, "stems": stems, "tools": tools})


def run_demucs(model: str, upload_match: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
    demucs = demucs_command()
    if demucs is None:
        return subprocess.CompletedProcess(["demucs"], 1, "", "Demucs is not installed.")
    cmd = [
        *demucs,
        "-n",
        model,
        "-d",
        processing_device(),
        "--mp3",
        "--mp3-bitrate",
        "320",
        "--out",
        str(out_dir),
        str(upload_match),
    ]
    return run_command(cmd)


def mvsep_command(input_dir: Path, store_dir: Path, settings: dict[str, Path] | None = None) -> list[str]:
    settings = settings or mvsep_settings()
    cmd = [
        mvsep_python(),
        str(settings["repo"] / "inference.py"),
        "--model_type",
        "bs_roformer",
        "--config_path",
        str(settings["config"]),
        "--start_check_point",
        str(settings["checkpoint"]),
        "--input_folder",
        str(input_dir),
        "--store_dir",
        str(store_dir),
    ]
    if os.environ.get("DETRACE_MVSEP_FORCE_CPU", "").strip().lower() in {"1", "true", "yes"}:
        cmd.append("--force_cpu")
    return cmd


def run_mvsep_model(upload_match: Path, store_dir: Path, settings: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    input_dir = store_dir / "_mvsep_input"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / upload_match.name
    shutil.copy2(upload_match, input_path)

    try:
        return run_command(mvsep_command(input_dir, store_dir, settings))
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)


def run_mvsep_accordion(upload_match: Path, store_dir: Path) -> subprocess.CompletedProcess[str]:
    return run_mvsep_model(upload_match, store_dir, mvsep_settings())


def run_mvsep_true_accordion(upload_match: Path, store_dir: Path) -> subprocess.CompletedProcess[str]:
    return run_mvsep_model(upload_match, store_dir, mvsep_true_settings())


def accordion_outputs(base: Path) -> list[Path]:
    files = sorted([*base.rglob("*.mp3"), *base.rglob("*.wav"), *base.rglob("*.flac")], key=stem_sort_key)
    return [path for path in files if "accordion" in path.stem.lower()]


def copy_accordion_stem(source_dir: Path, out_dir: Path) -> bool:
    matches = accordion_outputs(source_dir)
    if not matches:
        audio_files = sorted([*source_dir.rglob("*.mp3"), *source_dir.rglob("*.wav"), *source_dir.rglob("*.flac")])
        matches = audio_files if len(audio_files) == 1 else []
    if not matches:
        return False

    source = matches[0]
    target = out_dir / f"accordion{source.suffix.lower()}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return True


def copy_true_accordion_stems(source_dir: Path, out_dir: Path) -> set[str]:
    copied: set[str] = set()
    files = sorted([*source_dir.rglob("*.mp3"), *source_dir.rglob("*.wav"), *source_dir.rglob("*.flac")], key=stem_sort_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    for source in files:
        label = stem_display_name(source).lower()
        if not true_model_stem_has_audio(source):
            continue
        target = out_dir / f"{safe_stem_filename(label)}{source.suffix.lower()}"
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        copied.add(label)
    return copied


def safe_stem_filename(label: str) -> str:
    cleaned = label.lower().replace(" ", "-")
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in cleaned).strip("._-")
    return cleaned or "stem"


def true_model_stem_has_audio(path: Path) -> bool:
    rms_db = audio_rms_db(path)
    return True if rms_db is None else rms_db >= TRUE_MODEL_STEM_RMS_THRESHOLD_DB


def stem_path_by_label(base_dir: Path, label: str) -> Path | None:
    label = label.lower()
    files = sorted([*base_dir.rglob("*.mp3"), *base_dir.rglob("*.wav"), *base_dir.rglob("*.flac")], key=stem_sort_key)
    for path in files:
        if stem_display_name(path).lower() == label:
            return path
    return None


def create_true_other_residual(upload_match: Path, model_dir: Path) -> bool:
    target = model_dir / "other.mp3"
    if target.exists():
        return True

    ffmpeg = ffmpeg_executable()
    accordion = stem_path_by_label(model_dir, "accordion")
    piano = stem_path_by_label(model_dir, "piano")
    if ffmpeg is None or accordion is None or piano is None:
        return False

    temp = target.with_name(f"{target.stem}.tmp{target.suffix}")
    args = [
        ffmpeg,
        "-y",
        "-i",
        str(upload_match),
        "-i",
        str(accordion),
        "-i",
        str(piano),
        "-filter_complex",
        "[1:a]volume=-1[accordion];[2:a]volume=-1[piano];"
        "[0:a][accordion][piano]amix=inputs=3:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[aout]",
        "-map",
        "[aout]",
        *audio_codec_args(target),
        str(temp),
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        return False
    temp.replace(target)
    return True


def accordion_reduction_amount() -> float:
    configured = os.environ.get("DETRACE_ACCORDION_REDUCTION", "").strip()
    if configured:
        try:
            return max(0.0, min(1.0, float(configured)))
        except ValueError:
            pass
    return 0.62


def no_accordion_reduction_amount() -> float:
    configured = os.environ.get("DETRACE_NO_ACCORDION_REDUCTION", "").strip()
    if configured:
        try:
            return max(0.0, min(1.25, float(configured)))
        except ValueError:
            pass
    return 1.0


def audio_codec_args(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return ["-codec:a", "libmp3lame", "-q:a", "2"]
    if suffix == ".wav":
        return ["-codec:a", "pcm_s16le"]
    if suffix == ".flac":
        return ["-codec:a", "flac"]
    return []


def mix_headroom_gain(track_count: int) -> float:
    if track_count <= 1:
        return 1.0
    return max(0.22, min(0.92, 0.92 / math.sqrt(track_count)))


def accordion_stem_path(job_id: str) -> Path | None:
    base = job_dir(job_id)
    for stem in find_stems(job_id):
        if stem.get("name", "").lower() == "accordion":
            return base / stem["id"]
    return None


def create_no_accordion_mix(
    job_id: str,
    upload_match: Path,
    reduction: float | None = None,
    force: bool = False,
    aggressive: bool = False,
) -> bool:
    base = job_dir(job_id)
    target = base / NO_ACCORDION_STEM_NAME
    if target.exists() and not force:
        return True

    ffmpeg = ffmpeg_executable()
    accordion = accordion_stem_path(job_id)
    if ffmpeg is None or accordion is None or not accordion.exists() or not upload_match.exists():
        return False

    temp = target.with_name(f"{target.stem}.tmp{target.suffix}")
    default_amount = 1.18 if aggressive else no_accordion_reduction_amount()
    amount = default_amount if reduction is None else max(0.0, min(1.25, reduction))
    accordion_filter = f"[1:a]volume=-{amount}[accordion]"
    output_filter = "alimiter=limit=0.95"
    if aggressive:
        accordion_filter = f"[1:a]highpass=f=80,lowpass=f=9500,volume=-{amount}[accordion]"
        output_filter = (
            "equalizer=f=320:t=q:w=1.15:g=-1.5,"
            "equalizer=f=640:t=q:w=1.05:g=-2.5,"
            "equalizer=f=1250:t=q:w=1.05:g=-2.0,"
            "equalizer=f=2500:t=q:w=1.10:g=-1.4,"
            "alimiter=limit=0.95"
        )
    filtergraph = (
        f"{accordion_filter};"
        "[0:a][accordion]amix=inputs=2:duration=first:dropout_transition=0,"
        f"{output_filter}[aout]"
    )
    args = [
        ffmpeg,
        "-y",
        "-i",
        str(upload_match),
        "-i",
        str(accordion),
        "-filter_complex",
        filtergraph,
        "-map",
        "[aout]",
        *audio_codec_args(target),
        str(temp),
    ]
    result = run_command(args)
    if result.returncode != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        return False
    temp.replace(target)
    return True


def finalize_accordion_outputs(job_id: str, upload_match: Path) -> None:
    reduce_accordion_bleed(job_id)
    create_no_accordion_mix(job_id, upload_match, aggressive=True)


def reduce_accordion_bleed(job_id: str) -> None:
    base = job_dir(job_id)
    marker = base / ACCORDION_REDUCTION_MARKER
    if marker.exists():
        return

    ffmpeg = ffmpeg_executable()
    accordion = accordion_stem_path(job_id)
    if ffmpeg is None or accordion is None or not accordion.exists():
        return

    amount = accordion_reduction_amount()
    backup_root = base / "_accordion_originals"
    processed = []
    for stem in find_stems(job_id):
        label = stem.get("name", "").lower()
        if label not in ACCORDION_BLEED_TARGETS:
            continue
        target = base / stem["id"]
        if not target.exists() or target.resolve() == accordion.resolve():
            continue

        relative = target.relative_to(base)
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(target, backup)

        temp = target.with_name(f"{target.stem}.accordion-reduced{target.suffix}")
        filtergraph = (
            f"[1:a]volume=-{amount}[accordion];"
            "[0:a][accordion]amix=inputs=2:duration=first:dropout_transition=0,"
            "alimiter=limit=0.95[aout]"
        )
        args = [
            ffmpeg,
            "-y",
            "-i",
            str(target),
            "-i",
            str(accordion),
            "-filter_complex",
            filtergraph,
            "-map",
            "[aout]",
            *audio_codec_args(target),
            str(temp),
        ]
        result = run_command(args)
        if result.returncode != 0 or not temp.exists():
            temp.unlink(missing_ok=True)
            continue
        temp.replace(target)
        processed.append(str(relative))

    marker.write_text("\n".join(processed), encoding="utf-8")


def separate_combined_accordion(handler: BaseHTTPRequestHandler, job_id: str, upload_match: Path) -> None:
    tools = tool_status()
    missing = []
    if not tools["demucs"]:
        missing.append("Demucs")
    if not tools["mvsepAccordion"]:
        missing.append("MVSep accordion")
    if missing:
        json_response(
            handler,
            424,
            {
                "error": f"{', '.join(missing)} required for 6-stem plus accordion separation.",
                "tools": tools,
            },
        )
        return

    out_dir = job_dir(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not has_cached_model(job_id, "htdemucs_6s"):
        clear_incomplete_model_cache(job_id, "htdemucs_6s")
        demucs_result = run_demucs("htdemucs_6s", upload_match, out_dir)
        if demucs_result.returncode != 0:
            details = demucs_result.stderr or demucs_result.stdout
            json_response(
                handler,
                500,
                {
                    "error": "6-stem separation failed.",
                    "details": details[-4000:],
                    "tools": tools,
                },
            )
            return

    if has_cached_accordion(job_id):
        finalize_accordion_outputs(job_id, upload_match)
        json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tool_status(), "cached": True})
        return

    mvsep_dir = out_dir / "_mvsep_accordion"
    mvsep_dir.mkdir(parents=True, exist_ok=True)
    mvsep_result = run_mvsep_accordion(upload_match, mvsep_dir)
    copied = copy_accordion_stem(mvsep_dir, out_dir)
    shutil.rmtree(mvsep_dir, ignore_errors=True)

    stems = find_stems(job_id)
    if mvsep_result.returncode != 0 or not copied or not stems:
        json_response(
            handler,
            500,
            {
                "error": "Accordion separation failed after the 6-stem pass.",
                "details": (mvsep_result.stderr or mvsep_result.stdout)[-4000:],
                "tools": tools,
            },
        )
        return

    finalize_accordion_outputs(job_id, upload_match)
    json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tool_status()})


def separate_mvsep_accordion(handler: BaseHTTPRequestHandler, job_id: str, upload_match: Path) -> None:
    tools = tool_status()
    if not tools["mvsepAccordion"]:
        settings = mvsep_settings()
        json_response(
            handler,
            424,
            {
                "error": "MVSep accordion model is not configured.",
                "details": (
                    "Set DETRACE_MVSEP_REPO to a local Music-Source-Separation-Training checkout, "
                    "DETRACE_MVSEP_ACCORDION_CONFIG to the accordion config YAML, and "
                    "DETRACE_MVSEP_ACCORDION_CKPT to the accordion checkpoint. "
                    f"Current paths: repo={settings['repo']}; config={settings['config']}; checkpoint={settings['checkpoint']}"
                ),
                "tools": tools,
            },
        )
        return

    out_dir = job_dir(job_id)
    if has_cached_accordion(job_id):
        finalize_accordion_outputs(job_id, upload_match)
        json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tools, "cached": True})
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_mvsep_accordion(upload_match, out_dir)
    stems = find_stems(job_id)
    if result.returncode != 0 or not stems:
        json_response(
            handler,
            500,
            {
                "error": "Accordion separation failed.",
                "details": (result.stderr or result.stdout)[-4000:],
                "tools": tools,
            },
        )
        return

    finalize_accordion_outputs(job_id, upload_match)
    json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tool_status()})


def separate_true_accordion(handler: BaseHTTPRequestHandler, job_id: str, upload_match: Path) -> None:
    tools = tool_status()
    settings = mvsep_true_settings()
    if not tools["mvsepTrueAccordion"]:
        json_response(
            handler,
            424,
            {
                "error": "True local Accordion/Piano/Other model is not configured.",
                "details": (
                    "Place a true multi-stem MVSep config at models/mvsep_true_accordion/config.yaml "
                    "and its checkpoint at models/mvsep_true_accordion/checkpoint.ckpt, or set "
                    "DETRACE_MVSEP_TRUE_CONFIG and DETRACE_MVSEP_TRUE_CKPT. The config must declare "
                    "multiple instrument stems such as accordion and piano, with target_instrument unset or null. "
                    f"Current paths: repo={settings['repo']}; config={settings['config']}; checkpoint={settings['checkpoint']}"
                ),
                "tools": tools,
            },
        )
        return

    out_dir = job_dir(job_id)
    model_dir = true_model_dir(job_id)
    if has_cached_true_accordion(job_id):
        json_response(handler, 200, {"jobId": job_id, "stems": find_true_accordion_stems(job_id), "tools": tools, "cached": True})
        return

    if model_dir.exists():
        shutil.rmtree(model_dir, ignore_errors=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir = out_dir / "_mvsep_true_accordion"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir, ignore_errors=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    result = run_mvsep_true_accordion(upload_match, scratch_dir)
    copied = copy_true_accordion_stems(scratch_dir, model_dir)
    shutil.rmtree(scratch_dir, ignore_errors=True)
    if result.returncode != 0 or not copied:
        json_response(
            handler,
            500,
            {
                "error": "True multi-instrument separation failed.",
                "details": (result.stderr or result.stdout)[-4000:],
                "copied": sorted(copied),
                "tools": tools,
            },
        )
        return

    json_response(handler, 200, {"jobId": job_id, "stems": find_true_accordion_stems(job_id), "tools": tool_status()})


def append_accordion(handler: BaseHTTPRequestHandler) -> None:
    payload = read_json(handler)
    job_id = payload.get("jobId", "")
    upload_match = next(UPLOADS.glob(f"{job_id}-*.mp3"), None)
    if not upload_match:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return

    tools = tool_status()
    if not tools["mvsepAccordion"]:
        json_response(
            handler,
            424,
            {
                "error": "MVSep accordion model is not configured.",
                "tools": tools,
            },
        )
        return

    out_dir = job_dir(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    if has_cached_accordion(job_id):
        finalize_accordion_outputs(job_id, upload_match)
        json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tools, "cached": True})
        return
    mvsep_dir = out_dir / "_mvsep_accordion"
    if mvsep_dir.exists():
        shutil.rmtree(mvsep_dir)
    mvsep_dir.mkdir(parents=True, exist_ok=True)

    result = run_mvsep_accordion(upload_match, mvsep_dir)
    copied = copy_accordion_stem(mvsep_dir, out_dir)
    shutil.rmtree(mvsep_dir, ignore_errors=True)

    stems = find_stems(job_id)
    if result.returncode != 0 or not copied:
        json_response(
            handler,
            500,
            {
                "error": "Accordion separation failed.",
                "details": (result.stderr or result.stdout)[-4000:],
                "tools": tools,
                "stems": stems,
            },
        )
        return

    finalize_accordion_outputs(job_id, upload_match)
    json_response(handler, 200, {"jobId": job_id, "stems": find_stems(job_id), "tools": tool_status()})


def regenerate_no_accordion(handler: BaseHTTPRequestHandler) -> None:
    payload = read_json(handler)
    job_id = payload.get("jobId", "")
    upload_match = next(UPLOADS.glob(f"{job_id}-*.mp3"), None)
    if not upload_match:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return

    aggressive = bool(payload.get("aggressive", False))
    reduction = None
    if "reduction" in payload:
        try:
            reduction = max(0.0, min(1.25, float(payload["reduction"])))
        except (TypeError, ValueError):
            json_response(handler, 400, {"error": "Accordion removal strength must be a number."})
            return

    tools = tool_status()
    if not tools["ffmpeg"]:
        json_response(handler, 424, {"error": "FFmpeg is required to rebuild the No Accordion Mix.", "tools": tools})
        return
    if accordion_stem_path(job_id) is None:
        json_response(handler, 424, {"error": "Accordion stem must be created before rebuilding the No Accordion Mix.", "tools": tools})
        return

    ok = create_no_accordion_mix(job_id, upload_match, reduction=reduction, force=True, aggressive=aggressive)
    if not ok:
        json_response(handler, 500, {"error": "No Accordion Mix could not be rebuilt.", "tools": tools})
        return
    json_response(
        handler,
        200,
        {
            "jobId": job_id,
            "aggressive": aggressive,
            "reduction": reduction if reduction is not None else (1.18 if aggressive else no_accordion_reduction_amount()),
            "stems": find_stems(job_id),
            "tools": tool_status(),
        },
    )


def chord_templates() -> dict[str, list[float]]:
    major = (0, 4, 7)
    minor = (0, 3, 7)
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    templates = {}
    for root, name in enumerate(names):
        for suffix, intervals in (("", major), ("m", minor)):
            template = [0.0] * 12
            for interval in intervals:
                template[(root + interval) % 12] = 1.0
            templates[f"{name}{suffix}"] = template
    return templates


def normalize_vector(values: object) -> npt.NDArray[np.float64]:
    import numpy as np

    vector = np.asarray(values, dtype=float)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def best_chord(frame, templates: dict[str, list[float]]) -> str:
    frame_vector = normalize_vector(frame)
    best_name = "N"
    best_score = 0.0
    for name, template in templates.items():
        score = float(frame_vector @ normalize_vector(template))
        if score > best_score:
            best_score = score
            best_name = name
    return best_name if best_score >= 0.62 else "N"


def merge_chords(frame_chords: list[str], times: list[float], duration: float) -> list[dict]:
    if not frame_chords:
        return []

    segments = []
    start = float(times[0])
    current = frame_chords[0]
    for index, chord in enumerate(frame_chords[1:], start=1):
        if chord == current:
            continue
        end = float(times[index])
        if current != "N" and end - start >= MIN_CHORD_SECONDS:
            segments.append({"start": round(start, 2), "end": round(end, 2), "chord": current})
        start = end
        current = chord

    end = float(duration)
    if current != "N" and end - start >= MIN_CHORD_SECONDS:
        segments.append({"start": round(start, 2), "end": round(end, 2), "chord": current})

    smoothed = []
    for segment in segments:
        if smoothed and smoothed[-1]["chord"] == segment["chord"]:
            smoothed[-1]["end"] = segment["end"]
        else:
            smoothed.append(segment)
    return smoothed


def detect_chords(audio_path: Path) -> list[dict]:
    import librosa
    import numpy as np

    y, sr = librosa.load(str(audio_path), mono=True, duration=900)
    if y.size == 0:
        return []

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=CHORD_HOP_LENGTH)
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=CHORD_HOP_LENGTH)
    templates = chord_templates()
    raw_chords = [best_chord(chroma[:, index], templates) for index in range(chroma.shape[1])]

    smoothed = []
    for index, chord in enumerate(raw_chords):
        window = raw_chords[max(0, index - 1) : min(len(raw_chords), index + 2)]
        smoothed.append(Counter(window).most_common(1)[0][0])

    return merge_chords(smoothed, times.tolist(), librosa.get_duration(y=y, sr=sr))


def chords(handler: BaseHTTPRequestHandler) -> None:
    payload = read_json(handler)
    job_id = payload.get("jobId", "")
    upload_match = next(UPLOADS.glob(f"{job_id}-*.mp3"), None)
    if not upload_match:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return

    tools = tool_status()
    cached = load_cached_chords(job_id)
    if cached:
        json_response(handler, 200, {"jobId": job_id, "chords": cached, "cached": True, "tools": tools})
        return

    if not tools["chords"]:
        json_response(
            handler,
            424,
            {
                "error": "Chord detection requires librosa. Use Install Tools, then extract chords again.",
                "tools": tools,
            },
        )
        return

    try:
        segments = detect_chords(upload_match)
    except Exception as exc:
        json_response(handler, 500, {"error": "Chord detection failed.", "details": str(exc), "tools": tools})
        return

    segments = simplify_chords(segments)
    save_cached_chords(job_id, segments)
    json_response(handler, 200, {"jobId": job_id, "chords": segments, "cached": False, "tools": tools})


def export_mix(handler: BaseHTTPRequestHandler) -> None:
    payload = read_json(handler)
    job_id = payload.get("jobId", "")
    active = [str(item) for item in payload.get("stems", [])]
    try:
        bass_gain = max(-12.0, min(12.0, float(payload.get("bass", 0))))
    except (TypeError, ValueError):
        bass_gain = 0.0
    try:
        treble_gain = max(-12.0, min(12.0, float(payload.get("treble", 0))))
    except (TypeError, ValueError):
        treble_gain = 0.0
    all_stems = {}
    for stem in find_stems(job_id):
        target = ROOT / stem["path"]
        all_stems[stem.get("id", stem["name"])] = target
        all_stems[stem["name"]] = target
    upload_path = upload_for_job(job_id)

    selected = [all_stems[name] for name in active if name in all_stems]
    if not selected:
        json_response(handler, 400, {"error": "Select at least one track to export."})
        return

    tools = tool_status()
    if not tools["ffmpeg"]:
        json_response(
            handler,
            424,
            {
                "error": "FFmpeg is not installed. Use Install Tools, then export again.",
                "tools": tools,
            },
        )
        return

    export_id = str(uuid.uuid4())
    target = EXPORTS / f"{export_id}.mp3"
    ffmpeg = ffmpeg_executable()
    if ffmpeg is None:
        json_response(handler, 424, {"error": "FFmpeg is not installed. Use Install Tools, then export again.", "tools": tools})
        return
    args = [ffmpeg, "-y"]
    for source in selected:
        args.extend(["-i", str(source)])
    gain = mix_headroom_gain(len(selected))
    volume_filters = "".join(f"[{idx}:a]volume={gain:.6f}[s{idx}];" for idx in range(len(selected)))
    inputs = "".join(f"[s{idx}]" for idx in range(len(selected)))
    filtergraph = (
        f"{volume_filters}"
        f"{inputs}amix=inputs={len(selected)}:normalize=0:duration=longest:dropout_transition=0,"
        f"bass=g={bass_gain:.3f}:f=160,treble=g={treble_gain:.3f}:f=4200,"
        "alimiter=limit=0.98[aout]"
    )
    args.extend(["-filter_complex", filtergraph, "-map", "[aout]", "-codec:a", "libmp3lame", "-b:a", "320k", str(target)])

    result = run_command(args)
    if result.returncode != 0 or not target.exists():
        json_response(
            handler,
            500,
            {
                "error": "MP3 export failed.",
                "details": (result.stderr or result.stdout)[-4000:],
                "tools": tools,
            },
        )
        return

    json_response(
        handler,
        200,
        {
            "url": media_url(target.relative_to(WORKSPACE).as_posix()),
            "filename": display_name(upload_path, job_id) if upload_path else "detrace-mix.mp3",
            "tools": tools,
        },
    )


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            json_response(self, 200, {"tools": tool_status()})
            return
        if parsed.path == "/api/jobs":
            json_response(self, 200, {"jobs": list_jobs(), "tools": tool_status()})
            return
        if parsed.path.startswith("/api/jobs/"):
            get_job(self, parsed.path.removeprefix("/api/jobs/"))
            return
        if parsed.path.startswith("/media/"):
            self.serve_file(WORKSPACE / unquote(parsed.path.removeprefix("/media/")))
            return
        path = STATIC / "index.html" if parsed.path == "/" else STATIC / parsed.path.lstrip("/")
        self.serve_file(path)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/media/"):
            self.serve_file(WORKSPACE / unquote(parsed.path.removeprefix("/media/")), body=False)
            return
        path = STATIC / "index.html" if parsed.path == "/" else STATIC / parsed.path.lstrip("/")
        self.serve_file(path, body=False)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            upload(self)
            return
        if parsed.path == "/api/separate":
            separate(self)
            return
        if parsed.path == "/api/accordion":
            append_accordion(self)
            return
        if parsed.path == "/api/no-accordion":
            regenerate_no_accordion(self)
            return
        if parsed.path == "/api/export":
            export_mix(self)
            return
        if parsed.path == "/api/chords":
            chords(self)
            return
        if parsed.path == "/api/install-tools":
            install_tools(self)
            return
        if parsed.path == "/api/shutdown":
            shutdown(self)
            return
        json_response(self, 404, {"error": "Unknown endpoint."})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs":
            clear_jobs(self)
            return
        json_response(self, 404, {"error": "Unknown endpoint."})

    def serve_file(self, path: Path, body: bool = True) -> None:
        try:
            resolved = path.resolve()
            allowed = (STATIC.resolve(), WORKSPACE.resolve())
            if not any(resolved == base or base in resolved.parents for base in allowed):
                raise FileNotFoundError
            if not resolved.exists() or not resolved.is_file():
                raise FileNotFoundError
            file_size = resolved.stat().st_size
        except FileNotFoundError:
            self.send_error(404)
            return

        mime = content_type(resolved)
        range_header = self.headers.get("Range")
        if range_header:
            parsed_range = self.parse_range(range_header, file_size)
            if parsed_range is None:
                self.send_error(416)
                return
            start, end = parsed_range
            content_length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", mime)
            if resolved == STATIC.resolve() or STATIC.resolve() in resolved.parents:
                self.send_header("Cache-Control", "no-store")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(content_length))
            self.end_headers()
            if not body:
                return
            with resolved.open("rb") as file:
                file.seek(start)
                self.wfile.write(file.read(content_length))
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        if resolved == STATIC.resolve() or STATIC.resolve() in resolved.parents:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        if not body:
            return
        with resolved.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def parse_range(self, header: str, file_size: int) -> tuple[int, int] | None:
        if not header.startswith("bytes="):
            return None
        value = header.removeprefix("bytes=").split(",", 1)[0].strip()
        start_text, _, end_text = value.partition("-")
        try:
            if start_text:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
            else:
                suffix_length = int(end_text)
                start = max(file_size - suffix_length, 0)
                end = file_size - 1
        except ValueError:
            return None
        if start < 0 or end < start or start >= file_size:
            return None
        return start, min(end, file_size - 1)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def start_server() -> None:
    global ACTIVE_SERVER
    ensure_dirs()
    port = PORT
    while True:
        try:
            server = ThreadingHTTPServer((HOST, port), AppHandler)
            break
        except OSError:
            if "PORT" in os.environ:
                raise
            port += 1

    print(f"DeTrace is running at http://{HOST}:{port}")
    print(f"Tool status: {tool_status()}")
    ACTIVE_SERVER = server
    try:
        server.serve_forever()
    finally:
        terminate_active_processes()
        server.server_close()
        ACTIVE_SERVER = None


if __name__ == "__main__":
    start_server()
