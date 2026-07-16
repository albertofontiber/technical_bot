# S117 M2.7C — addendum adversarial v2

Este addendum supersede v1 en identidad, autoridad, reconciliación del delta y
proyección de retrieval. Continúa siendo diseño sin autorización de cambio,
carga, serving, modelos, red, DB, embeddings, M3 ni facts `OK`.

## 1. Autoridad exacta

El probe solo afirma fidelidad respecto de la **superficie ordenada de bloques
parseados del raw store**. La superficie se define con la misma normalización
whitespace-only congelada en M2.7B.

No afirma igualdad byte a byte con Markdown, JSON o PDF; tampoco afirma
fidelidad visual o semántica del extractor. Esas garantías requieren capas
distintas y quedan fuera de M2.7C.

El invariante corregido es: cada identidad
`(extraction_sha256, source_block_index)` del conjunto exacto de 333.161 bloques
parseados debe estar cubierta por al menos un span treatment; la superficie
ordenada de las filas treatment debe ser igual a la superficie ordenada de los
bloques raw, sin exclusiones.

## 2. Identidad del contrafactual

El treatment nunca reutiliza ni presenta como propia la identidad de la
materialización o del chunker baseline. Su contrato diagnóstico se calcula
canónicamente desde:

```text
{
  base_chunker_sha256,
  override: {
    symbol: "src.reingest.chunk.NOISE_CHARS",
    baseline: 15,
    treatment: 0,
    scope: "single_call_with_finally_restore"
  },
  runner_sha256
}
```

El SHA de ese payload es `treatment_contract_sha256`. IDs de filas treatment,
si se necesitan, pertenecen a un namespace diagnóstico separado y se derivan
solo de `{treatment_contract_sha256, extraction_sha256, ordinal, fingerprint}`.
No se llama a `materialize_raw_record` con el SHA baseline mientras el override
esté activo. Ninguna fila treatment es loadable.

El runner debe comprobar antes y después de cada llamada que `NOISE_CHARS ==
15`, instalar únicamente `0`, restaurar en `finally` y fallar si se observa
cualquier otro cambio global.

## 3. Reconciliación total, no supuesto de superset de filas

Desactivar el descarte puede cambiar packing, merges, ordinales y spans. La
comparación se hace por fingerprint estable independiente de ID y ordinal:

```text
{
  content_surface_sha256,
  source_block_start,
  source_block_end,
  section_lineage,
  section_title,
  section_path,
  page_number,
  is_flow_diagram,
  has_diagram,
  confidence
}
```

Por documento se publican cuatro conjuntos cerrados:

- `unchanged`: fingerprint completo presente en baseline y treatment;
- `removed`: fingerprint baseline sin pareja treatment;
- `added`: fingerprint treatment sin pareja baseline;
- `modified`: reconciliación diagnóstica de removed/added que comparten al menos
  una identidad de bloque raw, sin convertirla en igualdad.

`modified` no elimina las filas de `removed` o `added`; es un crosswalk
receipted para explicar cambios de packing. Duplicados de un fingerprint se
preservan como multiset y se emparejan por orden canónico.

## 4. Gates exactos de cobertura y estabilidad

Baseline obligatorio:

- 1.068 documentos;
- 31.212 filas;
- 333.161 bloques raw;
- manifest de filas exactamente igual al development result congelado;
- 333.061 identidades cubiertas y las mismas 100 identidades no cubiertas que
  `loss_rows` M2.7B;
- 13 de esas 100 autorizadas y 87 no regladas, sin reinterpretarlas.

Treatment obligatorio:

- 1.068 documentos y las mismas 333.161 identidades raw;
- 333.161/333.161 identidades cubiertas;
- cero exclusiones y cero pérdidas;
- superficie treatment igual a la superficie completa raw en cada documento;
- ningún span fuera de rango, reorder o duplicación de superficie;
- toda identidad cubierta baseline continúa cubierta treatment;
- diferencia de cobertura exactamente igual a las 100 identidades congeladas.

Estabilidad:

- los 1.041 documentos sin ninguna de las 100 identidades deben tener multiset
  de fingerprints completos idéntico entre baseline y treatment;
- los otros 27 documentos pueden cambiar filas únicamente con un crosswalk
  completo `unchanged/removed/added/modified`;
- casos vacíos, bloques oversized y spans compartidos permanecen válidos.

El número de filas treatment es una observación, no un criterio post hoc.

## 5. Inputs y freeze del probe

La preregistración debe hash-bindear:

- raw generation manifest y development result;
- design v1 y este addendum;
- runner y tests;
- `chunk.py`, `chunk_provenance.py` y validator independiente;
- prereg/gate M2.7B, sus dos seeds y el manifest exacto de las 100 identidades;
- snapshot fuente y sidecar roots seleccionados.

Se ejecutan seeds 1 y 2, perturbando orden de documentos y filas antes de
restaurar orden canónico. Deben producir bytes y payload lógico idénticos. No
se permite leer `.env`, usar red, DB, modelos, context generation ni embeddings.

Estados separados:

- `CONTRACT_INTEGRITY`;
- `BASELINE_REPLAY`;
- `TREATMENT_LOSSLESS`;
- `DELTA_ACCOUNTED`.

Todos deben ser `GO` para considerar el probe informativo. Aun así facts
movidos a `OK = 0` y `M3 = BLOCKED`.

## 6. Capa C corregida

No se añade `layout_only` todavía. La opción preferida es reutilizar la clase
final existente `register_only` y añadir un eje ortogonal
`retrieval_policy_reason`, por ejemplo `structural_layout_only`, con payload y
receipt persistidos y recalculables. Guardar solo el SHA del receipt es
insuficiente.

Para cualquier fila no elegible deben ser `NULL` y estar protegidos por
constraints: `context`, embedding y `search_vector`. Ambas funciones de
retrieval deben seguir leyendo exclusivamente la vista elegible.

Esta fase requiere otra preregistración y controles negativos. Cualquier
ambigüedad, texto alfanumérico corto, código, título, unidad, operador o símbolo
técnico se conserva y no se clasifica como layout por defecto. Ninguna decisión
de Capa C forma parte del probe M2.7C.
