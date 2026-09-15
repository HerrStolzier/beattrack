"""Serve the listening sheet on localhost; resolve official preview URLs on demand.

Only index.html and previews for its listed track IDs are exposed. The method
key and snapshot stay inaccessible. Audio streams directly from Deezer's CDN.
"""
import argparse
import json
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--port", type=int, default=8108)
    args = parser.parse_args()
    page = (args.directory / "index.html").read_bytes()
    match = re.search(rb'<script id="experiment-data" type="application/json">(.*?)</script>', page, re.S)
    data = json.loads(match.group(1))
    allowed = {str(song.get("deezer_id")) for case in data["cases"]
               for song in [case["seed"], *case["candidates"]] if song.get("deezer_id")}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)
                return
            track_id = self.path.removeprefix("/preview/")
            if not self.path.startswith("/preview/") or track_id not in allowed or not track_id.isdigit():
                self.send_error(404)
                return
            try:
                with urllib.request.urlopen(f"https://api.deezer.com/track/{track_id}", timeout=15) as response:
                    track = json.load(response)
                preview = track.get("preview", "")
                url = urlparse(preview)
                if (track.get("id") != int(track_id) or url.scheme != "https" or
                        not (url.hostname or "").endswith(".dzcdn.net") or url.username or url.password):
                    self.send_error(404, "No official preview available")
                    return
                self.send_response(302)
                self.send_header("Location", preview)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            except (OSError, ValueError):
                self.send_error(502, "Preview lookup failed")

        def log_message(self, format, *args):
            pass  # No signed CDN URLs or listening history in the console.

    print(f"Listening sheet: http://localhost:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
