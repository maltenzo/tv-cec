#!/bin/bash
# Idempotente. Lo corre a mano la primera vez y después tv-deploy en cada cambio.
set -e
cd "$(dirname "$0")"
U=$(id -nu 1000)  # usuario normal: "pi" en la imagen estándar; las units se renderizan con el real

command -v cec-ctl >/dev/null && command -v mpv >/dev/null || apt-get install -y v4l-utils mpv python3
install -m755 tv tv-console tv-sync tv-api.py /usr/local/bin/
[ -f /etc/tv-api.token ] || { openssl rand -hex 16 > /etc/tv-api.token; chown "$U" /etc/tv-api.token; chmod 600 /etc/tv-api.token; }
grep -q 'video=HDMI-A-1' /boot/firmware/cmdline.txt || sed -i '1s|$| video=HDMI-A-1:1920x1080@60D|' /boot/firmware/cmdline.txt
grep -q 'loglevel=3' /boot/firmware/cmdline.txt || sed -i '1s|$| quiet loglevel=3|' /boot/firmware/cmdline.txt  # sin mensajes del kernel encima del negro
systemctl disable -q getty@tty1  # sin login en tty1; tv-console lo arranca a pedido
usermod -aG video,render,audio "$U"

changed=
for u in *.service *.timer; do
  sed "s/^User=pi/User=$U/; s#/home/pi/#/home/$U/#" "$u" > /tmp/unit.$$
  cmp -s /tmp/unit.$$ "/etc/systemd/system/$u" || { install -m644 /tmp/unit.$$ "/etc/systemd/system/$u"; changed="$changed $u"; }
  rm -f /tmp/unit.$$
done
# ponytail: limpieza de tv-watch (ya no existe), borrar cuando no quede ninguna Pi vieja
[ -f /etc/systemd/system/tv-watch.service ] && { systemctl disable --now tv-watch; rm -f /etc/systemd/system/tv-watch.service /usr/local/bin/tv-watch; }
systemctl daemon-reload
systemctl enable --now tv-video tv-api tv-deploy.timer tv-sync.timer
systemctl restart tv-api
case "$changed" in *tv-video.service*) systemctl restart tv-video;; esac  # no cortar el video si no cambió
