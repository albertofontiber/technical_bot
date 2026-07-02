# s93 → FINE-GRAINED gate-0 · plan v2 (POST-DÚO: 16 hallazgos, 0 FP — v1 NO-SÓLIDA)

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
