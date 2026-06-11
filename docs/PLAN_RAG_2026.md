# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 11 jun 2026 (s62, DEC-043 — el audit #43 REFUTÓ "near-dups" (CORRECCIÓN a DEC-042): el
> mecanismo real es identidad producto↔serie + metadata rota de lotes viejos; branch de
> Alberto: ciclo A = registry de series en el seam s55 + filtro exacto-o-serie).
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

## Estado actual (s62 — 11 jun 2026)

**s62 (DEC-043):** el AUDIT #43 (read-only, `scripts/s62_audit43.py` + verificaciones regla-C)
**REFUTÓ el diagnóstico "near-dups" de s61** (CORRECCIÓN canonizada en DEC-042): J_doc entre los
3 manuales AM-8200 = 0.001-0.032 — no hay duplicación textual; el mecanismo real de cat012 es
**identidad producto↔serie** (el filtro de modelo matchea por substring → "am8200" deja pasar a
los HERMANOS 8200G/N, y el CE llena el top-5 con sus secciones conceptualmente equivalentes,
expulsando la tabla del producto correcto). Mix real de la deuda (diagnóstico
`evals/s62_audit43_diagnosis.md`): **capa A** identidad producto↔serie (daño MEDIDO: cat012-gate
+ antecedentes DEC-032/hp003) · **capa B** metadata de identidad rota en lotes viejos (≥15 docs
Spectrex/Pfannenberg bajo manufacturer=Detnov; model=unknown masivo; revision con basura de
parser; document_family=filename; supersedes 0/1065; 165 docs sin chunks) · **capa C** near-dup
textual MARGINAL (1 revisión MAD-472 V2 [toca cat024] + 1 FAQ; los 41 grupos ES/EN son legítimos
y se CONSERVAN). La "supersesión" retroactiva quedó SIN MATERIA → contrato al flujo de ingesta
futura. **Branch (Alberto, 4 opciones): CICLO A** — registry de series en `config/manufacturers`
(seam s55, cero DDL) + filtro de 3 niveles (sin entrada → comportamiento actual; con entrada →
mismo-producto o doc-de-serie; hermanos NO pasan), capa B arreglada DIRIGIDA donde el ciclo la
toque, C de propina. Diseño v1 en `evals/_s62_seriesA_design.md` (local, PRE-dúo). Lección #32
al log de bias (mecanismo canonizado sin medir en un diagnóstico post-mortem).

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre **`chunks_v2` = 25.090 chunks / 1.012
docs / 31 marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035).
**⚠️ Contratos rotos por el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Prod sin
cambios de código desde s58; ventana DB ABIERTA (ef_search=120, default mantener); **ventana de
freeze del corpus ABIERTA** (fingerprint 25.090).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría, baseline s58 congelado (PASS-control 10 / 6 unánimes);
cláusula R FIRMADA (s59b). **s61 (DEC-042, resumen):** lever L-i+cross-encoder construido tras
flag (`RERANKER_BACKEND`, 237 tests) y PARADO en gate pre-A/B (NO-GO por D2 sin pagar A/B);
hallazgos de instrumento: **drift de `embed_query` 0.003 entre sesiones** (hp001
frontera-frágil, irrecuperable por reranker) + CE determinista/5×rápido/15×barato con D1 limpio.
Lever preservado en `s61-lever-code-ROLLBACKED` (revisita condicionada); plan B MERGE descartado
con datos. Narración en HISTORY; mecánica en DEC-042 (+CORRECCIÓN s62).

## Qué sigue (orden vigente)

1. **(s63) Ciclo A — dúo FRESCO sobre el diseño v1** (`evals/_s62_seriesA_design.md`; corpus/
   retrieval = zona de dolor → cross-model INNEGOCIABLE) → v2 → **build** (registry `series` en
   `config/manufacturers/*.yaml` [seam s55, cero DDL] + `_filter_to_query_models` de 3 niveles:
   sin entrada de registry → comportamiento ACTUAL intacto; con entrada → mismo-producto o
   doc-de-serie, hermanos NO pasan; fail-open <3 se mantiene) → **gate barato** (filtro-nuevo vs
   filtro-actual, MISMO embedding por par [neutraliza el drift 0.003], probes s61 reutilizables;
   condiciones: PASS-control retiene sustento · cat012-mecanismo se cierra · hp003/#11e no
   regresan) → **A/B K=5 vs baseline s58** (cambio de código puro — baseline comparable;
   instrumentos s61: firma enmendada + shadow-rerank) → held-out bajo R si SHIP. **La curación
   inicial de series (AM-8200{,G,N} · CAD-150{,-8,R} · Vesta latente) se valida con Alberto
   ANTES del gate** (conocimiento de dominio con `evidence:` por entrada). De propina: marcar
   `superseded` el MAD-472 V1 (capa C, cat024). Capa B dirigida solo donde el ciclo la toque.
2. **Capa B completa (ciclo de higiene propio, tras A):** metadata de lotes viejos —
   manufacturer mal asignado (≥15 docs), model=unknown masivo, revision-basura de parser,
   document_family=filename, 165 docs sin chunks. Extender el seam s55 hacia atrás; mini-eval
   de no-regresión (los filtros por manufacturer/model SÍ tocan retrieval).
3. **Revisita condicional del lever CE** (tras ciclo A): re-gate ~$2 con el filtro nuevo —
   el mecanismo cat012 (hermanos) quedaría cerrado río arriba; techo honesto +1-frágil.
4. **Tras un lever shipped: confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` (PREREG).
5. **Después:** corpus nuevo (Aritech/Kidde/Ziton-GST). Antes de ingerir: #44 + contrato #45 +
   **contrato de supersesión EN EL FLUJO DE INGESTA** (sin materia retroactiva — audit s62: 1
   caso en 1.065 docs; las revisiones nuevas de docs existentes son las que lo necesitarán).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
