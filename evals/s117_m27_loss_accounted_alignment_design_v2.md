# S117 M2.7B — cierre contractual v2

Estado: **borrador corregido para revisión adversarial; no autoriza
implementación**. Supersede M2.7B v1 únicamente en los puntos siguientes.

## 1. Identidad y orden de página

Cada bloque sella dos campos distintos:

- `source_page_ordinal`: posición entera, cero-based, de la ocurrencia de página
  en `result.pages`;
- `page`: label del raw store, que puede repetirse y no define identidad.

El orden canónico de bloques es
`(source_page_ordinal, source_block_index)` y el de chunks es `chunk_index`.
First/last se calcula dentro de una sola `source_page_ordinal`, nunca agrupando
por el label `page`. Seeds solo perturban enumeración de entrada; todo stream,
span y boundary se calcula después de restaurar esos órdenes canónicos.

La única regla inicial queda cerrada así:

```yaml
rule_id: standalone_numeric_page_boundary_exact_v1
predicate:
  block.kind: exactly paragraph
  block.page_type: integer and not boolean
  block.page_range: 1..9999 inclusive
  block.text: strip(text) == str(page), ASCII exact
  source_page_position: first or last block of source_page_ordinal
  coverage: zero covering v3 chunks
```

Esto rechaza `None`, booleanos, strings, cero, negativos, leading zeros, signos,
unidades y cualquier número que solo sea numéricamente equivalente. El receipt
conserva `page`, su tipo, ordinal, posición y todos los predicados.

El caso standalone `"24"` en page integer `24` y boundary coincide
deliberadamente con la regla. El audit lo registra como riesgo residual: la
regla prueba forma/posición de número de página, no demuestra semánticamente que
el valor sea irrelevante. No se puede presentar match como prueba de ruido.

## 2. Cierre de población

Antes de clasificar bloques se exige:

- conjunto exacto de 1.068 `extraction_sha256` únicos, igual al manifest de
  generación/raw store congelado;
- exactamente 31.212 filas v3, IDs y `(extraction_sha256, chunk_index)` únicos;
- ordinals `chunk_index` contiguos desde cero por documento;
- `source_block_index` contiguos desde cero por documento;
- todos los spans dentro del rango de bloques de su documento;
- materializer y validator independientes iguales fila a fila.

Eliminar o duplicar un documento/fila es contract NO-GO antes de calcular
porcentajes o streams.

## 3. Taxonomía cerrada y documento no vacío

Las únicas disposiciones siguen siendo:

- `covered_by_v3`
- `authorized_exclusion`
- `unruled_loss`

`rule_matched_but_retained=true` es solo un flag diagnóstico permitido en una
fila `covered_by_v3`; nunca una cuarta disposición y nunca se resta del stream.

Además de los gates v1 se exige `document_nonempty_after_exclusions`: si el raw
tiene al menos un bloque, debe quedar al menos un bloque `covered_by_v3` y el
stream v3 normalizado debe ser no vacío. Un documento compuesto enteramente por
matches de la regla es NO-GO aunque la resta coincida con un stream vacío.

## 4. Tests adicionales obligatorios

- `page=None`, boolean, string, cero, negativo y leading zeros;
- labels page repetidos en dos `source_page_ordinal` distintos;
- documento raw no vacío íntegramente excluido;
- eliminación y duplicación de un extraction del manifest;
- shuffle que intenta cambiar first/last;
- standalone `"24"` en page integer 24 y boundary, con el flag de riesgo
  residual explícito;
- `rule_matched_but_retained` permanece `covered_by_v3` y no se resta.

Todas las demás prohibiciones, igualdad de streams y límites de autoridad de v1
permanecen vigentes.
