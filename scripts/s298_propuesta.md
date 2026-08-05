# Propuesta s298 — bootstrap al estado FINAL + docs al estado aplicado

## OBJETIVO + MÉTRICA
Contexto: Alberto aplicó la cola s295→s296→s297 en producción (5-ago, verificado contra el
catálogo). Este delta: (1) `supabase_schema.sql` re-concedía el estado PRE-cola — re-ejecutar
el bootstrap DESHACÍA en silencio la protección de la marca (clase s296, viva en main hasta
este branch); pasa al estado FINAL con postcondiciones por tabla (arrays separados
tabla/columna) y re-afirmación condicional de persona_seudonimo/consent_events. (2) Columnas
s296/s297 en el bootstrap con las MISMAS sentencias idempotentes que las migraciones
(bootstrap y cola convergen en cualquier orden; la maquinaria de retención queda con UNA
fuente: la cola; entorno nuevo = bootstrap + cola). (3) Test que extrae el bloque frontera
REAL (marcadores explícitos) y lo RE-EJECUTA tras la cola en el Postgres del CI — la
prevención de la clase pasa de procedimiento a CI (cierra el residual de s297). (4) Docs que
el despliegue dejó falsos («no ejecutable») → estado real.
MÉTRICA: ninguna de calidad de respuesta; corrección del bootstrap y de lo declarado.

## Verificado
43 unitarios verdes; CI Postgres real VERDE A LA PRIMERA incluyendo el test nuevo de
re-ejecución del bootstrap tras la cola (marca inalcanzable, voto vivo, libro solo-inserción).

## Gaps declarados
1. El bootstrap NO crea el rol/tablas/políticas/trigger de retención (una fuente: la cola);
   un entorno solo-bootstrap tiene bot funcional y retención que dice honestamente exit 2.
2. El test extrae el bloque por marcadores: si el bloque crece FUERA de los marcadores, el
   test no lo ve (los marcadores están comentados como contrato).
3. El fixture del CI no ejecuta el bootstrap COMPLETO (extensiones/roles supabase), solo el
   bloque frontera — la convergencia de CREATE TABLEs bootstrap↔cola se apoya en usar
   sentencias idénticas, no en ejecución.

## Ataca
¿El bloque frontera final es correcto para las 5+2 tablas (expectativas de tabla vs columna
separadas)? ¿Alguna vía por la que re-ejecutar bootstrap deje algo MÁS abierto? ¿Los grants
de columna del bootstrap referencian columnas que podrían no existir en algún orden de
aplicación? ¿Los docs actualizados declaran de más o de menos sobre el estado de producción?
