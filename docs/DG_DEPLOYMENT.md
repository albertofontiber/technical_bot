# DG Deployment — Briefing operacional

Plan para pasar el Technical Bot a directores generales de empresas en fase de DD durante la sesión 21 (a partir 27 abril 2026). Este doc cubre framing, política de iteración, alcance del eval que se generará, y checklists.

---

## 1. Mensaje sugerido al DG (template)

> *Hola [Nombre],*
>
> *Como te comenté, una de las palancas de valor que estamos preparando para el día 1 post-cierre es un asistente técnico de IA entrenado con vuestros manuales y los de los principales fabricantes con los que trabajáis (Notifier, Morley, Detnov).*
>
> *Te paso el bot en Telegram para que lo pruebes en tu día a día. Funciona con texto y audio — puedes preguntarle como si fuera tu técnico senior. Está en versión beta: cada pregunta tuya nos ayuda a ajustar el sistema con preguntas reales del sector, no de laboratorio.*
>
> *El primer mensaje que recibirás son los términos de uso (registramos las preguntas para mejorar el sistema). Si los aceptas con `/accept [tu nombre]`, ya puedes empezar.*
>
> *Bot: [@nombre_del_bot_en_telegram]*

**Importante**: el framing es "valor que verás post-cierre" + "tú nos ayudas a calibrarlo con preguntas reales". Esto convierte cada fallo del bot en señal positiva (rigor + iteración), no en "el bot no sabe lo que hace".

---

## 2. Política de iteración durante uso del DG

**Minor changes (silentes)**: ajustes de prompt, fixes de retrieval, mejoras de Whisper, nuevos modelos en BD, branding. Deploy directo a Railway sin avisar al DG. El bot puede tener una latencia de 30-60s durante el redeploy — aceptable.

**Breaking changes (con aviso)**: cambio de comandos (`/accept`, `/start`), cambio en términos (forzaría re-aceptación bumping `TERMS_VERSION`), eliminación de funcionalidades. Avisar al DG antes con un mensaje del bot tipo: *"Vamos a actualizar el sistema durante 5 minutos. Si tu próxima pregunta no responde, vuelve a intentarlo."*

**Trazabilidad**: cada query queda etiquetada con `bot_version` (git commit hash). Cuando analicemos eval, podremos separar queries por versión y descartar las generadas antes de un fix relevante.

**Backfill prohibido**: si introducimos un cambio que mejora respuestas, NO re-correr queries históricas con la versión nueva y sustituir respuestas en `query_logs`. Cada fila refleja la respuesta que el DG vio en su momento. Si queremos comparar versiones, se hace en eval separado.

---

## 3. Alcance del eval generado — "DG-grade" ≠ "técnico-grade"

El eval orgánico que produzca este deploy está etiquetado **DG-grade** internamente. Esto significa:

**Qué SÍ representa**:
- Preguntas que un fundador / DG con conocimiento técnico contrastado se hace en su día a día.
- Sesgo hacia decisiones de producto, comparativas, cobertura de gama, casos de uso comerciales con componente técnico.
- Vocabulario y nivel de detalle de alguien que conoce el sector pero no monta los equipos en obra.

**Qué NO representa**:
- Preguntas del instalador de campo (tornillería, jumpers, polaridad de un cable concreto, código de avería con LED parpadeando).
- Frecuencias reales de uso ponderadas (un técnico de campo hace 50× más preguntas básicas que un DG).
- Preguntas en jerga de obra (abreviaturas locales, modismos por región).

**Implicación para Capa 2/3**: las decisiones arquitectónicas grandes (LlamaParse, Contextual Retrieval, type-aware retrieval) NO se calibran solo contra el eval DG-grade. Se calibran contra la combinación de:
1. Eval curado existente (52 cases) — etiqueta "curated" (precisión, cobertura intencional).
2. Eval DG-grade (queries del Telegram) — etiqueta "DG-grade" (uso real, sesgado a fundador).
3. Eval técnico-grade (pendiente, semanas-meses) — etiqueta "field-grade" (uso real, instalador).

Phase 1 final solo se compromete cuando los 3 evals concuerden. Si DG-grade dice "go" y curated dice "no-go", investigar la divergencia antes de avanzar.

---

## 4. Checklist — Alberto (operacional)

### 4.1. Antes del primer DG — Supabase

- [ ] Abrir Supabase SQL Editor.
- [ ] Aplicar `migrations/004_query_logs_response_and_version.sql` (FASE A diagnóstico → FASE B aplicar → FASE C validación).
- [ ] Aplicar `migrations/005_user_consent.sql` (FASE A → B → C).
- [ ] Confirmar con `SELECT * FROM query_logs LIMIT 1` que las columnas `response` y `bot_version` existen.

### 4.2. Antes del primer DG — Railway deploy

- [ ] Crear cuenta en [railway.app](https://railway.app) (free tier vale para empezar).
- [ ] `New Project` → `Deploy from GitHub repo` → seleccionar este repo.
- [ ] En el proyecto Railway, ir a `Variables` y añadir todos los secrets del `.env.example`:
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `SUPABASE_SERVICE_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - (No hace falta `MANUALS_DIR` / `IMAGES_DIR` — solo se usan en ingest local.)
  - (`BOT_VERSION` opcional — Railway inyecta `RAILWAY_GIT_COMMIT_SHA` automáticamente.)
- [ ] El `Procfile` ya define `worker: python scripts/run_bot.py` — Railway lo arrancará como background worker (sin HTTP público).
- [ ] Tras el primer deploy, verificar logs en Railway: deben aparecer las líneas `Bot started. Listening for text and voice messages...`.
- [ ] Probar tú mismo: enviar `/start` al bot desde tu Telegram. Debe mostrar los términos.
- [ ] Aceptar con `/accept Tu Nombre` y hacer 5-10 queries reales para verificar end-to-end.
- [ ] Revisar en Supabase Table Editor que `query_logs` tiene filas con `response` y `bot_version` poblados, y que `user_consent` tiene tu fila.

### 4.3. Antes del primer DG — preparación comercial

- [ ] Confirmar branding del bot en [@BotFather](https://t.me/BotFather) (nombre y descripción visibles cuando alguien abre el chat).
- [ ] Decidir si quieres invitar 1, 2 o 3 DGs en la primera ronda. Recomendación: 2-3 desde el inicio para diversificar y multiplicar volumen.
- [ ] Adaptar el template del §1 a tu tono y cada DG concreto.

### 4.4. Durante el uso

- [ ] Una vez por semana, ejecutar `python -m scripts.review_logs --since YYYY-MM-DD` desde tu local para revisar acumulado (necesita `pip install -r requirements-dev.txt` la primera vez).
- [ ] Revisar feedback del DG (si lo da por chat informal o por correo) y reenviármelo.
- [ ] Si el DG pregunta sobre fabricantes que NO tenemos ingestados (ej. Hochiki, Apollo) → me avisas para evaluar ingest.

---

## 5. Checklist — Claude (lo que falta por mi parte)

Cerrado en sesión 21:
- [x] `bot_version` y `response` en `query_logs` (migration 004 + código).
- [x] Consent flow RGPD con `/accept` + tabla `user_consent` (migration 005 + código).
- [x] Whisper con vocabulario PCI dinámico (40+ modelos desde BD).
- [x] Branding multi-fabricante (Notifier + Morley + Detnov) en `/start`, `/help`, greetings, prompts vagos.
- [x] Tooling de revisión `scripts/review_logs.py` (CSV/XLSX, stats, filtros).
- [x] Esta documentación operacional (framing + política iteración + tiers eval).

Cerrado en sesión 21 (continúa):
- [x] Smoke test pipeline e2e (3 queries representativas, 1 por fabricante → 3/3 PASS, 116s total).
- [x] `scripts/smoke_test.py` para que tú o yo podamos re-ejecutarlo bajo demanda (`python -m scripts.smoke_test [--quick]`).
- [x] Railway deploy config: `Procfile` (worker), `runtime.txt` (Python 3.12), `.env.example` actualizado con `BOT_VERSION`, `requirements-dev.txt` para tooling local separado.

Pendiente para sesiones siguientes (post-deploy):
- [ ] Capa 1 refactoring: observability, versioning de prompts, tests de integración pipeline.
- [ ] Si DG-grade eval acumula ≥30 queries útiles → spike LlamaParse contra eval real.
- [ ] Phase 1 (refactor parser/retrieval) solo cuando 3 tiers de eval concuerden.

---

## 6. Notas de seguridad y privacidad

- Secrets en Railway env vars, NUNCA committed.
- `display_name` en `user_consent` es opcional y proporcionado voluntariamente por el DG.
- Respuestas en `query_logs.response` truncadas a 4096 chars (límite Telegram). Audio raw en Telegram, no se persiste en Supabase (solo transcripción).
- `revoked_at` en `user_consent` permite borrado lógico sin perder histórico de aceptación.
- Si el DG pide borrado RGPD: `UPDATE user_consent SET revoked_at = NOW() WHERE telegram_user_id = X` + `DELETE FROM query_logs WHERE telegram_user_id = X` + `DELETE FROM feedback WHERE telegram_user_id = X`.
