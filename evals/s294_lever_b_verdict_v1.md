# s294 · Lever B (`cat017#2`, referencia gobernada) — **NO-GO por POBLACIÓN**, no por mecanismo

**Nada cableado.** El mecanismo es correcto y su retorno está probado (alcanzabilidad
0/5 → 5/5, DEC-173). Lo que lo tumba es el censo que DEC-173 obliga a hacer ANTES de diseñar.

## Censo en el eval (replay $0 de la etapa de coverage, fidelidad **39/39**)

El brazo baseline reproduce los `appended_ids` del recibo **en los 39 golds** —no en uno—,
así que el instrumento está verificado antes de leer su resultado.

| medida | valor |
|---|---|
| golds donde dispara la conduct `facet_complement` | **2 / 39** |
| golds con el patrón «la necesidad se satisface con un PUNTERO» | **1** (`cat017`) |

## Censo en el corpus (muestra determinista de 3.000 chunks)

Clasificando las remisiones halladas (verbo «consulte/véase/see/refer to»):

| clase | n | lectura |
|---|---|---|
| sin código ni sección | 343 | remisión vaga |
| **remisión INTERNA** (sección/figura/página) | 329 | no cruza documento: nada que navegar |
| **código SIN casar** | 28 | citan documentos **que no tenemos** |
| **código casado** | **4** | la superficie real del lever B |

⇒ **≈0,13% de los chunks.** **Retiro explícitamente el argumento estructural que yo mismo di**
al recomendar este lever («los manuales se citan entre sí, luego escala a 30+ fabricantes»):
el corpus dice que **casi todas las remisiones son internas**, y cuando citan un documento
externo, la mitad no está ingestado. La forma que el lever navega es rara.

**Veredicto:** construirlo sería un arreglo de **1 hecho** tocando la satisfacción de
necesidades de `document_local_content_coverage_v1`, **viva en la release C1** — la clase
«radio a serving» que ya tumbó L3 v1. **NO-GO.** El mecanismo queda documentado por si el
patrón crece con corpus o consultas reales.

---

# Subproducto con valor propio: lista de adquisición DIRIGIDA POR CITAS

Al clasificar las remisiones apareció algo más útil que el lever: **nuestros manuales piden
documentos que no tenemos**. Cada cita es una petición explícita del fabricante, así que
ordenarlas da una lista de compra basada en evidencia, no en intuición — insumo directo para
el objetivo de 30+ fabricantes y para el Excel de inventario.

Barrido **corpus completo** (25.088 chunks, `scripts/s294_citation_gap.py`, recibo
`evals/s294_citation_gap_v1.json`): **44 documentos citados y ausentes · 77 citas.**

| citas | código | citado por | ejemplo |
|---|---|---|---|
| 11 | `997-340-003` | MFDT212 · MIDT212 | «consulte el **Manual de Programación de la Serie ID1000, 997-340-003**» |
| 6 | `997-415` | MIDT155 · MIDT156 | «consulte las **Instrucciones de actualización — Panel de un solo lazo, ref.: 997-415**» |
| 5 | `997-263` | MFDT155 · MIDT155 | «**Manual de Instalación, puesta en marcha y programación del panel ID50, ref.: 997-263**» |
| 3 | `997-264` | MIDT155 | «véase el **manual de funcionamiento, ref.: 997-264**» |
| 3 | `997-320-003` | MADT212 | «**Manual de Programación de la Serie 1000 (997-320-003/013)**» |

Casi todo **Notifier/Morley**, y concentrado en las series ID50/ID1000/1000 — familias de las
que tenemos el manual de instalación pero **no el de programación**, que es justo donde vive
el detalle que un técnico pregunta.

## Cómo se llegó a una cifra fiable (dos correcciones propias, ambas antes de publicar)

1. **Guiones**: el corpus escribe `MIDT155` donde el manual cita `MI-DT-155`. Sin normalizar,
   **160 documentos PRESENTES salían como ausentes** (42% de la lista era falsa).
2. **Ruido de pie de página**: el código del propio manual aparecía en la ventana cuando el
   verbo remitía a una sección o figura («Véase la Sección 4.1.4 … PK-ID3000»). Se exige ahora
   una palabra de documento (`manual`/`guía`/`ref.`/`instrucciones`…) **entre** el verbo y el
   código, y ≤100 chars de distancia: la lista pasó de 93 a **44**.

**Residual declarado**: quedan códigos-comodín (`997-670-00X`, que corresponde al manual Pearl
que SÍ tenemos como `997-670-005-3`). La lista es de **candidatos para adjudicación humana**,
con la cita literal incluida en el recibo para poder juzgarla sin abrir el manual.
