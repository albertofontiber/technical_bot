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
> **⚠️ s320d — AUDITORÍA DE PROCEDENCIA de mis lecturas de fuente (la cazó Alberto).** En s320c
> consulté el corpus con `ilike` sobre la tabla ENTERA para ahorrarle criterio a Alberto, **sin
> comprobar a qué producto pertenecía cada manual**. Auditadas las 5 contra
> `chunks_v2.product_model`:
>
> | ítem | la pregunta es de | manual que cité | `product_model` real | veredicto |
> |---|---|---|---|---|
> | 5 `hp006#2` | Notifier **AFP-400** | `15088SP` · `50253SP` | **AM-2020** · **AFP-300** | ❌ **otros paneles — CORREGIDO** |
> | 7 `hp001#2` | Detnov **CAD-250** | `CAD150R` | **CAD-150R** | ❌ **otro modelo — CORREGIDO** |
> | 4 `cat018#2` | Notifier **AM-8200** | `AM-8200N` | **AM-8200N** | ⚠️ variante hermana — declarado |
> | 9 CAD-171 | Detnov **CAD-171** | `MI-716` | **CAD-171** | ✅ |
> | 6 `cat020#2` | Morley **DXc** | `DXc_variaciones` | **DXc** | ✅ |
>
> Las dos corregidas cambiaron de sentido: en el 5 el manual propio dice «avería» genérica (no
> «corto») y **deshace** el sesgo hacia el demote; en el 7 la CAD-250 documenta la estructura de
> niveles y **refuerza** el hecho. Es la misma clase que el fallo de s305 —usar un resultado sin
> preguntar si la fuente podía responder a esa pregunta—, aquí en la capa de corpus en vez de la de
> instrumento. **Lección**: filtrar por `product_model` NO es opcional cuando la pregunta nombra un
> modelo; el proyecto tiene maquinaria de familia/serie (DEC-043/044) precisamente para esto y un
> `ilike` global la salta.
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
> **Coste de APLICAR una marca (medido en s321, no estaba en ninguna ficha)**: editar el ruler
> dispara 4 tests de contrato congelado. No es un bug — son guardas forzando ceremonia. Aplicarlas
> exige, en el MISMO commit: (a) el **diff acotado** contra el commit cuyo ledger casa con el sha
> pinneado, verificando que solo contiene lo adjudicado; (b) re-anclar los 3 canarios
> `s203/s204/s205`; (c) la cascada de `s277` — regenerar el contrato por su builder y propagar los
> pins a `prereg_v2`, `prereg_v3` y el scorer **a mano**, dejando el manifest histórico intacto
> (`TECH_DEBT #77`, `DEC-218`). **Marcas y re-anclaje van juntos en un commit**: separados dejan la
> suite roja en cada frontera y enmascaran cualquier deriva ajena que entre por esa ventana.
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
> ### ✅ s321 — CRITERIO ADOPTADO (DEC-221): se ancla en el pasaje que da el MECANISMO
>
> Alberto propuso anclar en el pasaje con más **empaque** en el manual —el de A5.2 va en recuadro
> amarillo con icono «!»— y **declarar la inconsistencia de la fuente** en vez de elegir una y
> borrar la otra. Su punto (2) se adopta tal cual. El (1) se midió antes de adoptarlo y **la señal
> visual NO sirve**: el subrayado sobrevive a la extracción como `<ins>`, pero aparece en **1.412 de
> 26.215 chunks (5,4%)** envolviendo mayoritariamente **títulos de sección** — como marca de
> criticidad sería una máquina de falsos positivos. Y la caja con el icono, que es lo que de verdad
> da el empaque, **la extracción la pierde** (deuda nueva `TECH_DEBT #83`).
>
> **Lo que sí discrimina, y vive en texto plano**: la A5.2 trae una marca explícita de criticidad
> («**es fundamental**») y sobre todo **el mecanismo** —«ya que, si no, esta **será anulada**»—; la
> A5.4 da la misma instrucción **sin explicar el efecto**. ⇒ criterio: **entre dos pasajes del mismo
> manual, ancla en el que da el MECANISMO**. Escala a 30+ fabricantes sin depender de maquetación,
> es pedagógicamente correcto (el porqué es lo que un técnico usa en obra) y **no es circular**: se
> decide contra la fuente, no contra cómo respondió el modelo.
>
> **Y la inconsistencia se DECLARA**: A5.2 y A5.4 no se contradicen —una singulariza la regla
> crítica, la otra da la limpieza completa— así que el gold puede llevar **las dos con su
> jerarquía**, con la quote de A5.4 añadida a `citations`.
>
> ⇒ **Esto refuerza la ✏️ y desaconseja la ✅**: la ✅ («ambas reglas») ancla en A5.4, que es la que
> NO da el mecanismo — y además es la que el bot ya reproduce solo (medido: A5.2 → 3/3 a 5/5;
> A5.4 → 0/3).
>
> **Tuyo:** ¿la respuesta debe decirle al técnico **qué regla le anula el retardo y por qué**, o
> basta «hay dos por defecto, bórralas»? Y: ¿en obra se borra **también la Regla 2** (tecla
> EVACUACIÓN activa todos los equipos), o esa se conserva?
>
> ### ✅ s321 — **SONDADO. El hecho ES ALCANZABLE: 3/3 firmes a 5/5** (`evals/s293_reachability_hp017_hp017_2.json`)
>
> Era el único ítem cuya premisa nunca se había medido. Ya está: sonda DEC-173 en modo `serve`,
> inyectando el portador de la **p43** (`94cbb0ce…`, §A5.2 «Crear una regla»), juez canónico K=5.
>
> | | base | oráculo |
> |---|---|---|
> | rep0 · rep1 · rep2 | **0/5** las tres | **5/5** las tres |
>
> `alcanzable: true` · `oracle_firme 3/3` · `max_oracle 5`. El portador se admitió en las 3 y las
> respuestas escriben la ruta «Editar Configuración» **y** «Regla 1» en las 3. **Delta perfecto: sin
> el carrier, cero; con él, todo.**
>
> **Qué derriba.** El «0/3 de la mitad (b)» que este ítem presentaba como evidencia **no medía la
> capacidad del modelo, medía su ausencia**: aquel probe era PRE-guard y el portador de la p43
> **nunca se sirvió**. Se le pedía escribir algo que no tenía delante. Y por tanto **esto no es un
> problema de síntesis, es de retrieval**: el hecho se transmite entero cuando el chunk llega.
>
> **Qué cambia en la decisión.** La opción ✅ («ambas reglas») queda **demostrada como aflojamiento**:
> re-anclaría a la p45 —la frase que el bot ya reproduce sin ayuda— cuando acabamos de medir que la
> formulación de la **p43 es perfectamente alcanzable**. No hay razón para rebajar un hecho que el
> sistema puede dar. **Mi ✏️ se refuerza**, con un matiz nuevo de la sonda: el operando duro (Regla 1
> + su efecto) sale **3/3**, pero el **porqué** («será anulada») solo **1/3** — al partir, decide si
> el porqué entra en el hecho o se queda como matiz.
>
> **Y lo que de verdad paga aquí no es editar el gold: es SERVIR la p43.** Lever de retrieval con
> retorno medido (0/5 → 5/5, 3 de 3), misma forma que `cat017#2` en s293. ⚠️ Con la advertencia del
> propio DEC-173: el oráculo eleva la `similarity` para forzar la admisión ⇒ dice «si lo viera, lo
> transmite», **no** que ninguna lane vaya a traerlo. **Un alcanzable NO es un GO.**
>
> *Declarado: la corrida tuvo varios `ReadTimeout` contra Supabase. No afectan al veredicto —el
> oráculo depende de la inyección, admitida 3/3— pero el `base 0/5` de esta corrida no se usa como
> prueba independiente, solo corrobora lo ya sabido.*
>
> **Escribe**: hp017 pasa de 5 a 6 cores · renumera `hp017#3→#4` · rompe el join con artefactos
> congelados que indexan por `qid#idx`.

`[ ] ✅ partir en dos (redacción "ambas reglas") · [X] ✏️ partir + reformular (anota) · [ ] ❌ dejarlo compuesto`

> ✏️ **ADJUDICADO (Alberto, s321) — APLICADO (DEC-224).** hp017#2 se CONSERVA (release_guard s277; ya nombra solo la Regla 1); +1 suppl «Regla 2» que describe la diferencia de alcance A5.2/A5.4-Ej.1 sin afirmar «no anula». Cazado por Alberto en la aplicación: **A5.4 es la sección de EJEMPLOS** — el «las dos» es un paso del Ejemplo 1 (evacuación por etapas), no una instrucción general.
>
> **La mitad (b) queda así:** «**Regla 1** (CUALQUIER entrada de alarma activa TODOS los equipos de
> salida): hay que **borrarla** antes de programar causa-efecto específico, porque si no **anula** la
> programación. La **Regla 2** (tecla EVACUACIÓN) **no interfiere** con reglas disparadas por alarma
> y puede conservarse; solo procede borrarla si se va a programar la propia evacuación de forma
> específica.»
>
> **Cómo se llegó, porque la lectura es de Alberto y disuelve el problema en vez de declararlo.**
> Yo iba a anclar en A5.2 y **declarar la inconsistencia** con A5.4. Alberto encontró el mecanismo
> que la explica: lo que obliga a borrar la Regla 1 es que **anula** lo tuyo, y eso pasa porque su
> disparador —cualquier entrada de alarma— es **el mismo** al que responden tus reglas específicas.
> La Regla 2 se dispara con la **tecla EVACUACIÓN**, así que no se cruza con ellas: conservarla no
> rompe nada y borrarla sí quita funcionalidad. ⇒ **A5.2 y A5.4 dejan de ser inconsistentes**: la
> primera es precisa (señala la única que anula en el caso normal), la segunda es genérica (limpieza
> completa). Ninguna está mal.
>
> **Matiz declarado como DERIVACIÓN, no como texto del manual**: la Regla 2 sí anularía si se
> programa algo específico **para la propia tecla EVACUACIÓN** (p. ej. evacuación por fases) — ahí
> ambas reglas se comportan igual y solo cambia el disparador. El manual no lo dice; se deduce del
> mecanismo. Es también cuando el «las dos» de A5.4 aplica.
>
> **Qué escribe**: split de `hp017#2` en dos cores ⇒ hp017 pasa de 5 a 6 · renumera `hp017#3→#4` ·
> añadir al `citations` la quote de A5.4 (hoy no está) · rompe el join con artefactos congelados que
> indexan por `qid#idx`. **Aplicación pendiente** junto con los ítems 4, 8 y 9, en UN commit con el
> re-anclaje (ver el coste en la cabecera). Criterio de anclaje: `DEC-221`.

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
> **⚠️ s321 — CORRECCIÓN: mi «vías paralelas» era del manual de la VARIANTE, y además decía lo
> contrario de lo que dice el manual del gold.** Lo de s320c salía de
> `AM-8200N` (`product_model = AM-8200N`). El manual que el gold cita —`AM-8200-manu-prog-spa`,
> `product_model = AM-8200/AM-8200-BB`— dice en la misma p7 **sin cláusula de CBE**:
> «EVACUACIÓN: Control de activación de la salida sirena y de todos los módulos de salida
> programados con **Tipo SW = SND** en ausencia de alarmas y averías».
>
> **Y en `p41` dice lo decisivo, que es lo opuesto a «paralelas»:**
> > «**SND** | Tipo de software específico… activado por cada alarma y sigue el estado de la salida
> > Sirena de central. […] **Nota: los módulos de salida utilizados para las funciones arriba
> > indicadas NO ACEPTAN CBE.**»
>
> Es decir: para esa familia de Tipo SW (SND, STR, MAINFV, REMV…) el Tipo SW y la CBE son
> **MUTUAMENTE EXCLUYENTES**, no dos vías equivalentes. Un módulo con esos tipos **no admite
> ecuación**. (Concuerda con lo que el dúo apuntó en `p65` sobre el TIPO ID de señalización general
> bloqueando la CBE: son dos notas de la misma regla.)
>
> **Qué cambia y qué no.** El **split sigue justificado** —son dos hechos distintos, y el índice del
> propio manual los documenta en secciones separadas («Tabla de resumen tipo SW para módulos», p35)—
> pero **el peso del alcance se mueve**: con la p41 delante, el Tipo SW no es «configuración previa
> ajena a la pregunta», sino lo que determina **si la CBE es siquiera posible** en ese módulo. Un
> técnico que programa una CBE sobre un módulo con Tipo SW = SND está programando algo que el panel
> no va a aceptar. Eso lo digo como **observación de fuente**, no como adjudicación: el alcance
> sigue siendo tuyo (ver más abajo por qué me abstengo).
>
> *(Precisión s320d, tras la auditoría de procedencia: la cita de la EVACUACIÓN sale del manual de la
> variante **AM-8200N** (`product_model = AM-8200N`), mientras el índice del p35 sale de
> `AM-8200-manu-prog-spa` (`product_model = AM-8200/AM-8200-BB`), que es el del gold. Misma línea de
> producto y variante hermana — muy lejos del cruce de paneles del ítem 5 — pero queda dicho: si
> quieres el ancla en el manual exacto del gold, la quote verbatim hay que sacarla de p61.)*
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
> **Tuyo, y con la p41 delante la pregunta es más nítida:** para «cómo programo una CBE para que un
> evento active una salida», **¿saber que el módulo lleva un Tipo SW —y que ciertos Tipos SW hacen
> que el módulo NO acepte CBE— es parte obligatoria de la respuesta, o es configuración previa que
> la pregunta no contrata?**
>
> Un matiz que quizá quieras separar al marcar: no es lo mismo **el ejemplo** («SND = sirena»,
> que sí suena a contexto previo) que **la regla de bloqueo** («esos Tipos SW no aceptan CBE», que
> es una condición de posibilidad de lo que se pregunta). Si te convence la regla pero no el
> ejemplo, la ✏️ es tu casilla: partir, con la mitad «Tipo SW» redactada sobre el **bloqueo**
> (p41/p65) en vez de sobre la etiqueta SND.
>
> **Escribe**: +1 core (131→132 clasificados) · endurece PASS si ambas van CORE · renumera
> `cat018#3` · falta escribir la quote verbatim de p7/p61 en `citations`.

`[X] ✅ partir en dos (ambas CORE) · [ ] ✅ partir con alcances distintos (CBE core · Tipo SW suppl) · [ ] ✏️ otra (anota) · [ ] ❌ dejarlo`

> ✅ **ADJUDICADO (Alberto, s321) — APLICADO (DEC-224).** Split #2 → asociación CBE + Tipo SW/TIPO ID **con la regla de p65** («la central no permite programar una ecuación si el módulo tiene un TIPO ID para señalizaciones de carácter general» — mecanismo, verificado al píxel + GPT-5.5). Tabla p40-41 = 23 tipos, no 7. Iconos SND=sirena/STR=flash confirman SND como tipo de sirena.
>
> **Su razón, literal: «no quiero falsear los misses.»** Rechaza explícitamente el demote de la
> mitad «Tipo SW» — que era, y el packet lo dice arriba, **la única casilla de toda la sentada que
> mejora el marcador sin tocar el bot**: `core_facts()` filtra `tipo=='core'`, así que degradarlo
> habría sacado del assessment un retrieval-miss real ya diagnosticado en s101. Adjudicar en contra
> del propio marcador es la decisión correcta y queda registrada como tal.
>
> **Refuerzo de fuente (p41), que el alcance ya tenía delante**: «*los módulos de salida utilizados
> para las funciones arriba indicadas **NO ACEPTAN CBE***» ⇒ el Tipo SW no es contexto previo
> ajeno a la pregunta: determina **si la CBE es siquiera posible** en ese módulo. Con eso, «ambas
> CORE» es coherente con la fuente y no solo con el alcance.
>
> **Qué escribe**: split de `cat018#2` en dos cores ⇒ +1 clasificado (131→132) · renumera
> `cat018#3` · endurece PASS · falta la quote verbatim de p41 en `citations`.

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

> ### ⚠️ s320d · **CORRECCIÓN: mi lectura de fuente era de OTROS PANELES** (lo cazó Alberto)
>
> El bloque anterior (s320c) apoyaba «la fuente dice que el ISO-X ve el CORTO» en dos manuales que
> **no son de la AFP-400**. Alberto lo vio en la portada del 15088SP. Verificado contra
> `chunks_v2.product_model`:
>
> | manual que cité | `product_model` REAL | qué saqué de ahí |
> |---|---|---|
> | `15088SP` | **AM-2020** (AM2020/AFP1010, doc. 15088SP rev H, 1998) | «el ISO-X **ve este corto**» |
> | `50253SP` | **AFP-300** | «si un circuito falla» · «Módulo aislador de Falla de Lazo» |
>
> Si un texto de la AM-2020 o de la AFP-300 gobierna para la AFP-400 **no es cosa de un grep**: es
> justo la pregunta que resuelve la maquinaria de familia/serie del catálogo (DEC-043/044). Yo la
> salté consultando la tabla entera con `ilike`. Misma clase que el fallo de s305: usar un
> resultado sin preguntar si la fuente podía responder a esa pregunta.
>
> **Lo que dice el manual que SÍ aplica** (`product_model = AFP-400`):
> - `MIDT170 p17` — «El ISO-X es un interruptor automático que abre la tensión del circuito a una o
>   varias ramas del lazo de comunicaciones **siempre que se detecta una avería en el circuito**. El
>   resto del lazo… continúa funcionando sin verse afectado por la avería.»
> - `MFDT170 p17` — «**El Estilo 7 requiere el uso de módulos ISO-X**.»
>
> **«Avería en el circuito», genérico — no «corto».** Eso apunta en dirección CONTRARIA a la que
> insinuaba mi bloque anterior: un fallo de tierra ES una avería del circuito, así que el manual de
> la AFP-400 **no excluye** el ISO-X del acotado. No lo zanja —«avería» es compatible con ambas
> lecturas— pero deshace el sesgo hacia el demote que yo había introducido.
>
> **Y el dato de fondo, del propio gold** (`gold_answers_v1.yaml:755`): «…ISO-X) en **MIDT170, que
> el autor NO consultó**». Este ítem lleva discutiéndose desde su autoría **sin el manual aplicable
> encima de la mesa**. Los `pdfs_used` del gold traen `50253SP` (anotado «MPS-400» — legítimo para
> la fuente de alimentación, que sí es de la familia) pero el mecanismo del ISO-X se ancló ahí.
>
> **Tuyo, y en una frase:** cuando llegas con **«Tierra»** en pantalla, ¿el ISO-X forma parte de tu
> procedimiento de acotado —¿partes el lazo por los aisladores?— o la tierra la localizas por
> regletas y el ISO-X no pinta, porque en la práctica solo abre ante cortocircuito aunque el manual
> diga «avería»?
>
> **Si marcas demote**: hay que **reescribir en el mismo upsert** la prosa del `gold_answer`
> (líneas 686 y 688), que hoy afirma ante el juez de PASS justo lo que el label negaría. Un demote a
> secas deja el gold auto-contradictorio **y** encoge la cola de etapa 3 de 9 a 8 — aunque ojo:
> *que el marcador baje no es argumento ni a favor ni en contra* (eso también sería circular).

`[X] ✅ demote a SUPPLEMENTARY (el ISO-X no es parte del acotado de TIERRA) · [ ] ✏️ se queda CORE (explica) · [ ] ❌ borrar el hecho`

> ✅ **ADJUDICADO (Alberto, s321) — APLICADO (DEC-224).** Demote + texto + las DOS frases del gold_answer (Sol cazó la segunda) + procedencia (offset +7) + `citations` creado (no existía). Traza completa y
> durable en **`DEC-223`**; aquí solo el resumen operativo.
>
> **Se cierra dentro de la fuente aplicable** — no se impone teoría eléctrica sobre el manual:
> - `MIDT170` **p71**, la MISMA página que el hecho cita: en la tabla «Funcionamiento del Lazo», la
>   fila **Tierra** es igual en Estilo 6 y 7, y la fila **Corto** solo mejora al llegar al 7. Como el
>   Estilo 7 es el que exige los ISO-X, **el manual documenta que los aisladores no compran nada
>   frente a una tierra**.
> - `MIDT170` **p77** (mecanismo): «*Un **cortocircuito**… El ISO-X detecta **este cortocircuito**…
>   abriendo el lado positivo (terminal 4)*». `DEC-221` aplicado: p17 resume, p77 explica.
> - `50253SP` **p98**: la misma frase con el término preciso («corto circuito»).
> - La detección de tierra vive en la **MPS-400** (LED, TB1-3, puente JP2), no en el lazo.
>
> **El argumento de Alberto que lo cierra**: si el ISO-X acotara la tierra, no verías «Tierra» —
> verías una rama caída. Verlo con el lazo funcionando prueba que ningún aislador se disparó.
>
> **La mitad procedimental (B) también resuelta, y NO por opinión**: el manual manda «*temporarily
> place a jumper between Terminals 2 and 4 on each ISO-X while taking measurements*» — el fabricante
> los trata como **estorbo para medir**, no como punto de corte. En 179 páginas, «ground fault» e
> «ISO-X» **no coinciden en ninguna**.
>
> **Qué escribe el upsert** — el label NO basta: hay que **reescribir el `gold_answer` en el mismo
> upsert**, retirando el inciso «*—en el lazo, mediante los aisladores ISO-X—*» (el método de mitades
> se queda). Si no, el gold pide ante el juez lo que el label niega.
>
> ⚠️ **CORRECCIÓN al bloque s320d de más arriba**: `50253SP` **SÍ es manual de la AFP-400**
> (`doc_map` línea 92: primary de `afp-300` **y** `afp-400`). Descartarlo por `product_model` fue mío
> y fue un error — la captura de Alberto sobre `15088SP` sigue siendo correcta. **El método que este
> packet recomienda (filtrar por `product_model`) es el que falla**: la aplicabilidad la responde el
> `doc_map`. Censo del daño y dirección de arreglo en `TECH_DEBT #84`.
>
> 📄 **Si vas al manual**: el gold cita `p63 (f71)` pero el pie dice **64** — offset real 7, no el 8
> registrado. Las citas impresas del gold van corridas una página.

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
> ### ✅ s321 — **AGOTADA LA FUENTE: lo responde el manual, no hace falta tu criterio**
>
> Quedaba pendiente decidir si el 80%/100% es del **protocolo** o de la **versión España**. La
> sección que los porta lo dice sin ambigüedad, y su encabezado también:
>
> > **§5.3.10.5 «Información específica según el PROTOCOLO»** → **§5.3.10.5.1 «Información
> > específica para protocolo Morley-IAS»** — «El valor analógico debe ser un número normalizado
> > entre 0% – 100%, independientemente del tipo de equipo. Para los detectores, **el nivel de
> > prealarma por defecto es el 80% y el nivel de alarma por defecto es el 100%**. • **El ajuste
> > máximo para el nivel de alarma es el 108%**.»
> > *(`DXc_Manual variaciones de mercado`, p6, `product_model: DXc`)*
>
> Los **tres** valores cuelgan del **protocolo Morley-IAS**, en una sección cuyo título es
> literalmente «según el PROTOCOLO». El **documento** es de variaciones de mercado; la **sección**
> es de protocolo. Anclar el `valor` a «versión España» atribuiría a un país lo que el manual
> atribuye a un protocolo.
>
> ⇒ **Si marcas ✏️, la redacción correcta es «específicos del protocolo Morley-IAS»**, no «de la
> versión España». Y el ❌ sigue siendo defendible: hoy el hecho no se mide y meterlo al denominador
> es una decisión de alcance tuya, no de fuente.
>
> **Escribe**: hoy el hecho **no se mide** — `_is_meta_ref` dispara `continue` porque el `valor`
> empieza por «Manual», así que ni llega a un juez. Con un `valor` de contenido **entra en el
> denominador** (131→132) y, sobre la respuesta congelada, saldría **MISS** (0 menciones de
> «España»). No añade un fallo: deja de ocultarlo.

`[ ] ✅ aplicar · [X] ✏️ otra redacción (anota) · [ ] ❌ dejarlo`

> ✏️ **ADJUDICADO (Alberto, s321) — APLICADO (DEC-224).** `valor` = el marcado por Alberto (v2-v4 lo habían cambiado sin declarar — Fable); texto con los DOS ejes España+protocolo (Sol).
>
> **Por qué no ✅**: esa casilla significaba «aplicar lo del PLAN», y el PLAN proponía escribir el
> valor como «*específicos de la **versión España***». La fuente lo contradice: los tres valores
> viven bajo **§5.3.10.5 «Información específica según el PROTOCOLO» → §5.3.10.5.1 «…para protocolo
> **Morley-IAS**»**. El documento es de variaciones de mercado; la **sección** es de protocolo.
> Marcar ✅ habría anclado a un país lo que el manual ancla a un protocolo.
>
> **Redacción que se escribe**: `valor` → «**niveles por defecto del protocolo Morley-IAS**»
> (prealarma 80% · alarma 100% · ajuste máximo de alarma 108%), citando
> `DXc_Manual variaciones de mercado` p6.
>
> **Y se mantiene el `texto` intacto**: recortarlo porque puntúa bajo en el matcher sería afinar el
> gold contra el instrumento. Si un texto legítimo aterriza como retrieval-miss falso, **el fallo es
> del scorer** — podar golds uno a uno no escala a 30+ fabricantes.
>
> **Qué escribe**: el hecho **hoy no se mide** (`_is_meta_ref` dispara `continue` porque el `valor`
> empieza por «Manual»). Con un `valor` de contenido **entra al denominador** (131→132) y sobre la
> respuesta congelada saldría **MISS**. No añade un fallo: **deja de ocultarlo** — que es la misma
> lógica del «no falsear los misses» del ítem 4.

---

## 7 · `hp001#2` — clave «1111» (afilar redacción)

**Estado:** **retrieval-miss** (`within-doc`), no síntesis — entra solo por la edición.
**Matiz del dúo (Sol)**: no hay medición de que la reescritura «reduzca fragilidad del juez»
— se propone como **claridad semántica**, no como mejora demostrada.
~~**Mi recomendación:** afilar el `texto` sin tocar el `valor`: «clave de usuario por defecto
**1111**; el acceso a configuración avanzada **requiere otra clave/nivel**».~~
**SUPERADA en s321 — ver el bloque de abajo: la recomendación queda INVERTIDA (conservar el hecho
como está).** La propuesta tachada borraba «completa», y la fuente dice que 1111 sí alcanza parte
de AJUSTES ⇒ quitarla puede hacer el hecho falso.

> ### s320c · qué escribe · qué dice la fuente · qué decides tú
>
> **El «antes», que este ítem no traía** (es el único cuyo objeto ES un diff, y v3 se lo dejó):
> **Hecho (hoy)**, verbatim de `gold_answers_v1.yaml:36-41` — «La clave de USUARIO por defecto es
> 1111, que **NO da acceso a la configuración avanzada completa** (solo el nivel de usuario)»,
> `cita: MU-376 p10`.
>
> **⚠️ s320d — CORRECCIÓN: mi lectura de s320c era del modelo EQUIVOCADO.** Cité
> `55315501 CAD150R Instalación` p19, que en `chunks_v2` es **`product_model = CAD-150R`**, para una
> pregunta de la **CAD-250**. Mismo error que en el ítem 5 (allí, manuales de la AM-2020 y la
> AFP-300 para una pregunta de la AFP-400). Lo destapó Alberto por la portada del 15088SP.
>
> **La fuente CORRECTA — manuales cuyo `product_model` es CAD-250:**
> - `MU-376` **p10** (§4 Nivel usuario): «La clave de usuario por defecto es **1111**.»
> - `CAD-250-MS-416-es` **p27** (§4.14.3 Configuración de usuarios y permisos): lista de usuarios
>   `USUARIO | 1111` frente a `INSTALADOR | 22`, y «**Acceso nivel 3**: o de instalador y
>   configuración le permitirá realizar **todas las acciones de configuración** del sistema o
>   acciones de diagnóstico»; el **nivel 4** queda para lo que exige abrir la central.
>
> **⚠️ s321 — SEGUNDA CORRECCIÓN, y esta invierte mi recomendación** (la disparó Alberto: «no son
> contradicciones, son niveles distintos; puedes entrar en ajustes con nivel 2, solo que no a todo»).
> Leí la sección de niveles ENTERA, no la ventana, y tenía razón:
>
> > `MC-380 2026-c` **p11** / `MS-416` **p27** — «**Acceso nivel 2** o de usuario permite: … **La
> > revisión del menú de ajustes del sistema** como datos generales como teléfono de contacto,
> > empresa instaladora o idioma · Ajuste de la **fecha** · Revisión de **versiones** · Ajuste de
> > **impresora** · Realización del **test de leds** e indicadores.»
>
> Y el diagrama del §3.1 (nivel de usuario) despliega **`Ajustes → General · Versiones ·
> Conectividad · Impresora · Test`** — sin `AVANZADO` ni `USUARIOS`. O sea: **1111 SÍ entra en
> AJUSTES, en su mitad general; lo que no alcanza es AVANZADO.**
>
> **Retiro las dos «contradicciones» que declaré en s320d**, porque no lo eran: (a) el «nivel 3» vs
> «nivel 2» de las dos revisiones del MC-380 describe el mismo requisito —ambas terminan «**con
> código de administrador**»— con el número pegado ambiguamente al menú; no es `conflicto-revision`.
> (b) Los rótulos «Nivel 1 Usuario» / «Nivel 2 Editar configuración» son las etiquetas de los dos
> **modos de menú** del propio manual, no niveles EN54: leí rótulos de UI como niveles normativos.
> La estructura normativa es consistente: usuario = Nivel 2 EN54-2, instalador = Nivel 3 EN54-2
> (`MS-416 p26`).
>
> **Mi recomendación, INVERTIDA: ❌ conservar «completa».** Es la única redacción que sigue siendo
> verdadera bajo las dos lecturas posibles de «configuración avanzada»:
>
> | si «configuración avanzada» significa… | entonces con 1111… | «completa» |
> |---|---|---|
> | el submenú **AVANZADO** | no hay acceso a **nada** de él | sobra (mi propuesta de s320c/d) |
> | **configurar en general** | hay acceso **parcial** (General, Versiones, Conectividad, Impresora, Test) | **es precisa; quitarla haría el hecho FALSO** |
>
> Aplicar la ✅ del packet («afilar» quitando «completa») sería un **empeoramiento** bajo la segunda
> lectura, y el propio ítem ya avisaba de ello. Mantengo también la enmienda del ancla: si se toca
> algo, que el apoyo sea `MS-416 p26` (usuario→Nivel 2 EN54-2 · instalador→Nivel 3 EN54-2), que es
> la única formulación sin ambigüedad — **no el número suelto**, que el manual escribe de tres
> maneras entre texto, revisiones y diagramas.
>
> *(Sol la llamaba circular por apoyarse en el error medido; Fable la daba por sólida desde la
> fuente. Con el manual correcto y la sección entera: la formulación de HOY es defendible, y el
> problema no era la negación sino mi propuesta de recortarla.)*
>
> **Tuyo, y ya solo esto:** ¿«configuración avanzada» en tu vocabulario es **el submenú AVANZADO** o
> **configurar en general**? Con la primera lectura, ✅; con la segunda, ❌. No hay más que decidir.
>
> **Escribe**: denominador invariante. Este hecho hoy sale `in_pool:false / reaches_gen:false` ⇒
> ningún juez de respuesta lo lee; el cambio no mueve métrica. Pero **conserva la clave de join**
> `qid#idx:valor` si no cambias el `valor`, así que las filas históricas seguirán pareando como si
> midieran lo mismo: decláralo al re-basear.

`[X] ✅ aplicar la propuesta · [ ] ✏️ tu redacción (anota) · [ ] ❌ dejarlo`

> ✅ **ADJUDICADO Y APLICADO (Alberto, s321)** — «configuración avanzada» = **el submenú AVANZADO**.
> Con esa lectura 1111 no alcanza nada de él, luego «completa» sobraba. **Aplicado vía `gold_store`**
> (validación 0 errores):
> - `texto`: «La clave de USUARIO por defecto es 1111, que NO da acceso al **submenu AVANZADO de
>   AJUSTES** (nivel de usuario; AVANZADO y USUARIOS requieren permiso de instalador)»
> - `cita`: `MU-376 p10 + MC-380 p31 (5.4 AVANZADO) + MC-380 p15 (3.1: AJUSTES de nivel usuario)`,
>   con **quote verbatim añadido** a `citations`. El término «AVANZADO» queda anclado en la fuente de
>   la PROPIA CAD-250, no importado de la CAD-171.
>   *(Corregido por el dúo: mi primera cita decía «p29», que es la paginación de **otra revisión** del
>   MC-380. El `pdfs_used` de este gold usa `CAD-250-MC-380-es.pdf`, donde el mismo §5.4 está en
>   **p31**. Y faltaba el quote: la cláusula adjudicada era la MENOS respaldada del ítem.)*
> - `_provenance`: p31 añadida declarando el método REAL (lectura del chunk de corpus, **no**
>   `render_pdf + cross_model` como p20-21). Declarado, no equiparado.
> - Cláusula gemela del `gold_answer` actualizada en el mismo upsert (si no, el gold afirmaría ante
>   el juez de PASS lo que el hecho niega).
> - `valor` **intacto** (`'1111'`) ⇒ la clave de join `qid#idx:valor` se conserva y las filas
>   históricas siguen pareando.

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

`[X] ✅ armonizar · [ ] ✏️ otra redacción · [ ] ❌ dejarlo`

---

> ✅ **APLICADO AL RULER (s321, 16-ago) — DEC-224.** **REDISEÑADO en la aplicación** (Sol v3/v4 + decisión de PRODUCTO de Alberto = conducta (a)): el enunciado **NO se armoniza** («de Detnov» es el estímulo; hp019 es el control — asimetría deliberada); +1 core «Securiton AG» al final (portada + p18 «Fabricante = Securiton»), sin meta-instrucción. **La corrección de marca NO la mide este gold**: el harness no atraviesa la ruta `mismatch` (Sol v4); se prueba con smoke del bot real cuando se cablee (a). Hoy el bot corrige y pide confirmar — NO «rechaza» como decía este packet.


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

`[ ] ✅ crear el gold ASÍ (core=ruta, suppl=acceso) · [X] ✏️ crearlo con cambios (anota): tiene que mencionar candado + clave 2222, porque si no no va a poder acceder a "AVANZADO" en primer lugar. ¿seguro que lo del "2222" es supplementary en hp001? · [ ] ❌ no crearlo (hp001 basta)`

---

> ✅ **APLICADO AL RULER (s321, 16-ago) — DEC-224.** `hp021` dado de ALTA con ficha completa: ruta AJUSTES > AVANZADO (core, **cita p27** — el render ±1 cazó que el chunk «p26» contiene la p27 física) + acceso candado/2222 (**core, UNO** — adjudicación de Alberto; su marca ✏️ lo pedía y la ficha v1 lo tenía mal como suppl) + 2 suppl. Estrato `sintesis-completitud`. Verificado COMPLETO (render 160dpi ±1 · GPT-5.5 en frío · localización ES+EN por doc_map).


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

---

## Consultas tuyas resueltas fuera de ítem (s321)

### `hp005` — ¿resolver su discrepancia con búsqueda abierta (internet / memoria del modelo)?

**No, y el motivo no es de principio sino de diagnóstico: no hay discrepancia de FUENTE que
resolver.** Verificado:

- El gold está `_provenance.estado: verificado`, `acuerdo: total`, `confidence: alta`, anclado en
  `MPDT190` (matriz de control, COINCIDENCIA 2 EQUIPOS, misma zona/subzona, CIRCUITO SIRENA). Su
  única nota describe un **offset de paginación ya resuelto** («el gold citó páginas IMPRESAS
  correctas → no era mis-atribución»).
- Lo que sí está documentado es de otra naturaleza: `docs/DECISIONS.md:854` clasifica hp005 en
  **GENERACIÓN**, y `:571` lo cita entre los casos donde «incluso con el chunk en top-5 el bot
  CONTRADICE hechos verificados». Es decir: **el manual es claro y el bot no lo reproduce**.

⇒ Una búsqueda externa contestaría una pregunta que nadie tiene. Y estructuralmente sería peor que
inútil: metería en el ruler un hecho que **no está en el corpus**, con lo que el eval pasaría a
exigirle al bot algo que por diseño no puede saber — el instrumento medido al revés.

**Dónde sí vale una búsqueda externa**, para que quede el criterio: para **descubrir que nos falta
un manual** (lista de adquisición). Si un hueco resulta ser «no tenemos el documento», eso se
arregla **consiguiendo el manual**, nunca tapándolo con conocimiento de fuera. Y si algún día una
fuente externa se usara como hipótesis para saber *dónde mirar* en el corpus, la afirmación
tendría que quedar anclada en el corpus antes de entrar en un gold.
