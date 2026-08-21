# s331 · Propuesta v4 — Resolución gobernada en la seam F1 + identidad del turno estructurada (spec completa de build)

> **Sustituye a `s331_variantes_hilo_propuesta_v3.md` tras el dúo r-v3 EMPAREJADO**
> (tally `2026-08-20T19:16:54`, `complete_pending_adjudication`): Sol — 4 críticos + 3 medios;
> Fable — «sustancialmente sólido», 2 medios CONVERGENTES con Sol + 2 menores. La ronda v3 ya no
> tocó arquitectura: todos los hallazgos eran huecos de ESPECIFICACIÓN, y esta v4 los cierra.
> Anclas nuevas verificadas en sesión: TTL de presencia (`catalog_resolver.py:297`), esquema
> cerrado del trace (`runtime_trace.py:579-596`).
> **Estado: PROPUESTA para dúo r-v4. NADA cableado.** Flags default-off = byte-idéntico.

## 0 · TL;DR

Un técnico dice su variante exacta («tengo la 2X-AF1-FBS») y el bot, dos turnos después, le
pregunta «¿qué variante exacta del 2X-AF1 tienes instalada?». La variante se destruye al LEER
(extracción legacy trunca a familia) y al ARRASTRAR (el hint solo lleva lo bindeado) — mientras
el resolver GOBERNADO la detecta perfectamente incluso en grafía ASR, y la re-pregunta amnésica
existe además como PLANTILLA sin LLM (`src/rag/generator.py:742-762`).

**Diseño v4** = v3 con la especificación operativa completa: **(A)** resolución gobernada en la
seam de detección de F1 (flag propio, interlock verificado EN BOOT, sin fetch síncrono jamás,
stale-while-revalidate); **(C.1)** detector de mención con DOS puertas asimétricas — conducta
(bajo daño) y corte-de-ruta (solo «variante no-resuelta de FAMILIA CONOCIDA», gate de
familia-prefijo) — con listas de exclusión GOBERNADAS y lifecycle de `pending_mention`
definido turno a turno; **(C.2)** conducta anti-re-pregunta en dos niveles gobernando prompt Y
plantillas deterministas; **(D)** canal `turn_identity` con su transporte completo
(`TurnSignals → policy.resolve → TurnResolution → TurnRequest/SingleHopPlan → generate`).

## 1 · El caso real (verificado en `query_logs`, 18-ago-2026)

| # | id | UTC | route | usuario (voz→ASR) | bot |
|---|----|----|-------|--------------------|-----|
| T1 | `b81a8af9…1e47` | 21:42:31 | `catalog_shortcut` | «¿Qué centrales de Kidde tienes?» | Lista «Kidde — central (36 de 156)» **incluyendo 2X-AF1-FB-S** |
| T2 | `e046836f…89ea` | 21:43:15 | `rag` | «Sobre la 2X-AF1-FBS.» | «¿Qué necesitas exactamente de la 2X-AF1-FBS: especificaciones…, programación…?» |
| T3 | `4fbca15f…3c71` | 21:43:53 | `rag` | «Programación principalmente.» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** |
| — | (feedback) | 21:44 | 👎 | «Si ya te he dicho que la que tengo es la FBS, ¿no debería estar información suficiente?» | — |

**`TECH_DEBT.md:1940` #49 trigger (c) DISPARADO.** Un caso real valida el MECANISMO; la
generalización la miden los gates.

## 2 · Diagnóstico mecánico (sondas $0; anclas verificadas por ambos revisores en r-v1/r-v2/r-v3)

**(D1)** `extract_product_models` (`src/rag/retriever.py:92`) trunca a familia vía el alias
`_base_aliases("2X-AF1-S")` (`src/rag/catalog.py:75-84`); el seed devuelve `[]`.
`extract_product_models("Sobre la 2X-AF1-FBS.") == ['2X-AF1']` (ídem grafía canónica). El alias
no es el bug; el bug es que la resolución gobernada no participa en el turno.

**(D2)** `WorkingState.last_query` guarda las palabras del usuario
(`src/orchestrator/conversation_policy_impl.py:721-747`); `_carry_forward` (`:442-451`) solo
inyecta bindeados: T3 llegó como `«Programación principalmente. (contexto: 2X-AF1)»`.

**(D3)** `catalog_resolver.detect("Sobre la 2X-AF1-FBS.") == ['2x-af1-fbs']`
(`src/rag/catalog_resolver.py:231`). **Recibo de la sonda (fix Fable-4 r-v3), corrida en esta
sesión sobre el repo en HEAD:**
```
'Sobre la 2X-AF1-FBS.'   -> detect: ['2x-af1-fbs']
'Sobre la 2X-AF1-FB-S.'  -> detect: ['2x-af1-fb-s']
```
Sin cuarentena (`config/identity_quarantine_v1.yaml`: 0 tokens `2x`). G0-a lo re-aserta.

**(D4)** El resolver corre en retrieval (`retriever.py:1859`) re-escaneando la QUERY, pero F1
re-detecta POR SU CUENTA (`detect_turn_signals`, def `conversation_policy_impl.py:281`,
consumida en `:701-704`; call-site `telegram_bot.py:2074-2077`): el `target_models` del handler
(`:1933`) NO alimenta F1. En T3 el hint ya no contenía la variante. **La re-pregunta amnésica
existe también como plantilla determinista** (`generator.py:742-762`).

**(D5)** `kidde:2x-af1-fb-s` **activo** en `data/catalog/products.jsonl` (gate GT 19/19 PASS,
§0 adjudicado 14-ago). En `doc_map.jsonl` el grep da **6 líneas**; las 4 entradas de manuales de
familia leídas full-line llevan `role: primary` (installation EN+ES, operation ES, quick guide
ES por regla «familia 2X-A» 16-ago). El censo completo de las 6 y sus roles = **G0-d**.

## 3 · Diseño v4 (flags default-off = byte-idéntico)

### A · `F1_RESOLVE_GOVERNED` — resolución gobernada en la seam de detección de F1

- **Contrato del flag:** flag PROPIO, default **off**, registrado en `src/flags.py` con
  lectores (`conversation_policy_impl.py`, `catalog_resolver.py`). A activo ⇔
  `F1_RESOLVE_GOVERNED=on` **Y** `IDENTITY_RESOLVE=on`. **Interlock verificado EN BOOT del
  worker** (fix Fable-3 r-v3): combinación inválida ⇒ el arranque ABORTA con log claro — nunca
  RuntimeError en el turno de un usuario (queda un guard en runtime como cinturón que no debe
  disparar jamás). El hook de boot es el mismo del warm de caché (abajo).
- **Dónde:** dentro de `detect_turn_signals` (`conversation_policy_impl.py:281`). El
  `target_models` del handler no se toca; el stamp `product_models` hereda de F1. Rama
  `resolved_model` (plan): fuera de alcance, declarada.
- **Qué:** wrapper `resolve_for_turn(query, legacy_models)` en `catalog_resolver` — la MISMA
  resolución de `resolve_for_retrieval` (detección + canonicalización + política + cuarentena +
  regla monótona s287), **sin** efectos seam-2 y **sin fetch síncrono JAMÁS** (abajo).
- **Presencia: stale-while-revalidate (fix Sol-5 r-v3 — el TTL es 900 s,
  `catalog_resolver.py:297`, así que warm-at-boot NO acota solo):** `resolve_for_turn` consume
  una vista `presence_view(allow_fetch=False)`:
  * set VIGENTE → política completa;
  * set EXPIRADO/fingerprint-invalidado → se sirve el set STALE + se programa refresco en
    HILO de fondo (nunca en el hot-path); stamp `presence: "stale"`;
  * NUNCA-calentado (boot reciente) → degradación declarada: sin regla monótona (fail-open
    conservar, la dirección que el resolver ya define); stamp `presence: "cold"`.
  El path de RETRIEVAL no cambia en v4 (sigue con fetch-on-miss dentro de su `to_thread`) —
  **alternativa declarada para el dúo**: extender stale-while-revalidate también a retrieval
  (beneficio compartido, más radio). La ventana de divergencia F1↔retrieval queda acotada y
  OBSERVABLE por el stamp; G2 la mide.
- **Warm-at-boot:** tarea de arranque no-bloqueante + refresco periódico en fondo a 0,8×TTL.
- **Doble resolución:** G0-c = `models(resolve(query cruda)) == models(resolve(query + hint
  canónico))`, política completa, caché vigente. Si falla → re-diseño.

### C.1 · Detector de mención con DOS PUERTAS asimétricas + lifecycle definido

**Corrección de fondo (Sol-1 + Fable-2 r-v3): un FP que corta ruta NO es bajo daño** — convierte
una respuesta buena en una pregunta. Por eso el detector tiene dos puertas con vara distinta:

1. **Puerta CONDUCTA (bajo daño real):** `detect_unresolved_mentions(query, resolved)` —
   forma-de-modelo (mezcla letras+dígitos, ≥4 chars, word-boundary + digit-guard) EXCLUYENDO
   por fuentes GOBERNADAS: términos resueltos (normkey) · `NON_PRODUCT_CODES`
   (`conversation_policy.py:112-114`) · cuarentena · solo-dígitos · **léxico de UNIDADES
   (nuevo, `config/mention_units_lexicon_v1.yaml`: VAC, VDC, V, A, mA, Hz, W, dB, IP, °C, Ω,
   AWG…)** · **léxico de NORMAS (nuevo, `config/mention_norms_lexicon_v1.yaml`: EN, UNE, ISO,
   NFPA, IEC, CE + patrón dígitos)**. Su output alimenta SOLO `turn_identity` (reconocimiento
   en generación). Un FP aquí = una frase de reconocimiento superflua.
2. **Puerta CORTE-DE-RUTA (alto daño ⇒ gate extra):** además de pasar la puerta 1, la mención
   debe tener **prefijo de FAMILIA GOBERNADA**: su normkey comparte prefijo con ≥1 término
   resoluble del catálogo a longitud del segmento de familia (ej.: `2xaf1fbs` ⊃ prefijo
   `2xaf1`, presente vía `2xaf1s`/`2xaf1fb`…). Solo entonces la rama de política (flag
   **`F1_MENTION_PRECEDENCE`**, propio, default off, lector `conversation_policy_impl`,
   requiere F1 activo) corta el carry-forward → CLARIFY dirigido determinista ($0) que USA la
   mención. `230VAC`, `SLC1`, `UNE-23007`, referencias de sección: sin prefijo de familia ⇒
   JAMÁS cortan ruta. La clase que SÍ corta = exactamente la del caso semilla: «variante
   no-resuelta de una familia que servimos».

**Gobernanza de las listas (Fable-2 r-v3):** los dos léxicos nuevos son ficheros config
versionados con la MISMA puerta que el resto del catálogo (PR + revisión; ampliación
documentada); no listas ad-hoc en código. `NON_PRODUCT_CODES` se declara SEED no exhaustivo
(su docstring ya lo dice) — los léxicos lo complementan sin tocarlo.

**Cohorte negativa G0-b' (anti-sesgo de autor, Fable-2):** incluye OBLIGATORIAMENTE los FP
candidatos nombrados por los revisores (`230VAC`, `24VDC`, `SLC1`, `UNE-23007`, ISO/NFPA refs)
+ una muestra de `query_logs` reales sin producto; la cohorte misma va en el paquete del dúo
r-v4 (revisión externa del diseño de la cohorte, no solo del código).

**Lifecycle de `pending_mention` (Sol-7 + Fable-1 r-v3):** campo NUEVO con transiciones
EXPLÍCITAS, compatible con el invariante «CLARIFY devuelve el estado prior INTACTO y no
refresca `last_turn_at`» (S99, `conversation_policy_impl.py:729-738`):
- **SET:** solo en la ruta CLARIFY-de-mención (puerta 2). El resto del `WorkingState` se
  devuelve INTACTO (mismos campos, mismo `last_turn_at`); `pending_mention` viaja con su
  PROPIO timestamp (`pending_at`).
- **CONSUME:** el turno siguiente lo lee: si la respuesta del usuario confirma/corrige
  (re-resolución con la cadena confirmada) → se intenta binding y se LIMPIA; si el usuario
  cambia de tema (turno con producto explícito u otra ruta) → se LIMPIA sin usar.
- **EXPIRE:** `pending_at` caduca con la MISMA ventana de 1 h; una mención caducada JAMÁS
  corta un carry-forward posterior (anti-stale, Fable-1).
- **NUNCA resucita** contexto expirado: la mención pendiente no refresca `last_turn_at` ni
  reactiva `last_target_models` (preserva sol-S4/F2).
- **Tests G0-f':** set/consume/clear/expire/no-resurrección, en MT-1a Y el espejo MT-1b
  (lock-step en el mismo commit).

**Transporte (Sol-2 r-v3) — contrato completo:** `detect_turn_signals` pasa a devolver
`TurnSignals { turn_models, available_options, unresolved_mention }` (dataclass interno;
call-sites actualizados) → `policy.resolve(..., unresolved_mention=…)` → `TurnResolution` gana
campo opcional `turn_identity: TurnIdentity | None` → el handler lo copia a
`TurnRequest.turn_identity` vía `build_turn_request` — sin costura ad-hoc en el handler.

### C.2 · `GENERATOR_NO_REASK` — dos niveles, prompt Y plantillas deterministas

Trigger en CÓDIGO sobre `turn_identity` (lección DEC-097), en DOS sitios:
1. **Prompt del LLM:** nivel RESUELTO (canónico presente — del turno o arrastrado — y sin
   mención nueva sin resolver) → no re-preguntar identidad; responder declarando alcance.
   Nivel MENCIÓN → reconocerla; confirmación dirigida permitida. El clarify necesario NUNCA
   se suprime.
2. **Plantillas sin-evidencia** (`generator.py:742-762`): con `turn_identity` presente →
   reconocimiento + confirmación dirigida (MENCIÓN) o decline honesto con alcance (RESUELTO);
   sin él (default None) → plantillas de hoy, byte-idénticas.
La rama E de la política (clarify determinista) queda intacta.

### D · Contrato `turn_identity` por las capas REALES

`TurnIdentity { resolved_models · unresolved_mention · provenance ∈ {resolved_this_turn,
carried} }` congelado; campo OPCIONAL (default None) en `TurnRequest`
(`src/orchestrator/contracts.py:27`) y `SingleHopPlan` (`:68`) → poblado por
`build_turn_request` (`src/orchestrator/telegram_adapter.py:29`; call-sites
`telegram_bot.py:2128/2141`) DESDE `TurnResolution.turn_identity` → passthrough `plan_turn` →
`run_turn` (`orchestrator.py:20-53`) → `execute_rag_turn` → `adapters.generate`
(`serving_pipeline.py:165-169`) → generador. Nunca se parsea identidad del texto.

**Trace (fix Sol-6 r-v3):** el trace tiene esquema CERRADO (`runtime_trace.py:579-596`,
`exact_keys`). El build añade UNA clave raíz OPCIONAL `turn_identity` (precedente
`mismatch_corrected`: registra evento, ausencia = flag off, byte-idéntico) con
`{presence: vigente|stale|cold · mention_detected: bool · route_cut: bool}` — cambio DECLARADO
de schema + builder + validador + tests, listado como ítem de build.

### B · Residual de datos (Alberto, NO bloquea)

Productos, doc_map y regla de familia YA adjudicados. Packet aparte: paraguas «2X-A» diferido.

## 4 · Gates pre-registrados v4

**Run-manifest obligatorio (fix Sol-4 r-v3, honesto):** cada recibo estampa corpus fingerprint
(**con su limitación declarada**: `_corpus_fingerprint` no detecta updates in-place de
`product_model` — `catalog_resolver.py:334-344`) + `catalog_commit()` + **git HEAD sha** +
snapshot de flags + model ids + seeds + config del juez. **Disciplina de ventana:** los brazos
ON/OFF de un mismo gate corren back-to-back; cualquier mutación de corpus/catálogo entre brazos
INVALIDA el recibo (regla operativa escrita en el runner del gate).

| Gate | Qué mide | Criterio | Coste |
|------|----------|----------|-------|
| **G0** unit ($0) | (a) cohort binding gobernado (2X-A completa + variantes de otras marcas); (b) negativos cross-brand #49; (b') cohorte del detector CON los FP de los revisores (230VAC, 24VDC, SLC1, UNE-23007, ISO/NFPA) + muestra real de query_logs — 0 FP en puerta 2; (c) idempotencia de política (caché vigente); (d) censo doc_map 6 líneas con roles; (e) flag-off byte-idéntico ×3 flags (patrón s316e); (f) lock-step MT-1a↔MT-1b; (f') lifecycle pending_mention (set/consume/clear/expire/no-resurrección) | 100% cohort; **0 FP en corte-de-ruta**; idempotencia exacta; off = hoy | $0 |
| **G1-pre** sonda de contenido | cobertura de «programación» en el manual de familia; **se ejecuta y ARCHIVA ANTES de G1b** y fija la expectativa | respuesta (o decline-con-alcance, declarado) | ~$0,5 |
| **G1a** replay solo-A | hilo real congelado, solo `F1_RESOLVE_GOVERNED=on` | estado/hint T3 con `2X-AF1-FB-S`; docs de familia servidos; atribución A | ~$1 |
| **G1b** replay paquete | + `F1_MENTION_PRECEDENCE` + `GENERATOR_NO_REASK` | expectativa G1-pre; cero re-pregunta amnésica (LLM y plantillas); OFF reproduce el bucle | ~$1-2 |
| **G1c** cohort C-solo | variante FUERA de catálogo (sintético), `F1_RESOLVE_GOVERNED=off`, C-flags ON | reconocimiento + confirmación dirigida; estado mixto → CLARIFY dirigido; sin supresión de clarify | ~$1 |
| **G2** no-regresión | sweep-39 servido ON-vs-OFF (ruido: OFF-vs-OFF o N-reps, DEC-096) + centinela hp009 nivel-hecho + famtie + MT flows + latencia p50/p95 con presencia vigente/stale/cold | 0 regresiones reales (lectura de respuestas, DEC-092b); MT verdes; sin bloqueo del event loop | ~$5-10 |
| **G3** conducta A/B | 24 gens (DEC-162e) × dos niveles × dos sitios (prompt/plantillas); centinela clarify legítimo | re-pregunta amnésica 0/N; clarifies necesarios sobreviven | ~$3-6 |
| **G4** pre-ship | censo Railway: `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` reales (asunción C1/s281, `src/release_profiles.py:329`) | confirmada antes de flags ON | $0 |
| **Ship** | PR → merge Alberto → lote Railway (3 flags) → verificación en prod re-lanzando la conversación real (DEC-099) | T2→T3 real responde sin re-preguntar | ~$0 |

## 5 · Alternativas consideradas y descartadas

1. Historia completa del hilo al generador — re-abre arrastre (INTENT_LLM 40/40, DEC-203/204);
   cambia la vara single-turn (DEC-154); coste/turno.
2. Prompt-only — generador ciego + plantillas deterministas fuera del prompt.
3. Resolver dentro de `extract_product_models` — revierte «una llamada por query» s91.
4. Cablear A en `telegram_bot.py:1933` (v1) — INVALIDADO POR LECTURA DE CÓDIGO (Sol-1 r-v1).
5. Mención en el texto del hint (v1) — re-entra al retrieval y spoofeable (Fable-3 r-v1).
6. Fetch síncrono de presencia en F1 — bloquea el event loop ~3 s (Sol-4 r-v2).
7. Corte-de-ruta con solo forma-de-modelo (v3) — FP de alto daño (`230VAC`→CLARIFY) — Sol-1
   r-v3; sustituido por el gate de familia-prefijo.
8. Quitar `_base_aliases` — regresa recall de familia sin dar binding.
9. Variantes en el prompt de Whisper — medido NO (DEC-233); `normkey` absorbe FBS↔FB-S.
10. Re-ingesta por variante — no existen manuales por variante; es mapeo.
11. Esperar al re-censo del piloto — #49(c) ya disparó; esperar = 👎 de DGs.

## 6 · Riesgos y gaps declarados

1. hp009-clase (REPLACE): regla monótona s287 + centinela hp009 en G2.
2. Divergencia F1↔retrieval por presencia stale/cold: acotada, observable en el trace
   (`turn_identity.presence`), medida en G2; la alternativa retrieval-también queda declarada
   para el dúo.
3. FP del detector: puerta 1 = daño bajo real (frase superflua); puerta 2 = 0-FP EXIGIDO en
   G0-b' con la cohorte de los revisores; gobernanza de léxicos por PR.
4. Prefijo-de-familia puede dar FN (variante de familia NO servida no corta ruta) — a
   propósito: esa clase cae a puerta 1 (reconocimiento), no al bucle amnésico.
5. Stamp `product_models` canónico (hereda de F1): consumidores verificados en G0; población
   de la rama ambigua de INTENT_LLM observable en el trace.
6. Lock-step MT-1a↔MT-1b: mismo commit, G0-f/f'.
7. `IDENTITY_RESOLVE=on` en prod: G4 lo verifica; interlock en BOOT lo hace imposible de
   ignorar.
8. Ruido del rerank (DEC-096): OFF-vs-OFF o N-reps.
9. Superficie §3.D (contrato + trace): opcional default-None; cambios de schema declarados
   como ítems de build con tests.
10. Cobertura de «programación»: G1-pre archivada antes de G1b.

## 7 · Settled citados y su métrica (Protocolo 2.5)

| Settled | Métrica | Relación |
|---|---|---|
| DEC-069 consumo aditivo NO-OP | retrieval-miss (pool) | Pool intacto; A alimenta `models` (seam válido) |
| DEC-084/091b REPLACE sobre-filtra | famtie/hp009 | Completa el linking turno-side; hp009 centinela |
| DEC-074 BP entity-linking | workstream | Integración turno-side; catálogo/doc_map ejecutados |
| DEC-154 utilidad conversacional | vara MT | G1*/G2-MT son la vara |
| DEC-233 marcas por voz | conducta/ASR | Fuera de alcance; `normkey` absorbe FBS↔FB-S |
| DEC-096 rerank no determinista | A/B rerank | Control de ruido G2 |
| DEC-097 prompt-gated sobre-dispara | conveyed/conducta | Trigger en código |
| DEC-023 freeze-contract | eval | Run-manifest con limitaciones DECLARADAS |
| S99/sol-S4 no-resurrección de estado | diseño MT-1a | `pending_mention` lo preserva explícitamente |
| TECH_DEBT #49 trigger (c) | deuda | Disparado 18-ago |

## 8 · Contrato

**BP**: una sola fuente de identidad (catálogo gobernado) para todas las capas; identidad
estructurada, exclusiones gobernadas por config versionada. **Estructural**: binding + estado +
contrato + plantillas. **Escalable**: marca nueva = catálogo; el detector cubre el hueco
pre-catálogo con asimetría de daño explícita.

## 9 · Coste y secuencia

Dúo r-v4 (~$3-6) → build A+C.1+C.2+D flag-off + G0 (1 sesión) → G1-pre/a/b/c + G2 + G3
(~$12-20) → G4 + ship + verificación prod (~$0). Rama `claude/synthesis-miss-attacks-p6ox9p`
(PR #323); merge y flags Railway = Alberto. Prioridad global: el paquete del abogado primero.

## 10 · Traza del dúo (v1 → v4)

- **r-v1** — Sol: 2 críticos confirmados (seam F1; dos niveles) + 3; Fable: SÓLIDO con 3 medios.
  Emparejado de Fable falló por commits míos intermedios (control #86/DEC-228 lo detectó);
  regla: cero git entre Sol y Fable.
- **r-v2 EMPAREJADO** (19:05:09) — Sol: 5 críticos (contrato flag, plantillas deterministas,
  estado mixto, caché fría, threading real) + 2; Fable: SÓLIDO, gap = detector. Confirmados
  contra código: `generator.py:742-762`, `catalog_resolver.py:422-428`, `orchestrator.py:20-53`.
- **r-v3 EMPAREJADO** (19:16:54) — Sol: 4 críticos + 3 medios (FP corta-ruta, transporte de la
  mención, flag de C.1, freeze honesto, TTL 15 min, trace cerrado, lifecycle); Fable: sólido,
  2 medios CONVERGENTES (lifecycle; daño FP + gobernanza) + fail-fast-en-boot + recibo D3.
  Verificados: `catalog_resolver.py:297` (TTL), `runtime_trace.py:579-596` (exact_keys).
- **r-v4**: pendiente (agentes frescos, worktree congelado durante la ronda).
