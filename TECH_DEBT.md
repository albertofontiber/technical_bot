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

## Mejoras YA incorporadas al flujo (no deuda, registro histórico)

- **Test de mapping en `tests/`**: verifica que todo PDF en `Manuales_{Manufacturer}/` tiene entrada en los dicts de override. Implementado [fecha ingesta Morley].
- **Dry-run de parsing con stats**: `scripts/dry_run_parse.py` reporta n_chunks, model, category, tokens por archivo sin generar embeddings. Implementado [fecha ingesta Morley].
- **Eval con preguntas por fabricante**: el eval incluye ≥3 preguntas cuya respuesta depende de manuales de cada fabricante ingestado.
