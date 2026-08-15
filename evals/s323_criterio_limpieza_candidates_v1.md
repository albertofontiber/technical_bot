# s323 — CRITERIO de la limpieza autónoma de candidates (sometido al dúo ANTES de aplicar)

**Mandato de Alberto (15-ago)**: «adelante con la fluida» — hago la pasada completa sobre
los ~753 productos *candidate* y **aplico yo** las clases con prueba, parándome solo en la
clase disputable. Objetivo declarado por él: **rebajar su dependencia**, no acelerar por
acelerar. Este documento es el CONTRATO de qué se aplica sin preguntar y qué no; el dúo lo
revisa ANTES de que se escriba una sola fila.

## Qué está en juego (y por qué no es cosmético)
`candidate: true` significa NO-CONSUMIBLE: `catalog_store` excluye esas entradas de la
resolución (`estado == "activo" and not candidate`). Por tanto:
- **Confirmar** un candidate = quitarle la marca = **el bot empieza a resolver ese nombre**.
  Es un cambio de conducta servida, no una anotación.
- **Retirar** = `estado: retirado` = desaparece del catálogo gobernado.
Ambas son reversibles (JSONL versionado en git + recibo por escritura), pero la primera
cambia lo que un técnico recibe y la segunda borra un hecho sobre un producto real si nos
equivocamos.

## Asimetría que gobierna todo el criterio
**Confirmar de más es barato; retirar de más es caro.** Un producto raro resoluble molesta
poco; borrar un equipo que existe rompe una respuesta futura y no deja rastro para el
técnico. Por eso las dos puertas NO son simétricas: la de retirada exige prueba positiva del
artefacto, no ausencia de prueba del producto.

## PUERTA A — RETIRADA automática (artefacto de extracción)
Se aplica SOLO si se cumplen TODAS:
1. **Prueba mecánica de origen**: se exhibe el fragmento VERBATIM del corpus del que el
   extractor derivó el término, y ese fragmento demuestra que es otra cosa: una cota
   («82 mm» → `MM-82`), una distancia («hasta 3200 m» → `TO-3200M`), un voltaje, una norma
   (`EN-54-25`), un número de certificación (`0786-CPD-…`) o una frase corrida
   («local 360° indication» → `LOCAL-360`).
2. **Cero apariciones como SUJETO** en todo el corpus: no aparece en título, encabezado,
   fila de tabla de modelos, referencia comercial ni campo «Ref./Mod./Art.».
3. **La búsqueda online NO lo encuentra** como producto del fabricante (o lo que encuentra
   es precisamente la norma/medida). Evidencia con URL + cita + fecha en el recibo.
Si falla cualquiera de las tres → **NO se retira**: va al packet de Alberto.

## PUERTA B — CONFIRMACIÓN automática (sale de cuarentena)
Se aplica SOLO si se cumplen TODAS:
1. Aparece como **SUJETO** en ≥1 manual que TENEMOS, con **cita verbatim verificada a texto
   completo** contra el documento entero (espacios normalizados) — el estándar r28.
2. **Sin colisión de homónimo**: su normkey no resuelve también a un producto de otra marca
   (el catálogo ya tiene el caso B501/B501AP; una colisión manda la fila al packet).
3. No es norma ni número de certificación.
Si falla cualquiera → **no se confirma**: al packet.

## PUERTA C — PARADA OBLIGATORIA (nunca aplico, siempre packet)
- **Producto real sin manual nuestro**: por la regla de Alberto es **hueco de corpus**, no
  basura. Va al packet Y a la cola de gaps.
- **Homónimos entre marcas**.
- **Cualquier retirada de algo con señal de ser producto real**, aunque sea débil.
- Cualquier fila no decidible con evidencia.
- **Términos del léxico peligroso** (cortos, palabra común): tocan al detector, y ahí el
  precedente `FUEGO` manda — jamás automático.

## Orden de la evidencia (aprendido esta semana)
**Corpus primero, internet después.** Dos veces hoy el «hace falta buscar fuera» resultó
falso: era muestreo pobre (#76: 22 filas «no decidibles» → 0 tras muestrear la tabla de
modelos; E3: 32 → 4). Internet solo entra para el residuo irreducible, y **jamás escribe
sola**: sirve para descartar retiradas (probar que el producto existe) o para declarar hueco
de corpus. **Ninguna confirmación se apoya solo en internet** — sin manual nuestro, no hay
confirmación, hay hueco.

## Trazabilidad y reversibilidad
- Toda escritura por `catalog_store.write_jsonl` (valida el conjunto entero) con recibo:
  id, veredicto, puerta aplicada, cita/prueba, y valor previo.
- Un solo commit por lote, revertible.
- Verificación adversarial POSTERIOR sobre lo aplicado: re-ejecutar las citas desde cero
  (censo, no muestra) y comprobar que ninguna fila aplicada incumple su puerta.

## Alternativas descartadas
- **Aplicar también las retiradas «probables»** (sin prueba mecánica): es la asimetría al
  revés; borraría productos reales por ausencia de evidencia.
- **Confirmar todo lo que tenga menciones**: una mención no es ser sujeto (`B501` aparece 134
  veces y muchas son dentro de `B501AP`).
- **Pedirle a Alberto que firme las 665**: es exactamente el cuello de botella que manda
  quitar, y hoy su firma ha sido «sí» en la práctica totalidad de lo que tenía prueba.

## Gaps declarados
- Confirmar ~600 productos ensancha la resolución: el riesgo real no es el producto raro,
  es un **falso positivo de resolución** por homónimo o por término corto. La puerta B lo
  ataja con la comprobación de colisión, pero no puedo probar que no exista un homónimo
  que el catálogo aún no conoce.
- La evidencia online envejece: una ficha de distribuidor puede desaparecer. Por eso se
  guarda URL + cita + fecha, y jamás se usa como única base de una confirmación.
- El criterio no cubre qué hacer si un candidate resulta ser **variante** de otro producto ya
  en catálogo (relación, no alta): esa clase va al packet.

---

# ADENDA post-dúo r30 (Sol xhigh: 6 hallazgos, 2 CRÍTICOS) — EL CRITERIO SE REHACE

**El diseño de arriba NO se aplica.** Sol tumbó su premisa central y lo he verificado
contra el código, línea por línea:

## Crítico 1 (CONFIRMADO) — «confirmar de más es barato» es FALSO a esta escala
Quitar `candidate` no activa solo el modelo canónico. Verificado:
- `catalog_store.py:112-113` — `_by_alias` indexa los alias cuyo DESTINO es consumible:
  confirmar un producto activa también **todos sus alias ya existentes**.
- `catalog_store.py:192-193` — los miembros de paraguas se filtran por `_consumable`:
  confirmar cambia además **la expansión de los paraguas**.
- `catalog_resolver.py:142-153` — el **detector generado** añade el canónico Y los alias
  (los model-shaped). O sea: confirmar ~600 productos **inyecta cientos de términos nuevos
  en el detector**, que es exactamente la clase `FUEGO`… multiplicada por 600 y sin medir.

Mi Puerta B no censaba nada de eso ni medía delta. **Ese era el fallo de diseño**, y es el
mismo que te describí como «barato» cuando pediste la vía fluida: **la premisa con la que
autorizaste era incorrecta**.

## Crítico 2 (CONFIRMADO conceptualmente) — ser SUJETO no valida la FILA
Que un manual hable de un producto prueba que existe, no que su fila tenga bien el
namespace de marca, `vendido_bajo`, el relabeling OEM ni la granularidad comercial
(¿es producto, variante o accesorio de otro?). La Puerta B promovía esos campos sin
verificarlos, y «variante → packet» no tenía predicado que detectara variantes.

## Correcciones menores aceptadas
- **Mi framing de la retirada era falso** (Sol, menor): `estado: retirado` NO borra nada —
  la fila y su id siguen versionados y cargados, solo dejan de indexarse como consumibles.
  El contrato de identidad además prohíbe borrar o reciclar ids. La retirada es **más
  conservadora** de lo que yo la pinté.
- Puerta A no puede probar ausencia con grep (scans, páginas-imagen, OCR): el canon de
  RULER_DESIGN lo dice explícitamente. Hay que acotar la afirmación a «ausencia en el
  texto extraído», no «ausencia».
- Falta MÉTRICA y umbral (Protocolo 2): objetivo sin métrica no es un objetivo.
- El recibo debe fijar la evidencia de forma reproducible: `document_id`, página, revisión
  del documento y hash del catálogo — si no, la verificación posterior no puede probar qué
  evidencia gobernó la escritura.

## DISEÑO CORREGIDO (para el dúo siguiente, antes de aplicar nada)
1. **Retiradas con prueba mecánica**: SIGUEN siendo aplicables — son conservadoras,
   reversibles y no borran la fila. Con la afirmación acotada («no aparece como sujeto en
   el texto extraído») y prueba verbatim del origen del artefacto.
2. **Confirmaciones: YA NO en bloque.** Pasan a un proceso MEDIDO por lotes:
   (a) censo del radio de explosión POR FILA — qué alias, qué pertenencias a paraguas y
   qué términos de detector se activarían; (b) exclusión automática de toda fila cuya
   activación añada un término de riesgo léxico (corto, palabra común, colisión); (c) gate
   MEDIDO por lote: delta del detector + negativos de resolución end-to-end antes/después,
   con la maquinaria de eval que ya existe; (d) solo el lote que pasa el gate se aplica.
3. **Validación de la FILA, no solo del producto**: antes de promover, comprobar namespace
   de marca, `vendido_bajo` y si el término es en realidad variante/accesorio de otro
   producto ya catalogado (predicado explícito, no buena voluntad).
4. **Métrica declarada**: reducción objetivo del packet, tasa de error admisible y gate de
   regresión servida — con números, no con adjetivos.

---

## RESULTADO DEL PRIMER INTENTO DE PUERTA A (s323, mismo día): LA PUERTA NO SIRVE

Ejecutada sobre las 18 filas con veredicto RETIRAR: solo 3 pasaron la prueba mecánica,
y **las 3 son falsos positivos** — es decir, la puerta habría retirado productos reales:
- `VSN 2Plus` — es un producto REAL (existe además en el catálogo como `notifier:vsn-2plus`).
- `PL4-E` — el «fragmento probatorio» era «central diseñada para gestionar 4 zonas…»: eso
  no prueba artefacto, describe una central.
- `34110400` — referencia numérica junto a una placa RS485; podría ser una referencia real.

**Causa raíz del fallo**: mi predicado de artefacto era «aparece una medida/norma a ±90
caracteres», y en un manual técnico eso ocurre CASI SIEMPRE. No probaba nada; solo
correlacionaba. El predicado correcto es mucho más estricto: **los caracteres del término
tienen que ser RECONSTRUIBLES desde el texto vecino** (`82 mm` → `MM-82`; `hasta 3200 m` →
`TO-3200M`; `local 360°` → `LOCAL-360`), no que haya un número cerca.

**NADA SE APLICÓ.** La puerta se cazó a sí misma antes de escribir, que es exactamente para
lo que existe — pero significa que las retiradas TAMPOCO están listas para automatizarse
hasta rehacer el predicado y validarlo contra los artefactos ya confirmados (`MM-82`,
`TO-3200M`, `OF-48V`, `LOCAL-360`, `EN-54-25`) como conjunto de control positivo, más los
productos reales de arriba como control NEGATIVO.
