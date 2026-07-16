# S117 M2.7A — adjudicación *live* de fidelity v1

Estado: **borrador para revisión adversarial; no autoriza ejecución**.

Este gate trabaja únicamente las 21 tareas `live` congeladas por M2.7 v2. Las
50 tareas `projected` quedan fuera de alcance. Todo el trabajo es local y
determinista: cero red, modelos, embeddings, base de datos, schema apply, load,
serving o deploy.

## 1. Objetivo y no-objetivos

El objetivo es cerrar causalmente las 21 diferencias sin confundir tres cosas
distintas:

1. fidelidad del chunk v3 respecto al documento fuente;
2. diferencia semántica de v3 respecto a los chunks legacy;
3. elegibilidad del contenido para retrieval.

Una adición correcta que existe en el documento fuente puede ser una diferencia
semántica real frente a legacy, pero no es por ello una corrupción de fidelity.
Del mismo modo, contenido fiel a la fuente puede seguir siendo ruido o quedar
fuera de la política de retrieval. Ninguno de esos casos se etiquetará como
`benign` para forzar un GO.

Este gate no cambia chunks, language policy, retrieval, SQL ni serving. Tampoco
autoriza M3. Solo produce evidencia y una ruta causal por tarea.

## 2. Evidencia congelada y completitud

Inputs obligatorios:

- los dos seeds byte-identical de M2.7 v2;
- su `task_manifest`, receipts de comparación y receipts raw;
- el snapshot local congelado usado por M2.7 v2;
- el raw store local validado por los receipts M2.7 v2.

Las 14 tareas ya completas conservan exactamente sus receipts. Para cada una de
las 7 incompletas se materializa un receipt suplementario con **todos** los
chunks legacy de su documento (`extraction_sha256`), ordenados de forma estable,
incluidos IDs, ordinales, contenido UTF-8 y SHA-256. El receipt también enlaza el
contenido local completo, su provenance raw y los hashes de los receipts M2.7.

`evidence_complete=true` solo si se recomputan correctamente:

- manifest y SHA-256 de todos los donors legacy del documento;
- SHA-256 del contenido local y de cada donor;
- lineage/provenance local contra el receipt raw ya congelado;
- enlace uno-a-uno con la task, comparison receipt y raw receipt originales.

No se recorta evidencia para adjudicar. Snippets pueden existir para lectura,
pero nunca sustituyen el contenido completo en la decisión.

## 3. Dos ejes de adjudicación, no uno

Cada task recibe primero los seis flags semánticos ya congelados por M2.7 v3,
comparando v3 con legacy:

- `negation_changed`
- `condition_or_scope_changed`
- `warning_or_safety_changed`
- `procedure_order_changed`
- `reference_target_changed`
- `protected_technical_tokens_changed`

Después recibe una evaluación separada de fuente y policy:

```yaml
source_fidelity: faithful | unfaithful | unresolved
retrieval_policy: eligible | should_exclude | unresolved
root_cause:
  repeated_header_footer |
  multilingual_policy_leakage |
  table_serialization_delta |
  diagram_serialization_delta |
  contact_footer_noise |
  other
```

Reglas:

- `source_fidelity=faithful` exige que todo contenido local adjudicado pueda
  reconstruirse desde la evidencia raw/provenance congelada, sin alterar
  negaciones, condiciones, warnings, orden de procedimiento, referencias ni
  tokens técnicos respecto a la fuente.
- `source_fidelity=unfaithful` exige una contradicción concreta con la fuente;
  no se infiere únicamente porque legacy sea distinto.
- `retrieval_policy=should_exclude` debe citar una regla general versionada
  (por ejemplo idioma no soportado o clase de boilerplate), nunca un ID o texto
  específico de esta cohorte.
- Si no existe todavía una regla general aplicable, el valor es `unresolved`;
  no se inventa una excepción local.

## 4. Disposición contractual

La disposición se deriva mecánicamente:

| Condición | Disposición |
|---|---|
| evidencia incompleta o cualquier eje unresolved | `unresolved` |
| fuente unfaithful | `material_fidelity_risk` |
| fuente faithful, policy should_exclude | `upstream_policy_fix_required` |
| fuente faithful, policy eligible, seis flags false | `adjudicated_benign_delta` |
| fuente faithful, policy eligible, algún flag true | `source_faithful_semantic_delta` |

`source_faithful_semantic_delta` no es benigno ni error de fidelity: abre una
obligación downstream explícita para comprobar que retrieval, rerank y synthesis
manejan la información nueva sin regresiones. `upstream_policy_fix_required`
obliga a corregir una regla estructural y repetir M2.6/M2.7 antes de avanzar.

La anterior pareja `benign|material` de M2.7 v3 sigue siendo válida para
equivalencia legacy, pero no se usará para convertir automáticamente una
adición fiel a la fuente en `material_fidelity_risk`. Este documento propone una
extensión versionada precisamente para evitar esa conflación. Hasta que la
revisión adversarial la apruebe, M2.7 v2 permanece `LOCAL_READINESS_NO_GO`.

## 5. Umbrales de salida

El gate de adjudicación solo puede declarar:

- `EVIDENCE_GO`: 21/21 completas y todos los hashes/manifests recomputables;
- `FIDELITY_GO`: `EVIDENCE_GO`, cero `unresolved` y cero
  `material_fidelity_risk`;
- `POLICY_GO`: `FIDELITY_GO` y cero `upstream_policy_fix_required`;
- `DOWNSTREAM_CASCADE_REQUIRED`: número y IDs de
  `source_faithful_semantic_delta` mayor que cero.

M3 sigue bloqueado si `POLICY_GO` no se cumple. Si se cumple pero existen
semantic deltas fieles, el siguiente gate debe prerregistrar su cascada por las
etapas del funnel; no puede saltar directamente a contar facts como `OK`.

## 6. Ejecución barata y reproducible

1. Generar el suplemento determinista de evidencia para las 7 tareas.
2. Ejecutarlo en dos procesos con seeds distintos; exigir bytes y logical hash
   idénticos.
3. Producir una ficha compacta por task para revisión, derivada de los receipts
   completos.
4. Adjudicar las 21 con un único contrato versionado y rationale verificable.
5. Recalcular disposiciones, manifests y gate sin llamadas externas.
6. Ejecutar tests focalizados y la regresión completa.

La revisión experta se concentra en 21 fichas; el runner barato realiza todos
los joins, hashes, invariantes y decisiones mecánicas. No se enviarán blobs SQL,
snapshots ni documentos completos a un modelo.

## 7. Criterios adversariales antes de implementar

La revisión debe intentar refutar, como mínimo:

- que `source_faithful_semantic_delta` sea una vía encubierta para aprobar
  cambios técnicos sin regresión downstream;
- que `should_exclude` permita excepciones específicas de fabricante/documento;
- que provenance de chunk pruebe realmente fidelity contra raw source;
- que la evidencia completa pueda depender de orden de entrada o caps;
- que los headers/footers repetidos oculten warnings o referencias materiales;
- que tablas/diagramas se juzguen por similitud superficial en vez de por
  obligaciones técnicas;
- que cualquier resultado de este gate se presente como incremento directo de
  facts `OK`.
