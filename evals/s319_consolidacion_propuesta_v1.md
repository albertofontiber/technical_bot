# s319 — Sesión de CONSOLIDACIÓN estructural (adjudicada por Alberto) — propuesta v2 (tras dúo r17)

> **v1→v2 (dúo r17: Sol 10 hallazgos con 2 críticos · Fable 3, convergentes en los
> flags sin métrica, 0 FP — NO SÓLIDO ambos, TODO aplicado):**
> 1. **Backup re-diseñado en DOS CAPAS** (Sol C1/C2): capa CORPUS/IDENTIDAD sin datos
>    personales (`documents`, `chunks_v2`, `chunks_v2_enunciados`, `chunks_v2_hyq` —
>    nombre real verificado, no `hyq`) con **gate de RESTAURACIÓN** (drill: carga en
>    SQLite local + counts + integridad FK docs↔chunks), RPO declarado (≤1 lote de
>    ingesta o 1 mes) y RTO (horas, manual); la capa de DATOS PERSONALES (7 tablas:
>    query_logs, feedback, answer_feedback, answer_messages, user_consent,
>    persona_seudonimo, consent_events) queda **FUERA del v1** — un dump estático no
>    hereda la retención de la tabla y exigiría TTL/cifrado/borrado verificable →
>    [DECIDIR-Alberto]: (A) excluir y apoyarse en el backup GESTIONADO de Supabase
>    (existe — el claim «no existe ninguna copia» se corrige a «no existe backup
>    LÓGICO restaurable bajo nuestro control») o (B) incluir con su aparato RGPD.
>    El DDL vive versionado en `migrations/` (hueco a verificar en build: RLS/
>    funciones fuera de migrations). Coherencia de snapshot: horas sin tráfico +
>    counts pre/post (PITR verdadero = capa gestionada).
> 2. **Backfill SOLO-FILENAME en v1** (Sol M-fuente): la puerta exige texto CRUDO y
>    la portada del store es OTRA fuente sin gate de equivalencia — el pase de
>    portadas queda detrás de un gate muestral (store vs PyMuPDF → mismas señales)
>    como v2 opcional. Y se reframe como **avance PARCIAL de #4** (Sol M-#4: el
>    contrato canónico exige rederivar también document_family — eso NO va aquí).
> 3. **Lote de graduación: 11 → 9** (Sol M-flags ≡ Fable F2): GENERATOR_DIRECT_FIRST
>    y VISUAL_ASSETS_LISTING_GATE no cumplen «SETTLED con métrica» (asentamiento no
>    es veredicto; la anécdota Detnov no es cifra) — fuera del lote; si se quieren,
>    van como categoría distinta «graduación-por-asentamiento» con regla propia.
>    Además (Fable F3): el análisis de impacto lista el MODO DE EVALUACIÓN por flag
>    (HYQ_TABLE y ORCHESTRATOR_PATH son constantes de IMPORT; los de generator son
>    runtime) — los tests que parchean env en runtime no ven defaults import-time.
> 4. **PR-C con el mapa completo** (Sol M-shadow): `CONVO_SHADOW` (telegram_bot
>    1515-1525) consume `turn`/`pipeline`/ORCHESTRATOR_PATH — su contrato se
>    resuelve en la cirugía (shadow_result := turn; la pierna pipeline muere).
>    **Ancla corregida** (Fable F1 — la mía era FALSA): el release gate NO importa
>    `execute_rag_turn`; lo atestigua POR STRING (`s277_c1_p1.py:5891`,
>    `attestation.get("entrypoint") == "src.rag.serving_pipeline.execute_rag_turn"`)
>    → el seam se conserva Y un rename fallaría tarde-y-distinto, no en import: el
>    gate de PR-C incluye correr la batería P1 además de MT+transporte+suite.
>    **Paridad por REPLAY CONGELADO** (Sol M-replay), no sonda live (reranker no
>    determinista): el instrumento de transporte con fakes ES la guarda.
> 5. Censo de tráfico: los 👎 con texto viven en `answer_feedback` (join) + regla de
>    redacción (uid → hash, textos truncados, agregación) para que «sin PII» sea
>    verdad (Sol M-👎).

**Mandato** (12-ago): «procede con la sesión de consolidación (1+2+3+4), y en paralelo
dejamos preparados los puntos 1/4 del paquete de apertura; tras esto, el elefante
(catálogo canónico DEC-074/091b)». Nada de esto es un incendio: es consolidación
programada sobre un sistema verde (3.829 tests, 4 tripwires activos).

**Secuencia de PRs** (riesgo creciente, rollback independiente):
- **PR-A** (aditivos): backup con recibo + backfill de revisión + anexo apertura (1/4).
- **PR-B**: graduación de flags lote 1.
- **PR-C**: retirada del camino legacy de serving (el mayor impacto — el último).

---

## PR-A.1 — Copia de seguridad con recibo (hoy NO existe ninguna — verificado)

- `scripts/backup_supabase.py`: dump paginado (patrón #72: `http_pool.abierto`,
  paginación 1000) de `documents` · `query_logs` · `feedback` · `chunks_v2` **SIN la
  columna embedding** (regenerable, ~$10-15, pipeline probado) · `chunks_v2_enunciados`
  y `hyq` ídem. Salida: JSONL.gz por tabla en `<data-root>/backups/<fecha>/` (OneDrive,
  FUERA del repo — `query_logs` lleva telegram_user_id = dato personal; el repo jamás).
- Recibo versionado SIN PII: `evals/s319_backup_receipt_v1.json` (tabla → filas,
  sha256 del dump, bytes, fecha). Runbook: 3 líneas en `docs/ENTORNO_CLOUD.md`.
- Cadencia: manual post-lote-de-ingesta + mensual (runbook; automatizar = decisión
  aparte, no aparato ahora).
- **RGPD**: el dump hereda la retención de la tabla origen; nota en el runbook.
  [DECIDIR-Alberto: retención de backups, propongo 3 rotaciones.]

## PR-A.2 — Backfill de la señal de revisión (#73 retroactivo + #4)

- Hoy: la puerta #73 protege HACIA ADELANTE; los ~1.069 docs previos tienen
  `documents.revision` NULL → el índice solo los ve por filename.
- `scripts/s319_revision_backfill.py`: para cada doc activo con `revision` NULL →
  `senales_documento(filename, portada_del_store)` (la portada YA está en el store de
  extracción — sin re-parsear PDFs) → PATCH de `revision`+`revision_date` con la MISMA
  serialización que la puerta (`serializar_senal`). Dry-run → recibo → aplicar.
- Cadenas de supersede (#4): el backfill NO cambia ningún `status` — emite el CENSO de
  colisiones resultante; los cambios de estado son adjudicación (DP312x ya viaja en la
  sentada; el par MI/bcn de DEC-192 se añade al packet si el censo lo confirma).

## PR-A.3 — Anexo apertura externa, puntos 1 y 4 (preparar, NO activar)

- **(1) Borrador aviso v8**: `docs/AVISO_PRIVACIDAD_V8_BORRADOR.md` — corrige el
  claim de cobertura (v7 dice 3 marcas; el corpus tiene 30 fabricantes), marca
  [DECIDIR] base jurídica + [DECIDIR] retención + banner BETA para externos, y
  portada: **BORRADOR — NO desplegar sin revisión de abogado** (yo no soy asesoría
  jurídica). El texto v7 servido por el bot NO se toca.
- **(4) Runbook de primer tráfico**: `scripts/s319_trafico_census.py` — lee
  `query_logs` desde fecha: consultas/día por ruta · latencias por etapa (timings de
  rag_trace) · decisiones `intent` · 👎 con texto · censo de fallo taxonomizable.
  Recibo sin PII. Se construye HOY contra datos casi-vacíos para que el día que haya
  DGs sea apretar un botón.

## PR-B — Graduación de flags: lote 1 (de 97 registrados)

**Regla del lote**: solo flags con veredicto SETTLED con métrica + semanas ON en
Railway + cero intención de volver. El default cambia EN CÓDIGO; las vars de Railway
NO las toco yo — entrego la lista de retirables a Alberto (redundantes = inofensivas).

| Flag | Default hoy → nuevo | Evidencia (métrica) |
|---|---|---|
| GENERATOR_PROMPT_VARIANT | "base" → "fidelity" | DEC-098: +3 rescates/0 regresiones fact-level; gate bvg PASS K=3 |
| RERANK_TOP_K | "5" → "10" | DEC-092/092b: rescata 11/13 rerank-miss, 0 regresión real |
| LLM_MAX_TOKENS | "2048" → "3500" | DEC-092b: 0 truncado (a 2048 truncaba cat019) |
| ENUNCIADOS_MULTIVECTOR | "off" → "on" | DEC-090: gate 4/4; verificado en prod (5-jul, RPC llamado) |
| HYQ_TABLE | "off" → "on" | DEC-099: flips 2/2 + bvg; verificado en prod vía query_logs |
| GENERATOR_SELECTION_BLOCK | "off" → "on" | DEC-101: cat022 FALLO→PASS; cat021 curada code-gated |
| GENERATOR_FOLLOWUPS | "on" → "off" | DEC-162e: coletilla 10/10→0/12; «recomendado OFF definitivo» |
| GENERATOR_DIRECT_FIRST | "off" → "on" | DEC-162e (lote s286 ON en Railway) |
| VISUAL_ASSETS_LISTING_GATE | "off" → "on" | DEC-162e (bug Detnov visto por Alberto) |
| ANTI_DIAGRAM_INVENTION | "off" → "on" | DEC-162a: peligro 10/10→0/20, supresiones 0/48 |
| WIRING_TOPOLOGY_GUARD | "off" → "on" | DEC-162a (mismo A/B ciego) |

- **Pre-verificación por flag**: la var VIVE en Railway con el valor a graduar
  (lectura API, patrón DEC-195) — un default nuevo que NO refleje producción es un
  cambio de conducta encubierto, no una graduación.
- **Riesgo señalado de entrada**: el release-config de P1 (`REQUIRED_EXACT_VALUES` /
  `SAFE_DEFAULTS`) y `DEMO_FLAGS` del assessment PINEAN valores — tocar defaults puede
  disparar P1 fail-closed (la clase r14: el sello es un tripwire, se toca CONSCIENTE).
  Análisis de impacto ANTES del build; los pins que queden redundantes se anotan, no
  se borran a ciegas.
- Gates: suite completa + assessment smoke (config ship) + byte-parity de los tests
  de paridad DEMO donde existan.
- CONVERSATION_POLICY/ORCHESTRATOR_PATH NO van en este lote: se gradúan en PR-C con
  la retirada de su camino gemelo.

## PR-C — Retirada del camino LEGACY de serving (el mayor impacto, el último)

- **Qué**: `handle_message` mantiene DOS rutas (orquestador `run_turn` vs `else`
  histórico con `execute_rag_turn` inline). Dos rutas que deben evolucionar juntas =
  la clase de #70. `ORCHESTRATOR_PATH=on` + `CONVERSATION_POLICY=impl` llevan en
  producción desde su ship con verificación e2e propia.
- **Cirugía**: el `else` muere; el orquestador queda como ruta ÚNICA; los flags
  ORCHESTRATOR_PATH ("off"→ruta única, flag retirado del código) y
  CONVERSATION_POLICY ("stub"→"impl" default; el stub queda para tests del
  instrumento). `execute_rag_turn`/`RagServingAdapters` NO se tocan (los usa el
  release gate s277 — verificado import en `s277_c1_p1.py:210`).
- **Pre-condición (asentamiento)**: verificar fecha del flip en prod + ausencia de
  incidentes en query_logs desde entonces; si el dúo o Alberto exigen más ventana,
  PR-C espera (los otros dos no dependen de él).
- Gates: MT 52/52 + instrumento de transporte + suite completa + smoke e2e del bot +
  sonda de paridad de composición (misma query, ids servidos, pre/post-retirada).

## Qué NO entra (pregunta cero)

Staging/multi-usuario (sin usuarios externos aún — se activa con la apertura real),
retirar la tabla `chunks` vieja (ventana de rollback = decisión Alberto), índice de
scripts vivos (media hora de higiene, sin retorno estructural), automatizar el backup
(cron = aparato hasta que el manual duela). El elefante (catálogo canónico) va DESPUÉS
por mandato explícito.

## Gaps declarados

- La graduación cambia el REPO-default: cualquier entorno SIN las vars de Railway
  (dev local limpio, CI) pasa a conducta ship — es EL OBJETIVO, pero los tests que
  asumían defaults viejos se tocan uno a uno (no un sed ciego).
- El backfill escribe 1.000+ PATCHes (writes mecánicos reversibles: la columna era
  NULL — el rollback es re-anular). Dry-run con recibo antes.
- El aviso v8 es BORRADOR para abogado: no se despliega en esta sesión bajo ningún
  supuesto.
