# S117 M2.7 — cierre contractual v3

Este documento supersede M2.7 v2 únicamente en los puntos siguientes. Los
cuatro blockers corregidos en v2 y todas las prohibiciones M2.7 siguen
vigentes. M2.7 permanece local: cero DB, red, modelos, vectores, schema apply,
load, serving o deploy.

## 1. Fidelity automática: solo equivalencia *surface-safe*

`NFKC`, `casefold` y shingles se pueden usar para descubrir candidatos, pero
nunca para cerrar fidelity automáticamente.

El único cierre automático de una fila `no_content_donor` es una ocurrencia
única de la secuencia local dentro del stream documental de donors después de
normalizar **exclusivamente whitespace Unicode** a un espacio y colapsar runs.
No se normalizan case, puntuación, signos, caracteres Unicode, super/subíndices
ni grafías de unidades o códigos. La evidencia registra:

- SHA-256 del contenido local raw y de la secuencia donor raw;
- SHA-256 de ambas formas whitespace-only;
- número de ocurrencias surface-safe en el documento;
- secuencia y SHA-256 de tokens técnicos protegidos en ambos lados.

Tokens protegidos incluyen como mínimo números, decimales, rangos, unidades,
códigos alfanuméricos case-sensitive, operadores, signos, símbolos técnicos y
super/subíndices. Un cierre automático exige igualdad exacta, incluido case y
Unicode, de la secuencia completa surface-safe y de tokens protegidos. Una
diferencia que no sea exclusivamente whitespace, múltiples ocurrencias o
múltiples spans candidatos produce una task de adjudicación; nunca
`exact_resegmentation_evidence`.

`structure_only_delta` solo puede cerrar automáticamente si el contenido raw
es byte-equivalent UTF-8, la provenance payload y la lineage resuelven contra
el raw store, y el receipt enumera exactamente los campos estructurales que
difieren. No autoriza reuse ni afirma mejora semántica.

## 2. Contrato de adjudicación versionado y separado

La primera ejecución genera un `task_manifest` determinista e inmutable. No
consume decisiones ad hoc. Cada task incluye:

- `schema=s117_m27_fidelity_task_v1`, `local_row_id`, cohorte y extraction SHA;
- SHA-256 del receipt de comparación y de la evidencia raw;
- IDs/ordinales donor, spans y snippets acotados de ambos lados;
- tokens protegidos, candidate method y razón por la que no cerró automático.

Una ejecución posterior solo puede importar un archivo de adjudicación cuyo
path y SHA-256 estén congelados en una prereg nueva, y cuyo
`task_manifest_sha256` coincida. Su schema es
`s117_m27_fidelity_adjudication_v1`, versión 1, con una sola decisión por
`local_row_id` y estos campos obligatorios:

```yaml
reviewer:
  method: human_expert | named_adversarial_model
  identity: <non-empty>
  provider: <non-empty-or-null>
  model: <non-empty-or-null>
rows:
  - local_row_id: <uuid>
    comparison_receipt_sha256: <sha256>
    raw_evidence_sha256: <sha256>
    rubric:
      negation_changed: false
      condition_or_scope_changed: false
      warning_or_safety_changed: false
      procedure_order_changed: false
      reference_target_changed: false
      protected_technical_tokens_changed: false
    verdict: benign | material
    rationale: <non-empty>
```

`benign` solo es válido si los seis flags son false. Cualquier flag true exige
`material`. Filas duplicadas, evidence/hash mismatch, schema incompleto,
veredictos contradictorios o un receipt no congelado se convierten en
`unresolved_requires_adjudication`; cualquier decisión `material` se convierte
en `material_fidelity_risk`. Los receipts importados no alteran el task
manifest ni el resultado de candidate discovery.

`LOCAL_READINESS_GO` conserva la regla v2: 590/590 cerradas por evidencia
surface-safe/estructura válida o adjudicación congelada; cero unresolved y
cero material risk. Projected sigue siendo diagnóstico.

## 3. Política SQL de inputs cerrada y común

Las dos RPC usan cap `200` y fail-closed mediante SQLSTATE `22023` con códigos
estables. No hay semántica accidental:

- `match_count|match_limit`: INTEGER no NULL en `[1, 200]`; si no,
  `M27_INVALID_LIMIT`;
- `filter_product|filter_category|filter_manufacturer`: NULL significa filtro
  ausente; si no es NULL, `btrim(value)` debe ser no vacío y se usa ese valor
  trimmed; si no, `M27_INVALID_FILTER`;
- vector: `query_embedding` no NULL; si no, `M27_INVALID_QUERY`;
- vector: `match_threshold` no NULL, distinto de NaN y dentro de `[-1, 1]`;
  si no, `M27_INVALID_THRESHOLD`; la comparación de admisión sigue siendo
  estricta `similarity > threshold`;
- FTS: `search_query` no NULL y `btrim(search_query)` no vacío; si no,
  `M27_INVALID_QUERY`; el tsquery se calcula una vez desde la forma trimmed.

Ambos canales comparten exactamente limit cap, normalización de filtros,
códigos de error y predicados de policy/canonicalidad/materialization/document.
No admiten `target_materialization_id`.

La especificación revoca primero el SELECT table-level existente de
`service_role` antes de conceder SELECT columnar. INSERT permanece separado.
Como precondición de ejecución futura, un guard verificará que `service_role`
existe y tiene `rolbypassrls=true`; si no, aborta con
`M27_SERVICE_ROLE_RLS_CONTRACT`. M2.7 solo testea estáticamente ese guard: no
afirma ejecutabilidad DB hasta un gate posterior con Postgres/Supabase real.

## 4. Presupuesto: distinguir exactos, proxies y retries

Antes de generar contextos son exactos únicamente: 8.493 llamadas lógicas,
405 documentos, 8.088 llamadas posteriores, límites de caracteres derivados
de truncación y el techo de output solicitado. HTTP retries no están incluidos
y solo se conocen por receipts del SDK.

Todo cálculo `ceil(chars/4)`, sus escenarios de cache y cualquier USD derivado
se etiqueta `planning_proxy`, nunca token bound ni cost bound. Para embeddings,
los rangos char4 y USD Voyage son `planning_proxy_low/high`; el batch manifest,
tokens facturados, requests HTTP y coste exactos solo existen tras generar los
contextos y conservar usage receipts. No se asume free tier.
