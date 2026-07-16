# S130 — gate v5 de adecuación e impacto de `chunks_v3`

Contrato normativo final compuesto por:

- `evals/s130_chunks_v3_adequacy_and_impact_design_v4.md`, SHA-256
  `7c77ff501eee3183866484b1bd6cc1ee115e2f37310f2ab047148a2304b41869`;
- esta única ampliación fail-closed del registro de embargo.

V5 no modifica los ejes S/P, Carril A/B, umbrales, A/B futuro, autorización ni
coste. Corrige que el cierre de relaciones debe incluir tanto relaciones de
producto como relaciones documentales.

## Inputs adicionales obligatorios del embargo

| Rol | Ruta | SHA-256 |
|---|---|---|
| catálogo de productos y endpoints | `data/catalog/products.jsonl` | `c192a407e9ebd780c8864936a4a5a90d7ba3190982c5c9a52b998efaf9b97229` |
| relaciones documento→documento | `data/catalog/docrel.jsonl` | `0a08b33ee75f6f7fdccdca7746d8f6af8b7a696fba37b13d8e82fd4a0f959a6d` |

El cierre de fase 0 debe:

1. validar que todo endpoint de `relations.jsonl` existe en
   `products.jsonl`;
2. validar que todo endpoint de `docrel.jsonl` existe en `doc_map.jsonl`;
3. expandir por punto fijo primero relaciones de producto→documentos y después
   relaciones documento→documento, incluyendo `language-variant-of` y cualquier
   tipo documental congelado futuro solo si está enumerado antes de ejecutar;
4. fallar cerrado ante endpoint ausente, tipo desconocido, identidad ambigua o
   drift de cualquiera de los cuatro ficheros de catálogo.

Ningún contenido de un documento incluido en ese cierre puede abrirse, aplanarse
ni pasar por el chunker durante el censo de desarrollo. Los totales globales se
validan contra los recibos estructurales congelados M28/M29; el auditor local
solo procesa contenido del universo elegible no embargado.
