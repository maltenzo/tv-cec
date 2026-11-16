# 01 · Reemplazar el video

**Estado:** hecho en código; falta desplegar y probar.

## Objetivo
Subir un video nuevo a la API y que la Pi lo reproduzca sola, sin tocar la Pi.

## Hecho
- `server/main.py`: `PUT /video`, `GET /video/sha`, `GET /video` (streaming, auth bearer, escritura atómica, sha256).
- `server/Dockerfile`.
- `tv-sync` + `tv-sync.service` + `tv-sync.timer`; `install.sh` los instala.
- README: comandos de subida y config de la Pi.

## Pendiente
- Crear servicio en Railway (Root Directory `server`, var `API_TOKEN`, volumen en `/data`).
- Crear `/etc/tv-sync.conf` en la Pi (`URL`, `TOKEN`).
- Commit y verificar de punta a punta: subir video → la Pi lo baja → `tv-video` reinicia.

## Criterio de hecho
Subo un mp4 con curl y en ≤ 1-2 min la tele muestra el nuevo.

## Límites conocidos
Un solo video; un upload a la vez; límites de tamaño/tiempo de request de Railway sin medir.
