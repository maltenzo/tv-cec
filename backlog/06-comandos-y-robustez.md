# 06 · Comandos desde la UI y robustez

**Estado:** hecho en código y tests; falta probar en la Pi.

## Hecho
- `POST /command {"cmd": "on"|"off"|"console"}`: el servidor guarda `{id, cmd, at}` en `state.command`; `tv-sync` (ahora cada 15 s) lo ejecuta una sola vez (guarda el último `id`) y descarta órdenes de más de 5 min (Pi apagada). Botones Prender / Apagar / Video-Consola en la UI.
- `tv-sync` sale en silencio si no existe `/etc/tv-sync.conf`.
- Subida con disco lleno: limpia el `.tmp` y responde 507; un archivo registrado pero ausente en disco da 404 (antes 500).

## Pendiente
- La UI no muestra el estado de la tele (la Pi no le reporta nada): hoy es "enviar y confiar". Si hace falta: la Pi hace `POST /status` en cada ciclo y la UI lo muestra.
- Latencia de hasta 15 s por el polleo. Para respuesta inmediata haría falta una conexión persistente (SSE/websocket) desde la Pi.
- Limpieza de `.tmp` huérfanos si el servidor muere en medio de una subida.
