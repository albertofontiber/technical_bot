# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 11 jun 2026 (s60, DEC-041 — lever de MERGE diseñado y REDEFINIDO a L-i+cross-encoder por
> gates; dado del reranker medido; diagramas muertos #45).
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

## Estado actual (s60 — 11 jun 2026)

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre **`chunks_v2` = 25.090 chunks / 1.012
docs / 31 marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035).
**⚠️ Contratos rotos por el SWAP s44, medidos:** `category` sin taxonomía canónica (DEC-040,
#44 — canal vectorial principal 0 filas en ~85% de queries; fallbacks tapan) y **`has_diagram`/
`diagram_url` a CERO en v2 vs 44.035 en la vieja (s60, #45 — el bot NO sirve diagramas: canal
+ tag del reranker + DIAGRAMAS_RELEVANTES muertos en silencio desde s44)**. Prod sin cambios
de código desde s58; ventana DB ABIERTA (ef_search=120, `--reset` revierte).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría, baseline s58 congelado (PASS-control 10 / 6 unánimes);
cláusula R FIRMADA (s59b). s59: lever RECALL (L-i) medido → **ROLLBACK regla 1** (código en
`s59-lever-code-ROLLBACKED`). **s60 (DEC-041): lever de MERGE diseñado v1→v4 (4 rondas de dúo,
35 findings/0 FP) y REDEFINIDO por 3 gates baratos en cascada SIN build** — paso-0: el reranker
LLM es sensible al orden 11/12 (palanca real) pero TAMBIÉN en PASS-control (sin freno) ·
hallazgo cat020: la ganancia +2 de s59 volteó con context idéntico = ruido → **Δ_net
pool-atribuible real de s59 ≈ −2** y techo del MERGE +2-frágil · r2 del dúo: **DADO
entre-corridas del reranker LLM medido (3/12 golds cambian top-5 con input bit-idéntico
entre sesiones)** — mina la atribución de cualquier A/B de retrieval y es defecto de producto ·
gate-D: **cross-encoder Voyage rerank-2.5 = determinista 12/12 + insensible al orden 12/12** →
**lever del ciclo REDEFINIDO (regla pre-acordada con Alberto): L-i + cross-encoder** (sustituye
al LLM-rerank; antecedente DEC-016b re-litigable: sus condiciones de descarte ya no existen).
Diseño v4 (criterio §3 endurecido: atribución por context-diff + guardia de margen en ganancias
+ shadow-rerank del baseline) TRANSFIERE al lever redefinido; artefactos `evals/s60_*` +
`evals/_s60_*` (diseños, local). **Ventana de freeze del corpus ABIERTA** (fingerprint 25.090).

## Qué sigue (orden vigente)

1. **(s61) Lever REDEFINIDO: L-i + cross-encoder (rerank-2.5) — diseño compacto + dúo FRESCO
   antes de build** (Protocolo 3; retrieval = cross-model innegociable). Transfiere de
   `evals/_s60_lever_design_FINAL.md` (v4): criterio §3 (Δ_net solo sobre movers
   context-cambiado · guardia de margen en ganancias [modal ≥4/5 o vínculo mecanístico] ·
   precisión regla-1 · **shadow-rerank del baseline en la sesión del A/B** — el dado vive en el
   brazo viejo), smokes (no-model/cat011, latencia p95 ≤1.3×), manifest con ef=120 capturado.
   Nuevo en el diseño: re-litigación formal de DEC-016b (condiciones disueltas), latencia/coste
   del cross-encoder, qué pasa con las instrucciones de dominio del LLM-rerank (multi-modelo /
   intents; diagramas MOOT por #45), y los 4-8 golds donde el corte-a-50 sí muerde. Secuencia:
   diseño+dúo → rebase L-i + swap reranker tras flag → gates → A/B K=5 vs baseline s58 →
   tabla §3 → held-out bajo R si SHIP. **El A/B exige el shadow-rerank pre-registrado (r2-X1:
   conservador, no-exonerante).** Plan B vivo: gate-0 del MERGE v4 (variantes congeladas) si el
   cross-encoder cae en diseño/gates; 2×2 generación (s58b) detrás.
2. **Tras un lever shipped: confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` bajo el
   PREREG (C1/C2 + cláusula R firmadas).
3. **Después del ciclo:** corpus nuevo (Aritech completo / Kidde resto / Ziton-GST; método en
   `docs/CORPUS_FIRESECURITYPRODUCTS.md`). **Freeze-contract:** ninguna ingesta dentro de la
   ventana baseline→A/B→held-out — y antes de ingerir, resolver TECH_DEBT #44 (el escritor de
   `category` sembraría más basura) y definir el contrato de #45 (diagramas, si se re-puebla).
   Paralelo menor vivo: hp009 / TECH_DEBT #43 (identidad de variantes).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
