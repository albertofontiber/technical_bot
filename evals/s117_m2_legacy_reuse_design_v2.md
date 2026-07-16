# S117 M2 — diseño v2 de auditoría read-only de reutilización legacy

Esta versión sustituye íntegramente a `s117_m2_legacy_reuse_design_v1.md`.

## Decisión y alcance

M2 compara la generación estructural local `chunks_v3` contra el `chunks_v2`
vivo para medir qué contexto y embeddings son **candidatos** a reutilización
exacta. No modifica la base, no descarga vectores, no llama a modelos y no
convierte candidatos en filas cargables. `legacy_v2_reuse` preserva un baseline;
no demuestra criptográficamente qué modelo produjo el contexto o el vector.

M2 tampoco afirma una mejora de retrieval ni de `% OK`. Su salida es un mapa de
coste y riesgo para M2.5.

## Snapshot remoto consistente, corto y reproducible

La captura usa una sola conexión PostgreSQL y una sola transacción
`REPEATABLE READ, READ ONLY`, con `statement_timeout`, `lock_timeout` y cursor
server-side. Solo se permiten `SELECT`, `SET TRANSACTION ... READ ONLY` y
`SET LOCAL`; el auditor y sus tests rechazan cualquier otro verbo SQL.

Se leen exclusivamente:

- `documents`: `id`, `source_pdf_sha256`, `status`;
- `chunks_v2`: identidad estructural, metadata, `context`, relaciones legacy y
  dos derivados escalares del vector: presencia y `vector_dims(embedding)`.

El vector completo y `search_vector` quedan fuera. Las dos queries ordenan por
UUID y escriben un snapshot JSONL canónico comprimido, sin DSN ni credenciales,
en `tmp/s117_m2/`; el artefacto de `evals/` solo conserva hashes y agregados.
El gzip se genera con `mtime=0` y se sellan tanto los bytes JSONL canónicos como
los bytes comprimidos.

En cuanto termina el streaming se ejecuta `ROLLBACK` y se cierra la conexión.
Todo el matching, hashing y replay ocurre después, contra el snapshot local. No
se mantiene una transacción abierta durante cómputo local ni revisión.

## Población local comparable

La base estructural es exactamente el raw store y el materializador sellados en
S117. Para reproducir la intención del pipeline actual sin modelos:

1. se reejecuta el chunker;
2. se detecta idioma por chunk;
3. `unknown` hereda el dominante del documento;
4. `fr|it|pt|de` queda `policy_excluded` y no requiere enriquecimiento;
5. sobre los chunks elegibles se reejecuta B5 con la misma muestra de los cuatro
   primeros chunks conservados y las mismas reglas de fabricantes.

La identidad estructural S117 no se renumera ni cambia. El ordinal renumerado de
la pipeline v2 es solo diagnóstico y nunca criterio de match. Se sellan versión
de Python, Lingua y psycopg2, hashes de código/config y valores efectivos del
embedder (`provider`, `model`, dimensión, input type y límites).

El store congelado contiene cero rutas de canal portal; si el replay detecta una,
falla cerrado. Así no existe una dependencia de sidecars externos sin sellar.

## Elegibilidad y binding documental

Los surrogates `parent_id IS NOT NULL` se contabilizan, pero no son donors.
`duplicate_of` no descalifica un donor estructural; su traducción a IDs v3 es un
gate posterior.

Cada target v3 productivo debe resolver su `extraction_sha256` a exactamente un
`documents.id` cuyo `source_pdf_sha256` sea el SHA exacto de 64 hex. Ausencia,
placeholder o ambigüedad produce `target_document_unresolved` y bloquea reuse.

El `document_id` del donor legacy se audita por separado. Que esté vacío o
desactualizado no obliga por sí solo a regenerar contexto/vector si el target
puede enlazarse exactamente y todos los inputs de enriquecimiento coinciden. Se
reporta como `donor_document_binding_drift`, nunca se copia al target.

## Funnel de matching

Para cada fila local elegible y con target documental resuelto se aplican etapas
acumulativas:

1. **extraction hit**: existe al menos un donor base con el mismo PDF SHA;
2. **content hit**: contenido byte-idéntico UTF-8;
3. **structure hit**: además coinciden `section_title`, `section_path`, página,
   flags de diagrama y `confidence` como IEEE-754 float32 canónico;
4. **metadata hit**: además coinciden `language`, `source_file`,
   `product_model`, `manufacturer`, `distributor`, `protocol`, `doc_type`,
   `category` y `content_type`;
5. **unique donor**: queda exactamente una fila v2. No hay tie-break por ordinal
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
El resultado presenta dos cotas, no una falsa cifra única:

- **residual estricto**: exige metadata exacta y todos los gates anteriores;
- **techo estructural**: cuántos podrían salvarse si la reconciliación explícita
  de metadata adopta el donor sin alterar el input contextual.

La segunda cifra nunca autoriza reuse; solo dimensiona la oportunidad de una
decisión de metadata en M2.5.

## Taxonomía terminal

Cada fila local cae exactamente en una hoja principal:

- `policy_excluded`;
- `target_document_unresolved`;
- `no_extraction_donor`;
- `content_miss`;
- `structure_miss`;
- `metadata_miss`;
- `ambiguous_donor`;
- `unique_donor_context_missing`;
- `unique_donor_embedding_missing_or_wrong_dim`;
- `legacy_context_and_embedding_candidate`.

Se añaden cortes no excluyentes por documento, fabricante,
canonical/duplicate y `donor_document_binding_drift`. No se persisten textos de
ejemplo en `evals/`; los diagnósticos usan hashes e IDs.

## Obligación de serving derivada

Las filas `policy_excluded` pueden conservarse como evidencia estructural, pero
**no pueden ser servidas**. El SQL shadow actual genera `search_vector` para toda
fila y la RPC FTS no filtra idioma/elegibilidad. Por tanto, incluso con M2 GO,
M3 queda bloqueado hasta que M2.5 elija y pruebe uno de estos contratos:

1. no cargar filas excluidas; o
2. persistir `retrieval_eligible` y filtrarlo en vector, FTS e índices.

No basta con dejar el embedding a `NULL`, porque FTS seguiría encontrándolas.

## Gate M2

GO exige:

- transacción remota `REPEATABLE READ, READ ONLY` demostrada y rollback antes
  del análisis;
- manifests local/remoto deterministas y snapshot comprimido sellado;
- snapshot S117, runtime y fuentes auxiliares sin drift;
- cada fila local en una única hoja y funnel monótono;
- cero vectores descargados, cero modelos, cero escrituras;
- replay local desde el snapshot sellado con resultado idéntico;
- revisión adversarial de definiciones y claims.

GO autoriza únicamente diseñar M2.5. No autoriza schema apply, carga, generación
de contexto, embeddings, HNSW, serving, deploy ni reclasificación de facts.
