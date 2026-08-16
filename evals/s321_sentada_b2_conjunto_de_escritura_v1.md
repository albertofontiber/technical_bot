# s321 — Conjunto de escritura de la sentada B2 · **PROPUESTA, NADA APLICADO**

Las 6 escrituras que quedan de `evals/s312_goldreview_b2_packet_v3.md`, con el *antes* y el
*después* literal. **Van en UN solo `upsert` por gold** porque los splits renumeran y rompen el
join por `qid#idx` con los artefactos congelados.

**Estado**: pendiente del dúo (Protocolo 3). Es zona de dolor — toca el patrón de medida, renumera
índices, cambia el enunciado de una query del harness y **da de alta un gold nuevo**.

**No entra aquí el ítem 1** (`hp008#4`): Alberto marcó «mantener CORE» ⇒ no escribe nada. El **7**
ya está aplicado. El **2** está retirado.

---

## Efecto agregado sobre el denominador

| ítem | gold | cores antes | cores después | otros efectos |
|---|---|---|---|---|
| 3 | `hp017` | 5 | **6** | renumera `#3→#4` … `#6→#7` |
| 4 | `cat018` | 4 | **5** | renumera `#3→#4` |
| 5 | `hp006` | 4 | **3** | reescribe `gold_answer` |
| 6 | `cat020` | 3 | 3 | el hecho **entra** al denominador (hoy no se mide) |
| 8 | `hp002` | 5 | 5 | cambia la **query** del harness |
| 9 | `hp021` **nuevo** | — | **+2** | alta de gold (ruta + acceso, los dos core) |

⚠️ **Dos de estos cambios mueven el marcador en direcciones opuestas y hay que declararlo**: el
ítem 5 **quita** un core (baja la exigencia) y los ítems 3/4/6/9 **añaden** cuatro. Ninguno se
adjudicó por su efecto en el marcador — el ítem 4 se adjudicó **en contra** de él («no quiero
falsear los misses»).

---

## Ítem 3 · `hp017#2` — split + redacción de las reglas por defecto

**ANTES** (1 hecho, `core`, cita `p43`):
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"; borrar la Regla 1
> por defecto (CUALQUIER entrada de alarma activa TODOS los equipos de salida) si se va a hacer una
> programacion especifica

**DESPUÉS** — dos hechos `core`:

**(a)** `valor: Editar Configuracion` · `cita: p43`
> Acceder a la pantalla "Causa y Efecto" desde el menu "Editar Configuracion"

**(b)** `valor: Regla 1 por defecto` · `cita: p43 (A5.2) + p45 (A5.4)`
> La central sale de fabrica con dos reglas por defecto. La REGLA 1 (CUALQUIER entrada de alarma
> activa TODOS los equipos de salida) hay que BORRARLA antes de programar causa-efecto especifico,
> porque si no ANULA la programacion (A5.2). La REGLA 2 (la tecla EVACUACION activa todos los
> equipos de salida) NO interfiere con reglas disparadas por alarma y puede conservarse; solo
> procede borrarla si se va a programar la propia evacuacion de forma especifica.

**Fundamento** (`DEC-221` + `DEC-223`): A5.2 es el pasaje que da el **mecanismo** («será anulada») y
nombra solo la Regla 1; A5.4 dice «las dos» sin mecanismo. La lectura de Alberto disuelve la
aparente inconsistencia: la Regla 1 anula porque **comparte disparador** con las reglas específicas;
la Regla 2 se dispara con la tecla EVACUACIÓN y no se cruza.

**Se añade a `citations`** la quote de A5.4 (hoy ausente).

**Declarado**: la frase «*solo procede borrarla si se va a programar la propia evacuación*» es
**derivación del mecanismo**, no texto literal del manual. Si el dúo la considera inferencia
excesiva para un `core`, la alternativa es cortar el hecho tras «puede conservarse».

---

## Ítem 4 · `cat018#2` — split, **las dos CORE**

**ANTES** (1 hecho, `core`, cita `AM-8200-manu-prog p7 + p15`):
> Los modulos de SALIDA llevan un Tipo SW (p. ej. SND = sirena); un modulo de salida se dispara
> cuando se cumple su ecuacion CBE (se activa 'por asociacion CBE')

**DESPUÉS** — dos hechos `core`, **partidos por el punto y coma, sin reescribir**:

**(a)** `valor: asociacion CBE` · `cita: AM-8200-manu-prog p15`
> Un modulo de salida se dispara cuando se cumple su ecuacion CBE (se activa 'por asociacion CBE')

**(b)** `valor: Tipo SW` · `cita: AM-8200-manu-prog p7 + p15 + p41`
> Los modulos de SALIDA llevan un Tipo SW (p. ej. SND = sirena)

**Se añade a `citations`** la quote verbatim de `p41`: «*los módulos de salida utilizados para las
funciones arriba indicadas **NO ACEPTAN CBE***».

**Decisión de fidelidad, declarada**: Alberto marcó la casilla ✅ «partir en dos (ambas CORE)», **no**
la ✏️ que proponía reescribir la mitad «Tipo SW» sobre la regla de bloqueo de p41. Por eso el texto
se **preserva** y p41 entra solo como cita de apoyo. Si el dúo cree que el hecho (b) sin la regla de
bloqueo es débil como `core`, es una ✏️ que debe volver a Alberto — no la tomo yo.

---

## Ítem 5 · `hp006#2` — demote **+ reescritura del `gold_answer`**

**ANTES** (`core`, cita `MIDT170 p63 (f71)`):
> Para acotar un fallo en el lazo se usan los modulos aisladores ISO-X, que aislan la rama en averia
> del resto del lazo (requeridos para Estilo 7 segun NFPA)

**DESPUÉS** (`supplementary`, cita `MIDT170 p70 (f77) + p64 (f71)`):
> Los modulos aisladores ISO-X aislan del resto del lazo la rama en la que se produce un
> CORTOCIRCUITO (MIDT170: «El ISO-X detecta este cortocircuito y desconecta la ramificacion en
> averia abriendo el lado positivo del lazo»), y son requisito del Estilo 7 de NFPA. NO intervienen
> en un fallo de TIERRA: la tabla «Funcionamiento del Lazo» da el mismo resultado para Tierra en
> Estilo 6 y en Estilo 7, y solo mejora la fila Corto.

**Y en el MISMO upsert, el `gold_answer`** — se retira el inciso:

> ~~El metodo general consiste en aislar/desconectar circuitos progresivamente **-en el lazo,
> mediante los aisladores ISO-X-** hasta que desaparece el aviso~~
>
> → «El metodo general consiste en aislar/desconectar circuitos progresivamente hasta que
> desaparece el aviso»

**Por qué el texto también cambia y no solo la etiqueta** (`DEC-223`): un `supplementary` que siga
afirmando que el ISO-X «acota el fallo» en una pregunta de TIERRA seguiría siendo falso; el demote
solo lo saca de la exigencia de PASS, no lo hace verdadero. **Esto excede lo literalmente marcado**
(la casilla decía «demote») y por eso va señalado para que el dúo lo mire y Alberto lo confirme.

**Corrección de cita arrastrada**: el gold registra offset +8 pero el pie de `f71` dice **64** y el
de `f77` dice **70** ⇒ offset real **7**. Las citas impresas se corrigen de paso.

---

## Ítem 6 · `cat020#2` — re-anclar del país al PROTOCOLO

**ANTES** (`core`, `valor: manual de variaciones Espana`):
> Estos valores por defecto son especificos de la VERSION ESPANA: figuran en el Manual de
> variaciones para Espana, que COMPLEMENTA el manual de configuracion base (996-203-005-X) donde
> esta la configuracion general del nivel de alarma (seccion Modos Horarios)

**DESPUÉS** (`core`, `valor: protocolo Morley-IAS`):
> Estos valores por defecto son los del PROTOCOLO MORLEY-IAS: viven en la seccion §5.3.10.5
> «Informacion especifica segun el protocolo» → §5.3.10.5.1 «…para protocolo Morley-IAS» del Manual
> de variaciones de mercado, que COMPLEMENTA el manual de configuracion base (996-203-005-X) donde
> esta la configuracion general del nivel de alarma (seccion Modos Horarios).

**Fundamento**: el **documento** es de variaciones de mercado, pero la **sección** que porta los tres
valores se titula literalmente «según el PROTOCOLO». Anclar a «versión España» atribuye a un país lo
que el manual atribuye a un protocolo.

**Efecto medible declarado**: hoy este hecho **no se juzga** — el predicado meta-ref corta antes
porque el `valor` empieza por «manual». Con un `valor` de contenido **entra al denominador** y,
sobre la respuesta congelada, **sale MISS**. No añade un fallo: deja de ocultarlo.

**Se mantiene el `texto` largo**: recortarlo porque puntúa bajo en el matcher sería afinar el gold
contra el instrumento.

---

## Ítem 8 · `hp002` — armonizar el enunciado, con la conducta (a) firmada

**ANTES**:
> El detector ASD535 **de Detnov** está dando una alarma intermitente de flujo bajo. ¿Cuál es la
> causa más probable y cómo se diagnostica?

**DESPUÉS** (espeja a `hp019`, que ya lo dice bien):
> El detector de aspiración ASD535 **(Securiton, distribuido por Detnov)** está dando una alarma
> intermitente de flujo bajo. ¿Cuál es la causa más probable y cómo se diagnostica?

`conducta_esperada` se **mantiene** en `answer`: Alberto firmó **(a)** — el bot debe responder con la
nota de que es Securiton distribuido por Detnov, no rechazar.

⚠️ **Riesgo declarado, y es el mayor del conjunto**: cambiar el enunciado **cambia la query del
harness**. Los 8 hechos de `hp002` fueron medidos contra la pregunta vieja; sus resultados
congelados dejan de ser comparables sin re-medir. El «cero impacto métrico» del packet estaba medido
**para la redacción de hoy**. Esto hay que decirlo en el `_provenance`.

**Nota**: `hp013` («la Detnov ADW535») mantiene la misma clase marca↔producto y **no** se toca aquí.

---

## Ítem 9 · `hp021` — **alta de gold nuevo** (CAD-171, menú avanzado)

**Puerta de no-duplicado EJECUTADA** (Protocolo 4): `hp001` cubre el menú avanzado de la **CAD-250**
y `ho008` cubre puntos/zonas de la **CAD-171**. Ninguno cubre la **ruta** de la CAD-171. Lo
discriminante es el manual propio (`MI-716`), no el `MC-380` compartido.

- **qid**: `hp021` (primer libre) · **split**: `dev` · **conducta**: `answer`
- **Pregunta**: «¿Cómo se accede al menú de configuración avanzada en la Detnov CAD-171?»
- **Hecho `core`** — `valor: AJUSTES > AVANZADO` · `cita: Manual_CAD-171-MI-716-es p26/p34/p35`
  > La ruta al menu de configuracion avanzada es AJUSTES (menu principal) > AVANZADO (submenu)
- **Hecho `core`** — `valor: candado + 2222` · `cita: MI-716 p25 §6.1`
  > El acceso al submenu AVANZADO esta protegido: tocar el icono del candado y introducir la clave
  > de ADMINISTRADOR por defecto 2222

**Anclado en la FUENTE, no en el fallo**: el crítico del dúo en s320c fue que la ruta se justificaba
desde `DEC-185` —un incidente de producción— y desde la prosa del bot. Se re-ancló leyendo
`MI-716` p26/p34/p35. **Se descarta** el hecho de v1 que remitía a la «Guía Avanzada»: ES el
`MC-380 rev c` que ya está en el corpus.

> ### ⚠️ CORRECCIÓN (s321) — el acceso va **CORE**, no `supplementary`. Fallo mío al redactar v1.
>
> La ficha original del packet proponía `supplementary` «por solape con `hp001#0/#1`». **Alberto ya
> lo había adjudicado en contra**, y su marca ✏️ lo dice literal: «*tiene que mencionar candado +
> clave 2222, **porque si no no va a poder acceder a "AVANZADO" en primer lugar***». Yo arrastré la
> ficha propuesta en vez de su marca.
>
> **Y su pregunta —«¿seguro que lo del 2222 es supplementary en hp001?»— destapa el segundo fallo.**
> Verificado contra el ruler: `hp001#0` (candado) y `hp001#1` (2222) son **los dos `core`**. Dejarlo
> `supplementary` aquí habría puesto el MISMO paso de acceso como CORE para la CAD-250 y
> SUPPLEMENTARY para la CAD-171, sin razón de principio. Incoherencia dentro del propio ruler.
>
> **Efecto en el marcador, declarado**: el acceso ya sale OK hoy, así que subirlo a `core` **sube el
> %OK por construcción**. No es motivo en contra —la adjudicación es técnica: sin la clave no
> llegas— pero se declara, igual que se declaró el efecto contrario en el ítem 4.
>
> **Queda una sub-decisión de Alberto**: `hp001` guarda candado y clave como **dos** cores separados.
> Aquí van en **uno solo** (lectura mínima de «candado + clave 2222»). Si prefiere paridad exacta con
> `hp001`, son dos cores en vez de uno — dígalo y se parte.

---

## Lo que el dúo tiene que atacar

1. ¿Alguna de las 6 escrituras **afina el gold contra el instrumento** en vez de contra la fuente?
   (es el pecado recurrente de esta sentada — ya cazado dos veces).
2. El ítem 5 **excede lo literalmente marcado**: reescribo el `texto` del hecho donde la casilla
   decía solo «demote». ¿Es fiel a la adjudicación o me arrogo alcance que es de Alberto?
   *(El ítem 9 tenía el mismo vicio —yo puse `supplementary` contra su marca explícita— y ya está
   CORREGIDO a `core`; lo cazó Alberto, no el dúo. Vale como recordatorio de que la ficha
   PROPUESTA de un packet no es la ADJUDICACIÓN: hay que leer la marca.)*
3. El ítem 8 invalida la comparabilidad de 8 hechos medidos. ¿Está bien declarado, o debería
   bloquear la escritura hasta re-medir?
4. Renumeración: ¿qué artefactos congelados indexan por `qid#idx` y se rompen? ¿Basta declararlo?
5. La derivación del ítem 3 sobre la Regla 2, ¿es inferencia admisible en un `core`?
