#!/bin/bash
# Idempotente. Lo corre a mano la primera vez y después tv-deploy en cada cambio.
set -e
cd "$(dirname "$0")"

command -v cec-ctl >/dev/null && command -v mpv >/dev/null || apt-get install -y v4l-utils mpv python3
install -m755 tv tv-watch tv-api.py /usr/local/bin/
[ -f /etc/tv-api.token ] || { openssl rand -hex 16 > /etc/tv-api.token; chown pi /etc/tv-api.token; chmod 600 /etc/tv-api.token; }
grep -q 'video=HDMI-A-1' /boot/firmware/cmdline.txt || sed -i '1s|$| video=HDMI-A-1:1920x1080@60D|' /boot/firmware/cmdline.txt
usermod -aG video,render,audio pi

changed=
for u in *.service *.timer; do
  cmp -s "$u" "/etc/systemd/system/$u" || { cp "$u" /etc/systemd/system/; changed="$changed $u"; }
done
systemctl daemon-reload
systemctl enable --now tv-video tv-api tv-watch tv-deploy.timer
systemctl restart tv-api tv-watch
case "$changed" in *tv-video.service*) systemctl restart tv-video;; esac  # no cortar el video si no cambió
