# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 10 jun 2026 (s58, DEC-039 — gate de atribución ejecutado).
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

## Estado actual (s58 — 10 jun 2026)

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`, sin prompt caching; **`stop_reason`/
`output_tokens` instrumentados s58**) sobre **`chunks_v2` = 25.090 chunks / 1.012 docs /
31 marcas / 587 modelos** (contextual-retrieval activo al 100%; identidad data-driven, DEC-035).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo, `verified()`=39),
taxonomía CONGELADA (DEC-033), juez GPT-5.5 + K-mayoría. **BASELINE FRESCO s58 (DEC-039):**
runner `scripts/bvg_kmajority.py` (4 fases reanudables; contexts top-5 CONGELADOS con blurb
hidratado; juez NUEVO congelado de la ventana = prompts harness + `response_format`; run-manifest
DEC-021 §F completo, alias del juez resuelto `gpt-5.5-2026-04-23`). **PASS-control FIJADO = 10**
(6 unánimes) · K-INESTABLE 3 · residual 26 clasificado: **retrieval-localizado 8** (within-doc-miss
domina; multi-doc clásico minoritario = hp008+hp001) · **GENERACIÓN 4** (+ severidad: los FALLO-modales
reparten hacia generación/sobre-admisión) · NO-LOCALIZADO 2 · INDETERMINADO-solo-débiles 8
(sobre-admisión 4/8) · CUALITATIVA 4 (1 fallo de conducta: hp004). **Truncamiento DESCARTADO**
(195/195 `end_turn`); suelo-del-juez no aparece como cuello. El mecanismo del within-doc-miss
(pool vs rerank vs extracción) NO está medido — los misses son POST-retrieve-wide (DEC-018).
**La ventana de freeze del corpus está ABIERTA desde el freeze s58** (ninguna ingesta hasta
cerrar el ciclo; fingerprint en `s58_run_manifest.json`). Artefactos versionados:
`evals/s58_{frozen_contexts,generations,judgments,run_manifest}.json` + `s58_gate_report.yaml`
(las 195 generaciones PERSISTIDAS — el scorer del A/B corre sobre ellas, cláusula C2).

## Qué sigue (orden vigente)

1. **(s59) Lever de retrieval-RECALL — branch FIRMADO por Alberto (s58b, DEC-039g), con los
   2 pasos baratos YA corridos:** el mecanismo está medido — funnel split de los 8
   retrieval-localizados: **RECALL=14 hechos fuertes ni-al-pool-50** (rerank 2, extracción 3);
   spot-check de las 4 sobre-admisiones: 3 = retrieval-honesto, 1 = generación-identidad
   (hp009, ZXe↔ZXAE/ZXEE). Bulto retrieval ≈11 golds. Secuencia de s59:
   (a) **dimensionamiento barato del POR QUÉ** los 14 hechos no matchean (léxico vs semántico
   vs chunking — los hechos están identificados en el funnel YAML) → (b) **diseño del lever
   con dúo** (NO pre-elegido) → (c) **medición K-mayoría** vs el baseline s58 (contexts
   congelados; PASS-control fijado 10). **Plan B declarado:** si no hay lever barato → A/B 2×2
   generación {Sonnet 4.6, Opus 4.8}×{blurb OFF,ON} (su brazo A YA corrido = el baseline;
   Batches −50%; ship/rollback antes de medir). Paralelo menor (no bloquea): hp009 → fix de
   identidad de variantes (TECH_DEBT #43); cat020/cat008 (generación pura) quedan al residual
   post-lever.
2. **Tras el lever (s59/s60): confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` bajo
   el criterio PRE-REGISTRADO (PREREG §held-out + **cláusulas C1/C2 FIRMADAS s58b**: Δ global
   ordinal answer-only; fabricaciones vía atomic_scorer sobre generaciones persistidas).
3. **Después del ciclo:** corpus nuevo (Aritech completo / Kidde resto / Ziton-GST; método en
   `docs/CORPUS_FIRESECURITYPRODUCTS.md`). **Freeze-contract:** ninguna ingesta dentro de la
   ventana baseline→A/B→held-out (la ventana corre DESDE el freeze s58).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
