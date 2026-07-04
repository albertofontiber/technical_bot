-- gate-0 track A · CONTROL cat009 (generado por scripts/s93_gate0_sql.py)
WITH qs(cell, q) AS (VALUES
  ('AND_con', plainto_tsquery('spanish_unaccent', $q$¿Qué resistencia de fin de línea (EOL) hay que instalar en las líneas de zona de la central convencional NFS Supra?$q$)),
  ('OR_con',  replace(plainto_tsquery('spanish_unaccent', $q$¿Qué resistencia de fin de línea (EOL) hay que instalar en las líneas de zona de la central convencional NFS Supra?$q$)::text, '&', '|')::tsquery),
  ('AND_sin', plainto_tsquery('spanish_unaccent', $s$Qué resistencia de fin de línea (EOL) hay que instalar en las líneas de zona de la central convencional$s$)),
  ('OR_sin',  replace(plainto_tsquery('spanish_unaccent', $s$Qué resistencia de fin de línea (EOL) hay que instalar en las líneas de zona de la central convencional$s$)::text, '&', '|')::tsquery)
), ranked AS (
  SELECT qs.cell, c.id, row_number() OVER (
           PARTITION BY qs.cell
           ORDER BY ts_rank(c.search_vector, qs.q) DESC, c.id) AS pos
  FROM chunks_v2 c JOIN qs ON c.search_vector @@ qs.q
)
SELECT cell,
  count(*) FILTER (WHERE pos <= 20 AND id::text = ANY(ARRAY['dccf72bf-37da-4ab9-ae74-56fa6552a1c8', 'cbf6d1c3-2089-4a8d-838e-44f68a739177', 'ec2c308e-34e2-4cbc-8a22-6303b1995644', 'c2eafe7a-71ee-49bc-9af5-1c7b091a721c', '8ed39797-f15d-4647-8adc-78c01fb7b0d0', 'bd280d16-85ee-4716-b452-5eb23ba4ca8c', '4dccf4c3-2d45-4acf-930d-72cc0eab5028', 'fd4061c1-95d7-4b43-8205-06d5b155c177', 'f412ba28-c317-432f-9413-41e673ac3147', '0e63b2ea-2196-49d2-a25f-b3b8d0172a84', '2adae9b9-0763-46cf-98fc-05e5fbd5365a', 'f7446982-b8c5-4873-ad50-1e51fa491844', '6ce4e65d-97b2-49af-ab95-bc34f7fae28b', '7d6e56a0-300f-4c82-b89d-34160fe594fd', 'a9320350-3c42-4a2c-87c8-bec42dffa84c', 'a8275677-4498-431f-9ca9-a756cb804938', 'c23baed9-35ab-49e1-9695-1fcc803047b9', '8b726d5a-1491-40e9-a488-34ae5629526e', 'b80aa594-2c33-4a7e-94dc-2040e4da860a', '8fef952b-9b12-4fcf-81f4-216b1f91ae79', '72c0a9a1-f6d9-4fba-9559-ed5ce74714eb', 'ab35b763-1c39-45e1-93bb-8b52bb270eb7'])) AS top20_en_pool,
  count(*) FILTER (WHERE pos <= 20 AND NOT (id::text = ANY(ARRAY['dccf72bf-37da-4ab9-ae74-56fa6552a1c8', 'cbf6d1c3-2089-4a8d-838e-44f68a739177', 'ec2c308e-34e2-4cbc-8a22-6303b1995644', 'c2eafe7a-71ee-49bc-9af5-1c7b091a721c', '8ed39797-f15d-4647-8adc-78c01fb7b0d0', 'bd280d16-85ee-4716-b452-5eb23ba4ca8c', '4dccf4c3-2d45-4acf-930d-72cc0eab5028', 'fd4061c1-95d7-4b43-8205-06d5b155c177', 'f412ba28-c317-432f-9413-41e673ac3147', '0e63b2ea-2196-49d2-a25f-b3b8d0172a84', '2adae9b9-0763-46cf-98fc-05e5fbd5365a', 'f7446982-b8c5-4873-ad50-1e51fa491844', '6ce4e65d-97b2-49af-ab95-bc34f7fae28b', '7d6e56a0-300f-4c82-b89d-34160fe594fd', 'a9320350-3c42-4a2c-87c8-bec42dffa84c', 'a8275677-4498-431f-9ca9-a756cb804938', 'c23baed9-35ab-49e1-9695-1fcc803047b9', '8b726d5a-1491-40e9-a488-34ae5629526e', 'b80aa594-2c33-4a7e-94dc-2040e4da860a', '8fef952b-9b12-4fcf-81f4-216b1f91ae79', '72c0a9a1-f6d9-4fba-9559-ed5ce74714eb', 'ab35b763-1c39-45e1-93bb-8b52bb270eb7']))) AS top20_nuevo,
  count(*)::int AS total
FROM ranked GROUP BY cell ORDER BY cell;
