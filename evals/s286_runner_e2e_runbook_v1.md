# s286 — Runbook e2e del runner Telegram (pre/post lote de ONs)

Por qué así: el bot es polling (`Procfile` → `scripts/run_bot.py`); dos pollers con el mismo
token = 409 de Telegram → NO se corre un runner local en paralelo a Railway. En fase demo
(Railway = demo, DEC-071e) la verificación e2e se hace SOBRE el bot de Railway tras el merge,
con los flags aún OFF (default = byte-idéntico) y luego al encender cada flag.

## Paso 0 — Post-merge, flags OFF (regresión cero)
1. Enviar al bot: una pregunta técnica cualquiera (p.ej. hp007-like). Esperado: respuesta
   normal, idéntica en forma a la release anterior.
2. Verificar en `query_logs`: fila nueva con `bot_version` = sha del merge.

## Paso 1 — Lote de ONs (click de Alberto en Railway, en este orden) + sonda por flag
| Flag → ON | Sonda (mensaje al bot) | Esperado observable | Rollback |
|---|---|---|---|
| `GENERATOR_FOLLOWUPS=off` | cualquier pregunta técnica | SIN cola «¿Quieres que…?» / «También puedo ayudarte con…» | quitar var |
| `GENERATOR_DIRECT_FIRST=on` | «¿qué resistencia final de línea lleva la ZX?» (hp009-like) | la PRIMERA línea contiene el dato (no preámbulo) | quitar var |
| `VISUAL_ASSETS_LISTING_GATE=on` | «¿qué productos Detnov tienes?» (la pregunta del bug que vio Alberto) | lista SIN imágenes/diagramas auto-adjuntos no pertinentes | quitar var |
| `ANTI_DIAGRAM_INVENTION=on` | «¿cómo conecto las sirenas en la central Morley?» (hp018-like) | no describe topología inventada; si la fuente no la sirve → lo dice | quitar var |
| `WIRING_TOPOLOGY_GUARD=on` | la misma sonda hp018 | si el texto afirmara topología sin soporte → aviso del guard (respuesta segura) | quitar var |

Cada flag es independiente y reversible por sí solo (default off/on documentado en
`src/rag/generator.py`). Si una sonda falla → rollback SOLO de ese flag + reportar.

## Paso 2 — Cierre
- `query_logs`: 1 fila por sonda, `response_time_ms` en rango normal (p50 histórico ±2×).
- Estampar resultado (flag → OK/rollback) en el paquete del arco; los ONs que sobreviven
  entran como config vigente en ARCHITECTURE.

## Paso 1b — Telemetría (tras el paste D9 + sus flags)
| Acción | Esperado | Verificación |
|---|---|---|
| `/start` (post-bump TERMS_VERSION v2) | pide re-aceptar; los términos listan la valoración 👍/👎 | texto de términos |
| `/accept` + pregunta técnica | respuesta CON botones 👍/👎 bajo el último fragmento | visual |
| tap 👍 | toast «¡Gracias por tu valoración!» | fila en `answer_feedback` (verdict=up) |
| tap 👎 en la MISMA respuesta | toast; el veredicto CAMBIA (last-wins, no fila nueva) | misma fila, verdict=down |
| `python -m scripts.bot_health_report` | digest con latencia/no-info/segmentación interna | salida CLI |
| quitar `TELEGRAM_FEEDBACK` y tapear un keyboard viejo | el tap RESUELVE (handler incondicional) | sin spinner colgado |

## Alternativa local (solo si algún día hace falta sin tocar Railway)
Crear un bot de pruebas con @BotFather → `TELEGRAM_BOT_TOKEN` de test en `.env` local +
`python scripts/run_bot.py` → mismas sondas. No requerido en fase demo.
