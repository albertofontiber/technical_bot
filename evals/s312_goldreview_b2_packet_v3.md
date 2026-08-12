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
> modelo). El eje modelo del hp011#2 está medido aparte (s305) y su ítem lo incorpora.

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
> **4/5**, max 5/5 los tres. **⇒ Este ítem sale del packet y el gold se queda COMO ESTÁ.** No hay
> nada que adjudicar: el bot puede transmitir el hecho, y el gold no se mueve por cómo se comportó
> un modelo (DEC-025).
>
> Lo que el número sí destapa **no es materia de sentada, es de ingeniería**: la transmisión es
> **inestable** (6/15 firmes teniendo la evidencia perfecta delante) y el brazo `base` da 0/5 en 14
> de 15 ⇒ el hueco es de **serving**. Eso vuelve a la cola de ingeniería, no a tu mesa.
>
> **Los otros 8 ítems del packet están sanos**: ninguno se apoya en s305 (verificado uno a uno).
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

`[ ] ✅ demote a SUPPLEMENTARY (el ISO-X no es parte del acotado de TIERRA) · [ ] ✏️ se queda CORE (explica) · [ ] ❌ borrar el hecho`

---

## 6 · `cat020#2` — meta-ref del manual de variaciones España

**Pregunta:** «En una central Morley DXc instalada en España, ¿nivel de alarma y prealarma por
defecto…?» **Estado:** hecho `meta-ref`, sin `texto`.
**Qué dijo el bot:** cita «**DXc_Manual variaciones de mercado**» y reproduce el matiz
nivel/modo. **Dúo: verificado exacto (FULL:4047, 4081-4082, 4199-4201).**
**Mi recomendación:** aplicar lo del PLAN — valor → «específicos de la versión España»;
la referencia al manual → **expectativa de CITA** (ya cumplida).

`[ ] ✅ aplicar · [ ] ✏️ otra redacción (anota) · [ ] ❌ dejarlo`

---

## 7 · `hp001#2` — clave «1111» (afilar redacción)

**Estado:** **retrieval-miss** (`within-doc`), no síntesis — entra solo por la edición.
**Matiz del dúo (Sol)**: no hay medición de que la reescritura «reduzca fragilidad del juez»
— se propone como **claridad semántica**, no como mejora demostrada.
**Mi recomendación:** afilar el `texto` sin tocar el `valor`: «clave de usuario por defecto
**1111**; el acceso a configuración avanzada **requiere otra clave/nivel**».

`[ ] ✅ aplicar la propuesta · [ ] ✏️ tu redacción (anota) · [ ] ❌ dejarlo`

---

## 8 · `hp002` — la pregunta dice «de Detnov»

**Problema:** el ASD535 es **Securiton**, distribuido por Detnov — hp019 ya lo dice bien. Los
5 hechos de hp002 salen OK: cero impacto métrico, coherencia pura. **Dúo: verificado exacto.**
**Mi recomendación:** armonizar la pregunta con hp019.

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

`[ ] ✅ crear el gold ASÍ (core=ruta, suppl=acceso) · [ ] ✏️ crearlo con cambios (anota) · [ ] ❌ no crearlo (hp001 basta)`

---

## Qué NO te pido y qué cambió respecto a v1 (transparencia del dúo)

- **Fuera la proyección «la cola quedaría en ~1-2»** (v1 la traía): mezclaba edición del
  denominador con reclasificaciones sin adjudicar — sesgaba tu sentada (Sol, menor).
- Sin cambios: nada sobre `hp013#1`/`hp017#1` (techo declarado), flips, ni `hp009#0`.
- Ítems verificados EXACTOS y listos sin cambios de fondo: **3, 6, 7, 8** (y el 1 con tu
  marca). Las correcciones grandes: **2+10 fusionados** y **9 con el no-duplicado**.
- El detalle del caso CAD-171 (`evals/s294_cad171_menu_avanzado_v1.md`) queda SANEADO en
  este mismo PR (cifras retiradas marcadas, pregunta del techo cerrada con DEC-186) — si lo
  abres en la sentada, ya no lee contradictorio.
