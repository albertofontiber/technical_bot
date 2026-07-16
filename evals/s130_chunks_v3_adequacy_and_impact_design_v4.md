# S130 — gate v4 de adecuación e impacto de `chunks_v3`

Contrato normativo final compuesto por:

- diseño base completo:
  `evals/s130_chunks_v3_adequacy_and_impact_design_v3.md`, SHA-256
  `1e9527e2d8b38c3e9dccdd6ebe6f474b17aa2d8c8bdd4f6db44cb12d1460807c`;
- la única sustitución normativa definida abajo.

V1, v2 y v3 conservaron veredicto **NO-GO-to-build**. V4 no modifica ninguna
otra precondición, población, embargo, gate de impacto, gate S, contrato de A/B,
autorización o límite de coste de v3.

## Sustitución normativa: tabla P

Se elimina la referencia ambigua de v3 a “el umbral sistémico de diversidad”.
Para el eje P se define un umbral propio, independiente del gate v4:
`P_systemic_diversity` es verdadero únicamente si se cumplen simultáneamente:

1. la clase afecta al menos al 1% de filas elegibles, limitando la contribución
   de cada documento al 10% del peso total;
2. aparece en al menos 20 documentos;
3. aparece en al menos 3 componentes de linaje independientes tras colapsar
   revisiones, traducciones y rebrands/OEM;
4. aparece en al menos 2 fabricantes;
5. ningún documento aporta más del 10% de la evidencia ponderada;
6. la regla propuesta es genérica y no contiene fabricante, modelo, documento,
   qid, literal gold ni pregunta concreta;
7. la responsabilidad `retrieval_owned` está adjudicada y no pertenece a pérdida
   raw→stored, extracción, fronteras/composición del chunker ni presentación;
8. existe una proyección lossless/reversible candidata, con cobertura fuente
   exacta y sin mutar `content` ni provenance.

Este umbral **no** contiene las condiciones “propia del chunker” ni “proyección
insuficiente”. La tabla P definitiva queda:

| Condición tras las precondiciones comunes | P |
|---|---|
| `P_systemic_diversity=true`, o clipping B8 cierto resoluble por una proyección lossless/reversible con cobertura fuente exacta | `projection_design_warranted` |
| `P_systemic_diversity=false`, no hay clipping B8 resoluble por P y todas las clases están adjudicadas | `no_projection_design_signal` |
| Responsabilidad, resolución, cobertura o reversibilidad no demostrada | `inconclusive` |

Como en v3, este gate solo autoriza **diseñar** una proyección. Su necesidad y su
efecto sobre retrieval requieren el A/B atribuible posterior.
