# s317 — Perfil de retrieve_chunks CON el pool HTTP compartido (#72 fase 1) — v2

Mismo instrumento que el v1 (cProfile local, ruta harness, DB real, mismas 2
queries), corrido tras la migración de 55 sitios al cliente de proceso.

## Antes → después

| Medida | v1 (cliente-por-llamada) | v2 (pool, HTTP_POOL=on) | Δ |
|---|---|---|---|
| Llamada FRÍA (proceso nuevo) | 53,5 s | **12,4 s** | **−77%** |
| Llamada CALIENTE | 19,0 s | **4,5 s** | **−76%** |
| Construcciones de `httpx.Client` | 14 por consulta | **0** (1 por proceso) | — |
| Contextos SSL (`load_verify_locations`) | 7,25 s | 0 | — |
| Handshakes TCP/TLS | ~3,4 s | 0 (keep-alive) | — |
| Espera real de RPCs (`ssl.read`) | ~8,2 s | **4,4 s** | también baja: pipelining de conexión viva |

Las MISMAS 14 peticiones por consulta — solo cambió el transporte. Proyección
sobre la traza real (retrieve_ms 11-27 s en las 6 filas de producción):
~3-8 s esperados por turno de retrieval.

## Paridad de conducta (r14 — A/B INTERCALADO, 3 queries × 3 reps por modo)

La sonda 2×2 inicial (n=1) era humo-check, no evidencia — lo cazaron Sol y
Fable. La definitiva (recibo `evals/s317_http_pool_paridad_v1.json`) usa la
comparación CORRECTA: diffs por pares DENTRO de cada modo (off-off, on-on) vs
ENTRE modos (off-on) — si el cross cae dentro del rango within, el churn es
jitter base del canal, no efecto del pool.

| Query | max diff dentro-de-modo | max diff entre-modos | Veredicto |
|---|---|---|---|
| NC-PF2 especificaciones | 9 | 9 | JITTER-BASE |
| CAD-250 silenciar sirena | 5 | 5 | JITTER-BASE |
| AM-8100 detectores compatibles | 9 | 9 | JITTER-BASE |

El pool no añade efecto distinguible en NINGUNA query: el churn entre modos es
EXACTAMENTE del tamaño del churn dentro de cada modo (no-determinismo
server-side pre-existente, clase DEC-096). Latencia mediana intercalada
(n=9 por modo, pool con cliente fresco por rep = su peor caso):
**off 11,9 s → on 4,6 s**.

## Qué queda (fase siguiente, no esta)

El residual caliente (4,4 s) es espera secuencial de ~14 RPCs sobre una
conexión viva. La siguiente palanca es paralelizar canales independientes
(VECTOR / ENUNCIADOS / HYQ) — diseño aparte con su propio dúo. La política de
reintentos consciente-de-idempotencia (la otra mitad de #72) también queda
fuera de esta fase, a propósito.
