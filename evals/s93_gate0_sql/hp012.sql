-- gate-0 track A · hp012 · '99 + 99|2 lazos / 396' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y cuántos dispositivos por lazo?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y cuántos dispositivos por lazo?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Cuántos lazos direccionables soporta la Notifier / y cuántos dispositivos por lazo$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Cuántos lazos direccionables soporta la Notifier / y cuántos dispositivos por lazo$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('11230b35-24ba-43e2-8df6-396e8f852f4a', '5730afb3-6aaf-4968-a022-37db21dde42f', 'f42f4901-9bf7-4633-967d-1c74756ec859')
ORDER BY 1, 2, 4;
