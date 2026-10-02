"""Loopback-only static host for the Learning OS prototype."""

from __future__ import annotations

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_FILE = "learning-os-app.html"


class LearningOSStaticHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        if self.path.split("?", 1)[0].endswith((".html", ".js", ".css")) or self.path.split("?", 1)[0] == "/":
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/":
            self.path = f"/{APP_FILE}"
        super().do_GET()


def create_server(host: str, port: int, directory: Path) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Static host must bind to a loopback address")
    handler = functools.partial(LearningOSStaticHandler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    server = create_server(args.host, args.port, args.directory.resolve())
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
