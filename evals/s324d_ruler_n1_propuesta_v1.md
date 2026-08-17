# s324d — El ruler etiqueta con N=1 y ~60 % de sus «no OK» son ruido: qué hacer con la medida

**Estado: NADA cableado. Propuesta para el dúo y para el sí de Alberto.** No toca serving: es el INSTRUMENTO de
medición (`scripts/factlevel_assessment.py`).

## 1 · El dato

Medidos los **15** hechos no-OK del FULL 16-ago con **N=5 sobre vista CONGELADA** (misma composición de contexto en
las 5 generaciones; mecanismo `gen_answer_only` de s289/DEC-168; juez `judge_conveyed21` K=5, `THRESH_FIRM=4`
**intacto**; $9,12 · `evals/s324d_estabilidad_sintesis_v1.md`; aritmética recomputada 15/15 por mí):

| clase | n | hechos |
|---|---|---|
| **INESTABLE** (0 < firmes < 5) | **9** | `cat001#3` 4/5 · `hp015#0` 3/5 · `cat020#1` 3/5 · `hp005#0` 3/5 · `cat008#3` 2/5 · `cat008#1` 2/5 · `cat016#1` 1/5 · `hp015#2` 1/5 · `hp005#3` 1/5 |
| **ESTABLE_MISS** (0/5) | **6** | `hp003#4` · `hp009#0` · `hp011#2` · `hp017#1` · `hp017#2` · `cat018#1` |

Con **una sola** generación —lo que hace el FULL— cada uno de esos 9 sale OK o no-OK según la tirada. Un hecho con
4/5 firmes tiene un 20 % de probabilidad de aparecer como fallo; uno con 1/5, un 20 % de aparecer como éxito.

## 2 · Qué invalida y qué no

**Invalida**: (a) leer un delta pequeño entre dos FULL como señal — con ~9 hechos oscilando, el ruido de muestreo
puede producir ±varios puntos sin que nada haya cambiado; (b) tratar la lista de no-OK como «la cola de defectos»:
la cola real son **6**; (c) cualquier «settled» sobre un hecho concreto medido con una sola generación.

**No invalida**: el eje de *soporte* (¿el carrier llega al generador?), que es determinista dado el pool; ni los
resultados con N≥3 que ya tenemos (sondas de alcanzabilidad, replay congelado); ni el juez, cuya varianza es baja
(bimodal 28/32 en el replay de s324c: lo que varía es la RESPUESTA, no el voto).

## 3 · Opciones

| # | Opción | Coste por FULL | Trade-off |
|---|---|---|---|
| **A** | **N=3 sólo para los hechos que salen no-OK** (segunda y tercera generación sobre la MISMA vista, y clasificar por mayoría: ≥2/3 firmes → OK) | ≈ +$6-9 (sólo se re-genera lo que falla; hoy son 15-19 hechos) | **RECOMENDADA**: ataca justo donde está el ruido, coste acotado, y deja el número comparable si se aplica también a los FULL de referencia |
| B | N=3 para TODOS los hechos | ≈ ×3 el coste de generación del FULL (~$60-70) | Estadísticamente lo más limpio, pero paga por 116 hechos estables para arreglar 9 |
| C | Dejar N=1 y **publicar la incertidumbre** (marcar los no-OK como «no confirmados» hasta re-medirlos) | 0 | Honesto y gratis, pero no arregla la clasificación: sólo advierte |
| D | No hacer nada | 0 | Seguir tratando 9 fallos de azar como cola de trabajo |

### Diseño de A
En `factlevel_assessment.py`, tras la primera pasada: para cada hecho con `conveyed_yes < THRESH_FIRM`, re-generar
**sobre la vista ya servida** (no un turno nuevo: eso mezclaría churn de retrieval, el error que el replay congelado
de s324c aisló) y volver a juzgar. Clasificación final por **mayoría de 3**; el recibo estampa `n_generaciones`,
los votos por rep y la clase (`ESTABLE_MISS` / `INESTABLE` / `ESTABLE_OK`) — para que un FULL futuro no pueda volver
a confundir «falló» con «falló esta vez».

**Comparabilidad**: un FULL con A **no es comparable** con los FULL históricos de N=1. Hay que declararlo como
serie nueva (precedente: `INSTRUMENT_VERSION` v3.0 → v3.2 ya rompió comparabilidad y se declaró). Propuesta:
`v3.3` + nota en el scoreboard.

## 4 · Riesgos y gaps declarados

1. **No arregla el bot, arregla la medida.** Los 9 inestables siguen siendo inestables: A los clasifica bien, no los
   estabiliza. La pregunta «¿por qué la generación varía con el contexto fijo?» queda abierta y es otra línea.
2. **Mayoría de 3 sigue teniendo error**: un hecho con 1/5 de probabilidad real puede dar 2/3. Reduce el ruido, no lo
   elimina. Con N=5 sería mejor y cuesta el doble; N=3 es el punto donde el coste sigue siendo asumible.
3. **El umbral se mueve de sitio**: hoy la incertidumbre está oculta en la etiqueta; con A queda explícita y el
   scoreboard tendrá hechos «INESTABLE» que antes contaban como fallo. El % OK **subirá** por definición — hay que
   decir en el scoreboard que el salto es de método, no de calidad, o se leerá como mejora del bot.
4. **Sólo se ha medido una vez** (15 hechos, N=5). La proporción 9/15 tiene su propio intervalo: con otra tirada
   podrían ser 7 u 11. La dirección es sólida (hay mucha inestabilidad); la cifra exacta no.

## 5 · Por qué es BP, estructural y escalable

- **BP**: medir un fenómeno estocástico con una muestra y tratar el resultado como categórico es el error que el
  propio proyecto ya corrigió en el juez (de single-pass a K=5 por mayoría, DEC-023). Esto es aplicar **la misma
  lección al otro lado del par**: el generador también es estocástico.
- **Estructural**: corrige la clasificación en su origen en vez de re-litigar hecho por hecho cuál fallo era real.
- **Escalable**: el coste crece sólo con los hechos que fallan, no con el tamaño del ruler.

## 6 · Qué pido al revisor

(a) ¿Mayoría de 3 sobre vista congelada es la regla correcta, o debería ser «≥1 firme de 3 ⇒ alcanzable» (asimétrica,
como el fail-closed del negativo en la sonda)? (b) ¿Re-generar sobre la vista servida introduce algún sesgo frente a
un turno nuevo? (c) ¿Rompe algún consumidor del recibo del FULL que asuma un voto por hecho? (d) ¿La subida mecánica
del % OK puede contaminar alguna decisión ya tomada con la serie vieja? (e) Cualquier claim que el código o los datos
no sostengan.
