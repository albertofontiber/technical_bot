# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 12 jun 2026 (s64, DEC-045 — lifecycle #46 CERRADO: contrato de supersesión poblado [3
> cadenas] + fix de re-entrada en diversify; la re-ingesta del MS-416 quedó SIN MATERIA
> [claim s63 refutada por SHA]; ventana de freeze CERRADA).
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

## Estado actual (s64 — 12 jun 2026)

**s64 (DEC-045): lifecycle #46 CERRADO.** El contrato de supersesión está **POBLADO por
primera vez** (3 cadenas: MAD-472 V1→V2 · MC-380 rev-b→rev-c · MS-416 2020→2026, con
status='superseded' + punteros; los 2 sucesores Detnov ganaron fila de identidad en
`documents` y sus 224 chunks quedaron enlazados → el generador ahora **cita 'rev c'**).
Guardarraíl pre-registrado completo: precheck de hechos-gold GO + pools before/after 39 dev
(C1: 0 docs viejos en pools; C3: 36/36 no-afectados byte-idénticos; cat024 pool 4→7) + smoke
del path real. **Fix estructural colateral**: los suplementos de diversify NO pasaban por el
lifecycle filter (re-entraban docs needs_review/superseded post-4b) → pre-filtro de universo
+ cinturón batch en ambos paths, 260 tests verdes. **La re-ingesta del MS-416 quedó SIN
MATERIA**: los 4 URLs del portal sirven byte-idéntico lo ingestado (SHA verificado; la claim
s63 "73pp difiere" fue cruce de identidades entre las dos ediciones → lección #34). Dúo
2 piezas: sub-agente 8/8 + cross-model 5/5, 0 FP. Apply autorizado explícito por Alberto
(el clasificador bloqueó la 1ª ejecución — freno correcto). Narración en HISTORY; DEC-045.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5) → generador `claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles) / 1.067 docs
{active 1059 · superseded 3 · needs_review 5} / 31 marcas / 587 modelos** (contextual-retrieval
100%; identidad data-driven, DEC-035). **⚠️ Contratos rotos por el SWAP s44, medidos:**
`category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120, default mantener);
**ventana de freeze del corpus: CERRADA (s64)** — la ingesta vuelve a estar permitida tras
#44/#45; el fingerprint de freeze ahora incluye la dimensión lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría. Baseline s58 = referencia histórica; **el próximo ciclo
de eval re-freeze** (el corpus efectivo cambió en s64: 3 docs fuera por lifecycle). Lever CE
preservado en `s61-lever-code-ROLLBACKED` (revisita condicional, punto 2).

## Qué sigue (orden vigente)

1. **Capa B completa (ciclo de higiene propio):** metadata de lotes viejos — manufacturer mal
   asignado (≥15 docs), model=unknown masivo, revision-basura de parser,
   document_family=filename, 165 docs sin chunks (y los lotes s55/s58 sin fila en `documents`
   — el backfill s64 de los 2 Detnov es el patrón a extender). Extender el seam s55 hacia
   atrás; mini-eval de no-regresión (los filtros por manufacturer/model SÍ tocan retrieval).
2. **Revisita condicional del lever CE:** re-gate ~$2 con el filtro de series ya en prod — el
   mecanismo cat012 (hermanos) está cerrado río arriba; techo honesto +1-frágil (hp001 es
   frontera de pool, irrecuperable por reranker).
3. **Corpus nuevo (Aritech/Kidde/Ziton-GST).** Antes de ingerir: #44 + contrato #45 +
   contrato de supersesión EN INGESTA (el retroactivo quedó poblado en s64 — DEC-045; el
   flujo de ingesta debe crear fila en `documents` + sha-check contra lo existente).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
