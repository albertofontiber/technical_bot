# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 11 jun 2026 (s61, DEC-042 — lever L-i+cross-encoder construido tras flag y parado en GATE
> (NO-GO pre-registrado, SIN pagar A/B); 2 mecanismos verificados + drift de embed_query
> medido; branch de Alberto: cerrar ciclo → atacar #43 supersesión/near-dups).
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

## Estado actual (s61 — 11 jun 2026)

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre **`chunks_v2` = 25.090 chunks / 1.012
docs / 31 marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035).
**⚠️ Contratos rotos por el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Prod sin
cambios de código desde s58; ventana DB ABIERTA (ef_search=120, `--reset` revierte; default
mantener — re-decidir dentro del ciclo #43, que re-mide corpus de todos modos).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría, baseline s58 congelado (PASS-control 10 / 6 unánimes);
cláusula R FIRMADA (s59b). **s61 (DEC-042): el lever redefinido (L-i + cross-encoder
rerank-2.5) se DISEÑÓ (v1→v3, dúo ×2 rondas: 28 findings, 1 FP), se CONSTRUYÓ tras flag
(`RERANKER_BACKEND`, default llm; dispatch condicional Y1: voyage SOLO sin target_models;
237 tests verdes) y se PARÓ en el GATE pre-A/B (NO-GO pre-registrado por D2, sin pagar A/B)**.
Mecanismos VERIFICADOS (no teorizados): **hp001 = pérdida de POOL** (chunk ganador s59 hoy en
rank 54/50 del canal vectorial; **drift de `embed_query` 0.003 ENTRE SESIONES medido** — 3er
decimal, no 7º; frontera-frágil de nacimiento, afecta a CUALQUIER reranker y al plan B) ·
**cat012 = efecto real del swap** (el CE de pares independientes llena el top-5 con
near-duplicates: la fórmula §11 en 3 REVISIONES del AM-8200 conviviendo = #43; el LLM
listwise diversificaba). D1 LIMPIO 0/6 (el swap no rompe el statu quo) · CE determinista
39/39 con header de paridad + 5× más rápido (p95 0.9s vs 5.1s) + ~15× más barato · corte-a-50
muerde 9/39 @ef120. **Branch (Alberto, 4 opciones en la mesa): cerrar ciclo sin A/B → atacar
la raíz #43.** Código del lever PRESERVADO en `s61-lever-code-ROLLBACKED` (build+gate+diseño;
revisita condicionada a #43 resuelto). Plan B (MERGE v4) DESCARTADO con datos (hereda hp001 y
conserva el dado del LLM). Artefactos `evals/s61_*` + diagnóstico `evals/s61_gate_diagnosis.md`.
**Ventana de freeze del corpus ABIERTA** (fingerprint 25.090).

## Qué sigue (orden vigente)

1. **(s62) Ciclo #43: identidad de variantes / near-duplicados del corpus — AUDIT primero
   (Protocolo 4), no build.** El gate s61 lo señaló como raíz: ediciones casi idénticas de una
   misma familia conviviendo (AM-8200 / 8200G Rv3 / 8200N RV4 — variantes hermanas + revisiones
   mezcladas, el modelo de datos no distingue ninguna de las dos) monopolizan el top-5 de
   cualquier reranker de pares y ensucian pools/atribución (cat009/cat012/hp011). Secuencia: (a) audit/dimensionado barato — cuántos docs con revisiones múltiples,
   cuántos near-dup chunks (umbral de similitud a declarar), qué golds tocan; (b) CONTRATO de
   supersesión — ⚠️ NO latest-wins naive: hp011/answer-con-conflicto y los conflictos ES↔US
   viven de que AMBAS variantes sobrevivan (la supersesión es por-doc-misma-edición-mismo-mercado);
   (c) diseño + dúo FRESCO (corpus = zona de dolor → cross-model INNEGOCIABLE); (d) ejecución
   medida en el RULER (la ventana de freeze está ABIERTA — este ciclo es EL momento de tocar
   corpus). Desbloquea la revisita del lever CE (preservado) y limpia hp011/cat009.
2. **Revisita condicional del lever CE** (tras #43): el NO-GO fue por D2; con near-dups
   tratados, re-correr el gate (pools nuevos + D1/D2) es barato (~$2). Si GO → A/B con techo
   honesto (+1-frágil: hp001 queda fuera del alcance de cualquier reranker — frontera+drift).
3. **Tras un lever shipped: confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` bajo el
   PREREG (C1/C2 + cláusula R firmadas).
4. **Después:** corpus nuevo (Aritech completo / Kidde resto / Ziton-GST; método en
   `docs/CORPUS_FIRESECURITYPRODUCTS.md`). Antes de ingerir: #44 (escritor de `category`) +
   contrato #45 (diagramas) + #43 resuelto (ingerir más revisiones sin supersesión = sembrar
   más near-dups).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
