from __future__ import annotations

from email.message import Message
from http import HTTPStatus
from io import BytesIO
from typing import Callable, Iterable

import server


StartResponse = Callable[[str, list[tuple[str, str]]], None]


class WSGIAppHandler(server.AppHandler):
    def send_response(self, code: int, message: str | None = None) -> None:
        self._status_code = code
        self._status_message = message or HTTPStatus(code).phrase

    def send_response_only(self, code: int, message: str | None = None) -> None:
        self.send_response(code, message)

    def send_header(self, keyword: str, value: str) -> None:
        if keyword.lower() not in {"connection", "transfer-encoding"}:
            self._response_headers.append((keyword, value))

    def end_headers(self) -> None:
        return

    def flush_headers(self) -> None:
        return

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        status_message = message or HTTPStatus(code).phrase
        body = f"{code} {status_message}\n".encode("utf-8")
        self.send_response(code, status_message)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(0 if self.command == "HEAD" else len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def address_string(self) -> str:
        return self.client_address[0]


def _headers_from_environ(environ: dict) -> Message:
    headers = Message()
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key.removeprefix("HTTP_").replace("_", "-").title()
            headers[name] = str(value)
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = str(environ["CONTENT_TYPE"])
    if environ.get("CONTENT_LENGTH"):
        headers["Content-Length"] = str(environ["CONTENT_LENGTH"])
    return headers


def application(environ: dict, start_response: StartResponse) -> Iterable[bytes]:
    server.ensure_dirs()

    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO") or "/"
    query = environ.get("QUERY_STRING")

    handler = WSGIAppHandler.__new__(WSGIAppHandler)
    handler.command = method
    handler.path = f"{path}?{query}" if query else path
    handler.request_version = environ.get("SERVER_PROTOCOL", "HTTP/1.1")
    handler.client_address = (environ.get("REMOTE_ADDR", ""), 0)
    handler.server = None
    handler.headers = _headers_from_environ(environ)
    handler.rfile = environ.get("wsgi.input") or BytesIO()
    handler.wfile = BytesIO()
    handler._status_code = 200
    handler._status_message = HTTPStatus.OK.phrase
    handler._response_headers: list[tuple[str, str]] = []

    route = getattr(handler, f"do_{method}", None)
    if route is None:
        handler.send_error(405, "Method Not Allowed")
    else:
        route()

    status = f"{handler._status_code} {handler._status_message}"
    start_response(status, handler._response_headers)
    return [handler.wfile.getvalue()]
