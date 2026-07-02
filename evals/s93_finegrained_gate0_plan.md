# s93 → FINE-GRAINED gate-0 · plan v2 (POST-DÚO: 16 hallazgos, 0 FP — v1 NO-SÓLIDA)
# → v3 ENMIENDA BAKE-OFF (§B/§C al final): pushback de Alberto aceptado — no solo FTS
# → EJECUTADO 2/3-jul: resultados y decisión en `evals/s93_bakeoff_resultados.md`
#   (A: NO-GO 1/11 · B: 1/10 · C: 2/4 ✅ · HyDE: 0-1/10 · paso-0: hp012'99+99'→diversify)

> **Lo que el dúo cambió de v1:** (1) la infra FTS **YA EXISTE** — `search_vector` tsvector
> ponderado (A=section_path/B=content/C=context, config `spanish_unaccent` por el bug de
> acentos de la migración 002), GIN, trigger, RPC `search_chunks_text_v2`, **25.090/25.090
> poblados (verificado en DB viva)** — y el retriever YA la consume parcialmente
> (`retriever.py:570-596`, Path B: solo queries sin modelo). Mi v1 proponía "construir el
> índice" = la clase DOS-COPIAS; las h4-6 pasan de *construir* a **RE-RUTEAR**. (2) El gate-0
> de v1 medía una config que NO es la de producción (`to_tsvector('spanish')` fresco). (3) Mi
> "fusión RRF pre-cap" NO describe el pipeline (hoy = merge `stamps`, cero RRF en src/) y
> confundía dos levers en un A/B. (4) "12 = fine-grained" era sobre-generalización (s86
> descompone distinto) → HIPÓTESIS post-S3. (5) tsvector ≠ BM25 (sin IDF) → el NO-GO honesto
> es "FTS-Postgres no basta", NUNCA "exige re-ingesta" (pg_search/trigram siguen query-side).

## La pregunta REAL del gate-0 (redefinida por el hallazgo H1)
**¿Por qué el canal FTS EXISTENTE no trae los 12 soportes al pool?** — hoy solo se activa para
queries sin modelo (Path B); las 12 queries-miss llevan modelo → el canal ni corre. Gate-0 =
simular su activación para estas queries y medir si los soportes entrarían.

## Gate-0 (h1-2, $0, SQL read-only sobre la config CANÓNICA)
- Input = **SOLO la pregunta del gold** (lo que producción ve) — guard anti-circularidad
  (cross-model): check explícito de que la pregunta NO contiene el token-soporte; si lo
  contiene → fila excluida y declarada.
- Sustrato = **`search_vector` real** vía el RPC/`@@` con `websearch_to_tsquery` sobre la
  config de producción — nunca un tsvector fresco.
- **Matriz de instrumento PRE-REGISTRADA antes de contar (H5):** {AND, OR} × {con/sin
  token-modelo en la tsquery} — la variable decisiva: los soportes son celdas donde el modelo
  vive en metadata, no en content; con AND un término ausente = ni matchea. GO/NO-GO se decide
  EN LA CELDA que el build usaría.
- **Evento pre-registrado (H4):** soporte ∈ **top-20** FTS (el K real del canal) **Y**
  sobrevive la fusión-`stamps` SIMULADA contra el ranking vectorial del pin (no "top-50 FTS
  puro", que contaría lo que el canal nunca traería).
- **Umbral honesto (H4):** <3/12 en la mejor celda = NO-GO (sin el teatro del "≥6"); ≥3 = GO.
- **Control de RUIDO (H9):** las mismas celdas sobre 6 golds SIN miss — solape con el pool
  actual (canal redundante) vs chunks nuevos (riesgo-desplazamiento a medir, no a asumir).
- Probes s86: el set corrible NO existe (H8, verificado) → se deriva un mini-set (≤6 probes
  bornes/LED de los briefs s86) o se declara n=12; NADA condicional.

## Si GO: re-ruteo del canal existente (h4-6, tras flag `FTS_ALL_QUERIES=off|on` default off)
- MINIMAL-DIFF (H3): extender el Path B existente a queries CON modelo, entrando por el merge
  `stamps` con score estampado (como MODEL 0.65 / CONTENT 0.70-0.85 hoy) — **aísla el lever**
  (canal-para-más-queries, fusión INTACTA). RRF = otro lever, otro día, terreno DEC-050
  declarado (re-medible post-NOCAT per digest, pero NO en este A/B).
- Sin DDL (existe todo). Si una celda ganadora exigiera índice extra: visible en sesión +
  rollback pre-escrito (H7) — jamás "OK implícito".
- Tests + dúo build + PR, como F2-S1/S3.

## Medición (h7): famtie + freeze COMPLETO estampado
Predicciones pre-registradas por-hecho → pin-regen (RESOLVE=on+add + FTS_ALL_QUERIES=on) →
famtie vs OFF-control **con freeze estampado: corpus+índice+embeddings+config+catálogo-commit
+celda-de-instrumento** (cross-model #7). **Criterio de regresión explícito (H9): nueva-miss
fuera del jitter documentado ±2 → NO-SHIP.** Métrica: retrieval-miss famtie (baseline 12), NO
PASS. Ship-gate eventual: famtie + bvg PASS-control ±2 (DEC-082).

## Costes y scope (sin cambio)
~$0 (SQL + replay local) · re-ingesta NO se lanza (si NO-GO: presupuesto en papel de pg_search
[BM25 real, extensión] vs trigram vs re-ingesta, para decisión de Alberto) · conduct-level
fuera (siguiente bloque CON Alberto) · PASS no se toca.

## Registro de honestidad
v1 cazada por el dúo ANTES de ejecutar (16 hallazgos, 0 FP): habría construido un canal
duplicado, medido sobre config equivocada, con criterio pseudo-calibrado y A/B confundido.
Tally en `evals/adversarial_review_log.jsonl` (2 entradas s93-plan).

---

# v3 · ENMIENDA BAKE-OFF (pushback de Alberto, aceptado): no solo FTS

**El porqué:** el plan v2 centraba las 8h en FTS — el mecanismo MÁS DÉBIL de los 4 de s86
para esta clase (si el soporte vive en tablas/celdas de chunks grandes, FTS es otro ranker
sobre la misma representación rota). Un NO-GO de FTS entregaba solo "papel de opciones".
Las mismas 8h pueden comprar **evidencia MEDIDA por mecanismo** sin lanzar re-ingesta.
El gate-0 FTS (arriba) pasa a ser el **track A** de un bake-off de 3 tracks sobre el
MISMO testbed. ColBERT queda FUERA declarado (infra pesada, último de la lista s86; solo
si A-C fallan todos).

## Testbed común (fijado ANTES de correr nada)
Los 12 miss-facts del pin `s92_retrieval_miss_ON_add.yaml` (famtie re-derivada 2-jul,
baseline 12/132), con sus chunk-ids soporte YA JUZGADOS (votes≥4, labels GPT pagados):
cat013 'CLIP' · cat016 'autobusqueda' · hp001 '2222' · hp006 ×3 ('Fallo de Tierra',
'Tierra', 'ISO-X') · hp011 '05 a 295 seg' · hp012 ×2 ('99 + 99', '2 lazos / 396') ·
hp013 'PWR-R' · hp014 '35' · hp018 '1 A'.
**Dato estructural del testbed:** en 10/12 el sup_fams == gold_family — el chunk-soporte
existe, es de la familia correcta, y NO entra al pool-50. La firma fine-grained exacta.

## PASO 0 (nuevo, sub-agente F4, $0): trace por-etapa ANTES de atribuir a fine-grained
El miss famtie = "no está en el pool FINAL" — el chunk-soporte pudo entrar por un canal y
morir en `_filter_to_query_models`/diversify/truncado. El instrumento YA existe:
`_trace` (`retriever.py:1221-25`, construido s85 para esto). Correr las queries-miss con
trace (config del pin: RESOLVE=on+add) y localizar DÓNDE muere cada soporte:
- muere post-canal (filtro/diversify/truncado) → NO es clase fine-grained → SALE del
  testbed B/C (mal atribuido; su fix es otro lever) — se reporta aparte;
- nunca entra a ningún canal → clase fine-grained confirmada → sigue en B/C.
Declarado: el trace re-recupera (jitter ±1-2 documentado) — localiza, no mide el evento.

## Track B (h3-4, ~$0.05): probe de MULTI-GRANULARIDAD (extracción determinista)
Prueba el mecanismo de multi-granularidad SIN re-ingesta: ¿un chunk más pequeño que
contenga el hecho rankearía donde el padre no rankea? **v3.2 — dúo completo: cross-model
(2 CRÍTICOS confirmados contra código) + sub-agente (F1 CRÍTICO + F2/F4 + F5-F7):**
- **Extracción DETERMINISTA (cross-model MEDIO-4 + sub-agente F6, cero elección humana):**
  localizar el `valor` juzgado en el `content` del chunk-soporte (votes≥4 ya establecieron
  presencia) → span = línea(s) contenedora(s) VERBATIM + línea de cabecera de tabla
  inmediatamente superior si existe. Sin parafraseo. Hechos SIN match literal del valor
  (soporte parafraseado) → flag declarado por-hecho, no se inventa span. Fuente = chunk
  del corpus, JAMÁS el gold (guard anti-circularidad).
- **Receta de embedding FIEL al corpus (cross-model CRÍTICO-2 + F5, `src/reingest/embed.py:52-59`):**
  el corpus embebe `context + "\n\n" + content` → el sub-chunk se embebe como
  `context-ALMACENADO-del-padre + "\n\n" + span` (columna `context` del chunk, no
  cabecera manual).
- **Espacio de medición SIN re-retrieval (sub-agente F1 CRÍTICO — el pin no guarda scores;
  re-correr vector_search re-introduce el jitter del falso-flip hp001):** UNA llamada
  `embed_query(pregunta-cruda)` por gold (HyDE=OFF verificado: default `hyde.py:44`, ni en
  .env — config del pin Y de prod; corrige el claim HyDE del cross-model, que era
  condicional) compartida entre ambos lados; cosenos computados LOCALMENTE
  (`_fetch_embeddings_by_id` + `_cos`, embeddings ALMACENADOS del pool pineado) — nada se
  re-recupera. **Tie-band ±0.003** (drift documentado DEC-042d): dentro de banda = TIE
  declarado, no win.
- **Evento pre-registrado (rebajado, cross-model CRÍTICO-1 + F1):** cosine(sub-chunk) ≥
  min-coseno LOCAL de los miembros del pool PINEADO (la frontera honesta disponible;
  pool_pin es post-merge/filtros — declarado). Se reporta además cosine vs threshold 0.3
  y el caso 2-modelos (hp012/cat013: effective_top_k=100, frontera distinta — declarado
  por-query). NO simula fusión-stamps/filtros/diversify → resultado = **"señal"**.
- **Lecturas pre-registradas (sub-agente F2 — asimetría corregida):** NO-rankea → mecanismo
  granularidad DESCARTADO para ese hecho (lectura fuerte válida: es la cota optimista);
  rankea → NO-descartado, pendiente la MISMA simulación-stamps del track A antes de
  cualquier "financia" — B solo NUNCA financia. Terceras salidas declaradas (F4): (i)
  celda info-pobre ('2222','35','1 A' — vocabulario coincide pero contenido casi vacío →
  el remedio es ENUNCIACIÓN, mecanismo C); (ii) artefacto del instrumento (espacio).
  Y el wording BM25 corregido (F4-settled, DECISIONS:187 "si falta el literal, BM25
  tampoco"): no-rankea NO implica "pesa BM25" — implica query-expansion/enunciación.
- **Predicción pre-registrada (antes de correr):** ganan 5-8/11 (los de tabla-celda:
  hp018 '1 A', hp012 ×2, hp013, hp014); dudosos los de vocabulario operativo
  (cat016 'autobusqueda', hp006 ×2). [n=11: el guard excluyó hp006 'Tierra' — el hecho
  viene en la pregunta.]

## Track C (h5-6, ~$2-5): micro-slice de EXTRACCIÓN-TABLAS (pipeline automatizable)
**SIN gate B→C (MEDIO-3 aceptado: la extracción estructurada añade contexto que el span
mínimo de B no tiene — el gate mataría justo esa evidencia).** C corre sobre su set
pre-registrado fijo, independiente del resultado de B.
- 2-3 docs peores del testbed (candidatos: MIE-MI-530 [hp018 '1 A'], HLSI-MN-103 [hp011],
  el doc-soporte de hp012/hp014) — extracción LLM de las tablas específicas a sub-chunks
  estructurados (fila + cabeceras como enunciado), embebidos con la MISMA receta fiel de
  B (context-del-padre + extract; mismo espacio HyDE), MISMO evento que B.
- Lo que mide DISTINTO de B: B = span verbatim mínimo; C = ¿la extracción AUTOMATIZABLE
  (enunciado estructurado) produce sub-chunks que rankean? (el pipeline real de ingesta).
- **Etiqueta de honestidad (MEDIO-6):** C es muestra diagnóstica sobre 2-3 docs, NO
  comparable 1:1 con A/B sobre los 12 — la tabla h7 lo etiqueta así.
- Coste declarado: ~$2-5 LLM (clase s83 en micro; disciplina feedback_cost_discipline:
  subset primero, esto ES el subset).
- **Pre-registro C (escrito TRAS medir A y B, ANTES de correr C):** set fijo = los 2
  FLAG de B (hp018 '1 A' [MIE-MI-530rv001], hp012 '2 lazos / 396' [MPDT280/MFDT280]) +
  hp014 '35' [MIDT180] + hp011 '05 a 295 seg' [HLSI-MN-103]. Extracción LLM
  (claude-sonnet-4-6, el del sistema) del chunk-soporte a enunciados fila-por-fila con
  contexto de producto/sección; embed receta-fiel; evento = MISMO del B v2
  (cos ≥ sim#50 del canal real ± tie). Predicción: ganan ≥2/4 (la enunciación añade el
  +0.05-0.10 que a los spans de B les faltó); si 0/4 → la clase exige query-side.
- **Mini-brazo HyDE (addendum pre-registrado tras el diagnóstico de B — vocab-gap
  query↔celda):** HyDE existe para ESTO (TECH_DEBT #25, default off desde s46, nunca
  medido en chunks_v2@50). Probe: `generate_hypothetical_document(pregunta)` →
  `embed_query(hipótesis)` → recomputar en ESE espacio la frontera del canal (RPC) +
  cos(padre) y cos(sub-chunk B). Evento: padre-o-sub ≥ sim#50 de su propio espacio.
  Predicción: mejora el rank del soporte en ≥3/10 (la hipótesis se escribe en registro
  de manual). 1 muestra HyDE por gold (jitter declarado — probe, no medición de ship).

## h7 revisada: el artefacto de decisión
Tabla comparativa **mecanismo × hechos-ganados × coste-de-escalar**: track A (léxico
query-side, coste≈0 cablear), track B (multi-granularidad, re-ingesta ~$150-300), track C
(extracción-tablas, re-ingesta + pipeline). Recomendación fundada para Alberto — con la
NATURALEZA de cada cifra declarada en la tabla: A = medición sobre el canal real
(instrumento del gate-0); B = señal de mecanismo (probe optimista, sin fusión/filtros);
C = muestra diagnóstica 2-3 docs (no comparable 1:1). Mejor que "FTS sí/no" + papel,
pero B/C priorizan la inversión, no la zanjan solos.
**Freeze del artefacto (sub-agente F7):** estampa `EMBED_MODEL=voyage-4-large` +
input_type (document/query) + `HYDE_ENABLED=false` + catálogo-commit + pin usado.
**Testbed n=11** (guard anti-circularidad excluyó hp006 'Tierra'): el umbral del track A
queda ABSOLUTO (<3 en la mejor celda = NO-GO), declarado sobre n=11.
- Si A gana claro (GO ≥3/12 en su mejor celda) → build re-ruteo h8 tras `FTS_ALL_QUERIES`
  default-off (como v2). B/C NUNCA se cablean en esta sesión: son probes DIAGNÓSTICOS;
  su salida es el presupuesto-con-evidencia (decisión de Alberto, re-ingesta gateada).
- Guard-rails sin cambio: $0 en DB (todo ad hoc/local), re-ingesta NO se lanza, PASS no
  se toca, conduct-level fuera.

**Estado dúo:** track A validado (PR #110); tracks B/C = enmienda NUEVA → dúo (sub-agente
fresco + cross-model GPT-5.5) ANTES de ejecutarlos; track A arranca en paralelo (no
depende de la enmienda).
