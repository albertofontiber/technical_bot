# s324f — El atajo de catálogo (propuesta v2, tras dúo r39)

**Cambia respecto de v1**: el dúo devolvió **13 hallazgos** (Sol 8 · Fable 5) y **ninguno de los
dos dijo SÓLIDO**. Verificados uno a uno contra el código y los datos (regla C), **11 se
confirman**, **1 es falso positivo** y **1 se adopta con matiz**. Los dos de mayor severidad
resultaron ser **mecanismos reales con efecto medido cero** — se adoptan igualmente, pero como
guarda, no como urgencia. Esta v2 es la propuesta corregida; el detalle del dúo va al §5.

**Estado**: NO cableado. Quedan **dos decisiones de Alberto** (§4) que ningún revisor puede tomar.

---

## 1. El diagnóstico (sin cambios, y ambos revisores lo anclan)

`_handle_catalog` responde «¿qué fabricantes tienes?» con **22 modelos de 756** (2,9 %) agrupados
bajo `DESCARTADO`, `EN_unico`, `ES` y `PT`. Cinco causas: `limit=5000` que PostgREST corta en 1000
· sin `ORDER BY` · `r.get("category","General")` que no cubre `None` y descarta 630 de las 1000
filas · `category` contaminada con idioma y estado de proceso · y la pregunta era por fabricantes.
Más dos de observabilidad: sin botones de feedback y sin `response` guardado.

**Dato que refuerza el diagnóstico, aportado por Fable**: la lección del cap de 1000 **ya está
escrita en ese mismo fichero**, 200 líneas antes (`get_available_manufacturers`, retriever.py:852-855,
con la historia de los smokes s21 y s65). No es una lección por aprender: es una función que
nunca se migró.

**Cómo se midieron las cifras** (exigencia de Fable, y es correcta): los conteos de productos y
marcas salen del **catálogo en fichero** (`data/catalog/products.jsonl`, 1696 productos → 1011
activos no-candidatos → **1000 con documentación mapeada**), no de PostgREST. La coincidencia de
«1000» con el max-rows del servidor es casualidad y está comprobada: el fichero se lee entero.
Los conteos de documentos sí salen de REST, **paginando** hasta agotar (1243 documentos).

## 2. Lo que se hace

### R1 · La pregunta por fabricantes se responde con fabricantes

Fuente: catálogo ∩ doc_map, **con filtro de servibilidad** (hallazgo crítico de Sol): sólo cuenta
un producto si tiene al menos un documento con `status='active'` e idioma servible.

> **Medido antes de adoptarlo**: sin el filtro son 35 marcas y 1000 productos; con él, **35 marcas
> y 993 productos**. No cae ninguna marca y caen 7 productos (0,7 %). El filtro entra porque es
> correcto y cuesta una condición, **no porque arregle un fallo visible hoy**. Declarar esto es la
> diferencia entre adoptar un hallazgo y obedecerlo.

### R2 · El volcado global se sustituye por la lista de marcas

756 modelos no caben en un mensaje de Telegram (4.096 caracteres, y `_PRESUPUESTO_MSG` ya lo
acota a 3.500). **Corrección de v1** (Sol y Fable, los dos): era falso escribir que «ninguna
paginación arregla eso» — repartirlo en ~8 mensajes es técnicamente posible. La razón real es que
**no conviene**: nadie lee ocho mensajes seguidos, y seguiría sin responder a lo que se preguntó.

### R3 · La pieza de «no cabe» — adjudicación de Alberto

Sol la marcó como posible sobreingeniería («abstrae anticipadamente un render ya resuelto»). Se
mantiene por dos razones que v1 no declaró y que son la respuesta al hallazgo:

1. **Está adjudicada literalmente**: «puede ser generalizable a preguntas en las que la respuesta
   no quepa […] además de incluir un mensaje de limitación en caso de llegar a dicho límite para
   que el usuario lo entienda» (17-ago). Sol declaró no haber podido inspeccionar esa fuente.
2. **Tiene consumidores concretos, no hipotéticos**: `_inventario_agrupado` (que ya implementa el
   patrón a mano, dos veces: «…y N categorías más» y «…y N más»), el inventario plano, y R2. Tres
   sitios, dos de ellos ya escritos.

Si al implementarla los tres no encajan en el mismo contrato, se abandona la extracción y se deja
el aviso en cada sitio: la adjudicación es «avisar y ofrecer follow-up», no «tener un módulo».

### R4 · Los atajos, observables — **con el orden invertido**

Hallazgo de Sol, confirmado en el código: hoy el atajo **envía primero y registra después**, así
que colgarle `reply_markup` crearía botones apuntando a una fila que aún no existe (o que falló).
La ruta RAG ya tiene el patrón correcto y es el que se copia:

```python
feedback_markup = (_feedback_keyboard(query_log_uuid)
                   if _feedback_keyboard_enabled() and query_logged else None)
```

Es decir: **registrar primero, comprobar que se registró, y sólo entonces enviar con botones**;
si el registro falla, se envía sin ellos. Incluye el gate `TELEGRAM_FEEDBACK` (verificado en
Railway: **`on`**, igual que `TELEGRAM_FEEDBACK_REASON`) y el anclaje del mensaje.

### R5 · Contrato de clasificación *(nuevo — Sol y Fable coinciden)*

v1 decía «se separa la intención» sin decir dónde ni cómo. Falta y se escribe **antes** de tocar
código: dónde vive el split (el regex de la ruta `catalogo` en el planificador), qué pasa con «¿qué
productos tienes?» sin marca, qué pasa con las colisiones, y **el equivalente en inglés** — el
patrón actual sólo cubre español.

### R6 · Objetivo y gate *(nuevo — Sol)*

v1 tenía baseline pero no criterio de éxito auditable. El gate, antes de cablear:

| # | Criterio | Cómo se comprueba |
|---|---|---|
| G1 | «¿qué fabricantes tienes?» devuelve marcas, no modelos | matriz de intents ES+EN, test |
| G2 | El conjunto servido = catálogo ∩ doc_map ∩ servible | test contra el catálogo en fichero |
| G3 | Ninguna respuesta supera `_PRESUPUESTO_MSG` | test de cota |
| G4 | Si se recorta, el texto lo dice y ofrece follow-up | test de la pieza R3 |
| G5 | Rutas de atajo: 👍/👎 presente y `response` guardado, sin FK colgante | test con `log_query` fallando |
| G6 | Sin sobre-routing: preguntas de producto siguen al inventario | casos de control |

---

## 3. Deuda que este cambio NO arregla, con su guarda

Corrección de framing exigida por **ambos** revisores: v1 decía «todos eran el mismo defecto» y
eso **sobre-afirma**. La fuente equivocada explica el truncamiento, la categoría vacía y la
contaminada; **no** explica ni la intención mal clasificada ni la falta de observabilidad, que son
fallos independientes y los arreglan R5 y R4 por separado.

| Deuda | Medida hoy | Guarda |
|---|---|---|
| **Tres** fuentes de «cuántos fabricantes» (Fable encontró la tercera: `get_available_manufacturers`, ruta `marca_no_servida`, **sin filtro `status`**) | 30 (documentos) · 35 (catálogo) · 30 (disponibles). **Marcas fantasma hoy: 0** — las 30 tienen documento activo | Unificar o declarar. **No puede quedar como está**: el bot puede decir dos cifras distintas en dos frases |
| `get_category_models` pide 2000, recibe 1000 | 4 categorías por encima: `None` 15.619, `ES` 6.233, `Detectores especiales` 1.670, `EN_unico` 1.060 | Paginar o acotar. R1/R2 no pasan por ahí |
| `_get_source_files_for_model` / `_get_pm_for_sources` piden 5000 | **Hoy ningún modelo ni fichero llega a 1000** (mayor: ID3000, 665) | **Corrección de v1**: dije «no afectado» y eso es una **foto, no un invariante** (Fable). Además el filtro es `imatch` por familia, no modelo exacto. Queda como deuda **con test-guarda** que se ponga rojo al acercarse al tope, porque el sesgo del diversify sería **silencioso** |
| `category` contaminada | 15.619 chunks (60 %) sin categoría; idiomas y estados de proceso como si fueran familias | Trabajo de corpus, no de serving |

---

## 4. Las dos decisiones que necesitan a Alberto

Ningún revisor puede tomarlas: son de negocio.

**D1 · ¿Qué es un fabricante cuando un producto se vende bajo varias marcas?** Medido: **56
productos** con más de una marca. `morley:vsn-4-plus` se vende bajo *Morley-IAS*, *Notifier* y
*Vision (HLSI)*; `kidde:2010-2-pak-rmsdk` bajo *Kidde Commercial*, *Edwards* y *Ziton*. Opciones:
(a) aparece en las tres marcas — lo que ve el técnico, que busca por la marca que tiene delante;
(b) sólo en la del fabricante real. Afecta al número que se publica y a la coherencia con el
inventario por marca, que hoy **sí** usa `vendido_bajo`.

**D2 · ¿Qué nombre se enseña?** El catálogo guarda nombres comerciales (*Kidde Commercial*,
*Argus Security*, *Vision (HLSI)*) distintos del identificador interno. ¿Se enseñan tal cual, o
hay una lista corta de nombres presentables? Hoy existe una tabla de alias **curada a mano y
corta a propósito** (`_MANUFACTURER_ALIASES`) que resolvía el problema inverso.

---

## 5. Adjudicación del dúo r39, hallazgo por hallazgo

| # | Rev. | Sev. declarada | Veredicto tras verificar | Qué se hace |
|---|---|---|---|---|
| 1 | Sol | crítico | **Real, efecto medido: 7/1000 productos, 0 marcas** | Se adopta el filtro (R1); severidad rebajada a menor-con-guarda |
| 2 | Sol | medio | **Confirmado**: 56 productos con >1 marca | → D1 y D2 |
| 3 | Sol | medio | **Confirmado**: el atajo envía antes de registrar | R4 con el orden invertido |
| 4 | Sol | medio | **Confirmado** (coincide con Fable 5) | R5 |
| 5 | Sol | medio | **Confirmado**: no había gate | R6 |
| 6 | Sol | medio | **Parcial**: la generalización está adjudicada por Alberto; la exigencia de consumidores concretos, aceptada | R3 con los tres consumidores declarados |
| 7 | Sol | menor | **Confirmado** (coincide con Fable 1) | §3, framing corregido |
| 8 | Sol | menor | **Confirmado**: «ninguna paginación» era falso absoluto | R2 reescrito |
| 9 | Fable | medio | **Confirmado** | §3 |
| 10 | Fable | medio | **Confirmado**: tercera fuente sin filtro `status`. **0 marcas fantasma hoy** | §3, deuda con guarda |
| 11 | Fable | medio | **FALSO POSITIVO**: «1000 = max-rows» era casualidad (fichero: 1696 → 1011 → 1000). Sospecha bien planteada | Se declara cómo se midió (§1) |
| 12 | Fable | medio | **Confirmado**: «no afectado» era foto, no invariante | §3, deuda con test-guarda |
| 13 | Fable | menor | **Confirmado** (= Sol 4) | R5 |

**Lo que el dúo NO cambió**: el diagnóstico (ambos lo anclaron en código), la decisión de no
volcar el catálogo completo, y las alternativas descartadas. **Lo que sí cambió**: dos afirmaciones
sobre-generalizadas mías, el orden de R4 —que habría creado botones rotos—, y la aparición de una
tercera fuente que yo no había visto.
