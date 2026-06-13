# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 13 jun 2026 (s69, DEC-051 — A/B del lever de GENERACIÓN = **NO-GO** [Δ_net=0, predicción
> falsada + regresión de conducta content-verificada]: **CIERRA la fase de levers-baratos
> del eval** — 3 ciclos seguidos sin GO [s67 CE ROLLBACK · s68 canal NO-GO · s69
> generación NO-GO] + el re-judge destapó **±2 de varianza del juez**. **Pivote propuesto:
> de exprimir el residual del eval → a preparar PRODUCTO/deploy para los técnicos de
> sept** [#45 diagramas-datos + fix available_models + scaffolding de eval orgánico];
> corpus sigue diferido [DEC-049]).
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

## Estado actual (s69 — 13 jun 2026)

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

## Qué sigue (PIVOTE propuesto s69 — pendiente de confirmación de Alberto)

**El cambio:** cerrada la fase de levers-baratos del eval (3 NO-GO + ruler con ±2 ruido),
el esfuerzo near-term pasa de "exprimir el residual" a **preparar PRODUCTO/deploy para los
técnicos de ~sept** (= lo que DEC-049 pedía con "chatbot estable, robusto, que funcione
bien"; está sin empezar y su valor marginal hoy supera al del siguiente micro-lever).

0. **Decisión de Alberto:** mergear el PR de s69 (A/B-NO-GO + canon; flag inerte, cero
   cambio de prod) + confirmar este pivote.
1. **DIAGRAMAS #45 (datos) — sube a prioridad.** Feature VISIBLE para el técnico de campo;
   la mitad de DATOS es eval-inerte (verificado, DEC-049d) → mapeo (documento, página)
   desde la tabla vieja (44.035 chunks con diagrama vs 0/25.090 en v2) + extracción de
   faltantes + poblar `has_diagram`/`diagram_url`, con before/after de pools por backfill
   (el fingerprint no caza edits in-place, DEC-036e). El CABLEADO de entrega va después.
2. **Fix de producto `available_models` (cross-model s69, SHIP-gate del lever):** el
   `models_context` (generator.py:449-455) inyecta "responde con lo que tengas" que
   CONTRADICE la regla dura clarify del SYSTEM_PROMPT — bug pre-existente, independiente
   del lever. Corregirlo estructuralmente (alinear con TIPO 1/2). + el 2º path
   (early-return sin chunks, gen:375-384, enumera modelos) que también roza la regla.
3. **Scaffolding de EVAL ORGÁNICO (prep para sept):** la tabla `query_gaps` + logging de
   queries reales → cuando lleguen los técnicos, se capturan los gaps que IMPORTAN (el
   ruler que vence al adversarial-39). Es F4 adelantado en su parte barata.
4. **Eval — fase de levers-baratos CERRADA.** Si se reabre: endurecer el ruler PRIMERO
   (dual-judge, el ±2; s47§D) — gated a "¿vale sin técnicos?". Levers que quedan, BAJA
   prioridad: within-doc-miss (hp013/cat016 — doc servido, chunk fuera del top-5; mecanismo
   distinto de s68) · aditiva del merge (forking-path, s68) · k>50 · #44 boost · Opus
   generación (NO auto — el prompt-completitud falló, no prueba que capacidad sea el cuello).
5. **Corpus: DIFERIDO demand-driven (DEC-049a, sin cambio).** Las 31 marcas = uso frecuente;
   la meta 30+ SIGUE en fase posterior. Gap real (vía Excel inventario) reactiva la ingesta
   con sus prerrequisitos (#44 escritor + #45 + identidad/supersesión EN INGESTA, DEC-045a +
   cola 74 `needs_review`). Los 3 sospecha-gap (hp006/hp009 corpus + cat017/hp010/hp012)
   alimentan esta cola. Pendientes menores s65: 25 huérfanos · TECH_DEBT #47 · lever #10.

**Auto-pushback declarado (Protocolo 2):** (a) ¿el pivote es huir de la dificultad? No —
el valor marginal del 4º micro-lever es demostrablemente bajo (3 NO-GO) y el deploy-prep
es necesario y no-empezado. (b) ¿declaro el eval "terminado" antes de tiempo? No: el ±2 de
ruido puede estar OCULTANDO wins de +1 (el content-level vio que fidelity SÍ completaba) →
por eso "endurecer el ruler primero" si se reabre, no "los levers no sirven". (c) Gap: el
pivote asume "bot bueno en lo común", medido por las conductas de seguridad + 10/39
PASS-control, pero NO verificado con técnicos reales — esa verificación ES el eval orgánico
(punto 3). Riesgo: producto-eng es otro modo de trabajo (no eval-driven con dúo); aplica el
contrato BP igual.

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
