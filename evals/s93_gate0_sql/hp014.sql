-- gate-0 track A · hp014 · '35' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$¿Cómo se conecta un módulo de aislamiento de línea en un lazo ID2000?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$¿Cómo se conecta un módulo de aislamiento de línea en un lazo ID2000?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Cómo se conecta un módulo de aislamiento de línea en un lazo$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Cómo se conecta un módulo de aislamiento de línea en un lazo$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('d4018c9b-8eff-4b19-b826-5bb4df55d29e')
ORDER BY 1, 2, 4;
