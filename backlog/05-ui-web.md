# 05 · UI web

**Estado:** hecho; probado con jsdom contra el servidor real, falta mirarlo en un navegador (la extensión de Chrome no estaba conectada).

## Objetivo
Manejar todo (subir, playlist, horario) desde una página, sin curl.

## Hecho
- `server/index.html`: una sola página, JS plano, sin dependencias ni build. `GET /` la sirve sin token (no lleva datos); el token se pide con `prompt` y queda en `localStorage`.
- Biblioteca (subir varios archivos con progreso, borrar), playlist (agregar, ↑ ↓, quitar; se guarda en cada cambio) y horario.
- Nombres de archivo siempre como texto (probado con un nombre con HTML).

## Pendiente
- Mirarla en el celular (es mobile-first en CSS, pero no se vio).
- Miniaturas/previsualización (requiere pedir cada archivo con el token).
- Si el token en `localStorage` molesta: pasar a sesión con login. Hoy, quien abra la página sin token no ve nada.
