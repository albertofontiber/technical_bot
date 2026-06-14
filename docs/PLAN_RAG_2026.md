# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 14 jun 2026 (s72, DEC-053 — primer build de los fixes de retrieval de DEC-052: **Lever 2
> [identidad]** construido tras flags. **Brazo A [e-series: hp009/hp018] VERIFICADO end-to-end**
> [el pool se da la vuelta: 0→23/26 chunks reales, espurio→0] = candidato a ship, falta medir
> PASS. **Brazo B [rescate pm, cat013] = NO-OP** [el chunk no entra al pool → bloqueado en
> Lever 1]. 3 rondas de dúo, 0 FP; flags default OFF = prod inerte. Siguiente: medir PASS de A,
> luego **Lever 1** [profundidad del pool] que desbloquea cat013 + el grueso de los 16).
>
> **El historial vive en [`docs/HISTORY.md`](HISTORY.md)** (movido en s56): log de sesiones
> s30→s55, rationale histórico de mayo 2026 (secciones originales ## 1-9, con su numeración —
> las citas antiguas tipo "PLAN §9.14" o "§660" resuelven allí) y changelog. Este fichero queda
> compacto a propósito: es el doc que se relee en cada arranque de sesión.
>
> **📍 Mapa canónico (un dueño por tema).** ESTE documento es el **único canónico** del
> **roadmap + estado + qué sigue**. Los demás lo referencian, NO lo duplican:
> `docs/RULER_DESIGN.md` = diseño del ruler (D1-D11 + §2 procedimiento + §8 taxonomía);
> `docs/DECISIONS.md` = el *por qué* de las decisiones med/alto; `TECH_DEBT.md` = deuda con
> triggers; `docs/ARCHITECTURE.md` = cómo funciona el sistema; `docs/HISTORY.md` = traza
> histórica (append-only). Si el rumbo aparece en dos sitios y discrepan, **manda éste**.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best practice con fuente
> identificable, (2) estructural — ataca la causa raíz, no el síntoma, (3) escalable a 30+
> fabricantes sin fricción por fabricante. Si una propuesta no cumple los tres, se declara como
> gap honesto.

## Estado actual (s72 — 14 jun 2026)

**s72 (DEC-053): primer build de los fixes de retrieval (DEC-052) — Lever 2 (IDENTIDAD) tras
flags; Brazo A VERIFICADO end-to-end, Brazo B NO-OP hasta Lever 1.** Orden decidido con Alberto:
Lever 2 (identidad) ANTES que Lever 1 (profundidad del pool) = más barato/escalable/bajo riesgo.
**Brazo A** (alias-paraguas `model_aliases` + serie e-series en `series_registry`, flag
`LEVER2_IDENTITY`): **VERIFICADO contra corpus real** — el pool de hp009/hp018 se da la vuelta
(0→23/26 chunks reales ZX2e/ZX5e, espurio 22/26→0, +25 docs de serie MI-530) = **candidato a
ship; falta medir PASS** (eval-driven incompleto). **Brazo B** (rescate de pm mal-atribuido en
`_filter_to_query_models`, flag `LEVER2_PM_RESCUE`): correcto+seguro+testeado, pero **verify-first
= NO-OP para cat013** (los chunks SDX-751 no entran al pool [broad-fallback capado a 5] → el
rescate no recupera lo ausente → **bloqueado en Lever 1**). **3 rondas de dúo (incl. cross-model
GPT-5.5), 0 FP** — corrigieron el rumbo 3× (C roto/B-gate; paraguas-no-en-members; B-NO-OP =
`feedback_my_bias` operando). C (keyword-strip hp006) / D (section_path, TECH_DEBT #48 nuevo) /
cat001 DIFERIDOS. 330 tests; flags default OFF = prod inerte (paridad probada). DEC-053; HISTORY.

### Antecedente s71 (DEC-052)

**El re-análisis del residual (pedido por Alberto, escéptico del pivote s69)
= el cuello es RETRIEVAL, atacable con fixes concretos.** Dos tracks ortogonales con dúo
adversarial (workflows batched; rate-limits y apagones gestionados con resume). **Track 1
(audit del ruler, doble-escéptico auditor+defensor):** de 13 candidatos a "gold-injusto",
solo **cat012** sobrevive como maybe-PASS (debatible) — el guard anti-"trampas al solitario"
tumbó 4 que el auditor marcó injustos (cat009/cat011/cat019/cat020 = gold JUSTO, bot falló);
**el bot NO está infra-puntuado, escepticismo de Alberto validado**; 6 golds reclasificados
a retrieval-miss; 10 dudas para Alberto (`s71_track1_audit.yaml`). **Clasificación v2 de los
29 no-PASS** (`s71_classification_v2.yaml`): **16 RETRIEVAL-miss + 2 retrieval-family ≈ 18
(≈60%)** · 4 generación · 3 corpus-gap? · 2 borderline (bot ~correcto, PARCIAL conservador)
· 1 diseño (cat011 catálogo) · 1 gold-injusto (cat012). **Track 2 (diagnóstico de retrieval,
17 golds, 6 mecanismos, 16/17 fixable** — `s71_track2_retrieval_diag.yaml`): raíz común =
**INANICIÓN DEL POOL aguas arriba** — `keyword_search` limit=5 sin order (orden físico
arbitrario), broad-fallback vectorial capado a 5, reranker LLM lee solo `content[:800]` (el
hecho cae fuera). Fixes CONCRETOS y baratos (subir límites, order, ventana del reranker),
varios MEDIDOS end-to-end (hp003: preview 800→2400 → el reranker ya sirve el chunk correcto).
NO es el canal-broad (NO-GO s68). **El pivote-a-producto de s69 queda CORREGIDO: el residual
SÍ es lever-addressable — la conclusión "agotado" fue prematura (le faltaba este diagnóstico
quirúrgico per-gold).** DEC-052; HISTORY.

### Antecedente s69 (corregido por s71):

**s69 (DEC-051): A/B del lever de GENERACIÓN (completitud + guarda de fidelidad tras flag)
= NO-GO — y con él CIERRA la fase de levers-baratos del eval.** Tras el NO-GO del canal
(s68), el ciclo de generación completo: audit de resolución ($0 — el eval SÍ tiene
resolución) → **4 audits para fijar la diana** (el bias #20 reapareció en 2 capas: diana
inflada 12→8→5; el re-audit por relato-del-juez ERA bias #20, cerrado solo a
nivel-de-CONTENIDO: 4 sólida [cat008/cat020/hp005/hp014] + 1 recuperada [cat019]) → diseño
v3.2 con dúo r1+r2 + 2 cortes cross-model (enmiendas: **verificación content-level de los
flips decisivos** [bias #20 aplicado a la DECISIÓN], flag estricto, available_models como
SHIP-gate) → build tras flag `GENERATOR_PROMPT_VARIANT` (default base = prod inerte;
paridad a nivel-de-construcción $0 — no output-LLM que es no-determinista; suite 317) →
A/B (~$20): brazo `fidelity` (195 gen, 0 err, `assembled_sha` distinto = corrió de verdad)
vs `s67base` **re-juzgado en la misma tanda** (mata el drift del juez). **Resultado:
Δ_net=0 — NINGÚN gold de la diana flipeó a PASS; la predicción §4 FALSADA · +1 regresión
de conducta (cat011 clarify→answer, content-verificada) · verbosidad en 3 PASS-control.**
La **verificación content-level (enmienda B) PAGÓ**: el Δ=0 del juez solo habría dicho
"inerte", pero el prompt SÍ añadió completitud (hp014 metió FET=20 y el límite 32) sin
flipear modal Y rompió clarify en cat011 → cuadro real = efecto modesto + colateral, no
inercia. **Hallazgo del re-judge: ±2 de varianza del juez** (re-juzgar las MISMAS
respuestas base dio F 5→7). **NO-GO: flag default base (inerte); NO se salta a Opus**
(anti-racionalización §4 — el prompt-completitud falló, no es prueba de que la capacidad
sea el cuello). DEC-051; HISTORY. (s68 DEC-050 canal NO-GO; s67 DEC-048 CE ROLLBACK.)

**Lectura estratégica (la que define el rumbo de abajo):** 3 ciclos de lever barato, 3
negativos. El residual está **mapeado y desmenuzado** (corpus-gap diferido · within-doc-miss
· generación que el prompt no mueve · K-INESTABLE = ruido del juez) y **el ruler tiene ±2
de ruido** justo donde SHIP exige +2. Conclusión honesta: **la fase de exprimir-el-residual-
con-levers-baratos está agotada**; cada NO-GO costó ~$20-30 y evitó shippear ruido, pero el
valor marginal del siguiente micro-lever es bajo. Los unlocks reales son corpus (diferido a
demanda) y **eval orgánico (técnicos, ~sept)** — gated. El pivote: dejar de pulir el eval y
**preparar producto/deploy para cuando lleguen los técnicos**.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5; dispatcher `RERANKER_BACKEND` default `llm` — el swap a CE
Voyage se midió en A/B s67 = **ROLLBACK**, lever archivado con evidencia; el dispatcher
queda como instrumento) → generador `claude-sonnet-4-6` (temp=0,
`max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles; 25 huérfanos
residuales) / 1.170 docs {active 998 · superseded 3 · needs_review 79 · retired 90} / 31
marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035; **catálogo
de fabricantes 30 marcas** tras el backfill s65 + fix de paginación). **⚠️ Contratos rotos por
el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120,
default mantener); ventana de freeze del corpus: CERRADA (s64); fingerprint con dimensión
lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo, intacto en s69),
taxonomía CONGELADA (DEC-033), juez GPT-5.5 + K-mayoría. **Baseline VIGENTE = re-freeze
`s67base`** (12 jun 2026: 10/39 PASS-control · 5 unánimes · 4 K-INESTABLES; manifest
completo + `s67_embed_cache.json` como pin de embeddings); frozen-s58 = referencia
histórica muerta. Próximo freeze: correr SIEMPRE con `EMBED_CACHE_PATH` (DEC-048c).
**⚠️ Límite de resolución medido (s69): ±2 de varianza del juez** — re-juzgar las MISMAS
respuestas base dio F 5→7. SHIP exige Δ_net≥+2 = justo en el suelo de ruido → el ruler
actual NO distingue fiable un win de +1/+2. Endurecerlo (dual-judge, s47§D) sería
prerrequisito de MÁS lever-work; gated a "¿vale sin técnicos reales?" (lean: esperar al
eval orgánico).

## Qué sigue (s72 — medir A, luego Lever 1)

1. **Medir el PASS-delta del Brazo A** (hp009/hp018) — A/B vs `s67base` con cobertura granular
   s70 (anti ±2) + gate PASS-control sobre los 39 + **pin `embed_cache`** (freeze-contract). El
   retrieval ya está PROBADO (el pool se da la vuelta); falta confirmar el PASS end-to-end
   (generador+juez). Si GO → ship A (flag `LEVER2_IDENTITY` on).
2. **Lever 1 — profundidad del pool** (el grueso de los ~16 + DESBLOQUEA cat013/Brazo B): el
   chunk correcto no entra al pool por la inanición aguas arriba. Fixes (cada uno tras flag,
   mismo método: cobertura granular + dúo + gate PASS-control):
   a. **Broad-fallback vectorial `limit=5`→`effective_top_k`** (`retriever.py` Step 2; hp013/
      hp002 + filtro-modelo — el canal vectorial sano está capado a 5; bajo categoría detectada
      el principal devuelve 0 → solo el broad-5 aporta).
   b. **`keyword_search` order determinista + `limit`↑** (cat016 — orden físico arbitrario).
   c. **Reranker preview `content[:800]`→`[:2400]`** (`reranker.py:74`; hp003 reproducido).
   d. **Rescates del diversify** (cat001/hp001/hp011/hp017 — aditivos, sin re-barajar el pool).
3. **Reactivar Brazo B (cat013) tras Lever 1** — cuando Lever 1 meta el chunk SDX-751 al pool,
   el rescate (ya construido) lo recupera; medir con el **gate de conducta refuse-inference**
   (`undue_inferences==[]` ∧ completitud de los 2 core sube ∧ ausente sigue ausente), end-to-end.
4. **Diferidos de s72:** C keyword-strip (hp006, blast global) · D section_path (#48, lever de
   rank, su propia tanda) · generación (hp005/hp014) · diseño cat011 · corpus-gap · #45 diagramas
   / available_models-fix / eval-orgánico. Dudas de Track 1 para Alberto (`s71_track1_audit.yaml`).

**Nota de método (s72):** el **verify-first barato** (¿el chunk entra al pool?) ANTES de pagar la
medición completa — ahorró medir el NO-OP del Brazo B. Y medir cada fix con la cobertura granular
(s70) ADEMÁS del juez (±2 de ruido que oculta wins de +1).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día);
language/revision_date/document_family masivos (B4/B5 s65 → contrato de ingesta, no
backfill); TECH_DEBT #40 (recall-gate CI), #47 (lista de manufacturers del diversify);
**dureza de la tabla de decisión** (Alberto s67b: replantearse las reglas/su dureza —
SOLO pre-registrado y motivado por evidencia, NUNCA post-hoc para dejar pasar un lever;
las válvulas existentes [dado-plausible, enmienda-de-instrumento con evidencia+Alberto]
ya absorben dureza legítima).
