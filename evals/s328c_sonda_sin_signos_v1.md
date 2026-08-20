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

**Trigger de re-medición — YA NO ES UNA NOTA, ES UNA PUERTA (s328e).** Al preguntar Alberto si
esto era mejor como sonda o como regla determinista, salió a la luz la debilidad real: el gatillo
vivía en un docstring y dependía de que alguien se acordara. Ahora la sonda es **pre-vuelo del job
de clasificación** (`scripts/clasificar_preguntas.py`): antes de escribir una sola fila mide los 12
casos y **aborta si el eje ha regresado**. Es el único camino por el que un prompt nuevo llega a los
datos, así que no hay forma de saltárselo por olvido.

Y no se re-mide por gusto: corre **solo si el prompt cambió**, medido por su **huella** (sha256 de
la plantilla + las descripciones). La huella es mejor señal que `version` del YAML, porque el
contrato de «tocar una descripción obliga a subir version» es una convención que nadie impide
saltarse — verificado: retocar una descripción sin tocar la versión **sí** dispara la re-medición.
El aprobado queda apuntado en `evals/sonda_eje_ultima_pasada.json`.

**Por qué NO se puso la regla determinista** (la alternativa que Alberto planteó): en castellano el
marcador interrogativo que una regla detecta sin ambigüedad es **la tilde** —`qué`, `cómo`,
`cuánto`— y un técnico escribiendo desde el móvil no pone tildes. La regla segura (solo con tilde)
se deja fuera justo el caso que Alberto señaló; la regla útil (también sin tilde) se traga
subordinadas normales («que no me va el lazo») y mete ruido en el denominador, que es lo que el eje
existe para evitar. **No hay regla léxica limpia para esto en castellano.** El `¿` de apertura sí
sería inequívoco, pero medido: de 84 mensajes con `¿`, **cero** carecen del cierre — sería una regla
para un caso que no ocurre.

**Límite**: ocho casos escritos por mí, no tráfico real. Miden que el mecanismo funciona, no la
frecuencia con que aparecen preguntas sin signos — eso solo lo dirá el piloto.
