# s321 — DEC-186b · PROPUESTA v2 (Sol v1 NO SÓLIDO, 4 medios, 0 FP — todos aplicados)

**Lo que la v1 tenía mal**, verificado: (1) «0/5-o-5/5 ⇒ selección del chunk» era sobre-lectura — los 5
son **votos del juez sobre UNA respuesta** (`judge_conveyed21`, K=5 en paralelo), no cinco generaciones;
la unanimidad solo prueba consistencia del juez. (2) Proponía «el FULL» como medición del eje modelo, pero
el FULL corre un solo modelo (opus-5) sin brazo ni freeze ⇒ mide calidad absoluta, no el eje modelo. (3)
Omitía el caveat de canal degradado (3/15 reps, todas 0/5) que **`TECH_DEBT #75` ya documenta**. (4)
Descartaba n=20 con un argumento de cobertura falso. **Raíz común: propuse sin leer entero #75, que ya
tenía la lectura correcta y más prudente.**

## Veredicto sustitutivo v2 — apoyado en #75, no reinventado

> **DEC-186b — Lo que la cifra rota de s305 sostenía CAE entero: con el juez leído bien, `hp011#2` es
> ALCANZABLE con evidencia perfecta en los tres modelos (re-juicio de las 9 guardadas: sonnet-4-6 2/3 ·
> sonnet-5 0/3 · opus-5 2/3, lower bound por truncado; A/B v2 n=5: 1/5 · 1/5 · 4/5). Lo que lo
> SUSTITUYE es lo que `TECH_DEBT #75` ya escribió y esta DEC adopta como propio: (a) el «NO alcanzable»
> de DEC-173 no describe el sistema actual; (b) este hecho, bajo estas configuraciones, transmite de
> forma MIXTA — 6/15 firmes con la evidencia ideal delante — y eso NO reclasifica la clase «elemento
> vecino» (sonda de UN hecho; los 15 son 3 generadores, no réplicas; CAD-171 sin re-medir); (c) la
> inyección aporta delta (base 0/5 en 14/15) pero NO localiza el hueco en serving; (d) opus-5 4/5 frente
> a 2/10 APUNTA a un eje de modelo SIN establecerlo — rango de sensibilidad p=0,089 (15 reps) / p=0,061
> (12 limpias); caveat: 3/15 reps con canal degradado, todas 0/5, incluida la única no-firme de opus —
> «MONTAJE NO COMPARABLE», no es freeze-contract limpio. NO se declara «techo del modelo» ni «lever de
> modelo». Si se quiere adjudicar el eje modelo hay que MEDIRLO: A/B pareado con freeze limpio, n≥20 por
> brazo, ≥2 hechos de la clase (hp011#2 + el de CAD-171), OBJETIVO = eje modelo, MÉTRICA = per-fact
> conveyed K=5 firme; coste ~$30. Queda como candidato, NO ordenado (pregunta cero: producción ya corre
> opus-5, el mejor de los tres — el eje solo importa si se plantea cambiar de modelo).**

**Qué se toca**: DEC-186 (banner «EN REVISIÓN» → «SUSTITUIDA por DEC-186b», sin borrar el banner: es el
acta del error); PLAN l.369 («pendiente de reescritura» → «reescrita: DEC-186b»); TECH_DEBT #75: **NO se
cierra** — su fix (que el juez exponga el entero) sigue pendiente; se añade una línea «DEC-186b escrita
16-ago apoyándose en este análisis». LEVER_DIGEST: sin cambio (la fila Etapa 3 ya no cita el techo).

**Qué NO afirma**: nada sobre selección/atención/expresión; nada sobre «lever de modelo»; nada que un
recibo no sostenga. Las cifras son las de #75 y de los dos JSON versionados.

## Lo que el dúo tiene que atacar en v2
1. ¿Queda alguna afirmación que exceda #75 + los dos recibos?
2. ¿Es correcto NO cerrar #75 (raíz) y sí cerrar «DEC-186 sin número»?
3. ¿El candidato de medición (A/B pareado n≥20, 2 hechos, freeze limpio) está bien especificado como
   OBJETIVO/MÉTRICA, o le falta algo para ser pre-registrable?
