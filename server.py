from __future__ import annotations
import importlib.util
import json
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
from urllib.parse import quote, unquote, urlparse


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
WORKSPACE = ROOT / "workspace"
UPLOADS = WORKSPACE / "uploads"
STEMS = WORKSPACE / "stems"
EXPORTS = WORKSPACE / "exports"

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "5180"))
MAX_UPLOAD = 250 * 1024 * 1024
ALLOWED_MODELS = {"htdemucs", "htdemucs_6s"}
PASSING_CHORD_MAX_SECONDS = 1.6
CHORD_HOP_LENGTH = 2048
MIN_CHORD_SECONDS = 0.18
ACTIVE_SERVER: ThreadingHTTPServer | None = None
ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
ACTIVE_PROCESSES_LOCK = threading.Lock()


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
    demucs_exe = shutil.which("demucs")
    if demucs_exe:
        return [demucs_exe]
    if module_available("demucs"):
        return [sys.executable, "-m", "demucs.separate"]
    return None


def tool_status() -> dict:
    return {
        "demucs": demucs_command() is not None,
        "ffmpeg": ffmpeg_executable() is not None,
        "codecs": codec_status(),
        "chords": module_available("librosa"),
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


def find_stems(job_id: str) -> list[dict]:
    base = job_dir(job_id)
    files = sorted([*base.rglob("*.mp3"), *base.rglob("*.wav")])
    stems = []
    for wav in files:
        rel = wav.relative_to(WORKSPACE).as_posix()
        stems.append(
            {
                "name": wav.stem,
                "url": media_url(rel),
                "path": str(wav.relative_to(ROOT)),
            }
        )
    return stems


def media_url(relative_path: str) -> str:
    return f"/media/{quote(relative_path, safe='/')}"


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
            shutil.rmtree(path)
    ensure_dirs()
    json_response(handler, 200, {"jobs": [], "tools": tool_status()})


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

    filename = safe_name(handler.headers.get("X-Filename", "audio.mp3"))
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
    model = payload.get("model", "htdemucs")
    if model not in ALLOWED_MODELS:
        json_response(handler, 400, {"error": "Unsupported separation model."})
        return
    upload_match = next(UPLOADS.glob(f"{job_id}-*.mp3"), None)
    if not upload_match:
        json_response(handler, 404, {"error": "Uploaded file was not found."})
        return

    tools = tool_status()
    if not tools["demucs"]:
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
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    demucs = demucs_command()
    if demucs is None:
        json_response(handler, 424, {"error": "Demucs is not installed. Use Install Tools, then analyze again.", "tools": tools})
        return
    cmd = [*demucs, "-n", model, "--mp3", "--mp3-bitrate", "320", "--out", str(out_dir), str(upload_match)]
    result = run_command(cmd)
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


def normalize_vector(values) -> object:
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
    all_stems = {stem["name"]: ROOT / stem["path"] for stem in find_stems(job_id)}
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
    inputs = "".join(f"[{idx}:a]" for idx in range(len(selected)))
    filtergraph = f"{inputs}amix=inputs={len(selected)}:normalize=0,alimiter=limit=0.95[aout]"
    args.extend(["-filter_complex", filtergraph, "-map", "[aout]", "-codec:a", "libmp3lame", "-q:a", "2", str(target)])

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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            upload(self)
            return
        if parsed.path == "/api/separate":
            separate(self)
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

    def serve_file(self, path: Path) -> None:
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

        mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        range_header = self.headers.get("Range")
        if range_header:
            start, end = self.parse_range(range_header, file_size)
            if start is None:
                self.send_error(416)
                return
            content_length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", mime)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(content_length))
            self.end_headers()
            with resolved.open("rb") as file:
                file.seek(start)
                self.wfile.write(file.read(content_length))
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        with resolved.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def parse_range(self, header: str, file_size: int) -> tuple[int | None, int | None]:
        if not header.startswith("bytes="):
            return None, None
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
            return None, None
        if start < 0 or end < start or start >= file_size:
            return None, None
        return start, min(end, file_size - 1)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


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
