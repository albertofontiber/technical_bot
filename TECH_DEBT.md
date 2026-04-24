# Deuda técnica consciente

Lista de mejoras conocidas que hemos **decidido posponer explícitamente**. Cada entrada tiene un *trigger condition*: la señal concreta que indica que ha llegado el momento de implementarla. No son fechas — son condiciones del sistema.

Si alcanzas un trigger, para y refactoriza antes de seguir añadiendo features.

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

## 4. Gestión de revisiones de documentos — ⏳ EN PROGRESO (Phase 1 ✅)

**Estado actual (16 abril 2026)**: **Phase 1 COMPLETADA**. Tabla `documents` creada (866 filas), `chunks.document_id` FK añadida y poblada al 100% (150,695 chunks vinculados). Phase 2 pendiente (revision_parser.py para extraer revisión/fecha de filenames). Phase 3 pendiente (re-hash con SHA-256 real para reemplazar placeholders 'backfill:'). Ver `docs/DOCUMENT_MANAGEMENT.md` para el diseño completo y `migrations/001_document_management.sql` para el schema.

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

**Trigger para implementar**:
- Detectamos **>20 colisiones** de filename-base en un solo scrape (señal de que hay muchas revs/partes mezcladas), O
- Un técnico reporta que el bot dio instrucciones de una versión obsoleta de un manual, O
- Queremos hacer re-scrapes periódicos del mismo fabricante (necesitamos detectar deltas)

**Solución propuesta**:
1. Campo `document_family` en `chunks` = base normalizado (ej: "AM-8100 manual de usuario")
2. Campo `revision` + `revision_date` extraídos del filename (parser heurístico) o del PDF (primeras páginas)
3. Al ingestar, si ya existe una revisión anterior del mismo `document_family`, marcarla como `superseded` (no borrar) y usar la nueva por defecto en retrieval
4. Parte (b) — multi-parte — se detecta porque los `_01/_02/_03` son consecutivos y el tamaño es pequeño: se unen en un único chunk group
5. Herramienta CLI: `scripts/diff_revisions.py prev_rev.pdf new_rev.pdf` — resumen de qué páginas cambiaron, para decidir si es rewrite total o diff

**Coste estimado**: ~4-6h (el parser de revisiones es el 70% del trabajo)

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

## 8. Observability + tabla `query_gaps` (tracking de qué manuales faltan)

**Estado actual (decidido 17 abril 2026)**: Hoy no existe ningún sistema de logging de las interacciones del bot. Se decidió en sesión que el bot debe registrar cada query donde responde *"no tengo este manual"* para construir la cola priorizada de ingesta futura.

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

**Resumen ejecutivo**: implementado y testeado con 2 iteraciones de eval completo. Ambas con resultado **net-neutral o negativo**. Generator.py revertido al estado pre-sesión-13; `src/rag/validator.py` + tests (15) se conservan como dead-code para futura re-exploración.

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

## 16. Separar retrieve top_k del generator top_k — "retrieve wide, generate narrow" (nuevo — 22 abril 2026)

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

## 24. Extracción de tablas pierde marcas visuales (X/✓) — genera alucinación por relleno (hp007, sesión 16)

**Estado actual**: el chunker/parser PDF extrae tablas matriz (ej. Tabla 7-1 del manual VESDA-E VEP-A00: calendario de mantenimiento con 7 tareas × 4 frecuencias) preservando headers y nombres de filas pero perdiendo las marcas visuales (X, ✓, ticks) que asignan cada tarea a una frecuencia. El chunk llega al generator con la tabla "vacía" — texto legible pero sin la información estructural clave. El generator, al verla incompleta, rellena con conocimiento de pretraining pretendiendo que la asignación viene del fragmento (alucinación inducida por ingest defectuoso).

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

### Fase 2 — Metadata enrichment por chunk durante ingest (pre-Fase 3 Telegram, ~1-2 días)

**Qué**: durante ingest, llamar a Claude Haiku por cada chunk para generar: (a) 5-10 sinónimos/paráfrasis del concepto central, (b) 3-5 preguntas frecuentes que ese chunk responde, (c) keywords de dominio PCI relacionados. Almacenar en `chunk.enriched_synonyms`, `chunk.enriched_faqs`, `chunk.enriched_keywords`. Indexar en FTS.

**Por qué segundo**: generaliza a cualquier vocabulary mismatch, no solo hp001. Pago único ($500 aprox en Haiku para 168k chunks), beneficio permanente en runtime (latencia igual que hoy, determinístico).

**Cómo**: (1) script `enrich_chunks.py` que itera BD y para cada chunk llama Haiku con prompt estructurado (output JSON). (2) Migration para columnas nuevas + índice FTS. (3) Modificar retriever para buscar en union(content, synonyms, faqs, keywords) con boosts. (4) Validar con subset de queries históricas fallidas.

**Coste**: ~1-2 días (prompt design + script + migration + smoke test). $500 en API.

### Fase 3 — Agentic RAG con failure detection + reformulación (Fase 4 del proyecto, condicional, ~1 semana)

**Qué**: Claude decide dinámicamente si tiene info suficiente; si no, reformula query y pide retrieval otra vez. Opcionalmente multi-hop (2-3 búsquedas encadenadas para preguntas compuestas).

**Por qué tercero (y condicional)**: solo aporta valor cuando el bottleneck deja de ser vocabulary (cubierto por 1+2) y pasa a ser (a) queries multi-hop reales *(ej. "qué cambios de cableado migrando de AFP-200 a ID3000")*, (b) queries que requieren que el bot decida cuándo parar/reformular, (c) multi-turn (TECH_DEBT #19). Con las 52 preguntas actuales no hay signal claro de multi-hop; predominan single-hop.

**Cons** si se implementa prematuramente: 2-3× latencia/coste por query (inaceptable en campo con alarma sonando), loops impredecibles difíciles de debuggear, cambio arquitectural mayor.

**Cómo**: Claude Agent SDK o tool-use nativo. Definir tools `search_corpus(query, top_k)`, `clarify_with_user(question)`, `finalize_answer(response)`. Loop hasta terminación con límite de 3 iteraciones.

**Coste**: ~1 semana + cambio infra + eval multi-turn.

### Relación entre las 4 fases

Son **capas ortogonales, se apilan** (no son alternativas):

```
┌──────────────────────────────────────────┐
│  Fase 3 — AGENTE (orchestration)         │
│  decide cuándo reformular / parar        │
├──────────────────────────────────────────┤
│  Fase 1b — BM25 + RRF (condicional)      │
│  hybrid fusion vector + BM25             │
├──────────────────────────────────────────┤
│  Fase 1 — RETRIEVAL weighted FTS         │
│  section_title (A) + content (B)         │
├──────────────────────────────────────────┤
│  Fase 2 — ÍNDICE enriquecido             │
│  synonyms + faqs + keywords              │
└──────────────────────────────────────────┘
```

Apilar Fase 3 sobre 1+2 = agente reformulando queries sobre índice rico (máxima probabilidad de encontrar). Apilar Fase 3 sin 1+2 = agente reformulando sobre índice pobre (2-3× coste sin fix de base). **Nunca hacer 3 antes de 1+2**. **Fase 1b solo si Fase 1 + Fase 2 no son suficientes y el gap restante es recall de retrieval**.

### Decisión actual (sesión 16, 24 abril 2026)

Diferido. Fase 1 es candidata prioritaria para sesión 17 (quick win, alto ROI). Fase 1b (BM25+RRF) condicional: solo si métricas plateau <95% tras Fase 1+2 y análisis de FAILs muestra gap de retrieval recall. Fase 2 se activa cuando se acerque el despliegue de Fase 3 Telegram (necesitamos runtime determinístico y baja latencia). Fase 3 solo si/cuando aparezcan signals reales de multi-hop o el bot necesite decidir dinámicamente (probablemente Fase 4+).

**Coste estimado total**: Fase 1 = 3-5h · Fase 1b = 5-7h (condicional) · Fase 2 = 1-2 días + $500 · Fase 3 = 1 semana (condicional).

