# S130 — corrección v7 del recibo físico del snapshot documental

Contrato normativo compuesto por:

- `evals/s130_chunks_v3_adequacy_and_impact_design_v6.md`, SHA-256
  `7ee9024d84eb854fdc6e8420d3426060d35240f4460198e02999922b753742e1`;
- esta corrección exclusivamente física de la ruta del snapshot.

V7 no cambia el universo lógico congelado por V6, sus 1.171 documentos, sus
25.090 chunks, el SHA-256 del fichero, el recibo canonical JSONL, los gates,
los umbrales, las autorizaciones ni el coste. Corrige una ruta incoherente: los
recibos ya fijados por V6 pertenecen al snapshot remoto M2 y no al snapshot
derivado M2.5.

## Sustitución normativa única

Donde V6 dice:

`tmp/s117_m25/derived_snapshot_v2.jsonl.gz`

debe decir:

`tmp/s117_m2/remote_snapshot_v1.jsonl.gz`

La ruta corregida debe seguir verificando, antes de leer su contenido:

- SHA-256 físico
  `3013c553da20c72fbfe0dc801dad4ea4b063ecff3138dcf55b5cd7831cf79067`;
- 1.171 documentos;
- 25.090 chunks;
- canonical JSONL SHA-256
  `c5c4e1027d85b5023e8834e221bb99799fedbea1a9826f5a42f88ff3ad8da8d5`.

Todo lo demás en V6 permanece normativo sin modificación.
