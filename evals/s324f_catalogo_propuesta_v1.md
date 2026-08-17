# s324f — El atajo de catálogo: responder a la pregunta que se hizo, y declarar el límite (propuesta v1)

**Disparador**: el smoke real del piloto. Alberto pregunta «¿qué fabricantes tienes?» y el bot
responde con 22 modelos agrupados bajo `DESCARTADO`, `EN_unico`, `ES` y `PT`. No pudo puntuarlo
con 👎 porque los atajos no llevan botones, y la respuesta ni siquiera quedó guardada.

**Estado**: propuesta. NO cableado. Impacto MEDIO-ALTO en serving y en zona de dolor (catálogo /
corpus) ⇒ dúo obligatorio (Protocolo 3) antes de tocar código.

---

## 0. El diagnóstico, medido

Reproducción exacta de `_handle_catalog` contra producción (`chunks_v2`, 26.216 chunks):

| Defecto | Medida |
|---|---|
| `limit=5000` ignorado — PostgREST corta en 1000 filas | recibe **1000 de 26.216** (3,8 %) |
| sin `ORDER BY` | qué 1000, es arbitrario (orden físico) |
| `r.get("category", "General")` **no cubre `None`**, y `if model and cat` las descarta | **630 de esas 1000** caen |
| `category` contaminada con idioma y estado de proceso | salen `DESCARTADO`, `EN_unico`, `ES`, `PT` como si fueran familias |
| resultado servido | **22 modelos de 756** = **2,9 %** |
| la pregunta era por fabricantes | la respuesta son modelos |
| ruta de atajo sin `reply_markup` | no se puede dar 👍/👎 |
| `log_query` del atajo sin `response` | no queda registro de qué se contestó |

**Lo que NO está afectado, verificado para no ampliar la alarma**: el retrieval. Los otros
`limit` altos (`_get_source_files_for_model`, `_get_pm_for_sources`, ambos 5000) filtran por
modelo o por fichero, y **ningún modelo ni fichero llega a 1000 chunks** (el mayor, ID3000, tiene
665). Sí está truncado `get_category_models` (pide 2000): cuatro categorías superan las 1000 filas
—`None` 15.619, `ES` 6.233, `Detectores especiales` 1.670, `EN_unico` 1.060—.

## 0-bis. La regla que este código viola, y que ya estaba adjudicada

`_productos_marca` lleva escrito **«r27 Fable C1: jamás los pm de chunks»**. Un dúo anterior ya
decidió que el catálogo servido no se deriva de los `product_model` de la tabla de chunks, sino
del catálogo normalizado ∩ `doc_map`. El inventario por marca lo cumple; `_handle_catalog` es un
superviviente del diseño anterior que **nunca se migró**. Esto no es un diseño nuevo: es terminar
de aplicar una decisión que ya se tomó — y es la razón de fondo por la que los cinco defectos de
arriba existen a la vez. Todos son consecuencias de mirar la fuente equivocada.

---

## 1. Recomendación

### R1 · Que la pregunta por fabricantes se responda con fabricantes

Hoy «¿qué fabricantes tienes?» cae en la ruta `catalogo`, que vuelca modelos. Se separa la
intención: **fabricantes** → lista de marcas con su número de productos; **productos** → sigue
llevando al inventario por marca, que ya funciona bien.

Fuente: **catálogo ∩ doc_map**, la misma que `_productos_marca` — hoy **35 fabricantes y 1000
productos** con documentación mapeada.

### R2 · El catálogo global deja de existir como volcado

Los 756 modelos **no caben en un mensaje de Telegram** (tope 4.096 caracteres). Ninguna cantidad
de paginación arregla eso: el volcado completo es una respuesta que no se puede dar. Se sustituye
por la lista de fabricantes (35 nombres entran de sobra) más la invitación a preguntar por uno,
que es la vía que ya sirve el inventario acotado.

### R3 · La pieza general de «no cabe» — adjudicación de Alberto (17-ago)

> «puede ser generalizable a preguntas en las que la respuesta no quepa, para facilitar que el
> usuario haga un follow-up, además de incluir un mensaje de limitación en caso de llegar a dicho
> límite para que el usuario lo entienda»

Una hoja pura, `src/bot/acotar.py`, con un contrato único: recibe los elementos, el presupuesto y
cómo se pide el resto; devuelve el texto acotado **más el aviso de que se recortó** y **la
coletilla de follow-up**. Dos propiedades que la hacen un control y no un adorno:

- **el aviso es parte del acotado, no una llamada aparte** — si el texto se recorta, el aviso
  existe por construcción; no se puede truncar en silencio olvidándose de avisar;
- **es hoja pura**: sin red, sin entorno, sin Telegram. Se prueba con una tabla de casos.

El patrón ya existe hecho a mano en `_inventario_agrupado` («…y N categorías más», «…y N más»):
esto lo extrae a una pieza y lo aplica también donde hoy falta.

### R4 · Los atajos, observables

`reply_markup=_feedback_keyboard(...)` y `response=` en el `log_query` de las rutas de atajo. Es
lo más barato de los cuatro y lo que hace visible cualquier regresión futura **sin depender de que
Alberto la cuente**: hoy el único detector de este fallo fue él.

**Orden sugerido**: R4 primero (barato, y empieza a medir), luego R1+R2 (el fallo que se ve), R3
como refactor que absorbe lo que R2 escribe a mano.

---

## 2. Alternativas consideradas y por qué se descartan

| Alternativa | Por qué no |
|---|---|
| **Subir el `limit` o paginar** el escaneo de chunks | Arregla el síntoma y deja la fuente equivocada. 26 peticiones por catálogo, y seguiría agrupando por una `category` contaminada. Viola r27 |
| **Limpiar la columna `category`** y seguir usándola | Es trabajo de corpus, real pero distinto (queda anotado como deuda). No hace falta para servir bien: el catálogo normalizado ya tiene la clasificación |
| **Partir el catálogo en varios mensajes** | 756 modelos son ~8 mensajes seguidos. Un DG no lee eso; y el problema seguiría siendo que preguntó por fabricantes |
| **Un `ORDER BY` y ya** | Hace el corte determinista, no menos ciego. Serviría el 3 % siempre igual |
| **Vista o RPC en Supabase con `DISTINCT`** | Añade migración y una segunda fuente de verdad para lo que el catálogo ya sabe. Se reconsideraría sólo si el catálogo normalizado no cargara |

---

## 3. Gaps y riesgos declarados

1. **Las dos fuentes de «cuántos fabricantes» no coinciden y hoy conviven**: la cabecera usa
   `get_manufacturers_by_docs()` → **30 marcas** (cuenta documentos); la propuesta usa catálogo ∩
   doc_map → **35** (cuenta productos). Miden cosas distintas y las dos son ciertas, pero **el bot
   no puede decir 30 en una frase y listar 35 en la siguiente**. Hay que unificar o declarar la
   diferencia en el texto. **No lo resuelvo aquí: es la primera pregunta para el dúo.**
2. **El aviso de privacidad dice «una treintena de fabricantes»**. Aguanta con 30 y con 35, pero si
   la cifra servida sube, hay que re-verificar el texto (riesgo ya declarado en el v8).
3. **`get_category_models` sigue truncado** tras esta propuesta si no se toca: R1/R2 no pasan por
   él. Queda como deuda con su medida (4 categorías por encima de 1000).
4. **`category` contaminada es deuda de corpus**, no de serving: 15.619 chunks con `category` vacía
   (60 %) y valores de idioma/proceso conviviendo con familias reales.
5. **R4 cambia lo que se guarda**: los atajos empezarán a escribir `response`. No es dato personal
   nuevo (es texto que genera el bot) pero sí más volumen en `query_logs`.
6. **Riesgo de la propia R2**: alguien que hoy usa el volcado para ver modelos deja de tenerlo. Con
   96 consultas de un usuario, el coste real es cero, pero es un cambio de conducta visible.

---

## 4. Por qué es BP, estructural y escalable

**BP**: se responde a la pregunta formulada, se declara el límite en vez de recortar en silencio, y
la respuesta servida se guarda y se puede puntuar. **Estructural**: no sube el `limit` — cambia la
fuente por la que ya es canónica desde r27, y con eso los cinco defectos caen a la vez porque
todos eran el mismo defecto. **Escalable**: a 30+ fabricantes el volcado completo empeora
monótonamente mientras la lista de marcas sigue cabiendo; y `acotar` es una pieza que sirve a
cualquier respuesta futura que no quepa, no sólo al catálogo.
