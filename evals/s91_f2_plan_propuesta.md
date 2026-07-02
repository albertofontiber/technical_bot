# s91 → F2: plan v2.2 (2 rondas de dúo: 15+13 hallazgos, todos verificados regla-C, 0 FP)

> Artefacto de revisión del dúo (Protocolo 3). Autor: Claude. **v1 → v2: el dúo completo
> (sub-agente Fable fresco + cross-model GPT-5.5 con tools) tumbó el mecanismo central de v1**
> — "expansión aditiva del pool" re-litigaba DEC-069 (aditivo = NO-OP-con-regresión MEDIDO,
> hasta el comentario de `retriever.py:1443` lo dice: "NO aditivo (DEC-069 fue NO-OP)") sin
> citarlo. Todos los hallazgos verificados contra código/DB antes de aceptar (regla C).
> Contrato canónico: `docs/IDENTITY_CATALOG_CONTRACT.md`. Tally: `evals/adversarial_review_log.jsonl`.

## Objetivo de F2 (métrica sin cambio; la CONDUCTA enmienda el contrato §5.1 — ✅ Alberto, PR #105)
Consumir el catálogo gobernado en query-side. Métrica pre-registrada (contrato F2, línea 167):
**hp018 4/4 SIN regresar hp009, medida con el instrumento famtie (`retrieval_miss_famtie.py`)
bajo freeze-contract COMPLETO (corpus+índice+embeddings+juez+seeds+config+catálogo-commit)** +
retrieval-miss=14 no empeora + tests verdes. bvg/PASS solo como control ±2 (PASS plateau settled
DEC-075 — no es la métrica). hp011→Supra vía `prefer` (test-case homónimo).

## El mecanismo v2.2 (corrección central del dúo r1, afinado en r2)
NADA de vía aditiva nueva al pool (DEC-069). El resolver del catálogo alimenta los DOS seams
existentes — con el estatus de evidencia DECLARADO por seam (r2: "medidos" sobre-afirmaba):

1. **Lista `models`** — generalizar el seam LEVER2 (`retriever.py:125-128`, hoy series-YAML
   per-familia flag OFF) a resolución data-driven desde `catalog_store.resolve()`.
   **Estatus de evidencia:** el seam con política REPLACE está MEDIDO (hp018 4/4 **y** regresión
   hp009 — `series_registry.py:325`: "replace, no add, para que el filtro vete el
   parecido-equivocado"). La política **ADD (añadir variantes sin retirar el token) es HIPÓTESIS
   NUEVA anti-regresión-hp009, no medida** — la tabla de predicciones (v2.1c) lleva replace y
   add como brazos explícitos y la famtie arbitra; si add reproduce la regresión de replace, no
   hay seam-1 y F2 queda whitelist-only.
2. **Whitelist doc_map-aware dentro de `_filter_to_query_models`** — el patrón IDENTITY_MAP
   (`retriever.py:1445-1451`: fail-open escalonado, filtra solo si deja ≥3) cambiando la fuente
   `family_scope` jsonl → doc_map del catálogo. **Estatus de evidencia:** el patrón existe pero
   su único dato previo es NET-NEGATIVO con la fuente mala (family_scope texto-libre, −2 hp011)
   — este seam es la MISMA apuesta "la-fuente-no-el-seam" que el seam 1, declarada como apuesta.
   La whitelist es SUSTRACTIVA (protege chunks ya recuperados del veto del filtro — la clase
   MIE-MI-600: 88 chunks pm=unknown que el vector/keyword SÍ puede traer y el filtro mataría);
   **el fetch por `document_id` NO forma parte del mecanismo de F2** — vive SOLO en la escalera
   de fallback v2.1d (r2: estaba en dos sitios contradictorios, y no es un seam existente).

**Conducta pre-registrada (H2): F2 = expand-only; la conducta answer/clarify del bot queda
INTACTA; clarify-por-divergencia DIFERIDO.** Motivo verificado: los 14 paraguas adjudicados son
TODOS divergent=true (incl. CAD-150, B500) y s79/s80 estableció clarify-solo-si-la-RESPUESTA-
diverge (hp009 family-genérico → answer). Cablear clarify por divergent=true = regresión hp009 +
toda query de familia degeneraría a clarify. `resolve()` ya deja esa decisión al consumidor.
**⚠ ESTO ENMIENDA EL CONTRATO (r2, ambos revisores): el contrato §5.1 manda clarify si
divergent=true y su fila F2 dice "+ clarify" — pero el propio contrato cita s79/s80 como
principio D4, y el flag-level mapping lo contradice (la divergencia es por-PREGUNTA, no
por-flag). Enmienda propuesta: F2-row → "resolución query-side tras flag (expand-only);
clarify conduct-level → fase posterior con lógica por-pregunta". GATE: marca de Alberto —
dos canónicos divergentes es la clase dos-copias que ya pagamos.**

**Detector de tokens (H5/H7, corregido r2):** reutilizar el approach PROBADO de regex generada
(`src/rag/catalog.py:57-72`) con fuente = catálogo gobernado (cubre términos multi-palabra
"FAAST LT-200"/"serie Dimension" y tokens partidos "ZX 2e" que un lookup exact-por-token no ve).
Pre-exclusión: **SOLO normkeys digit-only** ('808'/'816'). Los alfanuméricos cortos pasan por la
regex con word-boundary — **`norm('ZXe')='zxe'` tiene 3 chars: excluir "≤3" mataría el caso
central de hp018** (bomba cazada por el cross-model r2) → tests pineados ZXe/ZXSe en el detector.
La cifra de afectados se COMPUTA en build-time desde el catálogo (método declarado; hoy 42
canonical + 115 alias digit-only-o-≤3 — la cifra "86" de v2.1 era irreproducible, r2 hallazgo 7).
NUNCA fuzzy (DEC-074, −2 hp011).

**Anti-dos-copias / plan de retiro (H5 + cross-model; completado r2):** F2 nace declarando el
END-STATE de las vías de identidad hoy coexistentes: resolver-catálogo (nueva, la canónica) ·
LEVER2+series-YAML (retirar en F4, ya en contrato) · **LEVER2_PM_RESCUE (`retriever.py:1470-1484`
— omitida en v2.1, r2 la cazó; retirar con LEVER2)** · IDENTITY_MAP/family_scope (retirar al
aterrizar el whitelist doc_map) · `model_catalog.json` stale-s55 (pasar a DERIVADO del catálogo
gobernado, regen en CI — el guard §3 del contrato) · MODEL_PATTERN seed (se queda, es el regex
base). Sin esto D1 muere por segunda copia.

## Pasos

### S1 — Build shadow-first (1 PR)
Flag `IDENTITY_RESOLVE=off|shadow|on` (default off). Resolver + los 2 seams + shadow-log
**a tabla Supabase** (H8: el filesystem de Railway es efímero), con (query, tokens, resolución,
qué habría cambiado en models/whitelist). Testset: casos NEGATIVOS (tokens que NO deben resolver,
frases con '808'-clase) + detección-en-frase + pinned hp011/hp018/hp009 + muestra del round-trip
del catálogo (H8: el round-trip completo es parcialmente tautológico — valida el índice, no la
adjudicación; muestrear, no "miles de asserts"). En paralelo: packet C2 (19 marcas → 196
productos unresolved).
**+v2.1a — test de EXCLUSIÓN de flags de identidad (semántica definida en r2)**: los 4 flags
(`IDENTITY_RESOLVE`/`LEVER2_IDENTITY`/`LEVER2_PM_RESCUE`/`IDENTITY_MAP`) con regla FAIL-FAST:
`IDENTITY_RESOLVE≠off` + cualquier flag legacy ON ⇒ **ERROR al arranque** (no precedencia
silenciosa — el builder no improvisa la semántica, r2 hallazgo 3). El test asegura la lista
contra el código (grep de `os.getenv` de identidad en retriever) para que un flag nuevo no
escape a la regla.
**+v2.1b — stamp del catálogo-commit**: la famtie/eval estampa el commit de `data/catalog/` en
sus resultados (posible desde el fix D1 — el catálogo está versionado). Es la pieza que
materializa el "catálogo-commit" del freeze-contract, no una promesa.

### S2 — Shadow + medición famtie (1 sesión) — AJUSTES Alberto s92
- Replay: **39 golds dev SOLO** — `query_logs` DESCARTADO por Alberto (sus ~30 queries live son
  copias de las preguntas del eval, para ver las respuestas con sus ojos → duplicarían golds,
  no aportan forma-de-usuario). El shadow queda como smoke puro; el gate real es la famtie.
- **1er replay YA CORRIDO (s92, pre-medición): 27/39 golds expanden, 0 bloqueados-por-candidate,
  0 clarify. Cazó la clase FP 'palabra-común-como-alias'** ('Solo'→hp005; colores/CARGADOR/
  'Dimension') → detector endurecido: alias `nombre-largo` solo si llevan dígito (model-shaped)
  + DETECT_STOPWORDS; hp002/hp013/hp019 conservados vía la regla por-forma.
- FP-rate del detector en shadow → si limpio, flag `on` en dev → **famtie bajo freeze-contract
  completo** (hp018 4/4, hp009 sin regresión, retrieval-miss=14 no empeora) + bvg como control ±2.
  **⚠ Trampa de instrumento cazada en r2: la famtie NO re-recupera — lee el `pool_pin`**
  (docstring: "usa pool_pin… NO re-recupera el pool"). Medir F2 exige **RE-GENERAR el pin con el
  flag ON vía el instrumento upstream productor del pin** (reusando los labels de soporte del
  juez ya pagados — cost-discipline); correr la famtie sobre el pin viejo = NO-OP garantizado.
- **+v2.1c — tabla de predicciones PRE-REGISTRADA** (disciplina s69/C3, predicción-vs-resultado):
  ANTES de correr la famtie, por-gold: hp018×4 → qué doc/chunk esperamos que entre y por qué seam
  (models vs whitelist); hp009 → sin cambio; hp011 → Supra. La medición confirma o FALSA cada
  fila — mata la racionalización post-hoc (bias #20/#51).
- **+v2.1d — escalera de fallback PRE-REGISTRADA** (de la iteración con Alberto sobre DEC-069
  pre-NOCAT): si hp018 <4/4 → diagnóstico per-gold de DÓNDE se pierde el doc (la famtie es
  family-aware) → si la pérdida es en entrada-al-pool (el doc ni se recupera), el brazo
  siguiente es **fetch acotado GATEADO por el whitelist** (nunca unión ciega — la mitad
  regresión de DEC-069 es mecanismo-inherente al pool capado) como medición NUEVA bajo la
  config actual. Pre-registrado aquí para no inventar levers a mitad de medición.
- Scaffolding `query_gaps` (TECH_DEBT #8, ya decidido en DEC-051 como deploy-prep): opcional en
  esta sesión, da el ruler orgánico de ~sept.

### S3 — Candidates: DIFERIDO-IDENTIFICADO (ajuste Alberto s92, respaldado con dato)
**MEDIDO en el replay s92: 0 de los 39 golds dev tiene token bloqueado-por-candidate** → los
~630 candidates NO tocan ningún gold; fail-open = comportamiento de hoy, no muerden. Alberto:
no analizarlos ahora (él no quiere ser el stopper) — quedan IDENTIFICADOS aquí y en el QA de F1
(`evals/s91_f1_qa_riesgo.md`) para trabajarlos POR DEMANDA (cuando el shadow orgánico o un gold
nuevo los toque), con las reglas-de-clase + guards de abajo como método pre-acordado.

### S3 (método pre-acordado para cuando toque) — Candidates por CLASE
Desglose verificado: 353 single-extractor · 196 unresolved (~19 marcas) · 70 colisiones ·
41 contextual · 14 x-brand (cola 6 homónimos). **Guard v3 (r2 tumbó el v2 con su propio
contraejemplo: `notifier:z978` ES role=primary en TIDT089 con namespace coincidente — el guard
v2 lo habría promovido; y `role` sale de la MISMA extracción s83 = circular):** el guard que
soporta la carga es **"el token NO tiene hermano multi-namespace en el catálogo NI histórico de
homónimo"** (Z978 tenía `pepperl-fuchs:z978` → auto-excluido) + role=primary + doc mono-producto.
"Namespace del doc" DEFINIDO (r2 hallazgo 8: no es un campo): = namespace del entry primary si
es único; docs multi-primary cross-namespace (clase gemelos CMX-10RM/6424) EXCLUIDOS de
auto-promoción. Muestra por clase 50 (no 20: una cola del 5% escapa a n=20 con ~36% de prob.) +
residual declarado. Alberto adjudica la REGLA (1 decisión/clase).

### S4 — F3: re-tag DB (gated por S2; sin cambio de v1)
Dry-run diff → revisión Alberto → apply con snapshot. Política multi-producto del contrato
(multi-valor o paraguas, NUNCA colapso a un id); F3b (por-página) gated aparte.

## Vigencia de los settled que este plan pisa (+v2.1e, de la pregunta de Alberto)
- **DEC-069 (aditivo NO-OP)**: medido 29-30 jun, PRE-VECTOR_NOCAT (1 jul) → sus números no
  transfieren formalmente; su mitad regresión (desplazamiento en pool capado) es
  mecanismo-inherente y sí transfiere. v2 no depende de él: lo respeta por diseño.
- **LEVER2 hp018 4/4 (DEC-074)**: medido 1 jul, POST-NOCAT → el seam en que v2 se apoya está
  evidenciado bajo la config ACTUAL. Esta asimetría (negativo pre-fix, positivo post-fix) es la
  base de elegir los seams.
- CE/MERGE/generación: settled en PASS y pre-NOCAT — fuera del terreno de F2; si algún día se
  re-pisa su terreno con métrica retrieval, re-medir, no recordar.

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
