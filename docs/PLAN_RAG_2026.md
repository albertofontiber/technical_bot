# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 19 ago 2026 (s324j — el diseño del panel a Vercel CERRADO tras seis rondas del dúo; el estado
> vigente es el bloque «Estado actual» de abajo).
>
> **El historial vive en [`docs/HISTORY.md`](HISTORY.md)** (movido en s56): log de sesiones
> s30→s55, rationale histórico de mayo 2026 (secciones originales ## 1-9, con su numeración —
> las citas antiguas tipo "PLAN §9.14" o "§660" resuelven allí), changelog y, desde s324d, el
> **archivo de los «Estado anterior» s100→s322b** (con sus anclas). Este fichero queda compacto a
> propósito: es el doc que se relee en cada arranque de sesión.
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

<a id="estado-actual-s277--22-jul-2026"></a>
## Estado actual (s324j — 19 ago 2026; piloto DG vivo)

**La voz ya hace lo mismo que el texto (DEC-235, PR #284 mergeada).** El piloto destapó que
`handle_voice` nunca llamaba a `plan_turn`: las NUEVE rutas de atajo eran inalcanzables hablando
— la misma pregunta se contestaba tecleada y se rechazaba dicha. La causa no era la ruta que
faltaba: era el mismo default `= "text"` replicado SEIS veces, que hacía que olvidar la
procedencia registrase en silencio un audio como si se hubiera tecleado. **Las SEIS capas
cerradas**: Fase 1 (`Procedencia` + preludio compartido), Fase 2 (`TurnRequest` /
`build_turn_request`, PR #287) y la sexta —el `DEFAULT` del esquema— con la **018 APLICADA por
Alberto** (verificado 19-ago: `column_default = NULL`, `is_nullable = NO`, CHECK
`text|voice|error`). La **017** también (el CHECK ya lista `cuota_agotada`).
Suite 4426 verde. 8 rondas de dúo; el gate verificado que DISCRIMINA (12/24 fallaban antes).

**VERIFICADO EN PRODUCCIÓN (19-ago), no sólo en la suite.** El recibo está en `query_logs.route`,
que separa `rag` de `catalog_shortcut`, y lo prueba **la misma pregunta cambiando de ruta al
cambiar de canal**:

| hora (18-ago) | canal | `route` | `response_length` |
|---|---|---|---|
| 14:16 | voice | `rag` | 152 — «no he encontrado información relevante» |
| 14:18 | text | `catalog_shortcut` | **494** — el listado de 14 |
| **20:36** | **voice** | **`catalog_shortcut`** | **494** |
| 21:42 | voice | `catalog_shortcut` | 1041 — Kidde, 36 centrales |

Los dos `494` son **la misma respuesta byte a byte** por canales distintos y con la pregunta
redactada distinta: es la paridad del gate ocurriendo con tráfico real. Y el censo de las 10 filas
de voz da **cero ASR perdidos** — la invariante que `Procedencia` impone en el TIPO se cumple
también en los datos que ya estaban escritos.

**Abierto, con dueño**: «no te he entendido» (el ASR devuelve algo que no es marca → el bot afirma
un hueco de corpus que no existe; el arreglo es GENERAR las variantes de las 30 marcas como ya se
generan las de los modelos, no coleccionar confusiones) · el gate de ASR con ≥30 audios reales
(DEC-234: el bake-off no lo cumplió) · #86 el runner de Fable pega 191 KB y ahoga a su revisor
(DEC-236, diagnóstico medido) · bloque A del catálogo (`detnov:ccd-103` → convencional, regla
adjudicada, control independiente: reproduce 14 citas CAD sin contradicción).

### QUÉ SIGUE — cablear el panel (diseño CERRADO en s324j; DEC-238)

**El diseño del panel a Vercel está TERMINADO y validado: `evals/s324i_panel_vercel_propuesta_v9.md`**
(s324j, 19-ago). Seis rondas del dúo en una sesión (v3→v9, 64 hallazgos, cada uno verificado con
regla C y cerrado — traza completa en el tally, ts `07:50:18`→`09:02:03` del 19-ago): r1 tumbó 3
críticos; desde r2, cero defectos de mecanismo; r6 terminó con **Fable en «SÓLIDO» explícito**
(~30 anclas, cero desajustes) y Sol con 5 medios de contrato-de-integración sobre código aún
inexistente, cerrados en la v9. Piezas del diseño: `sello` de credencial en la cookie
(revocación/cambio de contraseña efectivos en la siguiente petición), cerrojo distribuido
contar-al-admitir (RPC `panel_puerta` INVOKER endurecida), frontera RLS/REVOKE de la 016 en las
tablas nuevas, idempotencia por `op`, retención por el patrón s299 (función hermana diaria con
recibo), y `IdentidadNoDisponible` (una caída no miente «credenciales incorrectas»).

**La sesión siguiente CABLEA — con el GO de Alberto** (un diseño SÓLIDO no es un GO, DEC-173):
migraciones `019`/`020` + `dashboard/cerrojo.py` + sello + op, las ~13 puertas y el test de
integración pg (patrón s295). El dúo VUELVE a correr sobre el DIFF (Protocolo 3, ALTO). La v9
lleva §13 con el alcance exacto y la secuencia.

**Gates previos a EXPONER, no opcionales** (v9 §13): plazo `[DECIDIR: Alberto]` de
`panel_usuarios` decidido · panel dentro del paquete del abogado (DEC-231) — que además NOMBRA el
pendiente canónico de la purga 24m de `bot_invitaciones`/allowlist (adjudicada s324e, sin
mecanismo) · medición XFF, tras la cual (y solo entonces) se enciende la mitad `ip:` del cerrojo
— hasta entonces esa clave NI CUENTA NI BLOQUEA (con la IP compartida del proxy, 5 fallos de un
atacante serían un 429 global; cazado en r5).

**Hallazgo LATENTE de HOY, aparte del panel** (r1, S-C1 — verificado): anular una invitación está
ROTA contra Supabase real — `gestion.py:271-273` firma en `nota` (r41) y el GRANT de la 016 no
concede `UPDATE (nota)` → 42501. Invisible para los tests sin red. La 020 lo arregla de raíz
(`revocada_por` + CHECK); si alguien anula una invitación desde el panel ANTES de cablear, fallará
con «Supabase respondió 400».

---

## Estado anterior (s324b/c — 16-17 ago 2026, misma sesión que s324; noche autónoma)

**s325b — el extraction store, a la nube (DEC-221)**: lo ÚNICO del corpus fuente que
no estaba ya en cloud (1.143 JSON / 354 MB, solo en OneDrive) vive ahora también en el
bucket privado `extraction`. `src/extraction_store.py` resuelve **disco primero,
bucket después**, así que en local nada cambia; cableados `enunciados_pass`,
`s94_f1_generate` y `src/reingest/pipeline`. Verificado contra el bucket REAL sin
disco: `_build_sha_map` da **1.136 claves, las mismas que desde disco**, en 0,5 s.
Consistencia por **puerta única**: `ingest_new` publica al bucket en el mismo acto en
que escribe (fail-open declarado), con `--verificar` por SHA como red y la `config`
como versión del mecanismo de extracción. **LÍMITE declarado**: ingestar manuales
NUEVOS sigue siendo local — `ingest_new` escribe al store y exige PDFs y sidecar en
disco. Dúo completo NO SÓLIDO → 3 críticos convergentes aplicados (faltaba un
consumidor; ingest_new es productor; la «descarga perezosa» era falsa), más un bug de
plataforma: `os.path.basename` sobre rutas Windows habría vaciado el mapa EN SILENCIO
al correr en Linux.

**Dos frentes en una sola sesión, en paralelo (Alberto: «prefiero la simplicidad de una sesión»): él
adjudica la asignación documento→modelo en los packets; yo mido la etapa 3 y aplico lo firmado (DEC-227).**
**Etapa 3, MEDIDA antes de construir**: sondas de los 8 «servido y omitido» del FULL 16-ago → 7 ALCANZABLE / 1 NO
(`hp009#0`); pero la población por gold de hoy = {hp017, hp005, hp015, hp001} = 4 y **no es una clase** (`hp015`
era DATOS —CCD-103 candidate, resuelto—, `hp001#2` within-doc NO-GO 3×, `hp005#3` omisión inestable) ⇒ **un solo
hecho pagable por serving: `hp017#1`** (cards de 360 chars cortan el bullet). Propuesta D1 «cierre de bloque de
lista» → **dúo r33 (Sol 6, Fable 5 con 14 tool_use reales): NO construir, medir antes** → medido esa noche:
**prueba offline D1** ($0, código real de coverage, fidelidad 40/40): alcanza `hp017#1` SOLO con la definición A
(blanco entre ítems no rompe), 0 hechos NO-OK adicionales, toca 6/27 filas estructurales y 9 hechos OK;
**replay congelado** de los 4 flips ($5,44, N=5 misma vista + N=3 fresco, juez K=5 intacto): **4/4 SÍNTESIS
INESTABLE**, 0 serving (con N=3 el FULL etiqueta «flip»/«stable-miss» por azar). Cifra de cabecera de DEC-175:
**1 hecho**; D1 solo con GO explícito de Alberto sobre «1». Los 3 de conducta («negar la premisa») → packet de
gold-review `evals/s324c_goldreview_conducta_packet_v1.md`.
**Catálogo (todo con las puertas de DEC-225, verificación posterior 0 fallos)**: R1' (62 entries) · §0.C (21 altas
+ 7 alias + 26 doc_map + 2 bajas; Fable standalone 6 hallazgos aplicados) · STRATOS = paraguas de familia · §0.D/§0.E
(5 docs retirados, altas Fidegas S/3-2·S/3-IR·S/2-IR y EMA1224B4R/W, TG = software, MADT731_06 → HSSD-2, 5 retags)
· **Detnov E1b** (8 confirmaciones + `detnov:ccd-103`; el gate cazó 14 alias descriptivos «2 zonas»… que la
confirmación activaba → retirados antes). **E1b PREPARADO, NO aplicado**: 13 planes + dry-run **13/13 PASS** (453
confirmables verificadas, 44 `no_aplicar` con propuesta, 132 alias descriptivos a retirar antes) —
`evals/s324c_e1b_bloques_censo_v1.md`. **Re-juicio K=5 cross-model** de las 61 «confianza media» (E1 14 + E1b 47; 3× sonnet-5 + 2× gpt-5.5, rúbrica original,
texto completo, cita verificada; ≈$6,6): 39 convergentes ≥4/5 (E1b 34 CONFIRMAR + 1 RETIRAR; E1 2 PRODUCTO_REAL + 2
ARTEFACTO), 22 no (10 con desacuerdo cross-model Sonnet↔GPT) → bloque `k5_confirmar` PREPARADO con el gate (31 PASS)
— `evals/s324c_rejuicio_k5_v1.md`. Suite verde (3.891; `test_s307` desacoplado de los datos del catálogo). Deuda nueva #89
(5 defectos del instrumento de sonda). Coste de la noche ≈ $25 (sondas ~$12, replay $5,44, K=5 ≈$6,6, resto $0). **PR #276 abierta** (rama `claude/s324b-sondas-etapa3`; la mergea Alberto).

**s324d (17-ago, mañana autónoma mientras Alberto revisa packets; DEC-228)**: E2 **re-derivado** tras los lotes
(conservador PASS · pleno STOP con las 5 pérdidas conocidas, CCD-103 ya no pierde · split 618+743); **PLAN podado**
162 KB → 17 KB (archivo íntegro en HISTORY); **#86** runner Fable audita `tool_use` reales; **#89 RESUELTO** con dúo
r34 (Sol 7/7 + Fable 1/1 aplicados): sonda con oráculo `serve` PAREADO, guard de cobertura valor+predicado,
`JUEZ_INCOMPLETO`, recibo parcial honesto, coste real, `--receipt`; **#88 PREPARADO** (55 retags `documents.pm` →
canónico E3, dry-run 55/55, nada aplicado); **#87**: sin pipeline OCR en el repo. Suite verde.

**s324d tarde (17-ago, autónoma con Alberto en paralelo; DEC-229)**: **el hallazgo que cambia el rumbo — de los 15
hechos no-OK del FULL, 9 son INESTABLES y sólo 6 son defecto real** (N=5 sobre vista congelada, $9,12): el ruler con
N=1 clasifica ~60 % de sus no-OK **por azar**. **#87 RESUELTO con su raíz real** (no era OCR: `md or text` dejaba pasar
un markdown degenerado; guarda en `src/ingestion/page_content.py`, dúo r35, TI-007 re-ingestado 47 → 3.601 chars).
**#84 corregido**: su «medido» era un NO-DATO (el flag no existe en Railway; el sub-defecto real es el join doc_map
exacto, 98/977 filas, 1 % de los chunks de golds). **#90 cerrada documentada** tras dúo r36 (Opus 5 dictaminó NO
SÓLIDO mi propuesta: mismatch de métrica del settled + una afirmación falsa; recomendación E = declarar el drop, en la
próxima ingesta). **#88 aplicado** (55 retags con CAS). Censo de corpus **completo 1.054/1.054**: 13 accionables,
**ninguno sustenta un gold**.

**s324e (17-ago) — PRIORIDAD #1 DE ALBERTO: preparar el piloto con Directores Generales (DEC-230).**
El bot tenía 96 consultas de UN usuario y 6 👎 / 0 👍, todos por el mismo fallo (hablar de otra marca).
Cableado con dúo: **puerta de acceso** por invitación de un solo uso (48 h, revocable, fail-closed con
gracia, tope diario, **chat privado obligatorio**), **errores con insights** (taxonomía por causa, red
global, `bot_errors` sin PII directa), **aislamiento por usuario PROBADO** (13 tests; cerrado el agujero de
la doble instancia que partía la sesión de un DG), y la **conducta (a)** ante marca cruzada con flag
apagado. Migraciones 015 y 016 **APLICADAS** (la 016 costó dos intentos: su validación con
`BEGIN/ROLLBACK` revertía el fichero entero — lección cableada como test). Suite 4192.

**s324f (17-ago) — LA PUERTA SE ENCENDIÓ Y EL PRIMER SMOKE REAL DESTAPÓ EL CATÁLOGO (DEC-232).**
Alberto puso `BOT_ALLOWLIST_BOOTSTRAP` + `BOT_ALLOWLIST=on` en Railway: la puerta está **ACTIVA en
producción** (log: «puerta de acceso ACTIVA … bootstrap=1 ids, tope diario=30») y su consulta la
atravesó (O2 ✅). Con eso preguntó «¿qué fabricantes tienes?» y el bot respondió **22 modelos de
756** bajo etiquetas de ingesta (`DESCARTADO`, `EN_unico`, `ES`, `PT`) y sin botones para
puntuarlo. Ninguna suite lo cazaba —los tests congelaban esa conducta como correcta—; lo cazó un
usuario en 30 segundos. Corregido con dúo r39 (13 hallazgos, ninguno SÓLIDO): la fuente pasa a
`get_manufacturers_by_docs()` (regla r27, que este atajo era el último en incumplir), se separa la
intención en el PLAN, y toda respuesta que no quepa **lo dice y ofrece el follow-up**
(`src/bot/acotar.py`, adjudicado por Alberto). **Panel web v1 construido y verificado**
(`dashboard/`, DEC-231): nada responde sin sesión, la service key no sale del servidor.

**s324f-noche (17/18-ago) — EL PILOTO ESTÁ VIVO Y YA HA ENSEÑADO CUATRO DEFECTOS (DEC-233).**
Alberto invitó a la primera usuaria (Sara, alta por invitación: **O3 verificado con tráfico
real**). En la primera hora: el bot le dijo «saturado» cuando lo que faltaba era **saldo** en la
cuenta de OpenAI de Railway (clave distinta de la local, ya corregida), y transcribió **«Detnov»
como «Death Knob»**, dejando el turno sin fabricante. Los dos arreglados y **desplegados**
(commit `5eda845`, verificado). Además, abrir el panel en un navegador destapó que **su propio
login daba 403** y que **la portada decía «0 errores» habiendo dos**. Dúo r40: Sol 8/8
confirmados — el mejor me hizo mover la corrección de voz porque rompía un contrato ya escrito.
Aviso **v9** desplegado. Suite **4373**.

**Qué sigue (s324f — VIGENTE; LO PRIMERO al abrir sesión):**
(0-0) **DE ALBERTO, cuando se levante**: (a) **volver a aceptar los términos** (`/start` +
`/accept`) — el v9 invalidó el v8, y Sara también tendrá que hacerlo; (b) **smoke de audio**
—preguntar por Detnov por voz— que es lo único que los arreglos de esta noche NO ejercitan;
(c) aplicar `migrations/017_bot_errores_clase_cuota.sql` y **sólo entonces** avisarme para
cambiar la clase en el código (al revés se pierde el registro).

(0-a) **DESPLEGAR lo de esta sesión**: PR → merge → Railway. Incluye el catálogo arreglado (que
hoy sigue roto en producción) y el panel, que además necesita **servicio Railway aparte** +
`DASHBOARD_SECRET` y `DASHBOARD_USUARIOS` (el hash lo genera
`scripts/s324f_dashboard_password.py`, que pide la contraseña por `getpass` y no guarda nada).
(0) **PILOTO DG — lo que falta es de Alberto**: (a) **abogado** = aviso v8 (redactado, 6 decisiones
resueltas) + texto de `bot_errors` + plazo de 24 meses de las tablas nuevas + el aviso de canje comunica
nombre/alias de quien canjea; **paquete listo para reenviar en `docs/PAQUETE_ABOGADO_PILOTO_DG.md`**;
(b) ✅ **HECHO** — PR #278 mergeada y Railway desplegó (SUCCESS 17-ago 16:18; log de arranque: «Bot
started» + el WARNING que declara la puerta apagada: el código está en producción e INERTE);
(c) **encender** `BOT_ALLOWLIST_BOOTSTRAP=<id>` y luego `BOT_ALLOWLIST=on`. ⚠️ **Matiz verificado
17-ago**: el motivo original del orden («al revés te quedas fuera de tu bot») **ya no aplica** — la
migración 016 hizo el bootstrap EN LA BASE y la fila de Alberto está activa (`origen=bootstrap`,
`alta_por=migracion_016`), y la puerta autoriza desde la base. Pero la variable **sigue haciendo falta
por otras dos razones**: el **aviso de canje** se manda a `ids_bootstrap()` —sin ella la contramedida
anti-reenvío se queda muda— y es el único camino que funciona con Supabase caído;
(d) invitar al PRIMER DG y hacer el **smoke real** (el harness no atraviesa `mismatch`: su testigo es
Telegram, no el eval); (e) medir la cobertura de la corrección en `rag_trace ? 'mismatch_corrected'`.
Criterio de GO: O1-O4 en `evals/s324e_allowlist_duo_r1_v1.md`; **NO-GO si fallan O1 u O4**.
(0-bis) **Pendiente técnico del piloto**: escribir la política de retención de las dos tablas nuevas en
`rgpd_retencion_pasada` (una función y dos UPDATE) cuando el abogado se pronuncie.
(0) **CABEZA DE COLA — el ruler y N=1**: decidir si los hechos no-OK se miden con N≥3 antes de etiquetarlos (9/15 son
ruido hoy). Afecta a cómo se lee CUALQUIER delta y a qué cola de defectos se ataca (6, no 15). Diseño + dúo pendientes.
(a) **Alberto, con lo preparado delante** (todo ⏳ en los packets canónicos): **bloques E1b** — un «sí» por bloque =
re-dry-run del mismo sha + `--aplicar` (cross-bloque morley↔unresolved/notifier exige adjudicar homónimos); las
3 preguntas de §0.D (MADT015_01 ¿NFS2-8?, MNDT600 ¿familia SMART 3?, MNDT701 sin id) · paraguas «2X-A» (¿con
2X-AT dentro?) · nombres con barra (10) · baja del FR `996-130` · packet **gold-review de conducta** (3 hechos ×
3 opciones) · ¿GO sobre «1 hecho» para D1? (recomendación: NO; si GO, definición A pineada + G2 antes de G3).
(b) **E2**: re-derivar snapshot + G1/G2 tras cada lote (conservador PASS hoy) antes de cualquier swap.
(c) Etapa 3 sin lever de serving: la varianza de síntesis (4/4 flips) es OTRA clase — si se quiere atacar, es
diseño nuevo con pregunta cero (¿medir con N≥5 por hecho antes de etiquetar el FULL?), no D1.
(d) ~~#89~~ ~~#86~~ hechos (s324d) · **#88: un «sí» de Alberto aplica los 55 retags** (`scripts/s324d_retag_documents_pm.py --aplicar`) ·
#87 OCR TI-007: sin pipeline OCR (Alberto aporta PDF OCR-izado o se diseña el paso con dúo) · #84 doc_map como
fuente de aplicabilidad (dúo).
(e) DEC-226 (conducta `mismatch`, decisión de producto multi-modelo) y DEC-186b siguen donde estaban.
(f) podar el PLAN (>160 KB).

## Estado anterior (s324 — 16 ago 2026)

**s324 — el residuo de los packets se adjudica por REGLAS, no por filas; y las puertas
prueban antes de escribir (DEC-225).** Alberto no firmó 911 filas: firmó **7 reglas** (R1
serie×categoría en el residuo · R2 confirmar solo modelos concretos nombrados como sujeto —
las etiquetas de familia son paraguas, nunca producto · R3 OEM no amplía `vendido_bajo` ·
R4 alta+doc_map solo con cita, jamás por ficha · R6 fuente retirada → no alta · R7 concatenados
→ componentes con cita propia · R5 → BAJA de 6 fragmentos PT con hermano ES + OCR de TI-007).
Con eso: **lote aplicado con recibo** (`evals/s324_lote_firmado_aplicar_20260816T113215Z.json`):
doc_map **+57 filas / 225 entries** (§0.B completo + §1.A por reglas + docs sustentantes), **13
altas** (KE-DP312x mini-familia + componentes R7), **7 confirmaciones** (DX1e/2e/4e + cajas —
cierra el ÚNICO agujero de paraguas del catálogo, «Dimension» 0/3 → 3/3 — y VSN 12 PLUS), 2
etiquetas retiradas (`2x-at`, `vsn-plus` → paraguas `2X-AT`/`2X-A Táctil`/`VSN PLUS`), 2 retags
DB con CAS (Qref INSPIRE mal etiquetada `CLSS-10`; KE-IO3144/IU3110 → IO3122/IO3144), 7 docs
retirados del corpus. **Todo por puertas que prueban**: cita verificada full-text en cada fila,
freeze (sha×4 + fingerprint + snapshot), build-validar-backup-swap, CAS con rollback, **censo del
radio de explosión** (detector del resolver 1.667→1.695, +28/−0; 0 gold perdidas; 0 disparos en
36 negativos; `resolve_query` sobre las 51 gold: 0 pérdidas / 9 ganancias), verificación
posterior en censo 0 fallos, suite 3.890 verde. **Dúo r32** (Sol 6/6 confirmados: freeze,
atomicidad, CAS documents, censo solo-detector, **R1' no firmada**, sobre-afirmación; Fable 5/6 +
1 premisa falsa) aplicado ENTERO antes de escribir. **Puerta A rehecha y VALIDADA** (predicado de
reconstruibilidad: 5/5 positivos, 3/3 negativos) — 0/18 filas RETIRAR de E1b son de esa clase
(palabras genéricas/part-numbers → siguen en cuarentena). Los packets que Alberto abre llevan el
ESTADO fila a fila (✅ resuelto / ⏳ suyo). **Deuda nueva #86** (Fable fabricó una transcripción
de tools: 0 `tool_use` reales; el emparejamiento se rompió al mover HEAD durante su run), **#87**
(ingestas vacías <300 chars: TI-007 47 chars, QR Morley-IAS Max 142 → OCR/baja), **#88**
(`documents.product_model` con artefactos residuales tras E3: TO-3200M, LOCAL-360…).

**Qué sigue (s324 — VIGENTE, consolidado; LO PRIMERO al abrir sesión):**
(a) **lo que solo puede firmar Alberto** (todo listado en el bloque 🟢 al inicio de
`s320_e1_packet_adjudicacion_v2.md`): **R1'** («si el doc NOMBRA modelos, atestar solo los
nombrados» — 3 docs 2X-A/2X-AT en espera), §0.C/§0.D/§0.E de E1 (sus «sí» pasan por el gate del
detector), nombres reales con barra (10), paraguas «2X-A» (frenado por el gate léxico), baja del
fragmento FR `996-130`, VSN2-PLUS/«Plus2»; los bloques E1b (474) y E2 (562) siguen abiertos y su
«sí» se aplica por lotes MEDIDOS (censo + gate), no en seco. (b) **Re-juicio K=5 cross-model** de
la clase «confianza media con sujeto nombrado» (E1 14 + E1b 42) → lo convergente sube a bloque
(NO se aplica). (c) **Re-derivar el snapshot E2** (`s320_e2_snapshot_derivado.py`) y pasar G1/G2
tras el cambio de catálogo, antes de cualquier swap. (d) **#80/#81**: las fases A (repunte 49), B (resolución TIPADA en la ingesta) y C
(gate de invariantes corpus↔catálogo) quedaron APLICADAS en s323 (PRs #266–#268); resta solo el
backfill #81 por igualdad exacta de sha → packet (pocos o ningún caso, y es lo correcto). (e) ~~**FULL fresco v3.2** — sigue sin medirse el bot e2e desde el elefante~~ **HECHO (16-ago tarde, PR #273): 116/135 OK (86%), paridad con s291; los 6 golds de la sentada por hecho = lo pretendido, 0 regresiones; fila 2026-08-16b en el scoreboard.** El censo; el censo
de s324 NO mide retrieval/generación. (f) smoke de recepción en cloud (DEC-220). (g) OCR de TI-007
+ censo de ingestas vacías (#87). (h) #86: endurecer el runner Fable (exigir `tool_use` reales o
marcar `sin_tools`) y no commitear durante un run emparejado. (i) **s321-ruler: su «Qué sigue» de la MAÑANA está SUPERADO por la tarde autónoma (PRs #273/#274).**
Estado real de los 5: **re-medir factlevel HECHO** (smoke #271 + FULL #273) · **#84 «medido»** — ⚠️ **s324d: era un NO-DATO** (el flag `ANSWER_OBLIGATION_PLANNER` no existe en Railway ⇒ `_product_aligned_chunks` no corre en producción; ver `TECH_DEBT #84`) · **sonda `hp013#1` hecha** (NO_ALCANZABLE; sale
de la población de lever B, que queda en ≥2) · **conducta (a) del `mismatch` NO cableada A PROPÓSITO**
(DEC-226: 4 subsistemas + una decisión de producto de Alberto) · **DEC-186b NO escrita A PROPÓSITO**
(reconciliación de 4 docs + prereg + pregunta cero de Alberto).
(j) **NUEVO, del FULL — la cola de síntesis DIMENSIONADA**: de los 19 hechos no-OK, **12 son de síntesis
y 10 de ellos son «servido y OMITIDO»** (el carrier llega al generador y el LLM no lo dice), repartidos
**1 por gold en 10 preguntas distintas** — no hay preguntas rotas, hay UN mecanismo. Solo **4 de los 12
tienen sonda de alcanzabilidad** (Protocolo 4): `hp017#2` y `hp003#4` **atacables PROBADOS** (0/5→5/5),
`hp011#2` **no** (0/5→0/5), `cat017#2` ya flipeó a OK. **Los 8 restantes están SIN SONDAR, ~$1 cada uno**
⇒ el movimiento barato y correcto antes de diseñar ningún lever es **sondarlos** y saber si hay población
(la pregunta abierta de DEC-175). Análisis: `evals/s321_full_analisis_fallos_v1.md`; **encargo listo para ejecutar** (los 8 con su modo, su `--span-grep` propuesto y las 3 trampas conocidas): `evals/s321_encargo_sondas_etapa3_v1.md`.

## Estado anterior (s321-ruler — 16 ago 2026, sesión paralela)

**s321 — la sentada B2 APLICADA al ruler (DEC-224), y por el camino el instrumento se
arregló dos veces.** Arrancó como una pregunta de Alberto sobre el ítem 2 del packet y
acabó así: (1) **DEC-186 en revisión** — el «techo del modelo» de s305 nunca leyó al juez
(`sum()` sobre un dict → constante 2; TECH_DEBT #75) y su «NO alcanzable» de `hp017#2` no
era una medición: la sonda de alcanzabilidad se **endureció** (prueba de entrega +
cobertura atestada, `scripts/reachability_verdict.py`, 10 tests) y **DEC-173/175 reabiertas**
(la población de lever B es ≥3, no 1). (2) **DEC-221**: el gold se ancla en el pasaje que da
el **mecanismo** — nació de un caso (PEARL A5.2/A5.4) y se pagó solo en el siguiente (ISO-X
p17/p77). (3) **DEC-223**: el ISO-X **no** acota un fallo de tierra — cerrado dentro del manual
aplicable, y con el razonamiento de Alberto («si lo acotara no verías 'Tierra'»). (4) **DEC-224**:
los 6 golds de la sentada escritos vía `gold_store` con verificación COMPLETA (render ±1 →
cazó un off-by-one en MI-716; GPT-5.5 en frío coincidente 7/7; localización ES+EN por
`doc_map`), cascada s277 + canarios en el mismo commit, **sin migración de índices** (no partir
`hp017#2`, que es release_guard). Y la **conducta ante marca↔producto errónea pasa a (a)
«corregir Y responder»** — decisión de producto, **pendiente de cablear** (serving, dúo, PR
propio); `hp002` NO es su testigo (el harness no atraviesa `mismatch`). Deuda nueva: **#83**
(capa visual de criticidad perdida), **#84** (`product_model` ≠ aplicabilidad: 35% de discrepancia
con `doc_map`, censo ejecutado), **#85** (guard de paridad lee `GENERATOR_INCLUDE_CONTEXT` con
distinta semántica que su consumidor). Y un guard que se apagaba en silencio en la suite
(`test_s321_reachability_delivery_proof`) — arreglado junto con la fuga de entorno de `s156` que
lo destapaba. Dúo: 4 rondas Sol (v1→v4) + Fable emparejado, **0 falsos positivos**; lo que el dúo
no cazó lo cazó Alberto dos veces (2222 como suppl; A5.4 es un EJEMPLO).

**Tarde autónoma (16-ago, Alberto fuera; DEC-226)** — hecho: smoke (#271) y **FULL** (#273) de
factlevel sobre el ruler nuevo: 116/135 OK, paridad con s291, los 6 golds de la sentada por hecho =
exactamente lo pretendido, 0 regresiones; `hp013#1` bajó a retrieval-miss (raw=0). **#84 «medido» en
serving (⚠️ s324d: NO-DATO — el flag no existe en Railway)**: 12,7% de chunks primary fuera del alineado, concentrado en 8/23 golds (hp006 48% · hp021 62% ·
cat008 100%; S141 no rescata ninguno). Dos cosas se llevaron **a propósito sin cablear/escribir**
tras dúo: la conducta (a) del `mismatch` (2 rondas Sol: 4 subsistemas + decisión de producto
multi-modelo — `s321_mismatch_conducta_a_propuesta_v3.md`) y DEC-186b (2 rondas Sol NO SÓLIDO:
reconciliación de 4 docs + prereg — `s321_dec186b_propuesta_v3.md`). 0 falsos positivos en 6 rondas.

**Qué sigue**: (1) **decisión de producto** multi-modelo en `mismatch` (DEC-226 recomienda «fuera de
alcance en v1») → sesión dedicada de cableado con dúo; (2) DEC-186b como reconciliación de
DEC/PLAN×2/LEVER_DIGEST/#75 con vocabulario único + pregunta cero (¿medir el eje modelo?); (3) #84:
proponer fix con dúo (el daño ya está medido) — el `doc_map` como fuente de aplicabilidad; (4)
`hp013#1`: el carrier ya no entra al pool — ver sonda `serve`; (5) podar el PLAN (154 KB).

**Qué sigue**: (antes de la tarde: (1) cablear la conducta (a);
(2) reescribir DEC-186 con su número real (dúo propio) y la raíz de #75; (3) #84 medir el daño
en serving antes de tocar `_product_aligned_chunks`; (4) sonda `hp013#1` para afinar la población
de lever B; (5) re-medir factlevel (los golds cambiaron: 4 cores nuevos, 1 demote, 1 entra al
denominador) — smoke antes del full.

## Estado anterior (s323 — 15 ago 2026)

> **ACOTADO en s325 (18 ago 2026, addendum DEC-220)**: el alcance ADOPTADO es
> **Cloud + Dispatch**; Remote Control queda documentado pero **NO activado**. No deja
> hueco: Dispatch abre sus sesiones EN EL PC, así que cubre igual lo que necesita
> OneDrive. Y la DB no exige tocar nada en Supabase (`service_role` por REST para datos;
> para DDL, `DATABASE_URL` por el pooler IPv4 o el conector MCP).


**s323 — «dónde corre Claude» montado (DEC-220)**: las TRES superficies quedan
cubiertas — **Cloud** (VM de Anthropic, sigue con el PC apagado), **Remote Control**
(la sesión corre en el PC y se dirige desde el móvil) y **Dispatch**. El hallazgo de
rumbo: **Remote Control cierra el gap que `ENTORNO_CLOUD.md §3` daba por perpetuo**
(OneDrive) — la ingesta ya es gobernable desde el móvil, ejecutándose en local.
Alberto adjudicó **un environment con todas las keys y red Full**, con el riesgo
declarado (no hay secret store). Nacen `scripts/cloud_smoke.py` + tests (verificador
con recibo, contrato de no-fuga de secretos), el hook de arranque pasa a ser
**idempotente**, y `ENTORNO_CLOUD.md` se reescribe contra la doc vigente. Dúo Fable:
NO SÓLIDO → 3 hallazgos aplicados (el mejor: el centinela del hook no sondeaba
`cryptography`, justo el módulo que motivó el hook en s315). **Queda pendiente el
smoke de recepción EN cloud** — sin ese recibo esto es aparato preparado, no entorno
verificado. Deuda nueva #79 (el revisor adversarial es ciego a `.claude/`).

## Estados anteriores a s323 — ARCHIVADOS en HISTORY (s324d, 17 ago 2026)

Los bloques «Estado anterior» de **s322b, s314, s293, s292, s291, s290, s289, s288c, s286, s285, S277
(con el cierre operativo de la P1 fresca y su contexto histórico), S205, s129, s104, s103b, s103, s102,
s101, s100** y el «Qué sigue (s77)» con sus **Antecedentes s69–s83** viven ahora en
[`docs/HISTORY.md`](HISTORY.md) → sección **«Archivo del PLAN — estados anteriores s100→s322b (movidos en
s324d)»**, con su texto íntegro y sus anclas (`estado-anterior-s205--18-jul-2026`). Motivo: el PLAN se relee
en cada arranque y había vuelto a superar los 160 KB (DEC-036/s56: el PLAN se mantiene COMPACTO; el estado
vigente son los 4 últimos bloques + «Qué sigue»). Nada se ha reescrito: es un movimiento, no una edición.

**Roadmap macro (vigente desde s77; rationale en HISTORY):** F1 calidad (levers de retrieval = rendimiento
decreciente; el ±2 del ruler es el techo) → **F2 escala (identidad de producto en ingesta = EL siguiente
bloque; el elefante DEC-074 se completó en s320-s321 y hoy se gobierna por catálogo + packets)** → F3
routing/tool-use + multi-dominio del scope M&A → F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).
