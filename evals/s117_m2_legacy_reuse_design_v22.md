# S117 M2 — aclaración v2.2 de capas estructural y de elegibilidad

Esta aclaración prevalece sobre la frase “chunk solo indexables” del addendum
v2.1 cuando se interprete como si M2 pudiera omitir la población estructural
S117 ya aprobada.

Hay dos capas diferentes:

1. **Envelope estructural S117:** se rematerializan una vez todos los raws para
   reproducir exactamente las 31.212 filas y sus IDs sellados, incluidos los
   documentos que después serán `register_only`. Esta capa está aguas arriba de
   B1/B2 y no afirma elegibilidad ni ejecuta enriquecimiento.
2. **Proyección productiva B1/B2/B5:** comienza con `profile_document`. Si el
   veredicto es `register_only`, las filas estructurales ya existentes se marcan
   `policy_excluded_register_only` y no se invoca un segundo `chunk_document`,
   ni `detect_language`, ni B5. Si es indexable, se ejecuta el chunker una vez
   dentro de esta proyección, se verifica su alineamiento con el envelope S117 y
   continúa el orden congelado de v2.1.

Así se conservan simultáneamente el denominador estructural completo, el orden
real del pipeline productivo y la prohibición de trabajar innecesariamente un
documento `register_only` dentro de la capa de elegibilidad.
