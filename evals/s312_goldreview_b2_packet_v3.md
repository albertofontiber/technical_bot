# s312 — Packet de la sentada B2 · **v3, tras dúo doble** · 9 decisiones

> **Linaje**: v1 (s294, 9 ítems) → +ítem 10 (s307) → **v3 (s312)**: revisado por el dúo
> completo a petición de Alberto — sub-agente Fable fresco (recibos abiertos ENTEROS) +
> GPT-5.6 Sol xhigh. Convergieron en 2 críticos y 7 medios/menores; TODOS incorporados
> aquí. v1 queda como registro. Tally: `evals/adversarial_review_log.jsonl` (s312).
>
> **Cómo usarlo (~25-30 min).** Cada ítem: pregunta · hecho · qué dijo el bot · evidencia
> medida · recomendación. Marca: `[ ] ✅ · [ ] ✏️ (anota) · [ ] ❌`. Yo aplico después vía
> `gold_store` (DEC-025: **el gold es tuyo**). Nada se edita sin tu marca.
>
> **⚠️ Staleness del generador, declarada (dúo)**: todas las «respuestas congeladas»
> citadas son del FULL v3.2 generado con `claude-sonnet-4-6`; producción corre **Opus 5
> desde s308**. Para los ítems de ALCANCE (1, 3, 4, 5, 6, 8) la decisión es
> independiente del generador (adjudicas qué contrata la pregunta, no cómo respondió un
> modelo). ~~El eje modelo del hp011#2 está medido aparte (s305) y su ítem lo incorpora.~~
> **RETIRADO (s320c)**: esa medición nunca leyó al juez — ver el ⛔ del ítem 2 y `TECH_DEBT` #75.
>
> ---
>
> ## 📌 Estado tras la revisión s320c (12-13 ago) — LÉEME ANTES DE MARCAR
>
> El ítem 2 está **retirado**. Los 7 restantes pasaron por: auditoría ciega (8 agentes) →
> **pase de falsación con el prior contrario** (la auditoría sobre-acusó en 5 de 7; ninguno resultó
> no-marcable) → recomendación por ítem → **dúo Sol xhigh + Fable 5** sobre esas recomendaciones.
> El dúo tumbó la mitad-de-alcance de varias por **circularidad** (justificarlas con el scorer, el
> serving o el marcador en vez de con la fuente). Lo que sobrevive está abajo, ítem por ítem, en un
> bloque `s320c` con tres cosas separadas: **qué escribe la marca · qué dice la FUENTE · qué decides
> tú**. Donde no hay recomendación, es porque no me la he ganado.
>
> **Ruptura de serie declarada**: si marcas los splits, el denominador pasa de 131 clasificados
> (133 cores) a ~134; los porcentajes congelados del scoreboard **no son comparables** después. Una
> sola re-medición cubre todo el conjunto — conviene cerrar los 7 en la misma sentada.

---

## 1 · `hp008#4` — LPB500 · **DISCREPO del triage previo** — ✅ YA MARCADO POR TI

**Pregunta:** «¿Qué detectores de humo analógicos son compatibles con la Notifier ID3000?»
**Hecho (hoy):** «Detectores de humo por rayo/haz proyectado compatibles: LPB500 (máx. 4 por
lazo) y LPB-700/LPB-700T».
**Qué dijo el bot:** enumeró los puntuales y los de entornos especiales (HPX-751E, IDX-751) y
cerró con el protocolo Notifier. **Cero menciones de detectores de haz/rayo.** Respuesta corta
(1.196 caracteres — corregido, era «1.188»).
**Medido:** fragmento servido en posición 2/10 y citado (s291c:19). **Dúo: evidencia VIVA,
verificada exacta contra FULL:6684-6902** (conveyed 0/5, `omitted` 5/5, `reaches_gen: true`).

- **s291c lo triaba como «alcance del gold»**; yo discrepo: un detector de haz **es** un
  detector de humo y va en el mismo lazo. El dúo confirma el fork como honesto y bien
  presentado — la cuestión residual es criterio PCI tuyo.

`[X] ✅ es síntesis (mantener CORE) · [ ] ✏️ acotar la pregunta a puntuales · [ ] ❌ otra cosa`
*(tu marca de v1, arrastrada intacta)*

---

## 2 · `hp011#2` — `t.A`: r.i / default / rango · ⛔ **NO ADJUDICAR — evidencia retirada (s320c, 12-ago)**

> ⛔ **NO marques ninguna de las opciones de este ítem.** La capa 2 de su evidencia (s305) **nunca
> midió nada**: el script sumaba sobre las CLAVES del dict que devuelve el juez ⇒ la cifra valía
> **siempre 2**, en las 9 reps de los 3 brazos, sin consultar al juez. El «máx 2/5 uniforme» que
> este ítem interpretaba como «umbral del juez sobre el hecho compuesto» **no existe** (TECH_DEBT
> #75). Re-juzgadas las respuestas que el recibo sí guardó, con el juez canónico y en dos corridas
> idénticas: **sonnet-4-6 2/3 firmes · opus-5 2/3**, con correlación **9/9** entre «firme» y la
> aparición literal del valor ⇒ el juez discrimina limpio, y en **4 de las 9 respuestas de aquella
> corrida el hecho SÍ se transmitió entero** (rango + default). Es decir: las opciones A y B te
> pedían **recortar el alcance de un gold legítimo para compensar un fallo que nunca se midió**, y
> la C se apoyaba en una «fragilidad del juez» que la correlación 9/9 desmiente.
>
> **Precisión (dúo s320c)**: esto NO dice «el techo era del modelo». Con el brazo de control
> transmitiendo, lo que corresponde es «montaje no comparable» — la corrida del 7-ago contradice a
> la del 2-ago (s293, medición válida) con el mismo modelo. Queda **inconcluyente**, y por eso hace
> falta la medición fresca antes de que este ítem vuelva —o no— a la sentada.
>
> ✅ **RE-MEDICIÓN FRESCA HECHA (s320c, `evals/s320c_techo_modelo_ab_v2.json`, 5 reps/brazo): el
> hecho SÍ es alcanzable hoy en los TRES brazos** — sonnet-4-6 1/5 firmes · sonnet-5 1/5 · opus-5
> **4/5**, max 5/5 los tres.
>
> ⚠️ **Lo que esto retira es la EVIDENCIA, no la pregunta de alcance** (crítico de Sol sobre mi
> primera redacción de este banner, s320c). Decir «el gold es legítimo porque el bot SÍ transmite el
> hecho» sería el mismo pecado en sentido contrario: la alcanzabilidad **no decide** si una pregunta
> de troubleshooting contrata el rango, el default o `r.i` — eso se resuelve contra la FUENTE y tu
> criterio PCI (DEC-025 · `RULER_DESIGN §2`). Así que: **las tres opciones A/B/C quedan sin
> evidencia que las sostenga y no deben marcarse**; si en algún momento quieres adjudicar el alcance
> de `t.A`, se hace de cero y solo con la fuente delante.
>
> Lo que el número sí destapa **es materia de ingeniería, no de sentada**: la transmisión es
> **inestable** (6/15 firmes teniendo la evidencia perfecta delante) y la inyección del carrier
> aporta un **delta** claro (`base` 0/5 en 14 de 15). Ojo, eso NO localiza el hueco en serving: base
> y oráculo son generaciones independientes y el recibo no guarda la composición servida por rep.
>
> **Los otros ítems del packet NO CITAN s305** — que es distinto de «están sanos»: verificado el
> grafo de citas, no re-verificada cada premisa.
>
> Recibos: `evals/s320c_rejudge_s305_stored_v1.json` · el roto
> `evals/s305_techo_modelo_ab_v1.json` se conserva como prueba.

*(lo de abajo queda como registro de lo que el packet pedía antes de retirarse la evidencia)*

> **Por qué la fusión (crítico CONVERGENTE del dúo)**: v1 te pedía DOS decisiones sobre el
> MISMO hecho con opciones contradictorias (ítem 2: «t.A entero → SUPPLEMENTARY» · ítem 10:
> «re-acotar t.A al default»). Marcar ambas = adjudicación inconsistente. Aquí va UNA
> decisión con el mapa completo.

**Pregunta:** «En la Morley RP1r, después de descargar la extinción el sistema no vuelve a
estado normal tras resetear. ¿Qué comprobar?»
**Hecho (hoy):** «Parámetro **t.A** "Duración de la descarga" (soak time): variable de 05 a
295 seg; "--" = circuito activado hasta el rearme (POR DEFECTO)».

**La evidencia, en tres capas (todas verificadas contra recibo por el dúo):**

1. **s293 (sonda de alcanzabilidad, generador prod de entonces)**: con las DOS mitades
   inyectadas y admitidas → 0/5 en 3/3; ninguna respuesta escribe «295». El bot abre con el
   parámetro **`r.i`** (Rearme inhibido) — **matiz del dúo**: los oráculos TAMBIÉN dan la
   sección t.A-default en 2 de 3 reps («§4 Comprueba el parámetro t.A»); no es solo r.i.
2. **s305 (3 generadores: Sonnet 4.6 / Sonnet 5 / Opus 5)**: 0/3 firmes los tres, máx 2/5.
   **⚠️ CORRECCIÓN DEL DÚO A MI PROSA DE v1**: escribí «los tres modelos eligen contar el
   default» — **FALSO leyendo las respuestas**: el rango `05 a 295` aparece LITERAL en ≥4
   de las 9 (Sonnet 4.6 en 2/3, Opus 5 en 2/3; solo Sonnet 5 en 0/3; respuestas del recibo
   truncadas a 1.500 chars, podría haber más) **y aun así el juez da 2/5 uniforme**. El 2/5
   mide el UMBRAL DEL JUEZ sobre el hecho compuesto (rúbrica «ante la duda, no»), no una
   preferencia de los modelos. La conclusión de ingeniería «no hay lever de modelo» se
   sostiene; el «consenso de modelos por el default» NO.
3. **Divergencia declarada (v1 no lo decía; DEC-186 sí)**: el control de s293 dio 0/5 y el
   de s305 dio 2/5 — corpus tocado entre medias; ambos bajo umbral.

**Decisión ÚNICA que te pido** (opciones reconciliadas, incluida la tercera vía que v1 no
ofrecía):

`[ ] ✅ A· aceptar r.i/t.A-default como comprobación válida → t.A-rango a SUPPLEMENTARY`
`[ ] ✅ B· split: este gold espera default+r.i (síntoma); el RANGO se va a un gold propio («¿qué valores admite t.A?»)`
`[ ] ✅ C· AFILAR valor/texto del hecho contra la fragilidad del juez (el rango APARECE y no se acredita — mismo remedio que el ítem 7) y re-medir antes de reclasificar`
`[ ] ✏️ combinación/otra (anota) · [ ] ❌ mantener tal cual (techo declarado)`

---

## 3 · `hp017#2` — «Editar Configuración» + reglas por defecto · **hecho compuesto**

**Pregunta:** «¿Cómo se programa el retardo de salida de alarma principal en la Notifier PEARL?»
**Hecho (hoy):** dos mitades — (a) acceder a «Causa y Efecto» desde «**Editar Configuración**»;
(b) borrar la(s) regla(s) por defecto si se programa específico.
**Medido (dúo: verificado EXACTO contra los 3 recibos s293):** (a) el modelo la escribe 3/3 y
el conflict-guard la borra 3/3; (b) 0/3 con cinco marcadores incluidas paráfrasis; PRE-guard
3/5·1/5·2/5 — bajo umbral aunque el guard no existiera.
**Matiz del dúo (Sol)**: la fuente ordena eliminar **las DOS reglas de causa-efecto por
defecto**, no solo «la Regla 1» — la redacción singular de v1 no debe perpetuarse en el split.

**Mi recomendación:** **partir el hecho en dos**, con la mitad (b) redactada sobre «las reglas
por defecto» (ambas), y si quieres semántica específica de la Regla 1, como matiz aparte.

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **⚠️ Corrección del marco de evidencia**: el «(b) 0/3» de arriba sale de 3 reps en las que el
> carrier de la p43 **no figura en `served_ids` de ninguna** ⇒ al modelo nunca se le puso ese texto
> delante. Eso mide RETRIEVAL, no alcance. **Ese número no debe pesar en tu marca.**
>
> **La fuente, que es lo que sí decide:**
> - **p43** (citada en el `citations` de este mismo gold): «Es fundamental borrar **la regla 1** si
>   se va a realizar una programación específica, **ya que, si no, esta será anulada**». Singular, y
>   con el mecanismo.
> - **p45**: «las dos reglas de causa-efecto por defecto. Deben eliminarse si se van a crear reglas
>   personalizadas». Plural, sin mecanismo. **No está en el `citations` del gold.**
>
> **⚠️ Trampa de la opción ✅ («ambas reglas»)**: re-ancla la exigencia a p45, que es (i) casi
> literal lo que la respuesta congelada ya escribe, (ii) lo que un apéndice must-preserve
> **determinista** vuelca solo, y (iii) los marcadores exactos de una obligación ya cableada en
> `answer_planner`. El gold pasaría a medir **si disparó un renderer**, no si el bot sabe. Y dejaría
> el gold citando p43 para una afirmación plural que p43 no hace.
>
> **Mi recomendación: ✏️ partir + reformular** la mitad (b) con el operando de p43 («borrar la
> Regla 1 — CUALQUIER entrada activa TODOS los equipos de salida — porque anula la programación
> específica»), y **añadir la quote de p45 al `citations`** si quieres el alcance plural anclado.
> *(Divergencia del dúo, adjudicada: Fable pedía APLAZAR por la premisa no sondada; Sol decía
> adelante. Voy con Sol — la premisa no sondada era «¿pagaría un lever?», que es otra pregunta; el
> alcance lo resuelve la fuente. Pero el marco de medición del ítem sí se retira, arriba.)*
>
> **Tuyo:** ¿la respuesta debe decirle al técnico **qué regla le anula el retardo y por qué**, o
> basta «hay dos por defecto, bórralas»? Y: ¿en obra se borra **también la Regla 2** (tecla
> EVACUACIÓN activa todos los equipos), o esa se conserva?
>
> **Escribe**: hp017 pasa de 5 a 6 cores · renumera `hp017#3→#4` · rompe el join con artefactos
> congelados que indexan por `qid#idx`.

`[ ] ✅ partir en dos (redacción "ambas reglas") · [ ] ✏️ partir + reformular (anota) · [ ] ❌ dejarlo compuesto`

---

## 4 · `cat018#2` — «Tipo SW / asociación CBE» · **hecho compuesto**

**Pregunta:** «¿Cómo se programa una ecuación causa-efecto (CBE) en la Notifier AM-8200…?»
**Hecho (hoy):** «Los módulos de SALIDA llevan un **Tipo SW** (p. ej. SND = sirena); un módulo
de salida se dispara cuando se cumple su **ecuación CBE**».
**Qué dijo el bot:** respuesta larga (3.862 chars — corregido, era «3.831») sobre CBE, **cero**
«Tipo SW»/«SND»/«asociación»; la mitad disparo-por-CBE SÍ la desarrolla (refuerza el split).
Sub-motivo `partial` 4/5 (FULL:3660-3664).
**Declarado (dúo)**: en s291c el refutador adversarial de ESTA fila fue el único caído por
crédito — el split llega sin refutación completada; lo sabes al marcar.

**Mi recomendación:** **partir en dos**. **Opción añadida por el dúo (Sol)**: al partir puedes
adjudicar alcances DISTINTOS — «asociación/disparo CBE» CORE y «Tipo SW/SND» SUPPLEMENTARY
respecto de «cómo programar una CBE».

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **La fuente (leída en s320c, y es la que justifica el split):**
> `AM-8200N manual de usuario y programación` **p7** — «**EVACUACIÓN**: Comando para activar la
> salida de sirena y todos los módulos de salida programados con **Tipo SW = SND** *y* módulos de
> salida que tengan en su **CBE** el operando "EVAC"». El manual trata **Tipo SW y CBE como dos vías
> de activación PARALELAS**, no una como prerrequisito de la otra — y las documenta en secciones
> separadas (índice: «Tabla de resumen tipo SW para módulos», p35). **Partir está justificado desde
> la fuente.**
>
> **Retiro mi recomendación anterior de «ambas CORE»** (crítico convergente del dúo): la justifiqué
> con `fact_match_score`, con el serving del carrier y con un precedente tuyo de s269 — las tres son
> circularidad, no fuente. Si «Tipo SW» es CORE para *esta* pregunta es alcance, y el alcance es tuyo.
>
> **⚠️ Trampa del demote**: «Tipo SW → supplementary» es **la única casilla de toda la sentada que
> mejora el marcador sin tocar el bot**. `core_facts()` filtra `tipo=='core'`, así que el hecho sale
> del assessment **y** de la exigencia de PASS (un `[SUPP]` ausente nunca baja el veredicto), y con
> él un retrieval-miss real ya diagnosticado en s101 con lever nombrado.
>
> **Tuyo:** para «cómo programo una CBE para que un evento active una salida», **¿saber que el
> módulo lleva un Tipo SW es parte obligatoria de la respuesta, o es configuración previa que la
> pregunta no contrata?** La fuente dice que son vías paralelas; si eso entra en el contrato, lo
> decides tú.
>
> **Escribe**: +1 core (131→132 clasificados) · endurece PASS si ambas van CORE · renumera
> `cat018#3` · falta escribir la quote verbatim de p7/p61 en `citations`.

`[ ] ✅ partir en dos (ambas CORE) · [ ] ✅ partir con alcances distintos (CBE core · Tipo SW suppl) · [ ] ✏️ otra (anota) · [ ] ❌ dejarlo`

---

## 5 · `hp006#2` — ISO-X

**Pregunta:** «La Notifier AFP-400 muestra "Tierra" (Earth Fault). ¿Qué significa y cómo se
localiza?»
**Hecho (hoy):** los módulos aisladores **ISO-X** acotan la rama en avería (Estilo 7 / NFPA).
**Qué dijo el bot (CORREGIDO por el dúo — v1 citaba mal)**: procedimiento en **5 pasos** (LED,
LCD, bandeja/canaleta-humedad-aislamiento, bloque TB1 de la MPS-400, **JP2**). Menciona
«aislamiento» del cable, no los ISO-X. **Y NO explica «desconexión por tramos»** — eso lo
escribí yo en v1 y la respuesta no lo dice (sobre-afirmación mía, cazada por ambos lados).

**Mi recomendación (rebajada a donde la evidencia llega)**: el recibo prueba
**servido+omitido**; NO resuelve la cuestión eléctrica de si el ISO-X es parte del
procedimiento de acotado de un fallo de tierra. s284 lo llamaba «core y mecanismo real de
acotación»; revertir eso exige tu criterio PCI, no mi prosa. **Decisión genuinamente tuya:**

> ### s320c · **sin recomendación mía: la fuente se contradice y esto es tuyo**
>
> Leí el corpus para ahorrarte la decisión y **no pude**: dice las dos cosas.
> - **Mecanismo** — `15088SP p70`: «El ISO-X **ve este corto** y desconecta la rama fallante,
>   aislando efectivamente la rama fallante del resto del lazo. Una vez que la falla ha sido
>   removida, el ISO-X reaplica la alimentación». Y el pie de figura: «**Cortos** en el resto de
>   este Lazo SLC… serán aislados».
> - **Descripción** — `50253SP p89`: aísla una zona «cual permite que un segmento… funcione **si un
>   circuito falla**»; y el índice de equipos lo llama «**Módulo aislador de Falla de Lazo**».
>
> Uno describe cortocircuito; el otro, falla genérica. **Ante conflicto de fuentes lo correcto es
> enseñarte las dos, no elegir yo** (ambos revisores me marcaron que recomendar el demote
> sobrepasaba la evidencia).
>
> **Tuyo, y en una frase:** cuando llegas con **«Tierra»** en pantalla, ¿el ISO-X forma parte de tu
> procedimiento de acotado —¿partes el lazo por los aisladores?— o la tierra la localizas por
> regletas y el ISO-X no pinta nada porque solo abre ante cortocircuito?
>
> **Si marcas demote**: hay que **reescribir en el mismo upsert** la prosa del `gold_answer`
> (líneas 686 y 688), que hoy afirma ante el juez de PASS justo lo que el label negaría. Un demote a
> secas deja el gold auto-contradictorio **y** encoge la cola de etapa 3 de 9 a 8 — aunque ojo:
> *que el marcador baje no es argumento ni a favor ni en contra* (eso también sería circular).

`[ ] ✅ demote a SUPPLEMENTARY (el ISO-X no es parte del acotado de TIERRA) · [ ] ✏️ se queda CORE (explica) · [ ] ❌ borrar el hecho`

---

## 6 · `cat020#2` — meta-ref del manual de variaciones España

**Pregunta:** «En una central Morley DXc instalada en España, ¿nivel de alarma y prealarma por
defecto…?» **Estado:** hecho `meta-ref`, sin `texto`.
**Qué dijo el bot:** cita «**DXc_Manual variaciones de mercado**» y reproduce el matiz
nivel/modo. **Dúo: verificado exacto (FULL:4047, 4081-4082, 4199-4201).**
**Mi recomendación:** aplicar lo del PLAN — valor → «específicos de la versión España»;
la referencia al manual → **expectativa de CITA** (ya cumplida).

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **La fuente (leída en s320c) CORRIGE la redacción propuesta.** El manual de variaciones organiza
> estos valores **por PROTOCOLO, no por país**:
> - **p6** — tras el ejemplo `S004 OPT Fuego:100% Prealarma: 80%` viene el encabezado
>   «**5.3.10.5 Información específica según el protocolo** → 5.3.10.5.1 … para protocolo
>   **Morley-IAS**».
> - **p5** — «Los detectores Multicriterio y láser **de Morley-IAS** son equipos que disponen de
>   varios niveles de alarma».
>
> ⇒ escribir el `valor` como «específicos de la **versión España**» ancla al eje equivocado. Lo
> fiel a la fuente es anclarlo al **protocolo Morley-IAS**, con el manual de variaciones de mercado
> como documento donde vive.
>
> **Retiro la otra mitad de mi propuesta** (recortar el `texto` porque puntúa bajo en el matcher):
> eso es afinar el gold contra el instrumento. Si un texto legítimo aterriza como retrieval-miss
> falso, **el fallo es del scorer** y se arregla ahí — podar golds uno a uno no escala a 30+
> fabricantes.
>
> **⚠️ Corrección a una «trampa» que te di mal**: dije que la mitad «expectativa de CITA» *no
> escribe nada*. **Falso.** No existe un campo especializado, pero el juez de PASS **recibe el
> `texto` literalmente**, y hoy ese texto exige que los valores figuren en el manual español ⇒
> tocarlo sí puede aflojar PASS.
>
> **Tuyo:** ¿el 80%/100% es un default **del protocolo Morley-IAS** (y cualquier central que lo
> hable traería lo mismo) o **de la versión España** que este manual documenta?
>
> **Escribe**: hoy el hecho **no se mide** — `_is_meta_ref` dispara `continue` porque el `valor`
> empieza por «Manual», así que ni llega a un juez. Con un `valor` de contenido **entra en el
> denominador** (131→132) y, sobre la respuesta congelada, saldría **MISS** (0 menciones de
> «España»). No añade un fallo: deja de ocultarlo.

`[ ] ✅ aplicar · [ ] ✏️ otra redacción (anota) · [ ] ❌ dejarlo`

---

## 7 · `hp001#2` — clave «1111» (afilar redacción)

**Estado:** **retrieval-miss** (`within-doc`), no síntesis — entra solo por la edición.
**Matiz del dúo (Sol)**: no hay medición de que la reescritura «reduzca fragilidad del juez»
— se propone como **claridad semántica**, no como mejora demostrada.
**Mi recomendación:** afilar el `texto` sin tocar el `valor`: «clave de usuario por defecto
**1111**; el acceso a configuración avanzada **requiere otra clave/nivel**».

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **El «antes», que este ítem no traía** (es el único cuyo objeto ES un diff, y v3 se lo dejó):
> **Hecho (hoy)**, verbatim de `gold_answers_v1.yaml:36-41` — «La clave de USUARIO por defecto es
> 1111, que **NO da acceso a la configuración avanzada completa** (solo el nivel de usuario)»,
> `cita: MU-376 p10`.
>
> **La fuente (leída en s320c) reconcilia la divergencia del dúo.** El manual del modelo hermano
> (`CAD150R Instalación` p19) da: «**User level code 1111** · **Installator level code 2222**» — y
> **no dice nada** sobre «configuración avanzada». O sea: la negación es **derivable** de que existen
> dos niveles distintos, pero **no está citada** en ninguna página.
> *(Sol la llamaba circular por apoyarse en el error medido; Fable la daba por sólida desde la
> fuente. La fuente dice: ambos a medias.)*
>
> **Mi recomendación: ✏️ reformular la negación como la ESTRUCTURA DE NIVELES**, que sí está en la
> fuente — «clave de usuario por defecto **1111** (nivel de usuario); el nivel de
> configuración/instalador requiere **2222**» — en vez de una afirmación sobre «lo avanzado» que
> ninguna página sostiene. Y editar en el mismo upsert la cláusula gemela del `gold_answer`.
>
> **Tuyo:** en una CAD-250 real con 1111, **¿se ve algo de configuración avanzada, o no hay nada?**
> Si hay avanzado parcial, «completa» es correcta y la ✅ del packet sería un empeoramiento.
>
> **Escribe**: denominador invariante. Este hecho hoy sale `in_pool:false / reaches_gen:false` ⇒
> ningún juez de respuesta lo lee; el cambio no mueve métrica. Pero **conserva la clave de join**
> `qid#idx:valor` si no cambias el `valor`, así que las filas históricas seguirán pareando como si
> midieran lo mismo: decláralo al re-basear.

`[ ] ✅ aplicar la propuesta · [ ] ✏️ tu redacción (anota) · [ ] ❌ dejarlo`

---

## 8 · `hp002` — la pregunta dice «de Detnov»

**Problema:** el ASD535 es **Securiton**, distribuido por Detnov — hp019 ya lo dice bien. Los
5 hechos de hp002 salen OK: cero impacto métrico, coherencia pura. **Dúo: verificado exacto.**
**Mi recomendación:** armonizar la pregunta con hp019.

> ### s320c · **el único con recomendación firme, y el que hay que ver PRIMERO**
>
> **Sólido por los dos revisores.** Y el ítem, tal como está redactado arriba, **omite la mitad
> principal del encargo**: `TECH_DEBT.md:2278` asignó a ESTA sentada dos cosas — «el gold hp002
> pregunta *el ASD535 de Detnov*; **prod hoy lo rechaza; adjudicar la conducta esperada** *y de paso*
> la redacción». El packet solo te ofrece la redacción, presentada como «coherencia pura, cero
> impacto métrico».
>
> **Qué pasa hoy**: el gold lleva `conducta_esperada: answer` mientras producción **rechaza** por la
> ruta `mismatch` («el ASD535 es de Securiton, no de Detnov») y no entra al RAG. Armonizar la
> pregunta **retira del ruler el enunciado que hace visible esa contradicción — sin firmarla**.
>
> **Mi recomendación: ❌ no tocar la redacción todavía.** Primero firma la conducta.
>
> **Tuyo, y desbloquea el resto:** ante «el ASD535 **de Detnov**», ¿qué debe hacer el bot?
> **(a)** responder con la nota «es de Securiton, distribuido por Detnov» · **(b)** ofrecer
> relanzamiento · **(c)** rechazar, como hoy.
> Si firmas (a) o (b) → armonizar pasa a ser correcto y barato en el acto. Si firmas (c) → ❌ en
> firme, y el gold se queda como testigo.
>
> **Corrección al ítem**: hp002 **no** es el único que ejercita marca↔producto errónea — `hp013`
> («la Detnov ADW535») mantiene la clase. Y «cero impacto métrico» está medido **para la redacción
> de hoy**: cambiar el texto cambia la query del harness, así que habría que re-correr el smoke.

`[ ] ✅ armonizar · [ ] ✏️ otra redacción · [ ] ❌ dejarlo`

---

## 9 · **NUEVO — candidato a gold de USO REAL** (CAD-171, menú avanzado) · **con el no-duplicado EJECUTADO**

**El fallo (veredicto final s304, DEC-185)**: preguntaste la ruta al menú avanzado de la
CAD-171; el bot encabezó con «AJUSTES > GENERAL» teniendo el §5.4 AVANZADO servido en rango 1
— **selección de sección** con la evidencia delante.

**⚠️ NO-DUPLICADO (el gatillo canónico de DEC-025 que v1 NO ejecutó — cazado por el dúo):**
**`hp001` ya cubre casi lo mismo**: «¿cómo se entra al menú de programación avanzada?»
(CAD-250, **misma serie Vesta, mismo MC-380 compartido**); sus hechos #0/#1 (candado, clave
2222) son los mismos que el Hecho 1 propuesto, y la ruta AJUSTES>AVANZADO ya aparece en la
respuesta congelada de hp001 (FULL:5143-5144). **Lo que discrimina de verdad es el Hecho 2**:
la ruta preguntada POR LA CAD-171 con su manual propio (MI-716) — la clase «elemento vecino»
de uso real.

**Ficha propuesta (recortada al valor discriminante):**
- **Pregunta**: «¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?»
- **Hecho CORE** — ruta: **AJUSTES (Menú principal) > AVANZADO (Submenú)** (MI-716 p.26/34/35).
- **Hecho SUPPLEMENTARY** — acceso: candado → clave admin **2222** (p.25 §6.1) — *suppl. por
  solape con hp001#0/#1; si prefieres evitar el doble conteo, referencia cruzada y fuera*.
- **Hecho descartado** (v1 lo traía): la remisión a la «Guía Avanzada» — ES el MC-380 rev c
  que ya tenemos (corrección s302-s303 incorporada).

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **Crítico de Fable, y RESUELTO con la fuente**: la ruta se justificaba desde DEC-185 —un incidente
> de producción— y desde la prosa congelada del bot; es decir, **desde el fallo del bot, no desde el
> manual**, mientras todos los cores de `hp001` llevan `cita:`. Anclar un gold nuevo en el fallo
> repetiría la forma del ítem 2 **en su génesis**. Lo leí:
>
> `Manual_CAD-171-MI-716-es` **p26 · p34 · p35** — el diagrama de navegación muestra, en la columna
> **Submenú** bajo AJUSTES: `GENERAL · VERSIONES · USUARIOS · **AVANZADO** · CONECTIVIDAD ·
> IMPRESORA · LOGS · TEST · INICIO`. **La ruta SÍ tiene ancla de fuente** — es cita de **diagrama**,
> no de prosa, y por eso ningún barrido por cabeceras la encontraba. (Nota: el MI-716 **no** tiene
> sección propia que documente AVANZADO — coherente con que la CAD-171 remita a la guía avanzada.)
>
> **Lo que sigue faltando NO es adjudicación tuya, es trabajo de aplicación** (Sol): «crear así» no
> es una ficha escribible — faltan `qid`, `conducta_esperada`, `split: dev`, `estrato`,
> `gold_answer`, la localización exhaustiva del checklist de `RULER_DESIGN §2` y la procedencia. La
> puerta `gold_store.py` falla-cerrado si no están, así que eso lo preparo yo tras tu marca.
>
> **Tuyo:** si el bot responde solo «AJUSTES > AVANZADO» **sin** mencionar candado + clave 2222,
> ¿la respuesta es **completa** para el técnico? Completa → `✅` tal cual (acceso queda
> supplementary). Incompleta → el acceso sube a core, asumiendo que añade 2 hechos que hoy ya salen
> OK y por tanto **suben el %OK por construcción**.
>
> **Escribe**: +1 core dev (133→134) · el valor «AJUSTES > AVANZADO» **no** dispara `_is_meta_ref`
> ⇒ sí se mide · no rompe tests.
>
> **Staleness que debes saber**: la conducta congelada del caso CAD-171 es de `sonnet-4-6` y
> producción corre Opus 5. Puede que el fallo ya no se reproduzca — en ese caso el gold nace como
> **centinela anti-regresión** en vez de como medida de un fallo vivo. Sigue mereciendo existir.

`[ ] ✅ crear el gold ASÍ (core=ruta, suppl=acceso) · [ ] ✏️ crearlo con cambios (anota) · [ ] ❌ no crearlo (hp001 basta)`

---

## Qué NO te pido y qué cambió respecto a v1 (transparencia del dúo)

- **Fuera la proyección «la cola quedaría en ~1-2»** (v1 la traía): mezclaba edición del
  denominador con reclasificaciones sin adjudicar — sesgaba tu sentada (Sol, menor).
- Sin cambios: nada sobre `hp013#1`/`hp017#1` (techo declarado), flips, ni `hp009#0`.
- Ítems verificados EXACTOS y listos sin cambios de fondo: **3, 6, 7, 8** (y el 1 con tu
  marca). Las correcciones grandes: **2+10 fusionados** y **9 con el no-duplicado**.
- ~~El detalle del caso CAD-171 (`evals/s294_cad171_menu_avanzado_v1.md`) queda SANEADO en
  este mismo PR (cifras retiradas marcadas, pregunta del techo cerrada con DEC-186) — si lo
  abres en la sentada, ya no lee contradictorio.~~ **CORREGIDO (s320c): era falso por partida
  doble.** (a) El fichero sigue con el bloque de diagnóstico **duplicado literal** (líneas 40-107 y
  158-225, 68 líneas idénticas) con veredictos opuestos — el de-duplicado sigue PENDIENTE. (b) «la
  pregunta del techo cerrada con DEC-186» está **stale**: DEC-186 quedó **EN REVISIÓN** y la
  pregunta **RE-ABIERTA** (`TECH_DEBT` #75). Si abres ese fichero en la sentada, **sí** lee
  contradictorio — léelo con esto delante.

---

## Traza de la revisión s320c (para que no haya que reconstruirla)

- **Bug del instrumento** → `TECH_DEBT.md` #75 · recibos `evals/s320c_rejudge_s305_stored_v1.json`
  y `evals/s320c_techo_modelo_ab_v2.json` (el roto, `s305_techo_modelo_ab_v1.json`, se conserva).
- **Auditoría de los 8 ítems vivos** (8 agentes) → dio «7 de 8 no marcables». **Sobre-acusó**: el
  pase de falsación con el prior contrario tumbó 5 de 7. Ninguna acusación de evidencia sobrevivió
  como bloqueante. *Causa declarada: el encargo de la auditoría pedía «encuentra por qué NO marcar»
  — el sesgo lo puse yo en el prompt.*
- **Dúo sobre mis recomendaciones** (Sol xhigh + Fable 5, `evals/adversarial_review_log.jsonl`
  ts=2026-08-13T10:58:17): tumbaron por **circularidad** la mitad-de-alcance de los ítems 4, 6 y 7,
  y el ancla de génesis del 9. Lo que ves arriba ya lo incorpora.
- **Lecturas de fuente hechas en s320c** para no gastar tu criterio: ítem 4 (AM-8200 p7) · ítem 5
  (15088SP p70 vs 50253SP p89, **conflicto no resuelto**) · ítem 6 (variaciones p5-p6) · ítem 7
  (CAD150R p19) · ítem 9 (MI-716 p26/34/35). Cuatro de las cinco convirtieron una pregunta abierta
  en una recomendación anclada.
- **Orden sugerido**: **8 primero** (desbloquea su propia redacción) → 5 (PCI puro) → 4 y 9 juntos
  (comparten doctrina: ¿un prerrequisito de configuración entra en el contrato?) → 7 → 6 → 3.
