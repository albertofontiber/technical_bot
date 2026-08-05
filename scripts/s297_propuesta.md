# Propuesta s297 — libro de consentimiento + feedback resistente + marca en canal espontáneo

## OBJETIVO + MÉTRICA
Cerrar dos de los tres gaps declarados en s296. MÉTRICA: ninguna de calidad de respuesta (no
toca retrieval/generación); el criterio es corrección de la evidencia y de lo declarado.

## Decisión previa, contraintuitiva
El tercer gap (código nuevo tras destruir el vínculo) NO se resuelve: conservar la
correspondencia tras el plazo = el vínculo no muere nunca. Declarado en DEC-179 con la
alternativa descartada (periodo de gracia = alargar retención por comodidad).

## Lo construido
1. `consent_events` (migración `20260805120000_s297_...`): patrón ESTADO + LIBRO.
   `user_consent` sigue siendo lo que `has_consent` lee; el libro es la evidencia — solo
   inserción para service_role (sin UPDATE/DELETE ni de tabla ni de columna), RLS+FORCE+REVOKE
   de anon/authenticated. `set_consent` escribe el evento TRAS el estado, fail-open con aviso.
   Revocación manual de DG_DEPLOYMENT inserta su evento ANTES del UPDATE. Backfill = 
   RECONSTRUCCIÓN declarada (un accepted por fila viva + un revoked donde conste).
2. `log_feedback`: reintento SIN enlace ante FK colgante — solo 23503 definitivo (409/400),
   nunca timeout. `_fk_rejected` nuevo.
3. `feedback.utilidad` + `utilidad_revisada_at` + CHECK (mismas 4 categorías). Sin cambio de
   privilegios: service_role no tiene UPDATE ahí desde julio.
4. `docs/RGPD_PONDERACION_INTERES_LEGITIMO.md`: borrador LIA para el asesor, rotulado SIN
   VALIDAR, con contrapesos declarados (transferencias pendientes, arista laboral del bonus).

## Verificado
7 unitarios nuevos + CI contra Postgres real EN VERDE A LA PRIMERA (la ruta de la migración
s297 se añadió al workflow ANTES del primer push — lección s296). Integración: backfill
reconstruye; inmutabilidad EJECUTANDO como service_role; re-aceptar no pisa evidencia; roles
anónimos sin acceso; la marca del canal espontáneo inalcanzable para el bot; el operador SÍ
puede marcar y un valor fuera de taxonomía revienta.

## Gaps declarados
1. Divergencia posible estado↔libro (evento fail-open): se detectaría comparando tablas; no
   hay reconciliación automática. 2. El libro solo registra revocaciones si el procedimiento
   manual se sigue. 3. `consent_events` ES dato personal; su plazo = mismo [DECIDIR] que
   `user_consent`, fuera de `rgpd_quedan_identificados` (si contase, el vínculo no moriría).
   4. El borrador LIA no vale nada hasta validación legal. 5. Backfill no recupera v1..v6
   (irrecuperable, no fingido).

## Ataca
¿El libro puede mentir (orden evento/estado, carreras, backfill duplicado si la migración se
re-ejecuta)? ¿El reintento de FK puede duplicar feedback o tragarse otro error? ¿`SET LOCAL
ROLE service_role` en los tests prueba lo que digo (BYPASSRLS del fixture vs prod)? ¿Los
claims de DEC-179/matriz/LIA declaran de más o de menos? ¿La migración es re-ejecutable?
