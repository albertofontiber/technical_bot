# s85·B0 — DISEÑO v2 del instrumento de retrieval-miss (juez semántico) — POST-DÚO

> v1 fue al dúo (Protocolo 3, diseño-primero, elección de Alberto). El dúo (cross-model GPT-5.5 +
> sub-agente Opus) cazó 6 fallos de diseño (2 CRÍTICO), TODOS confirmados regla-C, 0 falsos-pos.
> Esta v2 es el spec corregido que el build implementa. Tabla de respuesta al final.

## Objetivo y métrica
**retrieval-miss** = hecho CORE del gold, **servible en el corpus** (en algún chunk del manual), que **NO
está en el pool-50** (pre-rerank). Bucket `RETRIEVAL` del funnel: `in_top5→SINTESIS · in_pool50→RERANK-MISS
· in_manual_corpus→RETRIEVAL · else→CORPUS-GAP`. Métrica de B = count de `RETRIEVAL` sobre los **39 dev**,
reportado **por-PRIMARIO** (estricto: chunk del manual primario `_provenance.fuente`) **Y por-TARGET**
(laxo: cualquier manual en `targets` = fuente+citations+pdfs_used, incl. corroboradores). El por-PRIMARIO es
el canónico de B; el por-TARGET se reporta para no enmascarar el FP "corroborador tapa primario" (DEC-070).

## El juez (COMPONENTE NUEVO — no reuso; se versiona)
NO existe un juez hecho-vs-chunk; `bvg._judge_one` es end-to-end PASS. Se reusa SOLO la **plomería**
(threads/parse/Counter, `JUDGE_MODEL=gpt-5.5`, `judge_model_real`). El **prompt + rúbrica + agregación son
NUEVOS** y se congelan con `sys_sha`/`user_sha` en el manifest.

- **Input**: hecho (`valor` + contexto `texto`) + un batch de chunks con IDs (~20/batch).
- **Rúbrica ESTRICTA** (congelada ANTES de ver el count agregado — anti-overfit del árbitro): *"¿Alguno de
  estos textos AFIRMA o IMPLICA DIRECTAMENTE el dato «{valor}» (contexto: {texto})? Devuelve los IDs que lo
  soporten. SÍ solo si el VALOR CONCRETO está soportado — no por tema relacionado, no por mención del
  producto sin el dato."*
- **K=5** (Alberto). Un chunk "soporta" si **≥4/5** votos lo incluyen (umbral asimétrico estricto para el
  count FIRME); se reporta también la banda **≥3/5** (patrón FIRME/ALL del funnel, líneas 376-379) → expone
  los borderline que podrían flipear deltas de ±1-2.

## Sin pre-filtro con pérdida (fix del CRÍTICO #2)
El miss real es **within-doc** (26/27: el manual está en pool, 16/17 en top-5) → un top-8 por COSENO
rankea peor el chunk-valor (tabla/columna-EN, poco texto) frente a sus hermanos prosa-ricos = FN
estructural en el régimen dominante. Y "reusar embeddings del retrieval" era FALSO (los SELECT no traen
`embedding`; un "hecho" no es query ni documento en Voyage). Por tanto:
- **Candidatos = dedup( pool50[source-tied] ∪ manual[pre-filtro LÉXICO-anclado] )**. El pre-filtro del
  manual usa `fact_match_score` (léxico, ya existe) que ancla el VALOR literal — recall-safe para el
  within-doc (el chunk-valor CONTIENE el valor). Cap generoso (~40 candidatos/hecho).
- **Juzgar el hecho contra el conjunto-unión UNA vez** (batched K=5) → set de chunks-soporte. Derivar
  `in_top5 = soporte∩top5 ≠ ∅`, `in_pool = soporte∩pool50 ≠ ∅`, `in_manual = soporte∩manual ≠ ∅`. Colapsa
  los 3 niveles en 1 pasada de juez (corta coste ~3×).

## Universo y coste (fix #5 — recontado regla-C)
**134 hechos** CORE-presentes sobre los 39 dev (112 medibles + **22** no-medibles — el juez semántico SÍ los
juzga, cerrando el caveat de s81; NO 19). Coste ≈ 134 × (~3 batches × K=5) ≈ ~2000 llamadas GPT-5.5 para el
baseline. B3: re-juzgar SOLO hechos afectados por el método.

## Validación del árbitro (fix #5 — el dúo NO certifica el juez; mismo modelo GPT-5.5)
1. **Golds-trampa (la certificación real)**: N≥20 hechos CONOCIDAMENTE AUSENTES (valor real emparejado con un
   manual que NO lo contiene; + valores inventados plausibles) → el juez DEBE decir NO. Mide la **tasa de FP
   del juez** (sobre-acreditar = DESINFLA retrieval-miss = oculta el cuello = el sesgo peligroso). **Umbral de
   aceptación: FP ≤ 10%**; si lo supera, endurecer rúbrica (ANTES de ver el count agregado) y re-validar.
2. **Muestreo estratificado ciego** (N≥15) por: es-EN (los que motivaron DEC-070), within-doc, borderline
   (≥3/<4), valores-cortos, primario-vs-corroborador — no aleatorio.
3. **Varianza test-retest ≥3 corridas**: jitter del count agregado **+ jitter POR-HECHO** (un count estable
   puede ocultar hechos que flipean y se cancelan). Reportar la banda de error del árbitro (como el ±2 del ruler).

## Freeze-contract (Protocolo 4 — ampliado, fix #4)
corpus `chunks_v2` fingerprint + `ef_search=120` + `MERGE_STRATEGY=stamps` + **retriever LIMPIO (commit
post-A)** + juez `gpt-5.5` (`judge_model_real` real, no alias) + `sys_sha`/`user_sha` del prompt NUEVO +
K=5 + umbral=4 + `--all`/39-dev + `--workers` + embed-cache. Held-out (12) **EMBARGADO** (`exclude_heldout`).
seeds=knob-muerto (DEC-015). Manifest estampado.

## Reconciliación con s84 (fix #3 — honesta)
El 27→15 de s84 fue **Opus-manual-pool-completo** (DEC-070b), árbitro DISTINTO al propuesto (GPT-5.5-K5).
**NO es reconciliable** punto-a-punto (cambian modelo+método+universo) → solo **cota de sanidad gruesa**. El
número del instrumento nuevo (sobre 134, por-primario) **ES el baseline canónico**; NO se fuerza al 15, NO
se "confirma el ~45%". El léxico se reporta al lado como referencia del sesgo que DEC-070 midió.

## Output
Por-gold por-hecho: bucket (primario + target) · in_top5/in_pool/in_manual · conf (votos) · soporte-IDs ·
borderline. Agregado: retrieval-miss count (primario/target, FIRME/banda) + jitter. YAML + manifest. =
semilla directa de B1 (el "por qué" de cada miss: within-doc vs competición vs es-en).

## Cómo responde al dúo (traza)
| # | Hallazgo dúo | Sev | Fix en v2 |
|---|---|---|---|
| 1 | juez "reuso" = árbitro NUEVO encubierto | CRÍT | juez declarado NUEVO, prompt versionado (sha) |
| 2 | tie `targets` acredita corroboradores | CRÍT | métrica por-PRIMARIO **y** por-TARGET |
| 3 | top-8 coseno = FN estructural (within-doc) + premisa cache FALSA | CRÍT | candidatos = pool50-completo ∪ manual-léxico-anclado; juicio 1-pasada; sin coseno-solo |
| 4 | reconciliación con 15 inválida (Opus≠GPT5.5) | MED | 15 = cota gruesa, no target; nuevo = canon |
| 5 | universo 134 no ~112; validación N≈15 ritual | MED | universo=134; golds-trampa+estratificado+≥3 reps+jitter-por-hecho+umbral FP≤10% |
| 6 | freeze incompleto; rúbrica overfit-able | MED | freeze ampliado (sha/model-real/--all); rúbrica congelada pre-count |

## Gaps residuales declarados
- El juez GPT-5.5 puede tener sesgo propio NO cazable por el dúo (mismo modelo) → los golds-trampa son la
  única red; si su FP>10% tras endurecer, escalar a juez cross-model (Opus+GPT-5.5 mixto) — fork abierto.
- El pre-filtro léxico del manual podría perder un soporte SOLO-paráfrasis (sin token del valor); mitigado
  por la unión con pool50-completo (donde el within-doc vive) — el manual-prefilter es para CORPUS-GAP, raro.
