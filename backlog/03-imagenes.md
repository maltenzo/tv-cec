# 03 · Imágenes

**Depende de:** 02.

**Estado:** hecho en código y tests; falta probar en la Pi.

## Objetivo
Poder mezclar imágenes con videos en la lista.

## Diseño
- Aceptar `image/*` en `POST /media`; el tipo sale de la extensión/Content-Type.
- Cada ítem de la playlist puede llevar duración (`{"sha": ..., "seconds": 10}`); default para imágenes en el servidor.
- `tv-sync` genera el `.m3u` con `#EXTINF` / opciones por ítem; `mpv --image-display-duration=...` como default.
- Verificar que `mpv` con `--vo=gpu --gpu-context=drm` muestre bien imágenes en Pi 3 (rendimiento ya fue un problema con `vo=drm`).

## Criterio de hecho
Una lista video → imagen (10 s) → video se reproduce en loop sin cortes ni pantalla negra visible entre ítems.

## Riesgos
Transiciones entre ítems en `mpv`/DRM; redimensionado de imágenes grandes (puede requerir pre-escalar en el servidor).

## Hecho (como quedó)
Las imágenes (`jpg jpeg png gif webp bmp`) se suben igual que los videos y entran en la misma playlist. **Duración fija de 10 s** (`--image-display-duration=10` en `tv-video.service`): la duración por ítem no se hizo porque el `.m3u` de mpv no la soporta de forma simple y no se puede probar sin la Pi. Si hace falta, probar `edl://` con `length=`.

## Pendiente
Probar en la Pi: imágenes con `vo=gpu` (DRM), transiciones, imágenes grandes (¿pre-escalar en el servidor?).
