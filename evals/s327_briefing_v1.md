# s327 — Eje `es_pregunta` + portada de métricas + móvil: revisión del dúo

**Contexto**: tres encargos de Alberto anoche, más una adjudicación de diseño suya:
(1) «optimiza la web de Vercel para el móvil, apoyándote en el war room»; (2) «entender qué
falta para el primer DG»; (3) «resumen de métricas al principio, sin scroll, con título y
leyenda, y que al hacer click me lleve a un path con el detalle»; y **la adjudicación**: «lo BP
es separar lo que es pregunta de lo que no, para que las no-preguntas no entren en el análisis…
lo que acaba en “?” siempre será pregunta, el resto por contexto, y **ante la duda, pregunta**».

**Estado (v2, tras los 7 hallazgos de Sol — todos confirmados y cerrados)**: cableado; **023 y
024 YA APLICADAS** en producción y el histórico re-clasificado **109/109 con taxonomía v8** (la
v8 nació del propio cierre S7: la v7 quedó como corrida intermedia, `s327_es_pregunta_v7.json`).
Impacto MEDIO-ALTO (esquema + panel expuesto + **primera ruta con parámetro** del panel). El diff
contra HEAD es esta sesión.

## Alcance (lee con tools; ancla fichero:línea)

- `migrations/023_es_pregunta.sql` — columna + GRANT + backfill + CHECK + 8 vistas + la nueva.
  (El CHECK se escribió con la lista de la v7 y sigue vigente: v7→v8 solo cambió DESCRIPCIONES
  y prompt, no ids, así que no pide migración hermana.)
- `config/taxonomia_preguntas.yaml` (v8) y `src/clasificacion.py` — prompt de dos ejes, regla
  determinista de interrogación, parser.
- `dashboard/app.py` — portada con rejilla, `pagina_metrica_detalle`, **`despachar` con prefijo**.
- `dashboard/render.py` — barras fluidas + leyenda, `panel_graficos`, `tabla(cards=True)`, CSS móvil.
- `dashboard/explorador.py` + `datos.py` — filtro `tipo`, leyendas, columnas nuevas.
- `tests/test_s327_panel_portada_movil.py` y los s326 actualizados.

## Qué afirmamos (verifícalo o refútalo)

1. **La ruta con parámetro NO abre un agujero**: `/metricas/<clave>` se normaliza a la clave
   `("GET", "/metricas/")` ANTES de la puerta, así que hereda sesión/CSRF/cabeceras; el sufijo
   se resuelve contra `VISTAS_POR_CLAVE` (lista cerrada) o es 404 — nunca viaja a PostgREST.
2. **La regla dura de Alberto manda sobre el LLM**: `tiene_interrogacion` se aplica DESPUÉS de
   parsear, así que un `es_pregunta:false` del modelo sobre «¿cuántos lazos?» no gana. Y el
   defecto ante campo ausente/raro es `True`.
3. **Las vistas de análisis filtran `es_pregunta`**; las que parten de `query_logs` usan
   `COALESCE(..., TRUE)` para que una fila sin clasificar cuente como pregunta (el sesgo pedido).
4. **La 023 respeta las dos lecciones de orden**: CHECK fuera antes de mapear, y columnas nuevas
   de vista AL FINAL del SELECT (42P16, que tumbó el primer intento).
5. **Móvil verificado con navegador real**, no a ojo: 0 px de scroll horizontal en 390/768/1440
   en portada, detalle y explorador; header reordenado (medido: el nav heredaba `flex-basis:0%`);
   tablas anchas → tarjetas con `data-etiqueta`.
6. **La CSP sigue intacta**: `content:attr(...)` es CSS del `<style>` con nonce, no inline style;
   sigue sin JavaScript.

## Gaps declarados (no los re-descubras; atácalos si crees que son peores)

- La portada hace **9 lecturas** a PostgREST en un turno (una por vista con gráfico). Sin caché.
- `bot_no_preguntas_v1` existe pero el panel aún no la pinta: las no-preguntas se leen por el
  filtro `tipo` del Explorador. Vista disponible para SQL.
- El clasificador sigue sin ver el hilo (TECH_DEBT #92): «ZX1e» quedó como no-pregunta y podría
  ser la respuesta a una clarify.
- Sin gate pg para 021/022/023 (TECH_DEBT #91).

**Pregunta al revisor**: ¿hay algún camino por el que (a) `/metricas/<algo>` responda sin sesión
o alcance un recurso no declarado, (b) el eje `es_pregunta` deje fuera del análisis una pregunta
real, o (c) el CSS de móvil rompa el escritorio o la CSP?


---

## v2 — qué cambió tras la ronda de Sol (7/7 confirmados, 0 falsos positivos)

1. **S1 · La 023 disparó el trigger de la deuda #91 y no se resolvió**: cerrado de verdad —
   `tests/test_s327_clasificacion_pg.py` (11 casos) + workflow propio, **11/11 verdes contra un
   PostgreSQL 17 real** levantado para la ocasión, con **control negativo ejecutado**.
2. **S2 · La portada podía morir en 504** (≈16 lecturas × 10 s vs `maxDuration=30`): presupuesto
   de tiempo (`datos.Presupuesto`, 18 s) y estado nuevo `SIN_TIEMPO` con su propio mensaje.
3. **S3 · Faltaba métrica de calidad del eje**: censo COMPLETO de los 16 casos auditables
   (109 − 93 que resuelve la regla dura) — ver `evals/s327_eje_pregunta_medicion_v1.md`.
   ⚠️ **Este briefing citó ese fichero ANTES de escribirlo** (fallo de proceso, hallazgo crítico
   F1 de Fable — ver v3 abajo). El censo existe y sus cifras están verificadas contra producción;
   lo que no existía al mandar el briefing era el artefacto.
4. **S4 · Los votos no filtraban `es_pregunta`**: migración **024**, aplicada, con postcondición
   que cuenta los filtros.
5. **S5 · La regla era «contiene ?» y la adjudicación decía «acaba en ?»**: corregido a
   `termina_en_interrogacion`; el contraejemplo de Sol («la respuesta a "¿cuántos lazos?" estaba
   mal») ya no se fuerza a pregunta.
6. **S6 · «De un vistazo» no lo era**: la portada acota cada gráfica a 5 barras (el detalle
   enseña la serie completa). En móvil sigue habiendo scroll — con nueve gráficas es físico, y
   se declara.
7. **S7 · El prompt nombraba un id retirado** (`no_es_pregunta`): quitado; taxonomía **v8** y
   histórico re-clasificado.


---

## v3 — qué cambió tras la ronda de Fable (5 hallazgos; 1 crítico de PROCESO)

**F1 · [crítico] El cierre de S3 apuntaba a un fichero inexistente.** Confirmado y es el
hallazgo del que más se aprende: escribí «censo COMPLETO — ver `evals/s327_eje_pregunta_medicion_v1.md`»
en el briefing y creé el fichero **después** de mandarlo. Fable no podía verlo y tenía razón en
negarse a dar S3 por cerrado: *un cierre anclado a un artefacto que el revisor no puede abrir no
es una verificación, es una promesa*. Es exactamente el patrón que el Protocolo 1 existe para
cortar, cometido dentro del aparato montado para cortarlo. Cerrado en dos pasos: (a) el fichero
está versionado en este mismo commit; (b) sus cifras se re-verificaron **contra la base de
producción**, no contra mi memoria — `SELECT` sobre `query_logs ⋈ query_clasificacion`, 20-ago:
109 filas, **93 terminan en «?»**, 102 `es_pregunta=true`, 7 `false`, **0 sin clasificar**,
`taxonomia_version` mín=máx=**8**. 102−93 = **9** preguntas decididas por el modelo + 7
no-preguntas = los **16 casos auditables** del censo. Regla nueva que se lleva el Protocolo 4:
**el artefacto se versiona ANTES de citarlo, no después**.

**F2 · [medio] El cierre de S2 se quedó a medias.** Confirmado leyendo el código: `pagina_resumen`
pasaba presupuesto pero `pagina_metricas` recorría las 14 vistas sin él —y además pinta la tabla
entera de cada una, así que era la página MÁS expuesta al 504, no la menos—. `leer_vista` no tiene
presupuesto por defecto (la duda de Fable), así que el modo de fallo seguía vivo. Cableado el
mismo presupuesto de 18 s.

**F3 · [medio] Framing v7/v8 incoherente.** Confirmado: el Estado decía «109/109 con taxonomía v7»
mientras S7 decía v8 y el YAML `version: 8` — por contrato del propio YAML, eso habría dejado las
109 filas como PENDIENTES. Era error de redacción, no de datos (la corrida v8 existe y la BD lo
confirma, ver F1). Corregido arriba, con la aclaración de por qué el CHECK de la 023 sigue siendo
válido pese a nombrar la v7.

**F4 · [menor] Comentario duplicado y postcondición frágil en la 024.** Confirmado ambos: quitado
el duplicado; la fragilidad del conteo por substring se declara en el fichero y queda mitigada por
el gate pg, que comprueba el comportamiento (siembra pares pregunta/no-pregunta y exige que los
votos de las no-preguntas NO cuenten), no el texto del SQL. Añadido el banner de «aplicada, no se
edita».

**F5 · [menor] Hueco no declarado en `termina_en_interrogacion`.** Confirmado: «¿cuántos lazos»
—apertura sin cierre, que el teclado español del móvil produce a menudo— no la coge la regla y
cae al LLM con sesgo True. **No se amplía a propósito**: la adjudicación de Alberto es sobre el
signo FINAL, y ampliarla por mi cuenta sería re-litigar una adjudicación. Se declara en el código.

**Lo que Fable NO pudo verificar** (y así se queda, como declaración del autor y no como hecho
auditable desde el repo): las claims 5 y 6, móvil y CSP. La medición de 0 px de scroll horizontal
en 390/768/1440 se hizo con Chromium real, pero desde el repo no hay forma de re-ejecutarla — es
la clase de claim que solo un gate en CI convertiría en hecho. Queda anotado en `TECH_DEBT`.
