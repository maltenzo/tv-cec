# Tele por HDMI-CEC desde una Raspberry Pi

Pi 3B+/4/5, Raspberry Pi OS Lite (Bookworm), usuario normal (`pi` u otro: se detecta el uid 1000). **Nada probado en hardware real todavía.**

## Instalación y auto deploy

La Pi hace `git pull` cada minuto (timer `tv-deploy`) y, si hay commits nuevos, corre `install.sh`. Solo hace falta que pueda leer el remoto (sin puertos abiertos ni secretos en CI).

```bash
# en la Pi, una sola vez
sudo git clone <url-del-repo> /opt/tv      # repo privado: usar deploy key de solo lectura (o https con token)
sudo /opt/tv/install.sh
cp /ruta/a/tu/video.mp4 /home/pi/video.mp4  # H.264 1080p
sudo reboot
```

Después: `git push` a la rama clonada y en ~1 minuto queda desplegado (`journalctl -u tv-deploy` para ver). `install.sh` es idempotente y también se puede correr a mano.

Activar CEC en la tele (Anynet+, SimpLink, Bravia Sync, etc.).

## Probar (primero a mano, antes de los servicios)

```bash
ls /dev/cec0
TV_DEBUG=1 tv status      # muestra la salida cruda de cec-ctl
tv off; tv on; tv selftest
```

Si algo no anda, mirar la salida con `TV_DEBUG=1`:
- **Physical address**: si el parseo falla, `TV_PHYS=1.0.0.0 tv on` (o el que muestre `cec-ctl -d /dev/cec0 --playback`). `f.f.f.f` = sin enlace HDMI/EDID.
- **Estado**: se busca `pwr-state: on|standby|to-on|to-standby`; cualquier otra cosa → `unknown`.
- **Conector DRM**: `modetest -c | grep -i hdmi` o `ls /sys/class/drm/`; si no es `HDMI-A-1` (ej. Pi 4/5 con el 2º puerto), cambiarlo en `cmdline.txt` y en `tv-video.service` (`--drm-connector`).
- `tv status` da `unknown` si la tele está en standby profundo / ahorro de energía (no contesta CEC). El watcher lo ignora: conserva el último estado conocido, así standby → unknown → on igual reinicia el video.

## API

```bash
TOKEN=$(sudo cat /etc/tv-api.token)
curl -H "Authorization: Bearer $TOKEN" http://<ip-pi>:8080/status   # /on /off /status
```

Sin TLS ni puertos abiertos: acceder desde afuera con Tailscale (`http://<nombre-tailscale>:8080`).

## Cron (opcional; alternativa al horario de la API)

```cron
0 8  * * * /usr/local/bin/tv on
0 22 * * * /usr/local/bin/tv off
```

## Consola vs video

`tv-console` alterna: para `tv-video` (se ve la consola) o lo arranca. No persiste al reiniciar. Si el video tapa todo: SSH a la Pi y correrlo (o a ciegas en el teclado: login + `tv-console`).

## Web

`http://<ip-pi>:8080/` → botones prender/apagar/video-consola/estado. Pide el token una vez (`sudo cat /etc/tv-api.token`) y lo guarda en el navegador. Sigue sin TLS: usar solo en LAN/Tailscale.

## API en Railway

**UI web:** abrir `https://<app>.up.railway.app/` (pide el `API_TOKEN` una vez y lo guarda en el navegador): subir archivos, armar/ordenar la playlist y editar el horario. Lo de abajo es lo mismo por curl.

`server/` es un servicio aparte (Railway → Root Directory `server`, variable `API_TOKEN`, volumen en `/data`). La Pi *consulta* la API cada minuto (`tv-sync.timer`): sin puertos abiertos. Todo con `Authorization: Bearer $API_TOKEN`.

```bash
H="Authorization: Bearer $API_TOKEN"
# subir (video o imagen; devuelve el sha)
curl -H "$H" -T clip.mp4 "$URL/media?name=clip.mp4" -X POST
# playlist (orden = orden de reproducción, en loop) y horario; cada clave es opcional
curl -H "$H" -X PUT "$URL/state" -d '{"playlist":["<sha1>","<sha2>"],"schedule":{"on":"08:00","off":"22:00"}}'
curl -H "$H" "$URL/state"                    # media subida + playlist + horario
curl -H "$H" -X DELETE "$URL/media/<sha>"    # borra y saca de la playlist
curl -H "$H" -X PUT "$URL/state" -d '{"schedule":null}'   # sin horario
```

Horario: `tv-sync` usa la hora local de la Pi (`timedatectl set-timezone America/Argentina/Buenos_Aires`) y actúa solo al cambiar de estado, así un `tv on/off` manual dura hasta el próximo cambio. Imágenes: 10 s cada una (`--image-display-duration` en `tv-video.service`).

En la Pi, una vez:

```bash
printf 'URL=https://<app>.up.railway.app\nTOKEN=<API_TOKEN>\n' | sudo tee /etc/tv-sync.conf; sudo chmod 600 /etc/tv-sync.conf
```

## Tests

`python3 -m unittest discover tests` — levanta `server/main.py` en local y corre `tv-sync` contra él (con `systemctl` y `tv` falsos); no necesita la Pi.
