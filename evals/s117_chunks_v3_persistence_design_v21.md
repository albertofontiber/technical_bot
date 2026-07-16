# S117 — addendum v2.1 al diseño de `chunks_v3`

Este addendum prevalece sobre las cláusulas incompatibles de
`s117_chunks_v3_persistence_design_v2.md`.

## Publicación encapsulada

La publicación y el cleanup de generaciones no son `SECURITY INVOKER`.

- Se crea un rol dedicado `technical_bot_chunks_v3_publisher`, `NOLOGIN`,
  `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`.
- Las RPC estrechas de transición son `SECURITY DEFINER`, propiedad de ese rol,
  `search_path=''` y usan objetos totalmente cualificados.
- Se revoca `EXECUTE` a `PUBLIC`, `anon` y `authenticated`; solo
  `service_role` puede invocarlas.
- `service_role` no recibe `UPDATE` o `DELETE` directo sobre
  `chunk_materializations_v1` ni `chunks_v3`. Recibe `SELECT` y un `INSERT`
  column-level que no permite fijar `state`; este nace siempre `loading`.
- El rol publisher recibe únicamente los privilegios necesarios para validar y
  cambiar estados/limpiar una generación no publicada.
- Un índice parcial único sobre `state='active'` constituye la segunda defensa
  de “un solo active”. Advisory lock + row locks serializan la transición.

El rol privilegiado no se usa para retrieval ni para el loader cotidiano.

## Manifest de filas estructurales

Formato cerrado: JSONL canónico UTF-8, `ensure_ascii=false`, claves ordenadas,
separadores `(',', ':')`, una fila por línea y un newline `0x0a` final. Orden:
`(extraction_sha256, chunk_index)` ascendente binario.

Campos exactos incluidos, sin adicionales:

1. `id`
2. `materialization_id`
3. `extraction_sha256`
4. `chunk_index`
5. `content_sha256`
6. `provenance_version`
7. `provenance_contract`
8. `raw_artifact_sha256`
9. `chunker_sha256`
10. `provenance_payload_sha256`
11. `source_block_start`
12. `source_block_end`
13. `section_anchor`
14. `section_lineage`
15. `section_title`
16. `section_path`
17. `page_number`
18. `is_flow_diagram`
19. `has_diagram`
20. `confidence`
21. `duplicate_of`

Se excluyen contenido completo, rutas físicas, locators, timestamps, metadata
de producto y enriquecimiento futuro. `content` se compara campo a campo contra
la rematerialización y queda comprometido en el manifest mediante
`content_sha256`. M2.5 sellará por separado metadata/context/embedding.

`rows_manifest_sha256` es SHA-256 de los bytes JSONL anteriores. La igualdad
determinista entre ejecuciones aplica al manifest/payload sin timestamps, no al
receipt operativo completo.

El validador reejecuta el chunker congelado sobre el raw y reconstruye cada
campo esperado directamente. No llama al mapper/writer bajo prueba. Puede
compartir primitivas criptográficas puras y constantes congeladas, pero no el
constructor de filas.

## Identidad — aclaración

El manifest de generación incluye `chunker_sha256`, `materializer_sha256`,
fuentes y contrato. `validator_sha256`, tests y runtime viven en el receipt de
validación y no cambian IDs.

Todas las fórmulas UUIDv5 concatenan sus componentes UTF-8 mediante un único
byte NUL real `0x00` (`b"\\x00"`), no los caracteres backslash y cero.

## Gate SQL

El SQL puede implementarse y pasar validaciones estáticas dentro de M0a, pero
permanece `NO_GO_FOR_DB` hasta ejecutarse apply, catálogo, transiciones, grants,
RLS y rollback en PostgreSQL+pgvector desechable durante M0b.
