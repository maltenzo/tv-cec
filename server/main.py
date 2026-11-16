#!/usr/bin/env python3
"""API en Railway. PUT /video (sube), GET /video/sha, GET /video. Todo con Authorization: Bearer $API_TOKEN."""
import hashlib, hmac, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ["API_TOKEN"]
DATA = os.environ.get("DATA_DIR", "/data")  # volumen de Railway montado en /data
VIDEO, SHA = f"{DATA}/video.mp4", f"{DATA}/video.sha"


class H(BaseHTTPRequestHandler):
    def auth(self):
        given = self.headers.get("Authorization", "").removeprefix("Bearer ")
        ok = hmac.compare_digest(given.encode(), TOKEN.encode())
        if not ok:
            self.send(401, b"unauthorized")
        return ok

    def send(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.auth():
            return
        if self.path == "/video/sha" and os.path.exists(SHA):
            return self.send(200, open(SHA, "rb").read())
        if self.path == "/video" and os.path.exists(VIDEO):
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(os.path.getsize(VIDEO)))
            self.end_headers()
            with open(VIDEO, "rb") as f:
                while chunk := f.read(1 << 20):
                    self.wfile.write(chunk)
            return
        self.send(404, b"not found")

    def do_PUT(self):
        if not self.auth():
            return
        if self.path != "/video":
            return self.send(404, b"not found")
        left, h = int(self.headers.get("Content-Length", 0)), hashlib.sha256()
        if not left:
            return self.send(400, b"empty")
        os.makedirs(DATA, exist_ok=True)
        with open(VIDEO + ".tmp", "wb") as f:  # ponytail: un upload a la vez asumido; lock si hace falta
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    return self.send(400, b"truncated")
                f.write(chunk); h.update(chunk); left -= len(chunk)
        os.replace(VIDEO + ".tmp", VIDEO)
        open(SHA, "w").write(h.hexdigest())
        self.send(200, h.hexdigest().encode())


ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8000))), H).serve_forever()
