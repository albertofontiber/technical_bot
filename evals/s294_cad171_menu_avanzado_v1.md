# s294 — Fallo REAL del bot en producción: la ruta al menú AVANZADO de la CAD-171

**Origen: uso real, no eval.** Lo encontró Alberto probando el canal de feedback (2-ago,
`query_logs` 16:05 UTC, `bot_version=aae2f27`), y es el **primer caso orgánico** que entra por
el bucle 👎 → explicación que se construyó ese mismo día.

## Qué preguntó y qué respondió

**Pregunta:** «¿cómo puedo acceder al menú de configuración avanzada de la CAD-171?»

**Respuesta del bot** (extracto literal):
> Para acceder a los parámetros de configuración básica: **AJUSTES (Menú principal) > GENERAL
> (Submenú)** [F2]
>
> Desde el submenú AJUSTES tienes disponibles las siguientes opciones: GENERAL · VERSIONES ·
> USUARIOS · **AVANZADO** · CONECTIVIDAD · IMPRESORA · LOGS · TEST · INICIO
>
> El submenú **AVANZADO** está disponible dentro de **AJUSTES**, pero los fragmentos
> disponibles no detallan su contenido específico.

**Lo que dijo Alberto** (`answer_feedback.comment`, anclado a la consulta): «"AJUSTES > GENERAL"
según dices me llevaría a "GENERAL" dentro de Ajustes, pero AVANZADO está al mismo nivel, por lo
que es incorrecto para acceder al menú avanzado, ¿no?»

## Verificación contra la fuente — Alberto tiene razón

`Manual_CAD-171-MI-716-es`, TRES diagramas de navegación coincidentes (p.26 · p.34 · p.35):

- **Menú principal**: LAZO · SECTORIZACIÓN · MANIOBRAS · LOGS · RED · **AJUSTES** · INSTALACIÓN · MAPAS
- **Submenú de AJUSTES**: GENERAL · VERSIONES · USUARIOS · **AVANZADO** · CONECTIVIDAD · IMPRESORA · LOGS · TEST · INICIO

⇒ **AVANZADO es HERMANO de GENERAL**, no cuelga de él. Y el manual usa esa misma notación para
las rutas: «AJUSTES (Menú principal) > **TEST** (Submenú) > INICIAR» (p.34), «AJUSTES (Menú
Principal) > **CONECTIVIDAD** (Submenú)» (p.35).

**La respuesta correcta era:** acceder como administrador (icono del candado en la PANTALLA DE
REPOSO → clave por defecto **2222**, p.25 §6.1) y navegar a **«AJUSTES (Menú principal) >
AVANZADO (Submenú)»**, con el caveat de que el contenido de ese menú no está en este manual.

## La clase del fallo — y por qué importa más que el caso

No es un dato falso: la lista que dio es correcta. El fallo es de **SELECCIÓN**: encabezó con la
ruta de OTRO submenú (GENERAL, que él mismo etiqueta «básica») y **nunca compuso la ruta pedida**,
teniendo AVANZADO delante en la evidencia servida.

**Es la misma forma que `hp011#2`**: el bot tiene el dato servido y responde con el **elemento
vecino** — allí `r.i` (inhibición de rearme) en vez de `t.A` (duración de descarga), aquí GENERAL
en vez de AVANZADO. **Dos instancias de la misma clase, y esta viene de uso real.**

Esto matiza el argumento de s294 («ningún lever de síntesis se puede diseñar con n=1»): la clase
existe y empieza a poblarse sola en cuanto hay una persona usando el bot y un canal para
contarlo — que es exactamente lo que el paquete de telemetría acaba de habilitar.

## Lo que NO es: hueco de corpus para lo preguntado

El **acceso** al menú sí está en el manual que tenemos.

> ### ⚠️ CORRECCIÓN (s302, 6-ago — DEC-184): la «Guía Avanzada» TAMPOCO falta
>
> Este apartado decía que faltaba la «Guía Avanzada de Configuración» de la CAD-171, apoyado
> en que **ningún fichero de Detnov lleva «avanzada» en el NOMBRE**. Ese test era el
> equivocado — buscaba por nombre de fichero, no por contenido. La adjudicación de s302 lo
> desmontó:
>
> **El documento existe, está ingestado y está mapeado a la central.** Es
> `CAD-250_Manual-Configuracion-MC-380-es-2026-c`, cuyo control de revisiones (p.2) dice
> literalmente «**c · Adaptación para CAD-171 y CAD-201 · 23/04/2026**», que figura en
> `data/catalog/doc_map.jsonl` con **`detnov:cad-171` como `role: primary`** — y cuyo **§5.4,
> p.29** documenta exactamente lo pedido: «**AJUSTES (Menú principal) > AVANZADO (Submenú)** …
> dispone de 3 pestañas de configuración en este nivel, SISTEMA, OTROS y REINICIAR».
>
> **Consecuencia para el diagnóstico de este caso.** El caveat del bot («los fragmentos
> disponibles no detallan su contenido específico») era honesto **sobre la evidencia
> servida**, pero el corpus SÍ tenía el detalle. Así que el caso tiene **dos capas**, no una:
>
> 1. **SELECCIÓN** (lo ya diagnosticado, y sigue en pie): con AVANZADO delante en la
>    evidencia servida, compuso la ruta de GENERAL. Clase `hp011#2`, elemento vecino.
> 2. **RETRIEVAL — abierto, y NO medido**: ¿estaba el §5.4 del MC-380 en el pool de esa
>    consulta? Si NO estaba, este caso es (también) un retrieval-miss de documento-vecino
>    dentro de la MISMA familia de producto, y el veredicto «no alcanzable» de `hp011#2`
>    (DEC-173, oráculo 0/5→0/5) **no le aplica sin más**: aquel se midió con la evidencia
>    ideal de OTRO hecho, no con este documento delante.
>
> **SONDA CORRIDA (s303, 7-ago) — VEREDICTO: SÍNTESIS/SELECCIÓN PURA.**
> `scripts/s303_cad171_pool_probe.py`, recibo `evals/s303_cad171_pool_probe_v1.json`.
> Replay de la consulta LITERAL con la configuración de la demo (DEMO_FLAGS, misma fuente
> que el assessment) y **medido hasta la evidencia SERVIDA, no solo el pool** — el pool no
> es lo que ve el generador; el rerank recorta antes.
>
> | Etapa | Resultado |
> |---|---|
> | Pool (retrieval) | 34 chunks · **8 del MC-380** |
> | Chunks con el detalle del §5.4 (AVANZADO+SISTEMA+REINICIAR) | 3 en el pool |
> | **Evidencia SERVIDA (post-rerank)** | 10 chunks · **4 del MC-380** |
> | **El detalle del §5.4, SERVIDO** | **SÍ — en el rango 1**, y en 3 de 4 pasadas también una 2ª copia |
>
> Estabilidad: **K=4 pasadas, mismo veredicto** (el rerank es un LLM: una sola pasada no
> zanjaría). Representatividad: el mapeo `MC-380 → detnov:cad-171` entró en `doc_map.jsonl`
> en s91 y no se ha tocado desde s278 — **estaba vigente el 2-ago**, así que el replay no
> mide un mundo posterior al fallo.
>
> ⇒ **Retrieval queda DESCARTADO para este caso**: el bot tuvo el documento correcto y el
> párrafo correcto en el primer puesto de su evidencia, y aun así encabezó con la ruta de
> GENERAL. La familia doc-local / vecino estructural (s104/s107) **no aplica aquí**.
> ⇒ El caso pasa a ser **la 2ª instancia de la clase `hp011#2` medida CON la evidencia
> correcta delante**, y esta vez de uso REAL — es decir, coherente con el NO-GO de DEC-173
> (oráculo 0/5→0/5) en vez de contradecirlo.
> ### VEREDICTO FINAL (s304, tras el dúo) — SELECCIÓN DE SECCIÓN, dentro del documento correcto
>
> La pregunta de Alberto («¿ese catálogo estaba asociado a la CAD-171?») abrió dos rondas.
> Se dejan las dos, con lo que cayó, porque la traza importa más que el acierto:
>
> **Ronda 1 — mi hipótesis: «la identidad no llega al chunk».** Verificado que el `doc_map`
> dice `detnov:cad-171` primary y que los 136 chunks del MC-380 dicen `CAD-250`. De ahí
> deduje un defecto de propagación de identidad en el 57% del corpus.
>
> **Ronda 2 — el dúo la derribó, y con razón.** Tres cosas, todas verificadas contra el
> repo por mí:
> 1. **Mi instrumento tenía un bug real**: paginaba `limit/offset` SIN `ORDER BY`, así que
>    perdía entre el 12% y el 21% de los documentos, distintos en cada pasada. Sus cifras
>    no eran reproducibles. Corregido (`s304_identidad_propagacion.py` v2).
> 2. **La pregunta era la equivocada**: medía COINCIDENCIA DE ETIQUETA, no ALCANZABILIDAD.
>    La granularidad de familia (`pm='2X-A'` con 26 variantes en el mapa) es deliberada, no
>    un defecto.
> 3. **La identidad SÍ llega**, por otra vía que yo no comprobé antes de afirmar: el seam 2
>    doc_map-aware (`IDENTITY_RESOLVE=on` en Railway, DEC-084) y el `series_registry` —
>    que para ESTE caso declara desde s63/DEC-043 la serie Vesta `[CAD-171, CAD-201,
>    CAD-250]` con el MC-380 como `shared_docs`. El mecanismo llevaba un año resuelto.
>
> Con el instrumento corregido: **35 huérfanos (4,1%), 55 identidades**, y casi todas de ids
> `unresolved:` (candidatos sin adjudicar, que el catálogo declara que NO consume). No hay
> lever ahí.
>
> **Lo que queda, verificado, y es la respuesta al caso:** el bot tuvo servidos, en la MISMA
> pasada, el §5.4 AVANZADO (p.29 del MC-380, **rango 1**) *y* el §5.1 GENERAL (p.20 del
> mismo documento, **rango 4**) — y encabezó con la ruta del §5.1. No descartó el documento
> por su etiqueta: **respondió desde él, eligiendo la sección equivocada**. Y el manual
> propio de la CAD-171 (MI-716, 75 chunks etiquetados CAD-171) también estaba servido, con
> los diagramas que muestran AVANZADO como hermano de GENERAL.
>
> ⇒ **Fallo de SELECCIÓN DE SECCIÓN dentro del documento correcto, con la evidencia
> correcta delante.** El veredicto original de s303 era el bueno; mi «corrección» de la
> ronda 1 sobraba. Retrieval e identidad quedan DESCARTADOS para este caso, ahora por dos
> vías independientes.
>
> ⇒ ~~Sigue abierta … ¿el techo es del sistema o del MODELO?~~ **CERRADA (s305,
> DEC-186)**: medido con Sonnet 4.6 / Sonnet 5 / Opus 5 sobre el oráculo de DEC-173 —
> 0/3 firmes los tres. **El techo NO es del modelo.** Recibo:
> `evals/s305_techo_modelo_ab_v1.json`.

## La clase del fallo — y por qué importa más que el caso

No es un dato falso: la lista que dio es correcta. El fallo es de **SELECCIÓN**: encabezó con la
ruta de OTRO submenú (GENERAL, que él mismo etiqueta «básica») y **nunca compuso la ruta pedida**,
teniendo AVANZADO delante en la evidencia servida.

**Es la misma forma que `hp011#2`**: el bot tiene el dato servido y responde con el **elemento
vecino** — allí `r.i` (inhibición de rearme) en vez de `t.A` (duración de descarga), aquí GENERAL
en vez de AVANZADO. **Dos instancias de la misma clase, y esta viene de uso real.**

Esto matiza el argumento de s294 («ningún lever de síntesis se puede diseñar con n=1»): la clase
existe y empieza a poblarse sola en cuanto hay una persona usando el bot y un canal para
contarlo — que es exactamente lo que el paquete de telemetría acaba de habilitar.

## Lo que NO es: hueco de corpus para lo preguntado

El **acceso** al menú sí está en el manual que tenemos.

> ### ⚠️ CORRECCIÓN (s302, 6-ago — DEC-184): la «Guía Avanzada» TAMPOCO falta
>
> Este apartado decía que faltaba la «Guía Avanzada de Configuración» de la CAD-171, apoyado
> en que **ningún fichero de Detnov lleva «avanzada» en el NOMBRE**. Ese test era el
> equivocado — buscaba por nombre de fichero, no por contenido. La adjudicación de s302 lo
> desmontó:
>
> **El documento existe, está ingestado y está mapeado a la central.** Es
> `CAD-250_Manual-Configuracion-MC-380-es-2026-c`, cuyo control de revisiones (p.2) dice
> literalmente «**c · Adaptación para CAD-171 y CAD-201 · 23/04/2026**», que figura en
> `data/catalog/doc_map.jsonl` con **`detnov:cad-171` como `role: primary`** — y cuyo **§5.4,
> p.29** documenta exactamente lo pedido: «**AJUSTES (Menú principal) > AVANZADO (Submenú)** …
> dispone de 3 pestañas de configuración en este nivel, SISTEMA, OTROS y REINICIAR».
>
> **Consecuencia para el diagnóstico de este caso.** El caveat del bot («los fragmentos
> disponibles no detallan su contenido específico») era honesto **sobre la evidencia
> servida**, pero el corpus SÍ tenía el detalle. Así que el caso tiene **dos capas**, no una:
>
> 1. **SELECCIÓN** (lo ya diagnosticado, y sigue en pie): con AVANZADO delante en la
>    evidencia servida, compuso la ruta de GENERAL. Clase `hp011#2`, elemento vecino.
> 2. **RETRIEVAL — abierto, y NO medido**: ¿estaba el §5.4 del MC-380 en el pool de esa
>    consulta? Si NO estaba, este caso es (también) un retrieval-miss de documento-vecino
>    dentro de la MISMA familia de producto, y el veredicto «no alcanzable» de `hp011#2`
>    (DEC-173, oráculo 0/5→0/5) **no le aplica sin más**: aquel se midió con la evidencia
>    ideal de OTRO hecho, no con este documento delante.
>
> **SONDA CORRIDA (s303, 7-ago) — VEREDICTO: SÍNTESIS/SELECCIÓN PURA.**
> `scripts/s303_cad171_pool_probe.py`, recibo `evals/s303_cad171_pool_probe_v1.json`.
> Replay de la consulta LITERAL con la configuración de la demo (DEMO_FLAGS, misma fuente
> que el assessment) y **medido hasta la evidencia SERVIDA, no solo el pool** — el pool no
> es lo que ve el generador; el rerank recorta antes.
>
> | Etapa | Resultado |
> |---|---|
> | Pool (retrieval) | 34 chunks · **8 del MC-380** |
> | Chunks con el detalle del §5.4 (AVANZADO+SISTEMA+REINICIAR) | 3 en el pool |
> | **Evidencia SERVIDA (post-rerank)** | 10 chunks · **4 del MC-380** |
> | **El detalle del §5.4, SERVIDO** | **SÍ — en el rango 1**, y en 3 de 4 pasadas también una 2ª copia |
>
> Estabilidad: **K=4 pasadas, mismo veredicto** (el rerank es un LLM: una sola pasada no
> zanjaría). Representatividad: el mapeo `MC-380 → detnov:cad-171` entró en `doc_map.jsonl`
> en s91 y no se ha tocado desde s278 — **estaba vigente el 2-ago**, así que el replay no
> mide un mundo posterior al fallo.
>
> ⇒ **Retrieval queda DESCARTADO para este caso**: el bot tuvo el documento correcto y el
> párrafo correcto en el primer puesto de su evidencia, y aun así encabezó con la ruta de
> GENERAL. La familia doc-local / vecino estructural (s104/s107) **no aplica aquí**.
> ⇒ El caso pasa a ser **la 2ª instancia de la clase `hp011#2` medida CON la evidencia
> correcta delante**, y esta vez de uso REAL — es decir, coherente con el NO-GO de DEC-173
> (oráculo 0/5→0/5) en vez de contradecirlo.
> ### ⚠️⚠️ CORRECCIÓN DEL VEREDICTO (s304, 7-ago) — la pregunta de Alberto lo tumbó
>
> Alberto preguntó: «el bot tenía el catálogo, ¿pero ese catálogo estaba asociado a la
> CAD-171?». Verificado, y **mi veredicto de «síntesis pura» era DEMASIADO FUERTE**:
>
> | Capa | Qué dice |
> |---|---|
> | `doc_map.jsonl` (identidad ADJUDICADA) | MC-380 rev c → `detnov:cad-171` **primary** ✓ |
> | `chunks_v2.product_model` (lo que VIAJA al generador) | **136 de 136 chunks: `CAD-250`. Ninguno CAD-171** ✗ |
>
> Y el generador lee el CHUNK, no el mapa (`generator.py:704`). Así que el bot tuvo delante
> el párrafo correcto **etiquetado con OTRO modelo de central**. Su cautela —«los fragmentos
> disponibles no detallan su contenido específico»— es **defendible**: no trasladar el
> detalle de una CAD-250 a una CAD-171 es la conducta que se le exige a un bot de PCI.
>
> **Lo que SIGUE siendo fallo suyo, sin atenuante**: encabezar con `AJUSTES > GENERAL` como
> ruta a la configuración avanzada. Eso no depende del MC-380 — está en el manual PROPIO de
> la CAD-171 (MI-716, etiquetado CAD-171), cuyos 3 diagramas muestran AVANZADO como HERMANO
> de GENERAL. **Error de SELECCIÓN, confirmado, pero acotado a la RUTA.**
>
> **Lo que ya NO se sostiene**: «el modelo tuvo la evidencia correcta delante y aun así
> falló» como prueba de techo de síntesis. La evidencia estaba, sí, pero contradictoriamente
> etiquetada. El caso deja de ser instancia limpia del techo `hp011#2`.
>
> **Y lo que aparece en su lugar es MEJOR, porque es arreglable** (`scripts/s304_identidad_propagacion.py`,
> recibo `evals/s304_identidad_propagacion_v1.json`):
>
> **TABLA RETIRADA (dúo s304, DEC-185) — NO USAR ESTAS CIFRAS.** El instrumento v1
> paginaba sin ORDER BY (perdía 12-21% de docs POR PASADA) y medía coincidencia de
> etiqueta en vez de alcanzabilidad. Cifras reales del v2: **4,1% / 55 ids**, casi
> todos `unresolved:`. Se conserva solo como registro de la ronda:
>
> | *(retirada)* | |
> |---|---|
> | ~~Documentos con identidad primaria adjudicada y chunks~~ | ~~732~~ |
> | ~~Huérfanos~~ | ~~414 = 57%~~ |
> | ~~Identidades primarias que no llegan al generador~~ | ~~1.112~~ |
> | ~~Huérfanos con UN SOLO product_model~~ | ~~414 de 414~~ |
>
> Esa última fila es la firma estructural del defecto: **la ingesta asigna UN modelo por
> documento**, mientras la identidad adjudicada dice N. Todo el trabajo de s83/s91/s278
> (miles de adjudicaciones, algunas de Alberto a mano) muere en esa frontera para más de la
> mitad del corpus. Ejemplos: un manual de la serie 2X-A pierde 26 variantes Kidde; el de
> barreras Zener, 64; el MC-380, la CAD-171 **y** la CAD-201.
>
> **Alcance honesto de lo medido**: se ha medido la BRECHA, no su impacto en respuestas.
> `retrieve_chunks` NO filtra duro por `product_model` (verificado: el pool trajo chunks
> `CAD-250` con la consulta de CAD-171), así que el efecto no es supresión total; lo medido
> es que el generador ve etiquetas que contradicen la identidad adjudicada — y en el único
> fallo orgánico que tenemos, eso coincidió con una respuesta con hedge. Traducirlo a PASS
> exige eval, no inferencia.

⇒ **Candidato de adquisición**: Guía Avanzada de Configuración, CAD-171 (Detnov).

**Punto ciego declarado de la lista de adquisición** (`scripts/s294_citation_gap.py`): solo caza
referencias **con código de documento**; esta se cita **por nombre** («consulte la Guía Avanzada
de Configuración») y por tanto es invisible para el barrido. Medido en 3.000 chunks: 5
remisiones a documento nombrado, 4 sin código — punto ciego real pero **pequeño**, y casi todas
apuntan a *secciones* de manuales, no a documentos ausentes. Se declara en vez de construir un
segundo detector para ~4 casos.

## Propuesta (adjudica Alberto — DEC-025: el gold es suyo)

**Candidato a gold** para la sentada B2, ficha propuesta:

- **Pregunta**: «¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?»
- **Hecho 1** (acceso): desde la PANTALLA DE REPOSO, icono del candado → PANTALLA DE ACCESO →
  clave de administrador por defecto **2222**.
- **Hecho 2** (ruta): **AJUSTES (Menú principal) > AVANZADO (Submenú)** — AVANZADO es un ítem del
  submenú de AJUSTES, hermano de GENERAL.
- **Hecho 3** (alcance, opcional): el contenido de AVANZADO no se detalla en `MI-716`; remite a la
  Guía Avanzada de Configuración.
- **Fuente**: `Manual_CAD-171-MI-716-es` p.25 §6.1 y los diagramas de p.26/34/35.
- **Por qué es buen gold**: respuesta COMPUESTA (acceso + ruta exacta) sobre evidencia servida,
  y discrimina justo la clase de fallo «elemento vecino» que ya tiene dos instancias.
