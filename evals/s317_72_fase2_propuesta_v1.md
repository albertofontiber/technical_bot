# s317 — #72 FASE 2: paralelizar el camino con-modelo + reintentos opt-in idempotentes (propuesta v1, pre-dúo r15)

## Estado tras el dúo r15 y los gates (cierre)

**Dúo r15 (Sol 6 · Fable 5, 1 convergente, 0 FP) — TODO APLICADO:**
- Sol M1: kill-switches PROPIOS `RETRIEVAL_PARALLEL` / `HTTP_RETRIES` (el del
  pool no cubre estos mecanismos); registrados en flags + release-config.
- Sol M2 ≡ Fable F1: mi «el patrón 3c ya lo valida» era HUECO — 3c tiene
  fan-out máximo 1 en prod (`break` tras un PCI term). Reescrito como conducta
  de carga NUEVA con flag y gate propios. (5ª ronda consecutiva de framing.)
- Sol M3 (regla C ejecutada): s104 YA reintenta con backoff+bisección+poison —
  el opt-in de scripts habría ANIDADO reintentos sobre POST sin upsert →
  scripts FUERA del v1; la política v1 es solo-lectura del serving.
- Sol M4: el retry apunta a TRANSITORIOS (N=1, 0,2 s); la clase caída-larga de
  s316c queda donde estaba: bisección/reanudación. Sin anidamiento (los 4
  canales s306 y los scripts conservan su política medida).
- Sol M5: canales `CONTENT`/`DIVERSIFY` añadidos a la allowlist de la traza +
  `_record_channel_failure` en sus excepts (sus fail-open eran invisibles).
- Fable F2: `PoolTimeout` EXCLUIDO del set reintentable (backpressure local ≠
  transitorio de red; reintentarlo amplifica bajo saturación), con test.
- Fable F3: `diagram_search` entra en la lista de tareas (misma ola).
- Fable F4 CONFIRMADO por medición: bajo 6 ILIKE concurrentes cada scan sube
  ~790 ms → ~2,2 s (contención server-side); la ola completa 2,3 s vs 4,8
  secuencial. La proyección optimista se retira; valen las cifras medidas.
- Fable F5: framing «POST /rpc/*» corregido (la mayoría son GET; la
  idempotencia se declara por sitio igualmente).

**Gates (recibos `s317_fase2_paridad_v1.json` + `s317_rpc_timeline_v2_paralelo.json`):**
- **G1 composición: PASS** — 2 de 3 queries con PARIDAD EXACTA (ids y orden
  idénticos en off/on/off²/on²); la 3ª dentro del jitter base off-off (canal
  vectorial, clase DEC-096).
- **G2 latencia: mediana 4,2 → 2,6 s (n=6/modo)** · query pesada 8,9 → 5,2 s ·
  bloque content 7,0 → 2,3 s · diversify 1,0 → ~0,3 s.
- Suite completa + tests dedicados (14: orden determinista bajo finalización
  invertida, kill-switches, PoolTimeout excluido, agotamiento propaga,
  canales nuevos en la traza).

## El hecho (línea de tiempo por RPC, `evals/s317_rpc_timeline_v1.json`)

Instrumentando el choke-point del pool (fase 1) sobre un turno caliente real
(NC-PF2, 36 chunks): **32 RPCs, 8,7 s de red pura, 0,3 s de CPU** — todo
secuencial. Desglose:

| Bloque | RPCs | Tiempo | Qué es |
|---|---|---|---|
| `content_search` con-modelo (3a intent + 3b keywords) | 8×(~790+~90) ms | **7,0 s** | ILIKE por (keyword, modelo) + authority-rank, EN SERIE |
| `_diversify_by_source_file` | ~10×90 ms | **1,0 s** | fetch por source_file, EN SERIE |
| vector + keyword + status | 4 | ~0,5 s | ya rápidos |

## La asimetría que lo hace de bajo riesgo

**El camino SIN modelo (3c) ya corre en paralelo** — `ThreadPoolExecutor(max_workers=6)`
con el comentario «All content_search calls run in PARALLEL to avoid sequential
latency» — desde antes del s85. El camino CON modelo (el de los técnicos: 3a
spec/trouble-intent y 3b keywords/sinónimos/full-query) hace LAS MISMAS llamadas
independientes y quedó secuencial. La fase 2a es **extender el patrón existente
del propio fichero a los dos bloques que lo perdieron**, no introducir uno nuevo.

## Diseño 2a — paralelización conducta-neutral

1. **3a+3b**: recolectar las tareas `(term, limit, boost, model, canal)` en una
   lista (el orden actual de los bucles) → `ThreadPoolExecutor(max_workers=6)` →
   **extender `keyword_results` en ORDEN DE LISTA** (no de finalización). Mismas
   consultas, mismos límites, mismos scores, mismo orden de extensión ⇒ el pool
   resultante es EL MISMO, byte a byte, por construcción.
2. **`_diversify_by_source_file`**: los `_fetch_top_chunks_by_source_file` por
   fichero → mismo patrón, orden de extensión = orden de la lista de sources.
3. El cliente compartido es thread-safe (httpx.Client); `max_connections=40`
   del pool absorbe 6 workers sin encolar.

Proyección: content 7,0 s → ~1,6 s (2 tandas de ~800 ms) · diversify 1,0 s →
~0,2 s · turno retrieval ~8,9 s → **~2,5-3 s**.

## Diseño 2b — reintentos OPT-IN (la deuda original de #72)

- `abierto(timeout=X, reintentos=N)` — N>0 SOLO donde el sitio se declara
  idempotente. El shim reintenta ÚNICAMENTE sobre `httpx.TransportError`
  (ConnectError/ReadError/timeouts — la red, no el servidor); JAMÁS sobre
  respuestas HTTP (un 500 de PostgREST no se reintenta aquí; esa política es
  del sitio). Backoff corto fijo (0,2 s), sin jitter (determinismo de test).
- **La idempotencia se declara, no se infiere del verbo**: los canales de
  retrieval son POST /rpc/* de SOLO LECTURA (idempotentes) y los POST de
  escritura (query_logs) NO lo son aunque compartan verbo. Default
  `reintentos=0` = la conducta de hoy, byte-idéntica.
- Sitios que optan en v1: los GET/RPC de solo-lectura del retrieval (vector,
  keyword, content, diversify, hyq, enunciados) + los 3 scripts del origen de
  #72 (s316c). `log_query` y todo POST de escritura quedan a 0 reintentos
  (el retry de compatibilidad de columnas EXISTENTE de logging_db no se toca).
- CAMBIO DE CONDUCTA DECLARADO: bajo fallo transitorio de red, un canal que hoy
  degrada (fail-open, DEC-089/#63) ahora puede completar. Es la conducta que la
  deuda #72 pide desde s316c. Bajo éxito: byte-idéntico. La traza `retrieval`
  (s306) sigue registrando los fallos que persisten tras el reintento.

## Gates pre-registrados (antes de PR)

1. **Paridad de composición**: misma query, secuencial vs paralelo, ids Y ORDEN
   del pool final idénticos (no jitter-tolerante: la paralelización 2a debe ser
   EXACTA porque las consultas no cambian; el jitter server-side se controla
   comparando también secuencial-vs-secuencial).
2. Latencia: timeline v2 con el mismo instrumento (diana: content ≤2 s).
3. Suite completa verde + trinquetes (el barrido httpx.Client( no se toca).
4. Tests nuevos: orden determinista bajo finalización desordenada (fake con
   delays invertidos); reintento solo-TransportError; 0-reintentos en escritura;
   agotamiento → la excepción original propaga (fail-open del sitio intacto).

## Alternativas descartadas

- **Batchear los 8 ILIKE en un OR** (1 scan server-side): cambia la semántica
  de limit por-keyword → composición del pool distinta → exigiría gate de eval
  completo (bvg/factlevel), no paridad. Queda declarado como fase 3 OPCIONAL si
  el ~1,6 s residual importara; hoy el retorno (5,4 s) no lo necesita.
- **pg_trgm sobre content** (ILIKE ~790→~50 ms): migración DDL que Alberto
  aplica a mano + análisis de plan de query; ortogonal y complementaria — se
  anota, no se cablea.
- **Async-izar el retriever**: reescritura estructural; el ThreadPool ya está
  en el fichero y paga lo mismo aquí.

## Gaps declarados

- El paralelismo sube la presión instantánea sobre PostgREST (6 conexiones
  activas vs 1): el plan free de Supabase lo tolera (3c lo hace desde s59 sin
  incidentes), pero un turno concurrente de otro usuario suma — PoolTimeout
  del pool declarado en DEC-206 sigue siendo el techo, kill-switch idem.
- El orden de las tareas 3a/3b reproduce el orden de los bucles de HOY; si un
  refactor futuro reordena los bucles, la paridad se re-mide (gate 1 es
  reproducible).
- 2b no unifica el retry de compatibilidad de logging_db (existente, probado,
  otra clase: columna-desconocida ≠ transporte) — deliberado.
