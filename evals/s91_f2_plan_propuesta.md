# s91 → F2: plan v2 (POST-DÚO — v1 corregida con 15 hallazgos verificados, 0 FP)

> Artefacto de revisión del dúo (Protocolo 3). Autor: Claude. **v1 → v2: el dúo completo
> (sub-agente Fable fresco + cross-model GPT-5.5 con tools) tumbó el mecanismo central de v1**
> — "expansión aditiva del pool" re-litigaba DEC-069 (aditivo = NO-OP-con-regresión MEDIDO,
> hasta el comentario de `retriever.py:1443` lo dice: "NO aditivo (DEC-069 fue NO-OP)") sin
> citarlo. Todos los hallazgos verificados contra código/DB antes de aceptar (regla C).
> Contrato canónico: `docs/IDENTITY_CATALOG_CONTRACT.md`. Tally: `evals/adversarial_review_log.jsonl`.

## Objetivo de F2 (sin cambio)
Consumir el catálogo gobernado en query-side. Métrica pre-registrada (contrato F2, línea 167):
**hp018 4/4 SIN regresar hp009, medida con el instrumento famtie (`retrieval_miss_famtie.py`)
bajo freeze-contract COMPLETO (corpus+índice+embeddings+juez+seeds+config+catálogo-commit)** +
retrieval-miss=14 no empeora + tests verdes. bvg/PASS solo como control ±2 (PASS plateau settled
DEC-075 — no es la métrica). hp011→Supra vía `prefer` (test-case homónimo).

## El mecanismo v2 (la corrección central del dúo)
NADA de vía aditiva nueva al pool (DEC-069). El resolver del catálogo alimenta los DOS seams
que YA existen y están medidos:

1. **Lista `models`** — generalizar el seam LEVER2 (`retriever.py:125-128`, hoy series-YAML
   per-familia flag OFF) a resolución data-driven desde `catalog_store.resolve()`: el token
   paraguas/alias de la query se resuelve a las variantes reales ANTES de keyword+filter+content.
   Es el mecanismo que YA dio hp018 4/4 (DEC-074b); lo que lo mató fue la fuente (YAML per-familia
   no escala + regresó hp009), no el seam. Política de expansión del paraguas: AÑADIR variantes
   sin retirar el token original (hipótesis anti-regresión-hp009: los docs family-level tagueados
   combinado siguen matcheando) — la famtie decide, no la intuición.
2. **Whitelist doc_map-aware dentro de `_filter_to_query_models`** — el patrón IDENTITY_MAP
   (`retriever.py:1445-1451`: fail-open escalonado, filtra solo si deja ≥3) cambiando la fuente
   `family_scope` jsonl → doc_map del catálogo; + fetch dirigido por `document_id` para docs
   inalcanzables por `product_model` (la clase MIE-MI-600: 88 chunks pm=unknown, verificado en DB).

**Conducta pre-registrada (H2): F2 = expand-only; la conducta answer/clarify del bot queda
INTACTA; clarify-por-divergencia DIFERIDO.** Motivo verificado: los 14 paraguas adjudicados son
TODOS divergent=true (incl. CAD-150, B500) y s79/s80 estableció clarify-solo-si-la-RESPUESTA-
diverge (hp009 family-genérico → answer). Cablear clarify por divergent=true = regresión hp009 +
toda query de familia degeneraría a clarify. `resolve()` ya deja esa decisión al consumidor.

**Detector de tokens (H5/H7):** reutilizar el approach PROBADO de regex generada
(`src/rag/catalog.py:57-72`) con fuente = catálogo gobernado (cubre términos multi-palabra
"FAAST LT-200"/"serie Dimension" y tokens partidos "ZX 2e" que un lookup exact-por-token no ve).
Pre-excluir del detector: normkeys digit-only y ≤3 chars (86 tokens consumibles, incl. '808'/'816'
— FP conocidos a priori, no se descubren en shadow). NUNCA fuzzy (DEC-074, −2 hp011).

**Anti-dos-copias / plan de retiro (H5 + cross-model):** F2 nace declarando el END-STATE de las
6 vías de identidad hoy coexistentes: resolver-catálogo (nueva, la canónica) · LEVER2+series-YAML
(retirar en F4, ya en contrato) · IDENTITY_MAP/family_scope (retirar al aterrizar el whitelist
doc_map) · `model_catalog.json` stale-s55 (pasar a DERIVADO del catálogo gobernado, regen en CI
— el guard §3 del contrato) · MODEL_PATTERN seed (se queda, es el regex base). Sin esto D1 muere
por segunda copia.

## Pasos

### S1 — Build shadow-first (1 PR)
Flag `IDENTITY_RESOLVE=off|shadow|on` (default off). Resolver + los 2 seams + shadow-log
**a tabla Supabase** (H8: el filesystem de Railway es efímero), con (query, tokens, resolución,
qué habría cambiado en models/whitelist). Testset: casos NEGATIVOS (tokens que NO deben resolver,
frases con '808'-clase) + detección-en-frase + pinned hp011/hp018/hp009 + muestra del round-trip
del catálogo (H8: el round-trip completo es parcialmente tautológico — valida el índice, no la
adjudicación; muestrear, no "miles de asserts"). En paralelo: packet C2 (19 marcas → 196
productos unresolved).

### S2 — Shadow + medición famtie (1 sesión)
- Replay: 39 golds dev + `query_logs` (la tabla REAL — `query_gaps` NO existe, TECH_DEBT #8
  pendiente; H3 verificado con 404). **N≈69 queries del mismo autor (demo) — vale como SMOKE,
  no como gate estadístico; declarado.** El gate real es la famtie.
- FP-rate del detector en shadow → si limpio, flag `on` en dev → **famtie bajo freeze-contract
  completo** (hp018 4/4, hp009 sin regresión, retrieval-miss=14 no empeora) + bvg como control ±2.
- Scaffolding `query_gaps` (TECH_DEBT #8, ya decidido en DEC-051 como deploy-prep): opcional en
  esta sesión, da el ruler orgánico de ~sept.

### S3 — Candidates por CLASE (gated por demanda del shadow + reglas con guard)
Desglose verificado: 353 single-extractor · 196 unresolved (~19 marcas) · 70 colisiones ·
41 contextual · 14 x-brand (cola 6 homónimos). **Regla-ejemplo v1 CORREGIDA (H6):** "token
verbatim en el doc" promovería exactamente lo que Alberto acaba de adjudicar como NO-identidad
(Z978 = tabla de mapeo OEM, DH500 = cita de doc-number, M710 = compat) → la regla lleva guard:
promover solo si role=primary en el doc_map de SU doc + namespace del doc = namespace del
producto. Muestra por clase 50 (no 20: una cola del 5% escapa a n=20 con ~36% de prob.) +
residual declarado. Alberto adjudica la REGLA (1 decisión/clase).

### S4 — F3: re-tag DB (gated por S2; sin cambio de v1)
Dry-run diff → revisión Alberto → apply con snapshot. Política multi-producto del contrato
(multi-valor o paraguas, NUNCA colapso a un id); F3b (por-página) gated aparte.

## Riesgos declarados (v2)
1. Palanca ~4 golds; éxito = famtie + shadow-metrics, NO PASS (settled).
2. La política "añadir-sin-retirar" en `models` es HIPÓTESIS anti-hp009 — si la famtie la falsa,
   el fallback es whitelist-only (seam 2 sin seam 1).
3. Shadow N≈69 mono-autor: smoke, no estadística.
4. Cobertura parcial (674 candidates fail-open, doc_map 861/1014) — crece por lotes S3.
5. Coexistencia de 6 vías de identidad durante F2-F4: mitigada con el plan de retiro declarado;
   el riesgo real es un flag olvidado ON — el freeze-contract estampa config.

## Qué NO hace (sin cambio + refuerzos del dúo)
No PASS/juez (dual-judge ~sept) · no re-tag DB hasta S4 · no auto-promoción LLM · no clarify
nuevo (H2) · **no vía aditiva al pool (DEC-069)** · no boost/rerank nuevo.
