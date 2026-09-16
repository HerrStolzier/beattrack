"""Serve one prepared retrieval review on loopback without exposing its key."""
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def make_handler(directory: Path):
    page = (directory / "index.html").read_bytes()
    match = re.search(rb'<script id="experiment-data" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("index.html has no experiment data")
    data = json.loads(match.group(1))
    clip_names = [row["clip"] for case in data["cases"] for row in [case["seed"], *case["candidates"]]]
    if any(not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{24}\.wav", name) for name in clip_names):
        raise ValueError("index.html contains an invalid clip name")
    allowed = set(clip_names)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path in {"/", "/index.html"}:
                body, content_type = page, "text/html; charset=utf-8"
            elif path.startswith("/clips/") and path.removeprefix("/clips/") in allowed:
                name = path.removeprefix("/clips/")
                body, content_type = (directory / "clips" / name).read_bytes(), "audio/wav"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--port", type=int, default=8110)
    args = parser.parse_args()
    handler = make_handler(args.directory)
    print(f"Retrieval review: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
