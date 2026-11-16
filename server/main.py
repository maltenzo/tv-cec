#!/usr/bin/env python3
"""API en Railway. Auth: Authorization: Bearer $API_TOKEN.
POST /media?name=a.mp4 (cuerpo = el archivo) · GET /media/<sha> · DELETE /media/<sha>
POST /command {"cmd": "on"|"off"|"console"} (la Pi lo ejecuta en su próximo ciclo)
GET / (la UI, sin token) · GET /state · PUT /state {"playlist": [sha, ...], "schedule": {"on": "08:00", "off": "22:00"} | null}"""
import hashlib, hmac, json, os, re, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = os.environ["API_TOKEN"]
DATA = os.environ.get("DATA_DIR", "/data")  # volumen de Railway montado en /data
MEDIA, STATE = f"{DATA}/media", f"{DATA}/state.json"
VIDEO = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
SHA = re.compile(r"[0-9a-f]{64}")
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"), "rb").read()
LOCK = threading.Lock()  # ponytail: lock global para leer-modificar-escribir state.json; sobra para un solo usuario


def load():
    try:
        return json.load(open(STATE))
    except FileNotFoundError:
        return {"media": {}, "playlist": [], "schedule": None, "command": None}


def save(s):
    os.makedirs(DATA, exist_ok=True)
    json.dump(s, open(STATE + ".tmp", "w"))
    os.replace(STATE + ".tmp", STATE)


class H(BaseHTTPRequestHandler):
    def auth(self):
        given = self.headers.get("Authorization", "").removeprefix("Bearer ")
        ok = hmac.compare_digest(given.encode(), TOKEN.encode())
        if not ok:
            self.send(401, "unauthorized")
        return ok

    def send(self, code, body="", ctype="text/plain"):
        if not isinstance(body, (str, bytes)):
            body, ctype = json.dumps(body), "application/json"
        body = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def sha_arg(self):
        m = re.fullmatch(r"/media/([0-9a-f]{64})", urlparse(self.path).path)
        return m and m.group(1)

    def do_GET(self):
        if self.path == "/":  # la página es pública y no lleva datos; el token se pide en el navegador
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if not self.auth():
            return
        if self.path == "/state":
            return self.send(200, load())
        sha, rec = self.sha_arg(), None
        if sha:
            rec = load()["media"].get(sha)
        if not rec:
            return self.send(404, "not found")
        path = f"{MEDIA}/{rec['file']}"
        if not os.path.exists(path):
            return self.send(404, "not found")
        self.send_response(200)
        self.send_header("Content-Length", str(os.path.getsize(path)))
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                self.wfile.write(chunk)

    def do_POST(self):
        if not self.auth():
            return
        u = urlparse(self.path)
        if u.path == "/command":
            return self.queue_command()
        if u.path != "/media":
            return self.send(404, "not found")
        name = os.path.basename(parse_qs(u.query).get("name", [""])[0])
        ext = os.path.splitext(name)[1].lower()
        left = int(self.headers.get("Content-Length", 0))
        if ext not in VIDEO | IMAGE or not left:
            return self.send(400, "hace falta ?name=archivo.ext (video o imagen conocida) y cuerpo no vacío")
        os.makedirs(MEDIA, exist_ok=True)
        tmp, h = f"{MEDIA}/{uuid.uuid4().hex}.tmp", hashlib.sha256()
        try:
            with open(tmp, "wb") as f:
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        os.unlink(tmp)
                        return self.send(400, "truncated")
                    f.write(chunk); h.update(chunk); left -= len(chunk)
        except OSError as e:  # disco lleno (el volumen de Hobby es de 5 GB)
            if os.path.exists(tmp):
                os.unlink(tmp)
            return self.send(507, f"no se pudo guardar: {e.strerror}")
        sha = h.hexdigest()
        with LOCK:
            s = load()
            if sha in s["media"]:
                os.unlink(tmp)
            else:
                os.replace(tmp, f"{MEDIA}/{sha}{ext}")
                s["media"][sha] = {"name": name, "file": sha + ext, "kind": "video" if ext in VIDEO else "image"}
                save(s)
        self.send(200, {"sha": sha})

    def queue_command(self):
        try:
            cmd = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1 << 10)))["cmd"]
            assert cmd in ("on", "off", "console")
        except (ValueError, KeyError, TypeError, AssertionError):
            return self.send(400, 'se espera {"cmd": "on" | "off" | "console"}')
        with LOCK:
            s = load()
            s["command"] = {"id": uuid.uuid4().hex, "cmd": cmd, "at": time.time()}
            save(s)
        self.send(200, s["command"])

    def do_PUT(self):
        if not self.auth():
            return
        if self.path != "/state":
            return self.send(404, "not found")
        try:
            b = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1 << 20)))
            assert isinstance(b, dict)
        except (ValueError, AssertionError):
            return self.send(400, "json inválido")
        with LOCK:
            s = load()
            pl, sc = b.get("playlist", s["playlist"]), b.get("schedule", s["schedule"])
            if not (isinstance(pl, list) and all(x in s["media"] for x in pl)):
                return self.send(400, "playlist: lista de sha que existan en /media")
            if sc is not None and not (isinstance(sc, dict) and all(isinstance(sc.get(k), str) and HHMM.fullmatch(sc[k]) for k in ("on", "off")) and sc["on"] != sc["off"]):
                return self.send(400, 'schedule: {"on": "HH:MM", "off": "HH:MM"} distintos, o null')
            s["playlist"], s["schedule"] = pl, sc
            save(s)
        self.send(200, s)

    def do_DELETE(self):
        if not self.auth():
            return
        sha = self.sha_arg()
        with LOCK:
            s = load()
            rec = s["media"].pop(sha, None) if sha else None
            if not rec:
                return self.send(404, "not found")
            s["playlist"] = [x for x in s["playlist"] if x != sha]
            save(s)
            os.unlink(f"{MEDIA}/{rec['file']}")
        self.send(200, s)


ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8000))), H).serve_forever()
