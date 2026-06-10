# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 10 jun 2026 (s57c, DEC-038).
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

## Estado actual (s57c — 10 jun 2026)

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → rerank LLM Sonnet (top-5) → generador
`claude-sonnet-4-6` (temp=0, `max_tokens=2048`, sin prompt caching) sobre **`chunks_v2` =
25.090 chunks / 1.012 docs / 31 marcas / 587 modelos** (contextual-retrieval activo al 100%
— verificado s56; identidad de producto data-driven `config/manufacturers/` + sidecar, DEC-035).

**Eval (el ruler):** **50 golds = 39 dev + 11 held-out** (`ho001-ho011` — s57/s57b/s57c,
DEC-037/DEC-038; **autoría held-out COMPLETA**, 0 errores, embargo verificado `verified()`=39),
taxonomía de estratos **CONGELADA** (DEC-033), juez GPT-5.5 + K-mayoría, embargo en la puerta
(`gold_store.verified`) **y en los lectores-directos de diagnóstico** (`exclude_heldout()`,
TECH_DEBT #42 cerrado — el gate s58 no expone el held-out). PREREG con **criterio de confirmación
held-out PRE-REGISTRADO** (Δ global mismo signo + 0 fabricaciones nuevas; corrida única).
**Composición final held-out (DEC-038c, ramas pre-firmadas resueltas por FUENTE):** oem-relabel 2 ·
es-en 2 · multi-doc 1 · sintesis-completitud 3 · familia-ambigua 1 · sin-tag 2; conductas 9 answer /
1 clarify / **0 admit** / 1 refuse. **GAP ABIERTO (DEC-038d, decisión de Alberto al arrancar s58):**
eje no-fabricación held-out sin admit (solo ho011 refuse) — (i) autorar 1 admit gateado **ANTES de
la corrida única de s59** (candidata: la prio-2 firmada "software de config 2X-A" si la ausencia
se prueba) vs (ii) declarar el ciclo refuse-only. **Atribución del residual sigue STALE** (predata
la ingesta s55; sin baseline de los 39) — por eso el gate de s58.

**Revisión estructural s56 (DEC-036):** rumbo confirmado — NO overhaul; docs consolidados
(PLAN compacto + HISTORY); sub-agente adversarial pin `model: fable` (cross-model GPT-5.5
innegociable en ALTO/zona-de-dolor); corpus nuevo **POSPUESTO** hasta cerrar el ciclo A/B.

## Qué sigue (orden vigente)

1. **(s58) GATE de atribución fresco** — ANTES de nada: **decisión de Alberto sobre DEC-038d**
   (admit held-out pre-corrida vs refuse-only) + la pregunta F2 al **cross-model GPT-5.5** (va
   montada sobre la review cross-model que este gate ya exige). Luego: baseline K=5 de los 39 dev
   sobre el corpus actual (= el PASS-control que el PREREG ya exige) + audit per-caso de
   *context-sufficiency* (¿el dato llegó al top-5 entregado al generador?) + instrumentar
   `stop_reason` en el generador (hoy no se captura; descarta/confirma truncamiento por
   `max_tokens=2048`). Salida: clasificar el residual {generación / sub-retrieval multi-doc /
   suelo-del-juez} y PARAR al clasificar.
2. **(s59) El lever que el gate señale** (si DEC-038d resuelve "admit pre-corrida", la autoría
   gateada del admit entra ANTES de la corrida única de confirmación):
   - **generación** → A/B **2×2 pre-registrado** {Sonnet 4.6, Opus 4.8} × {context-blurb OFF, ON};
     retrieved-contexts congelados; endpoint primario **GLOBAL** a 2 ejes (completitud↑ sin
     invención↑; estratos solo direccionales — todos a n≤4); run-manifest completo (DEC-021 §F);
     generación del eval vía Batches API (−50%); criterio ship/rollback escrito ANTES de medir
     (extender el PREREG). Nota: el brazo Opus pierde `temperature=0` (Opus 4.7+ la rechaza) —
     absorbido por K-mayoría.
   - **sub-retrieval multi-doc** → lever de retrieval dirigido (leads DEC-028/DEC-031); el modelo
     del generador NO se toca.
3. **Después del ciclo (A/B + confirmación held-out):** corpus nuevo (Aritech catálogo completo /
   Kidde resto / Ziton-GST; método en `docs/CORPUS_FIRESECURITYPRODUCTS.md`). **Freeze-contract:**
   ninguna ingesta dentro de la ventana baseline→A/B→held-out.

**Fases macro (rationale en HISTORY):** F1 calidad (en curso) → F2 escala (identidad de producto
HECHA s55; resto gated) → F3 routing/tool-use + multi-dominio del scope M&A (gated por F1/F2) →
F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** es-us (sin manuales US en corpus); contrato de ausencia formal
(admit/refuse); estratos de contenido a n=1; dual-judge (medido y diferido, s47 §D); prompt
caching en prod (revisar al tener técnicos activos — umbral: ≥50 queries/día); TECH_DEBT #40
(recall-gate CI), #42 (lectores-directos del ruler), #43 (series multi-modelo).
