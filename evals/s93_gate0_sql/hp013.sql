-- gate-0 track A · hp013 · 'PWR-R' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$¿Cómo se cambia la batería tampón de la Detnov ADW535 sin perder configuración?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$¿Cómo se cambia la batería tampón de la Detnov ADW535 sin perder configuración?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Cómo se cambia la batería tampón de la Detnov sin perder configuración$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Cómo se cambia la batería tampón de la Detnov sin perder configuración$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('2365dfaa-45e5-4c65-9328-194441e375c9', 'a19e8735-0e84-471a-9224-4be148cc65b9', 'a5564c62-c198-4b5a-957d-96443a7a22a0')
ORDER BY 1, 2, 4;
