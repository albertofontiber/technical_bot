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
