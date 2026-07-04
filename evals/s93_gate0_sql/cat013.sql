-- gate-0 track A · cat013 · 'CLIP' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$Tengo una central Detnov CAD-150 y me ha sobrado de otra instalacion un detector optico Notifier SDX-751; ¿es compatible / puedo montarlo en su lazo?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$Tengo una central Detnov CAD-150 y me ha sobrado de otra instalacion un detector optico Notifier SDX-751; ¿es compatible / puedo montarlo en su lazo?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Tengo una central Detnov y me ha sobrado de otra instalacion un detector optico Notifier ; ¿es compatible / puedo montarlo en su lazo$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Tengo una central Detnov y me ha sobrado de otra instalacion un detector optico Notifier ; ¿es compatible / puedo montarlo en su lazo$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('cfcdc8f7-bdaf-412f-a85e-0ffb76878d99')
ORDER BY 1, 2, 4;
