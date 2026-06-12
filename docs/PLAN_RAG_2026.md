# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 12 jun 2026 (s67b, DEC-049 — re-priorización post-A/B confirmada por Alberto: **el
> ciclo del canal vectorial pasa a punto 1** ("el elefante en la habitación"); corpus
> DIFERIDO demand-driven hasta chatbot estable (la meta 30+ fabricantes SIGUE, en fase
> posterior); diagramas partidos en datos-paralelizable + cableado-post-canal. s67 =
> DEC-048: A/B del CE = ROLLBACK pre-registrado; baseline del ruler = `s67base`).
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

## Estado actual (s67 — 12 jun 2026)

**s67 (DEC-048): A/B del swap CE ejecutado (GO de Alberto, ~$30 real vs ~$40-60 estimado)
= ROLLBACK por la tabla pre-registrada — el lever CE queda ARCHIVADO con evidencia
end-to-end.** Diseño v2 post-dúo r1 (sub-agente 7/7 + cross-model GPT-5.5 6/6, **0 FP**;
F1 ALTA cerró el hueco dado-mediado en la clasificación de movers [freeze-A puede ser
4ª-vista aun con gate 3/3]; F2 re-derivó el dado del LLM contra el artefacto: **11/39
no-unánimes** [9× 2/1 + 2× 1/1/1; 24 unánimes con rerank + 4 short-circuit vacuos] — el
"12/39" que circulaba era falso, patrón bias #35). Día D bajo ventana verificada (X2 7/7
+ X1 código pinneado al build): **el assert (i) cazó embed-drift server-side ANTES de
pagar generación** (3/39 pools frontera, 1 chunk in/out; cat019 expuso además la frontera
de redondeo del `round(sim,2)` — la firma fue FIEL al header real del generador; la
reordenación F3/X6 del dúo pagó su valor) → **re-gate ~$5 con `EMBED_CACHE_PATH`
compartido = GO** (`s67_gate_*`; **el cache ancla gate y A/B a la MISMA ventana de
vectores POR CONSTRUCCIÓN** — el riesgo F3 muere estructuralmente; patrón nuevo para todo
ciclo de eval) → brazo LLM 195/195 gen+juicios · brazo CE 175/175 (pairing 4 = los
short-circuit) · herencia `shared_from` · juez servido idéntico entre brazos
(`gpt-5.5-2026-04-23`) · 0 errores. **Resultado: Δ_net=0 (techo +0/+1 confirmado; cat012
GANA PARCIAL→PASS pero 3/5 sin margen — no cuenta, coherente con el gate) · SIN regla-1
(0 PASS perdidos atribuibles; cat023 dado-excluido, control=1 ok) · PERO F_post 8 >
F_base 5 (cat007/cat017/hp001/hp014 PARCIAL→FALLO; hp001 ATRIBUIBLE-operacional — el
gold-frontera eterno pierde su PARCIAL bajo CE) + 2 regresiones de conducta
(cat016/hp014 answer→admit) = dos condiciones independientes de ROLLBACK.** El beneficio
instrumento/prod del CE (determinismo, latencia rerank p95 0.81s vs 3.29s, coste ~15×) NO
se compra al precio de degradar la cola PARCIAL→FALLO. El dado del rerank LLM (11/39)
sigue como defecto de producto DECLARADO — se re-ataca en el ciclo profundidad-del-canal
(donde renace L-i), no con este swap. **El re-freeze `s67base` SUSTITUYE a frozen-s58
como baseline del ruler: 10/39 PASS-control (5 unánimes 5/5) · 4 K-INESTABLES
(cat009/cat012/hp004/hp007) · residual 25 con atribución.** Flag `RERANKER_BACKEND`
queda en main default `llm` (inerte; dispatcher + manifest honesto de bvg = instrumentos
permanentes); Railway intacto. DEC-048; HISTORY.

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

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo, intacto en s67),
taxonomía CONGELADA (DEC-033), juez GPT-5.5 + K-mayoría. **Baseline VIGENTE = re-freeze
`s67base`** (12 jun 2026: 10/39 PASS-control · 5 unánimes · 4 K-INESTABLES; manifest
completo + `s67_embed_cache.json` como pin de embeddings); frozen-s58 = referencia
histórica muerta. Próximo freeze: correr SIEMPRE con `EMBED_CACHE_PATH` (DEC-048c).

## Qué sigue (orden vigente — re-priorizado DEC-049, 12 jun 2026)

1. **CICLO DEL CANAL VECTORIAL (s68+) — el lever prioritario** ("el elefante en la
   habitación", Alberto; 4 datos lo sostienen: canal principal devuelve 0 en ~85% de
   queries [DEC-040] · el embedding SÍ encuentra los hechos, rank 7-110 · hechos en rank
   51-70 medidos 4× [DEC-042d] · corte-a-50 muerde 9/39; + la lección de 3 ciclos de
   reranker = 0: reordenar lo que entra no arregla lo que NO entra). **Paso 0: AUDIT de
   dimensionamiento** ($0-barato; instrumentos existentes: funnel s58b + diagnosis-ranks
   s59 + atribución s67base) con DOS preguntas pre-registradas: (a) cuánto del residual
   es alcanzable río arriba (canal: ranks/corte/category-boost) vs (b) cuánto es
   **calidad-de-chunk** (extracción/fragmentación — los 9 INDETERMINADO-solo-débiles;
   lever #10 post-hoc) — si domina (b), el techo del canal baja y se sabe ANTES de
   construir. → diseño con dúo → levers según audit: **#44 re-etiquetado de category
   como BOOST** (no filtro duro — eso está medido como frágil; incluye el contrato del
   ESCRITOR, raíz) · **L-i renacido** (`s59-lever-code-ROLLBACKED`) · profundidad/corte.
   A/B vs `s67base` (embed-cache pin). **Riesgo declarado: redistribución de frontera
   (regla-1, pasó en s59)** — paridad-control + clasificación de dado ya existen.
2. **Re-gate del CE (~$5) SI el canal cambia los pools** (puerta DEC-048; sin promesa de
   revival — perdió la cola con paridad de información completa).
3. **Generación + cartera de levers (cada uno entra por gate/audit barato, DEC-016b):**
   A/B 2×2 {Sonnet/Opus}×{blurb} (pre-registrado s56) sobre el freeze post-canal ·
   **system prompt del generador** (no probado) · prompt del rerank-LLM (vs su dado
   11/39) · k/corte. El orden interno lo dan los audits, no se pre-supone.
4. **Diagramas (#45) — partido en dos (DEC-049d):** (a) **DATOS, paralelizable desde
   ya** en sesiones sueltas: mapeo por (documento, página) desde la tabla vieja (44.035
   chunks con diagrama allí vs 0/25.090 en v2 — nunca se extrajeron para v2) +
   extracción de faltantes + poblar `has_diagram`/`diagram_url`; **eval-inerte
   VERIFICADO** (before/after de pools por backfill — el fingerprint NO caza edits
   in-place, DEC-036e); (b) **CABLEADO de entrega al bot post-canal** (chunks confiables
   primero — si no, adjuntaríamos el diagrama equivocado).
5. **Corpus: DIFERIDO demand-driven hasta chatbot estable/robusto (decisión de negocio,
   DEC-049a).** Las 31 marcas actuales = las de uso frecuente de los técnicos; **la meta
   30+ fabricantes SIGUE, en fase posterior**. Un gap real (conversación con
   empresario/técnico, vía Excel inventario) reactiva la ingesta — y ENTONCES aplican los
   prerrequisitos: contrato del escritor #44 + #45 + identidad/supersesión EN INGESTA
   (crear fila + preferir active + sha-check, DEC-045a) + la cola de 74 `needs_review`.
6. **Pendientes menores s65:** 25 chunks huérfanos residuales; TECH_DEBT #47
   (`_get_all_known_manufacturers`).

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
