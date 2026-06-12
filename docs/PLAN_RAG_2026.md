# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 12 jun 2026 (s65, DEC-046 — capa B de #43 CERRADA: backfill de identidad de los lotes
> s55/s58 [103 filas + 2.040 chunks enlazados], 86 manufacturer corregidos, 80 revisiones
> basura a NULL, 164 docs sin contenido re-clasificados [90 retired + 74 needs_review=cola];
> #43 COMPLETO).
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

## Estado actual (s65 — 12 jun 2026)

**s65 (DEC-046): capa B de #43 CERRADA — el item #43 queda COMPLETO (A s63 · B s65).**
Higiene de identidad ejecutada con plan congelado y GO explícito de Alberto: **A1** backfill
de los lotes s55/s58 — 103 filas nuevas en `documents` + 1 enlace + **2.040 chunks enlazados**
(quedan 25 huérfanos residuales honestos: 8 sources del canal "Otros" sin marca demostrable);
los chunks Aritech/Kidde/Edwards ahora **citan revisión** (r004/r005…) y entran al lifecycle.
**A2** 86 manufacturer corregidos por evidencia (85 en documents [Detnov→Argus/Securiton/
Spectrex/Pfannenberg…, Notifier→Xtralis] + 8 chunks MAD565 Spectrex→Detnov). **A3** 80
revisiones-basura de parser → NULL (el generador ya no puede citar "rev io"). **A4** las 165
filas `active` sin contenido re-clasificadas (90 retired [descartes de idioma/duplicados-
fantasma] + 74 **needs_review = cola estructurada de re-ingesta** para la ingesta grande).
Guardarraíl: pools 38/39 byte-idénticos + hp020 (esperado) idéntico + cat011 reclasificado
dado-de-red-en-BEFORE con evidencia histórica s64 (pool 40 estable ×3); invariante A4 PASS;
279 tests. Colaterales cazados: falso-STOP del assert global del runner (corregido a scope-
del-plan: los inactivos s64 tienen chunks POR contrato) y **bug de paginación de
`get_available_manufacturers`** (cap PostgREST 1000 con 1.170 docs — fix + test; catálogo
26→**30 marcas**). Dúo: sub-agente 13/13 + cross-model 7/7, 0 FP. DEC-046; narración HISTORY.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5) → generador `claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles; 25 huérfanos
residuales) / 1.170 docs {active 998 · superseded 3 · needs_review 79 · retired 90} / 31
marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035; **catálogo
de fabricantes 30 marcas** tras el backfill s65 + fix de paginación). **⚠️ Contratos rotos por
el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120,
default mantener); ventana de freeze del corpus: CERRADA (s64); fingerprint con dimensión
lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría. Baseline s58 = referencia histórica; **el próximo ciclo
de eval re-freeze** (el corpus efectivo cambió en s64: 3 docs fuera por lifecycle). Lever CE
preservado en `s61-lever-code-ROLLBACKED` (revisita condicional, punto 2).

## Qué sigue (orden vigente)

1. **Revisita condicional del lever CE:** re-gate ~$2 con el filtro de series ya en prod — el
   mecanismo cat012 (hermanos) está cerrado río arriba; techo honesto +1-frágil (hp001 es
   frontera de pool, irrecuperable por reranker).
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
