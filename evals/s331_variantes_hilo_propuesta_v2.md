# s331 · Propuesta v2 — La variante del técnico muere dos veces: resolución gobernada en la seam F1 + canal estructurado de identidad del turno

> **Sustituye a `s331_variantes_hilo_propuesta_v1.md` tras el dúo r-s331-v1** (Sol 5.6 xhigh:
> 5 hallazgos, 2 críticos CONFIRMADOS contra código · Fable 5: «sustancialmente SÓLIDO», 3 medios
> + 2 menores; 12 tool_use reales auditados). Los dos críticos de Sol eran fallos de CABLEADO del
> diseño v1 — exactamente lo que el dúo existe para cazar pre-build. **Esta v2 va a dúo emparejado
> LIMPIO antes de construir** (incidencia de proceso declarada en §10).
> **Estado: PROPUESTA. NADA cableado.** Flags default-off = byte-idéntico.

## 0 · TL;DR

Un técnico dice su variante exacta («tengo la 2X-AF1-FBS») y el bot, dos turnos después, le
pregunta «¿qué variante exacta del 2X-AF1 tienes instalada?». La variante se destruye al LEER
(extracción legacy trunca a familia) y al ARRASTRAR (el hint solo lleva lo bindeado) — mientras el
resolver GOBERNADO, vivo en retrieval, la detecta perfectamente incluso en grafía ASR.

**Qué se propone** (corregido por el dúo v1): **(A)** la resolución gobernada se inyecta en la
seam de DETECCIÓN de F1 (`detect_turn_signals`), que es la que la política consume de verdad —
no en el `target_models` del handler, que F1 ignora (crítico Sol-1); **(C.1)** la mención
no-resuelta del usuario viaja SOLO por un canal ESTRUCTURADO de identidad del turno hasta
generación — nunca inyectada en `query_for_retrieval` (medio Fable-3); **(C.2)** conducta
anti-re-pregunta EN DOS NIVELES: con canónico bindeado no se re-pregunta; con mención sin
resolver se RECONOCE y se permite confirmación dirigida — el clarify necesario nunca se suprime
(crítico Sol-2). **Es diseño nuevo GATEADO sobre mecanismos existentes** — un wrapper de
resolución, un campo de estado y un parámetro de contrato end-to-end — no «mero cableado»
(Sol-3/Fable-1: el framing v1 sobre-afirmaba).

## 1 · El caso real (verificado en `query_logs`, 18-ago-2026)

| # | id | UTC | route | usuario (voz→ASR) | bot |
|---|----|----|-------|--------------------|-----|
| T1 | `b81a8af9…1e47` | 21:42:31 | `catalog_shortcut` | «¿Qué centrales de Kidde tienes?» | Lista «Kidde — central (36 de 156)» **incluyendo 2X-AF1-FB-S** |
| T2 | `e046836f…89ea` | 21:43:15 | `rag` | «Sobre la 2X-AF1-FBS.» | «¿Qué necesitas exactamente de la 2X-AF1-FBS: especificaciones…, programación…?» |
| T3 | `4fbca15f…3c71` | 21:43:53 | `rag` | «Programación principalmente.» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** |
| — | (feedback) | 21:44 | 👎 | «Si ya te he dicho que la que tengo es la FBS, ¿no debería estar información suficiente?» | — |

El propio bot ofreció «programación» en T2 y, elegida, re-preguntó la variante que T2 contenía.
**`TECH_DEBT.md` #49, trigger (c) — «queja de técnico por arrastre/colisión de variante» —
DISPARADO** (`TECH_DEBT.md:1940`). Es UN caso real: valida el MECANISMO diagnosticado, no «la
clase completa» (corrección Sol-5 — la generalización la miden los gates, no la retórica).

## 2 · Diagnóstico mecánico (sondas $0, reproducibles; verificado también por Fable r-s331-v1)

**(D1) La extracción legacy trunca a familia — en el turno que CONTIENE la variante.**
`extract_product_models` (`src/rag/retriever.py:92`) une `data/model_catalog.json` (derivado del
CORPUS: en la familia AF1 solo existe `2X-AF1-S`) + regex seed. El «2X-AF1» sale del **alias de
familia** `_base_aliases("2X-AF1-S")` (`src/rag/catalog.py:75-84`); el seed devuelve `[]`:

```
extract_product_models("Sobre la 2X-AF1-FBS.")  == ['2X-AF1']   # también con la grafía canónica
MODEL_PATTERN.findall(...)                       == []
```

El alias de familia NO es el bug (da recall de familia); el bug es que la resolución gobernada
no participa en el turno.

**(D2) El estado del hilo guarda las palabras del usuario y nadie las usa.**
`WorkingState.last_query` conserva «Sobre la 2X-AF1-FBS.»
(`src/orchestrator/conversation_policy_impl.py:721-747`), pero `_carry_forward` (`:442-451`)
construye el turno solo con los modelos bindeados: T3 llegó como
`«Programación principalmente. (contexto: 2X-AF1)»`.

**(D3) El resolver gobernado detecta la variante — incluso en grafía ASR.**
`catalog_resolver.detect("Sobre la 2X-AF1-FBS.") == ['2x-af1-fbs']`
(`src/rag/catalog_resolver.py:231`; regex generada del catálogo, separador-insensible,
longest-first). No está en cuarentena (`config/identity_quarantine_v1.yaml`: 0 tokens `2x`).

**(D4) El resolver corre en retrieval, pero re-escanea la QUERY — y el hint de T3 ya no contenía
la variante.** `src/rag/retriever.py:1859`: `models, _identity_res =
_resolver.resolve_for_retrieval(query, models)` — una llamada por query, DELIBERADAMENTE fuera de
`extract_product_models` («se llama en 3 sitios», comentario s91 en `:1853-1858`). El estado
conversacional y el hint se derivan de la resolución F1, que re-detecta POR SU CUENTA
(`detect_turn_signals`, vía `resolve_conversational_turn`
`src/orchestrator/conversation_policy_impl.py:701-704`, call-site
`src/bot/telegram_bot.py:2074-2077` con `resolved_model=_modelo_plan`) — el `target_models` del
handler (`:1933`) NO alimenta F1 (hallazgo Sol-1). En T3 el resolver de retrieval no tenía ya
nada que detectar: fue silenciado por el hint de su propio pipeline.

**(D5) Los datos y los manuales EXISTEN.** `data/catalog/products.jsonl`: `kidde:2x-af1-fb-s`
**activo** (gate GT 19/19 PASS, §0 adjudicado por Alberto 14-ago). `data/catalog/doc_map.jsonl`:
la variante es `primary` en **4 docs de familia** — verificado por grep full-line en esta sesión
(Fable-4 lo marcó no-verificable en SU lectura truncada; recibo aquí):
`00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0` ·
`00-3280-501-4009-05_r005_2x-a_series_installation_manual_es` ·
`00-3280-505-4009-04_r004_2x-a_series_operation_manual_es` ·
`00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide_es.pdf` (esta última por la regla
«familia 2X-A» adjudicada por Alberto 16-ago). **G0 lo asertará programáticamente.**

## 3 · Diseño propuesto v2 (flags default-off = byte-idéntico)

### A · `F1_RESOLVE_GOVERNED` — la resolución gobernada entra en la SEAM DE DETECCIÓN de F1

- **Dónde (corregido, Sol-1):** dentro de `detect_turn_signals` (la detección que
  `resolve_conversational_turn` consume cuando `resolved_model` es None,
  `conversation_policy_impl.py:701-704`) — la política F1 la usa por construcción. El
  `target_models` del handler (`telegram_bot.py:1933`) NO se toca: alimenta el régimen
  legacy/stub, y el stamp `product_models` del log ya refleja la resolución F1 aguas abajo
  (el handler la reemplaza tras resolver), así que hereda el canónico sin cambio propio.
- **Qué:** wrapper NUEVO `resolve_for_turn(query, legacy_models)` en `catalog_resolver` — la
  MISMA resolución de `resolve_for_retrieval` (detección + canonicalización + política
  replace/add + cuarentena + regla monótona s287), **sin** efectos seam-2 (ni
  `allowed_sources` ni fetch). Devuelve canónicos (`2X-AF1-FB-S`) → `turn_models` → política →
  estado → hint.
- **Rama `resolved_model` (plan):** fuera de alcance v2 — viene de rutas de catálogo ya
  canónicas; declarado, no tocado.
- **Doble resolución declarada (Fable-2):** con A activo, la resolución corre en la seam F1
  (query cruda) Y en `resolve_for_retrieval` (query+hint con el canónico). No basta la
  idempotencia de DETECCIÓN: **G0 incluye test de idempotencia de POLÍTICA completa** —
  `models(resolve(query cruda))  ==  models(resolve(query + hint canónico))` sobre la cohorte,
  incluyendo cuarentena y regla monótona (si el test falla, el diseño se re-trabaja antes de
  gates e2e; no se «ajusta» el test).
- **Gating:** activo solo con `IDENTITY_RESOLVE=on` (postura C1 de prod); `off` → passthrough.

### C.1 · Identidad del turno ESTRUCTURADA — la mención no-resuelta NUNCA viaja en texto

- `WorkingState` gana `last_unresolved_mention` (token(s) con forma de modelo que la resolución
  NO bindeó; diff conservador a nivel token). **Lock-step MT-1a↔MT-1b declarado**: el harness
  espejo se cambia en el mismo commit.
- **Corrección v2 (Fable-3 + Sol-3):** la mención NO se inyecta en `query_for_retrieval` (texto)
  — ahí re-entraría en `extract_product_models`/resolver del turno siguiente como filtro sin
  binding gobernado, y sería spoofeable por parsing. Viaja SOLO en el **parámetro estructurado**
  §3.D hasta generación. El hint de texto sigue llevando ÚNICAMENTE canónicos resueltos (A).
- Cubre la clase que A no puede: variantes fuera del catálogo y grafías ASR no normalizables.

### C.2 · `GENERATOR_NO_REASK` — conducta en DOS NIVELES (corrección Sol-2)

Regla inyectada al prompt SOLO cuando el turno lleva identidad (trigger en CÓDIGO sobre §3.D —
lección DEC-097):
- **Nivel RESUELTO** (canónico bindeado presente): no re-preguntar la identidad del producto;
  responder declarando alcance de familia/variante.
- **Nivel MENCIÓN** (solo mención sin resolver): RECONOCERLA explícitamente y permitir
  confirmación DIRIGIDA («no encuentro "X" en mi documentación; ¿es de la familia Y?») — nunca
  la re-pregunta amnésica. **El clarify necesario NO se suprime**: una mención no-resuelta no es
  un producto identificado (ASR corrupto, código fuera de dominio, norma) y prohibir preguntar
  ahí degradaría precisión.
- El clarify determinista de la política (rama E) queda intacto — upstream y $0.

### D · Contrato NUEVO declarado: `turn_identity` end-to-end (corrección Sol-3)

Hoy generación recibe `(query, served, available_models)` (`src/rag/serving_pipeline.py:165-169`)
— no hay canal para hint/mención/procedencia, y parsear «(contexto:…)» del texto sería
spoofeable. Se añade un parámetro estructurado `turn_identity`
(`resolved_models · unresolved_mention · provenance`) threadeado
`execute_rag_turn → serving_pipeline → adapters.generate → generator`. **Es la pieza nueva más
grande de la propuesta y se declara como tal** (Fable-1: «cero piezas nuevas» del v1
sobre-afirmaba). Superficie: un dataclass + un parámetro opcional (default None = conducta de
hoy) por capa.

### B · Residual de datos (Alberto, NO bloquea)

Productos, doc_map y regla de familia YA adjudicados (14/16-ago). Queda como packet aparte la
pregunta DIFERIDA del paraguas «2X-A» (mención a secas «la 2X-A»), no este caso.

## 4 · Gates pre-registrados v2 (por-brazo, con atribución — corrección Sol-4)

| Gate | Qué mide | Criterio | Coste |
|------|----------|----------|-------|
| **G0** unit ($0) | (a) cohort de binding desde el **catálogo gobernado** (familia 2X-A completa + variantes gobernadas de otras marcas) — NO los «80+ pares» de #49 (fracción metadata-inconsistency, Sol-5); (b) **controles negativos**: colisiones cross-brand de #49 NO deben bindear la marca equivocada; (c) **idempotencia de política completa** (Fable-2); (d) aserción doc_map de D5; (e) flag-off **byte-idéntico** (patrón s316e); (f) lock-step MT-1a↔MT-1b | 100% cohort al canónico; 0 falsos en negativos; idempotencia exacta; off = hoy | $0 |
| **G1a** replay **solo-A** | Replay congelado del hilo real (T1-T3 por id), `F1_RESOLVE_GOVERNED=on`, C apagado | El estado/hint de T3 lleva `2X-AF1-FB-S`; los docs servidos incluyen los manuales de familia mapeados; **atribución: el flip es de A** | ~$1 |
| **G1b** replay paquete | Ídem con C.1+C.2 también ON | T3 sale del bucle: **respuesta de programación con alcance** (sonda previa de contenido en G1-pre confirma cobertura; si la sonda muestra descubierto, la expectativa pasa a decline-con-alcance y se declara) — **cero re-pregunta amnésica**; OFF reproduce el bucle | ~$1-2 |
| **G1c** cohort C.1-solo | Hilo sintético con variante FUERA de catálogo (mención no-resoluble), solo C ON | Nivel MENCIÓN: reconocimiento + confirmación dirigida; NUNCA re-pregunta amnésica NI supresión del clarify | ~$1 |
| **G2** no-regresión | sweep-39 composición servida ON-vs-OFF con control de ruido (DEC-096: OFF-vs-OFF o N-reps) + **centinela hp009 a nivel hecho** (historia REPLACE/DEC-091b) + famtie + flows MT (`scripts/test_multiturn_vs_gold.py`) + latencia p50/p95 (+≤100 ms) | 0 regresiones reales (verificación leyendo respuestas, DEC-092b); MT verdes | ~$5-10 |
| **G3** conducta A/B | 24 gens (patrón DEC-162e) para C.2 en ambos niveles; centinela de clarify legítimo | re-pregunta amnésica 0/N; clarifies necesarios sobreviven | ~$3-6 |
| **G4** pre-ship | Censo Railway (`scripts/s322_railway_censo.py`): `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` reales en worker | confirma la asunción C1/s281 | $0 |
| **Ship** | PR → merge Alberto → flags ON por lote Railway → **verificación en producción re-lanzando la conversación real** (patrón DEC-099, query_logs) | T2→T3 real responde programación sin re-preguntar | ~$0 |

## 5 · Alternativas consideradas y descartadas

1. **Historia completa del hilo al generador** — re-abre el arrastre que INTENT_LLM cerró (gate
   40/40, DEC-203/204); cambia la vara de todo lo single-turn (DEC-154); coste/latencia por turno.
2. **Prompt-only (solo C.2)** — generador ciego: pedirle no preguntar lo que no sabe = invención
   o familia sin declarar.
3. **Resolver DENTRO de `extract_product_models`** — revierte la decisión s91 «una llamada por
   query» (`retriever.py:1856`), triplica resolución y mezcla semánticas.
4. **Cablear A en `telegram_bot.py:1933`** (el diseño v1) — **MEDIDO INVÁLIDO por el dúo**: F1
   re-detecta internamente y no consume esa variable (Sol-1). Queda descartado con ancla.
5. **Mención en el texto del hint** (el C.1 v1) — re-entra al retrieval siguiente como filtro
   sin binding y es spoofeable (Fable-3); descartado por el canal estructurado §3.D.
6. **Quitar el alias de familia `_base_aliases`** — el alias da recall de familia; eliminarlo
   regresa esas queries y no da el binding (la variante no está en el catálogo de corpus).
7. **Variantes en el prompt de Whisper** — medido NO (DEC-233: saturado 990/1000); `normkey` ya
   absorbe FBS↔FB-S sin tocar el ASR.
8. **Re-ingesta por variante** — no existen manuales por variante (4 docs de FAMILIA mapeados);
   es mapeo, no corpus.
9. **Esperar al re-censo del piloto** — #49(c) ya disparó con caso real; esperar = 👎 de DGs.

## 6 · Riesgos y gaps declarados

1. **hp009-clase (sobre-filtrado REPLACE):** binding más fino ⇒ filtro más estrecho. Regla
   monótona s287 + **centinela hp009 en G2**.
2. **Doble resolución por turno (Fable-2):** semánticas replace/cuarentena sobre inputs
   distintos (query cruda vs query+hint) — test de idempotencia de política en G0 ANTES de
   cualquier gate e2e; si falla, re-diseño.
3. **Stamp `product_models` con canónicos:** hereda de F1 (sin cambio propio); consumidores
   panel/clasificación no lo usan (verificar en G0); población de la rama ambigua de INTENT_LLM
   puede moverse — declarado, observable en la sección `intent` del trace.
4. **Lock-step MT-1a↔MT-1b** (WorkingState + harness): mismo commit, con test (G0-f).
5. **`IDENTITY_RESOLVE=on` en prod es ASUNCIÓN** (digest/C1 s281; `release_profiles.py:329` lo
   exige) — G4 la verifica ANTES de gates e2e.
6. **Ruido del rerank en G2** (DEC-096) — control OFF-vs-OFF o N-reps.
7. **Cobertura de «programación» en el manual de familia**: sonda de contenido G1-pre fija la
   expectativa del replay (respuesta vs decline-con-alcance); el bucle es lo inaceptable.
8. **Latencia:** una resolución extra por turno (regex cacheada; presence lookup TTL);
   presupuesto p50 +≤100 ms, medido en G2.
9. **Superficie del contrato §3.D:** parámetro opcional con default None (conducta de hoy);
   el riesgo de threading se paga una vez y queda para futuros usos de identidad.

## 7 · Settled citados y su métrica (Protocolo 2.5)

| Settled | Métrica del veredicto | Relación |
|---|---|---|
| DEC-069 consumo aditivo = NO-OP-con-regresión | retrieval-miss (pool) | El pool NO se toca: A alimenta la lista `models` (seam VÁLIDO medido, LEVER2/hp018 4/4) |
| DEC-084/091b REPLACE sobre-filtra con linking incompleto | famtie/hp009 | Completa el linking query-side a nivel turno; hp009 centinela en G2; retoma el fix aparcado de 091b |
| DEC-074 BP entity-linking 2 etapas | (workstream) | Integración turno-side pendiente del BP; catálogo/doc_map ejecutados (DEC-212-215) |
| DEC-154 utilidad conversacional | vara MT propia | G1*/G2-MT son la vara; el single-turn no se re-litiga |
| DEC-233 marcas por voz | conducta/ASR | Fuera de alcance; `normkey` absorbe FBS↔FB-S; tabla de confusiones sigue su curso |
| DEC-096 rerank no determinista | A/B rerank | Diseña el control de ruido de G2 |
| DEC-097 selection prompt-gated sobre-dispara | conveyed + conducta | C.2 usa trigger en CÓDIGO sobre canal estructurado |
| TECH_DEBT #49 | deuda con trigger | Trigger (c) disparado 18-ago; se ejecuta con el instrumento que s72 no tenía |

## 8 · Contrato

**BP**: una sola fuente de verdad de identidad (catálogo gobernado, DEC-074) consumida por todas
las capas; el turno conversacional es la capa que falta, y la identidad viaja ESTRUCTURADA, no
por texto. **Estructural**: ataca binding/estado/contrato, no el caso Kidde; C cubre el residual
por diseño. **Escalable**: marca nueva = entra al catálogo y el turno la ve sin código nuevo.

## 9 · Coste y secuencia

Dúo v2 (Sol xhigh + Fable emparejado, agentes frescos): ~$3-6 · Build A+C.1+C.2+D flag-off + G0:
1 sesión · G1a/b/c+G2+G3: ~$11-20 · G4+ship+verificación prod: ~$0. Rama
`claude/synthesis-miss-attacks-p6ox9p` (PR #322 draft); merge y flags Railway = Alberto.
Prioridad global intacta: el paquete del abogado primero.

## 10 · Traza del dúo v1 → v2 (incidencia de proceso incluida)

- **Sol r-s331-v1** (ts 2026-08-20T18:54:58, xhigh, tools): 5 hallazgos — Sol-1 crítico
  CONFIRMADO contra código (seam F1), Sol-2 crítico aceptado (dos niveles), Sol-3 confirmado
  (contrato §3.D), Sol-4 aceptado (gates por-brazo), Sol-5 aceptado (cohorte gobernada).
- **Fable r-s331-v1** (ts 2026-08-20T18:57:37, 12 tool_use reales): «sustancialmente SÓLIDO»;
  Fable-1 = Sol-3 (framing), Fable-2 doble resolución (→G0-c), Fable-3 mención en texto
  (→§3.D), Fable-4 doc_map (verificado con recibo en D5), Fable-5 higiene de paths (aplicada).
- **Incidencia declarada:** el emparejado FORMAL de Fable v1 falló — «Sol y Fable no revisaron
  exactamente los mismos bytes ordenados» — porque cometí commits (propuesta + recibos de Sol)
  ENTRE el arranque de Sol y el de Fable, bajo presión del stop-hook. El runner lo detectó y lo
  dijo (control #86/DEC-228 funcionando). El fichero-sujeto nunca cambió de bytes, así que el
  CONTENIDO de ambas reviews es válido como input de esta v2; el emparejado limpio lo tiene la
  ronda v2. **Regla re-aprendida: CERO operaciones git entre el arranque de Sol y el final de
  Fable, aunque el stop-hook proteste.**
