# s331 — Sondas de alcance MEDIDAS (encargo de Alberto: «mídelo»)

**Qué es.** Las dos decisiones de alcance que quedaron abiertas al revisar MNDT600 y MNDT701,
medidas con el gate real (`scripts/s324_lote_firmado_writer.py --plan <sonda>`: censo del radio de
explosión, 51 gold, negativos sintéticos, 111 consultas reales del `query_logs`).
**NADA APLICADO** — los 5 planes son sondas (`evals/s331_sonda_{A..E}_plan_v1.json`), generados por
`scripts/s331_sondas_alcance.py` con cita verificada full-text (token exacto con fronteras) en cada
alta. Recibos: `evals/s331_sonda_{A..E}_v1_radio_explosion.json`.

---

## 1. MNDT600 — ¿a qué se engancha el documento de calibración de detectores de gas?

| variante | alcance | productos | términos al detector | gold perdidas | disparos (sintéticos / 111 reales) | veredicto |
|---|---|---|---|---|---|---|
| **A** | SMART ya CONFIRMADOS | 3 | **+0** | 0 | 0 / 0 | PASS |
| **B** | familia SMART completa (promueve 8 candidates) | 11 | +19 | 0 | 0 / 0 | PASS |
| **C** | gama de DETECTORES de gas de la casa (SMART + SENTOX/LISA/VGS/S264/S317/S613) | 22 | +25 | 0 | 0 / 0 | PASS |

**Lo que el número de términos esconde (esto es lo que decide):** B y C pasan el gate, pero de los
+19 de B, **12 son alias descriptivos** que son basura de extracción y entrarían al detector:

> «SMART 3 con pantalla» · «SMART3G con pantalla» · «SMART 4 (COPTIR) Multi-sensor» ·
> «SMART4 (abreviado a SMT4)» · «Twin version Smart 2» · «serie 3G» · «SMART3C» · «SMART 3 CC-DC» ·
> «MTX2081»…

C añade cuatro más de la misma clase («LISA 2 (IN EEX-D)», «LISA 2 (EEx d)», «LISA 2 (EEx nA)»…).
Es exactamente el patrón que el gate cazó en s324c con Detnov (14 alias descriptivos retirados
ANTES de aplicar). Uno merece atención propia: **«serie 3G»** — el corpus tiene documentos UCIP-GPRS
donde «3G» es la red móvil, no el detector.

**Recomendación: A ahora, B/C con la sentada E1b.** A es gratis (0 términos, 0 riesgo) y engancha el
documento a los tres SMART que ya están confirmados. Los 8 candidates de B están **precisamente en
los bloques de E1b que esperan tu sí**: promoverlos aquí sería colar por la puerta de atrás una
decisión que ya tiene su sitio, y encima obligaría a la pasada de limpieza de alias en el momento
equivocado. Si prefieres B o C igualmente, la limpieza de alias es trabajo mío, no tuyo.

## 2. MNDT701 — la serie 20/20 SharpEye, que NO está en el catálogo

El censo destapó que el hueco no es la fila: **hay 8 documentos activos de la serie 20/20 y ni un
solo producto de esa serie en el catálogo** (la hermana 40/40 sí está, la firmaste en s324b). Con
cita de portada verificada:

| modelo | tipo | manual | chunks con el token |
|---|---|---|---|
| **S20/20MI** (alias `20/20MI`) | **Triple IR (IR³)** | MNDT696 (+ MADT696_01) | 43 |
| **S20/20SI** (alias `20/20SI`) | **Triple IR (IR³)** | MNDT694 | 40 |
| **20/20I** | **Triple IR (IR³)** | MNDT700 C | 3 |
| 20/20R | IR único espectro | MNDT713 | 2 |
| 20/20U · 20/20UB | UV | MNDT710 B | 9 · 9 |
| 20/20L · 20/20LB | UV/IR | MNDT720 | 8 · 8 |
| 20/20ML | UV/IR Mini | manual SharpEye 20/20ML | 13 |

| variante | alcance | altas | términos | gold perdidas | disparos | vínculos doc→producto | veredicto |
|---|---|---|---|---|---|---|---|
| **D** | solo la familia IR³ | 3 | +5 | 0 | 0 / 0 | 7 | PASS |
| **E** | serie 20/20 completa | 9 | +11 | 0 | 0 / 0 | 13 | PASS |

Los términos que entran son **todos de modelo, con dígitos y sin alias descriptivos** — el
contraste con B/C es total. En ambas variantes el software queda mapeado a los tres IR³, que es lo
que el propio manual dice: «El software permite comunicarse con hasta 64 detectores IR3».

**Recomendación: E.** El coste marginal sobre D son 6 términos igual de limpios, y cierra los 8
documentos huérfanos de una vez en lugar de dejar seis para otra sesión.

## Gaps declarados (los tres, de entrada)

1. **Ninguna variante mueve las 51 gold** (0 ganancias, 0 pérdidas): no hay golds sobre detectores
   de gas ni sobre llama 20/20. Esto es **cobertura de catálogo, NO una mejora medida en eval** —
   distinto del paraguas 2X-A, que sí hacía ganar fuentes a 2 golds. No debe venderse como delta.
2. **«20/20» y «S20/20» a secas** (47 y 41 menciones) siguen sin resolver modelo: quien escriba
   «el detector 20/20» sin sufijo no dispara nada. Un paraguas de serie tendría riesgo léxico real
   (proporciones, «20/20» como fracción) y **no se propone sin medirlo aparte**.
3. **MNDT690** («DETECTORES DE LLAMA — SPECTREX INC. / SPECTRONIX LTD.») es el catálogo de gama y
   queda sin mapear: es la clase R1 (serie × categoría) y se resolvería con tu firma en el mismo
   lote.
