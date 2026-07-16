# S117 — diseño de persistencia versionada `chunks_v3`

## Decisión

Crear `public.chunks_v3` como tabla shadow independiente y rematerializarla desde
los registros raw de extracción. `chunks_v2` permanece sin cambios y continúa
siendo la única tabla servida hasta que pasen los gates de migración, retrieval,
rerank, synthesis y regresión fact-level.

No se permite `INSERT ... SELECT` desde `chunks_v2` para poblar la tabla nueva:
`chunks_v2` no persiste `section_anchor`, `section_lineage` ni el span de bloques
fuente, por lo que una copia no podría demostrar provenance.

## Envelope por chunk

Cada fila de `chunks_v3` conserva el contrato actual de retrieval y añade:

- `provenance_version = 1`.
- `provenance_contract = 's116_section_lineage_v1'`.
- `raw_artifact_sha256`: hash del JSON raw completo usado para materializarla.
- `chunker_sha256`: hash de `src/reingest/chunk.py`.
- `content_sha256`: hash exacto de `content`.
- `source_block_start` y `source_block_end`: intervalo inclusivo en el stream
  aplanado del documento.
- `section_anchor JSONB`: ocurrencia concreta del heading hoja o `NULL`.
- `section_lineage JSONB`: array ordenado de todas las ocurrencias ancestras.

Los anchors incluyen `heading_text`, `title`, `level`, `source_page`,
`source_block_index` y `heading_sha256`. Los hashes de heading prueban
consistencia interna; `raw_artifact_sha256` liga el envelope al artefacto fuente.

## Identidad e idempotencia

El UUID de `chunks_v3` se deriva con UUIDv5 de:

`namespace_s117 + extraction_sha256 + chunk_index + content_sha256 + provenance_version`

La misma entrada produce el mismo ID en reintentos. Un cambio real de frontera o
contenido produce otra identidad. Los `duplicate_of` intra-documento se traducen
del ID transitorio al UUIDv5 antes de persistir.

La tabla exige unicidad de `(extraction_sha256, chunk_index,
provenance_version)` y el escritor usa lotes. No borra `chunks_v2` ni mezcla
versiones dentro de una misma tabla.

## Invariantes fail-closed

Antes de admitir una fila:

1. Los cuatro SHA-256 deben ser hexadecimales lowercase de 64 caracteres.
2. `content_sha256` debe recomputar exactamente sobre `content` UTF-8.
3. El span debe ser entero, no booleano, `0 <= start <= end`.
4. Cada anchor debe ser internamente válido y el lineage debe ir de menor a
   mayor `source_block_index`, con niveles estrictamente crecientes.
5. Estado vacío: lineage vacío, anchor/title/path nulos.
6. Estado anclado: anchor igual al último lineage; `section_title` y
   `section_path` derivados exactamente del lineage.
7. El UUID debe recomputar exactamente a partir del contrato versionado.
8. Al validar contra el raw, todos los anchors deben resolver al heading exacto
   y el lineage debe ser el prefijo común de todos los bloques del span.

La base de datos replica los invariantes estructurales comprobables mediante
`CHECK`; el validador Python realiza las comprobaciones criptográficas y contra
el raw que SQL no puede reconstruir por sí solo.

## Seguridad y superficie de API

- RLS activado desde la creación.
- `PUBLIC`, `anon` y `authenticated` sin privilegios sobre tabla ni RPC.
- Acceso mínimo para `service_role`; no se crean políticas públicas.
- RPCs `SECURITY INVOKER`, con `search_path` vacío y objetos cualificados.
- La tabla shadow no se conecta al retriever productivo mediante variables o
  renames en esta fase.

## Índices y carga

La migración de esquema crea PK, unicidad, índices de claves foráneas, filtros y
FTS. El índice HNSW se construye solamente después de cargar y validar el shadow:
mantenerlo durante el bulk load añade coste de escritura y no aporta valor antes
del replay. El operador será `vector_cosine_ops`, igual que el retrieval actual.

## Reutilización segura para reducir coste

Una fila de `chunks_v2` puede donar `context` y `embedding` únicamente si
coinciden exactamente dentro del mismo `extraction_sha256`:

- `content`, `section_title`, `section_path`, `page_number` y metadata usada por
  el retrieval;
- `context` no nulo;
- dimensión/modelo/versión de embedding congelados;
- hash exacto de `context + "\\n\\n" + content`.

Si cualquiera difiere, se regenera contexto y embedding. La reutilización es
una optimización content-addressed, nunca un fallback aproximado. Su porcentaje
y el coste residual deben medirse antes de autorizar llamadas pagadas.

## Secuencia de gates

1. **M0 — contrato local:** validador, escritor puro y SQL estático; cero red.
2. **M1 — rematerialización local:** 1.068 raws de desarrollo + 12 raws
   independientes; cero fallos, determinismo byte-lógico y conservación de
   content streams.
3. **M2 — plan de reuso:** diff read-only contra `chunks_v2`; presupuesto para
   contexto/embedding residual. No escritura.
4. **M3 — DB shadow:** aplicar esquema y cargar en `chunks_v3` solamente tras GO
   explícito; verificar conteos, hashes, RLS, advisors y rollback.
5. **M4 — índice y funnel:** construir HNSW, ejecutar retrieval → rerank →
   synthesis y regresión protegida contra `chunks_v2`.
6. **M5 — serving:** solo con convergencia en métricas prioritarias y sin
   regresiones core; switch default-off y reversible.

## Rollback

Antes de serving, rollback es `DROP TABLE/FUNCTION` de objetos v3: `chunks_v2`
nunca se toca. Después de cualquier futuro switch, el rollback debe ser una
variable/alias versionado que vuelva a `chunks_v2`; no se permiten renames que
destruyan la tabla anterior durante la ventana de observación.

## No autorizado por S117-M0/M1

- Aplicar SQL a Supabase.
- Leer o escribir la DB para estimar reutilización.
- Generar contexto o embeddings pagados.
- Construir HNSW remoto, reindexar, servir o desplegar.
- Recategorizar facts o afirmar mejora de `% OK`.
