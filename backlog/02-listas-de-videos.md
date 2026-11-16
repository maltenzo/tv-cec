# 02 · Listas de videos

**Depende de:** 01.

**Estado:** hecho en código y tests; falta probar en la Pi.

## Objetivo
Armar y manejar una lista ordenada de videos que se reproduce en loop.

## Diseño
- Servidor: archivos en `/data/media/<sha256>.<ext>`; `/data/state.json` con `{"playlist": [sha, ...]}` (escritura atómica).
- Endpoints: `POST /media` (sube, devuelve sha), `GET /media` (lista), `DELETE /media/<sha>`, `GET /state`, `PUT /state` (guarda la lista).
- `tv-sync`: lee `/state`, baja los sha que falten a `~/media/`, borra los que ya no están, escribe `~/playlist.m3u`, reinicia `tv-video` solo si cambió.
- `tv-video.service`: `mpv --playlist=/home/pi/playlist.m3u --loop-playlist=inf`.
- Migrar el `video.mp4` de la fase 1 a una lista de un elemento.

## Criterio de hecho
Subo 3 videos, defino su orden por API, la tele los reproduce en secuencia y en loop; cambiar el orden o quitar uno se refleja en ≤ 2 min.

## A decidir
Si hace falta nombre/etiqueta por archivo además del sha (probablemente sí para una futura UI).

## Hecho (como quedó)
`POST /media?name=`, `GET /media/<sha>`, `DELETE /media/<sha>`, `GET/PUT /state`; `tv-sync` (ahora Python) baja lo que falta, verifica sha256, borra lo que sobra, escribe `playlist.m3u` y reinicia `tv-video` solo si cambió; `tv-video.service` usa `--playlist` con `--loop-playlist=inf`. Playlist = lista de sha (un sha puede repetirse).

## Pendiente
- Probar en la Pi: mpv con playlist, cambio de orden en caliente.
- Una playlist vacía deja a mpv reintentando cada 3 s (inofensivo, pero no muestra nada).
- Nombres/etiquetas ya se guardan (`name`); falta una UI para verlos.
