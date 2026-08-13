# s294 — Packet de la sentada B2 · 10 ítems para tu adjudicación en lote

> **Cómo usarlo (~25-30 min).** Cada ítem trae: la **pregunta** del gold, el **hecho** tal como
> está escrito hoy, **qué dijo el bot** (respuesta congelada del FULL v3.2), la **evidencia
> medida**, y **mi recomendación** con la decisión concreta que te pido. Marca por ítem:
> `[ ] ✅ acepto · [ ] ✏️ editar (anota el matiz) · [ ] ❌ rechazo`.
> Yo aplico después las ✅/✏️ vía `gold_store` (la puerta valida; DEC-025: **el gold es tuyo**).
> **Nada se edita sin tu marca.**

**Qué hay en juego.** De los 12 synthesis-miss del FULL, **3 son gold/alcance** y otros **2**
se han vuelto candidatos esta sesión al medirlos. Si aceptas mis recomendaciones, el
denominador y la clasificación cambian —no el bot— y la foto pasa a reflejar lo que el bot
hace de verdad. **En 2 ítems mi lectura DISCREPA del triage previo de s291c**: los marco
explícitamente, porque son justo los que necesitan tu criterio de PCI y no el mío.

---

## 1 · `hp008#4` — LPB500 · **DISCREPO del triage previo**

**Pregunta:** «¿Qué detectores de humo analógicos son compatibles con la Notifier ID3000?»
**Hecho (hoy):** «Detectores de humo por rayo/haz proyectado compatibles: LPB500 (máx. 4 por
lazo) y LPB-700/LPB-700T».
**Qué dijo el bot:** enumeró los puntuales y los de entornos especiales (HPX-751E, IDX-751) y
cerró con el protocolo Notifier. **Cero menciones de detectores de haz/rayo.** Respuesta corta
(1.188 caracteres).
**Medido:** el fragmento estaba servido en posición 2/10 y citado.

- **s291c lo triaba como «alcance del gold»** (la pregunta no contrataría los de haz).
- **Yo discrepo**: un detector de haz **es** un detector de humo y va en el mismo lazo. Un
  técnico que pregunta «qué detectores de humo analógicos son compatibles» espera verlos. Si
  esto es alcance, entonces la respuesta correcta es incompleta por definición.

**Mi recomendación:** **mantener CORE** y reclasificar la miss como **síntesis real**
(incompletitud de enumeración), no como problema de gold. **Decisión que te pido:** ¿un
detector de haz cuenta como «detector de humo analógico» para un técnico? Si dices que no,
acoto la pregunta a «detectores puntuales» y el hecho pasa a SUPPLEMENTARY.

`[X] ✅ es síntesis (mantener CORE) · [ ] ✏️ acotar la pregunta a puntuales · [ ] ❌ otra cosa`

---

## 2 · `hp011#2` — t.A «05 a 295 seg» · **el más consecuente**

**Pregunta:** «En la Morley RP1r, después de descargar la extinción el sistema no vuelve a
estado normal tras resetear. ¿Qué comprobar?»
**Hecho (hoy):** «Parámetro **t.A** "Duración de la descarga" (soak time): variable de 05 a 295
seg; "--" = circuito activado hasta el rearme de la central (POR DEFECTO)».
**Qué dijo el bot:** abre con «**1. Verifica si el rearme está inhibido por parámetro de
configuración**» y desarrolla el parámetro **`r.i`** (Rearme inhibido tras extinción), con sus
valores y el caso `- -`.
**Medido esta sesión (sonda de alcanzabilidad):** inyecté las DOS mitades del hecho (etiqueta
`t.A` + tabla del valor) en la vista del generador y las admitió — y aun así **0/5 en 3 de 3
repeticiones**: ni menciona el «295». No es que no lo tenga: **elige contestar con `r.i`**.

- Y `r.i` es una respuesta **defendible**: «rearme inhibido tras extinción» ataca literalmente
  «no vuelve a estado normal tras resetear».

**Mi recomendación:** el gold está **infra-especificado**. O bien `r.i` se acepta como
comprobación válida (y el hecho `t.A` pasa a SUPPLEMENTARY), o bien la pregunta se afila a la
duración de la descarga. **Sin esto, seguiremos contando como fallo de síntesis algo que
probablemente es una respuesta correcta distinta de la esperada.**

`[ ] ✅ aceptar r.i (t.A → SUPPLEMENTARY) · [ ] ✏️ afilar la pregunta · [ ] ❌ t.A es la única válida`

---

## 3 · `hp017#2` — «Editar Configuración» + «borrar la Regla 1» · **hecho compuesto**

**Pregunta:** «¿Cómo se programa el retardo de salida de alarma principal en la Notifier PEARL?»
**Hecho (hoy):** dos mitades en una — (a) acceder a «Causa y Efecto» desde el menú «**Editar
Configuración**»; (b) **borrar la Regla 1** por defecto si se va a programar específico.
**Medido esta sesión:** la mitad (a) **el modelo la escribe siempre** (3/3) y **el conflict-guard
la borra** (3/3, porque en la fuente va pegada al número de menú en conflicto). La mitad (b)
**no aparece nunca** (0/3, con cinco marcadores incluidas paráfrasis). Con el juez canónico, el
borrador PRE-guard se queda en 3/5 · 1/5 · 2/5 — **por debajo del umbral aunque el guard no
existiera**.

**Mi recomendación:** **partir el hecho en dos**. Así (a) queda medible contra el guard —y su
NO-GO de hoy queda bien atribuido— y (b) se mide como lo que es: una omisión de síntesis
independiente.

`[ ] ✅ partir en dos · [ ] ✏️ partir y además reformular (anota) · [ ] ❌ dejarlo compuesto`

---

## 4 · `cat018#2` — «Tipo SW / asociación CBE» · **hecho compuesto**

**Pregunta:** «¿Cómo se programa una ecuación causa-efecto (CBE) en la Notifier AM-8200…?»
**Hecho (hoy):** «Los módulos de SALIDA llevan un **Tipo SW** (p. ej. SND = sirena); un módulo
de salida se dispara cuando se cumple su **ecuación CBE**».
**Qué dijo el bot:** respuesta larga (3.831 caracteres) sobre CBE, con **cero** apariciones de
«Tipo SW», «SND» o «asociación». El sub-motivo del juez fue `partial`.

**Mi recomendación:** **partir en dos** (el «Tipo SW» del módulo · el disparo por ecuación CBE)
y volver a medir. Es lo que ya proponía el diagnóstico de s291c y lo suscribo.

`[ ] ✅ partir en dos · [ ] ✏️ editar el texto (anota) · [ ] ❌ dejarlo`

---

## 5 · `hp006#2` — ISO-X

**Pregunta:** «La Notifier AFP-400 muestra el aviso "Tierra" (Earth Fault). ¿Qué significa y
cómo se localiza?»
**Hecho (hoy):** los módulos aisladores **ISO-X** acotan la rama en avería del resto del lazo
(requeridos para Estilo 7 según NFPA).
**Qué dijo el bot:** procedimiento de localización en 4 pasos (bandeja/canaleta, humedad,
aislamiento dañado, bloque TB1 de la MPS-400). Menciona «aislamiento» del cable, **no** los
módulos ISO-X.

**Mi recomendación:** **demote a SUPPLEMENTARY**. Los ISO-X aíslan cortocircuitos de lazo; la
localización de un fallo **de tierra** se hace por desconexión por tramos, que es lo que el bot
explica. Es adyacente, no contratado. **Pero esto es criterio de PCI y es tuyo**: si en tu
práctica el ISO-X es parte del procedimiento de acotado de tierra, dilo y se queda CORE.

`[ ] ✅ demote a SUPPLEMENTARY · [ ] ✏️ se queda CORE (explica) · [ ] ❌ borrar el hecho`

---

## 6 · `cat020#2` — meta-ref del manual de variaciones España

**Pregunta:** «En una central Morley DXc instalada en España, ¿cuál es el nivel de alarma y de
prealarma por defecto…?»
**Estado:** el hecho está marcado `meta-ref` y **sin `texto`**.
**Qué dijo el bot:** cita explícitamente «**DXc_Manual variaciones de mercado**» como fuente y
reproduce el matiz de que el umbral depende del nivel/modo.

**Mi recomendación:** aplicar lo que ya dejaste escrito en el PLAN — el **valor** pasa a
«específicos de la versión España» y la referencia al manual de variaciones se convierte en
**expectativa de CITA** (que la respuesta actual ya cumple).

`[ ] ✅ aplicar · [ ] ✏️ otra redacción (anota) · [ ] ❌ dejarlo`

---

## 7 · `hp001#2` — clave «1111» (afilar redacción)

**Estado:** es **retrieval-miss**, no síntesis (`within-doc`); entra aquí solo por la edición
pendiente. **Hecho (hoy):** «La clave de USUARIO por defecto es 1111, que NO da acceso a la
configuración avanzada completa (solo el nivel de usuario)».
**Mi recomendación:** afilar el **`texto`** sin tocar el **`valor`**, para reducir fragilidad
del juez (lo dejaste escrito en el PLAN). Propuesta concreta: dejar el hecho en «clave de
usuario por defecto **1111**; el acceso a configuración avanzada **requiere otra clave/nivel**»,
sin la negación larga.

`[ ] ✅ aplicar la propuesta · [ ] ✏️ tu redacción (anota) · [ ] ❌ dejarlo`

---

## 8 · `hp002` — la pregunta dice «de Detnov»

**Pregunta (hoy):** «El detector ASD535 **de Detnov** está dando una alarma intermitente…»
**Problema:** el ASD535 es **Securiton**, distribuido por Detnov — y así lo dice ya `hp019`
(«ASD535 (Securiton, distribuido por Detnov)»). Los 5 hechos de hp002 salen **OK**, así que
esto no cambia ninguna métrica: es coherencia del gold.
**Mi recomendación:** armonizar la pregunta con la de hp019.

`[ ] ✅ armonizar · [ ] ✏️ otra redacción · [ ] ❌ dejarlo`

---

## Efecto esperado si aceptas todo

- **2 hechos compuestos partidos** (`hp017#2`, `cat018#2`) → dejan de contar como una miss
  opaca y pasan a medir dos cosas distintas; el denominador sube en 2.
- **2 reclasificaciones** (`hp006#2` a supplementary, `hp011#2` a gold infra-especificado) →
  salen de la cola de síntesis, que quedaría en **~1-2 hechos de ingeniería real**.
- **1 discrepancia que puede ir en mi contra** (`hp008#4`): si me das la razón, la cola de
  síntesis **sube** en un hecho legítimo. Lo digo porque el packet no está montado para que
  salgan las cuentas bonitas.
- `cat020#2`, `hp001#2` y `hp002` son higiene: no mueven el número, reducen fragilidad.

**Lo que NO te pido:** nada sobre `hp013#1` ni `hp017#1` (techo declarado), ni sobre los flips
(`cat001#3`, `cat020#1`, ruido), ni sobre `hp009#0` (centinela de conducta).

---

## 9 · **NUEVO — candidato a gold nacido de USO REAL** (CAD-171, menú avanzado)

No es una edición de un gold existente: es una **ficha nueva** que propongo, y sale del primer
caso que entró por el canal de feedback que acabamos de construir (tu 👎 + explicación del 2-ago).

**El fallo, verificado contra la fuente:** preguntaste cómo acceder al menú de configuración
avanzada de la CAD-171 y el bot encabezó con «AJUSTES > **GENERAL**» —que él mismo etiqueta como
configuración *básica*— sin componer nunca la ruta pedida. El manual (`Manual_CAD-171-MI-716-es`,
tres diagramas coincidentes en p.26/34/35) deja claro que **AVANZADO es hermano de GENERAL**
dentro del submenú de AJUSTES, y usa esa misma notación para otras rutas («AJUSTES > TEST >
INICIAR»). La respuesta correcta era **«AJUSTES (Menú principal) > AVANZADO (Submenú)»**, tras
entrar como administrador con la clave **2222**.

**Ficha propuesta:**
- **Pregunta**: «¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?»
- **Hecho 1** — acceso: candado en la PANTALLA DE REPOSO → clave de administrador **2222** (p.25 §6.1).
- **Hecho 2** — ruta: **AJUSTES (Menú principal) > AVANZADO (Submenú)**.
- **Hecho 3** (opcional, alcance): el contenido de AVANZADO no está en `MI-716`; remite a la Guía
  Avanzada de Configuración — ~~que no tenemos (candidato de adquisición)~~.
  **⚠️ CORRECCIÓN (s302-s303, antes de que adjudiques con el dato viejo)**: la «Guía
  Avanzada» ES el `MC-380 rev c` que YA tenemos ingestado y mapeado a `detnov:cad-171`
  — con la ruta correcta (§5.4, p.29) que además llegó SERVIDA en rango 1 (sonda s303).
  El candidato de gold sigue teniendo sentido, pero como caso de SELECCIÓN DE SECCIÓN
  con la evidencia delante (veredicto final s304), no como hueco de corpus.

**Por qué merece entrar**: respuesta COMPUESTA sobre evidencia ya servida, y discrimina la clase
de fallo «responde con el elemento vecino», que ya tiene **dos** instancias (esta y `hp011#2`,
donde el bot contestó con `r.i` en vez de `t.A`). Detalle completo en
`evals/s294_cad171_menu_avanzado_v1.md`.

`[ ] ✅ crear el gold · [ ] ✏️ crearlo con cambios (anota) · [ ] ❌ no crearlo`


---

## 10 · `hp011#2` — rango vs default del parámetro `t.A` · ⛔ **EVIDENCIA RETIRADA (s320c) — NO ADJUDICAR**

> ⛔ **s320c (12-ago-2026)**: todo lo que sigue se apoya en una cifra que **nunca salió del juez**
> (el script de s305 sumaba sobre las CLAVES del dict ⇒ constante 2; TECH_DEBT #75). En particular,
> «no es un fallo de un modelo · los tres coinciden en describir el DEFAULT» es **falso en 4 de las
> 9 respuestas** del propio recibo, que citan el rango verbatim. Este packet es **v1**: el vigente
> es `evals/s312_goldreview_b2_packet_v3.md`, donde el ítem está fusionado y marcado NO ADJUDICAR.
> Se conserva como registro.

**Pregunta:** «El sistema no vuelve a estado normal tras resetear después de una extinción»
(RP1r-Supra).
**Hecho (hoy):** el gold espera el **RANGO** del parámetro `t.A` (05 a 295 segundos).
**Qué dijo el bot:** describe el **DEFAULT** («--» = el circuito de extinción queda activado
hasta el rearme de la central) — y este es el matiz nuevo: **no es un fallo de un modelo**.

**Medido (s305, DEC-186 · `evals/s305_techo_modelo_ab_v1.json`)**: oráculo de evidencia
perfecta de DEC-173 reusado tal cual (las dos mitades del hecho inyectadas, juez K=5, 3
repeticiones), única variable el generador → **Sonnet 4.6, Sonnet 5 y Opus 5: 0/3 firmes
los tres (máx 2/5; 9 respuestas distintas — sin caché; testigo del modelo enviado en
verde)**. Los tres modelos, con el rango DELANTE, eligen contar el default.

- **Mi lectura**: ante ESTA pregunta (un síntoma de troubleshooting: «no vuelve a estado
  normal»), el dato operativo es el default — explica POR QUÉ no vuelve. El rango es lo que
  responderías a «¿qué valores admite t.A?», que es otra pregunta. Tres generaciones de
  modelos coinciden en esa lectura; forzar el rango aquí mediría obediencia al gold, no
  utilidad para el técnico.

**Mi recomendación:** **re-acotar el hecho al default** (el rango pasa a SUPPLEMENTARY o a
un gold propio con la pregunta directa «¿qué valores admite t.A?»). **Decisión que te
pido:** ¿qué esperaría un técnico de PCI ante ese síntoma — el default que explica el
comportamiento, o el rango configurable?

`[ ] ✅ re-acotar al default · [ ] ✏️ split en dos golds (anota) · [ ] ❌ mantener el rango (techo declarado)`
