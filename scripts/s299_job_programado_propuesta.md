# s299 — Propuesta a atacar: retención PROGRAMADA (pg_cron) + pasada única en la base

## OBJETIVO + MÉTRICA (declarados)

**Objetivo**: programar la retención RGPD mensual SIN sacar credenciales de la base, y
eliminar el riesgo de drift entre implementación manual y programada dejando UNA sola
implementación de la pasada.

**Métrica**: NO toca ningún lever medido de eval (retrieval/PASS/retrieval-miss) — es
infraestructura de cumplimiento. El listón es: (a) suite completa verde (3539 pass local),
(b) integración contra Postgres real en CI (workflow `s295-rgpd-retencion-pg`) ejerciendo
la cola s295→s296→s297→s299 entera, (c) los invariantes estructurales previos (ventana
RLS, marca de utilidad inalcanzable, libro solo-inserción) INTACTOS tras el cambio.

## Qué se construyó (commit b02279b, rama claude/s299-scheduler)

1. `supabase/migration_proposals/20260805150000_s299_job_programado_v1.sql`
   - `public.rgpd_retencion_pasada(p_origen)` — plpgsql, **`SET role = rgpd_retencion` a
     nivel de función** + comprobación de `current_user` en el cuerpo (cinturón del
     tirante). NO SECURITY DEFINER. Emite códigos que falten, 3 UPDATE que estampan
     seudónimo y retiran identificador, DELETE de `answer_messages`, destrucción del
     vínculo vía `rgpd_quedan_identificados()`, e INSERT del recibo — todo en la misma
     transacción de quien la llama.
   - **La función NO repite la ventana** (`created_at < corte`): el plazo lo imponen SOLO
     las políticas RLS de s295. El `corte` calculado es informativo (recibo).
   - `public.rgpd_recibos` — solo INSERT para `rgpd_retencion` (política WITH CHECK true);
     API (anon/authenticated/service_role) a CERO; sin UPDATE/DELETE para nadie salvo owner.
   - Reloj: `cron.schedule('rgpd-retencion-mensual', '30 4 1 * *', ...)` condicional a
     `pg_available_extensions`; postcondición: si pg_cron está instalado el job DEBE
     existir; si está disponible y no instalado, EXCEPTION; si no disponible (CI), WARNING.
   - `REVOKE ALL ON FUNCTION ... FROM PUBLIC`.
2. `scripts/rgpd_retencion.py` — queda como DRIVER: `SET LOCAL statement_timeout` +
   `SELECT public.rgpd_retencion_pasada('manual')` + commit/rollback según `--aplicar`.
   Sin `SET LOCAL ROLE`, sin sentencias sobre tablas, sin `corte()` en Python.
3. `supabase_schema.sql` — bloque RGPD-BOUNDARY re-afirma `rgpd_recibos` (API a cero) y el
   REVOKE de EXECUTE de la función, con postcondiciones nuevas.
4. Tests: `tests/test_s299_job_programado.py` (12 unit) + 5 tests de integración nuevos en
   `tests/test_s295_rgpd_integracion_pg.py` (recibo persistido/revertido, `RESET role`
   aborta, EXECUTE denegado a service_role, recibos inmutables e ilegibles,
   vínculo destruido contado SIN ids) + re-bootstrap extendido. Workflow: path añadido.
5. `docs/RGPD_RETENCION.md` — tabla «Mecanismos de transferencia» por proveedor con fuente
   y fecha (5-ago-2026): SCCs-en-DPA para Anthropic/OpenAI/Railway/Supabase, DPF nominal
   para Voyage AI (declaración de MongoDB nombra a Voyage AI Innovations, Inc.), Telegram
   sin DPA (posición: responsable propio del transporte). Pendientes 3/4/6 actualizados;
   fila de `rgpd_recibos` en la matriz. `docs/RGPD_PONDERACION_INTERES_LEGITIMO.md`
   contrapeso actualizado.

## Claims fuertes del autor (atácalas)

- C1: `SET role` como atributo de función asume el rol al entrar y las políticas RLS del
  rol gobiernan TODO el cuerpo; con `RESET role` el cinturón aborta. (Se ejerce en
  integración, no solo se lee.)
- C2: quitar el predicado de fecha de las sentencias NO abre ningún camino a tocar filas
  recientes, porque la función siempre corre como el rol (¿hay algún camino donde no?).
- C3: pg_cron ejecuta el job como el rol que lo programó (`postgres` en el SQL Editor),
  que tiene membresía SET en `rgpd_retencion` — la cadena entera funciona en producción
  aunque en CI no se pueda ejercer (gap declarado).
- C4: el recibo dentro de la misma transacción ⇒ dry-run no deja rastro; toda fila
  persistida = pasada confirmada; el vínculo destruido queda contado pero sin ids.
- C5: el refactor no rompe ningún caller (solo los dos ficheros de test importaban las
  piezas eliminadas) ni ningún camino del bot (el bot no toca nada de esto).
- C6: la tabla de transferencias NO sobre-afirma: distingue «lo declara el proveedor en su
  propia página» de «lo dice una fuente terciaria», y deja la confirmación del registro
  DPF al asesor.

## Riesgos YA declarados (no los re-descubras: atácalos si la mitigación es débil)

- CI sin pg_cron ⇒ la rama de programación (bloque 3) no se ejerce en CI; mitigado con la
  postcondición 4.4 (en prod, disponible-y-no-instalado o instalado-sin-job ⇒ EXCEPTION) y
  verificación post-aplicación (`cron.job` + primer recibo).
- Hasta que Alberto aplique s299 en el SQL Editor, `scripts/rgpd_retencion.py` de esta
  rama sale con exit 2 en producción (la función no existe) — declarado en matriz y PR.
- La operación programada ejecuta `--aplicar` sin botón humano: mitigado por ventana-RLS
  como invariante + recibos + ~2 años de pasadas en vacío antes del primer vencimiento
  (2028).
