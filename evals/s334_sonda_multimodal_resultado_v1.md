# s334 — Sonda multimodal: **INCONCLUSA**. El dúo tumbó la refutación Y la reformulación

> **VERSIÓN CORREGIDA POST-DÚO r41** (Sol xhigh 7 hallazgos · Fable 8 · emparejados).
> La v1 de este documento titulaba «REFUTA la hipótesis y destapa otra mejor». **Las dos mitades
> eran falsas**, y las dos las cazó el dúo. Lo que queda escrito abajo con ~~tachado~~ conceptual es
> lo que había; lo que vale es esta cabecera y el §8.
>
> **1. La refutación no está establecida** *(Sol, CRÍTICO, verificado)*. Mi estrato «1 página =
> lectura completa» contaba **assets renderizados, no páginas del PDF**. Comprobado contra
> `evals/s271_pdf_coverage_v1.json`: `MAD-412` tiene `pdf_page_count: 2` y `renderable_pages: [1]`
> — leí 1 de 2. De los 24 que llamé «lectura completa», **0 son verificablemente completos**:
> 2 son PARCIAL demostrado y 22 ni siquiera están en el censo de cobertura. Así que el 0/24
> significa «el código no está EN LA PÁGINA QUE LEÍ», no «no está en el documento».
>
> **2. La reformulación tampoco se sostiene** *(Sol, medio, verificado)*. Escribí que la lectura
> multimodal «aporta el ALIAS en el idioma del técnico, que es justo lo que falta». **Ya existen**
> en `aliases.jsonl`: `1 Relay Module` y `2 Relay Module` → `mad-412`, `1/2 Zones Module` →
> `mad-442`, `Single/Double Input Unit` → `mad-402`, `Modelo 1 Relé`. Lo que impide que un técnico
> encuentre «el módulo de dos sirenas» no es que falte el alias: es que **el producto entero está en
> cuarentena** y por tanto no se consume.
>
> **3. «Los dos lectores coinciden» era falso** *(Sol y Fable, medio)*. En `mad-412` GPT devolvió
> `MAD-401`/`MAD-402` «en las etiquetas de las fotos» y Claude negó que hubiera códigos. Sea lectura
> correcta o alucinación, eso exige mirar el píxel — no autoriza inferir ausencia.
>
> **4. Las n no son independientes** *(los dos)*. La MISMA imagen cuenta como varios ensayos
> (`MAD-432` ×3, `DS-5` ×3, `FS` ×3; en el control, Fidegas ×4 y CS4 ×3). El 0/24 es en realidad
> 0/~19 páginas únicas, y los porcentajes presuponen independencia que no hay.
>
> **5. «Cero fuga verificada» sobrevende** *(Fable, menor)*. `_sin_fuga()` sólo inspecciona un
> PROMPT constante que nunca lleva nombres: el guardarraíl es vacuo por construcción. La propiedad
> real —que ni la URL ni el nombre del fichero viajan— se sostiene por inspección del código, que sí
> la cumple, pero eso es otra cosa que «verificada».
>
> **6. «Lee sólo la página 1» es impreciso** *(Fable, menor)*: lee `paginas[0]`, que a veces es la
> p7 (`nfs4`) o la p2 (`ds-5`).

**Encargo de Alberto (21-ago)**: dos observaciones suyas, que resultaron ser la misma.
(1) «Gemini parece que hace mejor la detección de modelos cuando le he subido documentos en pdf
sin nombres de modelos». (2) Los candidates con 0 menciones «pueden ser esquemas de montaje o
cableado que sí pueden ser útiles».

**Estado**: NADA aplicado. Sonda de sólo lectura, con recibo fila a fila
(`evals/s334_sonda_multimodal_resultado_v1.json`).

---

## 0. Lo que ya estaba construido (y que casi vuelvo a construir)

Antes de diseñar nada: `cross_verify_image.py` ya renderiza una página y hace que un modelo
frontera la lea; **DEC-115 (S203)** lo midió y concluyó que «el transporte visual y ambos Frontier
funcionan» (su NO-GO fue del *gold canary*, no del transporte); y **`document_visual_assets` tiene
16.343 páginas** con URL pública, clasificadas por rol y utilidad (DEC-123).

**Corrección de la traza**: DEC-123 dice que eso quedó «pendiente SOLO del runbook DB de Alberto».
La tabla existe y está llena — se aplicó en algún momento y el DEC se quedó desactualizado.

## 1. La población, medida

De los 601 candidates en cuarentena, 587 tienen documento. Comprobando si su token aparece en el
texto de **su propio** documento:

| | |
|---|---|
| su token **SÍ** está en el texto | **535 (91%)** — su problema es adjudicación, no extracción |
| token **PERDIDO**, con página renderizada | **52 (8%)** ← la sonda |
| token perdido y sin imagen | 0 — todos medibles |

**Primer recorte de expectativas**: lo multimodal NO es la llave de los 601. Es la llave de 52.

## 2. El diseño, y su fallo

Dos grupos (52 perdidos + 20 de **control** con el token presente en el texto), dos familias
(Claude y GPT) sobre la MISMA imagen, pregunta en frío («¿qué modelo(s) identifica este
documento?»), y patrón de **PLATA**: el nombre del modelo está en el nombre del fichero, así que se
puntúa sin adjudicación humana.

**Guardarraíl de fuga**: al modelo van los BYTES de la imagen y nada más — ni nombre de fichero, ni
URL (que contiene el nombre), ni el token esperado. `_sin_fuga()` aborta si el esperado aparece en
el prompt. En el smoke los lectores citan el título visible («MANUAL DE INSTALACIÓN Y USUARIO
CAD-171»), no un nombre de fichero.

**EL FALLO DE DISEÑO, que es mío y lo declaro antes que los resultados**: la sonda lee **sólo la
página 1**. Y **R9 —la regla que yo mismo escribí esta sesión— dice que la enumeración de modelos
vive en el CUERPO, no en la portada**. De los 52, **20 tienen 6+ páginas** (uno tiene 109). Para
ésos estoy midiendo la portada, no el documento, y un fallo no dice nada.

## 3. Resultados, estratificados por si la lectura fue completa

| grupo | documento | n | Claude | GPT | alguno |
|---|---|---|---|---|---|
| control | 2+ páginas (sólo portada) | 19 | 7 | 7 | **7 (36%)** |
| control | 1 página (lectura completa) | 1 | 1 | 1 | 1 |
| **perdido** | 2+ páginas (sólo portada) | 28 | 12 | 8 | **12 (42%)** |
| **perdido** | **1 página (lectura completa)** | **24** | **0** | **0** | **0 (0%)** |

**El control al 36% es el instrumento diciendo que no mide lo que yo quería**: son documentos cuyo
token SÍ está en el texto, y aun así la portada no lo enseña. Misma causa que el fallo de diseño.

## 4. El hallazgo: no es que el lector falle — es que el código NO ESTÁ

En los 24 de lectura completa (0/24), los dos lectores coinciden de forma independiente y coherente:
**la página no imprime el código del modelo**. Imprime el nombre DESCRIPTIVO.

| esperado | lo que la página dice, según AMBOS lectores |
|---|---|
| `MAD-402` | «Módulo de 1 entrada técnica» · «1 or 2 Input Module» |
| `MAD-412` | «MÓDULO DE 1 O 2 RELÉS» |
| `MAD-422` | «Módulo 1 Entrada 1 Salida» |
| `MAD-432` | «Módulo de 1 Sirena o Salida 24V Supervisada» |
| `MAD-442` | «Módulo de zona» |
| `DMDX-500` | «Detectores de CO — Versión Estándar / Versión Compacta» |
| `INSPIRE` | sólo marca, versiones de firmware y la herramienta CLSS |

O sea: **el código `MAD-xxx` no existe ni en el texto ni en la imagen. Sólo en el nombre del
fichero.**

**La hipótesis, tal y como yo la formulé, queda REFUTADA para esta clase**: una lectura multimodal
no recupera el nombre, porque el nombre no está.

## 5. Pero la sonda contesta una pregunta MEJOR que la que hice

Alberto tenía razón en lo que importaba: **son productos reales** (módulos Detnov de entradas,
relés, sirenas y zona) con su hoja de instalación en el corpus. Lo que la sonda destapa es que el
problema no es de recuperación de código, sino **de vocabulario**:

- el CATÁLOGO conoce `MAD-432`
- la PÁGINA dice «Módulo de 2 Sirenas o Salida Supervisada»
- y el TÉCNICO va a escribir lo segundo, no lo primero

Hoy una pregunta como «el módulo de dos sirenas de Detnov» no resuelve a nada. La lectura
multimodal no aporta el código — **aporta el ALIAS en el idioma del técnico**, que es justo lo que
falta, y lo aporta con cita de dónde lo ha visto.

**Reformulación propuesta**: la capacidad no es *recuperar nombres perdidos*, es **cosechar alias
descriptivos con evidencia visual**. Es una pregunta distinta, con un valor distinto, y hay que
medirla aparte antes de creérsela.

## 6. Señales sueltas que no encajan y hay que mirar

- `unresolved:mad-412` → GPT devolvió `["MAD-401","MAD-402"]` diciendo que están «en las etiquetas
  de las fotos». Si es cierto, **algunos códigos SÍ están impresos en las fotos del equipo** y la
  conclusión de §4 es demasiado tajante. Claude no los vio.
- `mad-432-módulo-1-sirena` → GPT devolvió `["MDA1S","MDA2S"]`, códigos que no había visto antes.
- Dos ids del catálogo (`MAD-432 Módulo 1 Sirena`, `MAD-432 Módulo 2 Sirenas`) **no son modelos**:
  son descripciones que la extracción s83 convirtió en productos. Eso es una clase de artefacto que
  R9/R12 no cubren.

## 7. Gaps declarados

1. **El fallo de diseño de la página 1** invalida la mitad de la muestra (28 de 52). Repetir con la
   página que R9 señala —o con las N primeras— es obligatorio antes de cualquier conclusión sobre
   los de 2+ páginas.
2. **Sin Gemini**: no hay clave en este entorno. Lo que Alberto observó no se ha reproducido con SU
   herramienta; se ha medido con las dos familias disponibles. Que estas dos coincidan en que el
   código no está es evidencia decente de que no está, pero no cierra su observación.
3. **Patrón de PLATA**: el esperado sale del nombre del fichero y **R8 dice que los ficheros
   mienten**. Aquí la evidencia apunta a que el fichero acierta (los códigos MAD-xxx son la
   nomenclatura de Detnov), pero no está verificado contra el fabricante.
4. **n pequeñas**: 24 y 28 por estrato, 1 solo caso en el control de lectura completa. El control
   está prácticamente vacío donde más falta hacía.
5. **La reformulación de §5 es MÍA y no está medida.** Que los lectores lean el nombre descriptivo
   no prueba que ese alias mejore el retrieval: eso es un delta en eval, y no lo he corrido.
6. **Coste no medido**: 144 llamadas de imagen sin instrumentar el gasto.


---

## 8. QUÉ QUEDA EN PIE, tras el dúo

**Lo que sobrevive:**

1. **La población está bien medida y es el hallazgo útil**: de 587 candidates con documento,
   **535 (91%) tienen su token en el texto de su propio documento**. Lo multimodal NO es la palanca
   de los 601 — como mucho lo es de 52. Esto no depende de ninguna de las claims tumbadas.
2. **El instrumento funciona** donde el nombre está a la vista: en el control, los lectores citan
   «MANUAL DE INSTALACIÓN Y USUARIO CAD-171» y aciertan, sin ver nombre de fichero.
3. **Observación cualitativa, con su alcance recortado**: en las páginas que leí de la plantilla
   Detnov de hoja corta, lo impreso es el nombre descriptivo y no el código. Fable precisa el
   alcance correcto: lo observado es «el código no se imprime **en esa plantilla**», no una tesis
   sobre el corpus.

**Lo que NO queda establecido:** absolutamente nada sobre la hipótesis de Alberto. No he leído un
solo documento verificablemente completo, no he usado Gemini —que es lo que él observó— y las dos
conclusiones que saqué estaban sobre-afirmadas en la misma dirección: a favor de mi propia lectura.

**Qué costaría una versión válida:**

- leer **todas** las páginas renderizadas de cada documento, no `paginas[0]`;
- restringir el estrato «completo» a documentos donde `renderable_pages` cubra `pdf_page_count`
  (hoy: 22 de 24 ni tienen ese dato — el censo `s271` cubre 816 documentos y la plantilla Detnov
  no está);
- contar por **imagen única**, no por candidate;
- y, para cerrar la observación de Alberto de verdad, **una clave de Gemini**.

**Recomendación**: no gastar más en esta sonda hasta decidir si merece la pena. Su premio máximo son
52 filas, y el trabajo de verdad —los 535 con el token en el texto— no lo toca. Si se retoma, se
retoma con el diseño corregido de arriba, no con el actual.

## 9. Lección de proceso, que es lo más caro de la sesión

Es la **tercera vez hoy** que presento una medida como decisiva y resulta medir algo más estrecho:
primero la tasa base heredada del v2, luego el fail-open que no reproducía el fallo real, ahora el
estrato de «lectura completa» que contaba assets. Las tres veces el error empujaba **en la dirección
que favorecía mi propia conclusión**, y las tres las cazó otro —el dúo o Alberto—, no yo.

El patrón no es de descuido: es que **valido el número y no la definición del número**. La guarda
que se lleva a `reglas_clasificacion.json` es de una línea: *antes de estratificar por una variable,
comprobar contra la fuente canónica qué cuenta exactamente esa variable*.
