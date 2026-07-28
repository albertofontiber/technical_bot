# s283 — Clase-085 rescue: cat022 + hp012 (within-doc data-cell miss)

**Lane:** s283 clase-085 (cat022 + hp012). **Rama:** claude/s282-h0t2-qa @ 5a8a440. **DB:** SELECT-only
(NADA escrito — la tabla `chunks_v2_enunciados` NO se tocó; todo por seam in-process). **Sin commits.**
**Baseline:** `evals/bot_vs_gold_39_baseline_c1v4_parity_s283.yaml` (cat022 = PARCIAL, hp012 = PARCIAL).
**Env de paridad s283:** `COVERAGE_RELEASE_PROFILE=coverage_c1_v4 IDENTITY_RESOLVE=on
IDENTITY_RESOLVE_POLICY=replace MUST_PRESERVE_CONTRACT=on ENUNCIADOS_MULTIVECTOR=on HYQ_TABLE=on
VISUAL_ASSETS_REGISTRY=on RERANK_TOP_K=10 GENERATOR_SELECTION_BLOCK=on GENERATOR_PROMPT_VARIANT=fidelity`.

---

## TL;DR — VEREDICTO (medido)

**El rescate within-doc vía enunciados NO flipea cat022 ni hp012** — es un **NO-GO medido** para el INSERT
como fix aislado. La autoría de enunciados es SÓLIDA (cosine query↔enunciado alto: cat022 0.64–0.74,
hp012 0.59–0.67; el swap surrogate→padre funciona), pero el padre rescatado **muere en `post_diversify`**
(`_diversify_by_source_file`) en AMBOS golds. El chunk-diana vive en un `source_file` **ya saturado**
(MNDT722_40-40L: 10 chunks en pool; 15088SP: 11 chunks) cuyos hermanos de coseno más alto agotan los
~slots que el round-robin del diversify concede al fichero antes de llegar al padre rescatado. **Es el
muro DIVERSIFY (clase DEC-091, CERRADO NO-GO), no un gap de autoría/ingesta** — exactamente el fallo que
el `LEVER_DIGEST` ya registró para hp012 '99+99' («el padre entra por swap y muere ahí — pipeline, no
ingesta») y que s88 (DEC-075f/DEC-088) ya había diagnosticado para cat022 («banda-IR en MNDT722 p8, el
MISMO doc servido, pero no sube al top-5»).

**Recomendación:** **NO shippear el INSERT de estos enunciados como rescate de cat022/hp012** — está medido
que no paga (defeated por diversify) y, peor, añadiría filas al canal A3 vivo con **riesgo de desplazar
anclas reales** en otros golds (lección DEC-102: la carga sin cuota agolpa el sort-mixto). El canal A3 paga
donde el `source_file` diana está **infra-representado** (p.ej. el lado ES `MPDT280` de hp012 '2 lazos/396',
o cat016); cat022/hp012 apuntan a ficheros **saturados** → el rescate se bloquea aguas abajo. Los
enunciados candidatos quedan documentados (formato exacto, reversibles por ids) por si el muro diversify se
resuelve, pero **hoy no hay INSERT que recomendar**.

---

## §1 — TRAZA cat022 ($0): ¿existe el chunk de las bandas IR? ¿está en el pool?

**SÍ existe** — el manual `MNDT722_40-40L` (Spectrex/Honeywell, texto digital-native, no OCR) tiene 71
chunks reales; **4 llevan la banda IR discriminante**:

| chunk id | pág | ci | contenido clave | ¿en pool cat022? |
|---|---|---|---|---|
| **`c94d2270`** | **p11** | 13 | **Tabla 2 «Versiones del detector»: L/LB = IR 2,8 µm sin/con BIT · L4/L4B = IR 4,5 µm sin/con BIT** — el discriminador LIMPIO que resuelve las 3 aristas del gold | **AUSENTE (0/pool)** |
| `a6eae6a1` | p49 | 54 | Apéndice A spec: «Respuesta espectral S40/40L-LB IR:2,5–3,0µm · S40/40L4-L4B IR:4,4–4,6µm» | **AUSENTE (0/pool)** |
| `74cc9f95` | p8 | 10 | prosa: «el sensor IR funciona … entre 2,5 y 3,0µm … hidrocarburos» (**solo el lado L**, no da 4,5µm) | **presente, rank 49** (cola) |
| `36ca37d0` | p12 | 15 | principios: «sensor IR en S40/40L y LB … 2,5 a 3,0 micrones» (solo L) | AUSENTE |

- **Fuente exacta del gold** (`atomic_facts` core): `MN-DT-722 S40/40L p1 §1.1` → en DB = `MNDT722_40-40L`
  p8/p11/p49. La tabla p11 (`c94d2270`) es la fuente ORO: cubre L=2,8µm, L4=4,5µm y el sufijo B=BIT
  (sin/con) en una sola celda.
- **Clasificación de clase:** cat022 es **la misma clase NETA que hp012** (el dato-de-celda discriminante
  no llega al servido → PARCIAL), con un matiz: cat022 tiene **UN testigo parcial** (`74cc9f95` p8) enterrado
  en rank 49 que el reranker LLM SÍ puede subir al servido (lo observamos en rank 0 en un run), **pero p8
  solo trae el lado L (2,5-3,0µm), nunca el L4=4,5µm** → el bot presenta la diferencia como sensibilidad/rango
  (exacto al diagnóstico del baseline). Los discriminadores LIMPIOS (`c94d2270` p11, `a6eae6a1` p49) están
  **ausentes del pool**, igual que el total 792/1980 de hp012. **Confirmado: pool-absent within-doc para la
  evidencia que realmente cierra el gold.**
- **hp012 (recap traza, `evals/s283_hp012_diag_v1.md`):** `b162a7eb` (15088SP p151) contiene AMBOS totales
  («El AM2020 … diez LIBs (1980 …). El AFP1010 … cuatro LIBs (792 …)») + `f03d3ae4` (p14, «= 792») —
  **ambos ausentes del pool (0/55)**.

Scripts: `scripts/s283_c085_trace.py`, `scripts/s283_c085_templates.py`.

---

## §2 — Enunciados candidatos (PROPUESTA de INSERT a `chunks_v2_enunciados`)

Autoría **DETERMINISTA ($0-LLM)**: cada enunciado ancla LITERAL al texto del chunk padre, formato
`R2_PROMPT_V1` (frase autónoma en ES técnico, modelo EXACTO, valores literales). Para el INSERT real Alberto
puede **regenerarlos vía `scripts/enunciados_pass.py`** (mismo formato + QA anti-alucinación); estos son la
propuesta + el vector medido. JSON versionado: `evals/s283_c085_candidates.json`.

**Contrato de fila** (idéntico a las filas reales de `chunks_v2_enunciados`, verificado con `SELECT` de
plantilla): `content` = el enunciado · `context` = el `context` (blurb-B7) del padre VERBATIM · `embedding`
= `embed(context + "\n\n" + content, input_type="document")` · `parent_id` = chunk diana · metadata
(`product_model/manufacturer/source_file/page_number/section_title/content_type/document_id/language`) =
copiada del padre · `ingest_batch = "enunciados-v1:s283-c085:p1"` · `extraction_sha256` = el del padre.
**Rollback:** `DELETE FROM chunks_v2_enunciados WHERE ingest_batch = 'enunciados-v1:s283-c085:p1'`.

### cat022 → parent `c94d2270` (MNDT722_40-40L p11, Tabla 2)  [cosine medido]
1. **[0.70]** «El detector de llama Spectrex SharpEye 40/40L está disponible en cuatro versiones: los modelos
   L y LB llevan el sensor IR a 2,8 µm, mientras que los modelos L4 y L4B llevan el sensor IR a 4,5 µm.»
2. **[0.74]** «En la familia del detector de llama Spectrex SharpEye 40/40L, el sufijo «B» (modelos LB y L4B)
   identifica las versiones que incluyen la función BIT (prueba incorporada / Built-In Test); los modelos L y
   L4 base no incluyen BIT.»
3. **[0.71]** «La diferencia entre el detector Spectrex SharpEye 40/40L y el 40/40L4 está en la longitud de
   onda del sensor IR: 2,8 µm en el 40/40L (y LB) frente a 4,5 µm en el 40/40L4 (y L4B).»

### cat022 → parent `a6eae6a1` (MNDT722_40-40L p49, Apéndice A)  [2º testigo]
4. **[0.64]** «Según las especificaciones técnicas del detector Spectrex SharpEye 40/40L, la respuesta
   espectral IR es de 2,5–3,0 µm en los modelos S40/40L-LB y de 4,4–4,6 µm en los modelos S40/40L4-L4B.»

### hp012 → parent `b162a7eb` (15088SP p151)  [cosine medido]
5. **[0.67]** «El sistema Notifier AM2020 admite un máximo de diez LIBs (tableros interface de lazo), lo que
   equivale a un total de 1980 dispositivos direccionables en todo el sistema.»
6. **[0.64]** «El sistema Notifier AFP1010 admite un máximo de cuatro LIBs (tableros interface de lazo), lo
   que equivale a un total de 792 dispositivos direccionables en todo el sistema.»

### hp012 → parent `f03d3ae4` (15088SP p14)  [2º testigo]
7. **[0.59]** «En el sistema Notifier AFP1010, el número de dispositivos direccionables en todo el sistema es
   de 792.»

> **Nota de fidelidad:** la tabla p11 dice «IR a 2,8 µm» (punto medio) y el Apéndice A dice «2,5–3,0 µm»; ambos
> son la MISMA banda del gold (2,5-3,0µm). Los enunciados conservan los literales de SU chunk-padre
> (p11=2,8µm, p49=2,5-3,0µm) — el QA de `enunciados_pass.py` exige tokens-valor en el chunk.

---

## §3 — FLIP-CHECK ($0 retrieval; sin DB-write) — cómo se midió y resultado

**Seam de medición.** `PILOT_PARENT_SWAP` (s94) está **RETIRADO** (insertaba en DB — prohibido aquí; su código
es histórico). El seam vivo es el canal A3 (`chunks_v2_enunciados` + `ENUNCIADOS_MULTIVECTOR=on`). Para medir
**sin escribir en DB**, el probe (`scripts/s283_c085_flipcheck.py`) hace **monkeypatch de `httpx.Client.post`**:
cuando el RPC es `match_chunks_v2_enunciados`, APENDE las filas candidatas con
`similarity = 1 − cos_dist(embed(context+content,"document"), query_embedding-del-payload)` — idéntico a lo
que el RPC calcularía server-side post-INSERT. **Todo el resto del pipeline corre INTACTO** sobre el padre
REAL hidratado desde DB (colapso por parent, `_enunciados_swap`, fusión sort-mixta [cuota OFF, s273],
model-filter, diversify, lang, rerank strict K=10, coverage). Fiel byte-a-byte salvo la fila candidata.

**Resultado (`evals/s283_c085_flipcheck_result.json`):**

| gold | padre diana | pool baseline | pool inyectado | servido baseline | servido inyectado | **FLIP** |
|---|---|---|---|---|---|---|
| cat022 | `c94d2270` (p11) | ausente | **ausente** | ausente | **ausente** | **NO** |
| cat022 | `a6eae6a1` (p49) | ausente | **ausente** | ausente | **ausente** | **NO** |
| hp012 | `b162a7eb` (p151) | ausente | **ausente** | ausente | **ausente** | **NO** |
| hp012 | `f03d3ae4` (p14) | ausente | **ausente** | ausente | **ausente** | **NO** |

**RAÍZ (traza por-etapa, `scripts/s283_c085_debug.py`):** en los 4 casos el padre inyectado **aparece en
`channels → post_merge → post_neighbor → post_superseded → post_model_filter`** y **desaparece en
`post_diversify`**. El enunciado ENTRA con cosine fuerte, el swap hidrata el padre real, sobrevive el
model-filter — y **`_diversify_by_source_file` lo expulsa**.

**Mecánica del muro (verificada en código, `retriever.py:2637-2687`):** el round-robin interleave del
diversify ordena `source_file` por su mejor-similarity y da a cada uno `max_per_source = max(2, top_k//3)=16`
slots, llenando hasta `top_k`. El `source_file` diana está **saturado de hermanos de mayor score**
(cat022: MNDT722_40-40L = 10 chunks, varios stampeados 0.80–0.85 por canales dirigidos typed/spec/synonym
—`retriever.py:526/623/1648/1694`, incomensurables con el coseno del enunciado; hp012: 15088SP = 11 chunks).
El padre rescatado (cosine ≤0.74) queda **por debajo de sus hermanos del mismo fichero** → el round-robin
agota los slots del fichero antes de alcanzarlo → cortado del pool[:50].

**Contrafactual (forzando la similarity del enunciado por encima de todos los hermanos;
`scripts/s283_c085_isolate.py`, inyección AISLADA de 1 enunciado):**

| gold | padre | forzado 0.95 | forzado 0.99 | interpretación |
|---|---|---|---|---|
| **hp012** | `b162a7eb` (15088SP p151) | **→ final rank 0** ✅ | — | muro **dependiente del score**: un rescate que puntúe el padre por encima de sus hermanos 15088SP (~0.80) SÍ lo lleva al pool. Pero el cosine real del enunciado (0.67) queda por debajo → **NO-GO con cosine real** |
| **cat022** | `c94d2270` (MNDT722_40-40L p11) | muere en post_model_filter | **muere igual** ❌ | muro **independiente del score**: NINGÚN enunciado (por bien autorado que esté) rescata este padre vía el pipeline actual — el round-robin del diversify lo excluye estructuralmente (la query detecta el modelo genérico `40-40` → el universo de `source_files` del diversify se expande y la mecánica de interleave/supplement no aloja al padre inyectado, incluso a 0.99) |

**Conclusión doble:** para **hp012** el rescate falla porque el enunciado **no puede superar en coseno** a los
hermanos del mismo fichero (techo semántico ~0.67 < ~0.80); para **cat022** falla porque el diversify
**excluye el padre a cualquier score**. Ambos = NO-GO, por vías distintas del MISMO muro (diversify), no de la
autoría. (La causa exacta de la asimetría cat022 vs hp012 a score alto se deja como hipótesis medida, no
aserto: no era necesario zanjarla para el veredicto.)

**Coste real de la medición:** pool-rank/etapas/contrafactual = **$0** (retrieval-only; solo embeddings Voyage,
despreciable). El flip-check con servido usa rerank LLM (`RERANKER_BACKEND=llm`, K=10) ≈ **$0.05** (4 measures).
**NO se pagó ninguna generación** (el flip a servido no se produjo → no había respuesta que medir). **Coste
total de la lane ≈ $0.05–0.20**, muy por debajo del cap $3.

---

## §4 — Plan de medición completo post-INSERT (si Alberto decide cargar de todos modos)

**PRE-condición honesta:** el flip-check ya dice NO-GO. Este plan es lo que se ejecutaría SI se resolviera el
muro diversify (fuera del alcance de esta lane; DEC-091/091b lo tienen CERRADO) o si Alberto quiere el ledger
completo. Orden barato→caro, con gates de parada:

1. **($0) INSERT dry + flip re-check.** Cargar los 7 enunciados a `chunks_v2_enunciados` (batch
   `enunciados-v1:s283-c085:p1`) → re-correr `scripts/s283_c085_flipcheck.py` contra la DB real (sin
   monkeypatch). **Gate:** ¿padre en servido top-10 de cat022/hp012? Si NO (esperado) → **STOP + rollback**,
   el INSERT no paga.
2. **(~$1) bvg dirigido cat022 + hp012** (K=3, juez GPT-5.5, freeze-contract) SOLO si el gate 1 flipea:
   `ONLY_QIDS=cat022,hp012 python scripts/test_bot_vs_gold.py`. Métrica: PARCIAL→PASS.
3. **($0 → ~$2) NO-REGRESIÓN en los 39 (crítico, lección DEC-102).** Añadir filas al canal A3 vivo puede
   **desplazar anclas** en otros golds (crowding del sort-mixto sin cuota). Control: dump de pools de los 39
   OFF-vs-ON (`scripts/s103_dump_pools.py`-style) → **assert 0 anclas-OK perdidas** en los 37 no-diana; si
   hay churn, bvg K=3 de los golds afectados. **Gate:** 0 regresiones reales.
4. **Controles negativos:** golds del MISMO fabricante/familia que NO deben moverse (Spectrex 40/40:
   cat021/cat023; Notifier AM2020: hp004/otros del 15088SP) — verificar servido byte-estable.
5. **Rollback documentado:** `DELETE ... WHERE ingest_batch='enunciados-v1:s283-c085:p1'` (reversible por
   batch o por lista de ids). Verificar 0 filas restantes + pools de los 39 vuelven a baseline.

---

## §5 — ¿La clase tiene más miembros? (declarado, no sobre-atribuido)

**Confirmados (trazados):** cat022 + hp012 = within-doc data-cell miss (DEC-085), con el matiz de que el
blocker efectivo hoy es **diversify** (source_file saturado), no solo retrieval.

**Candidatos NO confirmados** (del scan de diagnósticos del baseline v2 — **cada uno es candidato-FN hasta
trazarlo**, `feedback_corpus_gap`): entre los 18 PARCIAL-answer, los diagnósticos que mencionan una
celda/spec puntual ausente y PODRÍAN ser de esta clase: **cat008** (RFL 47kΩ / M200E-EOL-RD), **cat010**
(alimentación nominal 24V dc), **hp014** (valores de resistencia / 35Ω). El resto de PARCIAL-answer
(cat001/cat017/cat019/hp005/hp010/hp017/hp020) leen como **completitud de procedimiento / síntesis**
(eje distinto = el cuello DEC-075/094, no data-cell-retrieval). **No reclamo pertenencia** sin traza
per-gold; si la clase se persigue, el orden es: trazar cat008/cat010/hp014 (¿celda ausente del pool? ¿en
source_file saturado como cat022/hp012, o infra-representado como cat016?) antes de cualquier autoría.

**Observación estructural para la clase:** el rescate A3 paga cuando el chunk-diana está en un `source_file`
**infra-representado** en el pool (le da su primer slot). FALLA cuando el chunk-diana es el N-ésimo de un
`source_file` **saturado** (diversify lo capa). cat022/hp012 son del segundo tipo → el canal A3, tal como
opera hoy, **no los alcanza**. Esto acota dónde el lever DEC-085 tiene palanca real y dónde no.

---

## Artefactos (todos en territorio de la lane; NADA committeado; DB intacta)
- `evals/s283_c085_rescue_v1.md` (este doc) · `evals/s283_c085_candidates.json` (los 7 enunciados) ·
  `evals/s283_c085_flipcheck_result.json` (resultado del flip).
- `scripts/s283_c085_trace.py` (traza cat022) · `s283_c085_templates.py` (plantillas + hp012) ·
  `s283_c085_flipcheck.py` (flip-check in-process) · `s283_c085_debug.py` (traza por-etapa + contrafactual) ·
  `s283_c085_diversify_why.py` · `s283_c085_isolate.py` (confirmación aislada del muro).
