# Backlog: API en Railway para controlar la tele

## Idea general

Una API en Railway es la fuente de verdad (videos, imágenes, listas, horarios). La Pi **consulta** la API cada minuto y aplica lo que dice: no hay puertos abiertos ni NAT que atravesar. Es el mismo enfoque pull que ya usa `tv-deploy`.

- `server/` (Python stdlib, Docker, volumen en `/data`): guarda el estado y los archivos, auth con `Authorization: Bearer $API_TOKEN`.
- `tv-sync` en la Pi (timer cada minuto): compara con el estado remoto, baja lo que falta, verifica sha256, reemplaza de forma atómica y reinicia `tv-video` solo si algo cambió.
- Los archivos se identifican por sha256; `state.json` en el servidor describe qué se reproduce y cuándo.

Principio: cada fase es usable por sí sola y no rompe la anterior. Simplicidad primero (sin DB, sin framework, sin dependencias nuevas).

## Tareas

| # | Tarea | Estado |
|---|-------|--------|
| 01 | [Reemplazar el video](01-reemplazar-video.md) | hecho y desplegado en Railway; falta probar en la Pi |
| 02 | [Listas de videos](02-listas-de-videos.md) | hecho, falta probar en la Pi |
| 03 | [Imágenes](03-imagenes.md) | hecho, falta probar en la Pi |
| 04 | [Horarios de prendido/apagado](04-horarios.md) | hecho, falta probar en la Pi |
