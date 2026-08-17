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

> ⚠️ **s324e — con el acceso por invitación activado (`BOT_ALLOWLIST=on`), este template cambia**: en vez del usuario del bot se envía el **enlace de invitación** que genera `python -m scripts.s324e_invitaciones generar --nota "…"`, y la frase pasa a ser *«pulsa este enlace: te da de alta y te enseña los términos de uso»*. El enlace es de un solo uso y caduca en **2 días**, así que se manda **al DG concreto**, no a un grupo. Ver §4.3.b.

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

### 4.3.b. Invitar a un DG (s324e — acceso por invitación)

**Orden de activación, una sola vez** (importa: el código se despliega solo y la migración la aplicas tú):
1. ✅ **HECHO (17-ago)**: `migrations/016_allowlist_invitaciones.sql` aplicada. La FASE B dio de alta automáticamente a quien ya tenía consentimiento activo — o sea, a ti: no te quedas fuera. (Costó dos intentos: la prueba del un-solo-uso que iba dentro llevaba `BEGIN/ROLLBACK` y el SQL Editor revirtió el fichero entero. Ahora esa prueba vive aparte, en `016_validacion_un_solo_uso.sql`.)
2. `python -m scripts.s324e_invitaciones allowlist` → comprobar que tu fila está.
3. ⏳ **PENDIENTE, y es lo que enciende el control**. En Railway: `BOT_ALLOWLIST_BOOTSTRAP=<tu telegram_user_id>` (tu red de seguridad si algo falla) y **después** `BOT_ALLOWLIST=on`. En ese orden: al revés te quedas fuera de tu propio bot si algo va mal.

**Invitar (cada vez)**: `python -m scripts.s324e_invitaciones generar --nota "Juan Pérez, DG de Acme" --bot PCI_Soporte_tecnico_bot` → imprime el enlace **una sola vez** (en la base solo queda su huella); se lo mandas a esa persona; al pulsarlo queda dada de alta y el bot le enseña los términos. Caduca en **2 días** por defecto (`--dias`, máximo 7).

**Te llega un aviso al canjear.** El bot te manda por Telegram: «era para *Juan Pérez, DG de Acme* · la ha canjeado *Marta Ruiz (@martaruiz) · id 987654321*», con el comando de revocación listo. Es la contramedida contra el reenvío: no lo impide, pero lo hace visible en minutos. Requiere que `BOT_ALLOWLIST_BOOTSTRAP` tenga tu id.

**Ver y quitar**: `listar` (pendientes/usadas/caducadas) · `allowlist` (quién tiene acceso) · `revocar-invitacion <id>` · `revocar-acceso <telegram_user_id> --motivo "…"`.

**Cuánto tarda una revocación** (derivado del diseño y anclado en test offline; sin observación end-to-end todavía): hasta **10 min** con la base sana — es la caché de la puerta — y hasta **60 min** si Supabase está caído, porque la puerta sigue sirviendo el último «sí» confirmado durante una hora de gracia (los dos plazos no se suman: la gracia cuenta desde la última confirmación). Efecto **inmediato**: reiniciar el servicio en Railway. Un turno ya en vuelo termina; el corte llega en el mensaje siguiente. ⚠️ **Un id que esté en `BOT_ALLOWLIST_BOOTSTRAP` no se revoca desde el script** — esa lista no pasa por la base; hay que quitarlo de la variable en Railway.

**Solo chat privado**: el bot rechaza grupos y supergrupos, aunque quien escriba esté autorizado (sus respuestas las leerían participantes no invitados). Recomendación de segunda capa, que es cosa tuya en [@BotFather](https://t.me/BotFather): `/setjoingroups` → **Disable**, y así el bot no puede ni ser añadido a un grupo.

**Tope de gasto**: `BOT_DAILY_LIMIT` (30/día por persona por defecto; `0` lo desactiva). **Kill-switch**: `BOT_ALLOWLIST=off` devuelve el bot a acceso abierto sin deploy. ⚠️ Cualquier **otro** valor mal escrito (`onn`) deja la puerta PUESTA y además impide arrancar, con el motivo en el log: es deliberado — una errata no puede abrir el piloto.

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
- Si el DG pide borrado RGPD, la revocación va **en UNA transacción** (el dúo cazó que en dos sentencias sueltas, si el UPDATE falla, el libro afirma una revocación que no surtió efecto — evidencia en falso positivo): `BEGIN; INSERT INTO consent_events (telegram_user_id, terms_version, evento) SELECT telegram_user_id, terms_version, 'revoked' FROM user_consent WHERE telegram_user_id = X AND revoked_at IS NULL; UPDATE user_consent SET revoked_at = NOW() WHERE telegram_user_id = X; COMMIT;`. **Efecto en el bot: ≤10 minutos** (TTL de la caché de consentimiento) sin reiniciar el worker; para efecto inmediato, reiniciar. Qué hacer con las filas de `consent_events` del suprimido: **[DECIDIR] con el asesor** (borrarlas vs conservarlas como prueba de cumplimiento) — misma decisión pendiente que el plazo de `user_consent` + `DELETE FROM query_logs WHERE telegram_user_id = X` (la cascada se lleva votos, explicaciones y anclas **de SUS consultas**) + **`DELETE FROM answer_feedback WHERE telegram_user_id = X`** (los votos que emitió sobre consultas AJENAS, que la cascada NO alcanza) + `DELETE FROM feedback WHERE telegram_user_id = X` + **`DELETE FROM persona_seudonimo WHERE telegram_user_id = X`** (la correspondencia código↔persona ES dato personal; sin borrarla, el código sigue llevando a la persona). Los exports a disco de `review_logs.py` hay que borrarlos aparte (desde s301 llevan también la prosa del voto — `tap_comment` — seudonimizada como el resto). **Y desde s324e, si la migración 016 está aplicada, dos líneas más que NO cascadean desde `query_logs`** (son las primeras tablas con dato personal que no cuelgan de él): `DELETE FROM bot_allowlist WHERE telegram_user_id = X` — si no, la persona sigue autorizada — y `UPDATE bot_invitaciones SET canjeada_por = NULL WHERE canjeada_por = X`; revisar además la columna `nota` de ambas, que lleva su nombre y cargo escritos.
- **Retención (s295/DEC-177 · s299)**: 24 meses identificado → **disociado** (seudónimo estampado, identificador retirado). Matriz, encargados y pendientes: **`docs/RGPD_RETENCION.md`**. **EJECUTABLE desde el 5-ago-2026** (cola s295→s296→s297 aplicada por Alberto y verificada). **s299 (pendiente de aplicar)**: la pasada es UNA función en la base (`public.rgpd_retencion_pasada`) que pg_cron ejecuta el día 1 de cada mes con recibo en `rgpd_recibos`; `python scripts/rgpd_retencion.py` = driver manual de esa misma función (dry-run que ejecuta y revierte; `--aplicar` confirma). Si un entorno no tuviera la cola completa, el script sale con código 2 y dice qué falta. Canal de derechos: `info@fontiber.com`.
