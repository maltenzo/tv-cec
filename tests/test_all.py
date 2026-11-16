"""python3 -m unittest discover tests — levanta el server real en local y corre tv-sync contra él (systemctl y tv falsos)."""
import hashlib, json, os, pathlib, subprocess, tempfile, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT, TOKEN = "8123", "t"
URL = f"http://localhost:{PORT}"


def call(method, path, data=None, token=TOKEN):
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
    req = urllib.request.Request(URL + path, data=data, method=method, headers={"Authorization": "Bearer " + token})
    try:
        body = urllib.request.urlopen(req).read()
    except urllib.error.HTTPError as e:
        return e.code
    try:
        return json.loads(body)
    except ValueError:
        return body


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        self.srv = subprocess.Popen(["python3", ROOT / "server/main.py"], stderr=subprocess.DEVNULL,
                                    env={**os.environ, "API_TOKEN": TOKEN, "DATA_DIR": str(self.d / "data"), "PORT": PORT})
        self.addCleanup(self.stop)  # corre aunque setUp falle más abajo
        for _ in range(50):  # esperar a que el server escuche
            try:
                if call("GET", "/state", token="x") == 401:
                    break
            except OSError:
                time.sleep(0.1)
        (self.d / "pi").mkdir()
        (self.d / "bin").mkdir()
        (self.d / "tv-sync.conf").write_text(f"URL={URL}\nTOKEN={TOKEN}\nDIR={self.d}/pi\n")
        quiet = {"tv": "status", "systemctl": "is-active"}  # las consultas de estado no se anotan: solo las acciones
        for cmd in ("systemctl", "tv", "tv-console"):  # falsos: solo anotan cómo los llamaron
            (self.d / "bin" / cmd).write_text(f'#!/bin/sh\n[ "$1" = "{quiet.get(cmd)}" ] && {{ echo on; exit 0; }}\necho "$@" >> {self.d}/{cmd}.log\n')
            (self.d / "bin" / cmd).chmod(0o755)

    def stop(self):
        self.srv.kill()
        self.srv.wait()
        self.tmp.cleanup()

    def sync(self, now=None):
        env = {**os.environ, "TV_SYNC_CONF": str(self.d / "tv-sync.conf"), "PATH": f"{self.d}/bin:{os.environ['PATH']}"}
        if now:
            env["TV_NOW"] = now
        return subprocess.run([ROOT / "tv-sync"], env=env).returncode

    def log(self, cmd):
        p = self.d / f"{cmd}.log"
        return p.read_text().split("\n")[:-1] if p.exists() else []

    def upload(self, name, data):
        return call("POST", f"/media?name={name}", data)["sha"]

    def test_ui_publica(self):
        r = urllib.request.urlopen(URL + "/")  # sin token
        self.assertIn(b"<title>Tele</title>", r.read())
        self.assertIn("text/html", r.headers["Content-Type"])

    def test_auth(self):
        for m, p in (("GET", "/state"), ("POST", "/media?name=a.mp4"), ("PUT", "/state"), ("DELETE", "/media/" + "0" * 64)):
            self.assertEqual(call(m, p, b"x", token="mal"), 401, (m, p))

    def test_media_y_state(self):
        video = os.urandom(100_000)
        sha = self.upload("a.MP4", video)
        self.assertEqual(sha, hashlib.sha256(video).hexdigest())
        self.assertEqual(call("GET", "/media/" + sha), video)
        self.assertEqual(call("GET", "/state")["media"][sha]["kind"], "video")
        self.assertEqual(call("GET", "/state")["media"][sha]["file"], sha + ".mp4")
        self.assertEqual(self.upload("../x/b.png", b"img"), hashlib.sha256(b"img").hexdigest())  # solo se usa el basename
        self.assertEqual(call("POST", "/media?name=a.exe", b"x"), 400)
        self.assertEqual(call("POST", "/media?name=a.mp4", b""), 400)
        self.assertEqual(call("GET", "/media/" + "0" * 64), 404)

    def test_put_state_valida(self):
        sha = self.upload("a.mp4", b"x")
        self.assertEqual(call("PUT", "/state", {"playlist": ["f" * 64]}), 400)
        self.assertEqual(call("PUT", "/state", {"schedule": {"on": "8:00", "off": "22:00"}}), 400)
        self.assertEqual(call("PUT", "/state", {"schedule": {"on": "08:00", "off": "08:00"}}), 400)
        self.assertEqual(call("PUT", "/state", b"no es json"), 400)
        s = call("PUT", "/state", {"playlist": [sha, sha], "schedule": {"on": "08:00", "off": "22:00"}})
        self.assertEqual(s["playlist"], [sha, sha])
        self.assertEqual(call("PUT", "/state", {"schedule": None})["playlist"], [sha, sha])  # tocar una clave no pisa la otra
        self.assertEqual(call("GET", "/state")["schedule"], None)

    def test_delete_saca_de_la_playlist(self):
        a, b = self.upload("a.mp4", b"aa"), self.upload("b.jpg", b"bb")
        call("PUT", "/state", {"playlist": [a, b]})
        self.assertEqual(call("DELETE", "/media/" + a)["playlist"], [b])
        self.assertEqual(call("GET", "/media/" + a), 404)
        self.assertEqual(call("DELETE", "/media/" + a), 404)

    def test_sync_playlist(self):
        self.assertEqual(self.sync(), 0)  # estado vacío
        a, b = self.upload("a.mp4", b"video"), self.upload("b.jpg", b"imagen")
        call("PUT", "/state", {"playlist": [a, b]})
        self.assertEqual(self.sync(), 0)
        pi = self.d / "pi"
        self.assertEqual((pi / "playlist.m3u").read_text(), f"{pi}/media/{a}.mp4\n{pi}/media/{b}.jpg\n")
        self.assertEqual((pi / "media" / f"{b}.jpg").read_bytes(), b"imagen")
        n = len(self.log("systemctl"))
        self.assertEqual(self.sync(), 0)  # sin cambios: no reinicia
        self.assertEqual(len(self.log("systemctl")), n)
        call("PUT", "/state", {"playlist": [b]})  # cambia: reinicia y borra lo que sobra
        self.assertEqual(self.sync(), 0)
        self.assertEqual(len(self.log("systemctl")), n + 1)
        self.assertEqual(sorted(p.name for p in (pi / "media").iterdir()), [f"{b}.jpg"])
        self.assertIn("try-restart tv-video", self.log("systemctl")[-1])

    def test_sync_rechaza_archivo_corrupto_y_espera_antes_de_reintentar(self):
        sha = self.upload("a.mp4", b"video")
        call("PUT", "/state", {"playlist": [sha]})
        f = self.d / "data" / "media" / f"{sha}.mp4"
        f.write_bytes(b"corrupto")
        self.assertNotEqual(self.sync(), 0)
        self.assertFalse((self.d / "pi" / "playlist.m3u").exists())  # no se publica nada a medias
        f.write_bytes(b"video")  # el servidor ya está arreglado...
        self.assertEqual(self.sync(), 0)
        self.assertFalse((self.d / "pi" / "playlist.m3u").exists())  # ...pero hay que esperar: no se vuelve a bajar enseguida
        (self.d / "pi" / "download.retry").unlink()  # pasan los 10 min
        self.assertEqual(self.sync(), 0)
        self.assertTrue((self.d / "pi" / "playlist.m3u").exists())
        self.assertFalse((self.d / "pi" / "download.retry").exists())

    def test_sin_conf_no_hace_ruido(self):
        (self.d / "tv-sync.conf").unlink()
        r = subprocess.run([ROOT / "tv-sync"], env={**os.environ, "TV_SYNC_CONF": str(self.d / "tv-sync.conf")}, capture_output=True)
        self.assertEqual((r.returncode, r.stderr), (0, b""))

    def test_comandos(self):
        self.assertEqual(call("POST", "/command", {"cmd": "reboot"}), 400)
        self.assertEqual(call("POST", "/command", b"basura"), 400)
        self.assertEqual(call("POST", "/command", {"cmd": "on"}, token="mal"), 401)
        call("POST", "/command", {"cmd": "on"})
        self.sync(); self.assertEqual(self.log("tv"), ["on"])
        self.sync(); self.assertEqual(self.log("tv"), ["on"])  # no se repite
        call("POST", "/command", {"cmd": "off"})
        self.sync(); self.assertEqual(self.log("tv"), ["on", "off"])
        call("POST", "/command", {"cmd": "console"})
        self.sync(); self.assertEqual(self.log("tv-console"), [""])
        self.assertEqual(self.log("tv"), ["on", "off"])

    def test_comando_viejo_no_se_ejecuta(self):
        call("POST", "/command", {"cmd": "on"})
        st = json.loads((self.d / "data" / "state.json").read_text())
        st["command"]["at"] -= 3600  # la Pi estaba apagada una hora
        (self.d / "data" / "state.json").write_text(json.dumps(st))
        self.sync(); self.assertEqual(self.log("tv"), [])
        self.sync(); self.assertEqual(self.log("tv"), [])  # y tampoco después

    def test_archivo_faltante_en_disco_da_404(self):
        sha = self.upload("a.mp4", b"x")
        (self.d / "data" / "media" / f"{sha}.mp4").unlink()
        self.assertEqual(call("GET", "/media/" + sha), 404)

    def test_disco_lleno(self):
        import resource
        limit = lambda: resource.setrlimit(resource.RLIMIT_FSIZE, (100_000, 100_000))  # simula el disco lleno
        srv = subprocess.Popen(["python3", ROOT / "server/main.py"], stderr=subprocess.DEVNULL, preexec_fn=limit,
                               env={**os.environ, "API_TOKEN": TOKEN, "DATA_DIR": str(self.d / "small"), "PORT": "8124"})
        self.addCleanup(srv.wait); self.addCleanup(srv.kill)
        for _ in range(50):
            try:
                urllib.request.urlopen(urllib.request.Request("http://localhost:8124/state"))
            except urllib.error.HTTPError:
                break
            except OSError:
                time.sleep(0.1)
        req = urllib.request.Request("http://localhost:8124/media?name=a.mp4", data=os.urandom(300_000), method="POST", headers={"Authorization": "Bearer " + TOKEN})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 507)
        self.assertEqual(list((self.d / "small" / "media").iterdir()), [])  # sin .tmp huérfano

    def test_status(self):
        self.assertIsNone(call("GET", "/status"))
        self.assertEqual(call("POST", "/status", {"tv": "on"}), 400)
        self.assertEqual(call("POST", "/status", {"tv": "on", "video": "si"}), 400)
        self.assertEqual(call("POST", "/status", {"tv": "on", "video": True}, token="mal"), 401)
        self.sync()  # el tv falso responde "on" y el systemctl falso "activo"
        st = call("GET", "/status")
        self.assertEqual((st["tv"], st["video"]), ("on", True))
        self.assertLess(st["age"], 10)

    def test_sin_red_no_rompe(self):
        self.srv.kill()
        self.srv.wait()
        self.assertEqual(self.sync(), 0)

    def test_horario(self):
        call("PUT", "/state", {"schedule": {"on": "08:00", "off": "22:00"}})
        self.sync("15:00"); self.assertEqual(self.log("tv"), ["on"])  # primer arranque: aplica el estado actual
        self.sync("15:30"); self.assertEqual(self.log("tv"), ["on"])  # sin cambio: no insiste (respeta un override manual)
        self.sync("23:00"); self.assertEqual(self.log("tv"), ["on", "off"])
        self.sync("03:00"); self.assertEqual(self.log("tv"), ["on", "off"])
        self.sync("08:00"); self.assertEqual(self.log("tv"), ["on", "off", "on"])  # borde: on inclusivo
        self.sync("22:00"); self.assertEqual(self.log("tv"), ["on", "off", "on", "off"])  # off exclusivo
        call("PUT", "/state", {"schedule": {"on": "22:00", "off": "06:00"}})  # cruza medianoche
        self.sync("23:00"); self.assertEqual(self.log("tv")[-1], "on")
        self.sync("07:00"); self.assertEqual(self.log("tv")[-1], "off")
        call("PUT", "/state", {"schedule": None})
        n = len(self.log("tv"))
        self.sync("23:00"); self.assertEqual(len(self.log("tv")), n)

    def test_horario_sin_red_usa_el_cache(self):
        call("PUT", "/state", {"schedule": {"on": "08:00", "off": "22:00"}})
        self.sync("15:00")
        self.srv.kill()
        self.srv.wait()
        self.sync("23:00")
        self.assertEqual(self.log("tv"), ["on", "off"])


if __name__ == "__main__":
    unittest.main()
