# Gestión documental del RAG — diseño propuesto

Este documento describe el problema de **gestión del ciclo de vida de los
manuales** en el bot RAG, las consecuencias reales de no gestionarlo bien, y
la arquitectura que propongo implementar para resolverlo.

Es un **design document**: no es código todavía. La intención es alinear sobre
el enfoque antes de empezar a construir. Coste estimado de implementación:
~8-12h de desarrollo + ~2h de migración de datos existentes.

> **Contexto**: este documento se escribe en abril 2026, tras ingestar Notifier
> (357 PDFs) y antes de ingestar Morley. La decisión de hacerlo ahora y no
> después viene de la experiencia con Notifier — detectamos varios casos de
> revisiones múltiples del mismo manual (`rev 3` vs `rev 4`) y documentos
> multi-parte (`MADT951_01`, `_02`, `_03`) que sin gestión adecuada van a
> degradar las respuestas del bot.

---

## 1. El problema en lenguaje claro

Los fabricantes publican manuales. Los manuales **cambian con el tiempo**.
Cuando un fabricante corrige un error, añade un componente nuevo, o cambia un
procedimiento de instalación por motivos de seguridad, publica una **nueva
revisión** del mismo documento.

El problema es que nosotros descargamos PDFs de su web, y su web a menudo:

- **Mantiene las revisiones antiguas online** "por si acaso" (legítimo, porque
  hay instalaciones antiguas que usan la rev 1). Ejemplo real visto en
  Notifier: `AM-8100 manual rev 4.pdf` cuelga junto al índice pero nadie te
  dice si hay una `rev 5` en otra sección.
- **Divide un manual grande en partes** con sufijos `_01`, `_02`, `_03`, etc.
  Ejemplo: `MADT951_01.pdf`, `MADT951_02.pdf`, `MADT951_04.pdf`, `MADT951_06.pdf`
  son cuatro páginas de un único folleto de instrucciones que originalmente se
  imprimió en A3 doblado. Si las tratas como cuatro documentos independientes,
  el RAG puede darte la página 2 sin la página 1 que contiene el contexto.
- **Publica la misma información en varios idiomas** con nombres parecidos:
  `MANUAL_AM8100_ES.pdf`, `MANUAL_AM8100_EN.pdf`. Son el mismo documento, no
  dos distintos.

**Por qué nos importa críticamente**: los técnicos de PCI hacen instalaciones
que, si salen mal, tienen **consecuencias fatales reales**. Un incendio en un
edificio donde el sistema no disparó por una instalación incorrecta de un
detector es un muerto. Si el bot le dice al técnico "según el manual, el cable
de señal va al borne 7" cuando en la rev 4 el fabricante cambió al borne 9 por
un problema de interferencias, hemos metido al técnico en un error que el
fabricante ya sabía y había corregido.

La regla de oro del sistema:

> **El bot nunca debe devolver información de un documento obsoleto sin
> avisar explícitamente de que es obsoleto.**

---

## 2. Estado actual (qué tenemos hoy)

Tabla única `chunks` en Supabase con estas columnas relevantes:
- `content` — el texto del fragmento
- `embedding` — vector de 1536 dimensiones
- `manufacturer`, `product_model`, `category`
- `source_file` — el nombre del PDF original (ej: `AM8100 rev 4.pdf`)
- `page_number`

**Lo que sabemos hoy**: dado un chunk, sabemos de qué PDF vino y de qué página
exacta. **Lo que no sabemos**:
- Si ese PDF es la versión más reciente del manual
- Si existe una versión más nueva que deberíamos usar en su lugar
- Si es parte de un documento multi-pieza cuyas otras partes están en otros
  chunks
- Si el mismo contenido existe en otro idioma

No hay forma hoy de filtrar "dame sólo las versiones vigentes" porque no tenemos
el concepto de "versión vigente".

---

## 3. Diseño propuesto

### 3.1. Modelo de datos — dos tablas nuevas + una columna en chunks

**Tabla nueva: `documents`**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_family TEXT NOT NULL,        -- "AM-8100 manual usuario"
    revision TEXT,                         -- "4" | "Issue 3" | "v1.4" | NULL
    revision_date DATE,                    -- 2024-10-30 si detectado
    language TEXT,                         -- 'es' | 'en' | 'multi'
    doc_type TEXT,                         -- 'instalacion' | 'usuario' | 'programacion' | ...
    manufacturer TEXT NOT NULL,
    product_model TEXT,
    source_pdf_filename TEXT NOT NULL,     -- filename original
    source_pdf_sha256 TEXT NOT NULL,       -- hash SHA-256 del contenido del PDF
    status TEXT NOT NULL DEFAULT 'active', -- 'active' | 'superseded' | 'draft' | 'retired'
    supersedes_id UUID REFERENCES documents(id),
    superseded_by_id UUID REFERENCES documents(id),
    ingested_at TIMESTAMPTZ DEFAULT now(),
    notes TEXT,
    UNIQUE (manufacturer, source_pdf_sha256)
);

CREATE INDEX idx_documents_family_status ON documents(document_family, status);
CREATE INDEX idx_documents_mfr_status ON documents(manufacturer, status);
```

**Nueva columna en `chunks`**:
```sql
ALTER TABLE chunks ADD COLUMN document_id UUID REFERENCES documents(id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
```

**Tabla nueva: `document_groups`** (para documentos multi-parte)
```sql
CREATE TABLE document_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_name TEXT NOT NULL,              -- "MADT951 Multi-Part"
    manufacturer TEXT NOT NULL,
    description TEXT
);

CREATE TABLE document_group_members (
    group_id UUID REFERENCES document_groups(id),
    document_id UUID REFERENCES documents(id),
    part_number INT,                       -- 1, 2, 3, 4
    PRIMARY KEY (group_id, document_id)
);
```

**Explicación en lenguaje claro de por qué esta estructura**:

- **`documents` es el "catálogo maestro de manuales"**. Cada entrada es un PDF
  único que hemos procesado. Lleva la metadata que identifica al documento
  como individuo: qué familia, qué revisión, qué idioma, qué estado.
- **`chunks.document_id`** conecta cada fragmento con su documento padre. Hoy
  los chunks apuntan sólo a un `source_file` (texto plano, frágil a renames).
  Con la nueva estructura, un rename del fichero no rompe nada porque el
  enlace es por UUID estable.
- **`document_groups`** es el mecanismo para tratar `MADT951_01/_02/_03/_04`
  como un único folleto lógico. Cuando el retriever trae uno, puede opcionalmente
  traerse los hermanos del grupo.

### 3.2. Cadena de revisiones — cómo funciona

Cuando ingestamos un PDF nuevo, el proceso es:

1. **Parser heurístico** extrae `(document_family, revision, revision_date)`
   del filename y de las primeras 3 páginas del PDF.
   - Reglas del parser: detecta `rev N`, `Issue N`, `v1.4`, `Rev. A`,
     `30-10-2024`, etc. Si ambigüo, marca `revision = NULL` y continúa.
2. **Lookup**: ¿existe ya un `document` con el mismo `(manufacturer, document_family,
   language)`?
   - **No existe** → inserta como `status='active'`, no hay supersede.
   - **Existe, y la revisión nueva es >= existente**:
     - Marcar existente como `status='superseded'`, setear
       `existing.superseded_by_id = new.id`
     - Insertar nuevo como `status='active'`, setear `new.supersedes_id = existing.id`
   - **Existe, y la revisión nueva es < existente** (estamos ingestando algo
     viejo por error):
     - Insertar nuevo como `status='superseded'`, apuntar a la versión más
       reciente que encontremos
   - **Revisión incomparable** (una tiene `rev 4` y la otra `v1.4`): marcar
     `status='needs_review'` y notificar. No decidir automáticamente.

3. **Parser de revisiones — detalle técnico**: vive en un módulo nuevo
   `src/ingestion/revision_parser.py`. Tests exhaustivos con ejemplos reales
   de los filenames que hemos visto en Notifier + Morley + Detnov. Cuando
   falla, degrada a `revision=NULL` (nunca inventa).

### 3.3. Retrieval — cómo afecta al query

Consulta hoy (simplificada):
```sql
SELECT content, metadata
FROM chunks
WHERE manufacturer = 'Notifier'
  AND embedding <=> :query_embedding < 0.5
ORDER BY similarity LIMIT 20
```

Consulta propuesta:
```sql
SELECT c.content, c.metadata, d.revision, d.revision_date, d.status
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.manufacturer = 'Notifier'
  AND d.status = 'active'                  -- <<< clave: sólo vigentes
  AND c.embedding <=> :query_embedding < 0.5
ORDER BY similarity LIMIT 20
```

**Modo "incluir obsoletos" con warning**: caso de uso — el técnico pregunta
explícitamente por un procedimiento de una revisión antigua concreta (ej:
"¿cómo se conectaba el borne 7 en la rev 3 del AM-8100?"), o el retriever no
encuentra nada en las revisiones activas y queremos dar un fallback controlado.
Flag en el retriever:
```python
retrieve(query, include_superseded=True)
```
**Regla clave**: el warning **sólo** salta cuando el chunk devuelto es
efectivamente de un documento con `status='superseded'`. Que el equipo en
campo sea antiguo **no** es motivo de warning — si el manual que servimos es
la última revisión disponible del fabricante, esa **es** la fuente autoritativa
aunque el equipo tenga 10 años. El warning no es sobre la edad del equipo, es
sobre si la información que servimos está ella misma deprecada por una versión
más nueva.

Cuando sí salta (chunk de status='superseded'), el generator envuelve la
respuesta así:

> **⚠️ Aviso**: la información de abajo proviene del manual `AM-8100 rev 3` que
> está **obsoleto**. Existe una revisión más reciente (`rev 4`, publicada
> 2024-10-30) que tiene cambios en la sección de conexionado. Verifica con el
> manual vigente antes de aplicar esto en campo.

Caso contrario (chunk de status='active', aunque el manual sea de 2015 y el
equipo del técnico sea de 2010): se devuelve limpio, con la cita de la
revisión y la fecha, sin warning.

**Citación siempre**: la respuesta del bot siempre incluye la referencia
exacta del documento: `AM-8100 manual usuario, rev 4 (2024-10-30), página 14`.
Esto no es cosmético — es la única forma de que un técnico pueda auditar qué
le está diciendo el bot y contrastarlo con la fuente primaria.

### 3.4. Documentos multi-parte — cómo se gestionan

**Detección en la ingesta**: heurística basada en sufijos numéricos secuenciales
y tamaños pequeños. Si vemos:
- `MADT951_01.pdf` (2 páginas)
- `MADT951_02.pdf` (2 páginas)
- `MADT951_04.pdf` (2 páginas)
- `MADT951_06.pdf` (2 páginas)

...con el mismo prefijo, sufijo numérico no-continuo, y tamaño < 5 páginas cada
uno, lo tratamos como un grupo multi-parte. Creamos una fila en `document_groups`
y vinculamos los 4 documentos.

**Efecto en el retrieval**: cuando un chunk de `MADT951_01` aparece en los
resultados, opcionalmente el retriever trae también los primeros chunks de
`_02`, `_04`, `_06` como contexto adicional de baja prioridad (para que el
LLM tenga visibilidad del documento completo al responder).

**Nota importante**: esta heurística es frágil. Puede confundirse con revisiones
que usan sufijo numérico (`_01` = v1, `_02` = v2). El parser de revisiones
tiene prioridad sobre el parser multi-parte. Si ambos parsers disienten, el
fichero se marca `needs_review` y un humano decide.

### 3.5. Rollback y auditoría

**Rollback de una revisión**: si detectamos una regresión tras ingestar `rev 4`,
podemos hacer:
```sql
UPDATE documents SET status='superseded' WHERE id = <rev4.id>;
UPDATE documents SET status='active' WHERE id = <rev3.id>;
```
Los chunks no se tocan — sólo cambia qué documento está "vigente" y por tanto
qué chunks incluye el retriever. Rollback en 2 segundos.

**Auditoría**: tabla `documents` con `ingested_at`, `notes`, y los vínculos
supersedes/superseded_by forman un historial navegable. `SELECT * FROM
documents WHERE document_family = 'AM-8100 manual usuario' ORDER BY
revision_date DESC` te da la cadena completa de revisiones.

---

## 4. Safety layer — el plan para no matar a nadie

Tres capas de defensa contra el error "el bot da info obsoleta y el técnico
la aplica":

### Capa 1 — Nunca devolver obsoletos por defecto
Implementado vía `status='active'` en la query. Los chunks de `superseded`
están en la DB pero no se retornan salvo que el caller pase
`include_superseded=True`.

### Capa 2 — Citación obligatoria con fecha de revisión
El prompt del generator tiene una regla hard-coded:

> "Siempre cita la fuente con formato: `<nombre documento>, rev <N>
> (<fecha>), página <P>`. Si no tienes el dato de revisión, cita sin ella
> pero **menciona explícitamente** que no pudiste verificar la fecha de la
> fuente."

### Capa 3 — Eval de regresión con preguntas-trampa
Para cada fabricante, añadimos al eval set al menos **una pregunta cuya
respuesta correcta cambie entre dos revisiones conocidas**. Ejemplo sintético:

> Pregunta: "¿Cuál es la corriente máxima del relé de salida del AM-8100 según
> el manual vigente?"
>
> Respuesta oro: "8 A (manual rev 4, cambió de 5 A en rev 3)"
>
> Criterio de pass: la respuesta debe contener "8" y debe citar "rev 4".

Si por cualquier razón el pipeline vuelve a devolver chunks de `rev 3` (ej:
bug en la query, bug en el parser de revisiones, datos corruptos tras una
migración), esta pregunta falla y el eval bloquea el deploy.

**Esto es la red de seguridad**: ninguna de las otras capas es suficiente por
sí sola, pero el eval de regresión con pregunta-trampa es la que atrapa los
errores no anticipados.

---

## 5. Plan de implementación por fases

**Fase 0 — Pre-requisitos** (antes de cualquier código):
- [x] Este documento aprobado
- [ ] Credenciales Morley verificadas (para validar que el flujo funciona en
      un segundo fabricante además de Notifier)

**Fase 1 — Modelo de datos** (~2h):
- [ ] Migration SQL con las 3 tablas nuevas + ALTER de chunks
- [ ] Script de backfill que crea una fila en `documents` por cada
      `source_file` único existente en `chunks`, con `revision=NULL,
      status='active'` (migración suave)
- [ ] Actualizar `chunks.document_id` en todos los chunks existentes
- [ ] Tests: verificar que todas las filas de chunks tienen document_id no-NULL

**Fase 2 — Parser de revisiones** (~3h):
- [ ] Nuevo módulo `src/ingestion/revision_parser.py` con función
      `parse_revision(filename, first_pages_text) -> RevisionInfo`
- [ ] Test suite con ≥20 ejemplos reales de filenames (Notifier, Morley,
      Detnov) + edge cases
- [ ] Parser heurístico de `document_family` que normaliza
      "AM-8100 manual usuario y programacion rev 4 30-10-2024.pdf"
      → family="AM-8100 manual usuario y programacion"

**Fase 3 — Pipeline de ingesta actualizado** (~2h):
- [ ] `ingest_single_pdf` ahora:
      1. Calcula hash del PDF
      2. Llama al parser de revisiones
      3. Hace lookup en `documents` por `(manufacturer, document_family, language)`
      4. Decide insert / supersede / needs_review
      5. Inserta chunks con `document_id`
- [ ] Skip idempotente por hash en lugar de por filename

**Fase 4 — Retriever con filtro de status** (~1h):
- [ ] Query SQL actualizada para JOIN con documents + `WHERE status='active'`
- [ ] Flag `include_superseded` expuesto en el retriever
- [ ] Tests que verifican que chunks de superseded NO aparecen en modo normal

**Fase 5 — Generator con citación obligatoria** (~1h):
- [ ] System prompt actualizado con la regla de citación con revisión
- [ ] Tests unitarios contra respuestas del bot que verifican formato de cita

**Fase 6 — Eval de regresión** (~2h):
- [ ] Añadir al menos 2 preguntas-trampa por fabricante al eval set
- [ ] Automatizar ejecución del eval en `scripts/run_eval.py` para que corra
      antes de cualquier ingesta nueva

**Fase 7 — Grupos multi-parte** (~2h, opcional, priorizar según señal real):
- [ ] Detector de grupos por sufijo numérico
- [ ] Tabla `document_groups` + members
- [ ] Retriever opcional-extended: trae hermanos del grupo

**Total estimado**: 11-13h para fases 1-6 (lo imprescindible). Fase 7 la
dejaría para cuando se demuestre que hace falta con datos reales.

---

## 6. Preguntas abiertas

**Q1: ¿Qué hacemos con la cadena de revisiones para Detnov (ya ingestado)?**
Detnov fue el primer fabricante del bot, tiene ~30 manuales. Hoy están
ingestados sin metadata de revisión. Opciones:
- (a) Backfill best-effort: correr el parser de revisiones sobre todos los
  filenames existentes, asumir que cada uno es `active` y single-revision
- (b) Re-ingestar Detnov desde cero con el nuevo pipeline

Recomiendo (a) porque Detnov es estable y el coste de re-ingesta es innecesario.

**Q2: ¿Cómo detectamos que un manual que creíamos `active` ahora está obsoleto
porque el fabricante publicó una rev nueva?**
Propongo: **re-scrapes trimestrales** con diffing. Si el scraper trae un
filename que contiene `rev 5` y nosotros tenemos `rev 4` como active, ingesta
automática + supersede del viejo. Coste marginal bajo si el scraper ya es
idempotente.

**Q3: ¿Qué hacemos cuando el parser de revisiones falla?**
Fallar en silencio (setear `revision=NULL`) es peligroso porque pierdes la
capacidad de supersede. Proponer:
- Si `revision=NULL` y existe otro documento de la misma familia con `revision`
  conocida, marcar el nuevo como `needs_review`
- Dashboard/script `scripts/review_pending.py` que lista todos los `needs_review`
  para que un humano los resuelva

**Q4: ¿Hay riesgo de que una ingesta concurrente cree dos filas `active` de la
misma familia?**
Sí, si dos procesos ingestan al mismo tiempo. Mitigación:
- Ingesta single-process por defecto (lo es hoy)
- Si en el futuro necesitamos paralelismo, usar `SELECT ... FOR UPDATE` en
  postgres sobre la fila existente antes del supersede

---

## 7. Decisión requerida

Para avanzar necesito tu OK en 3 puntos:

1. **¿Apruebas el modelo de datos de la sección 3.1?** (3 tablas nuevas + 1
   columna en chunks). Es reversible pero costoso de deshacer.

2. **¿Priorizamos Fases 1-6 antes de ingestar Morley, o ingestamos Morley
   primero con el pipeline actual y luego hacemos el refactor sobre ambos?**

   Mi recomendación: hacer las fases 1-6 **antes** de Morley. Dos razones:
   - Morley va a añadir otra capa de complejidad (misma familia de manuales
     en dos fabricantes-hermanos de Honeywell). Mejor estrenar el sistema de
     revisiones con datos ya conocidos (Notifier + Detnov) antes de meter
     Morley.
   - El refactor sobre 17.000 chunks ya existentes es más seguro que sobre
     25.000+ con Morley añadido.

3. **¿Aceptas el trade-off de 12h de desarrollo a cambio de safety-net para
   revisiones?**

Una vez me digas sí a estos tres, empezamos por la Fase 1 y ejecutamos secuencial.
