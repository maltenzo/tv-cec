#!/usr/bin/env python3
"""GET /on /off /status con token (Authorization: Bearer X, o ?token=X)."""
import hmac, os, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = os.environ.get("TV_API_TOKEN") or open(os.environ.get("TV_API_TOKEN_FILE", "/etc/tv-api.token")).read().strip()


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        given = self.headers.get("Authorization", "").removeprefix("Bearer ") or parse_qs(u.query).get("token", [""])[0]
        if not hmac.compare_digest(given.encode(), TOKEN.encode()):
            return self.send(401, "unauthorized")
        cmd = u.path.strip("/")
        if cmd not in ("on", "off", "status"):
            return self.send(404, "not found")
        try:
            r = subprocess.run(["/usr/local/bin/tv", cmd], capture_output=True, text=True, timeout=40)
            self.send(200 if r.returncode == 0 else 500, (r.stdout + r.stderr).strip() or "ok")
        except subprocess.TimeoutExpired:
            self.send(504, "timeout")

    def send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write((body + "\n").encode())


ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()  # ponytail: sin TLS, solo via Tailscale
