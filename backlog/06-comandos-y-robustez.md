# 06 · Comandos desde la UI y robustez

**Estado:** hecho en código y tests; falta probar en la Pi.

## Hecho
- `POST /command {"cmd": "on"|"off"|"console"}`: el servidor guarda `{id, cmd, at}` en `state.command`; `tv-sync` (ahora cada 15 s) lo ejecuta una sola vez (guarda el último `id`) y descarta órdenes de más de 5 min (Pi apagada). Botones Prender / Apagar / Video-Consola en la UI.
- `tv-sync` sale en silencio si no existe `/etc/tv-sync.conf`.
- Subida con disco lleno: limpia el `.tmp` y responde 507; un archivo registrado pero ausente en disco da 404 (antes 500).

- Estado en la UI: `tv-sync` hace `POST /status` en cada ciclo (`tv status` + si `tv-video` está activo); la API lo guarda en memoria y la UI lo consulta cada 5 s ("Tele: prendida · Pantalla: video · hace 8 s", o "La Pi no responde" si pasó más de 1 min).

## Pendiente
- El estado de la tele es el último reportado (≤ 15 s de atraso); `to-on` / `to-standby` se muestran como "sin datos".
- Latencia de hasta 15 s por el polleo. Para respuesta inmediata haría falta una conexión persistente (SSE/websocket) desde la Pi.
- Limpieza de `.tmp` huérfanos si el servidor muere en medio de una subida.
