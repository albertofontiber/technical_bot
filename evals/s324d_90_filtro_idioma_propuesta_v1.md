# s324d — TECH_DEBT #90: el filtro de idioma POR CHUNK tira castellano en documentos multilingües. Diagnóstico, alcance y fix propuesto

**Estado: NADA cableado. v3 tras el dúo r36 (Sol 5 hallazgos, 2 críticos, todos verificados y aplicados).** La recomendación sigue siendo **D (no tocar el pipeline)**, pero por razones distintas y mejor fundadas: el alcance medido no la sostenía sola (cohorte sesgada) y el fix es bastante más caro de lo que yo había escrito (toca ingesta **y serving y esquema**). Propuesta para el sí de Alberto.
Producción no cambia con este documento.

## 1 · El defecto, medido en la cadena entera (no inferido)

Caso: `D1056-1_NFXI-BS-BSF` (ficha de la base NFXI-BS/BSF, 2 páginas), que el censo de cobertura marcó como
**castellano perdido**. Medí cada eslabón el 17-ago:

| eslabón | resultado |
|---|---|
| PDF nativo | tiene el contenido |
| LlamaParse (`parse_page_with_agent`, job `f2274867`) | `md` = **50.540 chars** con «Configuración», «Desactivado», «Descripción» |
| guarda de md degenerado (#87) | **no dispara — y hace bien**: ratio 0,95 y 0,43, con estructura |
| `chunk_document` | **4 chunks / 50.527 chars** |
| filtro `_DROP_LANGUAGES` (`pipeline.py`) | **descarta 2 chunks = 47.193 chars (93 %)** por `detect_language` = `de` |
| corpus hoy | **2 chunks / 3.593 chars** |

**Y los chunks descartados llevan el castellano dentro** (verificado token a token). Desglose por línea del chunk 2
(12.453 chars, adjudicado `de`): **`es` 4.122 chars** — *más que el alemán* (3.431) — `en` 2.820, resto menor.

**Por qué el detector se equivoca, con la forma real del dato:** no es un fallo de `lingua`. La tabla concatena las
seis traducciones **dentro de la misma celda**, sin separador:

> `DIP setting O=Off/1=On SW 1,2,3,4,5Paramètre DIP 0=Désactivé/1=Activé SW 1,2,3,4,5DIP-Schaltereinstellung O=Aus/1=Ein SW…Impostazione DIP O…`

El chunk que contiene esa tabla mide 34.740 chars y es, literalmente, seis idiomas trenzados. Pedirle a un detector
un veredicto único sobre eso es preguntar mal: **la unidad de decisión (el chunk) es demasiado gruesa para el dato.**

## 2 · Alcance — MEDIDO: es despreciable, y eso cambia la recomendación

De los **160** documentos que el censo clasificó como descartados por política (`paginas_perdidas_otro_idioma` 157
+ `texto_perdido_otro_idioma` 3), con adjudicación de idioma **por fragmento** (no global) y verificación de que el
fragmento no esté ya indexado:

| métrica | valor |
|---|---|
| documentos con algún castellano en el texto descartado | **13** de 160 |
| chars de castellano perdidos por esta vía, TOTAL | **2.146** (revisando cita a cita: ~1.760 reales en 9 docs; ~390 falsos positivos) |
| documentos que alcanzan el umbral accionable (≥500 chars) | **0** |
| escala de comparación | 3.326 páginas descartadas · menos de **un chunk medio** del corpus |

**Y lo que se pierde es boilerplate, no procedimiento**: direcciones de las delegaciones de Notifier España
(`MNDT040P`, 426 chars), el párrafo de exención de garantía de las hojas Kidde (`2x-a-lb` 344, `2x-lb` 100), una
línea de índice (`MNDT742P`), avisos genéricos («Toda la información contenida en este documento puede ser
modificada sin previo aviso»). El único con contenido semi-técnico es `D 1149-1 BGL Notifier` (361 chars).

Verificado por mí sobre el JSON del censo (regla C): 13 documentos con `chars_es_ausentes > 0`, suma **2.146**,
**0** por encima del umbral; `meta.castellano_intercalado.veredictos = {otro_idioma_puro: 160}`.

**Crédito de método, porque afecta a cuánto fiarse del número**: la primera derivación del agente daba una cifra
falsa (precisión **0/14** en una muestra revisada a mano: colaba portugués e italiano porque «ser/sobre/entre»
sobrevivían como «exclusivas del español»). Lo detectó él mismo, pasó a una regla simétrica con morfología
(`-ción` vs `-ção`/`-zione`/`-tion`), lo validó contra un banco de 28 líneas control (**26/28, los 2 fallos del
lado conservador, cero falsos positivos**) — aunque ese banco vive en prosa, **sin fixture versionado** (Sol r36). El
2.146 lleva ~390 chars de falsos positivos Y omite líneas cortas: el **sesgo neto es DESCONOCIDO** (no es una cota
inferior, como escribí en v2).

⇒ **`D1056-1_NFXI-BS-BSF` es la EXCEPCIÓN, no la punta del iceberg.** El mecanismo `_DROP_LANGUAGES` existe y es
real, pero en el resto del corpus lo que arrastra es despreciable.

Además: **ninguno de los afectados sustenta un gold del FULL** — verificado end-to-end contra `pool_ids`/`topk_ids`/
`served_ids` del 16-ago (la columna `gold` del censo marca `sí` en `2x-a-lb`, pero eso significa pertenencia a
`doc_map`/`pdfs_used`, no que sustente un gold medido: corregido tras Sol r36) ⇒ nada de esto mueve los OKs.

## 3 · Opciones

| # | Opción | Veredicto |
|---|---|---|
| **A** | Partir el chunk multilingüe por idioma antes del filtro | **INVIABLE con este dato, y lo probé**: las traducciones están concatenadas dentro de la misma celda; no hay línea, columna ni separador que partir. Sería reconstruir la tabla desde el markdown de LlamaParse — frágil y caro |
| B | No descartar un chunk si contiene castellano SUSTANCIAL, medido por fragmentos | Diseño correcto y ya escrito (§ siguiente), pero **el alcance no lo paga**: 0 documentos por encima del umbral. Construirlo hoy sería un aparato para 1 caso |
| C | Política por DOCUMENTO en vez de por chunk | Descartada: cambia el comportamiento en muchos más documentos que B para el mismo beneficio nulo, y mete FR/DE íntegro en el índice |
| **D** | **No tocar el pipeline; tratar `D1056-1` como el caso puntual que es** | **RECOMENDADA con la cifra delante.** 2.146 chars de boilerplate en 13 documentos no justifican tocar la política de idiomas de la ingesta |

### Diseño de B (escrito y NO cableado — queda aquí para cuando/si el alcance cambie)
Un predicado nuevo en el módulo de idiomas: `contiene_castellano_sustancial(texto)` → adjudica idioma por
fragmentos (mismo criterio que usó el agente del censo: ~35 palabras, señales gramaticales españolas para no
confundir terminología técnica común) y devuelve cierto si los chars adjudicados a `es` superan un umbral **absoluto**
(p. ej. ≥400 chars) — absoluto y no relativo, porque en una tabla trenzada el castellano nunca será mayoritario.
En `pipeline.process_file`, la línea que hoy es
`kept = [c for c in chunks if c.language not in _DROP_LANGUAGES]`
pasa a conservar además los chunks que, siendo de idioma descartable, contienen castellano sustancial; esos chunks
se marcan (`language="es"` no: **`multilingue=True`** + idioma real) y la decisión queda **declarada en el registro
de estado** (mismo patrón que la guarda #87: nada silencioso).

**Flag**: `LANG_FILTER_KEEP_MULTILINGUAL` (off por defecto) ⇒ el comportamiento actual es el default hasta que
Alberto lo apruebe con la medición delante.

## 4 · Lo que este fix NO hace (y hay que decirlo)

1. **No arregla el corpus ya ingestado.** Es un cambio de INGESTA: los documentos afectados hay que **re-ingestarlos**
   uno a uno (el re-ingestador ya existe y está generalizado: `scripts/s324d_reingesta_ti007.py --doc …`). Coste por
   documento = re-parse de LlamaParse (~45 créditos/página ≈ $0,056/página) + contextualización + embeddings. Con la
   lista del alcance sale la factura exacta; **sin ese paso el fix no cambia nada de lo que hoy ve el técnico**.
2. **No mejora los golds** (ninguno de los afectados sustenta uno) ⇒ el eval no lo verá. La medida correcta de éxito
   es «chars de castellano recuperados en el corpus», no OKs.
3. **Mete ruido multilingüe en el índice**: el chunk conservado lleva las seis traducciones. Hoy eso ya ocurre en los
   chunks mixtos que sobreviven (chunk 1 y 3 del caso), pero con B habrá más. Riesgo real a vigilar: embeddings de
   chunks trenzados de 30k chars son pobres, y el generador podría citar una fila en alemán.
4. **No toca la política de idiomas a nivel de DOCUMENTO** (`register_only` para documentos íntegramente
   extranjeros): esa sigue igual.

## 5 · Por qué es best-practice, estructural y escalable

- **Estructural**: corrige el punto donde se pierde la información (una decisión binaria sobre una unidad que mezcla
  idiomas), no el síntoma (re-ingestar a mano los documentos que alguien detecte).
- **Escalable a 30+ fabricantes**: las fichas multilingües son la norma en este sector (Notifier/Honeywell,
  Kidde/Aritech y Detnov publican hojas EN/FR/DE/IT/ES en el mismo PDF). Cuantos más fabricantes, más casos.
- **Reversible y medible**: flag off por defecto, decisión declarada en el estado de ingesta, y una métrica de éxito
  explícita (chars de castellano recuperados).

## 5-bis · Qué hacer con `D1056-1_NFXI-BS-BSF`, que sí es real

Es 1 documento con el 93 % del contenido tirado (la tabla DIP/tonos con su columna española). Opciones, para Alberto:
1. **Dejarlo declarado** en la deuda y no hacer nada (coste 0; el documento sigue incompleto en el corpus).
2. **Excepción por documento**: re-ingestarlo con el filtro de idioma desactivado SOLO para él (una línea en el
   re-ingestador, sin tocar la política general). Coste ~$0,2. Riesgo: entra la tabla trenzada de 6 idiomas al índice.
3. Construir B igualmente. **No lo recomiendo**: es el aparato para un caso.

~~Mi recomendación: (2)~~ **RETIRADA tras el dúo r36**: la opción (2) NO funcionaría (el filtro de idioma vive
también en `retriever._filter_by_language`, así que serving volvería a descartar el chunk) y además el re-ingestador
le asigna metadata incorrecta a este documento. Queda **(1): declararlo**; si quieres el contenido dentro, es el
proyecto completo del hallazgo C2 (esquema + serving + contrato de generación), con su propia sentada.

## 6 · Qué pido al revisor

(a) ¿La decisión de NO construir se sostiene con 2.146 chars / 13 documentos / 0 por encima del umbral, o hay un sesgo en la medición que la invalide (el propio agente declara que SUBESTIMA)? ¿El umbral absoluto de castellano sustancial sería defendible si se construyera, o hay una forma mejor de decidir sin reconstruir la
tabla? (b) ¿Conservar el chunk trenzado entero hace más daño (ruido en retrieval/embeddings, citas en alemán) que
bien? (c) ¿Debería el fix marcar el chunk como multilingüe para que el generador/renderer lo trate distinto?
(d) ¿Hay algún consumidor que asuma «todo chunk indexado está en un idioma indexable»? (e) Cualquier claim de este
documento que el código o los datos no sostengan.

---

## ADENDA — dúo r36 (17-ago): 5 hallazgos de Sol, TODOS verificados por mí y aplicados

### C1 (crítico) — La cohorte que medía el alcance EXCLUÍA por construcción los positivos conocidos
`scripts/s324d_castellano_intercalado.py` selecciona sólo las clases `*_otro_idioma`, así que `D1056-1` y los otros
dos casos de castellano perdido **no estaban en la muestra**. Decir «D1056 es la excepción» apoyándose en una cohorte
que lo excluye es circular. **Verificado**: las clases excluidas son 8 documentos (`texto_perdido_es` 1,
`paginas_perdidas_es` 2, `sin_url` 3, `escaneado_sin_texto` 1, `fuente_ilegible` 1).

**Reformulación honesta de lo que SÍ está medido:** de los **164** documentos del corpus con texto nativo ausente,
**160** se midieron (los `*_otro_idioma`) y su castellano es boilerplate (2.146 chars, 0 sobre el umbral); los **4**
restantes ya estaban identificados como pérdida española o no son medibles. Los 842 «sano» no tienen texto ausente.

**Y el límite que Sol destapa y yo no había declarado:** esto **no es la atribución end-to-end del mecanismo**. El
censo compara *texto nativo del PDF* contra el corpus; un chunk descartado por el filtro de idioma cuyo contenido
venga del OCR de una imagen (no de la capa de texto) **no aparecería como ausente**. La atribución correcta exigiría
correr `chunk_document` + `detect_language` sobre **todo** el store de extracción — que no está en esta máquina.
⇒ El alcance real del mecanismo **no está medido**; lo medido es una aproximación por texto nativo. Declarado.

### C2 (crítico) — B y «la excepción para D1056» NO funcionan end-to-end: el filtro de idioma está TAMBIÉN en serving
`src/rag/retriever.py:2438` — `_filter_by_language` con `_SERVED_LANGUAGES = {"es","en"}` **descarta en retrieval**
todo chunk cuyo `language` sea fr/de/pt/it (fail-open sólo si no queda nada). **Verificado.** Por tanto conservar el
chunk en la ingesta con `language="de"` no sirve de nada: retrieval lo vuelve a tirar en cuanto haya resultados ES/EN.
Y el `multilingue=True` que yo proponía **no existe**: no está en el modelo de chunk (`reingest/chunk.py:132` sólo
tiene `language`), ni en la fila que se indexa (`reingest/index.py:51`), ni en el esquema
(`migrations/006_chunks_v2.sql`).

⇒ **Mi diseño B estaba incompleto** y mi «opción 2» para `D1056` (re-ingestar con el filtro desactivado sólo para él)
**no habría arreglado nada**. Un fix real exige: campo nuevo en el esquema + persistirlo + contrato de serving
(¿qué hace el retriever con un chunk multilingüe? ¿y el generador, que podría citar una fila en alemán?). Eso es un
proyecto, no una línea — y **refuerza la recomendación D**.

### M3 — El re-ingestador «generalizado» no vale como excepción por documento
Para `D1056` produce `manufacturer=null`, `product_model="EN-54-3"` (una norma, no un modelo) y `language="de"`
(recibo `evals/s324d_reingesta_ti007_dry-run_20260817T095442Z.json`). Convertirlo en «excepción de una línea» habría
reindexado metadata incorrecta: es el quick-fix por documento que el contrato del proyecto prohíbe. **Retiro esa
opción.**

### M4 — «el 2.146 subestima» no está demostrado
La cifra incluye ~390 chars de falsos positivos Y omite líneas cortas no adjudicadas: el sesgo **neto es
desconocido**, no una cota inferior. Además el banco de 28 líneas control (26/28) vive en prosa/docstring, sin
fixture versionado que lo sostenga. Corregido en §2: la cifra es una **estimación con sesgo de signo desconocido**.

### M5 — La evidencia que yo citaba sobre los golds era incorrecta (la conclusión, no)
Yo escribí «ninguno de los afectados sustenta un gold» mientras mi propia fuente (`censo…v1.md:128`) marca
`00-3301-501-4000-04_r004_2x-a-lb` con `gold=sí`. **Verificado end-to-end**: ese documento **no aparece** en
`pool_ids`/`topk_ids`/`served_ids` de ningún gold del FULL 16-ago ⇒ la conclusión operativa se sostiene, pero la
columna `gold` del censo significa otra cosa (pertenencia a `doc_map`/`pdfs_used`), no «sustenta un gold medido».
Frase corregida y evidencia cambiada por la verificación real.

## Recomendación final tras el dúo (sin cambios en el veredicto, con mejores razones)

**D — no tocar el pipeline.** Ahora con tres apoyos y no uno:
1. lo medible del alcance es boilerplate (§2), con el límite de atribución declarado (C1);
2. el fix **no es un fix de ingesta**: exige esquema + serving + contrato de generación (C2) ⇒ el coste real es un
   orden de magnitud mayor que el que yo había estimado;
3. no toca ningún gold ⇒ no hay retorno medible en el eval.

**`D1056-1_NFXI-BS-BSF`** queda **declarado como caso conocido** en TECH_DEBT #90 (93 % del documento fuera del
corpus, con su tabla DIP española). Ya no propongo la excepción por documento: el dúo demostró que no funcionaría.
Si Alberto quiere ese contenido dentro, el camino honesto es el proyecto completo de C2 — con su propia sentada.
