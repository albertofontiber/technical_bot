# s331 · Propuesta v3 — Resolución gobernada en la seam F1 + identidad del turno estructurada, con contrato operativo completo

> **Sustituye a `s331_variantes_hilo_propuesta_v2.md` tras el dúo r-s331-v2 EMPAREJADO**
> (tally `2026-08-20T19:05:09`, `complete_pending_adjudication`): Sol 5.6 xhigh — 5 críticos +
> 2 medios, los 3 mecánicos CONFIRMADOS contra código en esta sesión; Fable 5 —
> «sustancialmente SÓLIDO», gap material = especificar el detector de mención (converge con
> Sol-6). Esta v3 integra los 7 y va a dúo v3 (agentes frescos, worktree congelado).
> **Estado: PROPUESTA. NADA cableado.** Flags default-off = byte-idéntico al mergear.

## 0 · TL;DR

Un técnico dice su variante exacta («tengo la 2X-AF1-FBS») y el bot, dos turnos después, le
pregunta «¿qué variante exacta del 2X-AF1 tienes instalada?». La variante se destruye al LEER
(extracción legacy trunca a familia) y al ARRASTRAR (el hint solo lleva lo bindeado) — mientras
el resolver GOBERNADO, vivo en retrieval, la detecta perfectamente incluso en grafía ASR.

**Diseño v3** (= v2 + contrato operativo que el dúo exigió): **(A)** resolución gobernada en la
seam de detección de F1, con flag PROPIO default-off, sin fetch síncrono jamás y con degradación
declarada en caché fría; **(C.1)** detector ESPECIFICADO de menciones no-resueltas + precedencia
de política para el estado mixto (mención nueva corta el carry-forward); **(C.2)** conducta
anti-re-pregunta en dos niveles que gobierna TAMBIÉN los retornos deterministas del generador —
la re-pregunta amnésica existe en plantilla (`src/rag/generator.py:742-762`), no solo en el LLM;
**(D)** canal estructurado `turn_identity` threadeado por las capas REALES
(`TurnRequest → plan_turn → SingleHopPlan → run_turn → execute_rag_turn → generate`).

## 1 · El caso real (verificado en `query_logs`, 18-ago-2026)

| # | id | UTC | route | usuario (voz→ASR) | bot |
|---|----|----|-------|--------------------|-----|
| T1 | `b81a8af9…1e47` | 21:42:31 | `catalog_shortcut` | «¿Qué centrales de Kidde tienes?» | Lista «Kidde — central (36 de 156)» **incluyendo 2X-AF1-FB-S** |
| T2 | `e046836f…89ea` | 21:43:15 | `rag` | «Sobre la 2X-AF1-FBS.» | «¿Qué necesitas exactamente de la 2X-AF1-FBS: especificaciones…, programación…?» |
| T3 | `4fbca15f…3c71` | 21:43:53 | `rag` | «Programación principalmente.» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** |
| — | (feedback) | 21:44 | 👎 | «Si ya te he dicho que la que tengo es la FBS, ¿no debería estar información suficiente?» | — |

**`TECH_DEBT.md:1940` #49 trigger (c) — «queja de técnico por arrastre/colisión de variante» —
DISPARADO.** Un caso real que valida el MECANISMO diagnosticado; la generalización la miden los
gates, no la retórica.

## 2 · Diagnóstico mecánico (sondas $0; verificado además por ambos revisores en r-v1/r-v2)

**(D1)** `extract_product_models` (`src/rag/retriever.py:92`) trunca a familia: el «2X-AF1» sale
del alias `_base_aliases("2X-AF1-S")` (`src/rag/catalog.py:75-84`); el seed devuelve `[]`.
`extract_product_models("Sobre la 2X-AF1-FBS.") == ['2X-AF1']` (ídem grafía canónica). El alias
NO es el bug (da recall de familia); el bug es que la resolución gobernada no participa en el turno.

**(D2)** `WorkingState.last_query` guarda las palabras del usuario
(`src/orchestrator/conversation_policy_impl.py:721-747`); `_carry_forward` (`:442-451`) solo
inyecta bindeados: T3 llegó como `«Programación principalmente. (contexto: 2X-AF1)»`.

**(D3)** `catalog_resolver.detect("Sobre la 2X-AF1-FBS.") == ['2x-af1-fbs']`
(`src/rag/catalog_resolver.py:231`). Sin cuarentena (`config/identity_quarantine_v1.yaml`).

**(D4)** El resolver corre en retrieval (`src/rag/retriever.py:1859`) re-escaneando la QUERY —
pero F1 re-detecta POR SU CUENTA (`detect_turn_signals`, consumida en
`conversation_policy_impl.py:701-704`; call-site `src/bot/telegram_bot.py:2074-2077` con
`resolved_model=_modelo_plan`): el `target_models` del handler (`:1933`) NO alimenta F1
(Sol-1 r-v1, confirmado). En T3 el hint ya no contenía la variante: el resolver de retrieval fue
silenciado por el hint de su propio pipeline. **Además, la re-pregunta amnésica existe también
como PLANTILLA determinista sin LLM** (`src/rag/generator.py:742-762`: «¿Puedes indicarme el
modelo concreto que estás usando?») — Sol-2 r-v2, confirmado.

**(D5)** Los datos y manuales existen: `kidde:2x-af1-fb-s` **activo** en
`data/catalog/products.jsonl` (gate GT 19/19 PASS, §0 adjudicado por Alberto 14-ago). En
`data/catalog/doc_map.jsonl` el grep de la variante devuelve **6 líneas**; las 4 entradas de
manuales de familia leídas FULL-LINE en esta sesión la llevan con `role: primary`
(installation EN+ES, operation ES, quick guide ES — esta por la regla «familia 2X-A» adjudicada
16-ago). **El censo completo de las 6 líneas y sus roles lo aserta G0-d** (corrección Fable-2
r-v2: no presentar como cerrado lo que el gate debe cerrar).

## 3 · Diseño v3 (flags default-off = byte-idéntico)

### A · `F1_RESOLVE_GOVERNED` — resolución gobernada en la seam de detección de F1

- **Contrato del flag (fix Sol-1 r-v2):** flag PROPIO, default **off**, registrado en
  `src/flags.py` con sus lectores. A activo ⇔ `F1_RESOLVE_GOVERNED=on` **Y**
  `IDENTITY_RESOLVE=on`. `F1_RESOLVE_GOVERNED=on` con `IDENTITY_RESOLVE≠on` ⇒ **RuntimeError al
  primer uso** (patrón fail-fast v2.1a del propio resolver). Mergear = byte-idéntico; G1a puede
  togglear A aislado; el rollout es el lote Railway.
- **Dónde:** dentro de `detect_turn_signals` (la detección que `resolve_conversational_turn`
  consume cuando `resolved_model` es None). El `target_models` del handler no se toca; el stamp
  `product_models` hereda de F1 aguas abajo. Rama `resolved_model` (plan): fuera de alcance,
  declarada.
- **Qué:** wrapper `resolve_for_turn(query, legacy_models)` en `catalog_resolver` — la MISMA
  resolución de `resolve_for_retrieval` (detección + canonicalización + política replace/add +
  cuarentena + regla monótona s287), **sin** efectos seam-2.
- **Caché fría SIN bloqueo (fix Sol-4 r-v2):** `resolve_for_turn` **NUNCA fetchea síncrono**. La
  presence-cache del corpus es la MISMA del módulo que usa retrieval
  (`_fetch_corpus_pm_elements`, `src/rag/catalog_resolver.py:422-428`: ~25.088 filas / ~3 s en
  frío — medido en su docstring). Con caché CALIENTE → política completa; con caché FRÍA →
  **degradación declarada**: se omite la regla monótona corpus-aware (dirección fail-open que el
  resolver ya define: conservar token) y se estampa `presence_cold=true` en el trace. **Warm-at-boot**:
  tarea de arranque no-bloqueante del worker calienta la caché; la ventana de divergencia
  F1-vs-retrieval queda acotada a los primeros turnos post-boot y es observable por el stamp.
  G0-c prueba idempotencia en caliente; G2 mide el path frío.
- **Doble resolución declarada (Fable-2 r-v1):** G0-c = `models(resolve(query cruda)) ==
  models(resolve(query + hint canónico))` sobre la cohorte, política completa en caliente. Si
  falla, re-diseño — no se ajusta el test.

### C.1 · Detector de mención ESPECIFICADO + precedencia de política (fixes Sol-3/Sol-6 r-v2, Fable-1 r-v2)

- **Detector (pieza NUEVA declarada)** `detect_unresolved_mentions(query, resolved)` en
  `catalog_resolver`: tokens con **forma de modelo** — mezcla de letras y dígitos con separadores
  opcionales, ≥4 chars, word-boundary + digit-guard (los mismos guards que las regex existentes
  del fichero) — EXCLUYENDO (todas fuentes gobernadas): términos resueltos del catálogo (por
  `normkey`), `NON_PRODUCT_CODES` (`src/orchestrator/conversation_policy.py:112-114`: RS-485,
  IP54, EN-54…), cuarentena (`config/identity_quarantine_v1.yaml`) y tokens solo-dígitos. **No es
  heurística ad-hoc en runtime**: es una función con cohorte de tests propia (G0-b') y FP
  declarados de BAJO DAÑO — alimenta conducta y política de ruta, **nunca** la lista `models` ni
  el filtro de retrieval (el veto de Fable-3 r-v1 se mantiene).
- **Precedencia del estado mixto (fix Sol-3 r-v2):** rama nueva flag-gated en la cascada: mención
  no-resuelta en ESTE turno que NO matchea (normkey) los canónicos del estado ⇒ **NO
  carry-forward plano** → CLARIFY dirigido determinista ($0) que USA la mención («no encuentro
  "X" en mi documentación; ¿puedes confirmar el modelo?»). Nunca responder del producto viejo
  callando la mención nueva. `WorkingState` gana `last_unresolved_mention`
  (lock-step MT-1a↔MT-1b en el mismo commit, con test G0-f).

### C.2 · `GENERATOR_NO_REASK` — dos niveles, gobernando TAMBIÉN los retornos deterministas (fix Sol-2 r-v2)

Trigger en CÓDIGO sobre `turn_identity` (lección DEC-097), en DOS sitios:
1. **Prompt del LLM**: nivel RESUELTO (canónico presente — de este turno o arrastrado — y sin
   mención nueva sin resolver) → no re-preguntar identidad; responder declarando alcance
   familia/variante. Nivel MENCIÓN → reconocerla y permitir confirmación dirigida. El clarify
   necesario NUNCA se suprime: mención no-resuelta ≠ producto identificado.
2. **Retornos deterministas sin-evidencia** (`src/rag/generator.py:742-762`): con
   `turn_identity` presente, las plantillas dejan de preguntar «¿el modelo concreto?» y pasan a
   reconocimiento + confirmación dirigida (nivel MENCIÓN) o decline honesto con alcance (nivel
   RESUELTO). Sin `turn_identity` (default None) → plantillas de hoy, byte-idénticas.
El clarify determinista de la política (rama E) queda intacto.

### D · Contrato `turn_identity` por las capas REALES (fix Sol-5 r-v2)

Dataclass congelado `TurnIdentity { resolved_models · unresolved_mention ·
provenance ∈ {resolved_this_turn, carried} }`, como campo OPCIONAL (default None = conducta de
hoy) en: `TurnRequest` (`src/orchestrator/contracts.py:27`) y `SingleHopPlan` (`:68`) →
poblado por `build_turn_request` (`src/orchestrator/telegram_adapter.py:29`; call-sites
`telegram_bot.py:2128/2141`) desde la resolución F1 → passthrough `plan_turn` → `run_turn`
(`src/orchestrator/orchestrator.py:20-53`) → `execute_rag_turn` → `adapters.generate`
(`src/rag/serving_pipeline.py:165-169`) → generador. **Es la pieza nueva más grande y se declara
como tal**; nunca se parsea identidad del texto de la query (spoofing cerrado).

### B · Residual de datos (Alberto, NO bloquea)

Productos, doc_map y regla de familia YA adjudicados (14/16-ago). Packet aparte: el paraguas
«2X-A» diferido (mención a secas «la 2X-A»).

## 4 · Gates pre-registrados v3 (por-brazo, atribución, freeze-contract)

**Run-manifest obligatorio (fix Sol-7 r-v2):** cada recibo de G1*/G2/G3 estampa corpus
fingerprint (`_corpus_fingerprint`), `catalog_commit()`, snapshot de flags, model ids, seeds y
config del juez — el freeze-contract de DEC-023 aplicado al replay.

| Gate | Qué mide | Criterio | Coste |
|------|----------|----------|-------|
| **G0** unit ($0) | (a) cohort de binding desde el catálogo GOBERNADO (familia 2X-A completa + variantes gobernadas de otras marcas); (b) controles negativos cross-brand de #49 (no bindear la marca equivocada); (b') cohorte del DETECTOR de mención (positivos con forma-de-modelo fuera de catálogo; negativos: `NON_PRODUCT_CODES`, normas, palabras con dígitos no-modelo); (c) idempotencia de política completa en caliente; (d) censo de las 6 líneas doc_map de la variante con roles; (e) flag-off byte-idéntico (patrón s316e); (f) lock-step MT-1a↔MT-1b | 100% cohort; 0 FP en negativos; idempotencia exacta; off = hoy | $0 |
| **G1-pre** sonda de contenido | ¿El manual de familia cubre «programación» para la variante? Se ejecuta y **ARCHIVA ANTES de G1b** (fix Fable-5 r-v2) y fija la expectativa del replay | expectativa = respuesta (o decline-con-alcance si descubierto, declarado) | ~$0,5 |
| **G1a** replay solo-A | Hilo real congelado (T1-T3 por id), solo `F1_RESOLVE_GOVERNED=on` | estado/hint de T3 con `2X-AF1-FB-S`; docs servidos incluyen manuales de familia; atribución: el flip es de A | ~$1 |
| **G1b** replay paquete | Ídem + C.1/C.2 ON | T3 cumple la expectativa de G1-pre; **cero re-pregunta amnésica** (LLM Y plantillas); OFF reproduce el bucle | ~$1-2 |
| **G1c** cohort C.1-solo | Hilo sintético con variante FUERA de catálogo; solo C ON | reconocimiento + confirmación dirigida; ni re-pregunta amnésica ni supresión del clarify; el estado mixto (canónico viejo + mención nueva) rutea a CLARIFY dirigido | ~$1 |
| **G2** no-regresión | sweep-39 servido ON-vs-OFF (control de ruido DEC-096: OFF-vs-OFF o N-reps) + centinela hp009 nivel-hecho (DEC-091b) + famtie + MT flows (`scripts/test_multiturn_vs_gold.py`) + latencia p50/p95 **incl. path frío del resolver** (presupuesto: p50 +≤100 ms caliente; frío sin bloqueo del event loop — verificado por diseño + medición) | 0 regresiones reales (lectura de respuestas, DEC-092b); MT verdes | ~$5-10 |
| **G3** conducta A/B | 24 gens (patrón DEC-162e) para C.2 en ambos niveles y en los DOS sitios (prompt + plantillas); centinela de clarify legítimo | re-pregunta amnésica 0/N; clarifies necesarios sobreviven | ~$3-6 |
| **G4** pre-ship | Censo Railway (`scripts/s322_railway_censo.py`): `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` reales en worker (asunción C1/s281, `src/release_profiles.py:329`) | confirmada antes de flags ON | $0 |
| **Ship** | PR → merge Alberto → lote Railway (`F1_RESOLVE_GOVERNED` + C-flags) → verificación en producción re-lanzando la conversación real (patrón DEC-099, query_logs) | T2→T3 real responde programación sin re-preguntar | ~$0 |

## 5 · Alternativas consideradas y descartadas

1. **Historia completa del hilo al generador** — re-abre el arrastre que INTENT_LLM cerró (gate
   40/40, DEC-203/204); cambia la vara single-turn (DEC-154); coste/latencia por turno.
2. **Prompt-only (solo C.2)** — generador ciego + los retornos deterministas ni pasan por el
   prompt (`generator.py:742-762`).
3. **Resolver DENTRO de `extract_product_models`** — revierte «una llamada por query» s91
   (`retriever.py:1856`), triplica resolución.
4. **Cablear A en `telegram_bot.py:1933`** (diseño v1) — **INVALIDADO POR LECTURA DE CÓDIGO**
   (Sol-1 r-v1, confirmado): F1 re-detecta internamente y no consume esa variable.
5. **Mención en el texto del hint** (C.1 v1) — re-entra al retrieval siguiente como filtro sin
   binding y es spoofeable (Fable-3 r-v1); el canal estructurado §3.D lo sustituye.
6. **Fetch síncrono de presencia en F1** — bloquea el event loop ~3 s en frío (Sol-4 r-v2);
   sustituido por warm-at-boot + degradación declarada.
7. **Quitar el alias de familia `_base_aliases`** — regresa recall de familia y no da el binding.
8. **Variantes en el prompt de Whisper** — medido NO (DEC-233); `normkey` ya absorbe FBS↔FB-S.
9. **Re-ingesta por variante** — no existen manuales por variante; es mapeo, no corpus.
10. **Esperar al re-censo del piloto** — #49(c) ya disparó; esperar = 👎 de DGs.

## 6 · Riesgos y gaps declarados

1. **hp009-clase (sobre-filtrado REPLACE)**: regla monótona s287 + centinela hp009 en G2.
2. **Divergencia F1↔retrieval en caché fría**: acotada a primeros turnos post-boot, observable
   (`presence_cold`), warm-at-boot la minimiza; G2 la mide.
3. **FP del detector de mención**: bajo daño por diseño (conducta, no retrieval); cohorte
   negativa G0-b' + centinelas G3. Un FP produce un reconocimiento superfluo, no un filtro roto.
4. **Stamp `product_models` con canónicos** (hereda de F1): consumidores verificados en G0;
   población de la rama ambigua de INTENT_LLM puede moverse — observable en el trace `intent`.
5. **Lock-step MT-1a↔MT-1b**: mismo commit, test G0-f.
6. **`IDENTITY_RESOLVE=on` en prod es ASUNCIÓN** (digest/C1 s281) — G4 la verifica; el interlock
   fail-fast del flag la hace imposible de ignorar en runtime.
7. **Ruido del rerank en G2** (DEC-096): OFF-vs-OFF o N-reps, pre-registrado.
8. **Superficie del contrato §3.D**: opcional default-None; el threading se paga una vez.
9. **Cobertura de «programación»**: la fija G1-pre ANTES de G1b, archivada.

## 7 · Settled citados y su métrica (Protocolo 2.5)

| Settled | Métrica | Relación |
|---|---|---|
| DEC-069 consumo aditivo NO-OP | retrieval-miss (pool) | Pool intacto; A alimenta `models` (seam válido, LEVER2/hp018 4/4) |
| DEC-084/091b REPLACE sobre-filtra | famtie/hp009 | Completa el linking turno-side; hp009 centinela G2; retoma el fix aparcado |
| DEC-074 BP entity-linking | workstream | Integración turno-side pendiente; catálogo/doc_map ejecutados (DEC-212-215) |
| DEC-154 utilidad conversacional | vara MT | G1*/G2-MT son la vara |
| DEC-233 marcas por voz | conducta/ASR | Fuera de alcance; `normkey` absorbe FBS↔FB-S |
| DEC-096 rerank no determinista | A/B rerank | Control de ruido de G2 |
| DEC-097 prompt-gated sobre-dispara | conveyed/conducta | C.2 con trigger en código |
| DEC-023 freeze-contract | eval | Run-manifest en todos los gates de replay |
| TECH_DEBT #49 trigger (c) | deuda | Disparado 18-ago; ejecutado con el catálogo gobernado |

## 8 · Contrato

**BP**: una sola fuente de identidad (catálogo gobernado) consumida por todas las capas; la
identidad viaja estructurada. **Estructural**: binding/estado/contrato + conducta de plantillas,
no el caso Kidde. **Escalable**: marca nueva = catálogo; sin curación per-familia en código; el
detector de mención cubre el hueco pre-catálogo con FP de bajo daño.

## 9 · Coste y secuencia

Dúo v3 (~$3-6) → build A+C.1+C.2+D flag-off + G0 (1 sesión) → G1-pre/a/b/c + G2 + G3
(~$12-20) → G4 + ship + verificación prod (~$0). Rama `claude/synthesis-miss-attacks-p6ox9p`
(PR #323 draft); merge y flags Railway = Alberto. Prioridad global intacta: el paquete del
abogado primero.

## 10 · Traza del dúo (v1 → v2 → v3)

- **r-v1** — Sol (ts 18:54:58): 5 hallazgos, Sol-1 (seam F1) y Sol-2 (dos niveles) críticos
  confirmados; Fable (ts 18:57:37, 12 tool_use): SÓLIDO con 3 medios (framing, doble resolución,
  mención-en-texto). Emparejado formal de Fable FALLÓ por commits míos intermedios (control
  #86/DEC-228 lo detectó). Regla re-aprendida: cero git entre Sol y Fable.
- **r-v2 EMPAREJADO** (ts 19:05:09, `complete_pending_adjudication`) — Sol: 5 críticos (contrato
  del flag, retornos deterministas, estado mixto, caché fría ~3 s, threading real) + 2 medios
  (detector sin especificar, freeze-contract); los 3 mecánicos confirmados contra código
  (`generator.py:742-762`, `catalog_resolver.py:422-428`, `orchestrator.py:20-53`). Fable:
  «sustancialmente SÓLIDO», gap material = detector de mención (converge con Sol-6) + higiene
  (doc_map 6 líneas, léxico «medido», ancla release_profiles) — todo aplicado en esta v3.
- **r-v3**: pendiente (agentes frescos, worktree congelado durante la ronda).
