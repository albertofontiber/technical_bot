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

## Estado actual (s59 — 10 jun 2026)

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`) sobre **`chunks_v2` = 25.090 chunks / 1.012
docs / 31 marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035).
**⚠️ Diagnóstico s59 (DEC-040): el canal vectorial principal está MUERTO en prod para el ~85%
de las queries** — `chunks_v2.category` tiene 0 filas de la taxonomía canónica (SWAP s44 cambió
el contrato de la columna en silencio) → `filter_category` devuelve 0 SIEMPRE y el pool vive del
broad-5 + canales léxicos; además `hnsw.ef_search=40` < k=50. El FIX (lever L-i) está construido,
gateado y MEDIDO — veredicto pre-registrado **ROLLBACK** (ver abajo): NO está en prod.

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo), taxonomía CONGELADA
(DEC-033), juez GPT-5.5 + K-mayoría, baseline s58 congelado (PASS-control fijado 10 / 6 unánimes).
**s59 EJECUTADO de punta a punta (DEC-040):** (a) dimensionamiento — los 14 hechos RECALL tienen
rank vectorial exacto 7–32 (10/14 ≤50): el embedding YA los encuentra, el filtro muerto los tiraba;
(b) lever "canal vectorial sano" diseñado con dúo ×2 rondas + focal (5b diferido; L-ii ef_search
PENDIENTE de autorización de Alberto — el permission-mode denegó el ALTER a prod);
(c) medición completa: **gate-1 11/11 · gate-2 RECALL-fuertes 14→3 (la mayoría hasta el TOP-5) ·
A/B K=5: Δ_net=0 con redistribución (cat020 FALLO→PASS, hp001 PARCIAL→PASS vs cat005/9/10
PASS→PARCIAL 3-2 frontera + hp018) → VEREDICTO §3: ROLLBACK regla 1 (cat010 unánime cayó)**.
El criterio duro pre-registrado funcionó: sin él esto se shipeaba como "empate con ganancias".
Código del lever PRESERVADO en branch `s59-lever-code-ROLLBACKED` (con sus 5 tests); artefactos
`evals/s59_*` versionados; instrumentos nuevos reutilizables (`s59_recall_diagnosis.py`,
`s59_gate1.py --alter/--reset`, `s59_fabrications.py` K-formato, `s59_ab_verdict.py`, runner
parametrizado `BVG_RUN_ID`). **Cláusula R del PREREG (held-out para levers de retrieval) escrita
pre-datos — PENDIENTE DE FIRMA; el held-out sigue BLOQUEADO.** **Ventana de freeze del corpus
ABIERTA** (fingerprint s58 intacto: 25.090).

## Qué sigue (orden vigente)

1. **(s60) Branch del siguiente lever — DECISIÓN DE ALBERTO (no pre-elegido), con el cuadro
   s59 en la mesa:** (i) **lever de MERGE/ranking** (pre-señalado por el dúo y por el resultado:
   el recall YA entrega los hechos al pool/top-5, pero los keyword-stamps planos 0.65-0.85 vs
   cosenos reales deciden el top-5 y redistribuyen los golds frontera — capturar las ganancias
   [cat020/hp001] sin las pérdidas [cat005/9/10, hp018]); (ii) **plan B A/B 2×2 generación**
   {Sonnet,Opus}×{blurb OFF,ON} (firmado s58b, brazo A corrido — matiz nuevo: cat020 dejó de ser
   su mejor argumento, lo arregló el pool); (iii) **L-ii solo** (`scripts/s59_gate1.py --alter`,
   ef_search 40→120: +10 candidatos reales al canal; re-medición barata con los instrumentos
   s59). Cualquier opción re-usa el baseline s58 + el runner parametrizado. **Firmas (s59b):
   cláusula R del PREREG ✅ FIRMADA · L-ii ✅ AUTORIZADO por Alberto — ejecución PENDIENTE
   (el permission-mode del agente la deniega; comando para Alberto:
   `python scripts/s59_gate1.py --alter`, reversible con `--reset`).** Paralelo menor: hp009
   identidad de variantes (TECH_DEBT #43); el contrato de `chunks_v2.category` (TECH_DEBT #44 —
   DIFERIDO con triggers FIRMES [DEC-040f]: al cerrar el ciclo (freeze) y SIEMPRE antes de la
   próxima ingesta; el ESCRITOR sigue sembrando).
2. **Tras un lever shipped: confirmación held-out** — corrida ÚNICA `INCLUDE_HELDOUT=1` bajo el
   PREREG (C1/C2 firmadas + cláusula R si el lever es de retrieval).
3. **Después del ciclo:** corpus nuevo (Aritech completo / Kidde resto / Ziton-GST; método en
   `docs/CORPUS_FIRESECURITYPRODUCTS.md`). **Freeze-contract:** ninguna ingesta dentro de la
   ventana baseline→A/B→held-out — y antes de ingerir, resolver TECH_DEBT #44 (el escritor de
   `category` sembraría más basura).

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
