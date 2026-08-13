# s320 E2 — Matar el doble catálogo: la DERIVACIÓN se gobierna — v2 (tras dúo r23)

> **v1→v2 (dúo r23: Sol 4 · Fable 3, convergentes, 0 FP — TODO aplicado):**
> 1. **Los términos del derivado los da `_resolvable_terms()`** (Sol M1): la puerta
>    YA adjudicada del resolver (canonical activos no-candidate + alias model-shaped
>    DETECT_ALIAS_TIPOS + paraguas + homónimos, con stopwords y guardas de segmento
>    cazadas por replays s92) — no una re-implementación con los gates legacy.
> 2. **Atestación = documento ACTIVO con chunks servibles** (Sol M2): entrada doc_map
>    cuyo document_id está activo Y tiene chunks; las **49 colisiones de E1 quedan
>    EXCLUIDAS** hasta adjudicación; el fallback pm-atestado se restringe a docs
>    activos.
> 3. **Gate de voz EXHAUSTIVO** (Sol M3 + Fable F1): lista ordenada completa de
>    `all_models` (el orden por `chunk_count` importa: Whisper trunca) + mapa
>    modelo→fabricante + PROMPT FINAL byte-a-byte + `known_manufacturers` explícito
>    (Fable F2 — la 4ª función sin cubrir). `chunk_count` derivado = conteo de chunks
>    por pm-normkey (misma fuente que hoy), declarado en el recibo.
> 4. **Gates heredados restaurados** (Sol M4): famtie + assessment smoke entran al
>    freeze-contract E2 (con corpus+índice+embeddings+config+catálogo-commit), no
>    solo el sweep-39.
> 5. Cifra corregida (Fable F3): el snapshot vigente tiene **591** modelos (mi 584
>    contaba tras exclusiones).

**Marco (plan v2, dúo r20)**: APUESTA ESTRUCTURAL declarada, no-eval-driven
(DEC-093: el wiring no arregla golds; DEC-094: identidad ⊥ cuello). Valor:
UNA fuente de verdad para escala-30+ y matar la clase dual-path. Gates de
EQUIVALENCIA (Δ acotado y explicado), jamás de mejora.

## Inventario de lectores (r20 M6 — hecho ANTES de elegir brazo)

`src/rag/catalog.py` mezcla DOS naturalezas:
- **Utilidades de TEXTO** (`normkey`, `_fold`, `_core`): 9+ módulos (resolver,
  must_preserve, mp_lexicon, evidence_contract, answer_planner, compat_bundle,
  procedure_bundle, identity_index) — SIN dependencia del snapshot. E2 NO las
  toca (son puras; separarlas de fichero = cosmética con blast-radius, fuera).
- **API de DATOS del snapshot** (5 funciones · 3 consumidores):
  `catalog_available` + `extract_models` + `model_manufacturer` +
  `known_manufacturers` (retriever: detector + clasificación) · `all_models`
  (whisper_vocabulary + voice_query_normalization: VOZ). El fichero
  `data/model_catalog.json` (584 modelos, regenerado ~18-jul, PRE-Kidde:
  drift medido en E0).

## Los dos brazos (y el porqué del elegido)

**A — Sustitución** (catalog.py lee el catálogo gobernado directo): DESCARTADO
para v1. El snapshot se construyó DESDE el corpus (detecta modelos con docs);
el gobernado tiene 1.655 productos incluidos sin-docs → la sustitución ingenua
cambiaría el DETECTOR (más modelos detectados → target_models sin docs →
retrieval alterado). No es Δ≈0: es un cambio de conducta grande disfrazado de
limpieza. Reconsiderable como fase posterior con su propia medición.

**B — Derivación gobernada (ELEGIDO)**: `model_catalog.json` pasa a ser
ARTEFACTO DERIVADO del catálogo gobernado — `build_model_catalog.py` v2 lee
`catalog_store` (products consumibles + aliases) ∩ **atestación de corpus**
(producto con entrada doc_map o pm atestado en chunks), conservando los gates
anti-ruido actuales (fechas/normas/acrónimos) como cinturón. Los 3 lectores NO
se tocan. El snapshot deja de nacer de un SQL suelto y nace de la fuente
gobernada, con recibo de DIFF (viejo vs derivado: altas/bajas con causa).

## Gates de equivalencia (pre-registrados en el freeze-contract E2)

1. **Sonda del detector**: `extract_models(q)` viejo-vs-derivado sobre las 39
   queries gold congeladas → diff por query con causa; cualquier PÉRDIDA de
   detección en gold = STOP (las altas se listan y adjudican).
2. **Sweep-39 de composición** (ids servidos, mismo freeze de corpus/config):
   Δ≈0 esperado; cualquier gold con composición cambiada se investiga antes de
   mergear.
3. **Voz**: `all_models` viejo-vs-derivado → diff de vocabulario Whisper
   (tamaño + muestras); acotado y adjudicable, no silencioso.
4. `catalog_store validate` + suite completa + 0 escrituras fuera del artefacto.

## Gaps declarados

- El derivado hereda la CALIDAD del gobernado: un candidate mal etiquetado no
  entra (candidate-gating) pero un consumable con pm sucio sí — la sentada E1
  (packets pendientes) mejora la fuente con el tiempo; el diff-recibo lo hace
  visible.
- La atestación por doc_map está incompleta donde doc_map lo está (887/1069):
  fallback = pm atestado en chunks (la fuente del snapshot actual) — declarado,
  y converge a doc_map puro conforme E1 se complete.
- `MODEL_PATTERN` estático (la unión de cero-regresión del v1) se CONSERVA.
