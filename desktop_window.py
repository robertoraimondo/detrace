from __future__ import annotations

import os
import socket
import threading
from pathlib import Path

import webview

import server


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


def main() -> None:
    port = find_free_port()
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    webview.create_window(
        "DeTrace",
        url,
        width=1280,
        height=860,
        min_size=(1280, 760),
        maximized=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
