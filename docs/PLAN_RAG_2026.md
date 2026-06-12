# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 13 jun 2026 (s68 — sesión autónoma nocturna con GO de Alberto [$100; gasto real ~$7]:
> **ciclo del canal EJECUTADO punta a punta** = audit por-hecho (stamps expulsan del
> pool material que el canal sano rankea ≤50) → lever MERGE+L-i′ tras flag, dúo
> completo → **gate-0 NO-GO pre-registrado** (mecanismo y conversión CONFIRMADOS
> [cosine 12/12 al pool, 10/12 al top-5] pero re-baraja 9/10 PASS-control → el A/B no
> se paga, DEC-016b) + **chunk-quality DESCARTADA como cuello con dato** (bloque-2:
> chunks servidos sanos — el residual no-retrieval es GENERACIÓN). DEC-050. s67b =
> DEC-049 [orden vigente]; s67 = DEC-048 [CE ROLLBACK; baseline `s67base`]).
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

## Estado actual (s68 — 13 jun 2026)

**s68 (DEC-050, sesión autónoma nocturna [GO de Alberto: $100; gasto real ~$7; prod y
held-out intactos]): el CICLO DEL CANAL VECTORIAL (punto 1 de DEC-049) se ejecutó punta
a punta — audit → lever → gate-0 NO-GO pre-registrado + chunk-quality descartada.**
**(a) AUDIT por-hecho** (`s68_audit_canal.yaml`; 22 golds residual-answer, 28 hechos
fuertes): el mecanismo dominante del lado-retrieval NO es profundidad (rank 51-110: solo
2 hechos) sino la MEZCLA del pool — **10 hechos con rank vectorial ≤50 (canal sano)
expulsados del pool servido por keyword-stamps planos** (0.8 ×12-28 por pool encima del
coseno real 0.52-0.68 del winner); 11 hechos YA-servidos-que-fallan + 9 golds
solo-débiles (≈50% del residual NO es retrieval); 3 sospecha-gap. **(b) Lever MERGE+L-i′**
(revivió el plan-B congelado de s60 con el sustrato re-verificado): diseño v6.1 con dúo
r1 completo (sub-agente **12/12 ALTA** [F1 banda-de-dado en m7; F3 L-i′=réplica exacta
s59; F6 (d2) MUERTA — sustituía el interleave intocable del 5a; F7 hp001/hp011 fuera del
techo k=50] + cross-model **6/6 CRÍTICO** [Y1: rama de 3c-i pre-registrada ANTES de
medir — 0 filas verificado, se eliminan], **0 FP**, 18/18); build tras flag
`MERGE_STRATEGY` (stamps|quota|cosine, default stamps = main bit-idéntico; PARIDAD
verificada 39/39); 310 tests. **(c) GATE-0 ($5): NO-GO por la letra** — el mecanismo y
la conversión quedaron CONFIRMADOS (cosine captura 12/12 hechos alcanzables al pool y
**10/12 llegan al top-5 modal** — hp008 4/4; "recall no convierte" NO aplicó) PERO
re-baraja el top-5 de **9/10 PASS-control** (cat022-quota overlap 0/5; cat010-cosine
2/5) → la condición dura (≤1 fuera-de-banda) ni de lejos; **el prior DEC-041(A) se
confirmó y el A/B (~$25-30) NO se pagó** (calibración DEC-016b). El flag queda en main
default `stamps` (inerte, instrumento como el dispatcher CE). **(d) Bloque-2 ($0):
chunk-quality DESCARTADA como cuello con dato** — los chunks servidos están SANOS (lens
1.1-3.1K, 0 fragmentos, 100% blurb, legibles) ⇒ **el ~50% no-retrieval del residual es
GENERACIÓN/síntesis**, no extracción (la pregunta-chunks de Alberto respondida; lever
#10 al fondo del backlog). Candidata FUTURA declarada con forking-path (nació de mirar
el gate-0): variante ADITIVA del merge (stamps intactos + cosenos del canal sano solo
en slots libres) — exige ciclo propio con dúo y pre-registro. DEC-050; HISTORY.

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

## Qué sigue (orden vigente — DEC-049 con el punto 1 EJECUTADO en s68)

0. **Decisión de Alberto al despertar (s68 dejó TODO preparado, nada shippeado):**
   mergear el PR de s68 (audit + lever-NO-GO + canon; cero cambio de comportamiento:
   flag default `stamps`) y confirmar el orden de abajo.
1. **GENERACIÓN (sube del punto 3 — ahora con MÁS peso por el dato del bloque-2: el
   ~50% no-retrieval del residual ES generación/síntesis con chunks sanos):** A/B 2×2
   {Sonnet/Opus}×{blurb} (pre-registrado s56, sobre `s67base` — el freeze sigue válido:
   el canal NO cambió) · **system prompt del generador** (no probado; los 11
   ya-servidos-que-fallan son su diana medida) · prompt del rerank-LLM (dado 11/39 +
   hp018: su hecho estaba EN el pool y el rerank no lo sube ni con pool sano). Cada
   lever por gate/audit barato (DEC-016b).
2. **Retrieval río-arriba (si Alberto quiere re-atacar tras el NO-GO):** candidata
   ADITIVA del merge (stamps intactos + cosenos del canal sano en slots libres —
   **declarada con forking-path: nació de mirar el gate-0 s68**; ciclo propio con dúo)
   · profundidad k>50 (hp001 rank 54 / hp011 rank 65 — lever separado DEC-049b) ·
   **#44 category-como-BOOST** (el re-etiquetado masivo; el contrato del ESCRITOR
   incluido). El re-gate del CE quedó SIN MATERIA (el canal no cambió pools).
3. **Diagramas (#45) — partido en dos (DEC-049d):** (a) **DATOS, paralelizable desde
   ya** en sesiones sueltas: mapeo por (documento, página) desde la tabla vieja (44.035
   chunks con diagrama allí vs 0/25.090 en v2 — nunca se extrajeron para v2) +
   extracción de faltantes + poblar `has_diagram`/`diagram_url`; **eval-inerte
   VERIFICADO** (before/after de pools por backfill — el fingerprint NO caza edits
   in-place, DEC-036e); (b) **CABLEADO de entrega al bot post-canal** (chunks confiables
   primero — si no, adjuntaríamos el diagrama equivocado).
4. **Corpus: DIFERIDO demand-driven hasta chatbot estable/robusto (decisión de negocio,
   DEC-049a).** Las 31 marcas actuales = las de uso frecuente de los técnicos; **la meta
   30+ fabricantes SIGUE, en fase posterior**. Un gap real (conversación con
   empresario/técnico, vía Excel inventario) reactiva la ingesta — y ENTONCES aplican los
   prerrequisitos: contrato del escritor #44 + #45 + identidad/supersesión EN INGESTA
   (crear fila + preferir active + sha-check, DEC-045a) + la cola de 74 `needs_review`.
   Los 3 sospecha-gap del audit s68 (cat017/hp010/hp012) alimentan esta cola.
5. **Pendientes menores s65:** 25 chunks huérfanos residuales; TECH_DEBT #47
   (`_get_all_known_manufacturers`); lever #10 (extracción) AL FONDO — chunk-quality
   descartada como cuello con dato (s68 bloque-2).

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
