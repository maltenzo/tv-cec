# Tele por HDMI-CEC desde una Raspberry Pi

Pi 3B+/4/5, Raspberry Pi OS Lite (Bookworm), usuario `pi`. **Nada probado en hardware real todavía.**

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

## Cron (opcional, `crontab -e` del usuario `pi`)

```cron
0 8  * * * /usr/local/bin/tv on
0 22 * * * /usr/local/bin/tv off
```
