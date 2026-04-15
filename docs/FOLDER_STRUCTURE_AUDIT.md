# Auditoría de estructura de carpetas

Fecha: 2026-04-15
Estado: **Recomendaciones — no se ha movido nada todavía**

Este documento inventaría el estado actual del repositorio, señala problemas, y propone una estructura objetivo. Cada acción lleva etiqueta de riesgo. **Nada se mueve sin aprobación de Alberto.**

---

## 1. Inventario actual

### Raíz del proyecto
```
=0.11.0                          ← BASURA (salida de pip atrapada en un fichero)
Inventario_Manuales.xlsx         ← trabajo auxiliar
Manuales_ES/                     ← manuales Detnov
Manuales_Morley/                 ← manuales Morley
Manuales_Notifier/               ← manuales Notifier públicos
Manuales_Notifier_Privado/       ← manuales Notifier con login
TECH_DEBT.md
docs/
dry_run_morley.log               ← log suelto
eval_results.json                ← resultado de eval suelto
eval_results_retrieval.json      ← resultado de eval suelto
eval_results_v2.json             ← resultado de eval suelto
extracted_images/                ← caché de imágenes
ingest_morley.log                ← log suelto
instructions.md                  ← 300 líneas, legado del prompt original
migrations/
notifier_db_sources.txt          ← trabajo auxiliar
product_inventory.json           ← trabajo auxiliar
requirements.txt
scripts/
src/
supabase_schema.sql              ← debería vivir en migrations/ o docs/
tests/
```

### `src/` (código de producción)
```
src/
├── __init__.py
├── config.py
├── logging_db.py
├── api/
│   └── __init__.py              ← VACÍO. Nunca se usó.
├── bot/
│   └── telegram_bot.py
├── ingestion/                   (12 módulos, sanos)
│   ├── chunker.py
│   ├── document_registry.py     ← nuevo (Fase 3)
│   ├── embedder.py
│   ├── image_extractor.py
│   ├── ingest.py
│   ├── language_filter.py
│   ├── pdf_parser.py
│   ├── revision_parser.py       ← nuevo (Fase 2)
│   ├── supabase_client.py
│   └── translator.py
└── rag/
    ├── generator.py
    ├── reranker.py
    └── retriever.py
```

### `scripts/` (25 ficheros, mezclados)
Agrupados por propósito real:

**Entry points (mantener):**
- `run_bot.py`
- `run_ingestion.py`
- `eval_rag.py`

**Scrapers / descargadores (mantener, activos):**
- `scrape_notifier.py`
- `scrape_notifier_auth.py`
- `download_morley.py`
- `_download_notifier_new.py` — nombre con `_` sugiere legado, revisar

**Operaciones de mantenimiento recurrentes (mantener):**
- `re_embed.py`
- `re_ingest.py`
- `translate_notifier_en.py`
- `dry_run_parse.py`
- `migrations/001_backfill_documents.py`

**One-offs ya ejecutados — candidatos a archivo:**
- `fix_notifier_unknown_models.py` — parche puntual
- `fix_unknown_models.py` — parche puntual
- `structural_fixes.py` — parche de limpieza DB
- `migrate_categories.py` — migración Detnov taxonomy (ya hecha)
- `dedupe_morley.py` — rescate duplicados Morley (ya hecho)
- `vision_rescue_zerochunks.py` — rescate zero-chunk (ya hecho)
- `llm_classify_unknowns.py` — clasificación puntual Notifier
- `update_notifier_metadata.py` — actualización metadatos puntual
- `reclassify_chunks.py` — reclasificación content_type puntual
- `reclassify_morley.py` — migración Morley manufacturer (ya hecha)

**Subcarpetas:**
- `scripts/migrations/` — correcto, un fichero (`001_backfill_documents.py`)
- `scripts/sql/fix_remaining_unknown_models.sql` — SQL suelto

### `tests/` (escaso)
- `test_override_mappings.py`
- `test_revision_parser.py` (nuevo, 55/55 passing)

### `docs/`
- `DOCUMENT_MANAGEMENT.md`
- `INGESTION_PLAYBOOK.md`

### `migrations/`
- `001_document_management.sql`

---

## 2. Problemas detectados

| # | Problema | Gravedad |
|---|---|---|
| 1 | Fichero basura `=0.11.0` con salida de pip en la raíz | Baja — ruido visual |
| 2 | 4 ficheros `eval_results*.json` sueltos en raíz | Baja — desorden |
| 3 | 2 ficheros `*.log` sueltos en raíz (Morley) | Baja — desorden |
| 4 | 4 directorios `Manuales_*` hermanos en raíz, sin paraguas común | Media — escalabilidad (cada fabricante nuevo añade otra carpeta) |
| 5 | `supabase_schema.sql` en raíz cuando existe `migrations/` | Media — confunde sobre cuál es la fuente de verdad |
| 6 | `src/api/` vacío desde su creación | Baja — confunde al lector |
| 7 | `scripts/` mezcla entry points vivos con 10+ one-offs históricos | Media — imposible saber qué está vivo |
| 8 | `tests/` con solo 2 ficheros de test (cobertura pobre) | Alta — pero es otra historia, no estructura |
| 9 | `instructions.md` (300 líneas) duplicando info que ahora vive en `docs/` y `CLAUDE.md` | Media — fuente de verdad ambigua |
| 10 | `product_inventory.json`, `notifier_db_sources.txt`, `Inventario_Manuales.xlsx` sueltos en raíz | Baja — trabajo auxiliar sin hogar |

---

## 3. Estructura objetivo propuesta

```
Technical Bot/
├── README.md                  (nuevo, breve, apunta a docs/)
├── CLAUDE.md                  (si existe, mantener)
├── requirements.txt
├── pyproject.toml             (opcional, futuro)
│
├── src/
│   ├── config.py
│   ├── logging_db.py
│   ├── bot/
│   ├── ingestion/
│   └── rag/
│   # src/api/ ELIMINADO
│
├── scripts/
│   ├── run_bot.py
│   ├── run_ingestion.py
│   ├── eval_rag.py
│   ├── re_embed.py
│   ├── re_ingest.py
│   ├── dry_run_parse.py
│   ├── translate_notifier_en.py
│   ├── scrapers/
│   │   ├── scrape_notifier.py
│   │   ├── scrape_notifier_auth.py
│   │   └── download_morley.py
│   ├── migrations/
│   │   └── 001_backfill_documents.py
│   └── archive/                        ← one-offs históricos aquí
│       ├── fix_notifier_unknown_models.py
│       ├── fix_unknown_models.py
│       ├── structural_fixes.py
│       ├── migrate_categories.py
│       ├── dedupe_morley.py
│       ├── vision_rescue_zerochunks.py
│       ├── llm_classify_unknowns.py
│       ├── update_notifier_metadata.py
│       ├── reclassify_chunks.py
│       ├── reclassify_morley.py
│       └── README.md                   (explica que son históricos, no ejecutar)
│
├── manuales/                           ← paraguas común para todos los fabricantes
│   ├── detnov/                         (antes Manuales_ES)
│   ├── notifier/                       (antes Manuales_Notifier)
│   ├── notifier_privado/               (antes Manuales_Notifier_Privado)
│   └── morley/                         (antes Manuales_Morley)
│
├── migrations/
│   ├── 001_document_management.sql
│   └── schema.sql                      (antes supabase_schema.sql)
│
├── docs/
│   ├── DOCUMENT_MANAGEMENT.md
│   ├── INGESTION_PLAYBOOK.md
│   ├── FOLDER_STRUCTURE_AUDIT.md       ← este documento
│   └── legacy/
│       └── instructions.md              (archivado)
│
├── tests/
│   ├── test_override_mappings.py
│   └── test_revision_parser.py
│
├── evals/                              ← resultados históricos de eval
│   ├── results/
│   │   ├── eval_results.json
│   │   ├── eval_results_retrieval.json
│   │   └── eval_results_v2.json
│   └── cases/                          (futuro: YAML de casos)
│
├── logs/                               ← logs de ingesta
│   ├── dry_run_morley.log
│   └── ingest_morley.log
│
├── data/                               ← trabajo auxiliar no versionable
│   ├── product_inventory.json
│   ├── notifier_db_sources.txt
│   └── Inventario_Manuales.xlsx
│
├── extracted_images/                   (mantener, es caché)
│
└── TECH_DEBT.md
```

---

## 4. Acciones concretas

Etiquetas de riesgo:
- 🟢 **Seguro** — no rompe imports ni rutas de código
- 🟡 **Revisar** — toca rutas referenciadas en código, hay que buscar usos antes
- 🔴 **Bloqueador** — requiere refactor en varios ficheros

### Fase A: limpieza sin riesgo (🟢)

| Acción | Comando conceptual |
|---|---|
| Borrar `=0.11.0` | `rm "=0.11.0"` |
| Crear `evals/results/`, mover los 3 `eval_results*.json` | |
| Crear `logs/`, mover `dry_run_morley.log`, `ingest_morley.log` | |
| Crear `data/`, mover `product_inventory.json`, `notifier_db_sources.txt`, `Inventario_Manuales.xlsx` | |
| Crear `docs/legacy/`, mover `instructions.md` | |
| Eliminar `src/api/` (está vacío) | |
| Añadir `docs/legacy/`, `logs/`, `data/`, `evals/` a `.gitignore` si corresponde | |

### Fase B: reorganización de scripts (🟡)

1. Crear `scripts/archive/` con `README.md` explicando que son históricos
2. Mover los 10 one-offs listados arriba a `scripts/archive/`
3. Crear `scripts/scrapers/`, mover los 3 scrapers
4. **Verificar antes:** ningún CI, cron, ni documento (`INGESTION_PLAYBOOK.md`) invoca rutas `scripts/fix_*.py` directamente
5. Renombrar `_download_notifier_new.py` o archivarlo (su nombre con guion bajo sugiere legado)

### Fase C: consolidar manuales (🟡)

1. Crear carpeta `manuales/`
2. Mover las 4 carpetas `Manuales_*/` dentro como subdirectorios en minúscula
3. **Revisar antes:** `src/config.py` define `MANUALS_DIR`. Los scripts de scraping escriben directamente a `Manuales_Notifier/`. Hay que actualizar:
   - `src/config.py` → `MANUALS_DIR`
   - `scripts/scrape_notifier.py`, `scripts/scrape_notifier_auth.py`, `scripts/download_morley.py` → destinos de descarga
   - `INGESTION_PLAYBOOK.md` → todas las rutas citadas
4. **Riesgo:** si hay rutas hardcoded que no detecto, rompe la ingesta.

### Fase D: SQL y migraciones (🟡)

1. Mover `supabase_schema.sql` → `migrations/schema.sql`
2. Mover `scripts/sql/fix_remaining_unknown_models.sql` → `scripts/archive/sql/`
3. Añadir nota en `migrations/` sobre cuál es la fuente de verdad (schema snapshot vs migraciones incrementales)

### Fase E: diferido (🔴, no ahora)

- Migrar a layout `src/` con `pyproject.toml` e imports absolutos de paquete (hoy son relativos con `python -m src.bot.telegram_bot`). Esto afectaría a todos los módulos y entry points — no tocar en esta sesión.
- Ampliar `tests/` con cobertura real del retriever, generator, y pipeline de ingesta. Esto NO es estructura, es deuda de tests.

---

## 5. Recomendación de ejecución

Propongo hacer **Fase A (🟢) inmediatamente** en cuanto Alberto dé el visto bueno — son todo limpiezas puras sin riesgo para el código. Después, decidir si Fase B y C se hacen **antes** de la ingesta de Morley o **después**:

- **Antes:** ventaja: la ingesta de Morley aterriza ya en la estructura limpia. Riesgo: si Fase C rompe la ingesta, retrasa Morley.
- **Después:** ventaja: no arriesgamos nada antes del hito Morley. Riesgo: Morley aterriza en la estructura vieja y hay que migrar igual después.

Mi preferencia: **Fase A ahora, Fase B-D después de Morley ingestado**. Los one-offs y las rutas de manuales son más seguras de mover cuando no hay ingesta activa.

---

## 6. Fuera de alcance de esta auditoría

- **Deuda de tests** — solo hay 2 ficheros en `tests/`. Es grave pero no es estructura de carpetas.
- **Refactor a layout package** (`src/pci_bot/...` con `pyproject.toml`). Upgrade futuro, no urgente.
- **Revisión del contenido** de `TECH_DEBT.md` y `instructions.md`. Archivarlos es estructural; releerlos para extraer tareas vivas es otro trabajo.
- **Reorganizar `src/ingestion/`** internamente (12 módulos planos). Hoy funciona, tocarlo rompe imports por todas partes.

---

## Próximo paso

Esperando aprobación de Alberto para ejecutar **Fase A**. Las demás fases se discuten después de ver el resultado limpio.
