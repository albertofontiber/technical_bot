# s283 — Diagnóstico hp011: el residual «ri»/«t.Fi» es PROPAGACIÓN de superficie corrupta servida, NO invención

**Lane:** hp011-diag (s283). **Rama:** claude/s282-h0t2-qa @ dc1f474. **DB:** SELECT-only. **Sin commits.** **Coste real:** ~$0.5 (3 generaciones + traza; reranker LLM barato).
**Baseline auditado:** `evals/bot_vs_gold_39_baseline_c1v4_parity_s283.yaml` (qid hp011 = **FALLO**, «introduce un segundo `ri` y `F.1`, alucina»).
**Gold:** `evals/gold_answers_v1.yaml` qid hp011 — VERIFICADO por Alberto (s101, DEC-line 1488). **NO se re-litiga el gold.**

## TL;DR — VEREDICTO

El residual de hp011 **NO es invención (clase síntesis-c)**. Los tres elementos que el juez marca como
«alucinación/confusión» están **LITERALMENTE en el texto de los chunks servidos** y el bot los **cita**:

| Síntoma en la respuesta | Nace en (chunk servido) | Forma EXACTA en el texto-fuente | Clase |
|---|---|---|---|
| Sección 1: «t.Fi (t.A → 0 seg.)» | **F13** = `475a8f18` p63 `HLSI-MN-103_RP1r-Supra_lr` (gold-cited) | `…configurado en parámetro ~~t.Fi~~ (~~t.A~~ → 0 seg.)` — **tachado OCR con letras** | **(b)+(a): artefacto de extracción tachado; el writer NO lo normaliza y lo propaga** |
| Sección 2: «parámetro **ri** — Resumen inhibido, apartado **4.1.2**» | **F3** = `2113ac69` p2 `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` | `### ri - Resumen inhibido tras extinción … apartado 4.1.2 … parámetro ri` | **(b): DUPLICADO CORRUPTO de r.I en un doc secundario; el writer NO deduplica** |
| Sección 5: «parámetro **F.1**» | **F2** = `4b81cc38` p54 `HLSI-MN-103I` (EN) | `Use the parameter [F.1] to configure the inhibition period…` | grounded (param REAL EN); ruido de scope, no defecto |

**El retrieval está SANO** — r.I, t.A, ABORT y Flow están todos representados en el top servido.
El cuello es **GENERACIÓN/SÍNTESIS sobre texto servido adversarial** (un duplicado corrupto + un
tachado OCR), consistente con DEC-070/094 (el cuello del eval = síntesis) y con el rótulo del commit
del baseline («hp011 residual `ri`, flip class single-pass»).

**El «ri/Resumen inhibido» es la mitad ESTABLE (3/3 runs); el «t.Fi» y el «F.1» son la mitad ESTOCÁSTICA (1/3, 0/3).**

---

## §1 — Env de paridad (contrato s283, idéntico a `s283_cat016_diag_v1.md` §1)

```
COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on IDENTITY_RESOLVE_POLICY=replace
MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on HYQ_TABLE=on VISUAL_ASSETS_REGISTRY=on
RERANK_TOP_K=10 LLM_MAX_TOKENS=3500 GENERATOR_SELECTION_BLOCK=on GENERATOR_PROMPT_VARIANT=fidelity
CHUNKS_TABLE=chunks_v2 (forzado por el harness)
```
Query hp011: «En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado
normal tras resetear. ¿Qué comprobar?»

## §2 — TRAZA retrieval ($0): pool + served, forma EXACTA de cada parámetro

`retrieve_chunks(top_k=50)` → **26 chunks** (todos RP1r-Supra; 0 corpus-gap de doc — la familia
está bien recuperada). Token-map del pool (en `content` crudo):

| token | ranks del pool |
|---|---|
| `r.i`/`r.1` (Rearme/Resumen inhib) | 2, 6 |
| `t.Fi` | 20 |
| `ABORT` | 0,1,9,10,14,15,20 |
| `Flow`/`flujo` | 5,7,13,14,15,19,20,21,24,25 |
| `Resumen inhib` | 2 |
| `Rearme inhib` | (en el chunk p63 servido, ver F13) |
| `4.12.2` (correcto) | 17 |
| `4.1.2` (corrupto) | 2 |

**Served set (rerank strict K=10 + coverage append=3 → 13 fragmentos = orden `[F#]` del generador):**

| `[F#]` | id8 | pág | origen | cómo llega | contenido clave |
|---|---|---|---|---|---|
| F2 | `4b81cc38` | p54 | HLSI-MN-103I (EN) | reranked | `Use the parameter [F.1] to configure the inhibition period… 4.12.2` |
| **F3** | **`2113ac69`** | **p2** | **Guía Rápida ES** | **reranked (top-10)** | **`### ri - Resumen inhibido tras extinción … 4.1.2 … parámetro ri`** |
| F6 | `296aa5f1` | p2 | Guía Rápida ES | reranked | `or - Entrada de paro (ABORT) rearmada automáticamente … 4.1.7` |
| F11 | `2d45a70a` | p56 | HLSI-MN-103 (ES) | **APPENDED** (document_local) | `Valor variable de 05 a 295 seg … Tiempo de activación del circuito` (= t.A, limpio) |
| **F13** | **`475a8f18`** | **p63** | **HLSI-MN-103 (ES)** | **APPENDED** (document_local) | **`[LCD display showing "r.i"] Rearme inhibido tras extinción … 4.12.2 … parámetro ~~t.Fi~~ (~~t.A~~ → 0 seg.)`** |

### Texto crudo de los dos chunks causales (verbatim)

**F13 (`475a8f18`, p63 — el chunk canónico gold-cited de r.I):**
> `| \[LCD display showing "r.i"] | Rearme inhibido tras extinción | De acuerdo con … apartado 4.12.2 … ~~- -~~	Rearme inhibido hasta finalizar extinción o cuando agotado tiempo configurado en parámetro ~~t.Fi~~ (~~t.A~~ → 0 seg.)&#xA;00	Rearme permitido en cualquier momento (por defecto)&#xA;De 01 a 30	Rearme inhibido durante intervalo definido |`

Observaciones sobre F13:
- El display se extrae como `"r.i"` (i minúscula) → el writer copia `r.i`. **Es fiel-al-chunk** (clase 7-seg documentada, `feedback_7segment`: Alberto adjudicó el glifo como `r.I`; la extracción escribió `r.i`).
- `~~t.Fi~~ (~~t.A~~ → 0 seg.)` = **tachado OCR con letras**. El TACHADO marca la superficie como
  NO fiable (erratum del PDF / mis-render de LlamaParse). El writer **elimina los `~~` y transcribe
  ambas formas** → «t.Fi (t.A → 0 seg.)». La forma limpia y correcta de t.A (05-295 seg) vive
  SEPARADA y sin tachar en F11 (p56).

**F3 (`2113ac69`, p2 — Guía Rápida, DUPLICADO CORRUPTO):**
> `### ri - Resumen inhibido tras extinción … apartado 4.1.2 … | 00 | Resumen inhibido desde finalizar extinción o cuando agotado tiempo configurado en parámetro ri (por defecto) | | 01 a 30 | Resumen inhibido … |`

Es el **MISMO parámetro** que F13 (r.I «Rearme inhibido tras extinción», 4.12.2), corrompido en la
transcripción del doc secundario: **Rearme→Resumen**, **4.12.2→4.1.2** (dígito perdido), y la
semántica del valor `00` invertida (F3: «00 = Resumen inhibido desde finalizar»; F13: «00 = Rearme
permitido en cualquier momento, por defecto»). El gold Alberto-verificado documenta UN solo
parámetro (r.I) para este concepto y sus notas listan `r.5/r.1/t.A/E.L/P.d` — **no existe «ri /
Resumen inhibido»**: es corrupción, no un segundo parámetro real.

**Estructura de serving relevante:** el DUPLICADO CORRUPTO (F3, Guía p2) entra **RERANKED en el
top-10 protegido**; el CANÓNICO (F13, manual p63) solo entra por **coverage-append** (lane
`document_local_content_coverage_v1`, que rescata el chunk gold-cited). El writer ve las dos
versiones y las reconcilia como **dos parámetros distintos**.

## §3 — REPRODUCCIÓN (pipeline completo ×3, mismo env de paridad) — ESTABILIDAD

`_s283_hp011_ans_run{1,2,3}.md`. Served-set estable en los 3 (F3, F13, F2 presentes siempre; ±1
por no-determinismo del LLM-rerank, DEC-line s102). `stop_reason=end_turn` en los 3 (0 truncado con 3500).

| forma en la RESPUESTA | run1 | run2 | run3 | estabilidad |
|---|---|---|---|---|
| «ri — Resumen inhibido» (de F3) | ✅ | ✅ | ✅ | **ESTABLE 3/3** |
| «apartado 4.1.2» (corrupto, de F3) | ✅ | ✅ | ✅ | **ESTABLE 3/3** |
| «t.Fi» (de F13 tachado) | ✅ | — | — | estocástico 1/3 |
| «F.1» (de F2 EN) | — | — | — | estocástico (✅ en el baseline) |
| «r.i/r.I» (correcto, F13) | ✅ | ✅ | ✅ | estable |
| «t.A» limpio / «05 a 295 seg» | 1/— | — | — | **rara vez transmitido** pese a servirse (F11) |
| ABORT enclavado/latched | ✅×2 | ✅×1 | ✅×1 | presente (el baseline single-pass lo omitió) |

Lectura: **la mitad ESTABLE del FALLO = el duplicado corrupto `ri/Resumen/4.1.2` de la Guía Rápida**
(se sirve siempre → se propaga siempre). La mitad ESTOCÁSTICA (`t.Fi`, `F.1`, omisión de ABORT/t.A)
es el «flip single-pass» que hace variar el veredicto run-a-run.

## §4 — CLASIFICACIÓN (taxonomía del brief)

- **(c) invención pura → DESCARTADA.** Cero afirmaciones no-ancladas: los tres síntomas se citan a
  `[F#]` y están verbatim en el chunk. `feedback_corpus_gap`/`feedback_my_bias`: no hedgear como
  «alucina» lo que es propagación fiel de fuente corrupta.
- **`t.Fi/t.A` = (b) + (a).** El chunk **trae** la ambigüedad (tachado OCR `~~t.Fi~~ (~~t.A~~…)`);
  el writer **no normaliza** el tachado y lo propaga. Clase 7-segmentos/extracción documentada.
- **`ri / Resumen inhibido / 4.1.2` = (b) corpus-quality.** Duplicado corrupto de r.I en
  `HLSI-MA-103` (Guía Rápida); servido junto al canónico → **fallo de síntesis: no deduplica dos
  renderizados del mismo parámetro de display**. Es la mitad estable y el corazón del FALLO.
- **`F.1` = grounded, no-defecto.** Parámetro real (manual EN p54); ruido de scope/relevancia.
- **Omisión de ABORT-enclavado (p44) / t.A-limpio (p56):** servidos vía chunks equivalentes
  (no siempre el gold-cited); transmisión estocástica. Retrieval NO es el cuello.

## §5 — PROPUESTAS (rankeadas · con MECANISMO y coste de medición · SIN implementar)

> **Protocolo 4 / alineación de MÉTRICA:** el objetivo de HOY = conducta hp011 medida en
> GENERACIÓN single-turn (bvg FALLO). Ningún «settled» lo zanja: el *lever de generación*
> `GENERATOR_PROMPT_VARIANT=fidelity` está **SHIP (s102/DEC-098)** pero su métrica es
> completitud fact-level (+3/0), ortogonal a deduplicar superficie corrupta; el *selection-block*
> como PROMPT fue **NO-GO (s102/DEC-097)** por sobre-disparo → se movió a gate de CÓDIGO. Ambos
> avisan: **el prompt del generator es el layer equivocado para esto.**

### P1 (RECOMENDADA) — Normalizar el TACHADO-OCR-con-letras en el contexto servido al generador
**Qué:** aplicar la política que la EC **ya codifica** (`src/rag/evidence_contract.py`:
`_STRUCK_RX = re.compile(r"~~(.*?)~~")`, `_apply_struck_ocr`, comentario s722/1222: «un tachado
CON letras corta el display — superficie que la extracción marcó como no fiable;
`feedback_7segment`: jamás re-afirmar una transliteración 7-seg») **también al texto que
`coverage_context_content` entrega al writer**, no solo a las obligaciones must_preserve. Hoy la EC
gatea las OBLIGACIONES pero el contexto crudo del generador conserva los `~~…~~` → el writer los ve
y los propaga.
**Mecanismo:** en el seam de ensamblado de contexto (`coverage_context_content` / `generator._format`),
depurar spans `~~letras~~` antes de construir `[Fragmento N]`. En F13 esto elimina «t.Fi (t.A→0seg)»
y **fuerza al writer a tomar t.A de F11 (p56, sin tachar)** → net esperado: desaparece la mitad t.Fi
sin perder t.A.
**Por qué BP + estructural + escalable:** transform GENÉRICO sobre un artefacto de extracción que
aparece en cualquiera de los 31 fabricantes (no un parche hp011); **reutiliza** máquina existente y
ya confiada; ataca el layer correcto (contexto servido, no el prompt).
**Alternativa descartada dentro de P1:** stripping en INGESTA (re-escribir chunks_v2) — más caro,
irreversible sin re-ingesta, y pierde la traza del tachado; el seam de serving es reversible (flag).
**Gaps/riesgos declarados:** (i) es **byte-afectante** al contexto → exige gate de no-regresión (¿cambia
el served-text de algún control?). (ii) En F13 t.A TAMBIÉN está tachado → stripping deja la cláusula
incompleta; se apoya en que F11 sirve t.A limpio (verificado servido) — **hay que medir que el writer
efectivamente lo recoge y no lo pierde**. (iii) fail-closed si el tachado vacía el único token (la EC
ya lo maneja; replicar en el seam de contexto).
**Coste de medición:** una pasada bvg de 39 con env de paridad (~$3) O, más barato, judge-free:
diff de served-context sobre los 39 (¿cuántos sets cambian?) + conveyed-fact-level en el subset RP1r
(hp011) A/B off/on (~$0.3). Métrica: nace en generación, se mide en conveyed-fact-level + no-regresión.

### P2 (para la mitad ESTABLE `ri/Resumen`) — RESIDUAL-A-TÉCNICO: defecto de corpus en `HLSI-MA-103`
**Qué:** el `### ri - Resumen inhibido … 4.1.2` de la Guía Rápida (`2113ac69`) es una **corrupción de
transcripción** de r.I (Rearme, 4.12.2). No es normalizable por léxico ni prompt (requiere el dominio
para saber que «Resumen»=corrupción de «Rearme»). **Surface a Alberto** con el id del chunk + el
render de la p2 de `HLSI-MA-103_GuiaRapida_RP1r-Supra_ES_lr` para adjudicar: (a) confirmar corrupción
→ patch/re-render de ESE chunk (corpus fix, 1 doc, Alberto-gated, clase DEC-line 1258/1261 corpus-gap
residual + `feedback_corpus_gap`: verificar antes de declarar defecto), o (b) descartar como parámetro
real. **No auto-generalizable.**
**Alternativa descartada:** un lever genérico de dedup/diversidad que «trague» el duplicado en serving
→ **RECHAZADA**: el near-dup TEXTUAL es marginal en el corpus (DEC-line s62), la Guía Rápida es un
chunk legítimo, y el desplazamiento por posición ya midió colateral (DEC-100). Un dedup por «mismo
parámetro» exige entity-linking a nivel de celda que no existe. Riesgo > beneficio para 1 doc.
**Gaps/riesgos:** ground-truth no 100% verificable por mí (¿corrupción vs 2º param real?) → es
precisamente el caso «surface a Alberto» (autonomía). El gold sugiere fuerte que es corrupción.
**Coste:** $0 (lectura de Alberto) + coste de re-render si procede.

### P3 (DESCARTADA) — Instrucción en el prompt del generator («no dupliques parámetros / prefiere el manual completo»)
**RECHAZADA por historial del lever:** el prompt del generator es settled/`fidelity` (DEC-098) y el
patrón prompt-gated de variantes **sobre-dispara** (hp009, DEC-097 → se movió a código). Una regla
«dedup de parámetros» (i) no distingue corrupción de 2º-param real, (ii) es inestable/no-medible-limpio,
(iii) toca un lever con métrica ya cerrada. Es el layer equivocado.

**Ranking:** **P1 (t.Fi, estructural, mide barato) → P2 (ri, residual-a-Alberto, la mitad estable) → P3 no.**
P1 y P2 son **complementarias** (atacan las dos mitades distintas del FALLO); ninguna sola vuelve
hp011 a PASS por sí misma — P1 quita la mitad estocástica t.Fi, P2 (vía Alberto) quita la mitad
estable `ri`. La omisión ABORT/t.A es estocástica y se mueve con el ancho ya shippeado (top-10, DEC-092b).

## §6 — Repro (comandos) + artefactos

```
# Traza $0 (pool + served + forma de tokens):
python <scratchpad>/s283_hp011_trace.py
# Reproducción pagada (pipeline completo ×N, escanea la respuesta):
N_RUNS=3 python <scratchpad>/s283_hp011_repro.py
# (ambos fuerzan el env de paridad §1 in-process)
```
Artefactos de trabajo (scratchpad, no versionados): `s283_hp011_trace.py`, `s283_hp011_repro.py`,
`_s283_hp011_served_dump.txt`, `_s283_hp011_ans_run{1,2,3}.md`.
Evidencia primaria en repo: `evals/bot_vs_gold_39_baseline_c1v4_parity_s283.yaml` (qid hp011);
`evals/gold_answers_v1.yaml` (qid hp011, notas s101); `src/rag/evidence_contract.py` (`_STRUCK_RX`).
