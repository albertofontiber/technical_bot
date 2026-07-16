# S117 M2.7B — alineación con pérdidas contabilizadas v1

Estado: **borrador para revisión adversarial; no autoriza implementación ni
cambios del chunker**.

## 1. Problema y autoridad

M2.7A demostró que el stream v3 omite dos bloques raw (`39`, `40`) porque la
limpieza descarta chunks con `_meaningful_len < NOISE_CHARS`. Aunque en ese caso
son números de página, aceptar toda la heurística como ruido podría ocultar
códigos, estados, tensiones o referencias técnicas cortas.

M2.7B audita **los 1.068 documentos y 31.212 chunks locales**, no solo los 18
documentos ni la task que descubrió el problema. Su autoridad sigue limitada al
raw store JSON; no prueba fidelidad al PDF/visual o a LlamaParse.

Este gate no adjudica tasks, no cambia policy/chunks y no autoriza M3.

## 2. Ledger completo de cobertura por bloque

Para cada documento se regeneran las filas v3 con el chunker/materializer y el
validator congelados. Cada bloque raw obtiene exactamente una disposición:

- `covered_by_v3`: su índice está incluido en el span de al menos un chunk v3;
- `authorized_exclusion`: está descubierto y satisface una regla congelada;
- `unruled_loss`: está descubierto y no satisface ninguna regla congelada.

Los spans compartidos por splits oversized son válidos: un bloque queda
`covered_by_v3` aunque varios chunks lo referencien. No se atribuye el bloque a
un target concreto. IDs de chunks que lo cubren, bloques vecinos, texto raw,
kind, page, lineage y hashes se conservan en el receipt.

Además de la cobertura estructural, se construyen dos streams ordenados con
serialización exacta `"\n\n".join(...)` y normalización exclusiva de whitespace:

1. raw completo;
2. raw menos únicamente los bloques `authorized_exclusion`.

El segundo debe ser exactamente igual al stream v3. Esta igualdad detecta
omisión parcial, duplicación, reorder o cambios de texto que los spans por sí
solos no detectan. Similitud, NFKC, casefold y edición aproximada están
prohibidos para cerrar el gate.

## 3. Registry inicial congelado y de alta precisión

La primera ejecución contiene una sola regla; no puede añadir reglas después de
ver los resultados:

```yaml
rule_id: standalone_numeric_page_boundary_exact_v1
predicate:
  block.kind: paragraph
  block.text: ASCII digits only after strip, 1..4 digits
  numeric_value: exactly equals block.page
  page_position: first or last raw block of that same page
  coverage: block is not covered by any v3 span
```

Todos los predicados y su orden se registran. La regla no admite manufacturer,
modelo, documento, UUID, filename ni literales observados como `39`/`40`.
Tampoco admite offsets ±1, números romanos, rangos, signos, unidades o texto
acompañante. Es preferible dejar un caso `unruled_loss` que ampliar la regla sin
un gate corpus-wide independiente.

Un bloque que cumple la forma pero está cubierto se registra como
`rule_matched_but_retained`; nunca se resta dos veces.

## 4. Gates y claims

- `COVERAGE_LEDGER_GO`: todos los bloques de los 1.068 documentos aparecen una
  vez en el ledger y todos los receipts/manifests recomputan.
- `LOSS_POLICY_GO`: cero `unruled_loss`.
- `LOSS_ACCOUNTED_ALIGNMENT_GO`: ambos anteriores y, en todos los documentos,
  `raw − authorized_exclusions == v3` bajo whitespace-only.

Un GO significa únicamente que toda pérdida textual del raw store está
contabilizada por una regla congelada. No afirma que la regla mejore retrieval,
que los chunks sean óptimos ni que un fact pase a OK.

Si existe cualquier `unruled_loss`, el gate permanece NO-GO. El siguiente paso
será decidir corpus-wide si ese contenido debe retenerse o si merece una regla
general nueva, con positivos/negativos y prereg separada; nunca se edita la lista
de reglas dentro del resultado.

## 5. Obligación de producto tras un audit GO

El audit por sí solo no desbloquea M2.7A. Después de `LOSS_ACCOUNTED_ALIGNMENT_GO`
se debe implementar un ledger versionado obligatorio para cada nueva
materialización:

- una fila por bloque excluido con `rule_id`, rule/implementation hashes,
  predicados, vecinos y raw block receipt;
- coverage manifest que pruebe que cada bloque está retenido o excluido una sola
  vez;
- fail-closed si aparece un drop sin regla;
- sin insertar los page-number blocks como chunks recuperables;
- tests con manuales/fabricantes no usados para definir la regla.

Solo después se rematerializa localmente, se repiten dos seeds M2.7A y se exige
alignment GO antes de adjudicar `acd5058d…`.

## 6. Ejecución barata y determinista

1. Runner local sobre el raw store congelado y snapshot/materialización local.
2. Dos seeds que perturban orden de documentos/bloques/rows y ordenan todas las
   salidas contractuales.
3. Identidad byte a byte, logical hash y manifests recomputables.
4. Cero red, modelos, DB, embeddings o env reads.
5. Tests focalizados y regresión completa.

Casos mínimos de test:

- page number exacto en primer y último bloque;
- número igual a page pero en posición interior;
- número distinto de page;
- `24 V`, `E01`, `1-2`, heading y table;
- bloque cubierto que también parece número de página;
- pérdida multi-bloque y fronteras;
- párrafo/lista oversized compartido por varios chunks;
- reorder, duplicación y omisión parcial;
- referencias y receipts manipulados con hashes bien formados.

## 7. Criterios adversariales

La revisión debe intentar demostrar que:

- el registry fue adaptado a los dos tokens observados;
- un valor técnico corto puede ser autorizado;
- un span amplio puede ocultar un hueco interno;
- un bloque puede quedar cubierto y excluido simultáneamente;
- la resta cambia orden o whitespace más allá del contrato;
- un documento/task/fabricante puede seleccionar reglas especiales;
- audit GO puede presentarse erróneamente como autoridad de chunker/M3.
