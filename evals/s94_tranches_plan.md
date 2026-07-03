# s94b · Plan de PASE CORPUS POR TRAMOS (v2 POST-DÚO)

> **v1→v2:** dúo completo (cross-model 7 hallazgos [3 CRÍTICOS] + sub-agente F1-F8 [3
> CRÍTICOS], convergentes en la idea-fuerza: **los TRAMOS son correctos; lo NO-sólido era
> heredar la infra del PILOTO como permanente**). Claims verificados regla-C:
> `index_chunks` borra por `extraction_sha256` (idempotencia real — marca-de-tramo ahí =
> huérfanos al re-procesar un manual) · default sidecar INEXISTENTE (flag-on sin env =
> swap inerte silencioso) · insertar en `chunks_v2` toca la demo VIVA de inmediato.
> Fork sidecar-vs-schema resuelto: **columna `parent_id`** (la semántica de
> extraction_sha256 no se mezcla — cross-model).

## El hallazgo que manda (sub-agente F1, CRÍTICO)
El plan v1 creaba una ventana en la que la DEMO sirve texto derivado citado como manual:
`chunks_v2` es la tabla viva; con el flag off los surrogates entran a pools como chunks
normales (violando inv.6 del spec). En el piloto era seguro solo por el rollback-en-finally.
**Fix estructural (v2): INVARIANTE DE NO-SERVICIO** — una fila con `parent_id IS NOT NULL`
JAMÁS se sirve cruda: excluida de todos los canales salvo que el swap esté on (y entonces
se sirve el PADRE). Fail-safe por construcción (config rota = excluir); elimina la ventana
y desacopla el orden inserción↔bvg.

## T0 — BUILD ESTRUCTURAL (pre-gasto, $0 API, ~1 sesión, dúo sobre el build + tests + PR)
1. **Schema (DDL visible + rollback pre-escrito):** `parent_id UUID NULL REFERENCES
   chunks_v2(id)` + `ingest_batch TEXT NULL` (vintage/tramo: `enunciados-v1:T1:p1`) +
   índice; el RPC `match_chunks_v2` devuelve `parent_id` y **excluye `parent_id IS NOT
   NULL`** salvo modo-swap; mismo filtro en los paths PostgREST (keyword/content).
   `extraction_sha256` conserva su semántica de identidad-de-extracción intacta.
2. **Invariante de no-servicio + swap permanente:** flag renombrado
   `ENUNCIADOS_MULTIVECTOR=off|on` (adiós naming PILOT_*); linkage leído de LA FILA (sin
   sidecar); off = surrogates excluidos; on = swap 1:1 al padre (semántica del piloto,
   5 tests existentes migran + nuevos de exclusión).
3. **QA GENERALIZADO por-enunciado** (F4: el v2 del piloto está keyed a hechos conocidos):
   valores extraídos del PROPIO enunciado + co-ocurrencia a nivel de FILA (no página) +
   **métrica de COBERTURA por marca** (tablas-con-statements / tablas presentes — el
   QA-rate solo mide fidelidad de lo generado, no lo que falta).
4. **Panel de desplazamiento (F6/C):** pools pineados pre/post-tramo — 51 golds + testbed
   + ~20 queries reales de `query_gaps` — overlap/rank-shift top-50 (patrón gate-0). El
   guard famtie ±2 solo ve el universo de los golds; esto ve el resto.
5. **Script del pase IDEMPOTENTE (F8):** id determinista por ancla (uuid5), delete-by-batch
   antes de re-insertar un tramo, marca en `ingest_batch`.
6. **Muestreo de fidelidad ESTRATIFICADO (F5):** marca × bucket-isPerfectTable,
   sobre-muestreo de tablas imperfectas (~10-15 por estrato de riesgo; uniforme-30 tiene
   P(miss)≈21% con tasa 5%).

## Tramos (post-T0)
- **T1 (~$25-45):** docs-piloto re-generados con prompt congelado (**GATE DURO de
  REPRODUCCIÓN — F3: famtie ≤8 con swap ON, ≥4 de los 6 flips de DEC-086 reproducen;
  antes era "bonus", error**) + marcas-de-golds + 2-3 marcas NO-vistas con isPerfectTable
  bajo (estrés de layout, cross-MENOR/sub-A). Gates para T2: reproducción ✓ · famtie sin
  nueva-miss ±2 · panel-overlap sin shift anómalo · QA-rate por marca ≥97% (calibrado:
  el piloto dio ~99%; 90% habría sido 25× la tasa real = laxo) + cobertura ≥ pre-registrada
  · muestreo estratificado sin mispairing sistemático.
- **T2-T3 (resto por lotes de marca, ~$60-110 c/u):** mismos gates. **Vintage en el
  batch-mark (F7):** la RECETA DE EMBEDDING congelada es INNEGOCIABLE (geometría del
  índice); el prompt puede versionar POR MARCA si el gate lo exige, marcado
  (`enunciados-v1:T2:p2`) → mezcla visible + rollback por-vintage, sin re-pagar tramos.
- **Demo:** bvg PASS-control ±2 (gate Alberto, coste juez) → `ENUNCIADOS_MULTIVECTOR=on`.
  Con el invariante de T0, el ORDEN inserción/bvg deja de ser crítico (crudos jamás
  servidos) — pero el flag no se enciende sin el bvg.

## Honestidad del instrumento (sin cambio de v1 + F8)
La famtie solo mide flips en los 12 misses (~docs del piloto); T2+ se valida con
no-regresión + panel + QA/cobertura + muestreo — no hay métrica de flips nueva sin más
golds. El guard no es "$0" absoluto: pin-regen = embeddings de query ×39 (céntimos).
Coste total por tramos ≈ igual que de golpe; lo que se compra es detección temprana.

## Registro del dúo (v1 NO-SÓLIDA → v2)
Cross-model: 7/7 confirmados (3 CRÍTICOS: sidecar-como-permanente, sin contrato schema,
colisión semántica extraction_sha256). Sub-agente: 8/8 confirmados (F1 ventana-demo =
el hallazgo top de la ronda; F2 fail-open verificado; F3 reproducción-como-bonus;
F4 QA no generalizado). 0 FP en ambos. Tally: `evals/adversarial_review_log.jsonl`.
