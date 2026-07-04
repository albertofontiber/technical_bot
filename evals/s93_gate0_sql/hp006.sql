-- gate-0 track A · hp006 · 'Fallo de Tierra|ISO-X' (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$La Notifier AFP-400 muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$La Notifier AFP-400 muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$La Notifier muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$La Notifier muestra el aviso 'Tierra' (Earth Fault). ¿Qué significa y cómo se localiza$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell, 'total' AS what, NULL AS id, count(*)::int AS val FROM ranked GROUP BY cell
UNION ALL
SELECT cell, 'sup', id::text, pos::int FROM ranked WHERE id::text IN ('096600ba-6680-4114-bd62-f5dce9ac7d59', '0ebf60d9-47f9-4311-9762-39205302be4a', '3f9dc99b-76d0-43b6-8943-0d18335917cc', '597cf90f-21ed-4cb4-a9cc-7239bda100d5', '66a941ea-035e-4552-a215-1d97074d9d9d', '6f10426e-8d30-4726-a9d4-efa780c8c8b8', '717a8dac-596f-4ef9-96e3-3f61c96f6250', '7cc8e74a-cc18-4eee-8add-350663d47b92', '9503f5a0-24ad-44af-94ff-d63cbe6c742b', 'a0ee9631-d156-48c6-92f9-126f899f35cb', 'cc29b97f-dca0-4bd1-a335-b038304ca11b', 'd0d6a7ba-c71c-486d-82e8-95801157a172', 'd35de7dd-0acd-40a1-99c5-d143e30a507d', 'd96f4566-d841-4aa7-a418-f0ddb71e6edc', 'dbd4ce93-2918-4a7e-985e-0e0a033ec101')
ORDER BY 1, 2, 4;
