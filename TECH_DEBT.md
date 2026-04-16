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

## Mejoras YA incorporadas al flujo (no deuda, registro histórico)

- **Test de mapping en `tests/`**: verifica que todo PDF en `Manuales_{Manufacturer}/` tiene entrada en los dicts de override. Implementado [fecha ingesta Morley].
- **Dry-run de parsing con stats**: `scripts/dry_run_parse.py` reporta n_chunks, model, category, tokens por archivo sin generar embeddings. Implementado [fecha ingesta Morley].
- **Eval con preguntas por fabricante**: el eval incluye ≥3 preguntas cuya respuesta depende de manuales de cada fabricante ingestado.
