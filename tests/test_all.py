"""python3 -m unittest discover tests  — levanta el server real en local y corre tv-sync contra él (systemctl falso)."""
import hashlib, os, pathlib, subprocess, tempfile, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT, TOKEN = "8123", "t"
URL = f"http://localhost:{PORT}"


def call(method, path, data=None, token=TOKEN):
    req = urllib.request.Request(URL + path, data=data, method=method, headers={"Authorization": "Bearer " + token})
    try:
        return urllib.request.urlopen(req).read()
    except urllib.error.HTTPError as e:
        return e.code


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.srv = subprocess.Popen(["python3", ROOT / "server/main.py"], stderr=subprocess.DEVNULL,
                                   env={**os.environ, "API_TOKEN": TOKEN, "DATA_DIR": cls.tmp.name + "/data", "PORT": PORT})
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.kill()
        cls.tmp.cleanup()

    def sync(self):
        d = pathlib.Path(self.tmp.name)
        (d / "tv-sync.conf").write_text(f"URL={URL}\nTOKEN={TOKEN}\nVIDEO={d}/video.mp4\n")
        (d / "bin").mkdir(exist_ok=True)
        (d / "bin/systemctl").write_text(f'#!/bin/sh\necho "$@" >> {d}/systemctl.log\n')
        (d / "bin/systemctl").chmod(0o755)
        env = {**os.environ, "TV_SYNC_CONF": str(d / "tv-sync.conf"), "PATH": f"{d}/bin:{os.environ['PATH']}"}
        return subprocess.run([ROOT / "tv-sync"], env=env).returncode

    def restarts(self):
        p = pathlib.Path(self.tmp.name) / "systemctl.log"
        return p.read_text().count("try-restart tv-video") if p.exists() else 0

    def test_1_auth_y_sin_video(self):
        self.assertEqual(call("GET", "/video/sha", token="mal"), 401)
        self.assertEqual(call("PUT", "/video", b"x", token="mal"), 401)
        self.assertEqual(call("GET", "/video/sha"), 404)
        self.assertEqual(call("PUT", "/video", b""), 400)

    def test_2_sync_sin_video_no_hace_nada(self):
        self.assertEqual(self.sync(), 0)
        self.assertEqual(self.restarts(), 0)

    def test_3_subir_y_sincronizar(self):
        data = os.urandom(2_000_000)
        sha = hashlib.sha256(data).hexdigest()
        self.assertEqual(call("PUT", "/video", data).decode(), sha)
        self.assertEqual(call("GET", "/video/sha").decode(), sha)
        self.assertEqual(call("GET", "/video"), data)
        self.assertEqual(self.sync(), 0)
        self.assertEqual((pathlib.Path(self.tmp.name) / "video.mp4").read_bytes(), data)
        self.assertEqual(self.restarts(), 1)
        self.assertEqual(self.sync(), 0)  # sin cambios: no reinicia
        self.assertEqual(self.restarts(), 1)
        call("PUT", "/video", b"otro video")  # reemplazo: baja y reinicia
        self.assertEqual(self.sync(), 0)
        self.assertEqual((pathlib.Path(self.tmp.name) / "video.mp4").read_bytes(), b"otro video")
        self.assertEqual(self.restarts(), 2)


if __name__ == "__main__":
    unittest.main()
