-- gate-0 track A · hp011 · '05 a 295 seg' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$En la Morley RP1r, después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$En la Morley , después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$En la Morley , después de descargar la extinción el sistema no vuelve a estado normal tras resetear. ¿Qué comprobar$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('2d45a70a-5202-442e-af84-c3a176c2178d', '4581dc4b-db9e-437f-8f96-3db8b57a045a')
ORDER BY 1, 2, 4;
