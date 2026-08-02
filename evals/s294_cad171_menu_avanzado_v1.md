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

El **acceso** al menú sí está en el manual que tenemos. Lo que falta es la **«Guía Avanzada de
Configuración»** de la CAD-171: verificado, **ningún fichero de Detnov en el corpus lleva
«avanzada» en el nombre** (de la CAD-250 sí tenemos sus dos manuales de configuración). El
caveat del bot era honesto.

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
