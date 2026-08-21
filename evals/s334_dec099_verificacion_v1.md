# s334 · Verificación DEC-099 en producción (21-ago 14:16-14:18Z) — NÚCLEO VERIFICADO ✅ + 2 observaciones

> Deploy `c9558bc` (merge #331), flags `F1_CORRECCION_FUZZY=on` + `F1_ESTADO_ATAJOS=on`
> puestas por Alberto. 5 filas leídas (DEC-092b).

## El núcleo — la clase de las 13:27, muerta

| id | turno | conducta |
|---|---|---|
| `7567314c` | «¿Qué centrales **CAFÉ** tienes?» (6ª corrupción de Kidde del día; sin fila, d≫1, sin cue) | Respuesta DIGNA: «No tengo ninguna central "CAFÉ"… ¿me confirmas fabricante y modelo de la etiqueta?» — no la plantilla vacía |
| `efad3e27` | «Quería decir KIDE» | **TABLA reescribe (kide→Kidde) → PLANTILLA casa → rebuild** → «Centrales Kidde: Serie NC, NC-PF2…». Trace: `marca_asr`+`marca_corregida` estampadas; `corr=not_invoked` (capa barata ganó — orden diseñado) |

## Observaciones nuevas (disciplina: se documentan, no se construyen sin GO)

1. **`2a1e1694`** «Sí, a eso me refiero.» → clarify pidiendo modelo. **PRIMERA observación del
   «sí» pelado tras respuesta** — la clase `pending_aviso` diseñada en s333 §1.E y DIFERIDA
   «hasta observarla»: umbral cumplido, candidata a build (GO pendiente).
2. **`fabef50b`/`9e8f650c`** «(Y ahora) quiero ver las (centrales) de Morley» → clasificador
   `nuevo` (1.2-1.4 s; en T5 CORRECTO según la frontera del owner — se sostiene sola) y AUN ASÍ
   plantilla vacía: **el fallo es aguas abajo** — el atajo de inventario no reconoce el fraseo
   «quiero ver las centrales de X» y el RAG no sirve peticiones de inventario. Clase NUEVA
   (cobertura de fraseos del atajo, plan-level), GO pendiente. T4 («las de Morley», anafórico)
   deja además una etiqueta límite para Alberto (¿corrección?).

## Estado

DEC-269 **VERIFICADA en su diana** (marca-corrupta-en-corrección + capas en orden). R8 activa
(estado fresco tras atajos — sin atajo en esta conversación, medida en GA1b). Las 2
observaciones entran a la cola de GO.
