# S117 M2.6 — contrato local de elegibilidad y validación independiente v1

## Alcance

M2.6 separa dos decisiones que M2/M2.5 solo proyectaban:

1. qué filas pueden entrar en los canales vectorial y FTS;
2. qué enriquecimiento legacy puede reutilizarse con evidencia independiente.

El gate es local y candidate-only. No lee DB, `.env` ni payloads vectoriales,
no llama modelos y no modifica schema, carga o serving. M3 permanece bloqueado.

## Dos universos distintos

### Load binding

Una fila solo puede cargarse en el schema actual si su raw resuelve a un
`document_id` exacto. M2.5 observa, sobre 31.212 filas locales:

- 29.791 ligadas a documentos activos;
- 523 ligadas a documentos no activos;
- 898 sin binding documental cargable.

Las 898 no se reinterpretan como exclusiones de retrieval: son un bloqueo
upstream de carga. No pueden insertarse con un `document_id` inventado o nulo.

### Retrieval

Para una fila cargable, `retrieval_eligible` representa la parte estática de la
política común a vector y FTS:

- el pipeline de idioma la considera indexable;
- no es una fila duplicada (`duplicate_of IS NULL`).

Se acompaña de `retrieval_exclusion_reason`, con precedencia exhaustiva:

1. `policy_register_only`;
2. `policy_unsupported_language`;
3. `duplicate`;
4. `null` cuando `retrieval_eligible=true`.

Un `CHECK` debe exigir la equivalencia exacta entre booleano, reason y
`duplicate_of`. No hay excepciones por fabricante, modelo, fichero o SHA.

El estado del documento es dinámico y no se congela dentro del booleano. La
returnability efectiva de ambos canales será:

`materialization active AND retrieval_eligible AND document active AND
document/extraction identity exact`, más el requisito específico del canal.

Vector añade `embedding IS NOT NULL`; FTS añade `search_vector` no nulo y match
de la consulta. Ambos RPCs deben hacer el mismo `JOIN documents` y el mismo
predicado común.

## Persistencia futura, no autorizada por M2.6

El sucesor versionado del schema deberá:

- añadir `retrieval_eligible BOOLEAN NOT NULL` y reason auditable;
- hacer que el trigger deje `search_vector=NULL` para filas no elegibles;
- usar índices parciales GIN/HNSW sobre filas elegibles canónicas;
- incluir el predicado común en `match_chunks_v3` y
  `search_chunks_text_v3`, no confiar en filtros de aplicación;
- validar conteos por reason antes de publicar una generación;
- exigir contexto/embedding nulos en filas excluidas por policy;
- conservar RLS, revocaciones explícitas y RPCs de retrieval
  `SECURITY INVOKER` con `search_path=''`.

La migración S117 actual permanece inmutable durante M2.6. Cualquier cambio se
hará en una versión sucesora y deberá probarse después en PostgreSQL+pgvector
desechable.

## Cohorte de reutilización

El input congelado son exactamente las 5.438 filas que M2.5 movió desde
binding documental a `legacy_context_and_embedding_candidate`. El runner debe
reconstruir esa cohorte desde raw + snapshot, no confiar solo en el agregado.
Congelará un receipt por par `(local_row_id, donor_chunk_id)` y un manifest.

El conteo 5.438 es una expectativa preregistrada del input. La distribución de
resultados independientes no se fija antes de observarla.

## Validación metadata-independent

La metadata usada por M2 para seleccionar un donor no puede autorizar su propia
reutilización. Para cada miembro de la cohorte se recalcula, sin manufacturer,
product, category, distributor, protocol, doc_type ni language:

1. mismo `extraction_sha256` exacto;
2. mismo contenido byte a byte;
3. misma estructura congelada: section title/path, página, flags de diagrama y
   confidence float32;
4. exactamente un donor estructural;
5. ese donor es el donor congelado por la cohorte;
6. `document_id` coincide con el binding activo exacto;
7. `duplicate_of IS NULL`.

Taxonomía de identidad fail-closed, en precedencia:

1. `donor_document_binding_mismatch`;
2. `donor_marked_duplicate`;
3. `metadata_required_for_donor_uniqueness`;
4. `independent_unique_structural_donor`.

Cualquier incoherencia distinta es un fallo interno, no un quinto terminal.

## Contexto y embedding son ejes separados

La identidad limpia no demuestra el enriquecimiento.

### Contexto

Autorizar contexto legacy requiere: texto no vacío, `context_sha256`, input
exacto del contextualizer, hash de implementación y prompt, modelo y límites
efectivos ligados criptográficamente al donor. Un hash del output por sí solo
no prueba cómo fue generado.

Si falta cualquiera, el terminal es `context_provenance_unavailable`; el
default operativo futuro es regenerar contexto.

### Embedding

Autorizar embedding legacy requiere: input SHA exacto, provider, modelo,
`input_type=document`, dimensión, SHA sobre float32 canónico y receipt que ligue
el vector al mismo modelo usado por queries. Presencia+1024 dimensiones no es
suficiente.

El snapshot congelado declara cero payloads, `vector_sha256=null` y
`historical_model_receipt=null`. Por tanto M2.6 local debe clasificar, nunca
autorizar silenciosamente, la ausencia de evidencia. El default futuro es
regenerar embeddings con el modelo vigente; pedir un snapshot adicional solo
tendría sentido si existe también provenance histórica verificable.

## Decisiones y semántica de gate

El resultado expone verdicts ortogonales:

- `eligibility_contract`: GO/NO_GO;
- `identity_validation`: GO/NO_GO por taxonomía e invariantes;
- `context_reuse`: GO solo para la intersección con provenance completa;
- `embedding_reuse`: GO solo para la intersección con provenance completa;
- `M3`: siempre BLOCKED dentro de M2.6.

Un GO de contrato o identidad no se presenta como GO de reuse. Si no existe
provenance completa, un resultado correcto puede cerrar M2.6 con contrato GO y
reuse NO_GO, reduciendo riesgo y fijando de forma explícita el trabajo a
regenerar.

## Gate de ejecución

- prereg antes del runner final;
- seeds `PYTHONHASHSEED=1,2`, outputs byte-idénticos;
- baseline M2.5 y sus 35+7 checks invariantes;
- 5.438 filas exactamente y taxonomías cerradas;
- cero policy-excluded dentro de la cohorte;
- cero reuse admitido sin todos los receipts;
- suite local completa;
- revisión adversarial antes y después de ejecutar.
