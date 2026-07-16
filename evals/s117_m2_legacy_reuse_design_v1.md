# S117 M2 — diseño de auditoría read-only de reutilización legacy

## Decisión y alcance

M2 compara la generación estructural local `chunks_v3` contra el `chunks_v2`
vivo para medir qué contexto y embeddings son **candidatos** a reutilización
exacta. No modifica la base, no descarga vectores, no llama a modelos y no
convierte candidatos en filas cargables. `legacy_v2_reuse` preserva un baseline;
no demuestra criptográficamente qué modelo produjo el contexto o el vector.

M2 tampoco afirma una mejora de retrieval ni de `% OK`. Su salida es un mapa de
coste y riesgo para M2.5.

## Snapshot remoto y seguridad

La lectura usa una sola conexión PostgreSQL y una sola transacción declarada
`READ ONLY`, con `statement_timeout`, `lock_timeout` y cursor server-side. Solo
se permiten `SELECT`, `SET TRANSACTION READ ONLY` y `SET LOCAL`; el auditor
rechaza cualquier otro verbo SQL en su contrato estático.

Se leen exclusivamente:

- `documents`: `id`, `source_pdf_sha256`, `status`;
- `chunks_v2`: identidad estructural, metadata, `context`, relaciones legacy y
  dos derivados escalares del vector: presencia y `vector_dims(embedding)`.

El vector completo y `search_vector` quedan fuera. Se procesa en streaming y se
sella un manifest canónico de las filas observadas, pero el artefacto final solo
guarda hashes, conteos y agregados, nunca contenido, contexto, credenciales ni
DSN.

La conexión siempre termina en `ROLLBACK`, incluso tras éxito.

## Población local comparable

La base estructural es exactamente el raw store y el materializador sellados en
S117. Para reproducir la intención del pipeline actual sin modelos:

1. se reejecuta el chunker;
2. se detecta idioma por chunk;
3. `unknown` hereda el dominante del documento;
4. `fr|it|pt|de` queda `policy_excluded` y no requiere enriquecimiento;
5. sobre los chunks elegibles se reejecuta B5 con la misma muestra de los cuatro
   primeros chunks conservados y las mismas reglas de fabricantes/sidecars.

La identidad estructural S117 no se renumera ni cambia. El ordinal renumerado de
la pipeline v2 es solo diagnóstico y nunca criterio de match.

## Funnel de matching

Los surrogates `parent_id IS NOT NULL` se contabilizan, pero no son donors.
`duplicate_of` no descalifica un donor estructural; su traducción a IDs v3 es un
gate posterior.

Para cada fila local elegible se aplican etapas acumulativas:

1. **extraction hit**: existe al menos un donor base con el mismo PDF SHA;
2. **content hit**: contenido byte-idéntico UTF-8;
3. **structure hit**: además coinciden `section_title`, `section_path`, página,
   flags de diagrama y `confidence` como IEEE-754 float32 canónico;
4. **metadata hit**: además coinciden `language`, `source_file`,
   `product_model`, `manufacturer`, `distributor`, `protocol`, `doc_type`,
   `category` y `content_type`;
5. **document binding hit**: `document_id` apunta al único documento cuyo
   `source_pdf_sha256` es exactamente el SHA de extracción;
6. **unique donor**: queda exactamente una fila v2. No hay tie-break por ordinal
   ni filename; la ambigüedad falla cerrada.

Las etapas se reportan por separado. Así, un fallo de metadata no se presenta
como fallo de chunking y una ausencia de contexto no se presenta como miss
estructural.

## Candidatos de contexto y embedding

Un `context_reuse_candidate` exige donor único y contexto no vacío. Se calculan:

- `context_sha256` del output almacenado;
- `context_input_sha256` de la petición efectiva reconstruida con documento y
  chunk truncados, instrucción, modelo y límites congelados;
- hash de la implementación del contextualizer.

El receipt prueba la reconstrucción actual, no la ejecución histórica de Haiku;
por eso el origen sigue siendo `legacy_v2_reuse`.

Un `embedding_reuse_candidate` exige además contexto reutilizable, embedding no
nulo y dimensión 1024. `embedding_input_sha256` incluye texto efectivo truncado,
provider, modelo, `input_type=document`, dimensión y límites. El vector no se
descarga en M2 y, por tanto, **no** existe todavía `embedding_sha256`; M2.5 debe
leerlo, convertirlo a float32 big-endian, hashearlo y verificarlo antes de carga.

Si el contexto falta o debe regenerarse, su embedding también debe regenerarse.

## Taxonomía de resultado

Cada fila local cae exactamente en una hoja principal:

- `policy_excluded`;
- `no_extraction_donor`;
- `content_miss`;
- `structure_miss`;
- `metadata_miss`;
- `document_binding_miss`;
- `ambiguous_donor`;
- `unique_donor_context_missing`;
- `unique_donor_embedding_missing_or_wrong_dim`;
- `legacy_context_and_embedding_candidate`.

Se añaden cortes no excluyentes por documento, fabricante y canonical/duplicate.
No se persisten textos de ejemplo; los diagnósticos usan hashes e IDs.

## Gate M2

GO exige:

- transacción remota verificada `READ ONLY` y cierre por rollback;
- manifests local/remoto deterministas;
- snapshot S117 y fuentes auxiliares sin drift;
- cada fila local en una única hoja;
- monotonicidad del funnel;
- cero vectores descargados, cero modelos, cero escrituras;
- repetición local del análisis sobre el snapshot sellado con resultado idéntico;
- revisión adversarial de definiciones y de cualquier claim de reutilización.

GO autoriza únicamente diseñar M2.5. No autoriza schema apply, carga, generación
de contexto, embeddings, HNSW, serving, deploy ni reclasificación de facts.
