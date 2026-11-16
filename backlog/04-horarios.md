# 04 · Horarios de prendido y apagado

**Depende de:** 01 (independiente de 02/03; se puede hacer antes).

**Estado:** hecho en código y tests; falta probar en la Pi.

## Objetivo
Definir desde la API a qué hora se prende y se apaga la tele.

## Diseño
- `state.json`: `{"schedule": {"on": "08:00", "off": "22:00", "days": [1,2,3,4,5,6,7], "tz": "America/Argentina/Buenos_Aires"}}`.
- `tv-sync` (o un `tv-schedule` aparte si crece) lee el schedule; cada minuto decide el estado deseado según hora local y llama `tv on` / `tv off` solo si difiere del actual.
- Evaluar por "estado deseado ahora" y no por "evento a las HH:MM", así un reboot o corte de red no deja la tele en estado equivocado.
- Endpoints: `GET/PUT /schedule` (o dentro de `/state`).
- Override manual (`tv on/off` desde la web) que dure hasta el próximo cambio de horario.
- Quitar el cron de ejemplo del README.

## Criterio de hecho
Con horario 08-22, la tele se apaga a las 22:00 y prende a las 08:00 sin intervención, y si la Pi arranca a las 15:00 queda prendida.

## A decidir
Horarios distintos por día; zona horaria en la Pi vs. en el servidor (lo más simple: la Pi usa su hora local y el servidor solo guarda strings).

## Hecho (como quedó)
`schedule: {"on","off"}` en `/state` (validado, `on != off`, puede cruzar medianoche). `tv-sync` lo guarda en caché local y lo evalúa cada minuto aunque no haya red; actúa solo cuando el estado deseado cambia (o en el primer arranque), así un `tv on/off` manual dura hasta el próximo cambio; si `tv` falla reintenta al minuto. Usa la hora local de la Pi.

## Pendiente
- Probar en la Pi con CEC real.
- Días de la semana (no hecho; agregar `days` si hace falta).
