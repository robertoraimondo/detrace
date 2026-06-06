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
        ui_item(ui, "chords", "Present" if check_module(runtime_python, "librosa") else "Missing")
        ui_item(ui, "desktop", "Present" if check_module(runtime_python, "webview") else "Missing")
    else:
        ui_item(ui, "demucs", "Waiting for runtime")
        ui_item(ui, "ffmpeg", "Waiting for runtime")
        ui_item(ui, "codecs", "Waiting for runtime")
        ui_item(ui, "chords", "Waiting for runtime")
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
    root.geometry("1920x1080")
    root.resizable(True, True)
    root.attributes("-topmost", True)
    root.configure(bg="#0c181c")
    root.state("zoomed")

    status = tk.StringVar(value="Preparing DeTrace.")
    items = {
        "python": tk.StringVar(value="Checking"),
        "runtime": tk.StringVar(value="Checking"),
        "demucs": tk.StringVar(value="Checking"),
        "ffmpeg": tk.StringVar(value="Checking"),
        "codecs": tk.StringVar(value="Checking"),
        "chords": tk.StringVar(value="Checking"),
        "desktop": tk.StringVar(value="Checking"),
    }

    splash = tk.Frame(root, bg="#10242a")
    setup = tk.Frame(root, bg="#eef3f2")

    splash_art = load_launcher_art()

    splash_image = tk.Label(splash, image=splash_art, bg="#10242a", borderwidth=0, cursor="hand2")
    splash_image.pack(fill="both", expand=True)
    header = tk.Frame(setup, bg="#10242a")
    header.pack(fill="x")
    tk.Label(header, text="DeTrace", bg="#10242a", fg="#f8fbf9", font=("Segoe UI", 22, "bold")).pack(
        anchor="w", padx=34, pady=(24, 2)
    )
    tk.Label(header, textvariable=status, bg="#10242a", fg="#c8d7d7", font=("Segoe UI", 10)).pack(
        anchor="w", padx=36, pady=(0, 24)
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
        ("Chord detection engine", "chords"),
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
    }

    setup_started = {"value": False}

    def show_setup() -> None:
        if setup_started["value"]:
            return
        setup_started["value"] = True
        splash.pack_forget()
        setup.pack(fill="both", expand=True)
        root.state("zoomed")
        refresh_requirement_status(ui, venv_python() if venv_python().exists() else None)
        threading.Thread(target=work, args=("desktop",), daemon=True).start()

    splash_image.bind("<Button-1>", lambda _event: show_setup())
    splash.pack(fill="both", expand=True)
    root.update_idletasks()
    root.state("zoomed")
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


def load_launcher_art() -> tk.PhotoImage:
    image_path = BUNDLE_DIR / "static" / "start-splash.png"
    if not image_path.exists():
        image_path = INSTALL_DIR / "static" / "start-splash.png"
    if not image_path.exists():
        image_path = BUNDLE_DIR / "static" / "launcher-splash.png"
    if not image_path.exists():
        image_path = INSTALL_DIR / "static" / "launcher-splash.png"
    return tk.PhotoImage(file=str(image_path))


if __name__ == "__main__":
    main()
