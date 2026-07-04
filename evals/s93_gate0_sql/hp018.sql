-- gate-0 track A · hp018 · '1 A' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$¿Cómo se conecta una sirena convencional en las salidas de sirena de la Morley ZXe?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$¿Cómo se conecta una sirena convencional en las salidas de sirena de la Morley ZXe?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Cómo se conecta una sirena convencional en las salidas de sirena de la Morley$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Cómo se conecta una sirena convencional en las salidas de sirena de la Morley$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('90d51dac-bd0b-4051-b414-ced0fe6e33bb')
ORDER BY 1, 2, 4;
