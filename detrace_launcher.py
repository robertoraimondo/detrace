from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox


if getattr(sys, "frozen", False):
    INSTALL_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS"))
else:
    INSTALL_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = INSTALL_DIR

APP_DIR = INSTALL_DIR / ".detrace-app"
VENV_DIR = INSTALL_DIR / ".detrace-runtime"
REQ_FILE = APP_DIR / "requirements.txt"
WHEELHOUSE_DIR = APP_DIR / "wheelhouse"


def run(args: list[str], cwd: Path = APP_DIR) -> subprocess.CompletedProcess[str]:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


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
    ui_busy(ui, True)
    result = run(
        [
            "winget",
            "install",
            "--id",
            "Python.Python.3.11",
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
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
    result = run(
        [
            str(runtime_python),
            "-c",
            f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec('{module}') else 1)",
        ]
    )
    return result.returncode == 0


def refresh_requirement_status(ui: dict, runtime_python: Path | None = None) -> None:
    ui_item(ui, "python", "Present" if find_python() else "Missing")
    ui_item(ui, "runtime", "Present" if venv_python().exists() else "Missing")

    if runtime_python and runtime_python.exists():
        ui_item(ui, "demucs", "Present" if check_module(runtime_python, "demucs") else "Missing")
        ui_item(ui, "ffmpeg", "Present" if check_module(runtime_python, "imageio_ffmpeg") else "Missing")
        ui_item(
            ui,
            "codecs",
            "Present"
            if check_module(runtime_python, "lameenc") and check_module(runtime_python, "soundfile")
            else "Missing",
        )
        ui_item(ui, "desktop", "Present" if check_module(runtime_python, "webview") else "Missing")
    else:
        ui_item(ui, "demucs", "Waiting for runtime")
        ui_item(ui, "ffmpeg", "Waiting for runtime")
        ui_item(ui, "codecs", "Waiting for runtime")
        ui_item(ui, "desktop", "Waiting for runtime")


def ensure_runtime(ui: dict) -> Path:
    ui_status(ui, "Checking system requirements...")
    refresh_requirement_status(ui)
    ui_progress(ui, 10)

    python = find_python()
    if not python:
        python = install_python(ui)

    if not venv_python().exists():
        ui_status(ui, "Creating DeTrace runtime...")
        ui_item(ui, "runtime", "Missing - creating")
        ui_busy(ui, True)
        result = run([*python, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Could not create runtime.")
        ui_item(ui, "runtime", "Present")

    runtime_python = venv_python()
    refresh_requirement_status(ui, runtime_python)
    ui_progress(ui, 45)
    ui_status(ui, "Installing and checking requirements...")
    ui_busy(ui, True)
    commands = [[str(runtime_python), "-m", "pip", "install", "--upgrade", "pip"]]
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
        result = run(command)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Requirement installation failed.")

    refresh_requirement_status(ui, runtime_python)
    ui_busy(ui, False)
    ui_progress(ui, 85)
    return runtime_python


def copy_file(name: str) -> None:
    source = BUNDLE_DIR / name
    target = APP_DIR / name
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_dir(name: str) -> None:
    source = BUNDLE_DIR / name
    target = APP_DIR / name
    if not source.exists():
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def ensure_app_files(ui: dict) -> None:
    ui_status(ui, "Preparing application files...")
    ui_progress(ui, 25)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("requirements.txt", "server.py", "desktop_window.py"):
        copy_file(name)
    copy_dir("static")
    copy_dir("wheelhouse")


def start_desktop(runtime_python: Path) -> None:
    subprocess.Popen(
        [str(runtime_python), str(APP_DIR / "desktop_window.py")],
        cwd=str(APP_DIR),
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
    env = os.environ.copy()
    env["PORT"] = str(port)
    subprocess.Popen(
        [str(runtime_python), str(APP_DIR / "server.py")],
        cwd=str(APP_DIR),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    return url


def ui_status(ui: dict, text: str) -> None:
    ui["root"].after(0, ui["status"].set, text)


def ui_item(ui: dict, key: str, value: str) -> None:
    ui["root"].after(0, ui["items"][key].set, value)


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
    root = tk.Tk()
    root.title("DeTrace")
    root.geometry("640x680")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#0c181c")

    status = tk.StringVar(value="Choose how to run DeTrace.")
    items = {
        "python": tk.StringVar(value="Checking"),
        "runtime": tk.StringVar(value="Checking"),
        "demucs": tk.StringVar(value="Checking"),
        "ffmpeg": tk.StringVar(value="Checking"),
        "codecs": tk.StringVar(value="Checking"),
        "desktop": tk.StringVar(value="Checking"),
    }

    splash = tk.Frame(root, bg="#10242a")
    setup = tk.Frame(root, bg="#eef3f2")

    art = tk.Canvas(splash, width=600, height=312, highlightthickness=0, bg="#10242a")
    art.pack(fill="x")
    draw_splash_art(art)

    tk.Label(
        splash,
        text="DeTrace",
        bg="#10242a",
        fg="#f8fbf9",
        font=("Segoe UI", 30, "bold"),
    ).pack(pady=(20, 4))
    tk.Label(
        splash,
        text="Separate every voice and instrument.",
        bg="#10242a",
        fg="#d3e1df",
        font=("Segoe UI", 13),
    ).pack(pady=(0, 18))
    tk.Button(
        splash,
        text="Continue",
        command=lambda: show_setup(),
        bg="#f0a33a",
        fg="#10242a",
        activebackground="#f8ca70",
        activeforeground="#10242a",
        relief="flat",
        padx=24,
        pady=10,
        font=("Segoe UI", 11, "bold"),
    ).pack(pady=(0, 24))
    credits = tk.Frame(splash, bg="#10242a")
    credits.pack(fill="x", padx=42)
    for text in (
        "This project is open source and available under the MIT License.",
        "Author: Roberto Raimondo - IS Senior Systems Engineer II",
        "© 2026 All Rights Reserved.",
    ):
        tk.Label(credits, text=text, bg="#10242a", fg="#a9bbbb", font=("Segoe UI", 9)).pack(anchor="w", pady=1)

    header = tk.Frame(setup, bg="#10242a")
    header.pack(fill="x")
    tk.Label(header, text="DeTrace", bg="#10242a", fg="#f8fbf9", font=("Segoe UI", 22, "bold")).pack(
        anchor="w", padx=34, pady=(24, 2)
    )
    tk.Label(header, textvariable=status, bg="#10242a", fg="#c8d7d7", font=("Segoe UI", 10)).pack(
        anchor="w", padx=36, pady=(0, 22)
    )

    progress_wrap = tk.Frame(setup, bg="#eef3f2")
    progress_wrap.pack(fill="x", padx=36, pady=(22, 12))
    progress_track = tk.Frame(progress_wrap, bg="#d6dde3", height=12)
    progress_track.pack(fill="x")
    progress_bar = tk.Frame(progress_track, bg="#0b6f7c", width=1, height=12)
    progress_bar.place(x=0, y=0, relheight=1)

    checklist = tk.Frame(setup, bg="#eef3f2")
    checklist.pack(fill="x", padx=36)
    labels = [
        ("Python", "python"),
        ("DeTrace runtime", "runtime"),
        ("Demucs separation engine", "demucs"),
        ("FFmpeg codec/export support", "ffmpeg"),
        ("MP3/audio codecs", "codecs"),
        ("Desktop window support", "desktop"),
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

    actions = tk.Frame(setup, bg="#eef3f2")
    actions.pack(fill="x", padx=36, pady=(18, 0))
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
    desktop_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))
    web_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

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
    }

    def show_setup() -> None:
        splash.pack_forget()
        setup.pack(fill="both", expand=True)
        center_window(root)
        refresh_requirement_status(ui, venv_python() if venv_python().exists() else None)

    splash.pack(fill="both", expand=True)
    root.update_idletasks()
    center_window(root)
    root.lift()
    root.focus_force()

    def set_buttons(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        root.after(0, desktop_btn.configure, {"state": state})
        root.after(0, web_btn.configure, {"state": state})

    def work(mode: str) -> None:
        try:
            set_buttons(False)
            ensure_app_files(ui)
            runtime_python = ensure_runtime(ui)
            ui_status(ui, "Starting DeTrace desktop app..." if mode == "desktop" else "Starting DeTrace web server...")
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
                messagebox.showerror("DeTrace setup failed", str(exc))

            root.after(0, fail)

    desktop_btn.configure(command=lambda: threading.Thread(target=work, args=("desktop",), daemon=True).start())
    web_btn.configure(command=lambda: threading.Thread(target=work, args=("web",), daemon=True).start())
    root.mainloop()


def center_window(root: tk.Tk) -> None:
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


def draw_splash_art(canvas: tk.Canvas) -> None:
    for index in range(34):
        ratio = index / 33
        red = int(16 + ratio * 174)
        green = int(36 + ratio * 116)
        blue = int(42 - ratio * 5)
        color = f"#{red:02x}{green:02x}{blue:02x}"
        canvas.create_rectangle(0, index * 10, 600, (index + 1) * 10, fill=color, outline=color)

    canvas.create_oval(50, 36, 210, 196, fill="#7edbd3", outline="", stipple="gray50")
    canvas.create_oval(424, 28, 650, 254, fill="#f8ca70", outline="", stipple="gray50")
    canvas.create_oval(326, 202, 506, 382, fill="#c95f4f", outline="", stipple="gray50")

    waves = [
        (210, "#f8fbf9", 4),
        (238, "#9be7df", 5),
        (266, "#f8ca70", 4),
    ]
    for y, color, width in waves:
        points = []
        for x in range(-20, 641, 44):
            offset = 30 if (x // 44) % 2 else -24
            points.extend([x, y + offset])
        canvas.create_line(*points, fill=color, width=width, smooth=True, capstyle="round")

    draw_note(canvas, 302, 58, 1.0, -8)
    draw_note(canvas, 120, 134, 0.68, 10)
    draw_note(canvas, 472, 154, 0.58, -14)


def draw_note(canvas: tk.Canvas, x: int, y: int, scale: float, angle: int) -> None:
    # Tk canvas has no grouped rotation, so this draws a stylized upright note.
    stem_h = int(150 * scale)
    stem_w = max(8, int(14 * scale))
    head_w = int(80 * scale)
    head_h = int(48 * scale)
    canvas.create_rectangle(x + 58, y, x + 58 + stem_w, y + stem_h, fill="#f8fbf9", outline="")
    canvas.create_oval(x, y + stem_h - 12, x + head_w, y + stem_h + head_h, fill="#f8fbf9", outline="")
    canvas.create_arc(
        x + 58,
        y + 4,
        x + int(154 * scale),
        y + int(96 * scale),
        start=278,
        extent=250,
        style="arc",
        outline="#f8fbf9",
        width=max(8, int(12 * scale)),
    )


if __name__ == "__main__":
    main()
