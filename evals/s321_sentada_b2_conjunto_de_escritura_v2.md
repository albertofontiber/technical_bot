# s321 — Conjunto de escritura de la sentada B2 · **v2 · PROPUESTA, NADA APLICADO**

**v1 → v2.** La v1 (`s321_sentada_b2_conjunto_de_escritura_v1.md`) recibió **NO SÓLIDO** de Sol
(8 hallazgos · 4 críticos · **0 falsos positivos** tras verificación regla-C). Antes de la v2,
Alberto cerró en conversación las decisiones que Sol devolvió a su alcance, y se leyó de primera
mano cada página que ancla un cambio. Lo que cambia respecto a v1 se marca **[v2]**.

**Estado**: pendiente del dúo emparejado (Sol xhigh + Fable) sobre ESTE fichero. Es zona de dolor:
toca el patrón de medida, renumera índices, cambia el enunciado de una query del harness y da de
alta un gold nuevo. **Van en UN solo `upsert` por gold**.

**No entra el ítem 1** (`hp008#4`, «mantener CORE» ⇒ no escribe). El **7** ya está aplicado. El **2**
está retirado.

---

## Efecto agregado — declarado POR INSTRUMENTO **[v2]**

Sol cazó que la v1 mezclaba denominadores. Hay dos instrumentos con reglas distintas:

- **`atomic_scorer.py:260`** — puntúa **todos** los `core` presentes (`core = [r ... if r["tipo"]=="core"]`), sin filtro meta-ref.
- **`factlevel_assessment.py`** — además salta los hechos cuyo `valor` dispara `_is_meta_ref` (empieza por «Manual…»).

| ítem | gold | cores antes→después | atomic_scorer | factlevel_assessment | otros |
|---|---|---|---|---|---|
| 3 | `hp017` | 5→**6** (+1 suppl) | +1 core | +1 core | renumera `#3→#4`…`#6→#7` |
| 4 | `cat018` | 4→**5** | +1 core | +1 core | renumera `#3→#4` |
| 5 | `hp006` | 4→**3** | −1 core | −1 core | reescribe `gold_answer` + procedencia |
| 6 | `cat020` | 3→3 | **sin cambio** (ya lo puntuaba) | el hecho **entra** (hoy lo salta) | — |
| 8 | `hp002` | 5→**6** | +1 core | +1 core | **cambia la query** del harness |
| 9 | `hp021` nuevo | —→**2** | +2 core | +2 core | alta |

Ninguna se adjudicó por su efecto en el marcador. El ítem 4 se adjudicó **en contra** de él («no
quiero falsear los misses»); el ítem 9 sube el %OK por construcción y se declara.

---

## Ítem 3 · `hp017#2` — split; (b) se conserva; la Regla 2 va `supplementary` **[v2]**

**ANTES** (1 `core`, `cita: p43`):
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"; borrar la Regla 1
> por defecto (CUALQUIER entrada de alarma activa TODOS los equipos de salida) si se va a hacer una
> programacion especifica

**DESPUÉS** — tres hechos:

**(a)** `core` · `valor: Editar Configuracion` · `cita: 997-671-005-3 p43 (A5.2)`
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"

**(b)** `core` · `valor: Regla 1 por defecto` · `cita: 997-671-005-3 p43 (A5.2)` — **texto SIN CAMBIOS**:
> Borrar la Regla 1 por defecto (CUALQUIER entrada de alarma activa TODOS los equipos de salida) si
> se va a hacer una programacion especifica

**(c)** `supplementary` · `valor: Regla 2` · `cita: 997-671-005-3 p43 (A5.2) + p45 (A5.4)` **[v2 nuevo]**:
> La Regla 2 por defecto (la tecla EVACUACION activa todos los equipos de salida) no anula las
> reglas causa-efecto que se introduzcan; conservarla no impide la programacion especifica. Solo la
> Regla 1 la anula (A5.2).

**Por qué así** (adjudicación de Alberto, s321): (b) ya nombraba solo la Regla 1 y es coherente con
su lectura — no se toca. Su lectura sobre la Regla 2 (no anula porque su disparador es la tecla, no
la alarma) se **documenta** sin **exigirse**: `supplementary` no condiciona el PASS. Es el mismo
patrón que `hp001#5` (aviso de seguridad como suppl). Usa el verbo del manual («anula», A5.2), no
«interfiere». **Se retira** la derivación de v1 sobre programar la evacuación por fases: no está en
el manual. Con esto queda respetado `DEC-221(a)`: el criterio de mecanismo ancló, y el alcance lo
decidió Alberto.

**`citations`**: se añade la quote de A5.4 («borrar las dos reglas»), hoy ausente, con la nota de
que A5.2 es el pasaje-mecanismo.

---

## Ítem 4 · `cat018#2` — split, las dos CORE, con la regla de p65 **[v2]**

**ANTES** (1 `core`, `cita: AM-8200-manu-prog p7 + p15`):
> Los modulos de SALIDA llevan un Tipo SW (p. ej. SND = sirena); un modulo de salida se dispara
> cuando se cumple su ecuacion CBE (se activa 'por asociacion CBE')

**DESPUÉS** — dos `core`:

**(a)** `valor: asociacion CBE` · `cita: AM-8200-manu-prog-spa p7 + p65`
> Un modulo de salida se dispara cuando se cumple su ecuacion CBE (se activa "por asociacion CBE");
> es una via de activacion distinta de la del Tipo SW.

**(b)** `valor: Tipo SW / TIPO ID` · `cita: AM-8200-manu-prog-spa p65 (mecanismo) + p40-41 (tabla)`
> Cada modulo de salida lleva un Tipo SW (el manual tambien lo llama TIPO ID), y ese tipo determina
> si admite CBE: la central NO PERMITE programar una ecuacion a un modulo con TIPO ID para
> senalizaciones de caracter general — los de la tabla "Modulos de salida para senalizaciones
> generales" (PWRC, GPND, GAC, GTC, GAS, GTS, SND, STR...), que se activan por su propia funcion;
> p. ej. SND es el tipo de la salida sirena.

**Anclas leídas de primera mano en el manual del gold** (`AM-8200-manu-prog-spa`, `pm=AM-8200/AM-8200-BB`):
- **p65** «Ecuación CBE nula»: «**NOTA: para los módulos de salida, la central no permite programar
  una ecuación si el módulo tiene un TIPO ID para señalizaciones de carácter general.**» — es el
  MECANISMO (`DEC-221`): la central rechaza la ecuación. Ni Sol ni la v1 lo habían localizado; lo
  señaló la edición IT/EN pública de Honeywell y se **verificó en el corpus** antes de usarlo.
- **p40-41** tabla «MÓDULOS DE SALIDA PARA SEÑALIZACIONES GENERALES»: p40 = PWRC, GPND, APND, GAC,
  TPND, GTC, TRS, ZFLT, ZDIS, MAINF, REM, GAS, GTS, ZFLTC, MAINFC, REMC; p41 = GASV, GTSV, ZFLTV,
  MAINFV, REMV, SND, STR; nota subrayada: «los módulos de salida utilizados para las funciones
  arriba indicadas no aceptan CBE». **La v1 listaba solo los 7 de p41 — la tabla son 23.**
- **p7**: en alarma se activan como viñetas separadas «Salida sirena · Módulos programados con
  tipo-SW SND · Todos los módulos activados por asociación CBE» ⇒ dos vías distintas.
- **TIPO ID = Tipo SW**: la p1 (índice) titula las tablas «Lista HW **tipo ID** módulos» y la p42 la
  misma sección de UDS como «**Tipo SW**». Mismo concepto, dos etiquetas; el hecho cita las dos.
- **SND = tipo de la salida sirena**: uso en p7/p44/p51/p61/p62/p69 («todos los dispositivos
  programados con tipo SW SND» de la salida sirena). La v1 lo restringía a «flashes» por una sola
  fila (p41), que en la edición inglesa lista modelos de sirena — la fila IT/ESP parece copia de STR.

**Lo que NO entra en el hecho, y se declara**: «los tipos genéricos (FORC/CON/CONV/GSND/GSTR) sí
aceptan CBE». La p39 solo los **lista**; que acepten CBE es deducción por contraste, no texto del
manual. Se deja aquí como nota, **no en el ruler**.

**Corrección al packet**: la cita de la EVACUACIÓN («módulos programados con Tipo SW = SND») **SÍ está
en el manual del gold** (p7). La v1 del packet la atribuía a la variante AM-8200N.

---

## Ítem 5 · `hp006#2` — demote + reescritura de texto, `gold_answer` **y procedencia** **[v2]**

**ANTES** (`core`, `cita: MIDT170 p63 (f71)`):
> Para acotar un fallo en el lazo se usan los modulos aisladores ISO-X, que aislan la rama en averia
> del resto del lazo (requeridos para Estilo 7 segun NFPA)

**DESPUÉS** (`supplementary`, `cita: MIDT170 p70 (f77) + p64 (f71)`):
> Los modulos aisladores ISO-X aislan del resto del lazo la rama en la que se produce un
> CORTOCIRCUITO (MIDT170: "El ISO-X detecta este cortocircuito y desconecta la ramificacion en
> averia abriendo el lado positivo del lazo"), y son requisito del Estilo 7 de NFPA. NO intervienen
> en un fallo de TIERRA: la tabla "Funcionamiento del Lazo" da el mismo resultado para Tierra en
> Estilo 6 y en Estilo 7, y solo mejora la fila Corto.

**`gold_answer`** — se retira el inciso «*—en el lazo, mediante los aisladores ISO-X—*»; el método de
mitades se queda.

**`_provenance` [v2]** — Sol cazó que la autoridad seguía contradiciendo el cambio. Se actualiza:
- `acuerdo`: «…'Tierra' como condición de avería del lazo (f71) + aisladores ISO-X» → «…(f71); los
  ISO-X aíslan CORTOCIRCUITOS (f77) y no intervienen en tierra (tabla f71) — DEC-223».
- `nota`: offset «+8» → «**+7** (pie 'MI-DT-170c 64'/'70' en f71/f77; el +8 registrado en s27 estaba
  corrido una página)».
- se añade `verificado_por`: «s321 · DEC-223 · workflow wf_38d0cbac-aaf + verificación manual».

**Excede la casilla** («demote») y se declara: un `supplementary` que siga afirmando que el ISO-X
«acota el fallo» en una pregunta de tierra sigue siendo falso; el demote lo saca de la exigencia de
PASS, no lo hace verdadero. Alberto lo vio en el packet (ítem 5 marcado con la nota de reescritura).

---

## Ítem 6 · `cat020#2` — conservar los DOS ejes: España + protocolo **[v2]**

Sol (crítico): reescribir a «protocolo Morley-IAS» a secas **sobre-generaliza** — el documento se
declara «versión para España» y el `gold_answer` lo dice tres veces. Tenía razón: la v1 cambiaba un
ancla por otra en vez de conservar ambas.

**ANTES** (`core`, `valor: manual de variaciones Espana`):
> Estos valores por defecto son especificos de la VERSION ESPANA: figuran en el Manual de
> variaciones para Espana, que COMPLEMENTA el manual de configuracion base (996-203-005-X) donde
> esta la configuracion general del nivel de alarma (seccion Modos Horarios)

**DESPUÉS** (`core`, `valor: version Espana / protocolo Morley-IAS`):
> Estos valores por defecto son los de la VERSION ESPANA para el PROTOCOLO MORLEY-IAS: figuran en el
> Manual de variaciones para Espana, en la seccion §5.3.10.5 "Informacion especifica segun el
> protocolo" → §5.3.10.5.1 "para protocolo Morley-IAS", que COMPLEMENTA el manual de configuracion
> base (996-203-005-X) donde esta la configuracion general del nivel de alarma (seccion Modos
> Horarios)

**`gold_answer` y `_provenance`**: **sin cambios** — ya dicen «versión España»; el hecho deja de
contradecirlos y les añade el eje del protocolo. El `valor` deja de empezar por «Manual», con lo que
`factlevel_assessment` deja de saltarlo (`atomic_scorer` ya lo puntuaba — ver tabla).

---

## Ítem 8 · `hp002` — armonizar el enunciado **+ hecho que exige la nota** **[v2]**

Sol (medio, confirmado): armonizar retira el estímulo del estrato `oem-relabel`, y **ningún** hecho
de `hp002` exigía la nota Securiton/Detnov ⇒ la conducta (a) firmada quedaba sin medir. **Alberto
adjudicó**: armonizar **y** añadir un `core` que la exija.

**ANTES**:
> El detector ASD535 **de Detnov** está dando una alarma intermitente de flujo bajo. ¿Cuál es la
> causa más probable y cómo se diagnostica?

**DESPUÉS** (espeja a `hp019`):
> El detector de aspiración ASD535 **(Securiton, distribuido por Detnov)** está dando una alarma
> intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?

**Hecho nuevo `core`** · `valor: Securiton` · `cita: ASD535_TD_T131192es_h (portada/fabricante) + hp019`
> El ASD535 es un detector de aspiracion de SECURITON, distribuido en Espana por Detnov; la
> respuesta debe dejarlo claro (no es un producto Detnov)

`conducta_esperada` se mantiene `answer` (conducta (a): responder con la nota, no rechazar).

**Riesgo declarado en `_provenance`**: cambiar el enunciado **cambia la query del harness**; los 8
hechos medidos contra la pregunta vieja dejan de ser comparables hasta re-medir. `hp013` («la Detnov
ADW535») mantiene la misma clase y **no se toca**.

---

## Ítem 9 · `hp021` — alta de gold, **ficha COMPLETA** **[v2]**

Sol (crítico): la v1 no era una ficha escribible. Ahora sí. Todo leído de primera mano en
`Manual_CAD-171-MI-716-es` (`pm=CAD-171`).

```yaml
qid: hp021
question: ¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?
conducta_esperada: answer
split: dev
estrato: [familia-ambigua, sintesis-completitud]
# ^ vocabulario CONTROLADO de gold_store (ESTRATOS_AUTORIA): `familia-ambigua` = misma serie Vesta
#   que la CAD-250 (hp001) compartiendo el MC-380; el fallo fue no distinguir la ruta de la CAD-171
#   con su manual propio. `sintesis-completitud` = la respuesta fusiona p25 (acceso) + p26 (ruta) del
#   mismo manual — mismo estrato que ho008 (el otro gold de la CAD-171). La v2 inicial traía
#   [single-doc, uso-real]: NO existen en el vocabulario, la puerta los habría rechazado como error.
gold_answer: |-
  En la Detnov CAD-171 el menu de configuracion avanzada esta en AJUSTES (Menu principal) >
  AVANZADO (Submenu). Para llegar hay que entrar como administrador: desde la pantalla de reposo
  tocar el icono del candado, que abre la PANTALLA DE ACCESO, e introducir la clave de administrador
  (por defecto 2222). El manual MI-716 no documenta el contenido de AVANZADO: remite a la Guia
  Avanzada de Configuracion (MC-380).
atomic_facts:
- texto: La ruta al menu de configuracion avanzada es AJUSTES (Menu principal) > AVANZADO (Submenu)
  tipo: core
  estado: presente
  valor: AJUSTES > AVANZADO
  cita: MI-716 p26 (diagrama de navegacion, columna Submenu bajo AJUSTES) + p34/p35
- texto: El acceso esta protegido: tocar el icono del candado en la pantalla de reposo abre la
    PANTALLA DE ACCESO, e introducir la clave de administrador por defecto 2222
  tipo: core
  estado: presente
  valor: candado + 2222
  cita: MI-716 p25 §6.1 "Acceso como administrador"
- texto: El MI-716 no documenta el contenido del submenu AVANZADO; remite a la Guia Avanzada de
    Configuracion (= MC-380, ya en corpus)
  tipo: supplementary
  estado: presente
  valor: Guia Avanzada
  cita: MI-716 p25
confidence: alta
pdfs_used: [Manual_CAD-171-MI-716-es.pdf]
_provenance:
  estado: verificado
  metodo: corpus_read (chunks_v2, product_model=CAD-171) + no-duplicado ejecutado
  fuente: Manual_CAD-171-MI-716-es
  paginas: [25, 26, 34, 35]
  verificado_por:
  - Claude s321 (lectura directa p25 §6.1 candado/2222; p26 diagrama Submenu con AVANZADO)
  - duo s320c (critico de genesis: anclar en fuente, no en DEC-185) — resuelto en s321
  acuerdo: ruta AJUSTES > AVANZADO en diagrama p26 (cita de DIAGRAMA, no de prosa); acceso p25
    literal "Introduzca la clave de administrador por defecto, 2222"
  fecha: '2026-08-16'
  nota: >
    NO-DUPLICADO (DEC-025): hp001 cubre el menu avanzado de la CAD-250 (MC-380 compartido) y ho008
    cubre puntos/zonas de la CAD-171; ninguno cubre la RUTA de la CAD-171 con su manual propio.
    Genesis: incidente DEC-185 (bot encabezo AJUSTES>GENERAL con AVANZADO servido) — pero el gold se
    ancla en MI-716, no en el fallo. Staleness: la conducta congelada era de sonnet-4-6; si el fallo
    no se reproduce con Opus 5, el gold nace como centinela anti-regresion. Acceso como UN core
    (adjudicacion Alberto s321), no dos como hp001: lectura minima de "candado + clave".
```

**Efecto**: +2 core dev. Ninguno dispara `_is_meta_ref`. Se sube el %OK por construcción (el
acceso ya sale OK hoy) — declarado.

---

## Lo que el dúo tiene que atacar en la v2

1. **Fidelidad**: ¿alguna de las 6 afirma como fuente algo que la fuente no dice? (v1 lo hizo dos
   veces; se retiraron «FORC…sí aceptan CBE» y «solo procede borrar la Regla 2 si…»).
2. **Autoridad coherente**: ¿queda algún gold `verificado` cuya procedencia/`gold_answer`
   contradiga el hecho cambiado tras el upsert?
3. **Alcance vs adjudicación**: ¿algo excede lo que Alberto marcó, más allá de lo declarado
   (reescritura del texto en ítem 5)?
4. **Renumeración**: qué artefactos congelados indexan `qid#idx` y cómo se declara la rotura.
5. **`hp002`**: ¿el hecho «Securiton» está bien anclado (portada del TD) o falta cita verbatim?
