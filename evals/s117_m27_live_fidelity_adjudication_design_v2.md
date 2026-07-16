# S117 M2.7A — adjudicación *live* de fidelity v2

Estado: **borrador corregido para segunda revisión adversarial; no autoriza
ejecución**. Supersede el diseño M2.7A v1.

Este gate trabaja únicamente las 21 tareas `live` congeladas por M2.7 v2. Las
50 tareas `projected` quedan fuera de alcance. Todo es local: cero red, modelos,
embeddings, base de datos, schema apply, load, serving o deploy.

## 1. Tres preguntas independientes

El gate no confunde:

1. `raw_store_fidelity`: correspondencia de chunks v3 con el artefacto JSON
   extraído y congelado;
2. `legacy_semantic_relation`: equivalencia o delta de significado frente a
   chunks legacy;
3. `retrieval_policy_status`: resultado de la policy que ya estaba congelada
   antes de observar estas 21 tareas.

`raw_store_fidelity` **no** prueba fidelidad al PDF, su render visual ni la
calidad de LlamaParse. Esa autoridad pertenece a un gate de extraction fidelity
con el documento original.

Una adición que existe en el raw store puede ser un delta semántico frente a
legacy sin ser corrupción. Contenido fiel puede, además, revelar un gap en la
policy de retrieval. Ninguno de esos casos se convierte en `benign`.

## 2. Evidencia completa y bidireccional

Inputs obligatorios:

- los dos seeds byte-identical de M2.7 v2 y todos sus manifests/receipts;
- el snapshot local congelado usado por M2.7 v2;
- el raw store y sidecars locales fijados por sus manifests M2.7 v2;
- la implementación y registry de retrieval policy congelados por M2.6.

Las 14 tareas completas conservan su evidencia legacy. Para cada una de las 7
incompletas se materializan **todos** los chunks legacy del documento
`extraction_sha256`, ordenados establemente, con IDs, ordinales, contenido UTF-8
y SHA-256.

Para las 21 tareas se añade evidencia raw explícita, no solo un hash de
provenance:

- bytes y SHA-256 del artefacto JSON raw;
- bloques raw completos desde `source_block_start` hasta `source_block_end`;
- un bloque anterior y posterior cuando existan, para detectar cortes de
  frontera;
- texto, tipo, página e índice de cada bloque y manifest estable del span;
- contenido local completo, offsets/lineage y SHA-256;
- comprobación independiente de que cada unidad del contenido local procede del
  span y de que ninguna unidad significativa del span se omite, duplica o
  reordena en el chunk.

La última comprobación puede cerrar automáticamente solo equivalencia textual
bidireccional bajo normalización exclusiva de whitespace. Cualquier tabla,
diagrama, warning, condición, referencia, diferencia de tokens técnicos o caso
que requiera interpretar significado queda para adjudicación. En tablas y
diagramas deben enumerarse obligaciones estructuradas (labels, relaciones,
filas/columnas y valores); si no pueden reconstruirse desde la evidencia, el
resultado es `unresolved`.

`evidence_complete=true` exige que todos los manifests y enlaces a task,
comparison/raw receipts originales sean recomputables y que no haya caps.
Snippets son solo ayudas de lectura y nunca sustituyen contenido completo.

## 3. Contrato de adjudicación

La generación de evidencia es seeded-deterministic. La decisión experta no se
presenta como determinista: es un receipt versionado con `reviewer.method`,
`identity`, `provider`, `model`, timestamp lógico, hashes de toda la evidencia y
rationale verificable.

Cada task recibe:

```yaml
raw_store_fidelity: faithful | unfaithful | unresolved
legacy_semantic_relation: equivalent | source_faithful_delta | unresolved
retrieval_policy_status: eligible_by_frozen_contract | policy_gap_candidate | unresolved
semantic_flags:
  negation_changed: false
  condition_or_scope_changed: false
  warning_or_safety_changed: false
  procedure_order_changed: false
  reference_target_changed: false
  protected_technical_tokens_changed: false
  other_semantic_meaning_changed: false
root_cause:
  repeated_header_footer |
  multilingual_policy_leakage |
  table_serialization_delta |
  diagram_serialization_delta |
  contact_footer_noise |
  other
```

Los flags explican la decisión, pero no son un clasificador exhaustivo.
`legacy_semantic_relation=equivalent` requiere una afirmación positiva de
equivalencia, evidencia citada y rationale; no se deriva solo de siete `false`.
Si la relación es `source_faithful_delta`, al menos un flag debe ser `true`.

`eligible_by_frozen_contract` exige un receipt mecánico con policy version/hash,
rule IDs y predicados evaluados. Este gate no puede inventar exclusiones. Si una
tarea sugiere que la policy congelada es incorrecta, se marca
`policy_gap_candidate`, permanece bloqueante y abre un gate separado corpus-wide
con positivos/negativos. Ninguna regla nueva puede seleccionar manufacturer,
modelo, documento, UUID ni texto específico de estas 21 tareas.

Warnings/safety, tablas, diagramas y cualquier `source_faithful_delta` exigen dos
revisiones independientes. Un conflicto deja la task `unresolved`.

## 4. Disposición derivada

| Condición | Disposición |
|---|---|
| evidencia incompleta, conflicto o cualquier eje unresolved | `unresolved` |
| raw store unfaithful | `material_fidelity_risk` |
| policy gap candidate | `upstream_policy_gate_required` |
| raw faithful + policy congelada eligible + relación equivalent | `adjudicated_benign_delta` |
| raw faithful + policy congelada eligible + source-faithful delta | `downstream_cascade_gate_required` |

Un delta fiel no cuenta como `OK`, no se llama benigno y bloquea cualquier
autoridad downstream hasta superar gates prerregistrados de
retrieval → rerank → synthesis. Un policy gap exige primero una solución
estructural corpus-wide y repetir M2.6/M2.7.

## 5. Salidas y autoridad

El gate puede declarar por separado:

- `EVIDENCE_GO`: 21/21 completas y recomputables;
- `RAW_STORE_FIDELITY_GO`: `EVIDENCE_GO`, cero unresolved/conflictos y cero
  `material_fidelity_risk`;
- `LEGACY_EQUIVALENCE_GO`: además, cero
  `downstream_cascade_gate_required`;
- `FROZEN_POLICY_GO`: además, cero `upstream_policy_gate_required`.

Estos estados son diagnósticos. **M2.7A nunca autoriza M3, context generation,
embeddings, DB, load ni serving**, incluso si todos son GO. Esa autoridad solo
puede concederla un gate posterior explícito. Cualquier semantic delta o policy
gap es bloqueante hasta cerrar su cascada correspondiente.

## 6. Ejecución barata

1. Implementar y testear el generador determinista de evidencia.
2. Ejecutarlo en dos procesos/seeds y exigir bytes y logical hash idénticos.
3. Generar 21 fichas compactas enlazadas a evidencia completa.
4. Emitir receipts de primera revisión y, donde aplique, segunda revisión.
5. Derivar disposiciones mecánicamente; ningún reviewer decide el gate.
6. Ejecutar tests focalizados y regresión completa.

Los modelos/revisores reciben fichas y citas mínimas, no snapshots, SQL ni
documentos completos. El runner barato conserva joins, hashes, invariantes y
derivación de estado.

## 7. Criterios adversariales de implementación

La revisión debe intentar demostrar:

- omisión, duplicación o reorder que pase por `faithful`;
- equivalencia declarada solo por ausencia de flags;
- policy post hoc disfrazada de regla general;
- tabla/diagrama sin obligaciones estructuradas;
- semantic delta o policy gap que desbloquee autoridad downstream;
- dependencia del orden de inputs, caps o snippets;
- cualquier claim de fidelity al PDF o de incremento directo de facts `OK`.
