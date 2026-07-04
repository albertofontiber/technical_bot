-- gate-0 track A · cat016 · 'autobusqueda' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$En la Detnov CAD-150, ¿como se da de alta un detector nuevo en el lazo y como se prueba que funciona?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$En la Detnov CAD-150, ¿como se da de alta un detector nuevo en el lazo y como se prueba que funciona?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$En la Detnov , ¿como se da de alta un detector nuevo en el lazo y como se prueba que funciona$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$En la Detnov , ¿como se da de alta un detector nuevo en el lazo y como se prueba que funciona$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('294a778c-1dca-40de-8a1b-a9f0c471ea36', 'af6ab292-dbf8-4a9d-a3f8-b048e2f781d9')
ORDER BY 1, 2, 4;
