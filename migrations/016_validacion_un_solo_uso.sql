-- ============================================================================
-- 016 · VALIDACIÓN — prueba de vida del UN SOLO USO del canje.
--
-- SEPARADO del fichero que crea las tablas a propósito (s324e, tras dos incidentes reales):
-- esta prueba escribe una invitación de mentira y necesita deshacerla, y la forma de
-- deshacerla depende del cliente SQL. Mezclarla con el DDL hizo que un `ROLLBACK` se
-- llevara la creación de las tablas por delante.
--
-- CUÁNDO: después de aplicar `016_allowlist_invitaciones.sql` y de comprobar que las dos
-- tablas existen. Es OPCIONAL: no crea nada y no deja rastro.
--
-- QUÉ DEBE SALIR: el primer UPDATE devuelve UNA fila; el segundo, NINGUNA. Eso demuestra
-- que la condición del canje (no canjeada · no revocada · no caducada) hace su trabajo.
-- Si tu cliente da «SAVEPOINT can only be used in transaction blocks» o similar, ejecuta
-- las tres sentencias a mano y borra al final la fila con
-- `DELETE FROM bot_invitaciones WHERE token_hash = repeat('a', 64);`
-- ============================================================================

-- C.6: prueba de vida del UN SOLO USO, en seco (el ROLLBACK no deja rastro).
-- Son DOS sentencias separadas a propósito: dos CTE que modifican datos dentro
-- de UNA sentencia comparten snapshot y no se ven entre sí — el manual de
-- Postgres llama a ese caso «unspecified», así que probarlo así no probaría
-- nada. Sentencias sucesivas sí ven el efecto de la anterior.
-- El primer UPDATE debe devolver UNA fila; el segundo, NINGUNA.
BEGIN;
  INSERT INTO bot_invitaciones (token_hash, nota, creada_por, expira_at)
  VALUES (repeat('a', 64), 'prueba de la 016', 'validacion',
          now() + interval '1 day');

  UPDATE bot_invitaciones SET canjeada_at = now(), canjeada_por = 1
  WHERE token_hash = repeat('a', 64) AND canjeada_at IS NULL
    AND revocada_at IS NULL AND expira_at > now()
  RETURNING canjeada_por AS primer_canje_debe_devolver_1_fila;

  UPDATE bot_invitaciones SET canjeada_at = now(), canjeada_por = 2
  WHERE token_hash = repeat('a', 64) AND canjeada_at IS NULL
    AND revocada_at IS NULL AND expira_at > now()
  RETURNING canjeada_por AS segundo_canje_debe_devolver_0_filas;
ROLLBACK;
