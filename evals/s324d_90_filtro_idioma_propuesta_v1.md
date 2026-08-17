# s324d — TECH_DEBT #90: el filtro de idioma POR CHUNK tira castellano en documentos multilingües. Diagnóstico, alcance y fix propuesto

**Estado: NADA cableado. v2 con el ALCANCE MEDIDO — la recomendación cambió de «construir B» a «NO tocar el pipeline (D)».** Propuesta para el dúo (zona de dolor: corpus/idiomas) y para el sí de Alberto.
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
lado conservador, cero falsos positivos**) y declaró que el 2.146 **subestima** (líneas cortas no adjudicadas).

⇒ **`D1056-1_NFXI-BS-BSF` es la EXCEPCIÓN, no la punta del iceberg.** El mecanismo `_DROP_LANGUAGES` existe y es
real, pero en el resto del corpus lo que arrastra es despreciable.

Además: **ninguno de los afectados sustenta un gold** ⇒ nada de esto mueve los OKs.

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

Mi recomendación: **(2)**, porque el contenido perdido es una tabla de configuración DIP —eso sí es procedimiento— y
el coste es trivial; pero es tu decisión porque mete un chunk multilingüe grande en el índice.

## 6 · Qué pido al revisor

(a) ¿La decisión de NO construir se sostiene con 2.146 chars / 13 documentos / 0 por encima del umbral, o hay un sesgo en la medición que la invalide (el propio agente declara que SUBESTIMA)? ¿El umbral absoluto de castellano sustancial sería defendible si se construyera, o hay una forma mejor de decidir sin reconstruir la
tabla? (b) ¿Conservar el chunk trenzado entero hace más daño (ruido en retrieval/embeddings, citas en alemán) que
bien? (c) ¿Debería el fix marcar el chunk como multilingüe para que el generador/renderer lo trate distinto?
(d) ¿Hay algún consumidor que asuma «todo chunk indexado está en un idioma indexable»? (e) Cualquier claim de este
documento que el código o los datos no sostengan.
