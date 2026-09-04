"""Read-only local file server used to feed GitHub web upload automation."""

from __future__ import annotations

import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", "node_modules", ".venv", "venv"}
EXCLUDE_SUFFIXES = {".pyc", ".exe"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path == "/files":
            files = []
            for path in sorted(ROOT.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(ROOT).as_posix()
                if set(rel.split("/")) & EXCLUDE_DIRS:
                    continue
                if rel.endswith(tuple(EXCLUDE_SUFFIXES)):
                    continue
                files.append(rel)
            self._send(200, json.dumps(files).encode("utf-8"), "application/json")
            return
        prefix = "/raw/"
        if not self.path.startswith(prefix):
            self._send(404, b"not found", "text/plain")
            return
        rel = self.path[len(prefix):]
        target = (ROOT / rel).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            self._send(403, b"forbidden", "text/plain")
            return
        if not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, target.read_bytes(), "application/octet-stream")

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
