# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 12 jun 2026 (s66, DEC-047 — re-gate del lever CE = GO con scope re-decidido a CE-PURO
> [swap del reranker tras flag, sin L-i]: D1 6/6 + D2′ 0 pérdidas atribuibles + CE
> determinista 39/39; falso-STOP de cat018 enmendado pre-paso-B con evidencia s63;
> A/B en s67 por decisión de Alberto).
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

## Estado actual (s66 — 12 jun 2026)

**s66 (DEC-047): re-gate del lever CE = GO — la revisita condicional (DEC-042e) ejecutada
con scope RE-DECIDIDO a CE-PURO.** Alberto confirmó (4 opciones en la mesa) re-scopear el
lever de {L-i+CE} a **CE-puro**: swap del reranker tras flag (`RERANKER_BACKEND`, dispatch
Y1 = CE solo sin `target_models`) sobre el retriever de main INTACTO — L-i archivado (su
upside demostrado se evaporó: hp001 volvió al pool vía s64 SIN L-i y es frontera-de-pool;
cat012 capturado río arriba por s63; rebase +315 líneas en zona caliente sin upside
pendiente; branch `s59-lever-code-ROLLBACKED` vivo, renace en el ciclo
profundidad-del-canal). Gate con probes CONGELADAS pre-paso-A (X1: anclas de cat018
extraídas del gold_store y verificadas contra sustento real ANTES de cualquier retrieve) y
**paridad-control** (pérdida ATRIBUIBLE := en-pool ∧ en-vista-LLM ∧ ¬en-vista-CE; UNA
pérdida atribuible de un SHIP s63 = NO-GO): **D1 6/6 unánimes retienen sustento · D2′ 0
pérdidas atribuibles (cat012 4/4 hechos — el mecanismo hermanos cerrado por s63 CONFIRMADO
empíricamente bajo CE; cat018 h1+h4) · instrumento limpio (CE determinista 39/39 +
orden-insensible 7/7 + 0 chunks sub-0.4)**. hp001 resolvió INFORMATIVA por branch
pre-registrada ('candado' en pool y AMBAS vistas; '2222' fuera de pool — frontera
re-confirmada). El precheck disparó **falso-STOP en cat018** (mis anclas sobre-especificadas
vs lo que el PASS s63 realmente sirvió — h1+h4) → enmienda pre-paso-B APROBADA por Alberto
con evidencia (frozen s63). Dado del LLM re-medido HOY: 12/39 votos no-unánimes (2× 1/1/1).
Latencia rerank CE p95 0.84s vs LLM 2.86s (~3.4×). Coste real ~$4.5 — el "~$2" heredaba la
subestimación s61 (X4). Dúo r1: sub-agente 8/8 + cross-model GPT-5.5 5/5, **0 FP** (F1
refutó mi premisa "hp001 irrecuperable" contra s64). Build: transplante limpio de 5
archivos desde `s61-lever-code-ROLLBACKED`, SIN `retriever.py`; 290 tests. **El GO
habilita pero NO autoriza el A/B (DEC-016b) — Alberto: A/B en s67.** DEC-047; HISTORY.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5; dispatcher `RERANKER_BACKEND` default `llm` = inerte — el swap a
CE Voyage está gateado-GO s66, pendiente de A/B) → generador `claude-sonnet-4-6` (temp=0,
`max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles; 25 huérfanos
residuales) / 1.170 docs {active 998 · superseded 3 · needs_review 79 · retired 90} / 31
marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035; **catálogo
de fabricantes 30 marcas** tras el backfill s65 + fix de paginación). **⚠️ Contratos rotos por
el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120,
default mantener); ventana de freeze del corpus: CERRADA (s64); fingerprint con dimensión
lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría. Baseline s58 = referencia histórica; **el próximo ciclo
de eval re-freeze** (el corpus efectivo cambió en s64: 3 docs fuera por lifecycle) — el A/B
del CE (punto 1) lo incluye. Re-gate CE: **GO** (s66); build en rama `eval/s66-ce-regate`.

## Qué sigue (orden vigente)

1. **A/B del swap CE (s67, autorizado el rumbo por Alberto en s66):** mini-diseño propio
   (pairing por VISTA-del-generador idéntica — firma F1-s61; bajo mismo-pool el
   shadow-rerank pierde su rol, el dado del LLM se mide con los votos n=3 del gate) + dúo
   FRESCO + **re-freeze del baseline** (pendiente de todos modos) + brazo CE K=5; manifest
   honesto de bvg (backend despachado) re-aplicado a mano sobre main (+70 divergidas).
   Criterio §3-v4 transferido + **F7 endurecida**: GRIS-estable → recomendación pre-escrita
   SHIP-por-estabilidad (beneficio NO-end-to-end: determinismo [dado LLM 12/39 hoy],
   latencia ~3.4×, coste ~15×; SOLO path sin-target_models, Y1). **Ventana X2 del GO:**
   vale con fingerprints idénticos a los del gate (corpus+registry+proconfig+modelos, en
   `s66_gate_report.yaml:meta`) — drift material → re-gate ~$5. Coste ~$40-60 (marginal
   atribuible al CE ~$20-30). Techo end-to-end honesto: ~+0/+1-frágil.
2. **Corpus nuevo (Aritech/Kidde/Ziton-GST).** Antes de ingerir, los 3 prerrequisitos:
   **#44** (contrato de category — el escritor sigue sembrando) + **contrato #45** (diagramas)
   + **contrato de identidad/supersesión EN INGESTA**: el flujo debe CREAR fila en `documents`
   (hoy `resolve_document_id` casa pero no crea — el hueco que s65 backfilleó) **prefiriendo
   filas active al casar** (F2 s65: re-ingestar un doc retired lo reactiva conscientemente,
   no cuelga chunks de una fila inactiva) + sha-check contra lo existente (DEC-045a). La
   **cola curada vive en los 74 `needs_review`** de s65 (inventario en
   `evals/s65_capab_inventory.yaml`) — candidatos ES/EN no migrados del corpus viejo.
3. **Pendientes menores del ciclo s65:** 25 chunks huérfanos residuales (8 sources canal
   "Otros" sin marca — curación con Alberto o quedan como gap honesto); fragilidad de
   `_get_all_known_manufacturers` (TECH_DEBT #47, medido: la lista del diversify = 2 marcas).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día);
language/revision_date/document_family masivos (B4/B5 s65 → contrato de ingesta, no
backfill); TECH_DEBT #40 (recall-gate CI), #47 (lista de manufacturers del diversify).
