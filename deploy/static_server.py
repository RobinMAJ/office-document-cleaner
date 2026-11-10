"""Serve the release's explicit public-file allowlist over loopback HTTP."""
import argparse
import hashlib
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

RELEASE = Path(__file__).resolve().parents[1]
DIST = RELEASE / "site"


def no_symlinks(path):
    for item in (path,) + tuple(path.parents):
        if item.is_symlink():
            raise RuntimeError("Symlinked files or directories are not supported")


def load_public_files():
    no_symlinks(RELEASE)
    manifest_path = RELEASE / "MANIFEST.json"
    no_symlinks(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    files = manifest["public_files"]
    if not files or "index.html" not in files:
        raise RuntimeError("Public file allowlist is incomplete")
    for name, expected in files.items():
        if name.startswith("/") or any(part in ("", ".", "..") or part.startswith(".") for part in name.split("/")):
            raise RuntimeError("Invalid public-file path")
        path = DIST / name
        no_symlinks(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Public release hash mismatch: " + name)
    actual = {str(path.relative_to(DIST)) for path in DIST.rglob("*") if path.is_file()}
    if actual != set(files):
        raise RuntimeError("Unexpected or missing public files")
    return files


def handler_type(files):
    class StaticHandler(BaseHTTPRequestHandler):
        server_version = "OfficeCleanerStatic"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            # Document uploads and extraction stay in the browser. Do not log
            # document names, query strings, headers or request bodies.
            pass

        def reject(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

        def file_response(self, head_only=False):
            try:
                parsed = urlsplit(self.path)
                if parsed.scheme or parsed.netloc:
                    return self.reject(404)
                path = unquote(parsed.path, errors="strict")
                if path == "/":
                    name = "index.html"
                else:
                    parts = path.split("/")
                    if not path.startswith("/") or any(part in ("", ".", "..") or part.startswith(".") for part in parts[1:]):
                        return self.reject(404)
                    name = path[1:]
                if "\\" in name or "\x00" in name or name not in files:
                    return self.reject(404)
                target = DIST / name
                no_symlinks(target)
                if not target.is_file():
                    return self.reject(404)
                content = target.read_bytes()
                if hashlib.sha256(content).hexdigest() != files[name]:
                    return self.reject(503)
            except (UnicodeError, ValueError, OSError, RuntimeError):
                return self.reject(404)
            overrides = {".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm"}
            mime = overrides.get(target.suffix, mimetypes.guess_type(name)[0] or "application/octet-stream")
            if mime.startswith("text/"):
                mime += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'none'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            if not head_only:
                self.wfile.write(content)

        def do_GET(self):
            self.file_response()

        def do_HEAD(self):
            self.file_response(head_only=True)

        def do_POST(self):
            self.reject(405)

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST
        do_OPTIONS = do_POST

    return StaticHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18815)
    args = parser.parse_args()
    os.umask(0o077)
    files = load_public_files()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_type(files))
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
