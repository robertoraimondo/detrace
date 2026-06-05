from __future__ import annotations
import importlib.util
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import uuid
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
    }


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def install_tools(handler: BaseHTTPRequestHandler) -> None:
    before = tool_status()
    packages = []
    if not before["demucs"]:
        packages.append("demucs")
    if not before["ffmpeg"]:
        packages.append("imageio-ffmpeg")
    if not before["codecs"]:
        packages.extend(["lameenc", "soundfile"])

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
        if parsed.path == "/api/install-tools":
            install_tools(self)
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
    server.serve_forever()


if __name__ == "__main__":
    start_server()
