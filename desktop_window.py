from __future__ import annotations

import ctypes
import os
import socket
import threading
import time
from pathlib import Path

import webview

import server


APP_USER_MODEL_ID = "RobertoRaimondo.DeTrace.App"


def app_icon_path() -> str | None:
    root = Path(__file__).resolve().parent
    for icon_path in (
        root / "assets" / "detrace-icon.ico",
        root / "assets" / "detrace-icon.png",
    ):
        if icon_path.exists():
            return str(icon_path)
    return None


def set_windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def apply_native_window_icon() -> None:
    icon_path = app_icon_path()
    if os.name != "nt" or not icon_path:
        return
    try:
        from System.Drawing import Icon
    except Exception:
        return

    for window in webview.windows:
        native = getattr(window, "native", None)
        if native is None:
            continue
        try:
            native.Icon = Icon(icon_path)
        except Exception:
            pass


def find_free_port(start: int = 5180) -> int:
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1


def run_server(port: int) -> None:
    os.environ["PORT"] = str(port)
    server.PORT = port
    server.start_server()


class AppApi:
    def exit_app(self) -> dict[str, bool]:
        def close() -> None:
            time.sleep(0.1)
            server.stop_server()
            for window in webview.windows:
                window.destroy()

        threading.Thread(target=close, daemon=True).start()
        return {"ok": True}


def main() -> None:
    set_windows_app_id()
    port = find_free_port()
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    webview.create_window(
        "DeTrace",
        url,
        js_api=AppApi(),
        width=1180,
        height=820,
        min_size=(720, 560),
        maximized=True,
    )
    try:
        webview.start(apply_native_window_icon, gui="edgechromium", icon=app_icon_path())
    finally:
        server.stop_server()


if __name__ == "__main__":
    main()
