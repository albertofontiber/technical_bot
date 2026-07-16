# S130 — gate v6 de adecuación e impacto de `chunks_v3`

Contrato normativo final compuesto por:

- `evals/s130_chunks_v3_adequacy_and_impact_design_v5.md`, SHA-256
  `5551433a5e33df08878a86618c2f2d1aecb04acedd1ec32f6a5991c3da905125`;
- esta corrección del universo documental usado para validar `docrel.jsonl`.

V6 no cambia ningún gate, umbral, autorización ni coste. V5 exigía que todos los
endpoints de `docrel.jsonl` apareciesen en `doc_map.jsonl`, pero `doc_map` solo
contiene documentos con asignación de producto y no es el inventario documental
completo.

## Inventario documental autoritativo adicional

| Rol | Ruta | SHA-256 |
|---|---|---|
| snapshot documental M2.5 | `tmp/s117_m25/derived_snapshot_v2.jsonl.gz` | `3013c553da20c72fbfe0dc801dad4ea4b063ecff3138dcf55b5cd7831cf79067` |

Recibo lógico congelado: 1.171 documentos, 25.090 chunks y canonical JSONL
SHA-256 `c5c4e1027d85b5023e8834e221bb99799fedbea1a9826f5a42f88ff3ad8da8d5`.

Sustitución normativa de V5.2:

1. todo endpoint de `docrel.jsonl` debe existir en el inventario documental del
   snapshot M2.5, no necesariamente en `doc_map.jsonl`;
2. el cierre documental se calcula en ese universo y después se proyecta sobre
   los 1.068 `source_pdf_sha256` del raw store mediante el binding M2.5;
3. un endpoint válido fuera del raw store queda registrado como
   `outside_development_store` y no bloquea; un endpoint ausente del snapshot sí
   falla cerrado;
4. solo las extracciones resultantes de la proyección entran en la lista física
   que el auditor debe saltar **antes** de abrir contenido.
