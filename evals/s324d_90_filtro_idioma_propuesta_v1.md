# s324d — TECH_DEBT #90: el filtro de idioma POR CHUNK tira castellano en documentos multilingües. Diagnóstico, alcance y fix propuesto

**Estado: NADA cableado. Propuesta para el dúo (zona de dolor: corpus/idiomas) y para el sí de Alberto.**
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

## 2 · Alcance

Medición en curso (agente, $0): de los **157** documentos que el censo clasificó `paginas_perdidas_otro_idioma`
(+3 `texto_perdido_otro_idioma`), cuántos llevan castellano intercalado y cuántos chars son. **Sin esa cifra, este
documento NO recomienda cablear nada** — con 3 documentos afectados la respuesta correcta es tratarlos a mano; con
50+ es un fix de pipeline. *(Esta sección se completa antes de pasar al dúo.)*

Lo que ya se sabe con certeza: **ninguno de los documentos accionables detectados hasta ahora sustenta un gold**
⇒ este fix **no moverá el número de OKs**. Su valor es el corpus que ven los técnicos reales, que es el producto.

## 3 · Opciones

| # | Opción | Veredicto |
|---|---|---|
| **A** | Partir el chunk multilingüe por idioma antes del filtro | **INVIABLE con este dato, y lo probé**: las traducciones están concatenadas dentro de la misma celda; no hay línea, columna ni separador que partir. Sería reconstruir la tabla desde el markdown de LlamaParse — frágil y caro |
| **B** | **No descartar un chunk si contiene castellano SUSTANCIAL**, medido por fragmentos (no por el veredicto global del chunk) | **RECOMENDADA**. Ataca la causa (unidad de decisión demasiado gruesa) sin tocar el chunker ni la extracción; inerte en documentos monolingües (la inmensa mayoría); reversible con flag |
| C | Política por DOCUMENTO en vez de por chunk (si el doc tiene páginas ES, no filtrar sus chunks) | Más simple, pero mete contenido íntegramente FR/DE de documentos mixtos; cambia el comportamiento en muchos más documentos que B |
| D | No tocar nada | Válida si el alcance resulta despreciable — se decide con la cifra de §2 |

### Diseño de B
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

## 6 · Qué pido al revisor

(a) ¿El umbral absoluto de castellano sustancial es defendible, o hay una forma mejor de decidir sin reconstruir la
tabla? (b) ¿Conservar el chunk trenzado entero hace más daño (ruido en retrieval/embeddings, citas en alemán) que
bien? (c) ¿Debería el fix marcar el chunk como multilingüe para que el generador/renderer lo trate distinto?
(d) ¿Hay algún consumidor que asuma «todo chunk indexado está en un idioma indexable»? (e) Cualquier claim de este
documento que el código o los datos no sostengan.
