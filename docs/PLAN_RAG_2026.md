# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 12 jun 2026 (s63, DEC-044 — CICLO A SHIPPED, PR #70: registry de series + filtro de 3
> niveles + diversify corregido EN PROD; dev Δ_net=+2 [cat012 y cat018 a PASS]; held-out
> corrida única DÉBIL-aceptada por Alberto).
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

## Estado actual (s63 — 12 jun 2026)

**s63 (DEC-044): CICLO A SHIPPED (PR #70, mergeado por Alberto).** El registry de series
(`config/manufacturers/*.yaml`, seam s55, cero DDL) + el filtro de 3 niveles + diversify
corregido están **EN PROD** (flag `SERIES_REGISTRY_ENABLED`, default ON; kill-switch en Railway
sin redeploy). Cierra la capa A de #43 en ambas direcciones: d1 (la query del base ya no
arrastra hermanos — cat012) y d2 (la variante VE los docs de serie — fetch dirigido en
diversify). Medido con el esquema pre-registrado (`evals/s63_gate_spec.yaml`): **gate G1-G8
GO** (cat012 pool 28→9 100% producto correcto; 38/42 queries byte-a-byte invariantes) →
**A/B dual-arm con pairing K=5: SHIP Δ_net=+2** (cat012 PARCIAL→PASS · cat018 FALLO→PASS ·
0 regresiones · 37/39 Δ:=0 estructural) → **held-out corrida ÚNICA (cláusula R, 1ª ejecución):
DÉBIL Δ=0 ACEPTADO por Alberto** (11/12 idénticos; ho008/CAD-171 modal IGUAL con la vista
ganando los docs de serie; 0 fabricaciones). Población curada por Alberto con `evidence:`
anclada en chunks_v2 (AM-8200 sin shared; Vesta con MC-380 rev-c + MS-416-2026 vigentes).
Dúo ×2 rondas frescas (36 findings, 0 FP netos); lección #33 al log de bias (la vigencia de un
doc se ancla en contenido, no en su tabla de revisiones interna — corrección de Alberto).
Instrumentos nuevos reutilizables: embed-cache por par (`EMBED_CACHE_PATH`), pairing por pool,
`INCLUDE_HELDOUT`, convergencia anti-dado-de-red. Narración en HISTORY; mecánica en DEC-044.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → **filtro de modelos series-aware (3
niveles, DEC-044)** → rerank LLM Sonnet (top-5) → generador `claude-sonnet-4-6` (temp=0,
`max_tokens=2048`) sobre **`chunks_v2` = 25.090 chunks / 1.012 docs / 31 marcas / 587 modelos**
(contextual-retrieval 100%; identidad data-driven, DEC-035). **⚠️ Contratos rotos por el SWAP
s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120, default
mantener); **ventana de freeze del corpus: el ciclo A/B→held-out está CERRADO** → puede
cerrarse al ejecutar el lifecycle #46 (la ingesta vuelve a estar permitida tras #46/#44/#45).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo — la corrida única s63
NO lo rompe: no se itera contra ho008), taxonomía CONGELADA (DEC-033), juez GPT-5.5 +
K-mayoría. Baseline s58 congelado sigue de referencia histórica; el próximo ciclo re-freeze
(el corpus cambiará con la ingesta). Lever CE preservado en `s61-lever-code-ROLLBACKED`
(revisita condicional, punto 3).

## Qué sigue (orden vigente)

1. **Lifecycle post-ciclo-A (TECH_DEBT #46, barato):** marcar `superseded` los 3 docs
   sustituidos (MAD-472 V1 [cat024] · MC-380 rev-b · MS-416 viejo solo-250) con lectura de
   pool antes/después + **re-ingestar el MS-416 actualizado del portal** (Detnov actualizó el
   PDF in-place; lo ingestado difiere) — primer caso REAL del contrato de supersesión en el
   flujo de ingesta. Al ejecutarlo, cerrar la ventana de freeze (re-fingerprint).
2. **Capa B completa (ciclo de higiene propio):** metadata de lotes viejos — manufacturer mal
   asignado (≥15 docs), model=unknown masivo, revision-basura de parser,
   document_family=filename, 165 docs sin chunks. Extender el seam s55 hacia atrás; mini-eval
   de no-regresión (los filtros por manufacturer/model SÍ tocan retrieval).
3. **Revisita condicional del lever CE:** re-gate ~$2 con el filtro de series ya en prod — el
   mecanismo cat012 (hermanos) está cerrado río arriba; techo honesto +1-frágil (hp001 es
   frontera de pool, irrecuperable por reranker).
4. **Después:** corpus nuevo (Aritech/Kidde/Ziton-GST). Antes de ingerir: #44 + contrato #45 +
   contrato de supersesión en ingesta (parcialmente ejercitado en el punto 1).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
