-- gate-0 track A · hp001 · '2222' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$En la Detnov CAD-250, ¿cómo se entra al menú de programación avanzada?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$En la Detnov CAD-250, ¿cómo se entra al menú de programación avanzada?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$En la Detnov , ¿cómo se entra al menú de programación avanzada$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$En la Detnov , ¿cómo se entra al menú de programación avanzada$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('2fe06904-158e-4922-82a5-76d95e938c7f', '8cf55c57-dc8d-4e81-b35b-67f777580cd5', '9bd17466-1a22-4ade-bb16-a44624c9f166')
ORDER BY 1, 2, 4;
