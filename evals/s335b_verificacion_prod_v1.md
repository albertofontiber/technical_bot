# s335b · Verificación en producción post-merge #333 (21-ago 15:53-15:54Z) + fila «quide»

> Deploy verificado: `bot_version f7c514d` = merge de #333 en las 4 filas — el código
> s335 servía desde la primera. Flags de prod: `correccion.status=invoked` ⇒
> F1_MARCA_CORRECCION+F1_CORRECCION_LLM on; `asunciones.status=on` ⇒ ASR_AVISOS on.
> La conversación real fue OTRA que la del guion — y eso es información.

## Las 4 filas (voz)

| id | query (transcripción) | ruta | resultado |
|---|---|---|---|
| `a9ba756a` | «¿Qué centrales de Notifier tienes?» | catalog_shortcut | 📦 listado, pero «ninguno de los 3 clasificados casa con central» (448 sin clasificar) |
| `0d660f7f` | «¿Y de Morley?» | rag | clasificador `nuevo` (1741 ms) → «No he encontrado…» |
| `4c868ab7` | «¿Ahora las de quiere?» (dijo: Kidde) | rag | clasificador `not_invoked` (sin marca gobernada) → «No he encontrado…» |
| `f8dcb59a` | «Quería decir quide.» (dijo: Kidde) | rag | clasificador `not_invoked` → «No he encontrado…» |

## Lo VERIFICADO en verde

1. **R8 en producción**: T1 (atajo) escribió el estado — prueba: en T2 el clasificador
   corrió con `last_query` viva 29 s después de un turno de ATAJO (sin R8 no habría
   last_query fresca; no hay filas previas en la ventana).
2. **Población del clasificador correcta**: invoked solo con marca gobernada (T2);
   not_invoked en T3/T4 («quiere»/«quide» no son marcas) — cero invocaciones basura.
3. **Trazas nuevas estampando**: secciones `correccion` (decision+latencia) y
   `asunciones` en `rag_trace` de prod.
4. **Guardas honestas**: el fuzzy NO disparó sobre «quide» (d(quide,kidde)=3 > 1, por
   diseño acotado) — cero falsos positivos.

## Lo que NO pagó (3 hallazgos)

1. **T2 «¿Y de Morley?» → `nuevo` → miss.** Frontera NO cubierta por la cohorte v3:
   la elipsis pura «¿Y de {marca}?» está ENTRE N14 («¿y de Aguilera qué tienes?» =
   re-pregunta completa → `nuevo` ✓ 3/3) y p15 («las de Morley» → `correccion` ✓ 3/3).
   Por el criterio del owner («¿se sostiene solo?») la lectura natural es CORRECCION
   (no es respondible sin la pregunta anterior) — pero es un LÍMITE y lo adjudica
   Alberto (precedente hp011#2). Si corrección ⇒ prompt v4 + cohorte v4 re-congelada
   ENTERA con fila obligatoria nueva (DEC-126). NO se cambia nada sin su etiqueta.
2. **7ª y 8ª corrupciones Whisper de «Kidde» en un día: «quiere» y «quide».**
   - **«quide» TABULADA en este commit** (vía pre-autorizada DEC-233: observada con
     cita `f8dcb59a`; verificado 0 hits en corpus, sin alias/marca/término). Cadena
     entera re-verificada en local: tabla→«Quería decir Kidde.»→
     `brand_correction_rebuild`→pregunta base reconstruida — la ruta que en prod ya
     sirvió Serie NC con KIDE (14:17Z).
   - **«quiere» JAMÁS tabulable**: palabra española real con **145 apariciones en
     chunks_v2** — reescribirla corrompería texto legítimo. Test la PINNA fuera de la
     tabla. Hueco DECLARADO: «¿Ahora las de quiere?» es irrecuperable con las capas
     actuales (sin cue de corrección, sin marca, d>1) — si la clase recurre, el
     movimiento estructural sería fuzzy d1 contra PATRONES tabulados (quide↔kide=d1),
     que requiere su propio dúo; hoy NO se construye.
3. **T1 es dato, no routing**: el atajo disparó bien; el catálogo de Notifier tiene
   3 clasificados / 448 sin clasificar → listado pobre con honestidad declarada. Es el
   backlog de clasificación (hilo del packet, PR #332 — sesión paralela).

## Lo PENDIENTE de verificar (el flip nuevo)

**Ninguna fila ejercitó la gramática nueva**: T1 era la forma interrogativa que ya
funcionaba antes. `INVENTARIO_FRASEOS=on` sigue SIN verificación en producción —
falta decir por voz una desiderativa, p. ej. **«Quiero ver las centrales de Kidde.»**
(mejor Kidde/Morley que Notifier, cuyo catálogo clasificado está fino), y la anafórica
del guion («Y ahora quiero ver las de Morley.») para ver la fila p15 en prod.

---

## ADENDA (17:00-17:02Z, deploy `a5b612c` = merge #334) — la gramática nueva y la anafórica, VERIFICADAS en producción

Dos filas de voz cierran lo que quedaba pendiente:

**T1 `48337b59` — la DESIDERATIVA (pieza A), en verde.** Whisper volvió a corromper:
transcripción cruda «Quiero ver las centrales de **Kide**.» → la TABLA reescribió a
Kidde (fila s334) → la gramática v2 con el punto final matcheó → `catalog_shortcut` →
**«📦 Kidde — central (36 de 158 productos): 2X-AE1, 2X-AE2, …»** — listado GOBERNADO
con filtro de categoría, 0 ms, $0. Tres capas en un turno (tabla → gramática → atajo).
`INVENTARIO_FRASEOS` queda VERIFICADO en producción.

**T2 `59ef06d2` — la ANAFÓRICA (pieza B), end-to-end en verde.** «Ahora enséñame las
de Detnov.» — sin sustantivo de inventario, marca nueva. R8 había escrito el estado
desde el ATAJO de T1 (sin R8 no habría last_query); el clasificador con prompt v3 dio
**`correccion` en 1238 ms**; rebuild «Quiero ver las centrales de Kidde.»→Detnov; el
RAG sirvió **«Centrales Detnov disponibles… Serie VESTA CAD-171 (analógica)…»** con
citas (53,6 s el turno entero; el clasificador es 1,2 s de eso). Asunción
`marca_corregida` estampada en la traza (n=1). GENERALIZACIÓN real: marca y verbo
DISTINTOS de la fila obligatoria del gate (Morley/«quiero ver» → Detnov/«enséñame»).
La frontera A/B aguantó en vivo: «las de Detnov» (sin sustantivo) fue al clasificador;
con «centrales» habría ido al atajo.

**Hueco de observabilidad detectado (menor, declarado):** la columna `response` de
`query_logs` trunca a 4096 chars; la respuesta de T2 la supera y el sufijo ℹ️ (que se
aplica ANTES del log, tras las referencias) queda fuera del texto persistido — NO
verificable desde el log; la traza sí estampa la asunción. **RESUELTO en s335c**: Alberto confirmó
visualmente la línea ℹ️ al final (19:02, con scroll) y adjudicó moverla a
CABECERA — el control va ANTES del contenido. Cambiado (`_con_prefijo_asunciones`),
manteniendo la aplicación DESPUÉS de las escrituras de estado (el orden protege
`last_answer_excerpt`/`last_response`; test de fuente lo pinna). Bonus: en cabecera
la nota entra en los primeros 4096 del log y este hueco se cierra.

Con esto, el ship s335 queda **verificado ENTERO en producción**. Siguen pendientes de
Alberto: etiqueta del límite «¿Y de {marca}?» (v4 si corrección) · GO lote
clasificación Notifier (429/3) · pieza C.
