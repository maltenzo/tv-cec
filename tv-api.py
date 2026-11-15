#!/usr/bin/env python3
"""GET / (página con botones, sin token), GET /on /off /status /console con token (Authorization: Bearer X, o ?token=X)."""
import hmac, os, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = os.environ.get("TV_API_TOKEN") or open(os.environ.get("TV_API_TOKEN_FILE", "/etc/tv-api.token")).read().strip()


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Tele</title><style>body{font:20px sans-serif;text-align:center;margin:2em}button{font:inherit;padding:1em 1.5em;margin:.3em}</style>
<h1>Tele</h1><p id=o>…</p>
<button onclick=go('on')>Prender</button><button onclick=go('off')>Apagar</button>
<button onclick=go('console')>Video / Consola</button><button onclick=go('status')>Estado</button>
<script>
const T=localStorage.t||(localStorage.t=prompt('Token'));
async function go(c){o.textContent='…';const r=await fetch('/'+c,{headers:{Authorization:'Bearer '+T}});
if(r.status==401)delete localStorage.t;o.textContent=c+': '+(await r.text())}
go('status')
</script>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self.send(200, PAGE, "text/html; charset=utf-8")
        given = self.headers.get("Authorization", "").removeprefix("Bearer ") or parse_qs(u.query).get("token", [""])[0]
        if not hmac.compare_digest(given.encode(), TOKEN.encode()):
            return self.send(401, "unauthorized")
        cmd = u.path.strip("/")
        if cmd not in ("on", "off", "status", "console"):
            return self.send(404, "not found")
        try:
            if cmd in ("on", "off"):  # ponytail: teles sin CEC ignoran tv on/off; igual pasamos el video/señal
                subprocess.run(["/usr/local/bin/tv-console", cmd], timeout=15)
            r = subprocess.run((["/usr/local/bin/tv-console"] if cmd == "console" else ["/usr/local/bin/tv", cmd]), capture_output=True, text=True, timeout=40)
            self.send(200 if r.returncode == 0 else 500, (r.stdout + r.stderr).strip() or "ok")
        except subprocess.TimeoutExpired:
            self.send(504, "timeout")

    def send(self, code, body, ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write((body + "\n").encode())


ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()  # ponytail: sin TLS, solo via Tailscale
