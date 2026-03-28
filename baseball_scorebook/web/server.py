"""Launch helpers for serving the web app locally."""

from __future__ import annotations

import socket
import threading
import webbrowser

import uvicorn

from baseball_scorebook.web.api import app


def find_free_port(host: str = "127.0.0.1") -> int:
    """Return a currently free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def open_browser_later(url: str) -> None:
    """Open the browser after a short delay."""
    timer = threading.Timer(0.75, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


def run_server(*, host: str = "127.0.0.1", port: int | None = None, open_browser: bool = True) -> None:
    """Run the local FastAPI server."""
    resolved_port = port or find_free_port(host)
    url = f"http://{host}:{resolved_port}"
    if open_browser:
        open_browser_later(url)
    uvicorn.run(app, host=host, port=resolved_port, log_level="info")
