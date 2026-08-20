# s328c — ¿Coge el clasificador una pregunta SIN signos de interrogación?

> **Por qué existe.** Alberto, al pasar el gate de acuerdo de la v8: «si alguien pregunta
> "qué productos Detnov tienes", sin los signos de interrogación, también debería considerarse
> pregunta». La regla determinista **no** coge ese caso —mira el signo FINAL, que es su
> adjudicación literal—, así que la conducta depende del **prompt**, no del código. Esto la mide
> en vez de suponerla.
>
> **Cómo se mide**: se llama al modelo de verdad (`claude-haiku-4-5`, taxonomía v8) con ocho
> peticiones reales escritas SIN un solo signo de interrogación, más cuatro controles que NO son
> preguntas. Reproducible: `python -m scripts.s328c_sonda_pregunta_sin_signos`.

## Resultado (20-ago-2026)

| | |
|---|---|
| Preguntas sin signos reconocidas | **8 / 8** |
| Controles limpios (no-preguntas que siguen siéndolo) | **4 / 4** |
| Coste | céntimos |

### Las ocho, con lo que decidió cada eje

| Mensaje (sin ningún signo) | regla dura | LLM | categoría |
|---|---|---|---|
| «qué productos Detnov tienes» | no | **pregunta** | catalogo_especificaciones |
| «que centrales de 4 lazos teneis» | no | **pregunta** | catalogo_especificaciones |
| «cuantos lazos tiene la CAD-250» | no | **pregunta** | catalogo_especificaciones |
| «como se rearma la ID3000 tras una alarma» | no | **pregunta** | averias_diagnostico |
| «dime las especificaciones del DGD-600» | no | **pregunta** | catalogo_especificaciones |
| «necesito el esquema de conexión del CAD-250» | no | **pregunta** | instalacion_configuracion |
| «me puedes pasar el manual de la NFS2-3030» | no | **pregunta** | catalogo_especificaciones |
| «cual es la resistencia de fin de línea de la AFP-200E» | no | **pregunta** | catalogo_especificaciones |

Los cuatro controles —«ok, entendido», «Programación principalmente.», «estoy trabajando con la
ZX1e», «gracias, me vale»— siguieron siendo no-preguntas. Sin la segunda mitad, un clasificador
que dijera «pregunta» a todo habría sacado 8/8 y parecería perfecto.

## Lectura honesta

La conducta que Alberto pidió **ya está**, pero no la sostiene una regla: la sostiene el prompt más
el sesgo «ante la duda, pregunta». Eso tiene una consecuencia práctica: **puede romperse sin que
nadie toque el eje**, con un cambio de descripciones de la taxonomía o de modelo.

**Por qué NO se amplió la regla determinista** (que era la reacción obvia): con 8/8 y 0 falsos
positivos, una regla de aperturas interrogativas —«qué / cómo / cuántos / cuál / dime / necesito /
me puedes»— no añadiría precisión hoy. Y sí haría daño: **taparía la señal**. Si un cambio de
prompt rompiera esto, la regla lo escondería en lugar de dejar que esta sonda lo cazara. Ampliarla
además re-litigaría una adjudicación explícita de Alberto (la regla es sobre el signo FINAL).

**Trigger de re-medición**: cuando suba `version` en `config/taxonomia_preguntas.yaml` o se cambie
de modelo. Está escrito en la cabecera del script.

**Límite**: ocho casos escritos por mí, no tráfico real. Miden que el mecanismo funciona, no la
frecuencia con que aparecen preguntas sin signos — eso solo lo dirá el piloto.
