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

1. **(s59, arranque) DOS decisiones de Alberto con la clasificación en la mesa (DEC-039 d/e/f):**
   - **(i) Branch del lever** — el gate NO lo ordena (PARAR cumplido). Opciones con sus pasos
     baratos exploratorios (protocolo congelado en DEC-039e; informan, no deciden):
     **retrieval-dirigido** → paso 1: funnel split {en-pool50-rerank-lo-deja / no-en-pool50 /
     no-extraído} sobre los 8 retrieval-localizados (corpus congelado, ~1h) ANTES de elegir
     dirección (A2 está deprioritizada por DEC-018 — no pre-suponer);
     **generación** → A/B 2×2 pre-registrado {Sonnet 4.6, Opus 4.8} × {blurb OFF, ON} sobre los
     contexts congelados s58 (el brazo A YA está corrido = el baseline; Batches −50%; brazo Opus
     sin temp=0, absorbido por K-mayoría; ship/rollback escrito antes de medir) + paso 2:
     spot-check de los 4 sobre-admisión (top-5 congelado vs fuente).
   - **(ii) Firma de las cláusulas C1/C2 del PREREG** (DEC-039f, pre-datos): C1 = fórmula del
     Δ global (ordinal answer-only, K-inestables excluidos); C2 = "0 fabricaciones" lo decide el
     atomic_scorer sobre generaciones persistidas. Sin firma, el criterio held-out queda con dos
     lecturas defendibles (los 2 CRÍTICOS del cross-model p2).
2. **Tras el lever (s59/s60): confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` bajo
   el criterio PRE-REGISTRADO (PREREG §held-out + C1/C2 firmadas).
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
