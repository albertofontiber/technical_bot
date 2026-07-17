# Deuda técnica consciente

Lista de mejoras conocidas que hemos **decidido posponer explícitamente**. Cada entrada tiene un *trigger condition*: la señal concreta que indica que ha llegado el momento de implementarla. No son fechas — son condiciones del sistema.

Si alcanzas un trigger, para y refactoriza antes de seguir añadiendo features.

> **📍 Mapa canónico:** este doc = **deuda con triggers**. El roadmap + estado vigente es
> canónico en `PLAN_RAG_2026.md`; el *por qué* de las decisiones de impacto med/alto en
> `docs/DECISIONS.md`.

---

## Índice de estado (s196 — 17 jul 2026; generado, no renumera)

- **Abiertos (trigger-gated):** #1, #2, #3, #5b, #5, #6, #7, #10, #11b, #12, #11g, #11h, #13, #15, #17, #18, #19, #20, #21, #22, #23, #25, #26, #27, #28, #29, #30, #31, #18, #32, #33, #34, #35, #37, #39, #40, #41, #44, #45, #47, #48, #49, #50, #51, #52
- **Parciales / elevados:** #8, #11f, #24, #53
- **Cerrados (✅ resueltos o 🔴 revertidos):** #4, #9, #11, #11c, #11i, #11d, #14, #16, #36 (✅ s88: cross-model agéntico con tools read-only, paridad con el sub-agente), #38, #42, #43 (✅ COMPLETO: capa A s63/DEC-044 + capa B s65/DEC-046; escritor-en-ingesta → PLAN punto 2), #46 (✅ s64/DEC-045)

Nota: hay dos items "## 18" (judge false positive, sesión 14; y atribución de fabricante, 28 mayo) —
se conservan ambos números porque las referencias cruzadas en DECISIONS/memoria los citan; el índice
y las citas nuevas deben desambiguar por título.

---


## 1. Externalizar overrides de modelo/categoría a YAML

**Estado actual**: Los dicts `{MANUFACTURER}_SOURCE_FILE_TO_MODEL` y `{MANUFACTURER}_SOURCE_FILE_TO_CATEGORY` viven hardcoded en `src/ingestion/chunker.py`.

**Problema**: Cambiar una categoría requiere editar código Python y hacer deploy. No escalable si un no-dev (p.ej. un técnico PCI) tiene que corregir mappings.

**Trigger para implementar**:
- El total combinado de entradas en los dicts de override supera **~300 filas**, O
- Un no-desarrollador necesita editar los mappings de forma recurrente, O
- Tenemos **5+ fabricantes** con overrides activos

**Solución propuesta**: Mover a `config/overrides/{manufacturer}.yaml`, cargar al arrancar. Un test de CI valida el schema.

**Coste estimado**: ~2h

---

## 2. Hash-based keys en lugar de filename stem

**Estado actual**: Los overrides usan `Path(filename).stem` como clave. Si el CMS del fabricante renombra un PDF, el override deja de aplicarse silenciosamente y el archivo vuelve a metadata por keywords (peor calidad) sin aviso.

**Problema**: Fragilidad silenciosa. El test del punto #3 lo captura parcialmente (detectaría "unmapped"), pero no detectaría un filename *nuevo* que deberíamos mapear.

**Trigger para implementar**:
- Un scraper de re-descarga encuentra **≥3 filenames que han cambiado** respecto a la versión anterior, O
- Una regresión silenciosa en el eval se rastrea hasta un rename del CMS

**Solución propuesta**: Clave = SHA-256 del contenido del PDF (primeras 10 páginas). Script `scripts/generate_override_keys.py` que recorre la carpeta y produce las claves.

**Coste estimado**: ~1h

---

## 3. Versionado de ingesta (`ingestion_run_id`)

**Estado actual**: La tabla `chunks` no tiene una columna que identifique a qué "corrida" de ingesta pertenece cada chunk. Para re-ingestar un fabricante usamos el workaround `DELETE WHERE manufacturer='X'` seguido de INSERT.

**Problema**: No hay rollback. Si una re-ingesta introduce una regresión, no podemos volver a la versión anterior sin re-descargar y re-procesar todo. Tampoco podemos hacer A/B de dos estrategias de chunking sobre el mismo fabricante.

**Trigger para implementar**:
- Primera vez que necesitamos re-ingestar un fabricante por **segunda vez** (= segundo ciclo de re-ingesta), O
- Queremos comparar dos estrategias de chunking/embeddings en paralelo, O
- Detectamos una regresión en producción y no podemos rollback en <10 min

**Solución propuesta**: Columna `ingestion_run_id UUID`, tabla `ingestion_runs` con metadata (timestamp, git sha, chunker version, manufacturer, n_chunks, status). Query de retrieval filtra por `status='active'`. Rollback = flip del flag.

**Coste estimado**: ~3-4h

---

## 4. Gestión de revisiones de documentos — 🔼 ELEVADO A TAREA PRÓXIMA (1 jun 2026); Phase 1 ✅ sobre tabla vieja, chunks_v2 SIN metadata de revisión

**Estado actual (16 abril 2026)**: **Phase 1 COMPLETADA**. Tabla `documents` creada (866 filas), `chunks.document_id` FK añadida y poblada al 100% (150,695 chunks vinculados). Phase 2 pendiente (revision_parser.py para extraer revisión/fecha de filenames). Phase 3 pendiente (re-hash con SHA-256 real para reemplazar placeholders 'backfill:'). Ver `docs/DOCUMENT_MANAGEMENT.md` para el diseño completo y `migrations/001_document_management.sql` para el schema.

**Estado en chunks_v2 (corpus de PRODUCCIÓN — verificado en `migrations/006_chunks_v2.sql`, 1 jun 2026)**: chunks_v2 NO tiene ninguna columna de revisión/fecha/estado — solo `document_id` (FK a `documents`), `source_file` y `page_number`. Las RPC `match_chunks_v2`/`search_chunks_text_v2` tampoco filtran por revisión. → el bot **puede servir una revisión obsoleta** y NO puede aplicar la conducta "latest-wins" (`RULER_DESIGN §1:67-72`). La Phase 1 (FK `document_id`) se hizo sobre la tabla VIEJA `chunks` (150,695 filas); el SWAP a chunks_v2 (sesión 27) dejó este corpus sin esa gestión.

**Problema original**: Tratamos cada PDF como un documento independiente identificado por su filename. No sabemos si dos PDFs son:
- (a) revisiones sucesivas del mismo manual (p.ej. `... rev 3` vs `... rev 4`)
- (b) partes distintas de un mismo documento multi-hoja (p.ej. `MADT951_01` + `_02` + `_03` son las 4 páginas de una misma hoja de instrucciones)
- (c) versiones en distintos idiomas del mismo contenido

**Problema**: Si el fabricante publica una revisión nueva y nosotros descargamos ambas, el RAG puede devolver la versión obsoleta, o mezclar fragmentos de ambas. No tenemos forma sistemática de:
1. Saber cuál es "la revisión más actual" que debemos apuntar
2. Saber si una rev nueva es un reemplazo total o un cambio parcial (merge diff)
3. Retirar chunks de la revisión obsoleta cuando llega una nueva

**Ejemplos detectados en scrape Notifier privado (abril 2026)**:
- `MADT731_01/_02/_04/_06` — probablemente multi-parte, no revisiones
- `AM-8100 manual de usuario y programacion rev 4 30-10-2024.pdf` — rev 4, ¿dónde están rev 1-3?

**🔼 ELEVADO A TAREA PRÓXIMA (decisión de Alberto, 1 jun 2026)** — ya NO trigger-gated.
**Motivo (traza)**: (1) riesgo de corrección en producción — citar una revisión caducada a un técnico; (2) es prerrequisito para que el ruler/bot pueda aplicar la conducta "latest-wins" (`RULER_DESIGN §1:67-72`), hoy inexpresable sin la metadata. Los triggers originales —que NO se cumplen hoy: >20 colisiones de filename-base, un técnico reporta versión obsoleta, o re-scrapes periódicos— quedan como contexto histórico, **superados** por la decisión de elevar.

**Solución propuesta**:
1. Campo `document_family` en `chunks` = base normalizado (ej: "AM-8100 manual de usuario")
2. Campo `revision` + `revision_date` extraídos del filename (parser heurístico) o del PDF (primeras páginas)
3. Al ingestar, si ya existe una revisión anterior del mismo `document_family`, marcarla como `superseded` (no borrar) y usar la nueva por defecto en retrieval
4. Parte (b) — multi-parte — se detecta porque los `_01/_02/_03` son consecutivos y el tamaño es pequeño: se unen en un único chunk group
5. Herramienta CLI: `scripts/diff_revisions.py prev_rev.pdf new_rev.pdf` — resumen de qué páginas cambiaron, para decidir si es rewrite total o diff

**Coste estimado**: ~4-6h (el parser de revisiones es el 70% del trabajo)

**Spec de precedencia (s76, DEC-058): `evals/_s76_revision_contract_spec.md`** — la ÚNICA clase estructural que
el lever-phase de retrieval NO tocó (cat009/cat024; cat008 es OEM-relabel→identidad #43/#49, NO este contrato).
Añade el **árbitro de precedencia** (revisión=latest-wins vs variante-regional=answer-con-conflicto vs OEM vs
multi-parte vs datasheet; regla rectora: ante duda NO supersede) + **validación judge-free** (paridad de POOL
servido, NO veredicto; desacoplada del dual-judge — solo el win end-to-end de 2 golds < ±2 lo necesita). **Vía
corregida (s76, pushback de Alberto + verificación DB): BACKFILL guardarraíl-eado s64-style, NO re-ingestión ni
DDL.** `documents` YA tiene las columnas (status/revision/revision_date/document_family/superseded_by_id);
`revision_date` poblado **1/1170** = el gap real que llena el parser Phase 2 (el 70%); `document_family` 1170 pero
**filename-naive** (s62) → re-derivar para agrupar revisiones; el `_filter_by_document_status` de s64 (DEC-045) YA
excluye `superseded` (precedente: 3 cadenas pobladas retroactivamente sin re-ingestar). El escritor-en-ingesta
(#43 capa B) = solo para no re-crear el hueco a FUTURO, NO bloqueante → #4 es **candidato cercano** (ciclo de
backfill propio), no gated a la ingesta lejana.

---

## 5b. Tratamiento de centrales de detección de gas en la taxonomía

**Estado actual (decidido 16 abril 2026)**: La categoría `Centrales de incendios` agrupa centrales de fuego Y centrales de detección de gas (PL4, AM-8200G de Notifier; CS-4, CA-2/4/8 de Detnov). Decisión consciente para evitar fragmentación cuando el volumen de gas es bajo (~6-8 familias en total). Ver comentario explicativo en `chunker.py` y guidance en `scripts/classify_general_chunks.py`.

**Problema potencial**: Dos cosas distintas conviven bajo un nombre que dice "incendios":
1. El nombre puede engañar al filtrar (`category='Centrales de incendios'` también devuelve paneles de gas)
2. La detección de gas se rige por normas distintas a EN 54 (EN 50545 para parking, EN 60079 para atmósferas explosivas), así que técnicamente son productos diferentes

**Datos que motivaron la decisión actual**:
- Detnov: 4 modelos de central de gas (CS-4, CA-2, CA-4, CA-8) en tarifa 2026
- Notifier: 2-3 modelos confirmados (PL4, AM-8200G, posiblemente Galileo)
- Total estimado: ~6-8 familias → fragmentación marginal
- El bot es Q&A, no catálogo: técnicos preguntan "cómo programo el CA-4", no "muéstrame todas las centrales de gas"
- Inconsistencia residual: los **sensores** de gas ya están en `Detectores puntuales` → split parcial existente, separar centrales no la cura

**Trigger para implementar splitting**:
- Un técnico se queja de que el filtro `Centrales de incendios` le mezcla paneles de gas que no esperaba, O
- El número de centrales de gas crece a >20 familias y la fragmentación deja de ser marginal, O
- Detectamos confusión sistemática del bot al razonar sobre productos de gas vs fuego

**Soluciones disponibles (cuando se dispare el trigger)**:

**Opción A — Renombrar a `Centrales de detección`** (más sencilla):
1. `UPDATE chunks SET category='Centrales de detección' WHERE category='Centrales de incendios'` (también `documents`)
2. Renombrar key en `_CATEGORY_KEYWORDS` en `chunker.py`
3. Actualizar prompts del retriever/generator si nombran la categoría explícitamente
4. Coste: ~1h

**Opción B — Crear categoría dedicada `Centrales de detección de gas`** (más limpia):
1. Añadir nueva entry en `_CATEGORY_KEYWORDS` con keywords: PL4, AM-8200G, CS-4, CA-2, CA-4, CA-8, "central de gas", "detección de gas", etc.
2. UPDATE manual o LLM-asistido para reclasificar las filas existentes
3. Coste: ~2-3h (incluye reclasificación de datos existentes con verificación humana)

Preferir B si se llega al trigger por volumen alto (>20). Preferir A si solo es cuestión de nombre engañoso.

---

## 5. Agrupación de fabricantes por grupo corporativo

**Estado actual**: Tratamos `manufacturer` como string plano (ej: "Notifier", "Morley", "Detnov"). Notifier y Morley son ambas marcas de Honeywell, pero esa relación no está modelada.

**Problema**: Si en el futuro queremos razonar sobre compatibilidad entre marcas del mismo grupo (ej: "este detector Notifier es compatible con esta central Morley porque ambos son Honeywell"), no tenemos forma sistemática de hacerlo. Hoy el bot trata cada manufacturer como independiente.

**Trigger para implementar**:
- Un técnico pregunta por compatibilidad cross-brand y el bot no puede responder bien, O
- Añadimos un 4º+ fabricante de Honeywell (ej: Gent, Esser) y la cuestión escala

**Solución propuesta**: Añadir columna `manufacturer_group TEXT` en `chunks` y `documents`. Valores: "Honeywell", "Detnov", etc. Backfill via SQL UPDATE.

**Coste estimado**: ~1h (schema + backfill + actualizar retriever + prompt)

---

## 6. Auditoría de idiomas en la BD de chunks

**Estado actual (detectado 17 abril 2026)**: Durante la revisión de los 64 documentos de `category='General'` descubrimos que `MADT236P` (impresora de la AFP4000) está 100% en portugués — el sufijo `P` del filename significa "Portugués". Mirando el resto de filenames de Notifier hay muchos candidatos con sufijo `P` (MNDT102P, MNDT105P, MNDT510P, MNDT515P, MNDT1003P, MADT236P, BTDT017, ETDT312, ETDT314, MADT575_01, MADT731_03_A, MADT742, MADT746_01, …) que podrían ser también portugueses. Puede haber también italianos o franceses sin detectar (`RP1R - MAN ITA r.A2` lo es explícitamente, `Smart 2_MT251_Ita-Eng` es bilingüe italiano-inglés).

**Problema**: La política del proyecto (`user_profile.md`) dice: *"Traducción: solo manuales 100% EN, multilingüe con ES no se traduce, otros idiomas caso a caso"*. Hoy no sabemos cuántos chunks tenemos en cada idioma distinto de ES/EN, así que no podemos aplicar la política. Peor: el retriever puede estar devolviendo chunks en portugués a técnicos que preguntan en español, sin que nos demos cuenta.

**Trigger para implementar**:
- **Inmediato tras cerrar el frente de `category='General'`** — aprovechar que estamos tocando estos documentos, O
- Un técnico reporta que el bot respondió citando contenido en portugués/italiano/francés, O
- Una ingesta futura (Morley u otro) añade un lote grande sin filtro de idioma

**Solución propuesta**:
1. Script `scripts/audit_chunk_languages.py` que:
   - Muestrea 2-3 chunks por `source_file` y detecta idioma con heurística simple (palabras función típicas: `the/of/and` → EN, `el/la/de/que` → ES, `o/de/que/não` → PT, `il/di/che/non` → IT, `le/de/et/est` → FR) o con `langdetect`/`lingua` si hace falta precisión
   - Dumpea inventario: `{source_file, manufacturer, language, n_chunks, confidence}` a `logs/language_audit.json`
2. Revisar el inventario caso a caso según la política existente:
   - PT/IT/FR 100% → decidir si traducir, filtrar del retrieval, o mantener
   - Multilingüe con ES → usar solo ES (filtrar el resto), política actual ya definida
3. Si se decide filtrar, añadir columna `language TEXT` a `chunks` (o usar el campo existente si ya hay) y filtrar en el retriever.

**Coste estimado**: ~2-3h (script de detección + análisis del inventario; la acción sobre los chunks depende de qué decida el usuario)

---

## 7. Bug de duplicación del chunker en datasheets multilingües + 3 re-ingestas pendientes

**Estado actual (detectado 17 abril 2026)**: Durante la auditoría de idiomas (TECH_DEBT #6) afloraron 3 documentos con counts de chunks anómalos. Investigación (`scripts/investigate_mega_docs.py`) confirmó duplicación masiva:

| source_file | páginas PDF | chunks totales | chunks únicos | ratio |
|---|---:|---:|---:|---:|
| `D1058-1_NFXI-WS-WSF` | 2 | 1.159 | 47 | 24,7× |
| `D1056-1_NFXI-BS-BSF` | 2 | 1.174 | 62 | 18,9× |
| `170020 ... TARJETAS IDIOMAS EXTINCION SUPRA REV A` | 1 | 138 | 39 | 3,5× |

Los 2.471 chunks se borraron el 17 abril 2026 vía `scripts/delete_pathological_chunks.py` (rollback snapshot en `logs/pathological_chunks_rollback_20260417T123104Z.json`). **Las filas en `documents` se conservaron** (`status='active'`), así que el path para re-ingestar queda abierto.

**Patrón sospechoso no explicado**: en los dos datasheets, los top-5 contenidos más repetidos aparecen **exactamente 80 veces cada uno**. Esa cifra constante sugiere un bucle en el pipeline — posiblemente `for each detected language × for each overlap chunk × ...`. Requiere instrumentación con logging para capturar en qué punto se multiplica.

**Característica común de los 3**: tablas densas multilingües (EN/FR/DE/IT/…) con mojibake en el TARJETAS. Probablemente el bug se activa por la combinación de (a) Vision + pdfplumber + PyMuPDF extrayendo la misma tabla 3 veces, (b) chunker aplicando overlap sobre contenido repetitivo, (c) algo en `language_filter` iterando por sección. No confirmado.

**Trigger para implementar**:
- **Antes de re-ingestar cualquiera de estos 3 docs** — el bug está latente hasta que se entienda
- O si aparece otro doc con `n_chunks / n_unique > 5` en cualquier auditoría futura

**Solución propuesta (pasos)**:
1. Reproducir el bug con uno de los 3 docs en modo `--dry-run` verbose (sin escribir a DB). Instrumentar contadores: "n_pages entered chunker", "n_chunks produced per page", "n_chunks after dedup".
2. Localizar el bucle responsable (hipótesis: `language_filter` × `enrich_with_tables` × chunker overlap).
3. Añadir guard en el chunker: si el hash de un chunk aparece >2 veces, deduplicar.
4. Re-ingestar los 3 docs. Verificar que `n_chunks ≈ n_páginas × factor razonable`.

**Coste estimado**: ~3-4h (investigación + fix + re-ingestar 3 docs)

**Sub-item (menor)**: inconsistencia en `documents.source_pdf_filename` — el backfill de Phase 1 guardó los stems **sin** `.pdf`, pero `document_registry.py` (ingesta moderna) los guarda **con** la extensión. No crítico, pero complica queries. Trigger: siguiente vez que toquemos la tabla `documents` en volumen; hacer un UPDATE normalizador para que todos terminen igual (decidir criterio: con o sin `.pdf`).

---

## 8. Observability + tabla `query_gaps` (tracking de qué manuales faltan) — 🟢 OBSERVABILIDAD GENERAL RESUELTA (sesión 21), `query_gaps` PENDIENTE

**Estado tras sesión 21 (27 abril 2026)**: la parte de **observabilidad general** está cerrada. `query_logs` ahora persiste cada interacción con `query`, `transcription` (si voz), `response` completo (truncado a 4096 chars), `chunks_used`, `response_time_ms`, `bot_version` (git short hash) y `telegram_user_id`. Tabla `feedback` activa para correcciones inline del técnico. Tabla `user_consent` añadida para cumplimiento RGPD (gate `/accept` antes de procesar queries). Migrations 004 + 005 aplicadas. Script `scripts/review_logs.py` exporta el corpus joineado a CSV/Excel para curar eval orgánico (DG-grade).

**Pendiente todavía**: tabla `query_gaps` específica con `review_status` para clasificar queries fallidas como `gap_propio` / `gap_terceros` / `added` / `discarded`. Hoy esta clasificación se hace fuera de banda (revisión manual del export de `review_logs.py`). Cuando volumen de queries del DG / técnicos crezca, conviene formalizar la cola priorizada en una tabla dedicada con SQL filtrable.

**Estado original (decidido 17 abril 2026)**: Hoy no existe ningún sistema de logging de las interacciones del bot. Se decidió en sesión que el bot debe registrar cada query donde responde *"no tengo este manual"* para construir la cola priorizada de ingesta futura.

**Problema que resuelve**: con 30+ fabricantes pendientes por añadir a la BD y un alcance que se expande fuera de PCI (rociadores, grupos de presión, CCTV, control de acceso), la priorización de ingesta debe guiarse por demanda real, no por intuición. El log de "gaps" es el indicador canónico.

**Dos tipos de gap que debe soportar el schema** (decisión deferida hasta tener volumen):
1. **Gap propio**: producto que las empresas del grupo sí instalan/ofrecen pero cuyo manual no se ha añadido aún. Prioritario.
2. **Gap de terceros**: sistema instalado por otros que los técnicos del grupo ahora mantienen. Caso nicho, decisión caso a caso.

Experiencia hacia el técnico: **la misma en ambos casos** (*"no tengo ese manual aún"*). La distinción es interna para priorizar.

**Trigger para implementar**:
- Junto con el primer deploy / piloto (sin deploy no hay queries reales que loguear), O
- Si antes del deploy se decide loguear las queries sintéticas del eval como dry-run del sistema de logging

**Schema propuesto** (tabla `query_gaps` en Supabase):
```sql
CREATE TABLE query_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    user_id_hash TEXT,           -- hash del Telegram ID (privacidad)
    query_text TEXT NOT NULL,
    model_mentioned TEXT,        -- extraído por el bot si lo detecta
    manufacturer_mentioned TEXT, -- idem
    bot_response_type TEXT,      -- 'not_found' | 'ambiguous' | 'answered' | 'error'
    review_status TEXT DEFAULT 'pending',  -- 'pending' | 'gap_propio' | 'gap_terceros' | 'added' | 'discarded'
    review_notes TEXT,
    added_at TIMESTAMPTZ          -- cuándo se cubrió el gap (si aplica)
);
CREATE INDEX idx_query_gaps_review ON query_gaps(review_status, created_at DESC);
```

**Observability más amplia** (relacionada, no bloqueante para este punto): además de `query_gaps`, el sistema debería loguear **todas** las queries (no solo las fallidas) con latencia, chunks recuperados, respuesta generada y (cuando haya feedback UI) rating del técnico. Esto es el prerequisito para eval continuo en producción.

**Coste estimado**: ~3-4h (migración SQL + instrumentación del generator + dashboard básico tipo SELECT agregados)

---

## 9. Verificación del pipeline de imágenes — ✅ RESUELTO (19 abril 2026)

**Resultado**: pipeline funciona end-to-end. `scripts/verify_image_pipeline.py` ejecutado el 19 abril tras arreglar un bug propio de paginación en el script (no del pipeline). Números finales por fabricante:

| Fabricante | Total chunks | Con diagrama | Con URL | % URL/diag |
|---|---:|---:|---:|---:|
| Notifier | 116.854 | 34.550 (29,6%) | 29.058 | 84,1% |
| Detnov | 17.582 | 7.004 (39,8%) | 6.289 | 89,8% |
| Morley | 13.788 | 4.604 (33,4%) | 3.852 | 83,7% |
| **Total** | **148.224** | **46.158 (31,1%)** | **39.199** | **84,9%** |

15/15 URLs sampleadas al azar respondieron HTTP 200 desde Supabase Storage. La capacidad de adjuntar diagrama en el generator + `bot.reply_photo()` está confirmada con el flujo real.

**Follow-up residual → TECH_DEBT #10** (huérfanos: 6.959 chunks con `has_diagram=true` pero `diagram_url IS NULL`, el 15,1% de los diagrammed). No bloquea el eval.

---

## 10. Chunks huérfanos de imagen (`has_diagram=true` pero `diagram_url IS NULL`)

**Estado actual (detectado 19 abril 2026)**: 6.959 chunks (15,1% de los 46.158 con `has_diagram=true`) están marcados como que tienen diagrama pero su `diagram_url` es NULL. Distribución por fabricante (derivada de los totals de coverage):

| Fabricante | Diagrammed | Con URL | Huérfanos | % huérfano |
|---|---:|---:|---:|---:|
| Detnov | 7.004 | 6.289 | 715 | 10,2% |
| Notifier | 34.550 | 29.058 | 5.492 | 15,9% |
| Morley | 4.604 | 3.852 | 752 | 16,3% |

**Patrón observado en dos muestras independientes**:
- Primera muestra (`logs/image_pipeline_audit.json` original): los 10 chunks pertenecían todos al doc Detnov `55320011 Manual zocalo con relé Z-200-R` en páginas FR/IT/EN. Sugería causa multilingüe: el extractor guardó solo la imagen ES y los chunks de páginas no-ES quedaron sin URL.
- Segunda muestra (tras re-ejecución con el script arreglado): 10 chunks de 5 docs distintos (`ASD535_TD_T131192es_h`, `MN-DT-951_v7.2`, `MCDT155`, `ASD531_OM_T811168es_b`, p4-64). El patrón "mismo doc multilingüe" no se reproduce — la causa es más amplia.

**Hipótesis a verificar** (ordenadas por probabilidad):
1. Páginas "visualmente vacías" (portadas, índices, páginas de separadores) donde la heurística de diagramas devuelve *true* falsamente pero el extractor no genera imagen útil que subir.
2. Páginas multilingües con el chunker emitiendo N copias (una por sección/idioma) pero el pipeline de imágenes solo sube 1 archivo por página — N-1 quedan sin URL.
3. Fallos silenciosos durante la subida a Supabase Storage en la sesión 6 (Notifier EN→ES traducido) — la traducción se aplicó a los textos pero las imágenes quedaron sin re-enlazar.
4. Mismatch entre `source_file` en el chunk y el `source_file` usado para derivar la URL durante la subida (encoding de espacios, acentos, guiones).

**Por qué no bloquea el eval**: 84,9% de los diagrammed tienen URL válida y 15/15 URLs sampleadas respondieron HTTP 200. La capacidad del bot de adjuntar diagramas está demostrada. Un técnico verá imágenes en la mayoría de queries relevantes.

**Trigger para investigar**:
- Si una pregunta del eval requiere explícitamente diagrama y falla, O
- Si el ratio de huérfanos crece al añadir un fabricante nuevo (señal de bug sistemático, no accidental), O
- Si hay que re-ingestar cualquiera de los 3 docs de TECH_DEBT #7 (aprovechar para instrumentar el pipeline de imágenes y cerrar esto)

**Solución propuesta**:
1. Script `scripts/inspect_diagram_orphans.py` que agrupe los 6.959 por `source_file` y `page_number`, cuente huérfanos por doc, y muestree contenido de 20 chunks representativos.
2. Clasificar los 4 buckets de la hipótesis y cuantificar cuántos huérfanos caen en cada uno.
3. Para buckets 1-2: normalizar la bandera `has_diagram` (ponerla a false cuando corresponda) para evitar que el generator intente adjuntar una imagen que no existe.
4. Para buckets 3-4: script de reparación que re-derive `diagram_url` desde `source_file + page_number` y compruebe que el objeto existe en Storage.

**Coste estimado**: ~2-3h (script de diagnóstico + clasificación + fix según bucket dominante).

---

## 11. MODEL_PATTERN incompleto + sin normalización de separadores — ✅ RESUELTO (20 abril 2026)

**Resultado**: `MODEL_PATTERN` ampliado con familias Notifier (AFP, ID, AM, PEARL, INSPIRE, Sistema 5000, VESDA-E, SDX, RP, LTS, POL-200-TS, etc.) y Morley (ZXe, ZXSe, ZXr, DXc, MI-\*, ECO10\*\*, AutoSAT, VSN, HSR, IRK...). Añadido helper `model_to_imatch_pattern()` que emite regex PostgreSQL (`\y...(?!\d)`) con separadores opcionales y guard contra extensión de dígitos (`ID-200` nunca matchea `ID2000`). `keyword_search`, `typed_search` y `content_search` migrados a `imatch` para cubrir compound stored values (`AM2020/AFP1010`, `AFP-300/AFP-400`). RPC `match_chunks` sigue usando `=` (filter_product), pero el keyword_search y los content_search filtrados por producto compensan vía imatch.

**Validación**:
- Tests: `tests/test_model_extraction.py` (59 casos, todos PASS; suite completa 144/144)
- Smoke-test contra BD real: 12/12 queries eval extraen modelos y hacen hit vía keyword_search
- Baseline eval (52 preguntas): 9/52 → 11/52 (+2 PASS absolutos)

**Delta vs predicción**: La predicción declarada era +10–15 PASS. Real: +2 PASS, pero **12 preguntas cambiaron de comportamiento** de `admit_no_info`/`ask_clarification` a `answer` (hp005/7/8/9/11, cm002/5, etc.). El gap de retrieval Notifier/Morley SÍ se cerró (probado con `hp018`: retriever devuelve chunks ZXe/ZXSe con secciones literalmente llamadas "Circuitos de Sirenas", pero el generator responde `admit_no_info`). La diferencia entre behavior-flip y PASS se queda en (a) keyword-match frágil (TECH_DEBT #12) y (b) prompt del generator que filtra evidencia válida (Quick-win #3).

**Regresiones asumidas**: 2 preguntas (nd003 Apollo+ID3000, cm007 B501+Detnov). Causa: retrieval ahora más fuerte → bot sobre-responde cuando solo uno de los dos productos está en la BD. Fijable en prompt del generator.

**Aprendizaje eval-driven**: la predicción (+10–15) midió PASS; la señal real estaba en el behavior-flip. Registrado como lección al final del fichero.

---

## 11b. Generator descarta evidencia válida cuando retrieval sí funciona (nuevo — 20 abril 2026)

**Estado actual (detectado 20 abril 2026)**: Durante la validación de TECH_DEBT #11 afloró un patrón: en varias preguntas happy_path (hp003 CAD-150, hp014 ID2000, hp018 ZXe), el retriever devuelve chunks **perfectamente relevantes** (probado en `hp018`: top-10 son todos Morley ZXe/ZXSe con `category='Centrales de incendios'` y `section_title` literal "Circuitos de Sirenas", "Figura 16– Conexionado de sirenas"), pero el generator responde `admit_no_info`. Es decir: la evidencia está en el contexto y el generator decide que no la tiene.

**Problema**: hay una inconsistencia entre lo que el retriever puebla y lo que el generator reconoce como "fuente válida para responder". Posibles causas:
1. El **reranker** (Claude relevance scoring) puntúa demasiado bajo chunks de `section_title`/`content_type` útiles y los filtra antes de llegar al generator.
2. El **prompt del generator** exige condiciones de cita (ej. `source_file` coincide con un modelo literal) que fallan con los docs Notifier/Morley donde `source_file` es un código interno (`MIE-MI-530rv001`) y el modelo vive en `product_model`.
3. El generator es conservador por diseño (evita inventar) y con chunks de índice/figuras sin texto-procedural denso, prefiere `admit_no_info`.

**Trigger para investigar**:
- Cualquier ampliación del eval en happy_path (el fail mode bloquea el número).
- Si el próximo run tras TECH_DEBT #12 (boundary matching) sigue mostrando ≥3 `admit_no_info` donde el retrieval sí traía chunks relevantes.

**Solución propuesta**:
1. Añadir al runner una métrica `had_relevant_chunks: bool` (ej. chunks con `product_model` coincidente y `section_title` no vacío) y cruzarla con `observed_behavior`. Cada vez que `had_relevant_chunks=True` y `observed_behavior=admit_no_info` es un fail del generator, no del retriever.
2. Auditar 3 fails conocidos (hp003, hp014, hp018) capturando: chunks que entraron al reranker, chunks que pasaron al generator, prompt exacto enviado, respuesta. Para localizar dónde se pierde la evidencia.
3. Según el diagnóstico: aflojar reranker threshold, simplificar cita obligatoria, o añadir un fallback "si hay chunks con `product_model` del modelo preguntado, responder antes que admitir no-info".

**Coste estimado**: ~2-3h (instrumentación + auditoría + fix).

---

## 12. Runner del eval: boundary matching + detección de pregunta de clarificación

**Estado actual (detectado 19 abril 2026)**: `scripts/run_eval.py:99-109` puntúa `expected_keywords` y `forbidden_keywords` mediante **substring match lowercased**. Dos consecuencias problemáticas:

1. **Falsos positivos en `forbidden_keywords`**: forbid `"ma"` choca con `"mañana"`, `"más"`; forbid `"menú"` marca como fallo una respuesta honesta *"prueba el menú principal de tu central"*; forbid `"compatible"` cubre tanto `"es compatible"` (malo) como `"no es compatible"` (bueno). Detectado al revisar el eval el 19 abril — se limpiaron manualmente las entradas problemáticas pero la fragilidad sigue ahí.
2. **No detecta `expected_behavior: ask_clarification` de forma estructural**: el runner solo mira keywords, no si la respuesta **contiene una pregunta**. Hoy fiamos la detección a keywords como `"cuál"` — frágil.

**Trigger para implementar**:
- Tras la primera corrida del eval: si aparecen ≥3 casos donde la respuesta manualmente clasificada como "correcta" pierde puntos por substring-match, O
- Si se añaden preguntas nuevas con behaviors matizados donde el substring no discrimina bien.

**Solución propuesta**:
1. **Boundary matching opcional** en keyword scoring. Sintaxis en el YAML: si el keyword está rodeado de `*` (`*ma*`) es substring (comportamiento actual); si va plano (`ma`) exige límites de palabra (`\bma\b`). Migrar las forbidden_keywords existentes a boundary por defecto. Coste: ~30 min + sweep del YAML.
2. **Detector de pregunta de clarificación**: para preguntas con `expected_behavior: ask_clarification`, además de keywords, exigir que la respuesta contenga al menos un `?` seguido o precedido por un wh-word (`cuál`, `qué`, `dónde`, `cómo`, `cuándo`, `puedes indicar`, `necesito saber`). Marcar una métrica `asked_clarifying_question: bool` en el JSON de resultados.
3. **Detector de admisión honesta**: análogo para `expected_behavior: admit_no_info`. Buscar frases canónicas: `"no tengo"`, `"no dispongo"`, `"no está en mi base"`, `"consultar al fabricante"`. Métrica `admitted_no_info: bool`.
4. Marcar el overall score de una pregunta como **válido** solo si `expected_behavior` coincide con el detector — si el bot responde cuando debía clarificar, la pregunta cuenta como fallo aunque tenga todos los keywords.

**Coste estimado**: ~2h (escribir detectores + integrar en score_answer() + sweep del YAML).

---

## 11c. Retriever multi-doc: solo trae un manual cuando el producto tiene varios — ✅ RESUELTO

**Estado actual (detectado 22 abril 2026 durante audit YAML)**: cuando un `product_model` tiene **múltiples `source_files`** en el corpus (p.ej. CAD-150-8 tiene manual Usuario 110 chunks + Instalación 28 chunks; CAD-250 tenía Usuario 78 + Instalación 340 hasta que hoy se añadieron MC-380 + MS-416), el retriever top-k queda dominado por el manual de mayor volumen y **nunca trae chunks del otro**. Consecuencia: el bot admite no tener info que SÍ está en el corpus, en otro manual del mismo modelo.

**Evidencia concreta**:
- **hp003** (CAD-150 baterías 24V): retriever solo trajo chunks del manual Usuario; la respuesta está en el Instalación (2.5 "Conexión de las baterías", página 9). Bot respondió parcialmente con la info del Usuario e inventó/rellenó el resto.
- **hp001** (CAD-250 menú programación avanzada): retriever solo trajo chunks del manual Usuario; la respuesta está en el Instalación (6.1 "Acceso como administrador", páginas 28-29, password 2222). Bot admitió no tener info.

**Trigger para implementar**:
- ≥3 preguntas del eval donde `had_relevant_chunks=True` en UN manual pero la respuesta verificada vive en OTRO manual del mismo `product_model` no recuperado.

**Solución propuesta**:
1. Diversificación en reranker: **garantizar al menos 1 chunk de cada `source_file` distinto** dentro del top-k cuando varios source_files comparten el product_model consultado, antes de aplicar similarity ranking puro.
2. Alternativa más fina: expandir el retriever a devolver top-k por `source_file`, hacer union de candidatos, luego reranker decide.
3. Catálogo por producto: construir al vuelo (o cachear) un mapping `product_model → [source_files]` con chunk counts. Si una query filtra por modelo con ≥2 source_files, activar modo "multi-doc retrieval".

**Coste estimado**: ~3-4h (instrumentación + fix en retriever + tests sobre hp001/hp003 como casos verificados).

**Fix aplicado**: `_diversify_by_source_file` con round-robin en `src/rag/retriever.py`. Validado: **hp003 FAIL → PASS** en el eval post-fix. Efecto secundario positivo: expone bugs del generator antes enmascarados (ver #11f, #11g, #11h).

---

## 11f. Generator no filtra chunks cross-manufacturer antes de componer respuesta — 🟡 PARCIALMENTE RESUELTO, RESIDUAL CRÍTICO

**Estado actual (detectado 22 abril 2026 durante audit hp002)**: cuando el retriever falla en traer la sección relevante del manual del producto preguntado, la similitud vectorial mete chunks de **otros fabricantes** en el top-k (porque el tema es semánticamente similar cross-brand). El generator los USA para rellenar la respuesta, con advertencia "honesta" del estilo *"este procedimiento viene del manual X"*. **Viola la política de no-inferencia cross-brand incluso con caveat explícito** — la política (registrada en memoria de usuario) es NO inferir cross-brand, período.

**Evidencia concreta**:
- **hp002** (ASD535 Detnov flujo bajo): retriever trajo 4 chunks ASD535 (sección general/specs) + 1 chunk MINILÁSER 25 **(Notifier, otro fabricante)**. Generator extrajo pasos 1-4 del diagnóstico desde el chunk Notifier y los aplicó al ASD535 con caveat. Judge PASS (lo consideró "honesto"), pero política usuario dice NO.
- Contenido correcto SÍ existe en el corpus ASD535_TD_T131192es_h (sección 2.2.10 Monitorización del flujo de aire, p.28), solo que el retriever no lo trajo — fallo downstream que el generator debe detectar.

**Trigger para implementar**:
- Ya alcanzado: 1 caso confirmado (hp002) + riesgo inferido en otros happy_path con fabricantes superpuestos (aspiración Detnov/Notifier, detectores puntuales Detnov/Notifier, centrales mezcladas).

**Solución propuesta**:
1. **Filtro duro** en el reranker o generator: si la query identifica un `product_model` (vía MODEL_PATTERN) o un `manufacturer` (vía nombre mencionado), descartar chunks que pertenezcan a otros fabricantes antes de componer la respuesta. Pasar solo chunks del fabricante correcto al LLM.
2. **Comportamiento cuando no queda suficiente material del fabricante correcto**: admitir gap (*"el manual del ASD535 no cubre este procedimiento en los fragmentos disponibles"*) sin rellenar desde otras marcas.
3. Añadir una regla explícita al SYSTEM_PROMPT del generator: *"Nunca uses un chunk cuyo `manufacturer` difiera del producto preguntado, aunque parezca temáticamente relevante, aunque declares la fuente."*

**Coste estimado**: ~2h (filtro en reranker + regla en prompt + test con hp002 como caso canónico).

**Fix parcial aplicado**: `_filter_to_query_models` en retriever.py bloquea chunks cuyo `product_model` no coincide con los modelos de la query. Validado en smoke tests.

**Residual crítico**: cuando el retriever NO trae chunks del fabricante correcto (porque el manual no tiene la respuesta específica o porque hay pocos chunks relevantes), el generator **inventa** en vez de admitir. Evidencia en eval: hp002 PASS → FAIL (bot inventa secciones 9.4, 10.3 tras filtrar el chunk Notifier que antes "rellenaba"), hp015 (bot inventa *"CCD-103 es central convencional"*), nd001 (bot inventa citación [F2] a sección inexistente). Prompt anti-alucinación actual es necesario pero insuficiente. Requiere validación estructural post-generación (cross-model validator tipo Opus revisando Sonnet — pendiente diseño).

---

## 11g. Generator miscita chunks cuando hay múltiples docs del mismo producto (nuevo — 22 abril 2026)

**Estado actual (detectado 22 abril 2026 en eval post-Sprint 3+4)**: cuando el retriever trae chunks de varios `source_file` del mismo producto (p.ej. 4 manuales DXc representados gracias a diversify_by_source_file), el generator puede **atribuir afirmaciones a chunks equivocados**. Ejemplo: hp010 — bot respondió citando `[F4]` (doc de niveles de acceso multilingüe) pero el contenido citado *"Nivel de usuario 3, OK → 5 → código"* no está en F4; está en el imaginario del modelo.

**Mecanismo probable**: con más chunks disponibles, el LLM se "confunde" en la atribución. Prefiere citar un chunk cualquiera aunque no contenga la afirmación, en vez de admitir que no tiene la info.

**Evidencia concreta**: hp010 (Morley DXc añadir detector) PASS → FAIL al diversificar de 1 doc a 4 docs. Judge rationale: *"instrucción de pulsar 'OK → 5 → código' y la referencia a 'F4' no aparecen en ningún fragmento recuperado"*.

**Trigger para implementar**:
- Ya alcanzado (1 caso confirmado post-diversify). Si detectamos ≥3 casos similares en próximos evals, prioridad sube.

**Solución propuesta**:
1. Validación post-generación: parser que para cada `[F<n>]` marker extraiga el claim textual y verifique que está literalmente en el chunk F<n>. Si no, flaggear.
2. Reforzar SYSTEM_PROMPT con anti-ejemplo de miscitation (equivalente al anti-ejemplo existente de invención).
3. Alternativa: validator LLM cross-model (Opus revisando Sonnet) — pendiente explorar arquitectura.

**Coste estimado**: ~2-3h (validador estructural + test contra hp010 canónico).

---

## 11h. Filter cross-brand falla cuando la query menciona 2 marcas (nuevo — 22 abril 2026)

**Estado actual (detectado 22 abril 2026 en eval post-Sprint 3+4)**: `_filter_to_query_models` filtra chunks de marcas/productos que NO aparecen en la query. Pero cuando la query menciona **explícitamente** 2 marcas distintas (query cross-brand), ambas pasan el filtro y el generator recibe chunks de los dos fabricantes. Entonces el bot infiere compatibilidad cross-brand — violando la política `no inferir cross-brand`.

**Evidencia concreta**: cm001 *"¿Puedo usar un detector Notifier SDX-751 con una central Morley ZXe?"* — retriever trae chunks de SDX-751 (Notifier) + ZXe (Morley). Filtro permite ambos porque query los menciona a los dos. Bot infiere: *"SDX-751EM es fabricado por System Sensor para Notifier, lo que podría encajar bajo soporte System Sensor de la ZXe"*. Judge marcó FAIL: `faithful=False` (no soportado por fragmentos) y `behavior_match=False` (YAML ahora espera `admit_no_info`).

**Trigger para implementar**:
- Inmediato. Las 8 preguntas cross_manual dependen de que el filtro opere correctamente.

**Solución propuesta**:
1. Detectar "cross-brand intent" en la query: si `extract_product_models()` devuelve ≥2 modelos de fabricantes diferentes (consultando `lookup_model_manufacturer()` por cada uno), activar modo estricto.
2. En modo estricto: el generator recibe una instrucción adicional en el prompt: *"la query menciona productos de 2 fabricantes distintos. NO infieras compatibilidad. Responde admit_no_info y remite a cada fabricante"*.
3. Alternativa más estricta: en modo cross-brand, pasar al generator SOLO chunks de 1 fabricante (el primer modelo mencionado) + una nota al prompt explicando que el otro producto no tiene chunks recuperados.

**Coste estimado**: ~1-2h (detector cross-brand intent + regla en prompt + test contra cm001-cm008).

---

## 11i. Validator cross-model (Opus→Sonnet) — 🔴 REVERTIDO (23 abril 2026, experimento net-negativo)

**Resumen ejecutivo**: implementado y testeado con 2 iteraciones de eval completo. Ambas con resultado **net-neutral o negativo**. Generator.py revertido al estado pre-sesión-13. `src/rag/validator.py` + tests se BORRARON en s56 (DEC-036; dead-code 7 semanas — git los conserva si la re-exploración llega).

**Iteración 1 — con fallback branch** (`logs/eval_20260423T074717Z.json`):
- Keyword 12/52 → **9/52 (-3)**
- Judge 25/52 → **20/52 (-5)**
- happy_path 13/20 (65%) → **0/20 (0%)** — colapso total
- 19/52 preguntas dispararon fallback (n≥4 unsupported → admit_no_info). TODAS fallaron judge.
- Diagnóstico: fallback convierte answers imperfectas en admits, peor UX que respuesta ruidosa.

**Iteración 2 — fallback eliminado, solo retry** (`logs/eval_20260423T094048Z.json`):
- Keyword 12/52 → 9/52 (-3)
- Judge 25/52 → **26/52 (+1 aparente)**
- Pero desglose: **+7 gains / -9 losses** (churn alto, net -2 de volatilidad)
- Además, entre baseline (sesión 12) y eval v2 se expandió corpus Morley (+166 privados + 118 guías). Ese +1 probablemente viene del corpus, no del validator.

**Edge cases identificados durante la iteración** (bugs estructurales del enfoque):
1. **Falsos positivos auto-contradictorios**: Opus marca como `unsupported` un claim cuya propia `reason` dice "los fragmentos mencionan esto" (hp002, hp015).
2. **Ask_clarification contamination**: heurística `warrants_validation` no detecta preguntas de clarificación del bot. Si bot lista modelos ("tengo ZXe, DXc..."), Opus los marca como unsupported → retry → clarificación degradada.
3. **Catalog-listing false positives**: si el bot responde "tengo manuales de X, Y, Z" (meta-query), Opus solo ve los chunks del top-k, no el corpus completo. Marca como unsupported productos que SÍ están en corpus.
4. **Coste operacional**: +2-3x latencia + coste API por query. Inaceptable para producción con técnico-en-urgencia.

**Conclusión** (Alberto + Claude, 23 abril):
- Validator post-generación con cross-model **no es la capa correcta** para cerrar alucinación en este dominio.
- Cada categoría de query descubre un nuevo edge case que el heurístico debe saltar → el heurístico acaba haciendo el trabajo, Opus es sello caro.
- Revert completo en generator.py. Próxima iteración debe probar alternativas: **citation faithfulness estructural** (parsear `[F<n>]` y verificar contenido citado vía string match / BM25, 0 coste LLM) O **reforzar prompt del generator** (anti-ejemplos adicionales, self-check más estricto) O **mejorar retrieval** (causa raíz).

**Contexto**: en sesión 13 se implementó `src/rag/validator.py` (Opus 4.6 auditando respuesta de Sonnet 4.6) para cerrar el residual de alucinación del 11f/g. Smoke test sobre los 5 peores alucinadores reveló límites del validator antes del full eval.

**Hallazgos**:

1. **Falso positivo (hp002)**: Opus marcó *"vida útil configurable de 1 a 24 meses"* como `unsupported`, pero su propio campo `reason` dice *"Los fragmentos mencionan vida útil configurable de 1 a 24 meses"* — literalmente se auto-contradijo. Resultado: fallback injustificado, respuesta bajada.
2. **Falso negativo (hp010)**: Opus devolvió `unsupported: []` pese a que el bot citaba *"Nivel de usuario 3"* + *"[F3] → OK → 5 → código"* que no está en F3. El judge Sonnet sí detectó la invención. Opus se perdió la miscitation.
3. **No detecta behavior mismatch (cm001)**: el validator sólo evalúa faithfulness (¿claim ⊆ chunks?). No razona sobre si el bot **debió** haber admitido (cross-brand → admit_no_info). Correcto por diseño; anotar para no atribuirle ese rol.

**Mecanismo probable**:
- Falso positivo: Opus procesa mal la negación/ubicación del claim en el fragmento cuando éste tiene estructura densa. Prompt del validator es suficientemente estricto pero quizá demasiado genérico — podría añadir "antes de marcar `unsupported`, busca literalmente el valor citado en TODOS los fragmentos".
- Falso negativo: la miscitation (`[F3]` apuntando al chunk equivocado) requiere que Opus cruce el marker con el índice de fragmentos. Puede mejorarse reforzando el prompt para exigir este cross-check explícitamente.

**Trigger para iterar**:
- Se cumplió (full eval completado). Delta -5 judge → revertido como default. Próximo intento requiere rediseño arquitectural, no tweaks menores.

**Hipótesis del fallo** (qué salió mal, no obvio a priori):
1. **Umbral demasiado bajo (4 unsupported → fallback)**: Opus reporta 4+ claims en casi cualquier respuesta factual no-trivial. Inherente al modelo, no a la configuración — Opus es **naturalmente más conservador que Sonnet** en lo que considera "soportado". Un umbral de 8-10 sería más realista, pero entonces el validator casi nunca actuaría y sería inútil.
2. **Opus confunde paráfrasis legítima con invención**: el fragmento dice "vida útil configurable 1-24 meses, default 6"; la respuesta dice "configurable 1 a 24 meses (defecto: 6 meses)" → Opus marca unsupported citando su propio texto que confirma el claim (auto-contradicción observada en hp002).
3. **Fallback rompe la semántica de "answer"**: convertir happy_path → admit_no_info no es conservador, es incorrecto. La pregunta pedía info específica; si el validator duda, mejor pasar la respuesta original marcada como "baja confianza" que reemplazarla con admit.

**Solución propuesta (para sesión futura)**:
1. **Abandonar el fallback**. Si Opus flagea claims, la acción debe ser EDITAR la respuesta (tachar claims concretos) o AÑADIR un warning, no reemplazarla.
2. **Sustituir Opus por Haiku-strict o Sonnet-con-temperature-alta**: un modelo con menos poder de razonamiento fine-grained es IRÓNICAMENTE mejor validador — solo detecta invenciones obvias y no se mete en paráfrasis.
3. **Validator como filter en chunks**, no en answer: antes del generator, usar Opus para reescribir los chunks en forma atómica de claims verificables ("chunk dice: X=Y, Z=W"). Generator ve forma canónica, compone respuesta reusando esa forma literal. Alucinación baja sin necesidad de audit posterior.
4. **O más simple**: NO implementar validator. Invertir el coste en mejorar **prompt del generator** (citation inline forzada con validación estructural de regex `\[F\d+\]` contra contenido del chunk citado).

**Coste estimado**: 6-10h de rediseño arquitectural. Baja prioridad vs. otras mejoras (expansión de corpus, ambiguous_model, missing_context).

---

## 11d. FTS (search_vector) no matchea términos presentes en content — ✅ RESUELTO (22 abril 2026)

**Estado actual (detectado 22 abril 2026)**: búsquedas FTS vía `search_vector: fts.<término>` devuelven 0 hits para términos que SÍ están literalmente en `content` del chunk. Ejemplo reproducible con CAD-250:
- `fts.menú` con source_file Instalación CAD-250 → 0 hits
- `fts.programación` → 0 hits
- `fts.configuración` → 0 hits
- `content ilike '%menú%'` sobre el MISMO source_file → 5+ hits

**Posibles causas**:
- Trigger de población de `search_vector` no corrió al ingestar (o corrió con config distinta a 'spanish').
- Normalización unaccent no aplicada — pero incluso sin acento ("menu", "programacion") falla.
- Schema de tsvector construido con columnas incorrectas (p.ej. solo `section_title` y no `content`).

**Impacto operativo**: el `keyword_search` del retriever usa este índice. Si FTS está roto, toda la rama keyword cae a cero. Probable contribuyente al bug #11c (multi-doc) ya que el retrieval queda totalmente dependiente del vector search.

**Trigger para implementar**:
- Confirmado reproducible — implementar inmediatamente antes de nuevas iteraciones de retrieval.

**Solución propuesta**:
1. Inspeccionar el schema actual de `search_vector` y cómo se pobla (trigger SQL o función).
2. Repoblar tsvector para todo el corpus con config 'spanish' + `unaccent` extension activa.
3. Test de regresión: para cada product_model, verificar que `fts.<palabra-esperada>` devuelve ≥1 hit cuando `ilike '%palabra%'` devuelve ≥1.

**Coste estimado**: ~2-3h (diagnóstico + migración SQL + backfill + test).

---

## 13. Re-ingesta con `--use-vision` de manuales UI-screenshot (nuevo — 22 abril 2026)

**Estado actual**: MC-380, MS-416 y SGD-151 (MC-399) ingestados el 22 abril 2026 **sin `--use-vision`**. Los 3 son manuales UI-screenshot-heavy: el contenido crítico (labels de menú "AVANZADO", "AJUSTES", "PANELES", botones, campos de formulario) vive DENTRO de los pantallazos como píxeles, no como texto. El extractor de texto captura la narrativa ("Al tocar el campo PANELES…") pero no los valores visibles en las capturas.

Métricas del corpus ingestado:
- MC-380: 622 chunks / 100 páginas (6.22 ch/p), 564 con diagrama (91%)
- MS-416: 488 chunks / 76 páginas (6.42 ch/p), 462 con diagrama (95%)
- **SGD-151: 22 chunks / 22 páginas (1.00 ch/p)**, 22 con diagrama (100%) — 7 páginas descartadas por el chunker por umbral de longitud (incluyendo p=22 con contenido operativo: Reinicio, Silenciar Sirenas, Activar Sirenas, Inhabilitar detectores)

**Evidencia concreta del impacto sin vision** (SGD-151):
- p=8 (1248 chars, 4 imgs) — contenido sobre licencia online — descartado
- p=11 (478 chars, 8 imgs) — Escalada/Fijo ajuste gráfico — descartado
- p=12 (823 chars, 11 imgs) — Marcador Mapa/elementos — descartado
- p=13 (1070 chars, 7 imgs) — Marcador Panel/centrales — descartado
- p=22 (505 chars, 3 imgs) — **Página operativa con todas las acciones de campo** — descartado

**Trigger para implementar**:
- YA alcanzado con SGD-151: contenido operativo perdido en última página.
- Si eval muestra que preguntas sobre "dónde está X en el menú" tienen respuestas incompletas con los nuevos CAD-250 docs.

**Solución propuesta**:
1. Borrar chunks existentes de los 3 source_files (`CAD-250-MC-380-es`, `CAD-250-MS-416-es`, `SGD-151 MC-399 es`).
2. `python scripts/run_ingestion.py --single <pdf> --use-vision` para cada uno.
3. Verificar que el ratio chunks/página sube a ≥3 y que las páginas previamente descartadas ahora aparecen.

**Coste estimado**: ~45-60 min + ~$3-4 API (3 docs × 22-100 páginas).

**Extensión futura**: identificar en `Manuales_ES/`, `Manuales_Notifier/` y `Manuales_Morley/` otros PDFs UI-screenshot-heavy (heurística: ratio chunks/página < 3 y has_diagram > 80%) y marcarlos para re-ingesta con vision.

---

## 15. Umbral mínimo de longitud del chunker descarta páginas con contenido útil (nuevo — 22 abril 2026)

**Estado actual (detectado 22 abril 2026 durante ingesta SGD-151)**: el chunker descarta páginas cuyo texto extraído es corto (probable umbral ~500-600 chars) aunque el contenido sea útil y self-contained. Ejemplo reproducible: SGD-151 p=22 (505 chars) contiene la lista completa de acciones operativas del software (Reinicio/Rearme, Silenciar Sirenas, Activar Sirenas, Inhabilitar detectores…) — es la página MÁS útil del manual y se descartó.

**Problema**: páginas cortas no son necesariamente basura. Listas, resúmenes, tablas de acciones, leyendas de iconos pueden ser muy densas en información aunque cortas en chars.

**Trigger para implementar**:
- Confirmado reproducible con SGD-151. Implementar junto con TECH_DEBT #13 (vision) ya que son complementarios.

**Solución propuesta**:
1. Inspeccionar `src/ingestion/chunker.py` para localizar el umbral.
2. Bajar umbral a ~200 chars o eliminarlo (dejando solo "si no hay texto ninguno, skip").
3. Añadir filtro semántico posterior: si el chunk solo contiene boilerplate repetido (header/footer, número de página), descartar por regex explícito — no por longitud.
4. Re-ingestar docs afectados (los mismos 3 de TECH_DEBT #13, coincidencia útil).

**Coste estimado**: ~1h (diagnóstico + fix + test con SGD-151 verificando que las 7 páginas se recuperan).

---

## 14. Bug en `scripts/run_ingestion.py --single`: no pasaba cliente Supabase — ✅ RESUELTO (22 abril 2026)

**Estado**: antes del 22 abril, `python scripts/run_ingestion.py --single <pdf>` ejecutaba todo el pipeline (parse, chunk, embed) pero **nunca subía a Supabase** porque el script no pasaba `supabase=get_supabase()` a `ingest_single_pdf()`. Al ser `supabase=None`, los pasos 3b (register_document), 4b (upload images) y 6 (insert chunks) se saltaban silenciosamente sin log de warning.

**Fix** (commit pendiente): pasar `supabase = None if dry_run else get_supabase()` en el branch `--single`. `ingest_all` ya lo hacía correctamente.

**Impacto previo**: cualquier ingesta manual con `--single` desde la creación del script quedó en dry-run encubierto. No crítico porque la ingesta masiva inicial usó `ingest_all`, pero si alguien hizo re-ingestas puntuales con `--single` pueden faltar.

---

## 16. Separar retrieve top_k del generator top_k — "retrieve wide, generate narrow" — ✅ RESUELTO (s44, DEC-018: RETRIEVAL_TOP_K 15→50)

> **✅ MEDIDO + SHIPPED (s44, 5 jun 2026 — `DECISIONS.md` DEC-018):** `RETRIEVAL_TOP_K` **15→50** (RERANK_TOP_K=5 sin cambio). A/B K=3 HyDE-off (`test_bot_vs_gold`): **FALLO ~6→1 estable** (wide 1/1/1), 7 mejoras / 1 regresión (hp013 completitud). El burial era el **CORTE `merged[:15]`** (`retriever.py:1131`) que decapitaba chunks de coseno real bajo keyword-stamps planos (0.80-0.85); el pool ancho deja sobrevivir + el reranker (CONTENIDO, no sim) los sube. **El número fue 50** (no el 15 propuesto en abril — empírico, cubre el rango vectorial 16-50 del burial); **trigger real = el bulto de FALLO** (hp019/020 etc.: "el chunk existe pero no llega al generator"), tal como anticipaba esta entrada. **Coste (Protocolo 3):** el prompt de rerank crece ~3-7× tok (cap-rerank-~30 = tuning futuro, mitigaría también hp013). El número exacto / cap es afinable. **Estado-actual de abajo (RETRIEVAL_TOP_K=5) era STALE** — ya estaba en 15, ahora 50.

**Estado actual**: `RETRIEVAL_TOP_K = 5` en `src/config.py` sirve simultáneamente para (a) cuántos chunks devuelve el retriever y (b) cuántos ve el generator. Son el mismo número. El reranker opera sobre los 5 que ya llegaron y no tiene margen para elegir.

**Problema**: la literatura 2024-26 (LangChain / RAGAS / Anthropic docs) recomienda separar los dos números:

- **Retrieve más** (10-20 candidatos) → recall más alto, el chunk relevante tiene más chances de entrar.
- **Reranker filtra** → re-ordena por relevancia real y devuelve los mejores.
- **Generator ve menos** (5-8) → evita el efecto "lost in the middle" (Liu et al. 2023), reduce coste y latencia.

Con nuestra implementación actual, si un chunk relevante queda en posición 6-7 del retrieval, **nunca llega al generator**. Y subir `top_k` a 15-20 todo el pipeline crearía "context pollution" (más ruido al LLM + latencia + coste ×3).

**Trigger para implementar**:
- Si tras Sprints 3+4 el baseline sigue < 75% (es decir, si fixes de retrieval no bastan).
- O si Alberto observa preguntas donde "el chunk relevante existe en corpus pero no llega al generator" vía muestreo manual.

**Solución propuesta**:
1. Añadir a `src/config.py`:
   - `RETRIEVAL_TOP_K = 15` (candidatos que salen del retriever)
   - `GENERATOR_TOP_K = 5` (chunks que ve el LLM)
2. En `retrieve_chunks()`: devolver top-15 (o el número configurado).
3. En el reranker (ya existe, es LLM-based custom): re-ordenar los 15 recibidos, devolver top-5.
4. El generator opera solo sobre los 5 re-rankeados.
5. **Medir delta con eval A/B** antes de hacer permanente: config original (5/5) vs. nueva (15/5).

**Número exacto (15 vs 10 vs 20) es empírico** — a determinar con el eval:
- 10: conservador, bajo overhead.
- 15: compromiso habitual en la industria.
- 20: solo si queries complejas con multi-hop reasoning.

**Coste estimado**: ~2h (refactor + test + eval A/B).

**Riesgo**: si el reranker no es fuerte (hoy es custom ad-hoc, no un modelo entrenado tipo Cohere Rerank), subir top-k sin mejorarlo metería ruido al generator. Mitigar: medir con eval antes de commitear.

---

## Mejoras YA incorporadas al flujo (no deuda, registro histórico)

- **Test de mapping en `tests/`**: verifica que todo PDF en `Manuales_{Manufacturer}/` tiene entrada en los dicts de override. Implementado [fecha ingesta Morley].
- **Dry-run de parsing con stats**: `scripts/dry_run_parse.py` reporta n_chunks, model, category, tokens por archivo sin generar embeddings. Implementado [fecha ingesta Morley].
- **Eval con preguntas por fabricante**: el eval incluye ≥3 preguntas cuya respuesta depende de manuales de cada fabricante ingestado.

---

## Lecciones del desarrollo eval-driven

**Lección #1 (20 abril 2026, post TECH_DEBT #11)**: La predicción declarada antes del fix fue *"+10 a +15 puntos del baseline"*. Real: +2 PASS (9/52 → 11/52). La predicción no se sostuvo **en la métrica que declaré**, pero **12 preguntas cambiaron de comportamiento** (`admit_no_info`/`ask_clarification` → `answer`) y el gap de retrieval Notifier/Morley se cerró en la BD (probado con retrieval-probe ad-hoc en `hp018`).

Dos cosas que se aprendieron:
1. **PASS-rate no es la única métrica útil**: un fix de retrieval puede subir el engagement del bot (behavior-flip) sin subir PASS si el bottleneck está aguas abajo (generator + keyword-match scoring). La próxima vez hay que predecir sobre la métrica más cercana al fix: *"¿cuántos `admit_no_info` infundados convierte en `answer`?"*, no *"¿cuántos PASS gana?"*.
2. **El número de fallos del generator aislado es real**: cuando el retrieval funciona y el bot sigue diciendo *"no tengo información"* es un fail del generator, no del corpus. TECH_DEBT #11b creado para rastrearlo.

Regla operativa que sale de esta sesión: **toda predicción eval-driven debe declarar la métrica Y el canal esperado** (ej. *"pronostico +X PASS y/o +Y behavior-flips de admit_no_info a answer en Notifier/Morley"*). Si el delta divergir del canal previsto, eso ya es información, no fracaso — siempre que el fix haga lo que dijimos en el canal técnicamente correcto.


---

## 17. Embedding batch supera el límite de 300k tokens en manuales Morley muy largos (nuevo — 23 abril 2026)

**Estado actual (detectado 23 abril 2026 en ingesta Manuales_Morley_Privado)**: 2 PDFs fallaron la ingesta con error de OpenAI:
```
Error code: 400 - {'error': {'message': "Invalid 'input': maximum request size is 300000 tokens per request."}}
```
Archivos afectados:
- `MIE-MI-300rv02.pdf` — falló en batch 800-900 (100 texts)
- `MIE-MP-315.pdf` — falló en batch 0-100 (100 texts)

**Mecanismo**: `src/ingestion/embedder.py` agrupa chunks en batches de 100 para el call a `embeddings.create`. Cuando los chunks individuales son muy largos (1500 tokens cada uno × 100 = 150k) pero el manual tiene chunks que exceden el target size (ej. secciones sin boundary detectado), el batch puede saltar los 300k tokens hard-limit de OpenAI.

**Trigger para implementar**: ya alcanzado (2 manuales no ingestables sin fix).

**Solución propuesta**:
1. **Adaptive batch sizing**: antes de enviar, sumar `len(tiktoken.encode(...))` de cada chunk; si total > 280k, partir en sub-batches.
2. **Fallback simpler**: batch size dinámico: en vez de 100 fijos, empezar en 100 y dividir por 2 tras cada 400 error hasta que pase (max 3 intentos).
3. **Log detallado**: hoy el log dice 'batch 800-900 failed' sin indicar qué chunk tenía overflow — añadir per-chunk token count en el error.

**Coste estimado**: ~1-2h (detección vía tiktoken + sub-batching + test).

**Workaround temporal**: no hay. Los 2 PDFs quedan fuera del corpus hasta arreglar.


---

## 18. Judge false positive en chunks densos (nuevo — 23 abril 2026, sesión 14)

**Estado actual**: caso canónico detectado en mc001 ("alarma de batería baja"). El bot citó correctamente valores "27,6 V / 20,4 V / 17,4 V", procedimiento "MODE 8768 [ENTER/STORE]", "48 horas de carga" y "MS-5210UD" todos presentes literalmente en el chunk `MNDT080`. El judge marcó `faithful=False` afirmando *"el bot inventa numerosas afirmaciones técnicas no respaldadas por ningún fragmento"*. Falso positivo verificado re-ejecutando retrieval.

**Mecanismo hipótesis**: el chunk no está truncado (len=1697 chars, bajo el límite de 2000 del judge desde sesión 11). Pero el contenido es denso técnicamente (valores + códigos + pasos intercalados) y el judge falla en localizar las afirmaciones dentro del texto. Diff del bug de sesión 11 (truncación): aquí no hay corte físico, es error cognitivo del modelo al escanear texto denso.

**Trigger para implementar**: ya alcanzado (bug verificado).

**Impacto en eval**: desconocido sin auditoría completa. Si el sesgo se repite en otros chunks densos → baseline está infraestimado.

**Solución propuesta (orden creciente de esfuerzo)**:
1. Reforzar el prompt del judge con instrucción explícita: *"antes de marcar `faithful=False`, busca LITERALMENTE (substring search) los valores numéricos o nombres de sección de la afirmación en el texto de cada fragmento. Solo si NO aparecen, marca unsupported"*.
2. Añadir pre-check determinista: extraer tokens numéricos + proper nouns de la respuesta del bot, verificar presencia por string match antes de pasar al judge. Si el token está y el judge marca unsupported → override a supported.
3. Calibración humana completa (bloque 2 de sesión 14 — diferido por cierre de sesión).

**Coste estimado**: ~2h (refuerzo prompt + evaluación del delta), +4h si se añade pre-check estructural.

---

## 19. Eval single-turn no valida conversaciones multi-turno (nuevo — 23 abril 2026, sesión 14)

**Estado actual**: `scripts/run_eval.py` ejecuta cada pregunta como llamada aislada al bot. Sin historial, sin turnos posteriores. Si el bot pide clarificación en el turno 1, el eval NO verifica que dé respuesta correcta en el turno 2 tras el input del técnico.

**Impacto**: el eval aprueba "el bot clarificó" como éxito sin verificar la calidad del diálogo completo. En producción (Telegram) podría darse la cadena: bot clarifica mal → técnico responde → bot ignora contexto o alucina → falla silencioso que el eval no mediría.

**Ejemplo concreto (sesión 14)**: am005 — bot respondió a *"¿cómo reseteo el panel?"* con una clarificación pidiendo modelo + tipo de reset. El eval marcó `behavior_match=True` y se quedó ahí. No sabemos si el bot, al recibir *"CCD-103, reset tras alarma"*, daría el procedimiento correcto.

**Trigger para implementar**: cuando se prepare piloto con técnicos reales (M&A post-cierre), el eval multi-turno es requisito.

**Solución propuesta**: nuevo YAML `multi_turn_eval_v1.yaml` con 10-15 diálogos de 2-3 turnos + runner que alimenta la respuesta scripted del "técnico" al bot tras cada clarificación.

**Coste estimado**: 4-6h (runner multi-turno + diseño de 10 diálogos + judge adaptado).

---

## 20. Calibración judge pendiente (diferida de sesión 14)

**Estado actual**: sesión 14 identificó en conversación con Alberto al menos 2 sesgos del judge que conviene auditar:
1. **Estrictez excesiva en clarificaciones**: el judge penaliza `faithful=False` cuando el bot atribuye fabricante a un modelo presente en corpus (ej: am005, bot dijo *"Detnov CCD-100"* — CCD-100 sí está en corpus, "Detnov" es atribución pre-training conocida en la industria). Es metadata de apoyo en clarificación, no invención maliciosa.
2. **Leniencia en cross-brand con info parcial**: cm003, cm007 pasaban el judge (baseline) pese a que el bot filtraba specs de un producto en consulta cross-brand interop, cuando la política estricta diría admit.
3. **Judge "pide UN detalle concreto"**: am005 penalizado por pedir 3 detalles (modelo + tipo reset + versión). ¿Debe realmente penalizar formato multi-pregunta?
4. **Judge false positive en chunks densos** (TECH_DEBT #18 — relacionado).

**Trigger para implementar**: acordado con Alberto al cierre de sesión 14 — pendiente Bloque 2 de la sesión siguiente.

**Solución propuesta**: sesión de calibración humana de 30-45 min con Alberto revisando 8-10 casos con discrepancia keyword↔judge (dump ya preparado al cierre de sesión 14). Aplicar correcciones al prompt del judge + re-eval.

**Coste estimado**: ~45 min contigo + 30 min de implementación + re-eval.


---

## 21. `product_family` extraction en ingest (coverage ground-truth)

**Estado actual**: el bot no tiene forma fiable de saber qué modelos de una familia existen en corpus. Si un técnico pregunta de forma abstracta ("la CAD", "Sistema 5000", "ZX"), el bot solo ve los ~10 chunks del retrieval, que pueden no cubrir todos los miembros por densidad desigual (ej: ZX2e con 500 chunks, ZX5e con 30 → retrieval casi siempre prioriza ZX2e). Esto bloquea dos mejoras de UX:
1. **Excepción 1-member en clarificación**: hoy prohibida porque "tengo solo X" puede ser falso.
2. **Respuesta a meta-queries del técnico** ("¿qué modelos Morley tienes?"): hoy vulnerable al mismo error de omisión.

**Problema**: la fuente de verdad (BD completa) no está accesible sin una fuente auxiliar. Una query `ILIKE 'ZX%'` ad-hoc requiere mantener map familia→prefijo — no escala a 30+ fabricantes.

**Trigger para implementar**:
- Feedback de técnicos reales post-M&A que "siempre me pregunta el modelo aunque yo sé que solo tenéis uno" (UX friction real), O
- Implementación del punto #22 (coverage query tool), que requiere esta pieza.

**Solución propuesta**: durante ingest, para cada `product_model` extraer `product_family` con regex (strip trailing digits + sufijos comunes: `ZX2e`→`ZX`, `CAD-250`→`CAD`, `AFP-400`→`AFP`, `DTD-210A`→`DTD`). Almacenar como columna nueva en `chunks` (o en el JSON de metadata). Migration + backfill de los ~168k chunks. Script de validación que agrupe product_model por product_family y Alberto revisa las agrupaciones.

**Coste estimado**: ~3-4h (regex con tests + migration + backfill + validación manual).

---

## 22. Coverage query tool (intent classifier + metadata SQL)

**Estado actual**: el bot enruta toda query por el mismo pipeline RAG (retrieval + generator). Las queries de cobertura del técnico ("¿qué modelos tienes?", "¿cubres Apollo?", "lista fabricantes disponibles") pasan por retrieval, que es estocástico y puede omitir miembros. Best practice agentic RAG (LangChain, LlamaIndex) separa este tipo de query con un **tool / function call**.

**Problema**: sin separación, el bot "miente" involuntariamente sobre qué hay en corpus — basa su respuesta en los chunks retrievados, no en el DB completo.

**Trigger para implementar**:
- Implementado TECH_DEBT #21 (`product_family` extraction) — requisito previo.
- Observación de ≥1 técnico real preguntando "qué modelos tienes" y recibiendo respuesta incompleta, O
- Deploy de la Fase 3 (Telegram live) — necesario antes de exponer a técnicos reales.

**Solución propuesta**: 
1. Intent classifier ligero (regex o LLM cheap) al inicio del pipeline. Patrones: "qué modelos tienes", "qué cubres", "lista fabricantes", "qué documentación".
2. Si intent=coverage → bypass retrieval, tool call SQL directa: `SELECT DISTINCT product_model FROM chunks WHERE manufacturer=? AND (product_family=? OR product_family IS NULL)`.
3. Generator formatea resultado como lista amigable.
4. Si intent=technical → RAG normal.

**Coste estimado**: ~2-3h (classifier + tool + integración en pipeline + tests).

---

## 23. Clarify-first con respuesta embedida (diseño híbrido para queries de código/error/indicador)

**Estado actual**: la edición 3 del SYSTEM_PROMPT (sesión 16) fuerza `ask_clarification` pura cuando la query menciona código de error / mensaje / LED sin fabricante ni modelo. Esto preserva escalabilidad (cuando lleguen 10 fabricantes con "código 7" distinto, clarificar será la única respuesta segura) a coste de 1 FAIL estable en am008 ("¿qué significa el código de error 7?" — el corpus solo tiene ese código documentado en el CCD-103 de Detnov; el judge penaliza porque la respuesta estaba visible en F1).

**Problema**: existe una tercera vía intermedia que es mejor UX que clarify pura **y** más segura que `answer` directo — respuesta con clarificación-primero embedida:

> *"Antes de responder: tengo documentado 'código 7' solo para el CCD-103 de Detnov. ¿Es ese tu panel? Si sí, significa Fallo de sistema (sistema no operativo) [F1]. Si es otro panel, dímelo y busco en sus manuales."*

Aplicable también a am003 (ASD sin variante → "tengo datos del ASD535, ¿es tu variante?") y a cualquier query ambigua donde retrieval colapsa a un único producto por densidad documental desigual.

**Por qué no se aplica hoy**: implementarlo bien requiere 3 piezas que NO tenemos:

1. **Prompt rule** "clarify-first con info condicionada" — orden obligatorio (clarify antes de info), framing que evita que el técnico apurado lea solo la primera línea factual. Hoy el prompt dice "pregunta abierta ES LA RESPUESTA", no contempla la vía híbrida.

2. **Scoring eval** — el heurístico de `observed_behavior` hoy mapea texto a `answer` / `ask_clarification` / `admit_no_info` por patrones regex (signos de interrogación → clarify). Una respuesta híbrida cae arbitrariamente en una u otra. Necesita un `expected_behavior: answer_with_clarify` nuevo (o `clarify_with_context`) con heurística que mida "hay clarify en primera mitad + info condicionada en segunda".

3. **Diversity-aware reranking** — el auto-escalado que haría la regla dinámica ("si fragmentos muestran >1 producto, clarify pura; si 1 solo, respuesta con clarify-first") depende de que retrieval refleje la diversidad real del corpus. Hoy el reranker optimiza relevancia semántica, no diversidad de `product_model`. Con 3 fabricantes documentando "código 7", top-5 puede colapsar al manual con más densidad y el bot nunca ve la ambigüedad. Mitigación: post-rerank counter `DISTINCT(product_model)` que fuerce clarify si >1.

**Trigger para implementar**:
- Feedback de técnicos reales en Fase 3 (Telegram live) que expresen fricción con clarify pura cuando el corpus era suficiente ("me pregunta qué panel tengo cuando el tuyo es el único documentado"), O
- Ampliación del corpus a ≥2 fabricantes con códigos/mensajes coincidentes que haga que la regla binaria actual (siempre clarify) pase de "conservadora" a "obstaculizante".

**Solución propuesta**:
1. Contador `DISTINCT(product_model)` post-rerank.
2. Si ==1 y query es código/error/indicador sin producto → prompt branch "respond-with-clarify-first" con plantilla fija.
3. Si >1 → clarify pura (comportamiento actual).
4. Nuevo `expected_behavior` en el scorer + heurística ad-hoc.
5. Re-calibrar am003, am008 con el nuevo behavior esperado.

**Coste estimado**: ~6-8h (prompt branch con tests de orden/framing + scorer nuevo + reranker diversity counter + re-eval + calibrar YAML afectado).

**Decisión actual (sesión 16, 24 abril 2026)**: **diferido como opción C** — am008 queda como FAIL estable documentado (judge 47/52 = 90% lo asume). La política "clarify pura si query ambigua" se mantiene porque es el default seguro hasta que (a) tengamos señal real de UX friction en Fase 3, (b) el corpus crezca al punto donde la asimetría fragmentos-único-vs-múltiple se vuelva frecuente. Si am008 flippea a PASS en un run futuro sin que hayamos tocado nada, es señal de regresión (el bot dejó de clarificar) — tratar como test de no-regresión.

---

## 24. Extracción de tablas pierde marcas visuales (X/✓) — genera alucinación por relleno (hp007, sesión 16) — 🟢 FASE A APLICADA (sesión 20)

**Estado actual**: el chunker/parser PDF extrae tablas matriz (ej. Tabla 7-1 del manual VESDA-E VEP-A00: calendario de mantenimiento con 7 tareas × 4 frecuencias) preservando headers y nombres de filas pero perdiendo las marcas visuales (X, ✓, ticks) que asignan cada tarea a una frecuencia. El chunk llega al generator con la tabla "vacía" — texto legible pero sin la información estructural clave. El generator, al verla incompleta, rellena con conocimiento de pretraining pretendiendo que la asignación viene del fragmento (alucinación inducida por ingest defectuoso).

**Update sesión 20 (26 abril 2026) — diagnóstico revisado + Fase A aplicada**:

Inspección directa de los chunks que el retriever entrega para hp007 reveló que el patrón problemático **no es el documentado originalmente**. El problema NO es que `pdfplumber` extraiga la tabla con celdas `[TABLA EXTRAÍDA]` vacías. Es que **`pdfplumber` no detecta la Tabla 7-1 como tabla** (probablemente porque no tiene bordes de cuadrícula limpios), por lo que el chunk recibe únicamente la extracción de PyMuPDF — texto plano sin glifos visuales. Resultado: el chunk muestra los 4 encabezados de frecuencia + las 7 filas de tareas SIN ninguna marca de asignación entre ellos. El bot rellenó con pretraining diciendo "5 tareas son anuales" cuando no podía saberlo.

Esto cambia las opciones de solución:
- **Fase A (prompt rule defensiva)**: aplicada — bloque "TABLAS MATRIZ — CALENDARIOS Y MATRICES DE ASIGNACIÓN" en `src/rag/generator.py` SYSTEM_PROMPT (entre CITACIÓN INLINE y CONVERSACIÓN DINÁMICA, **deliberadamente fuera del bloque CERO INVENCIÓN ya saturado** — lección S19 sobre cascade en prompts monolíticos). El bloque le instruye a admitir explícitamente "las marcas de asignación tarea↔frecuencia no son legibles en el fragmento recuperado" cuando ve el patrón "encabezados + filas + cero asignaciones explícitas".
- **Fase C (detector empty_cell_ratio + re-ingest Vision)**: ya no aplica con esa heurística porque el chunk no tiene `[TABLA EXTRAÍDA]`. La detección requeriría comparar páginas-con-tablas-detectadas-por-PyMuPDF-pero-no-por-pdfplumber → re-ingest selectivo con Vision. Diferido (Fase A logró el objetivo).

**Resultado eval Fase A (sesión 20, 26 abril 2026)**: judge 50/52 PASS vs baseline S19 46/51 → **+4 net**, fuera de variance ±2pt. **6 flips PASS** (cm004, cm008, hp005, hp007 ✓ target, hp015, mc006) — el bloque benefició a otros casos donde el bot estaba inventando asignaciones de matrices. **2 regresiones** (hp019, mc004): el bot ahora hace `admit_no_info` en lugar de `ask_clarification` en queries genéricas — efecto colateral de los ejemplos "admite explícitamente" del nuevo bloque, ver TECH_DEBT #28.

**Evidencia (hp007, sesión 16)**: query *"¿Cómo se realiza el test anual de un detector VESDA-E VEP según el manual del fabricante?"*. Bot listó 5 tareas como "Una vez al año" (prueba de humos, comprobar flujo, limpiar puntos, limpiar con agua, sustituir filtro). Los chunks retrievados F1-F5 (4 duplicados del mismo contenido) contienen literal las 7 tareas y las 4 columnas de frecuencia, pero las celdas de intersección están vacías — no hay manera de que el bot sepa qué tarea va con qué frecuencia desde el chunk. El bot rellenó.

**Alcance del problema**: no específico de VESDA-E. Cualquier PDF con tabla matriz donde las celdas tienen marcas visuales sufre el mismo fallo. Probablemente recurrente en:
- Calendarios de mantenimiento (frecuencia × tarea).
- Matrices de compatibilidad (producto × función).
- Tablas de códigos de error (código × causa × acción).

Coverage desconocido en los ~168k chunks. Requiere auditoría.

**Trigger para implementar**: este item bloquea el cierre de hp007 como PASS real en el eval. Además, en producción puede producir respuestas confidentes-pero-inventadas en cualquier pregunta que dependa de una tabla matriz — alto impacto en seguridad del técnico.

**Solución propuesta (combinación A + C)**:

**A — Prompt rule defensiva (1h, bajo riesgo, síntoma inmediato)**:
Añadir al SYSTEM_PROMPT: *"Si ves una tabla con headers y filas pero las celdas de valores están vacías (sin X/✓/números), NO infieras las asignaciones. Admite explícitamente: 'La Tabla X existe con estas N tareas y M frecuencias, pero no puedo leer las marcas de asignación en el chunk recuperado; consulta el manual físico para la asignación exacta.'"* No resuelve causa raíz pero limita daño inmediatamente.

**C — Detector proactivo en ingest + re-ingest selectivo (3-4h, causa raíz sistemática)**:
1. Heurística en el chunker: al extraer una tabla, medir ratio de celdas vacías. Si >50%, log warning + flag `table_incomplete=True` en metadata del chunk.
2. Script de auditoría: `SELECT source_file, count(*) FROM chunks WHERE table_incomplete=True GROUP BY source_file ORDER BY count DESC` → lista de manuales afectados priorizada.
3. Re-ingestar los top-N afectados con `--use-vision` (infra existente, TECH_DEBT #13) para recuperar marcas visuales vía Claude Vision.
4. Validar que las tablas re-ingestadas preservan asignaciones (smoke test de 3-5 queries por manual).

**B y D consideradas y descartadas**:
- **B** (re-ingest único del VESDA con `--use-vision`): solo parchea este caso, no identifica otros.
- **D** (reemplazar parser con `camelot`/`pdfplumber` + re-ingestar todo): ~1-2 días, riesgo de regresión en extracciones que sí funcionan. Overkill hasta saber el scope.

**Decisión actual (sesión 16, 24 abril 2026)**: diferido. Calibrar judge primero (TECH_DEBT #18/#20) para tener métrica fiable; después aplicar A como quick-win y lanzar C como auditoría sistemática. D se reserva para si A+C no es suficiente.

**Coste estimado**: A = 1h. C = 3-4h + audit + re-ingest de manuales afectados (variable según scope). Combinado: ~1 sesión.

---

## 25. Vocabulary mismatch retriever — stack de 3 capas (hp001, sesión 16)

**Estado actual**: el retriever falla inconsistentemente cuando el vocabulario del técnico diverge del vocabulario del manual. Caso documentado (hp001): query *"¿cómo se entra al menú de **programación avanzada** de la CAD-250?"* — los chunks con `section_title = "AJUSTES (Menú principal) > AVANZADO(Submenú)"` existen en BD (verificado: IDs `267d9584-...`, `b7476847-...`, source `CAD-250-MC-380-es`, content literal *"Para acceder a estos ajustes pulse: AJUSTES > AVANZADO"*) pero **no suben al top-20/46 del retriever** porque la palabra "programación" no aparece en el content (el manual usa "configuración", "ajustes", "puesta en marcha"). Behavior: flaky — 5 FAIL / 6 PASS en 11 runs históricos, según el reranker trae o no el chunk correcto.

**Alcance**: no es bug aislado. Es limitación inherente del retriever actual (vector + BM25 sobre content) cuando el técnico usa terminología de campo que no coincide con la terminología del manual. Frecuente en:
- Queries con palabras comunes (*"programación"*, *"setup"*, *"inicializar"*) que el manual documenta con sinónimos (*"configuración"*, *"puesta en marcha"*, *"reset"*).
- Queries abstractas / conceptuales donde el manual usa pasos concretos.
- Cross-language (técnico escribe castellano estándar, manual usa mexicanismos o anglicismos técnicos).

**Stack de 3 capas** (best practice industrial, ordenado por ROI e implementación recomendada):

### Fase 1 — Hybrid retrieval con field boosting sobre `section_title` (next sprint, ~3-5h)

**Qué**: indexar `section_title` en FTS además del content. Boost de matches en título ×2 porque los títulos son texto curado, alto valor (cadenas de navegación tipo *"AJUSTES > AVANZADO > Sistema"*).

**Por qué primero**: hp001 tiene "AJUSTES" y "AVANZADO" literal en el section_title pero el retriever no los usa para ranking. Fix quirúrgico, alto ROI para corpus de manuales técnicos con títulos descriptivos.

**Cómo**: (1) añadir columna `search_vector_title` generada desde `section_title` con `to_tsvector('spanish', ...)`. (2) Modificar `search_chunks_text` RPC para unir búsqueda sobre content + title con boost. (3) Reranker puede usar el boost como señal adicional.

**Coste**: ~3-5h (migration + RPC + tests + re-eval subset).

### Fase 1b — BM25 + RRF hybrid fusion (condicional, ~5-7h)

**Qué**: upgrade del retriever a hybrid search state-of-the-art industrial:
1. **BM25** vía extensión `pg_search` (ParadeDB) — índice BM25 nativo sobre `content` + `section_title` con weights más granulares que los 4 niveles A/B/C/D de `setweight`. Ranking ~2-5% mejor que `ts_rank` clásico para queries con múltiples keywords.
2. **RRF (Reciprocal Rank Fusion)** — nueva RPC `hybrid_search` que combina rankings de vector search + BM25 con `score = 1/(k + vector_rank) + 1/(k + bm25_rank)` (k=60 típicamente). Canonical industry standard para hybrid search (Weaviate, Pinecone, Elasticsearch 8.x lo implementan built-in).

**Relación con Fase 1**: Fase 1b es **ortogonal a Fase 1**, no la sustituye. Fase 1 mete title en el tsvector con `setweight`; Fase 1b añade BM25 (scoring más fino) y RRF (combinación vector+FTS). Fase 1b no depende de trigger vs Generated STORED — son capas independientes.

**Trigger para implementar**: si tras Fase 1 (setweight title) + Fase 2 (metadata enrichment) el baseline judge se estanca por debajo del 95% y el gap restante es de retrieval recall, Fase 1b es el siguiente escalón. Si no hay gap de recall, no merece la pena: BM25+RRF son mejora marginal (~2-5%) comparado con el coste de instalar extensión + refactor de RPC.

**Cómo**:
1. Instalar extensión `pg_search` (ParadeDB). Requiere permisos admin en Supabase.
2. Crear índice BM25 sobre `chunks` con fields `content` (weight 1.0) + `section_title` (weight 2.0) + `enriched_synonyms` (weight 1.5 — requiere Fase 2).
3. Nueva RPC `hybrid_search(query, top_k)` que ejecuta 2 CTEs (vector_search top-50, bm25_search top-50) y combina con RRF score.
4. Modificar `retriever.py` para llamar a `hybrid_search` en lugar de vector+keyword separados.

**Coste**: ~5-7h (extensión + índice + RPC + refactor + eval). Sin coste API adicional.

**Decisión actual (sesión 17, 24 abril 2026)**: diferido. Implementar solo si Fase 1 + Fase 2 no alcanzan target y el análisis de FAILs muestra gap de retrieval recall (no de generation, no de behavior). Si el gap es retrieval, Fase 1b es best-practice industrial para cerrar.

**Actualización s36 (1 jun 2026 — EVIDENCIA: RRF ya se midió y NO movió):** `scripts/gate.py` (PR#8, 26-may)
**ya implementa RRF** (`rrf_fuse`, k=60) y lo midió: `hyb_new hit@5 = 0.3636 == vec_new 0.3636` (idéntico;
recall@15 0.286→0.305 trivial; verdict NO PASS) — `evals/gate_results.json`. Medido sobre el gold ROTO
pre-s31 + como proxy de recall, así que no es definitivo, PERO no hay evidencia A FAVOR de RRF y la única
que existe dice que no mueve el top-5. La auditoría s36 además mostró que los casos del eval NO son de
"BM25 captaría el literal" (hp006 da 0.0 incluso con RRF; FTS usa AND `@@` → si falta el literal, BM25
tampoco). **Deprioridad fuerte**: no re-intentar RRF "a ciegas"; si acaso, re-correr `gate.py` sobre el
ruler arreglado (sigue siendo proxy). Detalle: `DECISIONS.md` DEC-005 (síntesis RRF RETRACTADA tras 4ª review).

### Fase 2 — HyDE (Hypothetical Document Embeddings) (next sprint, ~3-4h)

**Qué**: antes de retrieval, Claude (Haiku) genera una *respuesta hipotética* a la query usando vocabulario "rico" del dominio PCI. Usamos el embedding de esa respuesta hipotética (en lugar — o además — del embedding de la query original) para vector search.

**Ejemplo concreto (hp001)**:
- Query original técnico: *"¿cómo entro al menú de programación avanzada?"*.
- HyDE hipothesis (Haiku): *"Para acceder al menú de programación avanzada de la central, navegar a AJUSTES (Menú principal) y luego al submenú AVANZADO. Esto requiere nivel de acceso de configuración. En la pestaña SISTEMA se ajustan parámetros básicos como número de cabinas, lazos, LEDs de zona..."*.
- El embedding de esa hipótesis matchea con chunks que usan *AJUSTES, AVANZADO, configuración, parámetros* — incluso aunque la query original use *programación*.
- Retrieval trae los chunks correctos.

**Por qué HyDE es best practice (vs metadata enrichment estática)**:

| | HyDE | Metadata enrichment |
|---|---|---|
| **Cost upfront** | $0 | $500 ingest |
| **Cost runtime** | +1 LLM call (~$0.001) | $0 |
| **Re-ingest si cambias prompt** | NO | Sí ($500 cada vez) |
| **Cubre queries no anticipadas** | Sí (genera paraphrase ad-hoc) | Solo si synonym lo predijo |
| **Adapta a jerga técnica regional/coloquial** | Sí (LLM la interpreta) | No (lista estática) |
| **Implementación** | ~3-4h | 1-2 días |
| **Best practice rank 2024-2025** | ⭐⭐⭐⭐ first-class (LangChain/LlamaIndex) | ⭐⭐ niche e-commerce |

**Especialmente crítico para Fontiber**: los técnicos PCI tienen léxico no sofisticado, usarán jerga regional, abreviaturas, posibles errores ortográficos. HyDE adapta dinámicamente; synonyms estáticos no escalan.

**Referencia**: Gao et al. 2022, "Precise Zero-Shot Dense Retrieval without Relevance Labels". Implementación canónica en LangChain `HypotheticalDocumentEmbedder`, LlamaIndex `HyDEQueryTransform`.

**Cómo (implementación canónica)**:

1. **Función `generate_hypothetical_document(query: str) -> str`** en `src/rag/hyde.py`:
   - Llama a Haiku con prompt: *"Eres un manual técnico PCI. Escribe el párrafo del manual que respondería a esta consulta del técnico, usando terminología formal del sector (no parafraseo conversacional). Query: {query}. Manual técnico:"*.
   - Output: 100-200 palabras de "respuesta del manual" en vocabulario rico.
   - Coste: ~$0.001 Haiku + ~500ms latencia.

2. **Modificar `retrieve_chunks(query)`**:
   - Generar hypothesis = generate_hypothetical_document(query).
   - `query_embedding = embed_query(hypothesis)` en lugar del embedding de query directa.
   - Mantener keyword/intent search con la query original (para no perder modelo product).

3. **Variante con RRF (mejor)**: hacer 2 retrievals — uno con embedding(query), otro con embedding(hypothesis) — y combinar con Reciprocal Rank Fusion. Captura tanto matches literales como adaptados.

4. **Smoke test**: hp001, am003, casos de vocabulary mismatch confirmados.

5. **Eval completo**: validar delta y descartar regresiones.

**Coste**: ~3-4h (función HyDE + integración retriever + tests + eval). Runtime ~+500ms-1s por query, ~$0.001 Haiku.

**Decisión actual (sesión 17, 25 abril 2026)**: PRIORIDAD ALTA — siguiente paso tras Fase 1. La razón es escalabilidad real al perfil de técnico (léxico no sofisticado, vocabulary mismatch frecuente), no caso aislado de hp001.

**Update sesión 18 (25 abril 2026) — HyDE APLICADO con resultado positivo**:

Implementación: `src/rag/hyde.py` (nuevo) + integración en retriever.py. Modelo `claude-haiku-4-5`, prompt curado para producir párrafo en estilo de manual PCI formal con terminología sectorial. Feature flag `HYDE_ENABLED` (default `true`).

Eval delta (s16=48 baseline vs s18 con HyDE):
- Run 1: 46/52 · Run 2: 48/52 · promedio 47
- **Persistent gains** (FAIL s16 → PASS ambos s18 runs): **hp001, am001, am008** (+3)
- **Persistent regression** (PASS s16 → FAIL ambos s18 runs): **cm008** (-1, patrón TECH_DEBT #23)
- Net estructural: **+2** ganancias persistentes
- Net visible: 0 (48→48) absorbido por variance ~2pt

**hp001 RESUELTO** ✅ — Judge confirmó: *"Todas las afirmaciones del bot están directamente soportadas por F1 (CAD-250-MC-380-es, sección AVANZADO): la ruta AJUSTES > AVANZADO, las tres pestañas SISTEMA/OTROS/REINICIAR..."*. Vocabulary mismatch resuelto vía hipótesis del manual.

Coste runtime: +1 Haiku call por query (~$0.001, ~500ms-1s latencia).

**Estado Fase 2**: COMPLETADA. HyDE en producción.

**Próximo paso**: cm008 + casos similares se han movido al patrón TECH_DEBT #23 (clarify-first vs respuesta con contexto). Fase 1b (BM25+RRF) sigue condicional al gap restante.

### Fase 2b — Metadata enrichment durante ingest (CONDICIONAL, ~1-2 días + $500)

**Qué**: si HyDE no es suficiente para el volumen/latencia de Fase 3 (Telegram live), pre-computar synonyms/FAQs/keywords por chunk con Haiku durante ingest. Indexar en FTS.

**Por qué condicional**: HyDE cubre el mismo caso (vocabulary mismatch) sin re-ingest, pero pagando latencia runtime. Si en producción la latencia de HyDE es problemática (>2s percibido por técnico bajo presión), metadata enrichment es el upgrade que mueve el cómputo del runtime al ingest.

**Trigger**: solo si tras HyDE en producción detectamos que la latencia añadida (~500ms-1s) crea fricción real para los técnicos. Hasta entonces, no merece la pena pagar $500 + re-ingest cycle.

**Coste**: ~1-2 días + $500 API.

### Fase 3 — Agentic RAG con failure detection + reformulación (Fase 4 del proyecto, condicional, ~1 semana)

**Qué**: Claude decide dinámicamente si tiene info suficiente; si no, reformula query y pide retrieval otra vez. Opcionalmente multi-hop (2-3 búsquedas encadenadas para preguntas compuestas).

**Por qué tercero (y condicional)**: solo aporta valor cuando el bottleneck deja de ser vocabulary (cubierto por 1+2) y pasa a ser (a) queries multi-hop reales *(ej. "qué cambios de cableado migrando de AFP-200 a ID3000")*, (b) queries que requieren que el bot decida cuándo parar/reformular, (c) multi-turn (TECH_DEBT #19). Con las 52 preguntas actuales no hay signal claro de multi-hop; predominan single-hop.

**Cons** si se implementa prematuramente: 2-3× latencia/coste por query (inaceptable en campo con alarma sonando), loops impredecibles difíciles de debuggear, cambio arquitectural mayor.

**Cómo**: Claude Agent SDK o tool-use nativo. Definir tools `search_corpus(query, top_k)`, `clarify_with_user(question)`, `finalize_answer(response)`. Loop hasta terminación con límite de 3 iteraciones.

**Coste**: ~1 semana + cambio infra + eval multi-turn.

### Relación entre las fases

Son **capas ortogonales, se apilan** (no son alternativas):

```
┌──────────────────────────────────────────┐
│  Fase 3 — AGENTE (orchestration)         │ ← solo si multi-hop/multi-turn
│  decide cuándo reformular / parar        │
├──────────────────────────────────────────┤
│  Fase 1b — BM25 + RRF (condicional)      │ ← solo si plateau <95% post 1+2
│  hybrid fusion vector + BM25             │
├──────────────────────────────────────────┤
│  Fase 2 — HyDE ✓ done                    │ ← sesión 18
│  query → hypothetical doc → embed        │
├──────────────────────────────────────────┤
│  Fase 1 — RETRIEVAL weighted FTS ✓ done  │ ← sesión 17
│  section_title (A) + content (B)         │
├──────────────────────────────────────────┤
│  Fase 2b — Metadata enrichment           │ ← solo si HyDE latency duele
│  synonyms + faqs + keywords (CONDICIONAL)│
└──────────────────────────────────────────┘
```

Apilar Fase 3 sobre Fase 2 + Fase 1 = agente reformulando queries sobre retrieval con HyDE (máxima probabilidad de encontrar). **Nunca hacer Fase 3 antes de Fase 2**. Fase 1b y Fase 2b son condicionales, se evalúan según el gap restante post-Fase 2.

### Decisión actual (sesión 16, 24 abril 2026)

Diferido. Fase 1 es candidata prioritaria para sesión 17 (quick win, alto ROI). Fase 1b (BM25+RRF) condicional: solo si métricas plateau <95% tras Fase 1+2 y análisis de FAILs muestra gap de retrieval recall. Fase 2 se activa cuando se acerque el despliegue de Fase 3 Telegram (necesitamos runtime determinístico y baja latencia). Fase 3 solo si/cuando aparezcan signals reales de multi-hop o el bot necesite decidir dinámicamente (probablemente Fase 4+).

**Coste estimado total**: Fase 1 = 3-5h · Fase 1b = 5-7h (condicional) · Fase 2 = 1-2 días + $500 · Fase 3 = 1 semana (condicional).

### Update sesión 17 (25 abril 2026) — Fase 1 APLICADA con resultado neutral

**Aplicado**:
1. Migration 003: `search_vector` recompuesto con `setweight(section_title='A', content='B')` en 167,569 chunks. Trigger function reemplazada. GIN index reconstruido en bulk (~4 min) tras drop+update+recreate.
2. RPC `search_chunks_text` fix: antes recalculaba `to_tsvector('spanish', content)` inline. Ahora usa `search_vector` con `ts_rank` y `spanish_unaccent`.

**Lecciones operacionales**:
- Supabase SQL Editor tiene proxy timeout ~60s. Pooler tiene `statement_timeout=2min`. Ninguno suficiente para UPDATE de 168k chunks con weighted tsvector.
- Fix: conexión directa via `DATABASE_URL` (pooler URI) + `SET LOCAL statement_timeout=0` + drop GIN antes del bulk UPDATE + recreate después.
- Tiempo real: ~3h para el UPDATE, ~4 min para recreate GIN. Standard Postgres pattern para large bulk operations.

**Eval delta (3 runs comparados)**:
- Sesión 16 final: 48/52 (92%)
- Sesión 17 run 1: 45/52 (87%)
- Sesión 17 run 2: 46/52 (88%)

**Análisis honesto**:
- Persistent regression: solo `am003` — bot ahora ve datos del ASD531 en F (antes ASD535) pero sigue clarificando por política TECH_DEBT #23. Trade-off filosófico documentado.
- Persistent gain: solo `am001` — recovered.
- Resto del delta visible son flips de variance entre runs (hp003/011/012/014 oscilan, históricamente flaky).
- **Net real: 0 PASS** (+1 −1).

**hp001 (objetivo original) NO RESUELTO**:

El chunk target (`AJUSTES > AVANZADO`) sí ocupa top-1 y top-2 por `ts_rank` en SQL directo. Pero **el chunk NO contiene "programación" literal** — el manual usa "configuración" + "ajustes" + "puesta en marcha".

`plainto_tsquery('menú programación avanzada')` produce `'menu' & 'programacion' & 'avanz'` (AND). El chunk target tiene `'menu'` y `'avanz'` pero NO `'programacion'` → no matchea con `@@`.

**Esto es vocabulary mismatch puro.** Setweight + title boost mejora ranking solo cuando los términos sí coinciden. Cuando el técnico usa terminología distinta del manual ("programación" vs "configuración"), Fase 1 no alcanza. Para cerrar hp001 se necesita:
- **Fase 2 (synonyms en metadata enrichment)**: durante ingest, Haiku genera sinónimos por chunk. *"configuración" → ["programación", "setup", "ajustes"]*. Indexar synonyms en FTS.
- **HyDE**: el bot expande la query con paraphrase generada por LLM antes del retrieval.

**Estado Fase 1**: COMPLETADA pero efecto neutral en eval. Infra mejorada (search_vector weighted, RPC con ts_rank, GIN index aprovechado, unaccent uniforme). Base sólida para Fase 2.

**Próximo paso**: Fase 2 (metadata enrichment) tiene ROI más alto que las micro-iteraciones sobre prompt. Fase 1b (BM25+RRF) sigue condicional al gap post-Fase 2.


---

## 26. Judge upgrade roadmap — gold standard humano + cross-model + panel ensemble (sesión 19)

**Estado actual del judge (sesión 19)**: ~7/10 vs state-of-the-art. **Above-average** para early-stage RAG project pero **NO top-tier**. Lo que tenemos sí está alineado con best practices intermedias (rúbrica multi-dimensional G-Eval, separación citation/corpus_faithful inspirada en RAGAS, verification chunks, JSON structured output, temperature=0, calibración iterativa). Lo que **falta** para llegar a top-tier:

### Gaps identificados (en orden de impacto)

1. **Sin gold standard humano** — el más impactante. Las 52 preguntas tienen `verified: false`. No sabemos si el judge está bien calibrado (podría tener 80% accuracy o 60%, no hay forma de medir).
2. **Mismo modelo evaluator que generator** (ambos Sonnet 4.6). Comparten blind spots — si Sonnet "no ve" una alucinación al generarla, "no la ve" al juzgarla.
3. **Single judge (no panel ensemble)** — variance individual no mitigada.
4. **Booleano true/false** en lugar de escala 1-5 con anchors (G-Eval canonical).
5. **Sin holdout/dev/test split** — calibrar judge contra mismas preguntas que evalúas → overfitting riesgo.
6. **Sin self-consistency** (N runs por evaluation, consensus voting).

### Roadmap por fase

**Sesiones 20-25 (desarrollo, sin técnico real)** — NO upgrade. Razones:
- Cross-model: costo alto, beneficio incierto sin gold standard que mida si mejora algo.
- Panel ensemble: 3-5× cost sin justificación real hoy.
- Score 1-5: refactor grande, beneficio marginal sin más granularidad real necesaria.

**Cuando Fase 3 (Telegram + técnico real)** — PRIORIDAD:
1. **Gold standard humano** (~2-3h del técnico). Recoger 15-20 queries de los técnicos en producción, técnico verifica las respuestas correctas. Marcar `verified: true` en YAML con feedback estructurado.
2. **Medir judge agreement** contra gold (Cohen's kappa, F1, accuracy). Threshold ~85%.
3. Si agreement <85%:
   - **Cross-model**: probar Claude Opus 4.6 (cross-tier mismo vendor) o GPT-4 (cross-vendor) como judge alternativo. Comparar agreement con humano.
   - Si sigue <85% → **panel ensemble** (3 jueces, consensus voting).
4. **Holdout split**: separar preguntas calibration (~10) vs eval (~42). Calibrar prompts/rules del judge solo contra calibration set; medir bot solo contra eval set.

**Cuando Fase 4 (producción 100+ queries reales)**:
5. **Self-consistency** (3 runs por evaluation, majority vote). Solo si volumen y variance lo justifican.
6. **Score 1-5 con anchors** si necesitas granularidad para detectar regresiones sutiles.

### Coste estimado

- Gold standard: ~2-3h del técnico (humano) + ~1h tuya para integrarlo. $0 API.
- Cross-model probe: ~$10-15/eval extra (Opus es ~3× más caro que Sonnet). 1-2 evals para decidir.
- Panel ensemble: 3-5× cost por eval. Solo si agreement humano-judge muy bajo.
- Self-consistency: 3× cost del judge. Solo si variance es problema real.

### Por qué importa

Sin gold standard humano, **estamos optimizando una métrica sin saber si correlaciona con calidad real**. El judge puede estar consistentemente mal en algún tipo de caso y nosotros mejorando hacia esa señal incorrecta.

**Trigger para implementar**: primer técnico real disponible en Fase 3.


---

## 27. Prompt caching del generator — diferido para Fase 3 con TTL 1h (sesión 19)

**Estado actual**: caching del generator REMOVIDO (commit revierte sesión 19 attempt).

**Por qué se removió**: el caching ephemeral de Anthropic tiene TTL de 5 min. Para evals (52 queries/30 min, ~30s entre cada) hit rate ~98% → ahorro ~$0.78/eval (~10% del coste). Para producción Telegram con uso disperso (técnicos consultando esporádicamente, >5 min entre queries de un mismo técnico), cache miss + write fee 25% extra → **coste neto incrementa**. La complejidad no compensa para el patrón de uso real.

**Cuándo reconsiderar**:
- **Si al acercarse Fase 3 (Telegram live)** evaluamos: el patrón de uso real (burst vs disperso). Si burst (varios técnicos coincidentes) → ephemeral 5min vale. Si disperso → considerar Anthropic 1h cache (lanzado recientemente con multiplier de precio distinto).
- **Anthropic 1h cache**: TTL extendido a 1 hora. Multiplier write fee mayor (~+50% vs ephemeral) pero amortiza a usos dispersos. Ideal para tráfico tipo soporte técnico.

**Coste estimado para reactivar**: ~30 min (re-implementar cache_control con la variante apropiada al patrón observado).

**Trigger**: instrumentación de Fase 3 que muestre patrón de uso real > revisar cuál variante de caching aplica.


---

## 28. Side-effect del bloque TABLAS MATRIZ: queries genéricas degradan de clarify a admit_no_info (hp019, mc004 — sesión 20)

**Estado actual**: tras aplicar Fase A de TECH_DEBT #24, dos casos previamente PASS regresionaron:

- **hp019** (`¿rango de temperatura de los detectores Detnov serie ASD?`): en S19 el bot clarificaba ("¿qué variante ASD usas?") — judge=PASS. En S20 el bot hace `admit_no_info` ("ningún fragmento cubre la serie ASD") — judge=FAIL porque YAML pide `answer` y `behavior_match=false`. La respuesta del bot es honesta pero menos útil; el corpus SÍ contiene ASD535 (el retriever simplemente no lo trajo en este turno).
- **mc004** (`¿dónde se conecta el cable de tierra?`): en S19 el bot clarificaba directo ("¿qué equipo tienes?") — judge=PASS. En S20 el bot responde con info de 3 productos (MIE-MI-120, EFS/EM 8, ID2000) y termina con clarify final — judge=FAIL porque `behavior_observed=answer` no coincide con `expected=ask_clarification`.

**Hipótesis causa**: el bloque nuevo "TABLAS MATRIZ" introducido en `src/rag/generator.py` SYSTEM_PROMPT (sesión 20) contiene ejemplos del tipo "Admite explícitamente: 'El manual incluye [...] pero no es legible'". Estos ejemplos refuerzan el patrón admit/answer, lo que parece desplazar ligeramente el equilibrio del bot en queries genéricas familia/ambigua donde la decisión clarify-vs-admit-vs-answer es naturalmente borderline.

El nuevo bloque NO menciona clarification — el efecto es indirecto, vía bias estilístico hacia "respuestas que admiten limitaciones" en lugar de "respuestas que piden información al técnico".

**Por qué no se revierte ahora**: el net global es claramente positivo (+4 PASS, fuera de variance ±2pt). Las 6 ganancias incluyen casos importantes como hp007 (target original) + cm004/cm008 (cross_manual) + hp005/hp015 (happy_path), que justifican aceptar las 2 regresiones. Además, las 2 regresiones están en queries genuinamente borderline donde tanto clarify como admit son comportamientos defendibles.

**Trigger para revisar**:
- Si en sesión 21+ corremos otra vez el eval y las 2 regresiones persisten sin variance (NO flippan a PASS espontáneamente), es regresión estructural y hay que ajustar.
- Si hp019/mc004 flippan a PASS en una run aislada → era variance, no regresión. Cerrar #28.

**Acciones futuras posibles si confirma regresión persistente**:
1. **Ajuste menor del bloque TABLAS MATRIZ**: añadir disclaimer "este bloque NO modifica las reglas de CLARIFY-FIRST de TIPO 2 (familia/ambigua)" para que el LLM no transfiera el bias.
2. **Recalibrar YAML**: hp019/mc004 son borderline; si admit_no_info es comportamiento defendible para Detnov ASD genérico (sin sufijo), `expected_behavior` podría ser `admit_no_info` en hp019. Mismo análisis para mc004.
3. **TECH_DEBT #23 v2 (tool use / prompt routing)**: si esto se reproduce, refuerza la lección de que el SYSTEM_PROMPT está saturado y el approach correcto es separar en tools/sub-prompts.

**Coste estimado**: 30min recalibración YAML + revert si no es variance, o 1-2h ajuste del bloque con tests.


---

## 29. RLS audit en tablas existentes — defensa en profundidad sobre anon key (sesión 21)

**Estado actual**: en sesión 21 se creó la tabla `user_consent` con Row Level Security (RLS) habilitado siguiendo el aviso de Supabase ("New table will not have RLS enabled"). Las tablas previas (`chunks`, `query_logs`, `feedback`, `documents`) probablemente NO tienen RLS habilitado — patrón heredado de migrations antiguas cuando el aviso aún no aparecía o se ignoraba.

**Por qué importa**: el bot accede a Supabase con `SUPABASE_SERVICE_KEY`, que **bypassea RLS automáticamente**. Por tanto el bot funciona idéntico tenga o no tenga RLS habilitado. **Pero**: si en algún momento la `anon` key del proyecto se expone (frontend, demo público, tooling externo, leak inadvertido en repo público), las tablas sin RLS quedan en lectura/escritura libre para cualquiera con esa key. Defensa en profundidad → habilitar RLS en todas las tablas y crear policies explícitas para los pocos casos donde anon necesite acceso (hoy: ninguno).

**Acción propuesta**:
1. Auditar qué tablas tienen RLS hoy (`SELECT relname, relrowsecurity FROM pg_class WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace;`).
2. Para cada tabla sin RLS, ejecutar `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;` (no crea policies → default-deny para anon, service_role sigue funcionando).
3. Smoke test del bot tras cada ALTER para confirmar que nada se rompe (debería ser invariante porque service_role bypassea).
4. Documentar en `supabase_schema.sql` el patrón "todas las tablas tienen RLS por defecto".

**Coste estimado**: 30-60min (audit + ALTERs + smoke). Idempotente si se hace `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` que no falla si ya está habilitado.

**Trigger para hacerlo**: cualquier momento sin presión (no bloqueante para deploy DG porque service_role funciona). Idealmente antes de exponer cualquier endpoint público o el primer despliegue multi-tenant.

**No urgente porque**: hoy ningún cliente usa anon key contra esta DB. El riesgo es de exposición futura, no presente.


---

## 30. Markdown raw aparece en respuestas con filenames con `_` — fallback sin formato (sesión 21 smoke)

**Estado actual (27 abril 2026, smoke step 9)**: respuestas que mencionan filenames con guiones bajos (ej. `MI_372_es_2024 e`) muestran asteriscos literales en lugar de negritas (`*CAD-250*` en vez de **CAD-250**). Causa: el parser Markdown legacy de Telegram interpreta cada `_` como inicio de cursiva, encuentra desbalance, lanza excepción, y el fallback en `_process_query` (líneas 411-414) reenvía el mensaje **sin** `parse_mode`, mostrando los asteriscos sin renderizar.

**Reproducción**: cualquier query Detnov cuya fuente sea un manual con `_` en el filename (común: `MI_372_es_2024`, `MI_DT_015`, etc.).

**Impacto**: estético, no funcional. La respuesta es legible pero con asteriscos visibles que rompen la presentación profesional ante el DG.

**Fix propuesto** (3 alternativas, ordenadas por esfuerzo):

1. **Quick fix**: en `format_for_telegram()` escapar `_` con `\_` antes de enviar. Riesgo: rompe el `_italic_` legítimo del bot. Coste: 15min.
2. **Cambiar a `MarkdownV2`**: requiere escapar más caracteres pero el escape es bien definido y `python-telegram-bot` provee `helpers.escape_markdown(text, version=2)`. Coste: 1-2h con tests.
3. **Cambiar a `parse_mode="HTML"`**: convertir el output a HTML (`<b>`, `<i>`, `<code>`). Mucho más robusto contra contenido del usuario. Coste: 2-3h (modificar `format_for_telegram` + `convert_tables` + tests).

**Recomendación**: opción 3 (HTML) en sesión futura. El bot evolucionará a respuestas más complejas (tablas, código, links) y HTML es más sostenible que Markdown legacy. Mientras: aceptar el bug estético.

**No urgente porque**: queries con filenames sin `_` (la mayoría) renderizan bien. Y el contenido del mensaje es perfectamente legible aunque con asteriscos visibles.


---

## 31. Shortcuts del bot no se loggean en `query_logs` — gap de observability (sesión 21 cierre)

**Estado actual (28 abril 2026)**: `log_query()` solo se invoca al final de la rama RAG completa de `_process_query` (`src/bot/telegram_bot.py:478`). Los `return` tempranos de los shortcuts (greeting, thanks, bye, **catalog**, manufacturer-mismatch, manufacturer-without-model) nunca llegan al log. **Evidencia**: la query "¿Qué fabricantes tienes?" del smoke real post-hotfix-2 (que sí entró por `_handle_catalog`) no aparece en el CSV de `query_logs` exportado por Alberto. La misma query, días antes (commit `cebf3ef` pre-hotfix-2 cuando regex aún no detectaba "fabricantes"), sí aparece porque cayó a RAG.

**Por qué importa**: si los técnicos preguntan mucho "¿qué fabricantes tienes?" o saludan, no hay forma de saberlo. Se pierde:
- Métricas de uso real por canal (¿% queries que son catálogo?, ¿% saludos vs RAG?)
- Detección de patrones de uso (¿mismo técnico pregunta catálogo a diario? señal de mala UX en respuestas RAG)
- Trazabilidad RGPD completa (auditar TODO lo que el bot dice)

**Acción propuesta**:
1. Añadir columna `route TEXT` a `query_logs` con valores: `'rag'`, `'catalog_shortcut'`, `'greeting'`, `'thanks'`, `'bye'`, `'manufacturer_mismatch'`, `'manufacturer_no_model'`.
2. Llamar `log_query()` en cada rama de shortcut (con `chunks_used=0`, `product_models=[]`, `category=None`, `response_time_ms` medido).
3. Migración de schema en `migrations/`. Default `route='rag'` para filas históricas.

**Coste estimado**: 1-2h (cambio simple pero hay que tocar ~6 ramas + migración + tests).

**Trigger para hacerlo**: (a) Alberto pide métricas de uso por canal post-deploy DG, O (b) detectamos un técnico con comportamiento extraño (queries que no llegan al RAG) y necesitamos visibilidad, O (c) cualquier sesión sin presión.

**No urgente porque**: hoy nadie está mirando esos números. Se acepta el gap mientras la base de uso sea pequeña (Alberto + DG en demo).

---

## 18. #6 — Atribución de fabricante: decisiones conscientes y diferidos (28 mayo 2026)

**Qué se hizo**: se atribuyó `manufacturer` a los 9.260 chunks (499 docs) que lo tenían NULL, vía Haiku sobre blurb B7 + portada + legal (`scripts/fix_null_manufacturer.py` → `refine_null_mfr_review.py` → `apply_null_mfr.py`). Resultado: 0 NULL, 28 marcas. El catálogo (`data/model_catalog.json`) pasó de 178 (regex) a ~536 modelos. Rollback snapshot: `logs/null_mfr_rollback_20260528T182051Z.json`.

**SIN spot-check (aceptado por Alberto, dejar trazado)**: las **318 correcciones de `product_model`** (junk→real, p.ej. UN-10→NRT) + las atribuciones por `docX-rescue` (46) y `new-brand` de Haiku (85) se aplicaron **sin verificación humana por ítem**. Si aparecen anomalías de retrieval en esos modelos/docs → re-verificar contra el rollback. El spot-check se omitió deliberadamente.

**Decisiones del gate (en `scripts/build_model_catalog.py`)**:
- `manufacturer-name`: excluye un product_model que es nombre de marca **solo si no tiene dígito** (`Spectrex`/`TG-NOTIFIER` fuera; `System 5000`/`SENSOR-6424` dentro).
- `compound`: slash-multi-código se **divide en componentes** (`AM2020/AFP1010`→AM2020+AFP1010); conjunción/fragmento (`AM2020 y AFP1010`, `AM2020-y`) se descarta. **Gap: compuestos pure-alpha sin dígito (`ZXAE/ZXEE`) se pierden** — no se cataloguean (caen a vector search). Trigger: query real necesita esa variante.
- **29 product_model → `unknown`** (basura: formularios admin, descripciones, multi-modelo) → excluidos del catálogo, no se escribió la basura.

**classify catalog-first (no seed-first)**: la marca real del dato manda; el seed solo es fallback para modelos fuera del catálogo. Corrige VESDA→Xtralis, 40-40→Spectrex, ASD→Securiton. **El seed conserva entradas legacy hoy-erróneas (VESDA/40-40/ASD→marca original) pero son inocuas** (el catálogo las sobreescribe). End-state limpio: el seed encoge a cero conforme el catálogo es fuente única — limpieza futura opcional.

**Cross-brand por ecosistema** (`_ECOSYSTEM_OF` en `retriever.py`): `Xtralis↔Notifier`, `Securiton↔Detnov` no se marcan cross-brand (mismo ecosistema/distribución). **Pendiente confirmar**: `System Sensor↔Notifier`. **Versión escalable**: leer la columna `distributor` (hoy poblada solo ~3.500 chunks) en vez del mapa hardcoded → completar `distributor` es tarea futura.

**Diferido — `product_models TEXT[]` (campo multi-modelo)**: idea de Alberto (#6) para alocar un chunk a varios modelos sin el junk compuesto. Es el modelo de dato más correcto a largo plazo, pero implica migración de esquema + refactor de ~8 funciones del retriever (todas usan `product_model` con imatch/eq) + cambios en RPCs. **Diferido**: el split en detección ya da la conducta multi-modelo. **Trigger**: el tagging multi-modelo se vuelve generalizado, o el routing por substring del compuesto causa errores reales de retrieval.

**Residual `product_model=unknown`**: seguro (excluido del catálogo por diseño), bajo valor, alto coste manual. **Diferido**. Trigger: una query real necesita un producto que vive en un doc residual-unknown.

**Follow-up de idioma (no #6)**: `VSN4-PLUS_ITA` y otros docs en italiano — política dice idiomas ≠ ES/EN caso a caso; chunks_v2 tiene columna `language`. Pendiente decidir si filtrar italiano del retrieval al técnico español.

---

## 32. Auditoría crítica del legacy del retriever — el cuello es GENERACIÓN, no recall (sesión 29)

> **⚠️ ACLARACIÓN "A2" + ESTADO (s44, 4 jun 2026 — verificado en git, NO memoria).** "A2" es AMBIGUO; son TRES cosas distintas:
> 1. **A2-fusión** (ESTA entrada #32) = constantes planas del retriever (`retriever.py:407/458/491/516/973/1019/1042`). **NUNCA tocada**: `git log --all -S` sobre la constante `0.85` → solo el commit inicial (nunca borrada en NINGUNA de las 24 ramas + 0 stashes); viva en `origin/main` HOY (diff vacío vs working tree). Es la que s44 va a **BORRAR**.
> 2. **A2-extracción** (`src/reingest/extract.py`, este doc §556/607) = la etapa LlamaParse que **CONSTRUYÓ** chunks_v2. CONSERVADA (es el corpus bueno).
> 3. **Ingesta v1** (`src/ingestion/`, `#38`/Track C) = lo que SÍ se borró en s43 (24 ficheros pdfplumber). NO es ningún "A2".
>
> **Reframe del lever (s44, `DECISIONS.md` DEC-018 pendiente al cierre):** A2-fusión = **BORRAR el cruft de scores planos + rankear por coseno Voyage real** (conservar guardas: filtros modelo/categoría [§1241] + ruta diagrama + match exacto de modelo), NO "construir una fusión RRF". El dúo (cross-model GPT + sub-agente, verificado en código) tumbó "A2-first como build": (a) la atribución de burial se midió **HyDE-OFF**; producción corre **HyDE-ON** por default (`hyde.py:39`, sin override commiteado — valor en Railway PENDIENTE de confirmar) → gap NO reconciliado con el path real; (b) `RETRIEVAL_TOP_K=15` (`config.py:36`) → re-estampar sobre `merged` alcanza ~2 hechos de 6 (los de rango vectorial 16-50 exigen ENSANCHAR el fetch, cambio aparte); (c) per-hecho ≠ per-pregunta (solo el árbitro end-to-end lo zanja). Plan corregido → `PLAN_RAG_2026` bloque s44. **POST-s44 (DEC-018, SHIPPED → DEPRIORITIZADO):** el lever NO fue borrar-cruft — fue **#16 retrieve-wide** (`RETRIEVAL_TOP_K` 15→50), que **SORTEÓ el burial** (el CORTE `merged[:15]`) sin tocar las constantes planas → **#32/borrar-cruft DEPRIORITIZADO**: el cruft de scores planos SIGUE VIVO pero **ya no bloquea calidad** (FALLO ~6→1 con retrieve-wide solo, medido K=3); revisitar solo si una medición futura lo señala. Residuales de retrieval (→ s45): **hp006** (recall-miss, 'Tierra' no recuperable → corpus/term-exacto/BM25), **HyDE-off** (DEC-018f: re-medir on-vs-off EN el path retrieve-wide — la medición s29 NO transfiere; + override Railway), **cap-rerank-~30** (tuning de latencia, A/B vs las ganancias s44 de #16).

**Hallazgo (medido determinista + matcher estricto)**: NINGÚN lever de recall (reranker/Voyage rerank-2.5, subir top-k, RRF, dense-only) convierte en mejor calidad **end-to-end**. dense-only sube recall 51→59% pero da **−2 FALLO** end-to-end (4/9/6 vs baseline 3/12/4) por **alucinación CROSS-PRODUCT** al quitar los filtros de modelo/categoría. La conversión recall→calidad la bloquean la **GENERACIÓN** (el bot admite no-info con el dato en top-5; síntesis incompleta) + el balance precisión/recall. **El árbitro es el eval END-TO-END, no el recall metric.**

**Distinción clave (norma de auditoría legacy — Alberto, sesión 29)** — dos tipos de legacy en el retriever:
- **Scoring-heurísticas = CRUFT** (constantes planas por-path 0.65/0.80/0.85; boosts genéricos spec/trouble): entierran los matches vectoriales reales (hp019: tabla de specs a vector-sim 0.73 caía a rank 26 bajo ~25 chunks flat-0.85). Arreglar/quitar.
- **FILTROS = GUARDAS de precisión/anti-alucinación** (modelo/categoría): hieren el recall metric (filtro de categoría −18 pts: broad 59% vs filtered 41%) PERO previenen contaminación cross-product. Para un bot que NO debe alucinar, **+FALLO (alucinación) > +recall → SE QUEDAN**. No son cruft.

**Inventario a escrutar contra el eval (cada pieza demuestra su delta o se va)**:
- `_filter_to_query_models` (hard-filter modelo): HIERE recall (hp003/hp010) pero da precisión → ¿soft vs hard? medir el trade-off.
- filtro de categoría en `vector_search` (Step 2): −18 pts recall, mismo trade-off.
- `_diversify_by_source_file` / `_diversify_by_manufacturer`: heurísticas con scores planos (0.72) + fetches suplementarios.
- `typed_search` / `diagram_search` (scores planos 0.82/0.85): ¿el diagrama-en-wiring se gana su sitio?
- `src/rag/validator.py` (dormant desde s13), helpers cross-brand (s14 "preserved unused"): código muerto — ¿borrar?
- `MODEL_PATTERN` (seed legacy, ya catalog-first): encoge a cero — limpieza opcional.
- **HyDE** (`hyde.py`): medido — no mejora recall ni formal (51≈) ni coloquial (49 vs 47 dense) Y rompe determinismo (LLM no bit-determinista → misma pregunta, respuesta distinta). Candidato a OFF por defecto; conservar tras flag para revisitar con queries coloquiales reales (su caso de diseño).

**Trigger**: la sesión #15 (lever de generación). Auditar estas piezas con el eval determinista+estricto end-to-end, **sin subir alucinación** (mantener filtros). Base de medición LISTA: matcher estricto + determinismo (PR#15, en main) + flags `RETRIEVER_DENSE_ONLY`/`HYDE_ENABLED` para A/B; `test_bot_vs_gold` ya replica producción (árbitro end-to-end).

**Actualización s36 (1 jun 2026 — auditoría DEC-003 RE-CONFIRMA este bug, y añade matiz):** la auditoría
del embudo (HyDE-off por hecho atómico, `scripts/audit_retrieval_funnel.py` + `validate_s29_burial.py`)
confirmó el burial de scores planos en **hp017** (el manual de Config-ES de la PEARL está en vector rank 3
pero no llega al pool-15) — idéntico al hp019 de esta entrada. **DOS matices nuevos, verificados:** (1) hp017
está ADEMÁS mal-etiquetado `product_model='AC-220'` (no PEARL) → excluido del boosting por modelo: **es un
bug de METADATA (clase B5), no solo de scoring** — sanearlo es lo que mete el chunk al pool, no RRF. (2)
**`doc_type` está poblado solo al 6%** (NULL en todos los manuales del eval) → un routing por `doc_type` no
es viable sin re-poblarlo. **Lección s36 (feedback_my_bias): se propusieron 4 levers (change-1/doc-routing/
fail-open/RRF) y los 4 cayeron por review+verificación** — el bucle viene de medir sobre PROXIES (recall,
HyDE-off, gold roto) en vez del árbitro end-to-end. **Decisión: NO tocar el merge/levers de retrieval hasta
crecer el ruler + medir END-TO-END** (DEC-003). El bug de scores planos sigue siendo cruft real, pero su fix
debe medirse end-to-end, no por recall (RRF ya lo demostró — ver #25 Fase 1b). Canónico: `DECISIONS.md` DEC-005.

---

## 33. Auditoría sistemática del GOLD — el ruler está parcialmente ROTO (conflictos/OCR), no solo estrecho (sesión 30)

**ACTUALIZACIÓN s33 (31 may 2026): CERRADO — 19/19 golds verificados contra la fuente.** La cola
"necesita técnico real" era DEMASIADO AMPLIA. Tier A (12): sin error factual; hp007 (matriz VESDA)
verificado por render. Tier B (5): hp006/09/17 conducta corregida (admit→answer), hp011 OCR retrofitado.
**Tier C (2: hp012/hp018 — los que de verdad se habían diferido a técnico) — RESUELTOS SIN TÉCNICO vía
render + cross-model:** hp012 = conflicto REAL ES-vs-US (AFP1010 2 lazos/396 ES vs 4 lazos/792 US 15088SP)
→ answer-con-conflicto; hp018 = el gold s27 citaba el PRODUCTO EQUIVOCADO (MIE-MI-310 = ZXAE/ZXEE
convencional, no el e-series ZXe) + 3 valores fabricados → re-anclado a MIE-MI-530 (ZX2e/ZX5e). El render
(toolkit de s31, que NO existía en s30 → de ahí el diferimiento) + cross-model GPT-5.5 + sub-agente
bastaron; el técnico (D1) pasa a spot-checker, no es prerequisito. Detalle: `RULER_DESIGN.md` §4. Residual
CERRADO en la misma sesión: hp009 (también mis-anclado a MI-310) RE-ANCLADO a MIE-MI-530 (ZX2e/ZX5e); la sustancia (lazo = bucle cerrado sin RFL) se confirmó al píxel (f19 Fig 9/10).

**ACTUALIZACIÓN s34 (1 jun 2026): change-1 re-validado contra el ruler corregido → REVERTIDO.**
Con 19/19 verificados, el A/B end-to-end del lever de generación `change-1` (bloque anti-falso-rechazo
en `generator.py`, que entró a producción en PR #17) mostró: NO rescata ninguno de los 5 falso-rechazos
(idénticos con/sin change-1 → son **retrieval**, p.ej. hp018: el chunk del dato pedido no llega al top-5)
e **induce sobre-respuesta** (hp015: el bot CONSTRUYE un procedimiento NO documentado —"puentear terminales para aislar un detector"— sobre datos de cableado REALES: los terminales 1/3/4 SÍ están en los fragmentos F2/F3 del CCD-103. Es **inferencia procedimental no soportada** —con disclaimer "no está en el manual"—, NO alucinación de datos; matiz verificado re-corriendo el retrieval. El riesgo para el técnico es real; el mecanismo no es fabricación de datos sino inferencia no documentada inducida por el prompt anti-rechazo).
El "FALLO 5→3" de s30 era artefacto del ruler roto; ya no se corrobora → **revertido** (PR a main). El
revisor adversarial (Protocolo 3, GPT-5.5) cazó 9 over-claims de framing míos → la recomendación se acotó
a "revertir por PRECAUCIÓN (riesgo hp015), NO por superioridad de B". **Próximo lever = HIPÓTESIS abierta**
(retrieval/reranker vs síntesis/v2-prompt): requiere auditar si el dato omitido en los 13 PARCIAL estaba
o no en el top-5 (no hecho). Caveats: el A/B fue HyDE-off (modo diagnóstico, prod usa HyDE); judge opaco
(s32), aunque el delta A/B es robusto a su sesgo y hp015 se verificó en la respuesta cruda. A/B
reproducible: `HYDE_ENABLED=false python scripts/test_bot_vs_gold.py` (resultados por-k gitignored, no source).

**Disparador**: el experimento retrieve=50 (#16 "retrieve wide, generate narrow") marcó "regresiones peligrosas" en hp012/hp018 que, al verificar contra la **FUENTE** (no contra el gold), resultaron **errores del gold, no alucinaciones del bot**. Eso obligó a auditar los 19 golds de `evals/gold_answers_v1.yaml`.

**Método**: agentes Opus 4.x contra `chunks_v2` + PDFs en MANUALS_DIR, escépticos del gold Y de sí mismos (clasificar error-factual / conflicto-entre-manuales / OCR / conducta-discutible; verificar aritmética).

**Resultado (19 golds)**: 12 CORRECTOS; **hp007** ERROR-FACTUAL (3 frecuencias de la matriz de mantenimiento VESDA mal asignadas — pero es una MATRIZ #24, no verificable sin renderizar el PDF, que aquí falla por falta de `pdftoppm`); **hp012** CONFLICTO (España MFDT280/MPDT280 = 2 lazos/396, internamente consistente, vs US 15088SP = 4 lazos/792); **hp018** CONFLICTO/OCR (gold cita MI-310 ZX5e=5 salidas/EOL 10kΩ con OCR degradado; MI-530 dice ZX5e=4/EOL 6K8; MI-310 podría ser otro producto, ZXAE/ZXEE); **hp011** OCR (sustancia OK pero labels "P.18/P.02" no existen —reales r.i/t.H— y default no es 295s sino "--"); **hp006/hp009/hp017** CONDUCTA-DISCUTIBLE (gold dice admit_no_info pero el corpus SÍ cubre el tema → debería answer; hp017 el config-manual de la PEARL `997-671-005-3_Configuration_ES` está en el corpus con retardos causa-efecto; hp009 cita el manual del producto equivocado).

**Hallazgos meta (los importantes)**:
1. **El ground-truth del gold es parcialmente NO FIABLE** — no solo estrecho (s28-29) sino con errores factuales, conflictos entre manuales (revisión/mercado España vs US/UK) y OCR degradado. No nos fiamos de los veredictos del eval en los ~7 problemáticos hasta resolverlos.
2. **Corregir golds NO es automatizable**: hasta el verificador Opus sobre-afirma (hp012: declaró "gold inconsistente" por un error aritmético propio — 2 lazos × [99 detectores + 99 módulos] = 396, consistente). Matrices (#24), conflictos y OCR necesitan **PDF renderizable + técnico real** (no hay técnicos hasta meses). El triage es automatizable; la corrección NO.
3. **Los errores sesgan a INFRA-valorar al bot** (admit-cuando-debería-responder; valores que penalizan respuestas correctas) → el bot probablemente **rinde mejor que lo que marcaba el eval**; varios "fallos" (incl. buena parte de retrieve=50) eran el bot acertando contra un gold erróneo. → Las cifras de calidad de s28-30 son **indicativas, no firmes**.

**Decisiones (sesión 30)**:
- **NO regla "manual-España-gana"** (Alberto): el ENG a veces tiene MÁS info; conflicto same-version → gold/bot correcto = **surfacear ambos + admitir la discrepancia** (conducta honesta que el SYSTEM_PROMPT ya pide), NO elegir ganador. Distinguir same-version (surfacear) de versiones-distintas (respuesta version-específica) necesita PDF/técnico.
- **Filtrar chunks no-ES/EN del retrieval**: hay fr=47, de=46, pt=3 (96 chunks; no hay IT en chunks_v2 ahora). Filtro `language IN ('es','en')` en el retriever — DIFERIDO a tarea propia testeada (toca las RPC), no bundlear. Mantener EN.
- **Issue de corpus** (separado del gold): el chunk del Apéndice 3 de la ID3000 (hp008) está TRUNCADO en chunks_v2 → riesgo de retrieval (la lista de compatibles no se recupera entera).
- **Arreglar el ruler ANTES del lever del reranker** — evaluar un reranker contra golds rotos repetiría el error de llamar "trampa" a un win.

**Cola (s30, AHORA VACÍA — ver ACTUALIZACIÓN s33 arriba)**: ~~hp007 matriz, hp012/hp018 conflictos, hp011 OCR, hp006/hp009/hp017 conducta~~ → los 19 verificados contra la fuente (render del píxel). El scoring de calidad end-to-end ya puede usar los 19 (no solo el núcleo de ~12 "limpios" de s30).

**Lever de generación (sesión 30, dentro del frame #32)**: change-1 = bloque "DOS ERRORES SIMÉTRICOS" en SYSTEM_PROMPT (rechazar-en-falso con el dato presente = fallo hermano de inventar) → FALLO 5→3 end-to-end (HyDE-off, juez gpt-5.5), sin alucinación nueva → DIRECCIONAL, pero medido contra ruler defectuoso = indicativo. change-2 (completitud) REVERTIDO. Reranker = lever siguiente tras el ruler (research: Zerank-2, Cohere Rerank 4 —fuerte ES—, Voyage 2.5 —identifier-tuned pero degrada fuera de EN—, Jina v3, bge-v2-m3; perfil = ES + identifier-heavy + cross-product → elección empírica; reranker solo NO arregla cross-product → el filtro modelo/categoría SE QUEDA). Repo: change-1 + `RETRIEVE_K_OVERRIDE` (override de retrieve-pool en `test_bot_vs_gold`) en rama `feat/generation-lever`, NO main.

---

## 34. Gaps de corpus-infra destapados por el revisor del localizador (sesión 31)

El review adversarial del localizador del ruler (RULER_DESIGN §2) destapó, **anclado en código**, que chunks_v2 está más incompleto de lo asumido. Alimentan el lever de extracción (#10) y condicionan tanto el localizador del ruler como el bot:

1. **`diagram_url = None` en TODO chunks_v2** (`src/reingest/index.py:61`, follow-up B4 pendiente) y **`has_diagram` impreciso** (`chunk.py:352` = "la página tiene cualquier imagen", logos/cabeceras incluidos). Las cifras 31%/84.9% de #9/#10 son de la tabla VIEJA `chunks`. → respuestas solo-en-diagrama son **invisibles al texto/grep**; el localizador no puede surfacearlas por metadata → render-browse + GAP DE CORPUS. Re-poblar `diagram_url` (B4) es prerrequisito para que el bot adjunte diagramas Y para localizar respuestas visuales (cableado/conexiones — muchas preguntas PCI).

2. **El catálogo (`model_catalog.json`) YA hace split-compound** (`AM2020`, `AFP1010`, `ZX2e/ZX5e` incluidos con `source:split-compound`); los 50 "excluidos" son mayormente risky-acronym/junk, NO productos. → el localizador **REUSA** el catálogo, no re-implementa el split. Residual real: pure-alpha `ZXAE/ZXEE` (gap ya declarado, #18).

3. **Fiabilidad del grep es POR-PÁGINA, no por-doc**: `diagnose_corpus.py:74-81` ya clasifica (escaneado / imagen-heavy / texto-limpio / **mixto**); los manuales UI-screenshot-heavy caen en `mixto` (texto fiable en unas páginas, píxel en otras). Y "digital-native" ≠ texto fiel (7-seg = glifo corrupto sin ser escaneo). → enrutar grep-vs-render **por página** reusando `diagnose_corpus`, no un switch binario por-doc.

4. **El localizador NO se puede validar sobre los 19 golds actuales** — la `page` ya está fijada por el autor → la rebanada vertical no testea el caso duro (encontrar la ubicación de cero). Necesita un **test CIEGO** (pregunta nueva o ignorar la `page` del gold).

**Trigger**: al construir el localizador (Fase 0) y el lever de extracción (#10).

**Meta-lección (s31)**: el localizador se diseñó 3× sobre supuestos del corpus que el código contradecía; el revisor adversarial (Protocolo 3) los cazó leyendo el código → **leer el código real ANTES de diseñar**.

## 35. Scorer atómico del ruler (Fase 2) — construido; refinamientos pendientes (sesión 32)

`scripts/atomic_scorer.py` puntúa la respuesta del bot contra los hechos atómicos del gold, por hecho y transparente (reemplaza el juez LLM opaco). 3 ejes:
- **completitud** (mecánico/determinista): reusa el matcher estricto de PR#15, extraído a `scripts/strict_match.py` (módulo leaf, solo stdlib, sin stack RAG; `retrieval_eval.py` lo importa, behavior-neutral).
- **factual/alucinación** (cross-model GPT-5.5, opcional `--llm`): detecta CONTRADICCIONES de hechos verificados (NO omisiones ni info extra; carve-outs anti-s13; juzga por significado no por etiqueta) → cualquier contradicción = FALLO (asimetría de seguridad). Caracterizado con `evals/factual_gate_fixture.yaml` + `scripts/factual_gate_eval.py`: **5/5 recall, 4/4 especificidad** (n=9 a mano → indicativo).
- **conducta**: heurístico mínimo (answer/admit/clarify).

Demostrado en la rebanada vertical (hp007/hp011/hp017): hp011→FALLO (caza la alucinación "ri=00 inhibido" vs el hecho "r.1 00=permitido"); hp007/hp017→PARCIAL (sin falsos positivos). **El scorer transparente SUPERÓ al juez opaco en hp007** (el juez penalizaba por dato obsoleto).

**Refinamientos pendientes (no bloquean Fase 1, pero antes de fiarse del scorer como árbitro firme):**
1. **Completitud de PROSA es débil** (eje mecánico): sinónimos (`trimestral`≠"cada 3 meses"), `valor` compartido no distintivo (hp007: las 4 tareas anuales comparten "una vez al año" → indistinguibles), códigos 7-seg cortos (`r.1`). → la misma capa LLM del eje factual puede cubrir la completitud de prosa.
2. **`valor` debe ser el IDENTIFICADOR DISTINTIVO del hecho, no una frecuencia/etiqueta compartida.** Re-autorar hp007 (valor=tarea, no "una vez al año"). Fijar como regla de autoría.
3. **Conducta** es heurística → endurecer ahora que Tier B (s33) aporta **5 golds de conducta
   verificados** (hp004 clarify; hp006/09/13/15 answer/answer-parcial, con hechos `ausente-probado`)
   para testear los ejes answer/clarify y la asimetría parcial (present + ausente-probado).
4. **Recall del gate factual sin caracterizar a escala**: n=9 a mano (perturbaciones quizá más fáciles que alucinaciones sutiles reales) → crecer el fixture con casos reales/difíciles.
5. Bug **C1** (substring de anchors, `'40' in '240'`) corregido EN el scorer; frontera **refinada en s32 Tier-A a DÍGITO** (no de palabra): casa `'24'` en `'24V'`/`'24 °C'` pero NO en `'240'` (la de palabra fallaba "24V"; lo cazó hp003 ">24V"). `chunk_has_quote_strict` (PR#15, en strict_match) conserva el `in` crudo → re-tocarlo exige re-validar el eval de recall (live stack). Pendiente al revisar el matcher de recall.

**Proceso (s32)**: 3 reviews adversariales (Protocolo 3): 2× sub-agente Claude (cazaron **C1** substring + 2 over-claims "validado"; verificaron los 3 veredictos contra ficheros) + 1× **cross-model GPT-5.5** (`adversarial_review.py`) que dio independencia CONCEPTUAL y halló gaps que el mismo-modelo NO vio:
- **#1/#3 (ARREGLADO)**: el veredicto decía "sin alucinación" = over-claim; el gate solo descarta CONTRADICCIONES de hechos LISTADOS → wording corregido ("sin contradicción con hechos listados").
- **#2 (ARREGLADO)**: core `manual` (valor=null) quedaba fuera del denominador → un PASS podía OCULTAR core sin puntuar; ahora el veredicto surfacea los core sin puntuar + la dependencia de prosa frágil.
- **#5 (PENDIENTE)**: presencia del `valor` ≠ hecho afirmado bien — el matcher cuenta el token aunque esté en negación/comparación/contexto erróneo ("no es 295 s" casa "295"). Completitud necesita conciencia de negación/contexto (→ capa LLM).
- **#6 (PENDIENTE)**: prosa-overlap no escala a sinónimos/traducción ES↔EN ni terminología de 30+ fabricantes ("cada 2 años"/"bienal"/"biennial") — gap del contrato escalable.
- **#7 (PENDIENTE)**: el fixture n=9 es **smoke/regression test, NO caracterización de seguridad** (no estima recall/especificidad reales; sin EN, sin respuestas largas, sin contradicciones sutiles). No usarlo para sostener que el gate está "listo".
- **#8 (decisión)**: el scorer siempre `return 0` → consistente con "diagnóstico, no gate" (RULER_DESIGN §0), pero el rol debe ser EXPLÍCITO si alguna vez desbloquea algo.

ROI de los reviews: sano (bugs + over-claims reales, no ritual). El cross-model demostró su valor distinto del sub-agente (catches que el mismo-modelo, que comparte mi marco, no vio).

**Trigger**: al escalar el scorer a más golds (Fase 1) o al fiarse de un veredicto como gate firme.

## 36. Cross-model adversarial reviewer ciego al repo → agéntico/grounded (✅ CERRADO s88 — pedido de Alberto)

**CERRADO (s88, 1 jul 2026):** `adversarial_review.py` corre ahora el loop AGÉNTICO con tools READ-ONLY
(`read_file`/`grep_repo`/`list_dir`) sandboxeadas al repo — deny `.env*`/`.git`/el log de tally, cap 30
tool-calls, `--no-tools` como escape. El invariante de abajo se PRESERVA: el cross-model ve el artefacto
por su propia lente + lee el repo él mismo + su salida se lee CRUDA (NO anidado en el sub-agente).
Smoke: cazó 2 claims falsas plantadas con ancla `fichero:línea` exacta (14 tool-calls). Paridad de
información con el sub-agente (que desde s88 corre pin `fable`). Texto original ↓ como histórico.

`scripts/adversarial_review.py` (revisor cross-model GPT-5.5, Protocolo 3) es una llamada single-shot CIEGA al repo: solo ve los ficheros que se le pegan a mano → medio-adivina sobre código que no ve. Mejora ideal: que GPT-5.5 lea el código él mismo (agéntico, tool-use) y su salida se lea en crudo → grounding + independencia conceptual sin filtro Claude.

**DECISIÓN (s32): DIFERIDO, no construir ahora.** Pregunta cero: (a) la orquestación manual funciona (cazó 4 hallazgos reales en s32; yo verifico sus claims contra código); (b) el revisor dispara POCO (chunky, por build/commit), no es el caballo de batalla; (c) el workhorse cross-model de Fase 1 es OTRO tool — `cross_verify_image.py` (lee la fuente, ≥1 por gold), ya construido; (d) tool-use agéntico OpenAI es un mini-proyecto que competiría con Fase 1. Prior: la infra especulativa "para luego" tiende a no usarse o salir distinta (validator s13, apparatus §9, hooks semánticos, force_vision YAGNI).

**NO anidar dentro del sub-agente Claude**: reintroduce el filtro mismo-modelo (Claude cura el input + interpreta el output) → erosiona la independencia, que es el único activo del cross-model. **Invariante a preservar**: el cross-model ve el ARTEFACTO por lente no-Claude + su salida se lee CRUDA (input = artefacto, no los hallazgos del sub-agente → le invitan a anclarse).

**Trigger para construir**: cuando ensamblar el contexto a mano sea un cuello MEDIDO, o cuando la ceguera cause un review malo/falsa-confianza demostrable.
**Mejora barata intermedia — HECHA (1 jun 2026):** flag `--diff` en `adversarial_review.py` auto-incluye `git diff HEAD` como contexto (mitiga el sesgo de SELECCIÓN de qué pegarle al revisor). Lo que sigue DIFERIDO es solo el salto **agéntico** (que GPT lea el repo él mismo con tool-use). Misma tanda: M1 briefing único (`scripts/adversarial_briefing.md`, cierra la divergencia spec↔script) + M3 log de tally (`evals/adversarial_review_log.jsonl`) + M4 formato de salida anclado — ver `docs/ADVERSARIAL_REVIEWER.md`.

## 37. Calibración del scorer como árbitro END-TO-END — fiable para categórico, no deltas finos (sesión 37)

El primer run del árbitro end-to-end (`atomic_scorer.py --llm` sobre los 19, s37; `DECISIONS.md` DEC-006: 8 FALLO / 10 PARCIAL / 1 REVISAR / 0 PASS) reveló que el scorer es fiable para señal **CATEGÓRICA** (over-admit, alucinación) pero **aún no para deltas finos**. Calibrado en parte; pendiente el resto:

- **(ARREGLADO s37) Falso-positivo del eje conducta** — `detect_conducta` marcaba "admite" en cuanto veía una cláusula no-info en los primeros 300 chars, aunque la respuesta SÍ respondiera (hp015 era respuesta CORRECTA marcada FALLO; hp001/14 parciales con hedge). Fix: discriminador `hedged_admit` (admite-fraseo + p>0 hechos core ENTREGADOS = respuesta parcial, no admit real; solo p≈0 = FALLO-admite). Conserva los over-admit reales (hp017/19, p=0). Dual-review SÓLIDO (log 13-14). **Gap residual**: `p>0` es umbral débil (un hecho incidental podría rebajar un admit real a PARCIAL) — mitigado (nunca da PASS; completitud gobierna el verdict a p≥1 igualmente); endurecer si muerde.
- **(✅ RESUELTO s42, `DECISIONS.md` DEC-015) Eje factual NO-DETERMINISTA** — la contradicción cross-model (GPT-5.5) varía run-a-run: en s37, entre dos corridas idénticas, hp008 pasó de "alucinación 1" a "completitud 0/4"; hp011 1→2; hp013 2→1. Para un árbitro que compare levers esto es RUIDO → necesita estrategia de determinismo (temp=0 + múltiples corridas/votación, o caracterizar la varianza). Compañero del no-determinismo del reranker (DEC-005). **ELEVADO a PRERREQUISITO de s42 (`DECISIONS.md` DEC-013)**: el dúo lo identificó como el prerrequisito real de CUALQUIER lever — el re-baseline "7 FALLO" (s41) es un draw de una variable ruidosa; sin estabilizarlo ningún delta es legible. **s42 arranca aquí.** **Método v2 (s42, tras el dúo — `DECISIONS.md` DEC-014, `adversarial_review_log` #31; NO el "temp=0 + votación" esbozado en DEC-013):** (1) **testear temp/seed empíricamente** (no inferir; `seed` probablemente inerte en reasoning-model sin sampling); (2) **endurecer `response_format`** en las 3 llamadas cross-model (`factual_check`/`undue_inference_check`/`prose_complete_check`) — mata el path parse/red-error→REVISAR (`atomic_scorer.py:327-330`) en el ORIGEN, más estructural que votar; (3) **caracterización screen-then-focus** (K=5/19 → K alto sobre el subconjunto inestable; flips-a-REVISAR-por-error contados APARTE de los cruces de conteo 0↔1); (4) **agregación = decisión de SEGURIDAD a priori** (el eje es false-negative-biased, `:122`: votar por mayoría LAVA una contradicción real rara = washout) → salida honesta = **veredicto + flag de estabilidad + spot-check humano**, no voto silencioso; (5) **separar diagnose/confirm** + artefactos auditables. Sharpening verificado: el veredicto es robusto al CONTEO salvo el filo 0↔1 (`if contradictions: FALLO`, `:323`) → la métrica es estabilidad-de-VEREDICTO, no varianza-de-conteo. **RESUELTO (s42):** temp/seed MUERTOS (gpt-5.5 rechaza `temperature=0`, `seed` inerte — no hay knob, testeado en `scripts/probe_gpt55_determinism.py`); **response_format** cableado en las 3 llamadas → 0 error→REVISAR; **mayoría+flag** (`scripts/characterize_factual_variance.py`) mata el ruido de sampling; la cláusula (d) del contrato se intentó y se REVIRTIÓ (dúo 2×, scope creep + hueco echo-and-deny). Baseline legible: **7 FALLO estables / 18-22 estables** (`evals/factual_variance_baseline.json`). El paso (4)/(5) del método (agregación + baseline) = HECHO; ver DEC-015.
- **(PENDIENTE) Completitud-prosa deflacta** (es `#35.1`): muchos hechos de prosa marcados ausentes a <80% overlap que el bot parafraseó bien (hp003 "rojo y negro" 67%, hp007 "cada 3 meses" 67%) → los PARCIAL son un **SUELO**, no el techo real del bot. Hasta tener completitud-prosa por LLM (#35.1), el número subestima al bot.
- **(PENDIENTE) Invariante de esquema answer-con-conflicto** — el gate delega el surfaceo de ambas variantes a COMPLETITUD; eso EXIGE que el gold codifique AMBAS ramas como hechos core (hp012 sí: 396 ES / 792 US). Falta un check en `gold_store.validate_entry` que lo garantice (cross-model, log 13).
- **(RESUELTO s41, `DECISIONS.md` DEC-012) Check de "inferencia indebida" para refuse-inference** — el **eje NO-FABRICACIÓN** (`undue_inference_check`, cross-model GPT-5.5, gated `--llm`, conservador) caza que el bot AFIRME un hecho `ausente-probado` (compatibilidad/valor/recomendación/inferencia); refuse-inference YA entra en `ANSWER_LIKE`. C1: `score_gold` ramifica por estado-del-hecho. **Validación sobre golds de conducta reales (n>0) pendiente del smoke de s42** (DEC-013); hoy ejercido solo en hp006 (n=1, con 1 FP por hecho mal formulado).

**Trigger ACTIVO**: el scorer YA se usa como árbitro end-to-end (DEC-006). Estos refinamientos condicionan cuándo sus deltas son fiables para DECIDIR un lever (vs solo señal categórica).

---

## 38. Retirar el pipeline de ingesta VIEJO (`src/ingestion/`) — ✅ RESUELTO (s43, PR #32: 24 ficheros v1 fuera; módulos compartidos conservados)

**Estado actual** (verificado s38): producción sirve `chunks_v2` (Voyage-1024, vía `CHUNKS_TABLE=chunks_v2`), construido por el pipeline NUEVO `src/reingest/`. El pipeline VIEJO `src/ingestion/` (construyó la tabla `chunks` vieja, OpenAI-1536, **167.788 filas, NO servida**) sigue en el repo y **mezcla código muerto con infra viva**:
- **Infra COMPARTIDA / viva — NO tocar**: `ingestion/embedder.py` (lo importa el retriever VIVO `retriever.py:14`, enruta a Voyage), `ingestion/supabase_client.py` (lo usan `reingest/{pipeline,index,dedup_pass}` + ~15 scripts).
- **Específico del pipeline VIEJO — candidato a retirar**: `ingest.py`, `chunker.py`, `language_filter.py`, `translator.py` (el PLAN ya dijo "se retira"), `table_extractor.py`, `image_extractor.py`, `vision_describer.py`, `pdf_parser.py` (PyMuPDF; el nuevo usa LlamaParse vía `reingest/extract.py`), `document_registry.py` (verificar). Invocados SOLO por `scripts/{re_ingest,run_ingestion,dry_run_morley,dry_run_parse,vision_rescue_zerochunks}.py` + tests `{test_language_filter, test_override_mappings}`. **El bot VIVO no toca nada de esto** (verificado: `telegram_bot`→RAG→`retriever` solo importa `ingestion/embedder`).

**Problema**:
1. **Trap real**: `scripts/re_ingest.py` y `run_ingestion.py` escriben en la tabla `chunks` VIEJA, que prod ya no sirve → "añadir un manual" por la vía vieja es un **no-op silencioso para producción**. El alta debe ir por `python -m src.reingest.pipeline`.
2. **Duplicación de detectores de idioma** (origen de la pregunta de s38): `ingestion/language_filter.py` (heurístico, viejo) vs `reingest/language.py` (`lingua`, etiqueta `chunks_v2`). El `_filter_by_language` de retrieval (s38, #24) LEE la etiqueta del nuevo y se queda; el viejo es el redundante.
3. El nombre `src/ingestion/` sugiere que es el pipeline activo cuando está muerto → confusión de mantenimiento.

**Trigger para implementar**: antes de la ingesta masiva post-M&A / escalado a 30+ fabricantes (que nadie use la vía vieja por error), O la próxima vez que se toque el path de ingesta / se añada un fabricante, O antes de dropear la tabla `chunks` vieja.

**Solución propuesta** (quirúrgica, NO `rm -rf src/ingestion/`):
1. Verificar por-módulo que nada vivo importa cada candidato (el barrido de s38 cubrió los principales; confirmar `revision_parser` [testeado, lo usa la gestión documental], `pdf_parser`, `document_registry` antes de borrar).
2. Mover la infra compartida (`embedder`, `supabase_client`, lo que quede) a `src/common/` para que el nombre no engañe.
3. Borrar módulos viejos + sus scripts + sus tests.
4. **NO** dropear la tabla `chunks` vieja: es el rollback del SWAP (reversible con `CHUNKS_TABLE=chunks`). Se retira el CÓDIGO, no la tabla.
5. Actualizar el workflow "nuevo fabricante" (memoria `feedback_approach`) → apuntar a `src.reingest.pipeline`.

**Coste estimado**: ~3-4h (medio). Riesgo bajo si se verifica por-módulo (el bot vivo no depende del pipeline viejo, verificado s38).

---

## 39. Frontera compuesta del matcher de anchors — separador de millar/decimal español (sesión 46)

**Estado actual** (s46, DEC-019/F0#2): `strict_match.anchor_present` (canónica, usada por el scorer atómico y el gate de retrieval) usa frontera de DÍGITO (`\d`) para anchors numéricos. NO bloquea el separador de millar/decimal español → `"792"` casa dentro de `"13.792"` y `"159"` dentro de `"2.159"` (falso positivo: el anchor se cuenta presente dentro de un número MAYOR distinto).

**Problema**: en el gate (`audit_retrieval_funnel`) un hecho puede clasificarse SÍNTESIS/RERANK-MISS por un anchor que en realidad no está; en el scorer (`atomic_scorer`) un hecho puede contarse completo por el mismo FP. **Acotado**: el gate exige anchors FUERTES (≥2 anchors / código de modelo / ≥3 dígitos), que diluyen el FP de millar; el caso real es estrecho (número de 4+ díg con punto cuyos últimos 2-3 = el anchor).

**Por qué se pospuso** (verificado en el dúo Protocolo 3, s46): la "solución obvia" `[\d.,]` (la frontera de `locate_fact._value_on_page`) **empeora** el balance — bloquea FN COMUNES: `"295"` en `"295, 300"` (coma de lista) y en `"295."` (punto de fin de frase). El scorer usó `\d` por eso. Cambiar la frontera toca el scoring de golds → no es gratis.

**Trigger para implementar**:
- Un `--dump` del gate (F1) revela un hecho mal clasificado rastreable a un FP de millar/decimal, O
- Un gold falla/aprueba el scoring por el mismo FP (spot-check humano), O
- Se vuelve a tocar `anchor_present` por otra razón.

**Solución propuesta**: frontera COMPUESTA que distingue puntuación-entre-dígitos (millar/decimal) de puntuación-de-prosa (lista/frase): bloquear dígito adyacente SIEMPRE + añadir `(?<!\d[.,])` y `(?![.,]\d)` (bloquea solo cuando hay dígito al otro lado de la puntuación). Resuelve FP-millar Y FN-lista. Requiere re-baseline del scorer de golds (cambia `atomic_scorer`) + A/B; la política actual está congelada en `tests/test_strict_match.py::test_anchor_present_politica_congelada_s46`.

**Coste estimado**: ~1-2h + re-baseline del scorer (riesgo bajo, cubierto por tests).

---

## 40. recall@k como gate pre-merge (baseline + `--gate`) — DIFERIDO a F2/F3 (sesión 46)

**Estado actual** (s46, DEC-019/F0#6): la métrica de recall@k determinista YA existe
(`scripts/retrieval_eval.py`: recall por-fact y por-pregunta, matcher estricto canónico,
diagnóstico de gap raíz). Lo que FALTA para que sea un "gate": baseline versionado + modo
`--gate` (compara vs baseline, exit≠0 si regresa) + config estampada en el output (como F0#1).

**Por qué se difirió** (s46): (1) el CI es OFFLINE (`.github/workflows/ci.yml`: pytest +
check_deps, sin secrets ni red) → no puede correr recall@k real (necesita Supabase + Voyage)
sin romper el CI rápido/sin-secrets; un gate de recall real es pre-merge con red, no en cada
PR. (2) Esta sesión NO toca retrieval (F0=higiene, F1=gate-audit, prior=F3) → un gate sin uso
inmediato es aparato (pregunta cero). El cimiento (la métrica) existe; el gate se cablea al
primer uso real.

**Trigger para implementar**: antes de mergear un cambio que toque RETRIEVAL —reranker Voyage
/ contextual-retrieval (F2), externalización de `CATEGORY_TERMS` si altera valores, o
escala/ingesta (F3)—. Ahí: congelar baseline con la config de prod (HyDE-off, retrieval
crudo@50 SIN reranker = determinista; el reranker LLM es el ruido a separar) + añadir `--gate`.

**Solución propuesta**: `retrieval_eval.py --gate` lee `evals/retrieval_baseline.yaml` (recall
por-fact/pregunta + bloque meta de config), compara, exit≠0 si regresa > margen. Corrida
pre-merge (con red); opcional job CI separado con secrets (NO recomendado: rompe el CI offline).

**Coste estimado**: ~1h (el comando ya existe; falta baseline + comparador + estampado).

## 41. Eje factual del scorer: distinguir "no en los fragmentos recuperados" (retrieval-local) de "el manual no lo describe" (manual-global) (sesión 47)

**Estado actual** (s47, DEC-021 §D): el eje FACTUAL del scorer (`atomic_scorer.py:104`,
contradicción-only) trata como "no-contradicción" que el bot admita carecer de un dato. Pero el
contrato NO separa dos casos materialmente distintos: (a) "no está en **los fragmentos
recuperados**" = afirmación VERDADERA sobre el retrieval (honesto = incompletitud, eje
completitud); (b) "**el manual** no lo describe" cuando SÍ lo describe = afirmación FALSA sobre la
fuente (más cerca de fabricación). Hoy ambas pasan como incompletitud. Destapado por el K-run del
juez (`scripts/judge_kruns.py`): cat007/hp010 eran del tipo (a), honesto → GPT acertó al no
marcarlas, Claude las sobre-marcaba.

**Por qué no se arregló ahora**: no bloquea — los casos del K-run eran tipo (a), y el eje
completitud + el juez holístico ya los cazan como PARCIAL. Es un afinamiento de precisión del eje,
no un fallo activo (pregunta cero).

**Trigger para implementar**: si un audit futuro encuentra el caso (b) —el bot afirmando
falsamente sobre el MANUAL (no sobre los fragmentos recuperados)— sin que ningún eje lo marque.
Entonces: añadir la distinción retrieval-local vs manual-global al prompt del eje factual (o al
no-fabricación `:160`).

**Relacionado**: DEC-021 §D (dual-judge DIFERIDO — el juez Claude sería over-strict por este mismo
contrato; revisar SI GPT-5.5 muestra un hueco de recall), `atomic_scorer.py:104`.

## 42. ✅ CERRADO (s57, DEC-037) — Lectores-directos de `gold_answers_v1.yaml` que NO pasan por la puerta — el embargo del held-out no los cubre (sesión 49)

**Resolución (s57)**: el trigger ("cuando existan golds held-out reales") llegó al poblar el held-out.
Fix de raíz: `gold_store.exclude_heldout()` público + filtro en los 3 lectores (`audit_retrieval_funnel.py`
— el dump por qid embargado falla con mensaje explícito —, `retrieval_eval.py`, `validate_s29_burial.py`)
+ test (`test_gold_store.py`). Bite F2 del dúo s57: el gate s58 usa exactamente estas herramientas; sin el
fix, su default habría expuesto el held-out al diagnóstico de retrieval.

**Estado previo** (s49, DEC-023): el embargo del held-out vive en `gold_store.verified(include_heldout=False)`
(cubre los 4 consumidores del juez: `atomic_scorer:408`, `judge_kruns:82`, `judge_disagreement:99`,
`characterize_factual_variance:83`) + replicado en `test_bot_vs_gold.py` (lee el YAML directo). PERO 3
herramientas de DIAGNÓSTICO de retrieval leen el YAML directo sin filtrar `split`:
`audit_retrieval_funnel.py:62`, `retrieval_eval.py:46`, `validate_s29_burial.py:47` (este último = one-off
muerto de s29). Hoy es no-op (0 held-out), pero al autorar held-out de verdad quedarían expuestos.

**Por qué no se arregló ahora** (pregunta cero): son herramientas EXPLORATORIAS de diagnóstico, NO el
camino que DECIDE un lever (ese es el juez + el harness, ya cubiertos). Migrarlas todas a la puerta =
over-scope del backbone. El embargo sobre ellas es disciplina (no correr diagnóstico sobre held-out)
hasta el trigger.

**Trigger para implementar**: cuando existan golds held-out reales Y se quiera diagnóstico de retrieval
sobre el set; o al construir el run-manifest (freeze-contract, DEC-021 §F) que centralizaría la selección
de set. Fix de raíz: que todo consumidor del ruler pase por `gold_store.dev()/verified()/heldout()` en
vez de abrir el YAML directo.

**Relacionado**: DEC-023 (backbone Track B + embargo en la puerta), `gold_store.py`
(`verified`/`dev`/`heldout`), DEC-021 §F (run-manifest).

## 43. ✅ COMPLETO (capa A s63/DEC-044 · capa B s65/DEC-046) — Retrieval: los manuales de SERIE quedan invisibles a los productos hermanos por el filtro de modelo (sesión 55)

**Resolución capa B (s65, DEC-046)**: backfill de identidad de los lotes s55/s58 — 103 filas
nuevas en `documents` + 2.040 chunks enlazados (entran al lifecycle y citan revisión); 86
manufacturer corregidos por evidencia doc↔chunks (excepción MAD565: los chunks estaban mal);
80 revisiones-basura de parser → NULL; 165 filas `active` sin contenido re-clasificadas (90
retired + 74 needs_review = cola de re-ingesta). Residual declarado: 25 chunks / 8 sources del
canal "Otros" sin marca demostrable. **⚠️ El ESCRITOR del hueco sigue vivo**: el flujo de
ingesta (`src/reingest/index.py:resolve_document_id`) casa pero NO crea filas y NO prefiere
filas active al casar (F2 s65: re-ingestar un doc retired colgaría chunks de una fila
inactiva = invisibles) — el contrato de identidad EN ingesta es prerrequisito de la ingesta
grande (PLAN punto 2). B4/B5 (language/revision_date/family masivos) diferidos a ese contrato.

**Problema** (verificado en código, s55): el `product_model` se asigna a **nivel DOCUMENTO por filename**
(`metadata.py:apply_metadata` copia `meta.product_model` a TODOS los chunks; `_detect_model` sobre
`CAD-250_Manual-Configuracion-MC-380…` → `CAD-250` para el manual entero). Luego `_filter_to_query_models`
(`retriever.py:1235`, hard-drop con fail-open<3) tira los chunks cuyo `product_model` no contiene el modelo
de la query (substring normalizado). Consecuencia: una query de **CAD-201** (config/programación) NO
recupera el manual de configuración de la serie (etiquetado `CAD-250`; "cad201"⊄"cad250") aunque el dato
EXISTA en el corpus. Aplica a toda serie con manual compartido (Detnov serie Vesta CAD-171/201/250; Kidde
serie 2X-A; NC series; etc.).

**El matiz** (tensión precisión↔recall): ese filtro NACIÓ para lo OPUESTO (#11e/hp003: que un manual
CAD-250 no contamine una query de CAD-150). El modelo de datos no distingue "manual DE la CAD-250" de
"manual de la SERIE que aplica a {171,201,250}". Lo destapó Alberto al añadir CAD-201 (DEC-032).

**AMPLIACIÓN s61 → CORREGIDA POR EL AUDIT s62 (DEC-042+CORRECCIÓN, DEC-043):** la lectura del
gate s61 ("near-duplicados monopolizan el top-5") quedó REFUTADA midiendo: los 3 manuales
AM-8200 comparten J_doc 0.001-0.032 (no hay duplicación textual). El mecanismo REAL de cat012 es
ESTE item (#43) en su forma original: la query "AM-8200" deja pasar por SUBSTRING a los chunks
de los productos HERMANOS (AM-8200G/N) y el cross-encoder llena el top-5 con sus secciones
conceptualmente equivalentes (cada central tiene SU fórmula §11), expulsando la tabla del
producto correcto. cat009 (HLSI-MN-025 vs -I v05) resultó ser par ES/EN + revisión EN — se
CONSERVA (B3). El near-dup textual real del corpus: 1 caso (MAD-472 V2, toca cat024).
**→ CICLO A en ejecución (DEC-043, branch de Alberto): registry `series` curado-por-evidencia
en `config/manufacturers/*.yaml` (seam DEC-035, cero DDL) + `_filter_to_query_models` de 3
niveles (sin entrada de registry → comportamiento actual; con entrada → mismo-producto o
doc-de-serie; hermanos NO pasan). Diseño v1: `evals/_s62_seriesA_design.md`; dúo s63.**
⚠️ vigente: sin latest-wins naive (hp011/ES↔US viven de ambas variantes de mercado).

**✅ CAPA A CERRADA — s63 (DEC-044, PR #70, SHIPPED a prod):** registry de series
(`src/rag/series_registry.py` + clave `series:` en los yaml del seam s55) + filtro de 3 niveles
(substring histórico como base; vetos de hermanos + aperturas de shared_docs DECLARADOS;
fail-open escalonado) + diversify corregido (fetch dirigido de shared — sin él, d2 seguía
cerrado: el doc de serie no llega por recall vectorial). Medido con esquema pre-registrado:
gate G1-G8 GO → A/B K=5 con pairing **Δ_net=+2** (cat012 PARCIAL→PASS · cat018 FALLO→PASS ·
0 regresiones) → held-out corrida única DÉBIL-aceptada (ho008 modal igual con vista más
correcta). Población: AM-8200{base,G,N} sin shared · Vesta{171,201,250} con MC-380 rev-c +
MS-416-2026. Ampliar series = añadir yaml con `evidence:` (la validación dura vive en
`tests/test_series_registry.py`, incl. resolución contra corpus). **Sigue ABIERTO de este
item: la capa B** (metadata de lotes viejos — ciclo de higiene propio, PLAN punto 2);
el lifecycle de docs sustituidos pasó a **#46**.

**Por qué no se arregló ahora** (pregunta cero): el corpus CAD **no está ingestado** (ingesta diferida tras
el gate RULER) → gap FUTURO, hoy no hay chunks que recuperar. Y es un cambio de RETRIEVAL → debe MEDIRSE en
el eval, no a ciegas (DEC-019).

**Fix candidato (estructural, eval-driven)**: modelar `series`/`applies_to` (la serie ya se conoce del
scraping del corpus — p.ej. `_download_manifest.json` lleva `series`) y que `_filter_to_query_models`
matchee por **serie-O-modelo**. Así el manual de serie es alcanzable por cualquier hermano SIN reabrir la
contaminación cross-producto. Descartado: relajar el filtro a boost-blando (reabre #11e/#11f); etiquetar
por-chunk según menciones de contenido (ruidoso y frágil).

**Trigger para implementar**: al INGESTAR un producto cuyo manual de config/serie está etiquetado con otro
hermano; o cuando la sesión del eval retome retrieval. Medir con un gold "config/programación CAD-201" en
el RULER (la familia CAD ya está cubierta: cat013 CAD-150, cat019 CAD-250) + A/B del fix vs el filtro actual.

**Relacionado**: `retriever.py:_filter_to_query_models` (#11e/#11f, hp003), `metadata.py:apply_metadata`,
DEC-032 (lote CAD-201 que lo destapó), DEC-019 (eval-driven), gate RULER + Protocolo 3 (ingesta diferida).


## 44. Contrato roto de `chunks_v2.category` — columna sin taxonomía canónica; consumidores muertos inventariados (s59, DEC-040)

**Qué pasó**: la tabla vieja `chunks` tenía la taxonomía canónica EN-54 ("Centrales de incendios" 51.900,
"Detectores de aspiración" 28.335…) y el código del retriever/bot se escribió contra ELLA. La re-ingesta a
`chunks_v2` pobló `category` con la clasificación del INVENTARIO de manuales ('Detección analógica',
'PA_VA Evacuación por voz', 'ES'/'EN_unico'/'PT', 'DESCARTADO', 'MIXED'…) y los lotes s55 ni eso (NULL).
Resultado medido (s59): **0 filas canónicas** — 58% NULL, 25% 'ES' — y todo filtro `category=eq.<canónica>`
devuelve 0 SIEMPRE. El SWAP s44 cambió el contrato semántico de la columna en silencio; los fallbacks
(broad-5 + canales léxicos) taparon el síntoma ~15 sesiones.

**Lo que YA se arregló (lever s59, DEC-040)**: el retrieval ya NO filtra por category (canal vectorial
wide + content_search sin el parámetro + search_tasks muertas eliminadas). La DETECCIÓN
(CATEGORY_TERMS/_CATEGORY_PHRASES) sigue exportada para log/conversación.

**Inventario de consumidores AÚN rotos/degradados (el ESCRITOR primero — sigue sembrando)**:
- **`src/reingest/metadata.py:247`** (`category=_detect_category(source_path)`): el ESCRITOR del bug —
  puebla category con la clasificación del inventario. Toda ingesta futura (Aritech/Ziton/GST post-ciclo)
  siembra más basura hasta que se re-defina el contrato de la columna.
- `get_category_models` → `available_models` (telegram_bot:459 → generator:449): con categoría canónica
  devuelve [] → el path ask_clarification NUNCA ofrece modelos disponibles (conversación degradada).
- `get_all_models_by_category` → `_handle_catalog` (telegram_bot:354): el catálogo agrupa por la
  pseudo-categoría del inventario.
- `_diversify_by_manufacturer` (Step 5b, no-model): gatea/cuenta con `chunks[0].category` (basura) y la
  suplementaria filtra el RPC por ella → subconjunto arbitrario. **DIFERIDO a propósito en s59** (consenso
  dúo ×2: tocarlo = mecanismo reactivado nunca medido; hoy con NULL mayoritario casi nunca dispara).

**Fix candidato (estructural, eval-driven)**: decidir el contrato de la columna — (i) re-poblar con
taxonomía canónica a nivel DOCUMENTO (mapeo doc→categoría; ~1.012 docs; semi-automático por
product_model/catálogo) y reintroducir categoría como **BOOST data-driven** (NUNCA filtro duro: la
respuesta puede vivir en doc de otra categoría — hp008 compatibilidad detector↔central); o (ii) retirar la
columna y sus consumidores. Cualquier opción se mide en el RULER (DEC-019).

**Trigger**: antes de la PRÓXIMA ingesta (el escritor sembraría más basura) o al retomar la conversación
dinámica (available_models). **Relacionado**: DEC-040, `evals/s59_recall_diagnosis.yaml` (verification),
`evals/_s59_lever_design_FINAL.md` §6, TECH_DEBT #43 (identidad de variantes, mismo espíritu data-driven).

## 45. Contrato roto de `chunks_v2.has_diagram`/`diagram_url` — el canal de diagramas está MUERTO en v2 (s60, gate-D)

**Actualización S190 (17-jul-2026): diagnóstico revalidado y solución redefinida.** La tabla
activa tiene 25.090/25.090 filas con `has_diagram=true` y 0 con `diagram_url`; por tanto la bandera
es página-con-alguna-imagen, no diagrama técnico útil. El cruce live/GET-only con la tabla legacy
encuentra 5.096 páginas exactas y no ambiguas por `document_id + page_number + source_file`, que
alcanzan 7.685 chunks activos; 30/30 URLs muestreadas responden HTTP 200. Sin embargo, una muestra
visual diagnóstica contiene 2 esquemas útiles y 3 portadas/marketing: copiar URLs a `chunks_v2`
queda explícitamente **NO-GO**. El fix vigente es un registro `document_visual_assets` ligado a
revisión+página+hash, independiente del chunker, con rol/utilidad y gate ciego ≥95% precision;
véanse `evals/s190_visual_asset_contract_design_v1.md` y
`evals/s190_visual_asset_contract_gate_v1.yaml`.

**Actualización S191:** Luna clasificó 60/60 activos sin outputs inválidos por $0,04029, pero el
trigger preregistrado exigía 10–30 positivos y produjo 44. Ese límite superior no estaba alineado
con una cohorte que contenía 48 páginas de intención técnica; por ello el instrumento cierra como
`CLOSED_NO_GO_TRIGGER_OUT_OF_RANGE` y la calidad del clasificador queda `NOT_MEASURED`, no como
falso positivo demostrado. No se elevó el umbral, el razonamiento ni se llamó a revisores frontera.
Trigger siguiente: una cohorte nueva y balanceada con controles negativos y gold independiente;
no DB write, backfill ni producción antes de medir precisión ≥95%.

**Qué pasó (medido s60, 11-jun)**: la tabla vieja `chunks` tiene **44.035 filas** con
`has_diagram=true AND diagram_url NOT NULL`; **`chunks_v2` tiene 0 de 25.090**. La re-ingesta
LlamaParse (s44) no pobló estas columnas → otro contrato de columna roto en silencio por el SWAP,
hermano exacto del #44 (category). Descubierto al intentar el smoke de diagramas del gate-D s60
(los 12 pools congelados tenían 0 diagram-chunks; el count de corpus lo confirmó).

**Consumidores muertos/degradados desde s44 (verificar al fixear)**:
- `diagram_search` (`retriever.py:411`, stamp 0.82, WIRING_INTENT): devuelve 0 SIEMPRE en v2.
- El tag `[DIAGRAMA DISPONIBLE]` del reranker LLM (`reranker.py:53-54`) y su instrucción WIRING:
  nunca disparan.
- `DIAGRAMAS_RELEVANTES` del generador: el bot NO sirve diagramas a técnicos de conexionado —
  degradación de PRODUCTO en silencio, no solo de eval. (La "guarda load-bearing" de DEC-016d
  protege un canal que ya no existe en v2.)

**Matiz a investigar en el fix**: 44.035/~52k en la vieja (~85%) no cuadra con la "diagram density
~3-5%" del docstring de `diagram_search` — la semántica de `has_diagram` en la vieja pudo ser
sobre-inclusiva (página-con-imagen vs diagrama-útil). Definir el contrato ANTES de re-poblar
(¿imagen extraída por página? ¿flow/wiring clasificado? `is_flow_diagram` existe en el schema v2).

**Fix candidato**: re-poblar desde los artefactos LlamaParse (las imágenes extraídas existen en
`extracted_images/`/storage — verificar) con clasificación útil, o retirar el canal y sus
consumidores. Cualquier opción se mide en el RULER (DEC-019). **Trigger**: al diseñar el lever
s60-redefinido (L-i + cross-encoder) el smoke de diagramas queda MOOT mientras v2 esté a 0 — si
se re-puebla, la guarda funcional de diagramas vuelve a ser obligatoria; y SIEMPRE antes de dar
por bueno cualquier trabajo de "diagramas" en v2. **Dependencia NUEVA (s61, diseño v3 §2.0/§2.3 —
Y4 cross-model)**: el doc que el cross-encoder rerank-2.5 recibe (`_voyage_doc`, header de paridad
Producto|Sección|Tipo) NO incluye el diagram_tag a propósito (canal muerto); si este contrato se
re-puebla y el reranker activo es el CE, el soporte de diagramas para ese path se DISEÑA en el
ciclo del fix (boost post-rerank, metadato en el header, o instrucción — rerank-2.5 es
instruction-following), no se hereda en silencio. **Relacionado**: #44 (patrón contrato-roto-por-SWAP),
DEC-016d (boosts load-bearing), gate-D s60 (`evals/s60_step0_order_sensitivity_voyage.yaml`).


## 46. ✅ Lifecycle post-ciclo-A: 3 docs sustituidos conviviendo (s63, DEC-044 → CERRADO s64, DEC-045)

**Qué era**: el ciclo A dejó identificados, con evidencia, 3 documentos SUSTITUIDOS que convivían
activos con su sucesor en chunks_v2: MAD-472 V1 (→ V2), CAD-250-MC-380-es rev-b (→ rev-c 2026),
CAD-250-MS-416-es 2020 (→ versión 2026 multi-central). Y una claim arrastrada de s63: "el PDF
del MS-416 en el portal fue actualizado in-place; el actual (73 pp) difiere de lo ingestado".

**✅ CERRADO s64 (DEC-045):**
- **(a) EJECUTADO** — contrato de supersesión poblado por PRIMERA vez (3 cadenas:
  status='superseded' + superseded_by_id/supersedes_id) + backfill de identidad de los 2
  sucesores Detnov en `documents` (el pipeline s44/s55 no crea filas; sus 224 chunks enlazados).
  Con guardarraíl pre-registrado: precheck de hechos-gold en sucesores GO + cobertura de
  secciones MS-416 viejo→nuevo 90%≥75% + pools before/after de los 39 dev (C1: 0 docs viejos
  en pools; C3: 36 no-afectados byte-idénticos; cat024 pool 4→7) + smoke C4 del path real
  (cita 'rev c' — los suplementos ahora llevan document_revision). Reporte:
  `evals/s64_lifecycle46_report.yaml`; rollback documentado en el runner.
- **(a+) FIX de re-entrada descubierto y cerrado** — diversify re-fetcheaba docs que el
  lifecycle filter (4b) acababa de excluir (variante lifecycle del patrón F1-r1 s63; ya mordía
  con los 5 needs_review Morley): pre-filtro del universo de missing_sources + cinturón batch
  `_filter_by_document_status` en ambos paths (source_file y manufacturer), contrato
  `include_superseded` respetado. 4 tests nuevos; fixture hermética (F4 r1).
- **(b) SIN MATERIA — claim REFUTADA por verificación** (12-jun): los 4 URLs del portal
  (páginas CAD-171, CAD-250 ES y CAD-201) sirven byte-idéntico lo ingestado (MS-416-2026-b
  sha e1985c3d…; viejo sha 49d0f899…; ídem MC-380); Wayback sin snapshots. El "73 pp difiere
  de lo ingestado" fue un CRUCE DE IDENTIDADES entre las dos ediciones conviviendo (73 pp =
  el -2026-b YA ingestado; el viejo tiene 76). No hay nada que re-ingestar. El contrato de
  supersesión EN INGESTA queda para la primera ingesta real (precedente retroactivo poblado).
- **(c) EJECUTADO** — `corpus_fingerprint()` extendido con dimensión lifecycle
  (documents_status + chunks_excluded_by_lifecycle; era ciego a status: una supersesión en
  ventana de freeze era invisible). Post-s64: 1067 docs {active 1059 · superseded 3 ·
  needs_review 5}, 262 chunks excluidos (220 s64 + 42 Morley). Ventana de freeze CERRADA.

**Residuo (no deuda nueva)**: supersede-traps de `eval_rag.py` (harness legacy) siguen
placeholder — NO se autoran allí (el ruler vivo ya cubre: cat024 manda V2 con V1 anotado
SUPERSEDED + C1 del runner + smoke). Si el ruler quisiera un trap dedicado, ahora HAY materia
(3 cadenas reales) — decisión de autoría futura vía `gold_store`.

**Relacionado**: DEC-045 (cierre), DEC-044(e), audit s62 (capa C), `scripts/s64_lifecycle46.py`
(runner 5 fases con rollback), `scripts/s64_state46.py`, `config/manufacturers/detnov.yaml`
(evidence actualizada).

## 47. `_get_all_known_manufacturers` (diversify Step 5b) lee 200 chunks físicos sin ORDER BY — la lista real es 2 marcas (s65)

**Estado actual (MEDIDO en s65, F9b del dúo)**: la lista que alimenta `_diversify_by_manufacturer`
(`src/rag/retriever.py:1843`) se construye de los primeros ~200 chunks FÍSICOS de la tabla
(sin ORDER BY, con cache de proceso). Medido en los snapshots before/after de s65: devuelve
**['Argus Security', 'Aritech']** — 2 de las 31 marcas del corpus. Consecuencias: (a) el
diversify por manufacturer del path no-model solo "ve" 2 marcas (sus fetches suplementarios
solo rellenan esas); (b) la lista depende del ORDEN FÍSICO del heap de Postgres → un UPDATE
masivo puede REORDENARLA en silencio y cambiar pools de golds genéricos sin tocar sus sources
(dado de instrumento; en s65 no cambió — verificado en el report).

**Por qué no se arregló en s65** (pregunta cero): es código de RUTINA de retrieval (cambiarlo
= lever que debe medirse, DEC-019) y el Step 5b entero está ya DIFERIDO-a-propósito en #44
(gatea con `category` basura; consenso dúo s59 ×2: tocarlo = mecanismo reactivado nunca medido).

**Trigger para implementar**: al resolver #44 (el Step 5b se rediseña entero con el contrato
de category) — la lista debe salir de `documents` (paginado, como el fix s65 de
`get_available_manufacturers`) o de un agregado estable, NUNCA de un scan físico sin orden.
O antes: si un C3-fail de pools en un ciclo futuro se atribuye a este mecanismo (la
explicación pre-declarada quedó escrita en `evals/s65_capab_report.yaml`).

**Relacionado**: #44 (Step 5b diferido), DEC-046e, `s65_capab_report.yaml`
(known_manufacturers_diff), fix s65 de `get_available_manufacturers` (mismo patrón de causa).

---

## 48. `section_path` curado no llega al cliente ni al reranker — señal jerárquica desaprovechada (s72)

**Estado actual (detectado s72, audit de campos para la tirada Lever 2)**: `chunks_v2.section_path`
está POBLADO con breadcrumbs jerárquicos curados y ricos (p.ej. `"AJUSTES > 5.4 AVANZADO"`,
`"6 Puesta en marcha > 6.4.2 Comprobaciones del lazo"`, `"A1.4 Prestaciones"`) y es el feed
PRIMARIO del FTS (peso A, `migrations/006:174` — `coalesce(section_path, section_title)`)
server-side. PERO el retriever NUNCA lo incluye en ningún `select=` de PostgREST (verificado:
**0 referencias a `section_path` en `src/rag/`**) y el reranker usa solo `section_title` en su
header (`src/rag/reranker.py:69-70`). → la señal de identidad jerárquica solo entra vía FTS
server-side; NO llega al cliente para rank ni al LLM del reranker.

**Problema**: el reranker elige el top-5 a ciegas del breadcrumb jerárquico (solo ve el título
de la sección-hoja + `content[:800]`). Una señal curada de alto valor para desambiguar "en qué
parte del manual vive este chunk" se desperdicia.

**Trigger para implementar**: ABIERTO — candidato #1 de una tirada de "señal jerárquica/rank"
(post-Lever 2). Construir tras flag propio y medir como brazo INDEPENDIENTE: es un cambio de
RANK con blast-radius global (toca la entrada del reranker para las 39 de control) y ningún gold
predice flip → medir cobertura granular amplia (s70) + NO-regresión de PASS-control + dúo
cross-model (reranker = zona-de-dolor). NO empaquetar con la tirada de identidad: rompería la
atribución del delta (DEC-019).

**Solución propuesta**: añadir `section_path` al `select=` de los paths de retrieval y al header
de chunk del reranker (LLM y path Voyage CE). Coste ~1h código + medición.

**Relacionado**: hp017 (su gold usa el PARENT `section_path` para el rescate sección-hermana —
mecanismo distinto, Lever 1 de contigüidad/diversify, no la exposición del campo).

---

## 49. Identidad de variantes/familias NO auto-escala a 30+ — la curación es manual+reactiva, y una fracción grande es METADATA-INCONSISTENCY (no config-fixable) (s72)

**Estado actual (scan s72 sobre chunks_v2)**: el seam config (`series:`/`model_aliases`, DEC-043/035)
escala en CÓDIGO (añadir fabricante = añadir YAML) pero la CURACIÓN es manual y REACTIVA (cada familia
se descubre porque un gold/queja la destapa — p.ej. ZXe vía hp009/hp018, DEC-053). Scan del solape-substring
de `product_model` (la condición que dispara base-drags-variant + variant-misses-base + el matching del filtro):
- **Same-brand base→variante: 80+ pares (consulta CAPADA), ~9 fabricantes** — Argus (SG*-IS), Aritech
  (2X-AT-F2-*), Kidde (KE-*), Morley, Notifier (~25 bases: AM-8200, ID50/60, INSPIRE E10/E15, G-100-R,
  SMART 3G, NAS-20…), Pfannenberg, Securiton (ADW535-1), Spectrex (40-40R-SINGLE), Xtralis (VESDA-E,
  FAAST-FLEX). **Declaradas hoy: 3 series (Vesta, AM-8200, e-series) de ~47+ familias.**
- **Cross-brand: 53 pares / 21 cores colisionan** (p.ej. FAAST bajo Morley/Notifier/Xtralis) → el filtro
  substring puede arrastrar la MARCA equivocada.
- **HALLAZGO CLAVE: una fracción grande NO es familia-de-variantes sino METADATA-INCONSISTENCY** — el MISMO
  producto etiquetado de N formas (ID200/ID-200; Pearl/PEARL/Pearl-997-670-005-3; NFS Supra/NFS-Supra/
  NFS-SUPRA; RP1r/RP1R/RP1r-Supra; SECURNET PLUS/SECURNETPLUS) + pm compuestos (AM2020/AFP1010, ID50/60,
  M700KAC + M700KACI, UCIP/UCIP-GPRS). **El config seam NO arregla esto** (no se puede series-declarar una
  inconsistencia de etiqueta) — es la raíz de DATOS (#43 capa B / #18-mfr).

**Problema**: a 30+ fabricantes la curación a mano no llega (cubrimos 3 de ~47+); y el grueso ni siquiera
es config-fixable (es calidad de dato). Además el matching es por substring → las colisiones crecen con el
catálogo (fragilidad del MECANISMO, no solo de la curación).

**Trigger para implementar**: (a) arranque de la INGESTA grande (la push a 30+ mete familias nuevas en
bloque — el escritor debe NORMALIZAR `product_model` + poblar `product_family` AHÍ, no a posteriori); O
(b) ≥2º gold de identidad que caiga FUERA de una serie declarada (la curación reactiva no da abasto); O
(c) queja de técnico por arrastre/colisión de variante.

**Solución propuesta** (en orden de estructura):
1. **Raíz de datos (lo que SÍ escala)**: normalizar `product_model` a forma canónica + poblar
   `product_family` (#21) EN INGESTA → la serie se DERIVA del corpus en vez de curarse a mano, Y desaparece
   la clase metadata-inconsistency. Ligado a #43 capa B (escritor-en-ingesta) + #44/#45.
2. **Detector proactivo (puente semi-auto)**: productizar el scan s72 (solape-substring same/cross-brand +
   tokens-paraguas) → herramienta que PROPONE entradas series/alias para revisión humana y FLAGEA la
   metadata-inconsistency para saneo. Descubrimiento reactivo→proactivo; alimenta (1).
3. **Config a mano (lo actual)**: solo para las familias de más valor que surjan por gold, como tapón hasta (1)/(2).

**Refinamiento s73 (diseño del detector ANOTADO, NO construido — rumbo decidido con Alberto: medir A → Lever 1 primero; build del detector gated al trigger (a)/(b)). Se canoniza como DEC-054 al cierre.** Validado por dúo cross-model GPT-5.5 + workflow adversarial (estado verificado contra código):
- **El detector (sol. 2) usa un LLM content-based** (lee título/propósito del manual), no solo el regex
  genérico de #21 — desambigua pm compuestos (AM2020/AFP1010, ID50/60) y elige el modelo REAL sobre el
  más-frecuente/prefijo que hoy escoge `_detect_model` (`metadata.py:109-118`), que es la raíz de la
  mis-atribución (SDX-751→LOCAL-360). Esta es la mejora real de Alberto sobre el canon — se conserva.
- **Alcance preciso (no sobre-afirmar)**: ataca P3(a) mis-atribución solo **PARCIAL** (aplicabilidad a
  nivel-MANUAL ≠ atribución correcta a nivel-CHUNK: marcar un doc multi-producto entero como {X,Y,Z}
  puede contaminar el pool de cada modelo). Resuelve bien P2 (shared-docs). **NO resuelve P3(b)**
  metadata-inconsistency (conocer el conjunto de modelos ≠ IDs canónicos).
- **Cross-check anti-alucinación OBLIGATORIO**: validar cada modelo derivado contra el catálogo de 587
  modelos catalog-first (`classify_model_manufacturer`/`model_manufacturer`, `retriever.py:156,175`) — NO
  contra el índice (circular: heredaría la contaminación de filename que se quiere sustituir). Árbitro
  real = el manual / muestra humana.
- **Prerequisitos antes de CUALQUIER backfill**: (a) cerrar **F2** del escritor
  (`index.py:resolve_document_id` casa por hash/filename, devuelve None, no prefiere `active` ni crea
  filas) **y replicar la normalización en el writer** — si no, backfill y writer divergen y la re-ingesta
  repite la mis-atribución (chunk colgado de fila inactiva invisible); (b) **auditar P3(b) por-familia**
  ANTES de mecanizar. [s73: F2 ANOTADO como prerequisito, NO cerrado aún — no hay ingesta activa.]
- **Economía (clave, la propuesta "ZXe-ahora + tech-debt resto" la tiene invertida)**: lo barato = correr
  el LLM (~Haiku/doc, ya probado a escala = B7-contextual-retrieval); lo caro/diferible = **VERIFICAR** el
  backfill a ~47+ familias / 1.170 docs. → **NUNCA backfill ciego a 1.170 docs**; verificado solo de
  familias de alto valor que un gold destape. "Done para ZXe" NO entrega valor estructural nuevo (ya
  resuelto a mano, Brazo A/DEC-053) — solo prueba el aparato. Precedente de deuda silenciosa: las 318
  correcciones de product_model de #18-mfr salieron como derivada y nunca se auditaron.
- **Alcance honesto vs el cuello MEDIDO**: %resuelto de los ~16 retrieval-miss (DEC-052) ≈ **0** —
  identidad es ORTOGONAL a la inanición del pool; el detector NO sustituye a Lever 1 (broad-fallback
  capado a 5, `retriever.py:1103`). Probado por el Brazo B NO-OP de s72.
- **Alternativa BARATA para la capa de filtrado** (ni el dúo previo ni el autor la habían puesto
  explícita): mapping modelo→familia en registry/YAML lazy-load (como las series hoy), SIN tocar DDL —
  evita ALTER+INDEX+cambiar RETURNS TABLE de `match_chunks_v2`/`search_chunks_text_v2` (migrations/006).
  Nota: `documents.document_family` YA existe (migrations/001); denormalizar a columna en chunks solo si
  un lever futuro exige exponer la familia al generador.

**Coste estimado**: detector ~3-4h (regex) → +LLM/doc (~Haiku, escala B7) + verificación humana muestreada
NO dimensionada (= el coste dominante real del backfill); raíz de datos = parte del contrato de ingesta
(#44/#45), lift grande gated.

**Medición s75 (audit-first, DEC-057 — `scripts/s75_identity_audit.py`):** Alberto eligió medir antes de construir.
Resultado: **el detector tiene ~0 palanca eval real → DIFERIDO a su gatillo (ingesta-30+); NO se construye como lever.**
- **Palanca eval ≈0** (lo decisivo): de los 17 NO-PASS de retrieval (s71 track2), el detector toca SOLO **cat013** — y
  cat013 es gold de **CONDUCTA** (`refuse-inference` cross-marca, verificado en `gold_answers_v1.yaml`), no de
  retrieval-recall: el detector no lo arregla y podría EMPEORARLO. hp009/hp018 son **config** (e-series, Brazo A), no el
  detector. Confirma que la identidad es ORTOGONAL al cuello medido (Lever 1).
- **Escala = real pero ACOTADA, en PROXIES RUIDOSOS (no pisos medidos)**: pm-compuesto **78 etiquetas** (sobre-cuenta:
  `20/20I`, `DH500AC/DC` son modelos únicos con `/`); mis-atribución **≤114 docs** (crudo 368 CONTAMINADO — el regex y el
  catálogo `model_catalog.json` MISMO heredan códigos de manual `MNDT-xxx` como pseudo-modelos = **la circularidad que
  este #49 / DEC-054 predijo**; el refinado ≤114 sigue con residual `GUIDE-`/SKU); metadata-inconsistency **18 clusters**.
  Concentrado en **3-4 marcas legacy** (Notifier/Morley/Detnov), no corpus-wide.
- **El sizing EXACTO de la mis-atribución requiere lectura de CONTENIDO = el propio detector** (la circularidad). Sin
  freeze-contract del corpus/catálogo, 78/≤114/18 se mueven sin traza. **Dúo Opus+GPT-5.5 (0 FP)** confirmó DIFERIR.
- **Implicación**: el saneo del dato se hace EN el contrato de ingesta (#44/#45/escritor), NO a posteriori como lever;
  el detector se justifica solo como prep de escala al gatillo, no por golds. La curación a mano sigue siendo el tapón.

**Relacionado**: DEC-057 (audit-first → DIFERIR, cifras medidas), DEC-053 (Brazo A = primer caso curado a mano),
DEC-043/#43 capa B (seam + escritor), #21 (product_family), #18-mfr (atribución/etiquetas), #44/#45 (contratos de
ingesta), #47. Scan reproducible: self-join de `chunks_v2` por `lower(regexp_replace(product_model,'[- ]','',''))` con
`LIKE`, o `scripts/s75_identity_audit.py` (pm-compuesto + mis-atribución catalog-first + inconsistencia + cruce eval).

**Medición s76 (DEC-058, PROD-REACH — `scripts/s76_prod_reach.py`):** el gate manufacturer-check del handler
(`telegram_bot.py:292-339`) corta **9/29 NO-PASS ANTES del RAG; 7 cortes ERRÓNEOS** — `lookup_model_manufacturer`
(catálogo de 587) devuelve None para CAD-150/ZXe/40-40 (**DESINCRONIZADO con el corpus**: 103 / 157-207 / 486
chunks resp., verificado con count_rows) y la marca equivocada para RP1R (está en `_NOTIFIER_PATTERNS`, pero el
corpus lo tiene Morley); 2 son OEM-relabel (ADW535/ASD535=Securiton en el corpus). → **el gate-fix #49 sube a
deploy-prep MEDIDO** (defecto latente de prod, sin usuarios aún = no urgente-por-daño). Confirma el mecanismo del
NO-OP de LEVER2_IDENTITY (ZXe cortado antes del RAG). NO cierra bias #40 solo: los OEM/multimarca necesitan el
contrato de identidad (esta capa). **reach ≠ PASS** (arreglar el gate los hace llegar al retrieval; el PASS sigue
dependiendo del retrieval bancado). Corte cross-model: sin contrato de identidad, el gate-fix solo cambia
falsos-rechazos por falsos-aceptados/mis-atribución.

## 50. ELIMINAR `LEVER2_IDENTITY` (+ su YAML por-familia) — sustituido por resolución data-driven (s86)

**Decisión (Alberto, s86):** marcar para eliminación próxima. El flag `LEVER2_IDENTITY` (s72, brazo A:
`resolve_aliases` + `passes_nivel2` en `retriever.py:125/1445`) y su dato (`config/manufacturers/*.yaml`
`model_aliases`/`series`) NO se van a usar como el fix de identidad: es **curación manual por-familia**
(3/11 fabricantes con entrada; solo Morley con `model_aliases`, y esa entrada se hizo PARA hp018 →
validarlo en hp018 es circular). No auto-escala a 30+ (relacionado #49).

**Trigger de eliminación:** cuando la resolución de identidad **data-driven** (consumo del activo DEC-067:
`evals/s83_document_identity_final.jsonl` 2761 productos + índice `s84_identity_index.json`) esté cableada
y medida con el instrumento family-aware. Entonces borrar: el bloque del flag en `retriever.py` (125-126,
el brazo `passes_nivel2` en `_filter_to_query_models`, `LEVER2_PM_RESCUE`), `series_registry.py` si queda
huérfano, y las entradas `model_aliases`/`series` de los YAML. **Medido s86:** ON resuelve 4/4 hp018 pero
regresa hp009/aisladores (tensión clarify-vs-answer family-genérico) → es stopgap de familia-conocida, no BP.
Ref: DEC de cierre s86; el +4 hp018 = cota de "lo que un buen registro lograría", no el fix a shipear.

## 51. Frescura de corpus: auditar revisiones nuevas vs Excel/fabricante + poblar `revision_date` (s86)

**Contexto (s86, verificado en DB):** el superseding-*detection* está SANO y completo — `document_management`
(migración 001) corrió sistemático (1170/1170 con `document_family`); donde había dos versiones en el corpus
(Detnov CAD-250 MC-380/MS-416, 2026-c/b) las cazó y marcó `superseded` + cadena `supersedes_id`; el resto de
los 68 filenames "versionados" son versión-única (`fam_total=1`) → correctamente no-superseded. Total real = 3
superseded / 220 chunks (~1%). NO es un hueco de detección.

**La deuda real = FRESCURA, no detección:** el mecanismo solo supersede lo que está ingestado. Ej: tenemos
"Manual instalacion CAD-250 (MI_372_es_**2024** e)" como único manual de instalación; si Detnov sacó una revisión
2026 del de instalación (además de los de config que sí tenemos), la serviríamos como vigente sin saberlo.

**Trigger:** cuando montemos el registro canónico index-time (workstream de identidad data-driven) O antes de
un demo con técnico real. **Acción:** (a) auditoría de frescura por-fabricante contra `data/Inventario_Manuales.xlsx`
+ webs (¿falta la última revisión?); (b) poblar `revision_date` (hoy 1/1170) desde páginas 1-5 → activa el orden
de las supersede-chains para citar la revisión vigente. **Baja palanca en el eval** (golds píxel-verificados active);
es **producto-calidad** (un técnico no debe recibir un manual obsoleto), NO gate del trabajo de identidad. Ref: cierre s86.

## 52. Canal hyq: family-parity por texto-de-pregunta — 3 límites declarados (s102, dúo r2)

**Contexto:** el ship del canal question-side (tabla `chunks_v2_hyq`, mecánica v2 con
`_hyq_family_rows` — family-parity a nivel fila, patrón 012) pasó su gate 2/2 con atribución.
El dúo r2 (cross-model + sub-agente) dejó 3 límites CONOCIDOS del matcher de familia, ninguno
bloquea la activación (el fallback a-cero-matches acota el daño a "no-peor que cuota global"):

1. **Ventana series/shared-docs**: el filtro (texto de pregunta vs modelos post-resolver) es
   más estricto que la apertura nivel-2 de docs compartidos de `_filter_to_query_models`
   (CAD-201→MC-380): una pregunta que solo nombra el doc de serie se filtra aunque el pipeline
   downstream la habría admitido.
2. **Techo de escalabilidad del top-200 client-side**: la paridad 012 VERDADERA sería el
   family-pattern como parámetro del RPC `match_hyq` (server-side, migración futura). Con 70k
   preguntas la familia rankea ~49-53 (cabe en 200); a 200k+ (contrato 30+ fabricantes) el
   top-200 puede traer CERO filas de familia → fallback silencioso a cuota global condenada.
   Trigger: al duplicar el corpus o si el gate de un fabricante nuevo pierde flips.
3. **Padres pm=unknown sin adjudicar**: la pregunta de familia pasa el filtro pero el padre
   hidratado muere en `_filter_to_query_models` salvo rescate del fail-open <3 o del
   union-protector de identidad (hp018 sobrevivió vía IDENTITY_RESOLVE=on + doc adjudicado).
   Los ~150 docs sin adjudicar quedan fuera → se resuelve con el workstream identidad (DEC-074),
   no con parches al matcher.

Además: el anclaje a producto de las preguntas generadas es CONDICIONAL («cuando aporte»,
prompt s99; QA muestral 15/15 ≈ cota inferior ~80%) — mitigado con el filtro a nivel FILA
(pre-colapso, fix #2 r2), no eliminado. Ref: DEC-099 (pendiente al cierre), gate
`evals/s102_hyq_table_gate.yaml`, tests `tests/test_hyq_channel.py`.

## 53. Transporte del autor de golds: compilación estática probada; generalización real pendiente (s194→s196)

**Estado medido:** el gate fresco S194 se detuvo como `NO_GO_COHORT_CONSTRUCTION` porque
`s194_src_09` entregó una lista de soportes fuera del rango 1–3. No fue un fallo de parseo ni de
población: 13 preguntas elegibles, 50 puntos y equilibrio 7 tabla/6 prosa habrían pasado. La
causa de contrato es concreta: `author_schema()` heredado de S168 declara
`support_unit_ids: {type: array, items: string}`, mientras `validate_author_item()` exige
1–3 IDs únicos. El proveedor cumplió el schema estructurado y falló después en el validator.

**Avance S195 y nuevo estado medido:** Anthropic no soporta `maxItems`/`uniqueItems` en el
dialecto compilado. S195 conservó esas reglas en el contrato canónico y eliminó arrays del
transporte mediante slots acotados. La cohorte fue completamente nueva y excluyó S194, pero la
combinación de enums dinámicos por unidad, `$defs` y cuatro puntos fue rechazada en la primera
inferencia con HTTP 400 `Schema is too complex for compilation`. Hubo 14 token-count preflights,
0 inferencias completadas, Luna 0 y facts 0. Estado `NO_GO_EXECUTION_CONTRACT_REJECTED`.

**Avance S196:** el canary sintético estático compiló y validó en la única inferencia permitida.
El schema rectangular usa 4 puntos × 3 soportes, cero arrays/refs/defs/combinators/enums/consts;
identidad, facets, cardinalidad, pertenencia, unicidad y contigüidad quedan en código determinista.
Haiku 4.5, SDK 0.97.0, 1 preflight + 1 inferencia, `max_retries=0`, coste $0,002583.
Estado `GO_STATIC_TRANSPORT_COMPILED`; facts 0 porque el fixture es sintético.

**Trigger actualizado:** congelar en un tramo S197 separado otra cohorte real fresca que excluya
los 14 documentos de S194 y los 14 de S195. Reusar exactamente el schema estático S196 y el
validador determinista, luego exigir Luna externa sobre todos los ítems. No modificar/reintentar
S194/S195/S196 ni relajar cero inválidos/unsupported. Solo si ese upstream pasa se abre el planner
con 90/80/75 intactos.

**Límite:** corregir el schema elimina una clase de invalidez del instrumento; no aporta evidencia
de que el planificador descompuesto supere recall 90%/precisión 80%/completas 75%, ni mueve facts.
Eso solo lo decide una ejecución fresca posterior. Ref: DEC-103/104/105, `evals/s194_*`,
`evals/s195_*`, `evals/s196_*`.
