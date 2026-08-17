# s324f — Lote del piloto vivo: cuota agotada, transcripción de marcas y aviso v9

**Los tres cambios nacen del piloto REAL de esta noche**, no de un plan. Alberto invitó a la
primera usuaria (Sara) y en menos de una hora aparecieron dos defectos que ninguna suite veía.

**Estado**: cableado en rama, suite pendiente de correr entera. Alberto autorizó desplegar lo que
esté verde y con dúo. **NO desplegado todavía.**

---

## 1. El diagnóstico, medido

### 1.a · «Sistema saturado» cuando lo que pasaba es que no había saldo

Sara mandó un audio. La transcripción (OpenAI Whisper) devolvió:

```
429 · insufficient_quota · "You have no credits remaining. Add credits to continue using the API"
```

El bot le respondió **«estoy saturado, prueba en unos minutos»**. Dos afirmaciones falsas en una
frase: no había congestión, y reintentar no iba a funcionar nunca. La taxonomía metía todos los
429 en el mismo cajón.

Y peor: **el único camino por el que eso llegó al responsable fue que ella se lo contara**. Un
fallo que sólo el operador puede arreglar viajaba al usuario, que no puede hacer nada.

Causa raíz verificada: la clave `OPENAI_API_KEY` de Railway era **distinta** de la local y
pertenecía a una cuenta sin saldo (comparadas por huella, sin exponer valores). Anthropic y Voyage
eran la misma y con saldo — o sea, el bot funcionaba con texto y no con audio.

### 1.b · «Detnov» → «Death Knob»

Con la clave arreglada, Alberto probó un audio: Whisper transcribió el fabricante como **«Death
Knob»** y el bot no encontró nada. Lo revelador, medido: **«Detnov» YA ESTABA en el prompt** que
se manda a Whisper. El prompt es una pista de contexto, no un diccionario que obligue, y está
**saturado — 990 de 1000 caracteres**, casi todos códigos de modelo. Meter los 30 fabricantes
ahí habría diluido más la señal, no menos.

Un fabricante mal transcrito cuesta mucho más que un modelo mal transcrito: sin marca, el turno
entero se queda sin ancla y la respuesta es «no tengo eso» — justo la que hunde la confianza de
quien prueba el bot por primera vez.

---

## 2. Qué se hace

### R1 · El 429 tiene dos caras y se sirven distinto

`error_taxonomy` mira el TEXTO del error dentro del 429 (es el único sitio donde el proveedor
dice cuál es; el SDK no los distingue en el tipo). Si dice cuota → decisión propia: **no
reintentable**, severidad `critico`, y un mensaje que no invita a repetir lo que va a fallar.
Cubre las variantes de OpenAI y Anthropic.

**Degradación declarada**: si un proveedor cambia su redacción, deja de reconocerse y vuelve a
clasificarse como saturación — la conducta de hoy. Se pierde la mejora, no se rompe nada. Hay
test que lo ancla.

### R2 · El aviso va a quien PUEDE arreglarlo

Toda incidencia `critico` manda un Telegram a los ids de `BOT_ALLOWLIST_BOOTSTRAP`. **No lleva ni
la consulta ni el identificador de quien la hizo**: el operador necesita saber qué está roto, no
quién tropezó, y eso ya vive en `bot_errors`/`query_logs` con su gobernanza.

**Con cota anti-inundación**: una hora por clase+etapa. Un fallo de cuota no ocurre una vez —
ocurre en cada turno hasta que alguien pague—, y sin cota el operador recibiría un mensaje por
turno y dejaría de mirarlos, que es exactamente perder el aviso. En memoria y declarado: un
redespliegue reinicia la cota y se vuelve a avisar, que es la degradación correcta.

### R3 · Corrección de la transcripción, en la normalización de voz

> **CORREGIDO tras el dúo r40 (hallazgo de Sol, confirmado por Fable).** La primera versión de
> esta propuesta —y del código— aplicaba la corrección **en el borde de la transcripción**,
> argumentando que así llegaba «tanto a la búsqueda como a lo que se registra». Era **la decisión
> equivocada y contradecía un contrato que ya existía en el código**: «raw ASR stays visible and
> is logged unchanged; the retrieval form is explicit when it differs». Reescribir antes de que
> nadie lo vea significa que el técnico no puede detectar una corrección FALSA y que el histórico
> miente sobre lo que produjo Whisper.

Tabla curada de confusiones **observadas** (hoy: una) aplicada dentro de `normalize_voice_query`,
que es el sitio que ya tiene el contrato correcto: **`raw` se conserva intacto** —lo que el
técnico ve y lo que se registra— y la corrección va en la forma de búsqueda, que el bot ya
enseña aparte cuando difiere. Verificado: un audio «que centrales tiene Death Knob» conserva ese
texto como dicho y busca por «Detnov».

**Disciplina, igual que `_MANUFACTURER_ALIASES`**: sólo entra lo observado en una transcripción
real, citando dónde se vio. Cada entrada inventada es una forma nueva de corromper una pregunta
que estaba bien. Hay un tope de 25 con un mensaje que obliga a parar y replantear si se llega.

### R4 · Aviso v9: la mención a la UE baja a `/privacidad`

Decisión de Alberto. **No desaparece** —informar de las transferencias internacionales es
obligatorio y son ciertas—: cambia dónde se lee. La primera capa dice que hay proveedores
implicados y remite al detalle; `/privacidad` se consulta **sin haber aceptado nada**, así que la
información sigue disponible antes de decidir. Hay un test nuevo cuyo único trabajo es separar
«lo movimos» de «lo perdimos».

### R5 · Migración 017 preparada, **sin aplicar**

Alberto pidió poder tener más de seis clases de error. La 017 abre el CHECK y añade
`cuota_agotada`. **El orden no se puede invertir**: primero se aplica la migración, y sólo
entonces se cambia la clase en el código. Al revés, el bot escribiría un valor que el CHECK
rechaza y se perdería el registro de la incidencia justo cuando más falta hace. Por eso hoy la
cuota se guarda como `llm_fallo` —que además es correcto: es determinista— y el paso queda
escrito en los dos sitios.

---

## 3. Alternativas consideradas y por qué se descartan

| Alternativa | Por qué no |
|---|---|
| Distinguir la cuota por **código HTTP** | No se puede: los dos casos son 429. El proveedor sólo lo dice en el cuerpo |
| Meter los **30 fabricantes** en el prompt de Whisper | Medido: el prompt está a 990/1000 y «Detnov» ya estaba dentro. Más nombres = más dilución, y habría que sacar códigos de modelo que sí funcionan |
| **Reintentar** la transcripción ante un 429 | Con cuota agotada, reintentar es gastar tiempo del técnico para fallar igual |
| Avisar al operador de **todo** fallo | Un Telegram por timeout convierte el aviso en ruido que se ignora. Sólo `critico` |
| Clase `cuota_agotada` **ya mismo** en el código | El CHECK de `bot_errors` la rechazaría y se perdería el registro. Es el orden lo que importa, no la clase |
| **Quitar** la mención a la UE del aviso | Es información obligatoria y cierta. Moverla informa igual; quitarla haría el aviso falso |

## 4. Gaps y riesgos declarados

1. **La detección de cuota depende del texto del proveedor.** Si cambia la redacción, degrada a
   la conducta de hoy. Es un riesgo aceptado y con test; la alternativa (parsear el JSON del
   cuerpo) ataría el código a una estructura que también cambia.
2. **La cota del aviso vive en memoria.** Un redespliegue la reinicia. Para un piloto de dos
   personas es el equilibrio correcto; una tabla sería infraestructura para un problema que no
   tenemos.
3. **La tabla de confusiones tiene UNA entrada.** No pretende cubrir el espacio de errores de
   Whisper: pretende que el siguiente cueste una línea y que nadie lo llene de suposiciones.
4. **El v9 obliga a re-aceptar a todo el mundo.** Hoy son dos personas (Alberto y Sara). Es el
   segundo bump del día, y Alberto lo autorizó sabiendo el coste.
5. **No hay smoke real de la corrección de audio**: se ha probado la función con el texto
   observado, pero el testigo de verdad es otro audio contra Telegram. Queda para Alberto.
6. **El aviso al operador no se ha ejercitado contra Telegram real**, sólo con dobles.

## 5. Por qué es BP, estructural y escalable

**BP**: no se le miente al usuario sobre lo que puede hacer, el aviso llega a quien puede actuar,
y la corrección de la transcripción se aplica donde todo el mundo la ve. **Estructural**: la
distinción cuota/congestión vive en la taxonomía —el punto único por el que ya pasan todos los
fallos—, no en un `if` dentro del manejador de voz; y el aviso cuelga de la severidad, así que
cualquier crítico futuro avisa solo sin tocar nada. **Escalable**: añadir una confusión es una
línea con su cita; añadir una clase de error es una migración preparada; y el orden de los dos
pasos está escrito para que nadie lo invierta.
