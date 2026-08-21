# s331 · Propuesta v5 — Resolución gobernada en la seam F1 + identidad del turno estructurada (spec de build cerrada)

> **Sustituye a `s331_variantes_hilo_propuesta_v4.md` tras el dúo r-v4 EMPAREJADO**
> (tally `2026-08-20T19:24:54`, `complete_pending_adjudication`): Sol — 2 críticos + 3 medios
> (todos de especificación, ambos críticos CONFIRMADOS contra código en sesión); Fable —
> «SUSTANCIALMENTE SÓLIDO», 2 medios de especificación + 2 menores. Ninguna ronda desde r-v2
> toca arquitectura; esta v5 cierra los 8 ítems de r-v4.
> **Estado: PROPUESTA para dúo r-v5. NADA cableado.** Flags default-off = byte-idéntico.

## 0 · TL;DR

Un técnico dice su variante exacta («tengo la 2X-AF1-FBS») y el bot, dos turnos después, le
pregunta «¿qué variante exacta del 2X-AF1 tienes instalada?». La variante se destruye al LEER
(extracción legacy trunca a familia, `src/rag/catalog.py:75-84`) y al ARRASTRAR (el hint solo
lleva bindeados, `conversation_policy_impl.py:442-451`) — mientras el resolver GOBERNADO la
detecta hasta en grafía ASR (`catalog_resolver.py:231`), y la re-pregunta amnésica existe además
como PLANTILLA sin LLM (`src/rag/generator.py:742-762`).

**Diseño v5** = v4 con la spec operativa CERRADA: **(A)** resolución gobernada en la seam de
detección de F1 (flag propio con interlock EN BOOT; `presence_view` sin NINGUNA llamada de red
en el path de lectura — ni fetch ni re-chequeo de fingerprint —, refresher single-flight en
background); **(C.1)** dos puertas asimétricas — conducta (bajo daño) y corte-de-ruta gateado
por **extensión de término gobernado completo** con veto de ambigüedad multi-fabricante (no
prefijo arbitrario) — con léxicos gobernados, **gramática cerrada de confirmación** (ciclo máx.
1) y lifecycle de `pending_mention` anclado a sus DOS puntos de mutación reales; **(C.2)**
conducta anti-re-pregunta en prompt Y plantillas; **(D)** `turn_identity` con **provenance por
componente**, threading por las capas reales, y **observabilidad TAMBIÉN en rutas directas**
(trace `direct/1` — hoy CLARIFY retorna sin trace, `telegram_bot.py:2079-2114`).

## 1 · El caso real (verificado en `query_logs`, 18-ago-2026)

| # | id | UTC | route | usuario (voz→ASR) | bot |
|---|----|----|-------|--------------------|-----|
| T1 | `b81a8af9…1e47` | 21:42:31 | `catalog_shortcut` | «¿Qué centrales de Kidde tienes?» | Lista «Kidde — central (36 de 156)» **incluyendo 2X-AF1-FB-S** |
| T2 | `e046836f…89ea` | 21:43:15 | `rag` | «Sobre la 2X-AF1-FBS.» | «¿Qué necesitas exactamente de la 2X-AF1-FBS: especificaciones…, programación…?» |
| T3 | `4fbca15f…3c71` | 21:43:53 | `rag` | «Programación principalmente.» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** |
| — | (feedback) | 21:44 | 👎 | «Si ya te he dicho que la que tengo es la FBS, ¿no debería estar información suficiente?» | — |

**`TECH_DEBT.md:1940` #49 trigger (c) DISPARADO.** Un caso real valida el MECANISMO; la
generalización la miden los gates.

## 2 · Diagnóstico mecánico (sondas $0; anclas verificadas por ambos revisores r-v1→r-v4)

**(D1)** `extract_product_models` (`src/rag/retriever.py:92`) trunca a familia vía
`_base_aliases("2X-AF1-S")` (`src/rag/catalog.py:75-84`); el seed devuelve `[]`.
`extract_product_models("Sobre la 2X-AF1-FBS.") == ['2X-AF1']` (ídem grafía canónica).

**(D2)** `WorkingState.last_query` guarda las palabras del usuario (`:721-747`);
`_carry_forward` (`:442-451`) solo inyecta bindeados: T3 = `«Programación principalmente.
(contexto: 2X-AF1)»`.

**(D3)** `catalog_resolver.detect(...)` — recibo de sonda en sesión, repo en HEAD:
```
'Sobre la 2X-AF1-FBS.'   -> detect: ['2x-af1-fbs']
'Sobre la 2X-AF1-FB-S.'  -> detect: ['2x-af1-fb-s']
```
Sin cuarentena. G0-a lo re-aserta.

**(D4)** El resolver corre en retrieval (`retriever.py:1859`) re-escaneando la QUERY; F1
re-detecta POR SU CUENTA (`detect_turn_signals` def `:281`, consumo `:701-704`; call-site
`telegram_bot.py:2074-2077`): el `target_models` del handler (`:1933`) NO alimenta F1. En T3 el
hint ya no contenía la variante. La re-pregunta amnésica existe también como plantilla
(`generator.py:742-762`). **Y las rutas directas (CLARIFY/DECLINE) responden, loguean
(`log_query`, s301) y RETORNAN sin construir trace alguno (`telegram_bot.py:2079-2114`)** —
Sol-1 r-v4, confirmado: la observabilidad de C.1 exige un trace de ruta directa (§3.D).

**(D5)** `kidde:2x-af1-fb-s` **activo** en `products.jsonl` (gate GT 19/19, §0 adjudicado
14-ago). En `doc_map.jsonl`: grep de la VARIANTE = 6 líneas; **grep de la FAMILIA `2x-af1` = 8**
(añade `:53` — manual ES mapeado SOLO a `kidde:2x-af1-s`, la variante hermana — y `:75`)
(Fable-1 r-v4). Las 4 entradas de manuales de familia leídas full-line llevan `role: primary`.
**G0-d censa la FAMILIA (8 líneas, roles completos)**, y G1a aserta que el doc
variante-hermana-only NO desaparece del servido bajo REPLACE (clase hp009, abajo).

## 3 · Diseño v5 (flags default-off = byte-idéntico)

### A · `F1_RESOLVE_GOVERNED` — resolución gobernada en la seam de detección de F1

- **Contrato del flag:** flag PROPIO, default **off**, registrado en `src/flags.py` (lectores:
  `conversation_policy_impl.py`, `catalog_resolver.py`). Activo ⇔ `F1_RESOLVE_GOVERNED=on` **Y**
  `IDENTITY_RESOLVE=on`. **Interlock verificado EN BOOT** (abort con log claro; guard runtime
  como cinturón). Mismo hook de boot que el warm de caché.
- **Dónde:** dentro de `detect_turn_signals` (`conversation_policy_impl.py:281`). `target_models`
  del handler intacto; stamp hereda de F1. Rama `resolved_model` (plan) fuera de alcance.
- **Qué:** wrapper `resolve_for_turn(query, legacy_models)` — la MISMA resolución de
  `resolve_for_retrieval` (detección + canonicalización + política + cuarentena + regla
  monótona s287), sin efectos seam-2 y sin red en el hot-path (abajo).
- **Presencia (fix Sol-5 r-v4 — cierra el hueco del fingerprint):** `presence_view()` de SOLO
  LECTURA: **ninguna llamada de red en el path de lectura — ni fetch ni el re-chequeo de
  fingerprint que hoy vive en `_presence_lookup` (`catalog_resolver.py:474-491`, GET 1×/60s)**.
  Sirve el set actual con su edad: `vigente` · `stale` (TTL vencido o fingerprint marcado
  inválido — sigue sirviendo el último set) · `cold` (nunca calentado → degradación declarada:
  sin regla monótona, fail-open conservar). **Toda la red vive en el REFRESHER de fondo**:
  tarea única **single-flight** (lock de módulo; peticiones coalescidas) que re-arma a 0,8×TTL,
  ejecuta el fp-recheck, marca invalidación y recarga. Retrieval NO cambia en v5 (fetch-on-miss
  dentro de su `to_thread`); alternativa retrieval-también declarada para el dúo. Divergencia
  F1↔retrieval acotada y observable (stamp en `turn_identity.presence`); G2 la mide.
- **Doble resolución:** G0-c = `models(resolve(query cruda)) == models(resolve(query + hint
  canónico))`, política completa, caché vigente. Si falla → re-diseño.

### C.1 · Dos puertas asimétricas + gramática de confirmación + lifecycle anclado

**Puerta 1 — CONDUCTA (bajo daño real):** `detect_unresolved_mentions(query, resolved)` —
forma-de-modelo (mezcla letras+dígitos, ≥4 chars, word-boundary + digit-guard) EXCLUYENDO por
fuentes gobernadas: términos resueltos (normkey) · `NON_PRODUCT_CODES`
(`conversation_policy.py:112-114`, declarado seed) · cuarentena · solo-dígitos · léxico de
UNIDADES (nuevo `config/mention_units_lexicon_v1.yaml`) · léxico de NORMAS (nuevo
`config/mention_norms_lexicon_v1.yaml`). Output → SOLO `turn_identity` (reconocimiento en
generación). FP aquí = frase superflua.

**Puerta 2 — CORTE-DE-RUTA (alto daño ⇒ gate gobernado, fix Sol-2 r-v4):** además de la
puerta 1, la mención debe ser **EXTENSIÓN DE UN TÉRMINO GOBERNADO COMPLETO**:
`normkey(mención) = normkey(término resoluble del catálogo) + cola`, con **cola ≤6 chars
alfanuméricos** (forma de sufijo de variante). NO es un prefijo arbitrario: el prefijo es un
término entero del catálogo (canónico o alias), longest-term-wins. **Veto de ambigüedad:** si
los términos extendidos mapean a **más de un fabricante** ⇒ NO corte-de-ruta (cae a puerta 1).
El texto del CLARIFY dirigido usa la familia/paraguas GOBERNADA del término extendido
(`umbrellas.jsonl`/`relations.jsonl` vía `catalog_store`) cuando exista; si no, el fabricante
del término. Ejemplos: `2xaf1fbs` extiende el término gobernado `2xaf1` (kidde:2x-af1, un solo
fabricante) con cola `fbs` ⇒ corta ruta. `230VAC`/`SLC1`/`UNE-23007`: no extienden término
gobernado ⇒ jamás cortan. Flag propio **`F1_MENTION_PRECEDENCE`** (default off, lector
`conversation_policy_impl`, requiere F1 activo).

**Gramática cerrada de confirmación (fix Sol-3 r-v4) — turno siguiente a un CLARIFY-de-mención
(`pending_mention` presente), precedencia determinista:**
1. el turno contiene un token RESOLUBLE del catálogo ⇒ resolución normal; `pending` LIMPIADO;
2. si no, matchea el **léxico de AFIRMACIÓN** (nuevo `config/confirmation_lexicon_v1.yaml`,
   ES/EN: «sí», «si», «correcto», «eso es», «exacto», «yes», «correct»…) ⇒ re-intento de
   binding de la CADENA PENDIENTE; si sigue sin resolver ⇒ **se procede con la familia
   gobernada del término extendido + reconocimiento (nivel MENCIÓN)** — **ciclo máximo 1**: no
   se vuelve a preguntar (anti-bucle por diseño);
3. si no, léxico de NEGACIÓN («no», «no es», «te confundes», «not»…) ⇒ `pending` LIMPIADO +
   UNA petición de etiqueta (rama E clásica); sin segunda iteración;
4. else (cambio de tema) ⇒ `pending` LIMPIADO sin usar; cascada normal.
Los léxicos son config versionada con la misma gobernanza que los demás (PR + revisión).

**Lifecycle `pending_mention` — anclado a los DOS puntos de mutación reales (fix Fable-2
r-v4):** el SET en la ruta CLARIFY-de-mención sustituye el `return ws` identidad de
`advance_working_state` (`conversation_policy_impl.py:737-738`) por una **copia del estado
prior con SOLO `pending_mention`/`pending_at` añadidos** (resto de campos y `last_turn_at`
INTACTOS — invariante S99 preservado); el CONSUME/LIMPIA es **transición EXPLÍCITA** en el
constructor de la ruta ANSWER (`:741-747`), no omisión implícita del campo. **G0-f' testea
AMBAS rutas de mutación** (set en `:738`, clear/consume en `:741`) en MT-1a Y el espejo MT-1b
(lock-step mismo commit). EXPIRE: `pending_at` con la ventana de 1 h; una mención caducada
jamás corta un carry-forward posterior; nunca refresca `last_turn_at` ni resucita
`last_target_models`.

**Transporte:** `detect_turn_signals` → `TurnSignals { turn_models, available_options,
unresolved_mention }` → `policy.resolve(..., unresolved_mention=…)` → `TurnResolution.turn_identity`
(opcional) → `build_turn_request` → `TurnRequest.turn_identity`.

**Cohorte negativa G0-b' (anti-sesgo de autor):** OBLIGA los FP nombrados por los revisores
(`230VAC`, `24VDC`, `SLC1`, `UNE-23007`, ISO/NFPA refs) + muestra real de `query_logs`; la
cohorte va en el paquete del dúo r-v5.

### C.2 · `GENERATOR_NO_REASK` — dos niveles, prompt Y plantillas deterministas

Trigger en CÓDIGO sobre `turn_identity` (DEC-097), en DOS sitios: (1) prompt del LLM — nivel
RESUELTO (canónico presente y sin mención nueva sin resolver): no re-preguntar identidad,
responder declarando alcance; nivel MENCIÓN: reconocerla, confirmación dirigida permitida; el
clarify necesario NUNCA se suprime; (2) plantillas sin-evidencia (`generator.py:742-762`) —
con `turn_identity` presente: reconocimiento + confirmación dirigida (MENCIÓN) o decline
honesto con alcance (RESUELTO); sin él → plantillas de hoy byte-idénticas. Rama E intacta.

### D · Contrato `turn_identity` + observabilidad TAMBIÉN en rutas directas

**Dataclass (fix Sol-4 r-v4 — provenance POR COMPONENTE):**
```
TurnIdentity {
  resolved_models: tuple[str, ...]          # puede ser vacía
  models_provenance: {resolved_this_turn | carried | none}
  mention: str | None
  mention_provenance: {this_turn | pending_carried | none}
  presence: {vigente | stale | cold} | None # solo si A corrió
  route_cut: bool                           # puerta 2 disparó
}
```
**Invariantes de combinación (tabla en el build):** `mention_provenance=none ⇔ mention=None`;
`route_cut=true ⇒ mention_provenance=this_turn`; estado mixto VÁLIDO y representable:
`models_provenance=carried` + `mention_provenance=this_turn` (el caso Sol-3 r-v2);
`models_provenance=none ∧ mention=None ⇒ turn_identity=None` (no se construye vacío).

**Threading:** campo opcional (default None) en `TurnRequest` (`contracts.py:27`) y
`SingleHopPlan` (`:68`) → `build_turn_request` (`telegram_adapter.py:29`; call-sites
`telegram_bot.py:2128/2141`) desde `TurnResolution.turn_identity` → `plan_turn` → `run_turn`
(`orchestrator.py:20-53`) → `execute_rag_turn` → `adapters.generate`
(`serving_pipeline.py:165-169`) → generador. Nunca se parsea identidad del texto.

**Observabilidad (fix Sol-1 r-v4):** dos superficies, ambas declaradas como ítems de build con
tests:
1. **Ruta RAG:** el trace (`src/rag/runtime_trace.py` — path completo, fix Fable-3 r-v4;
   esquema cerrado `exact_keys` en `:579-596`) gana UNA clave raíz OPCIONAL `turn_identity`
   (precedente `mismatch_corrected`): ausencia = flag off, byte-idéntico.
2. **Rutas DIRECTAS (CLARIFY/DECLINE):** hoy retornan sin trace (`telegram_bot.py:2079-2114`);
   el log s301 (`log_query` en `:2102-2111`) adjunta un **trace mínimo declarado
   `{schema:"direct/1", route, turn_identity}`** en la columna `rag_trace` (hoy NULL en esas
   filas — sin migración), validado por una RAMA propia del validador del sink. Con flags off
   no se adjunta nada (filas byte-idénticas a hoy). Así `route_cut` es observable
   PRECISAMENTE en la ruta donde ocurre.

### B · Residual de datos (Alberto, NO bloquea)

Productos, doc_map y regla de familia YA adjudicados. Packet aparte: paraguas «2X-A» diferido.

## 4 · Gates pre-registrados v5

**Run-manifest obligatorio:** corpus fingerprint (limitación declarada: no detecta updates
in-place de `product_model`, `catalog_resolver.py:334-344`) + `catalog_commit()` + git HEAD sha
+ snapshot de flags + model ids + seeds + config del juez. **Disciplina de ventana:** brazos
ON/OFF back-to-back; mutación de corpus/catálogo entre brazos INVALIDA el recibo (regla escrita
en el runner).

| Gate | Qué mide | Criterio | Coste |
|------|----------|----------|-------|
| **G0** unit ($0) | (a) cohort binding gobernado (2X-A completa + otras marcas); (b) negativos cross-brand #49; (b') cohorte detector CON los FP de los revisores + muestra query_logs — **0 FP en puerta 2**; (c) idempotencia de política (caché vigente); (d) **censo doc_map de la FAMILIA (8 líneas, roles completos)**; (e) flag-off byte-idéntico ×3 flags; (f) lock-step MT-1a↔MT-1b; (f') lifecycle `pending_mention` en AMBOS puntos de mutación (`:738` set · `:741` consume/clear) + expire + no-resurrección; (g) gramática de confirmación (afirmar/negar/corregir/cambiar, ciclo máx 1); (h) invariantes de `TurnIdentity` | 100% cohort; 0 FP ruta; idempotencia exacta; off = hoy | $0 |
| **G1-pre** sonda contenido | cobertura de «programación» en manual de familia; **ARCHIVADA ANTES de G1b**, fija expectativa | respuesta (o decline-con-alcance declarado) | ~$0,5 |
| **G1a** replay solo-A | hilo real congelado, solo `F1_RESOLVE_GOVERNED=on` | estado/hint T3 con `2X-AF1-FB-S`; docs de familia servidos; **el doc variante-hermana-only (`doc_map.jsonl:53`) NO desaparece del servido bajo REPLACE** (centinela hp009-local, fix Fable-1 r-v4); atribución A | ~$1 |
| **G1b** replay paquete | + `F1_MENTION_PRECEDENCE` + `GENERATOR_NO_REASK` | expectativa G1-pre; cero re-pregunta amnésica (LLM y plantillas); OFF reproduce el bucle | ~$1-2 |
| **G1c** cohort C-solo | variante FUERA de catálogo (sintético), A off, C-flags ON | reconocimiento + confirmación dirigida; estado mixto → CLARIFY dirigido; ciclo máx 1 verificado; trace `direct/1` con `route_cut` persistido | ~$1 |
| **G2** no-regresión | sweep-39 servido ON-vs-OFF (ruido: OFF-vs-OFF o N-reps, DEC-096) + centinela hp009 nivel-hecho + famtie + MT flows + latencia p50/p95 en presencia vigente/stale/cold | 0 regresiones reales (lectura de respuestas, DEC-092b); MT verdes; 0 llamadas de red del path de lectura (asertado con mock) | ~$5-10 |
| **G3** conducta A/B | 24 gens (DEC-162e) × dos niveles × dos sitios; centinela clarify legítimo | re-pregunta amnésica 0/N; clarifies necesarios sobreviven | ~$3-6 |
| **G4** pre-ship | censo Railway: `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` (asunción C1/s281, `src/release_profiles.py:329`) | confirmada antes de flags ON | $0 |
| **Ship** | PR → merge Alberto → lote Railway (3 flags) → verificación en prod re-lanzando la conversación real (DEC-099) | T2→T3 real responde sin re-preguntar | ~$0 |

## 5 · Alternativas consideradas y descartadas

1. Historia completa del hilo al generador — re-abre arrastre (INTENT_LLM 40/40); cambia la
   vara single-turn (DEC-154); coste/turno.
2. Prompt-only — generador ciego + plantillas fuera del prompt.
3. Resolver dentro de `extract_product_models` — revierte «una llamada por query» s91.
4. Cablear A en `telegram_bot.py:1933` (v1) — INVALIDADO POR LECTURA (Sol-1 r-v1).
5. Mención en el texto del hint (v1) — re-entra al retrieval; spoofeable (Fable-3 r-v1).
6. Fetch síncrono de presencia en F1 — bloquea event loop ~3 s (Sol-4 r-v2); y el re-chequeo
   de fingerprint en lectura (Sol-5 r-v4) — todo a background.
7. Corte-de-ruta con solo forma-de-modelo (v3) — FP de alto daño (Sol-1 r-v3).
8. Corte-de-ruta por prefijo textual arbitrario (v4) — colisiones cross-brand/OEM a 30+
   (Sol-2 r-v4); sustituido por extensión-de-término-gobernado + veto multi-fabricante.
9. Quitar `_base_aliases` — regresa recall de familia sin dar binding.
10. Variantes en el prompt de Whisper — medido NO (DEC-233).
11. Re-ingesta por variante — no existen manuales por variante.
12. Esperar al re-censo del piloto — #49(c) ya disparó.

## 6 · Riesgos y gaps declarados

1. hp009-clase (REPLACE): regla monótona s287 + centinela hp009 en G2 + **centinela hp009-local
   del doc variante-hermana en G1a**.
2. Divergencia F1↔retrieval por presencia stale/cold: acotada, observable, medida en G2.
3. FP detector: puerta 1 bajo daño real; puerta 2 con 0-FP exigido en G0-b'; FN deliberados
   (familia no servida → puerta 1, no bucle).
4. Colisión residual de extensión-de-término: mitigada por cola ≤6 + veto multi-fabricante;
   si un homónimo single-fabricante colisionara, el daño = un CLARIFY dirigido (no respuesta
   errónea); medido en G0-b'.
5. Stamp `product_models` canónico: consumidores verificados en G0; INTENT_LLM observable.
6. Lock-step MT-1a↔MT-1b: mismo commit; G0-f/f' en ambas rutas de mutación.
7. `IDENTITY_RESOLVE=on` en prod: G4 + interlock en boot.
8. Ruido rerank (DEC-096): OFF-vs-OFF o N-reps.
9. Superficie §3.D (contrato + trace RAG + trace `direct/1`): opcional default-None; cambios
   de schema declarados con tests; filas byte-idénticas con flags off.
10. Cobertura de «programación»: G1-pre archivada antes de G1b.
11. Gramática de confirmación: léxicos cerrados versionados; ciclo máx 1 = anti-bucle por
    diseño; «afirmación con token nuevo» la gana el token (precedencia 1).

## 7 · Settled citados y su métrica (Protocolo 2.5)

| Settled | Métrica | Relación |
|---|---|---|
| DEC-069 consumo aditivo NO-OP | retrieval-miss (pool) | Pool intacto; A alimenta `models` |
| DEC-084/091b REPLACE sobre-filtra | famtie/hp009 | Completa linking turno-side; centinelas hp009 (G2) y hp009-local (G1a) |
| DEC-074 BP entity-linking | workstream | Integración turno-side; relaciones gobernadas usadas también en puerta 2 |
| DEC-154 utilidad conversacional | vara MT | G1*/G2-MT son la vara |
| DEC-233 marcas por voz | conducta/ASR | Fuera de alcance; `normkey` absorbe FBS↔FB-S |
| DEC-096 rerank no determinista | A/B rerank | Control de ruido G2 |
| DEC-097 prompt-gated sobre-dispara | conveyed/conducta | Trigger en código |
| DEC-023 freeze-contract | eval | Run-manifest con limitaciones declaradas |
| S99/sol-S4 no-resurrección | diseño MT-1a | `pending_mention` lo preserva; mutaciones ancladas |
| TECH_DEBT #49 trigger (c) | deuda | Disparado 18-ago |

## 8 · Contrato

**BP**: una sola fuente de identidad (catálogo gobernado + sus relaciones) para detección,
corte-de-ruta y clarify; identidad estructurada; exclusiones y gramáticas por config
versionada. **Estructural**: binding + estado + contrato + plantillas + observabilidad de rutas
directas. **Escalable**: marca nueva = catálogo; veto multi-fabricante hace el corte-de-ruta
seguro a 30+.

## 9 · Coste y secuencia

Dúo r-v5 (~$3-6) → build A+C.1+C.2+D flag-off + G0 (1-2 sesiones) → G1-pre/a/b/c + G2 + G3
(~$12-20) → G4 + ship + verificación prod (~$0). Rama `claude/synthesis-miss-attacks-p6ox9p`
(PR #323); merge y flags Railway = Alberto. Prioridad global: el paquete del abogado primero.

## 10 · Traza del dúo (v1 → v5)

- **r-v1** — Sol: 2 críticos confirmados (seam F1; dos niveles) + 3; Fable: SÓLIDO con 3
  medios. Emparejado de Fable falló por commits míos intermedios (control #86/DEC-228); regla:
  cero git entre Sol y Fable.
- **r-v2 EMPAREJADO** (19:05:09) — Sol: 5 críticos (flag, plantillas, estado mixto, caché
  fría, threading) + 2; Fable: SÓLIDO, gap = detector. Confirmados: `generator.py:742-762`,
  `catalog_resolver.py:422-428`, `orchestrator.py:20-53`.
- **r-v3 EMPAREJADO** (19:16:54) — Sol: 4 críticos + 3 medios; Fable: sólido, 2 medios
  convergentes. Confirmados: TTL (`:297`), `exact_keys` (`runtime_trace.py:579-596`).
- **r-v4 EMPAREJADO** (19:24:54) — Sol: 2 críticos (trace ausente en rutas directas
  `telegram_bot.py:2079-2114`; prefijo textual vs relaciones gobernadas) + 3 medios
  (gramática de confirmación; provenance por componente; fingerprint en el path de lectura
  `:474-491`) — los 2 críticos confirmados en sesión. Fable: SUSTANCIALMENTE SÓLIDO; censo de
  FAMILIA (8 líneas, `doc_map.jsonl:53`) + puntos de mutación del lifecycle (`:738`/`:741`) +
  path completo del trace. Todo integrado en esta v5.
- **r-v5**: pendiente (agentes frescos, worktree congelado durante la ronda).
