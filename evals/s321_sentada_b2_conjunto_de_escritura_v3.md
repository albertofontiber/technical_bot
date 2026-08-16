# s321 — Conjunto de escritura de la sentada B2 · **v3 · PROPUESTA, NADA APLICADO**

**Historial.** v1 → Sol NO SÓLIDO (8 · 4 críticos · 0 FP). v2 → Sol 8 hallazgos (6 críticos), de
los que **5 confirmados** contra código/datos (regla C), 1 parcial (`familia-ambigua`), 2 con la
premisa mal leída por AMBOS (Sol y yo): «A5.4 ordena eliminar ambas reglas» — **A5.4 es una sección
de EJEMPLOS**, cazado por Alberto. Esta v3 incorpora todo. Lo que cambia respecto a v2 va **[v3]**.

**Estado**: pendiente del dúo emparejado (Sol xhigh + Fable) sobre ESTE fichero — Fable no ha
corrido aún sobre ninguna versión (no se gasta sobre un artefacto que ya se sabía que cambiaba).

**Alcance mecánico [v3]**: además de los 6 upserts, este conjunto **incluye la migración s277 y la
cascada de canarios EN EL MISMO COMMIT** (Sol crítico 4-5, confirmados). Ver §Migración.

---

## Efecto agregado — por instrumento (sin cambios respecto a v2 salvo `hp002`)

| ítem | gold | cores antes→después | atomic_scorer | factlevel_assessment | otros |
|---|---|---|---|---|---|
| 3 | `hp017` | 5→**6** (+1 suppl) | +1 | +1 | renumera `#3→#4`… ⇒ **migración s277** |
| 4 | `cat018` | 4→**5** | +1 | +1 | renumera `#3→#4` (sin clave histórica afectada) |
| 5 | `hp006` | 4→**3** | −1 | −1 | `gold_answer` (2 frases) + procedencia |
| 6 | `cat020` | 3→3 | sin cambio | el hecho entra | — |
| 8 | `hp002` | 5→**6** | +1 | +1 | cambia la query; core «Securiton» **al final** |
| 9 | `hp021` nuevo | —→**2** | +2 | +2 | alta |

---

## Ítem 3 · `hp017#2` — split; (b) intacto; Regla 2 `supplementary` **reformulado [v3]**

**ANTES** (1 `core`, `cita: p43`):
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"; borrar la Regla 1
> por defecto (CUALQUIER entrada de alarma activa TODOS los equipos de salida) si se va a hacer una
> programacion especifica

**DESPUÉS**:

**(a)** `core` · `valor: Editar Configuracion` · `cita: 997-671-005-3 p43 (A5.2)`
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"

**(b)** `core` · `valor: Regla 1 por defecto` · `cita: 997-671-005-3 p43 (A5.2)` — texto **sin cambios**:
> Borrar la Regla 1 por defecto (CUALQUIER entrada de alarma activa TODOS los equipos de salida) si
> se va a hacer una programacion especifica

**(c)** `supplementary` · `valor: Regla 2` · `cita: 997-671-005-3 p43 (A5.2) + p45 (A5.4 Ejemplo 1)` **[v3]**:
> El pasaje normativo (A5.2) solo exige borrar la Regla 1, que anula la programacion especifica. La
> Regla 2 (tecla EVACUACION activa TODOS los equipos de salida) no esta en esa advertencia; el
> manual solo indica eliminar las dos reglas por defecto en el Ejemplo 1 de A5.4 — un caso de
> evacuacion por etapas, donde la programacion toca la propia evacuacion.

**Anclas leídas verbatim (`997-671-005-3_Configuration_ES`)**:
- **p43 (A5.2)**, subrayado en el original: «*Es fundamental borrar la regla 1 si se va a realizar una
  programación específica, ya que, si no, esta será anulada.*» Solo la Regla 1. Con mecanismo.
- **p45 (A5.4)**: encabezado «*A5.4 **Ejemplos** de reglas de causa-efecto — En esta sección se
  ilustra la programación… mediante varios ejemplos típicos*». Dentro del **Ejemplo 1** («*¿Cómo
  crear una regla para permitir una **evacuación por etapas**…?*»): «*el usuario encontrará aquí las
  dos reglas de causa-efecto por defecto. **Deben eliminarse si se van a crear reglas de causa-efecto
  personalizadas.***»

**Por qué así**: (b) ya nombraba solo la Regla 1 y no se toca. El (c) **no afirma «no anula»** (Sol
crítico 2: el manual no lo dice literalmente) — afirma solo lo que las dos páginas dicen: la norma
nombra una regla, el ejemplo dice dos, y el ejemplo es de evacuación. La lectura de Alberto (la Regla
2 se dispara con la tecla, no con la alarma, y por eso el ejemplo que sí toca la evacuación borra
las dos) queda **implícita en los hechos citados** y explícita en `DEC-221`/packet — no firmada
como texto del fabricante. `supplementary` ⇒ no condiciona el PASS (adjudicación de Alberto).

**Corrección a `DEC-221` [v3]**: hoy describe A5.4 como «la instrucción de limpieza completa».
Hay que precisar: **es un ejemplo**, no una instrucción normativa. Se edita en el mismo commit.

---

## Ítem 4 · `cat018#2` — split, ambas CORE, con p65; **`gold_answer` alineado [v3]**

**ANTES** (1 `core`): «Los modulos de SALIDA llevan un Tipo SW (p. ej. SND = sirena); un modulo de
salida se dispara cuando se cumple su ecuacion CBE (se activa 'por asociacion CBE')»

**DESPUÉS** — dos `core` (idénticos a v2):

**(a)** `valor: asociacion CBE` · `cita: AM-8200-manu-prog-spa p7 + p65`
> Un modulo de salida se dispara cuando se cumple su ecuacion CBE (se activa "por asociacion CBE");
> es una via de activacion distinta de la del Tipo SW.

**(b)** `valor: Tipo SW / TIPO ID` · `cita: AM-8200-manu-prog-spa p65 (mecanismo) + p40-41 (tabla)`
> Cada modulo de salida lleva un Tipo SW (el manual tambien lo llama TIPO ID), y ese tipo determina
> si admite CBE: la central NO PERMITE programar una ecuacion a un modulo con TIPO ID para
> senalizaciones de caracter general — los de la tabla "Modulos de salida para senalizaciones
> generales" (PWRC, GPND, GAC, GTC, GAS, GTS, SND, STR...), que se activan por su propia funcion;
> p. ej. SND es el tipo de la salida sirena.

**`gold_answer` [v3]** (Sol medio, confirmado: conservaba el compuesto). El punto 3 pasa de:
> ~~3. LA SALIDA: los modulos de salida llevan un Tipo SW (por ejemplo SND para sirena); un modulo de
> salida se dispara cuando su ecuacion CBE se cumple (se activa 'por asociacion CBE').~~
a:
> 3. LA SALIDA: un modulo de salida se dispara cuando su ecuacion CBE se cumple (se activa "por
> asociacion CBE"). Ojo al Tipo SW (TIPO ID) del modulo: la central NO permite programar una
> ecuacion a un modulo con TIPO ID para senalizaciones de caracter general (tabla p40-41: PWRC,
> GAC, GTC, GAS, GTS, SND, STR...); esos se activan por su propia funcion, p. ej. SND es el tipo de
> la salida sirena.

**`_provenance.acuerdo` [v3]**: se añade «s321: split #2 en asociación-CBE + Tipo SW; regla de
bloqueo p65 verificada en corpus (y corroborada por ediciones IT/EN públicas de Honeywell)».

Anclas verbatim: las de v2 (p65 · p40-41 · p7 · índice p1/p42 para TIPO ID=Tipo SW · uso de SND en
p7/44/51/61/62/69). **Fuera del hecho**: «FORC/CON/CONV/GSND/GSTR sí aceptan CBE» (p39 solo lista).

---

## Ítem 5 · `hp006#2` — demote + **las DOS frases** del `gold_answer` + procedencia **[v3]**

**Hecho DESPUÉS** (`supplementary`, `cita: MIDT170 p70 (f77) + p64 (f71)`) — igual que v2:
> Los modulos aisladores ISO-X aislan del resto del lazo la rama en la que se produce un
> CORTOCIRCUITO (MIDT170: "El ISO-X detecta este cortocircuito y desconecta la ramificacion en
> averia abriendo el lado positivo del lazo"), y son requisito del Estilo 7 de NFPA. NO intervienen
> en un fallo de TIERRA: la tabla "Funcionamiento del Lazo" da el mismo resultado para Tierra en
> Estilo 6 y en Estilo 7, y solo mejora la fila Corto.

**`gold_answer` [v3]** — Sol crítico 3, confirmado: había **dos** frases, no una. Las dos cambian:
1. viñeta «~~Para acotar un fallo en el lazo se emplean los modulos aisladores ISO-X, que aislan la
   rama en averia del resto del lazo (MIDT170).~~» → «Los modulos aisladores ISO-X (requeridos en
   Estilo 7) aislan cortocircuitos del lazo; no intervienen en un fallo de tierra (MIDT170).»
2. «El metodo general consiste en aislar/desconectar circuitos progresivamente ~~-en el lazo,
   mediante los aisladores ISO-X-~~ hasta que desaparece el aviso» → sin el inciso.

**`_provenance` [v3]**: `acuerdo` → «…'Tierra' como condición de avería del lazo (f71); los ISO-X
aíslan CORTOCIRCUITOS (f77) y no intervienen en tierra (tabla f71) — DEC-223»; `nota` offset «+8» →
«+7 (pie 'MI-DT-170c 64'/'70' en f71/f77)»; `verificado_por` += «s321 · DEC-223 · wf_38d0cbac-aaf
+ verificación manual».

---

## Ítem 6 · `cat020#2` — dos ejes (idéntico a v2)

`valor: version Espana / protocolo Morley-IAS` · texto:
> Estos valores por defecto son los de la VERSION ESPANA para el PROTOCOLO MORLEY-IAS: figuran en el
> Manual de variaciones para Espana, en la seccion §5.3.10.5 "Informacion especifica segun el
> protocolo" → §5.3.10.5.1 "para protocolo Morley-IAS", que COMPLEMENTA el manual de configuracion
> base (996-203-005-X) donde esta la configuracion general del nivel de alarma (seccion Modos
> Horarios)

`gold_answer`/`_provenance` sin cambios (ya dicen España). Solo entra al denominador de
`factlevel_assessment`; `atomic_scorer` ya lo puntuaba.

---

## Ítem 8 · `hp002` — enunciado + core «Securiton» **anclado en la fuente, sin «distribuido» [v3]**

**Enunciado DESPUÉS** (espeja `hp019`):
> El detector de aspiración ASD535 (Securiton, distribuido por Detnov) está dando una alarma
> intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?

**Hecho nuevo `core` — AL FINAL de la lista** (no desplaza `#0/#1/#2` históricos):
> `valor: Securiton` · `cita: ASD535_TD_T131192es_h p1 (portada: "SECURITON — Securiton AG,
> Alpenstrasse 20, 3052 Zollikofen, Suiza")`
> El ASD535 es un detector de aspiracion del fabricante SECURITON (Securiton AG, Suiza), no un
> producto Detnov; la respuesta debe dejarlo claro.

**Sol crítico 6, confirmado [v3]**: `hp019` **no** tiene fuente para la relación comercial (sus
citas son de temperatura), y **ningún chunk del manual ASD535 menciona Detnov** (verificado:
`ilike '*Detnov*'` sobre `ASD535_TD_T131192es_h` = 0). Por eso el hecho **NO exige «distribuido en
España por Detnov»**: eso no está en el corpus. Exige lo que la portada prueba — que es Securiton.
La mención a Detnov queda en el **enunciado** (que es la query, no un hecho) para conservar el
estímulo `oem-relabel`.

`conducta_esperada`: `answer` (conducta (a)). `_provenance` declara: cambio de query ⇒ los 8 hechos
previos no comparables hasta re-medir; `hp013` no se toca.

---

## Ítem 9 · `hp021` — ficha completa; **estrato y procedencia corregidos [v3]**

```yaml
qid: hp021
question: ¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?
conducta_esperada: answer
split: dev
estrato: [sintesis-completitud]
#  ^ [v3] SOLO este (Sol medio, confirmado): la pregunta identifica CAD-171 sin ambigüedad ⇒
#    `familia-ambigua` describía un riesgo cross-product, no ambigüedad de la consulta, y habría
#    contaminado la métrica por estrato. `sintesis-completitud` = la respuesta fusiona p25 (acceso)
#    + p26 (ruta) del mismo manual — mismo estrato que ho008 (el otro gold de la CAD-171).
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
citations:
- {manual: Manual_CAD-171-MI-716-es, page: 25, quote: "Toque la pantalla táctil con el dedo sobre la figura del candado (🔒). Al hacerlo accederá a la PANTALLA DE ACCESO solicitando el código de acceso o password."}
- {manual: Manual_CAD-171-MI-716-es, page: 25, quote: "Introduzca la clave de administrador por defecto, 2222."}
- {manual: Manual_CAD-171-MI-716-es, page: 26, quote: "Menú principal … AJUSTES (highlighted) · Submenú … GENERAL · VERSIONES · USUARIOS · AVANZADO · CONECTIVIDAD …"}
- {manual: Manual_CAD-171-MI-716-es, page: 25, quote: "Si desea información detallada de utilización y configuración de la central consulte la Guía Avanzada de Configuración."}
confidence: alta
pdfs_used: [Manual_CAD-171-MI-716-es.pdf]
_provenance:
  estado: verificado
  metodo: corpus_read (chunks_v2; aplicabilidad por doc_map, NO por product_model — TECH_DEBT #84) + no-duplicado ejecutado + render pendiente
  fuente: Manual_CAD-171-MI-716-es
  paginas: [25, 26, 34, 35]
  verificado_por:
  - Claude s321 (lectura directa p25 §6.1 candado/2222; p26 diagrama Submenu con AVANZADO; p34/p35 repiten AVANZADO en la lista de Submenu)
  - duo s320c (critico de genesis: anclar en fuente, no en DEC-185) — resuelto en s321
  acuerdo: ruta AJUSTES > AVANZADO en diagrama p26 (cita de DIAGRAMA, no de prosa); acceso p25 literal "Introduzca la clave de administrador por defecto, 2222"
  fecha: '2026-08-16'
  nota: >
    NO-DUPLICADO (DEC-025): hp001 = menu avanzado de la CAD-250 (MC-380 compartido); ho008 =
    puntos/zonas de la CAD-171. Ninguno cubre la RUTA de la CAD-171 con su manual propio.
    Genesis: incidente DEC-185, pero el gold se ancla en MI-716, no en el fallo. Staleness: la
    conducta congelada era de sonnet-4-6; si el fallo no se reproduce con Opus 5, nace como
    centinela anti-regresion. Acceso como UN core (adjudicacion Alberto s321). GAP DECLARADO
    (Sol critico 1): el render al pixel del diagrama p26 y la doble senal independiente que
    RULER_DESIGN §2 exige NO se han hecho aun — se hacen en el commit de aplicacion (render de p25/p26
    + cross_verify_image.py), y hasta entonces el gold NO se escribe como 'verificado'.
```

**[v3] Sol crítico 1, aceptado en parte**: la ficha declaraba `verificado` con solo lectura de
chunks. RULER_DESIGN §2 exige render + doble señal. **Se hará en el commit de aplicación** (render de
p25/p26 y `scripts/cross_verify_image.py`), y si no se hace, el gold entra como `pending`, no
`verificado`. Y la referencia a `product_model` en el método se retira (TECH_DEBT #84): la
aplicabilidad se lee del `doc_map` (`Manual_CAD-171-MI-716-es` → primary `detnov:cad-171`,
a verificar en el commit).

---

## §Migración s277 + cascada de canarios **[v3]** — en el MISMO commit que los upserts

**Sol críticos 4-5, confirmados contra `scripts/s277_build_c1_p1_contract.py:514-537`.** El builder
resuelve las claves históricas OK del ledger `s113` por **posición entre los cores presentes**
(`historical_core_facts`) y **aborta** si `valor` no coincide (`historical suffix/value mismatch`).

**Mapa exacto de la rotura** (claves históricas OK en los golds tocados, extraídas del ledger):
```
cat018#0:Control By Events         ← índice 0, split en pos 2 ⇒ NO se mueve
cat020#0 / cat020#1                ← texto de #2 cambia sin mover índices ⇒ NO se mueven
hp002#0 / #1 / #2                  ← core nuevo AL FINAL ⇒ NO se mueven
hp006#0:Fallo de Tierra            ← demote de #2 por detrás ⇒ NO se mueve
hp017#0 / hp017#1                  ← delante del split ⇒ NO se mueven
hp017#3:seis tipos de retardo      ← el split inserta (b) en pos 3 ⇒ SE MUEVE a #4  ✗
```
**Una sola clave rompe**: `hp017#3`. Y el builder **ya la retira** del histórico (línea 536-537,
`old_disclosure`) — pero DESPUÉS del bucle que valida índice/valor (519-525), así que el `raise`
salta antes. **Migración**: sacar la retirada de `hp017#1` y `hp017#3` **antes** de la validación
por índice (o validar solo las claves que sobreviven). Cambio de ~3 líneas, en el builder, con test.

**Cascada** (DEC-218, ejecutada ya una vez en s321): regenerar el contrato → copiar a mano los pins
a `prereg_v2/v3` y al scorer (TECH_DEBT #77) → re-anclar los tres canarios `s203/s204/s205` con
diff acotado → manifest histórico **intacto** → 4/4 ficheros de test en verde. **Marcas + migración +
re-anclaje en UN commit** — si van separados la suite queda roja en cada frontera.

---

## Lo que el dúo tiene que atacar en la v3

1. **Fidelidad**: ¿alguna de las 6 afirma como fuente algo que la fuente no dice? Especial atención
   al (c) de `hp017` — reformulado para NO decir «no anula».
2. **Norma vs ejemplo**: ¿está bien caracterizado A5.4 como sección de ejemplos y A5.2 como el
   único pasaje normativo sobre las reglas por defecto?
3. **Autoridad coherente**: tras los upserts, ¿queda algún `gold_answer`/`_provenance` contradiciendo
   su hecho? (v2 dejó dos: `hp006` frase 1 y `cat018` punto 3 — corregidos aquí).
4. **Migración s277**: ¿el mapa de claves es completo? ¿la migración propuesta (mover la retirada
   antes de la validación) es la mínima correcta o hay algo más limpio?
5. **`hp021`**: ¿es honesto entrar como `pending` si el render no se hace, o eso mete un gold
   no-medible al ruler?
