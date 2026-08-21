# s335 · Fraseos de inventario + anafórica + «sí» pelado — v2 VINCULANTE (post-dúo, 21-ago-2026)

> Sustituye a la v1. Ronda emparejada ts=2026-08-21T14:40:14: **Sol 6 + Fable 7 = 13/13 con
> sustancia, 0 FP** (§5). Veredicto conjunto: «NO SÓLIDO por los dos críticos de pieza B» —
> ambos cerrados aquí con el rediseño honesto: prompt v3 + cohorte v3 + fila obligatoria.

## 1 · Pieza A — fraseos del atajo de inventario (flag `INVENTARIO_FRASEOS`, default off)

- **Formas nuevas** (con sustantivo de inventario + marca, ES **y EN** — Sol-3):
  desiderativas («quiero/necesito/me gustaría ver|saber … (listado|centrales|detectores|
  productos|modelos|equipos|catálogo) … de {marca}»), imperativas («dime|muéstrame|enséñame|
  dame …»), EN («I want to see {marca} panels/catalogs», «show me {marca} panels»).
- **Colocación definida** (Fable-5): las formas SIN marca-inline van al regex estático
  `_ENUM_FABRICANTE`; las variantes «… de {marca}» van a la rama dinámica de
  `_intencion_inventario` (donde ya vive «catálogo de {marca}»).
- **Tolerancia terminal `[.!?…]*$`** (Fable-4, hueco VIVO: Whisper cierra con «.» y el ancla
  actual `\??$` rompe hasta las formas interrogativas existentes por voz) — se aplica a las
  formas nuevas Y a las existentes, PERO gateada por el flag (cambia conducta de población
  real: consultas de voz que hoy van a RAG pasarían al atajo — Fable-6/Sol: el precedente
  s322 #76 era un cuantificador, esta superficie es mayor ⇒ FLAG, adjudicado).
- **Frontera anti-sobre-disparo** (Sol-4): anclaje terminal tras la marca/sustantivo con
  cola permitida SOLO de filtros censados (los del inventario actual) — y 6 negativos
  dirigidos que incluyen continuaciones TÉCNICAS con el mismo prefijo («quiero saber qué
  centrales Morley tienen salida de relé» ⇒ NO atajo, va a RAG).
- Framing honesto (Sol-6): la equivalencia s316e es un censo de rutas, no una prueba sobre el
  espacio de textos — la protección real son los tests dirigidos + el flag off.

## 2 · Pieza B — la anafórica, SIN autoengaño (Fable-1/2 + Sol-1/2 críticos)

**La v1 estaba mal**: relabel con prompt intacto no cambia la conducta (el clasificador dijo
`nuevo` en producción sobre `fabef50b`); la analogía con v2.1 era falsa (allí el gold se
alineó con el modelo; aquí se le pide al modelo cambiar sin tocarle el prompt). Rediseño:

- **PROMPT v3**: el criterio del owner se completa con la cláusula anafórica explícita —
  «si el mensaje se apoya en un pronombre/artículo anafórico sin sustantivo propio
  (“las/los/la/el de {marca}”, “eso de {marca}”) para referir la petición ANTERIOR,
  NO se sostiene solo ⇒ CORRECCION». Prompt nuevo ⇒ **cohorte v3 re-congelada ENTERA y
  re-corrida** (DEC-126, sin herencias).
- **Cohorte v3** = v2.1 + POSITIVA `fabef50b` («Y ahora quiero ver las de Morley», cita
  prod + adjudicación del owner). **Barra con fila OBLIGATORIA** (Sol-2/Fable-2): 0 falsas
  Y ≥14/15 Y **la fila fabef50b DEBE pasar su propia mayoría K** — no absorbible por
  holgura. GB2-e2e además VINCULANTE por encima del gate.
- **GB2 honesto** (Sol-1): el rebuild de una corrección sirve por RAG (STANDALONE — el atajo
  es inalcanzable desde F1, el oráculo murió en s333). La barra e2e = contenido Morley
  no-vacío sin cross-brand **con la LIMITACIÓN DECLARADA de lista parcial** (clase s307) —
  el listado GOBERNADO completo llega por pieza A cuando el usuario formula la petición
  entera; ambas vías quedan medidas y ninguna se vende como la otra.
- **Interacción a MEDIR, no presumir** (Fable-3): «y ahora» es cue de `_SWITCH_FRASE`
  (guardia INVALIDAR del plan) y el estado escrito por R8 entra en la población del
  clasificador con `models=()` — el GB2 corre el escenario e2e COMPLETO (atajo→corrección)
  y un dirigido del cruce con la guardia; el resultado se estampa sea cual sea.

## 3 · Pieza C — acotada (Sol-5 + Fable-7)

La v1 sobre-afirmaba «la generalización correcta». Alcance JUSTIFICADO hoy: `pending_aviso`
(la clase diseñada s333 §1.E, 1ª observación cumplida) — y Fable-7 precisa que la observación
real (`2a1e1694`) es «sí» tras RESPUESTA, no tras pregunta del bot: un TERCER caso que el
mecanismo pending-q NO cubriría. Todo ello va a SU dúo propio con objetivo+métrica cuando
Alberto dé el GO; aquí queda solo el censo de casos (aviso-ASR · pregunta-del-bot ·
confirmación-tras-respuesta) y NADA se cablea.

## 4 · Gates PRE-REGISTRADOS (v2)

- GB0: flags off ⇒ suite + dirigidos de no-cambio + MT 52/52.
- GB1 (flag A on): «Quiero ver las centrales de Morley.» ⇒ inventario (CON punto final);
  «dime qué centrales de Morley tienes.» ⇒ inventario; formas EN; 6 negativos técnicos ⇒ RAG;
  replay de la conversación real.
- GB2 (pieza B): gate cohorte v3 (regla K pinnada, fila obligatoria) + e2e atajo→«Y ahora
  quiero ver las de Morley.» con clasificador real (medido y estampado, incluida la
  interacción `_SWITCH_FRASE`) + limitación-lista-parcial declarada en el recibo.
- Ship: PR → merge → flags (`INVENTARIO_FRASEOS=on`; los de s334 ya viven) → verificación
  por voz: la conversación de la tarde entera, terminada con puntos como Whisper manda.

## 5 · Traza y adjudicación (ts=2026-08-21T14:40:14, 13/13 · 0 FP)

| # | hallazgo | adjudicación |
|---|---|---|
| Sol-1 crít | GB2 aceptaba lista RAG parcial como «reparada»; el rebuild no alcanza el atajo | §2: limitación declarada + doble vía medida |
| Sol-2 crít | barra ≥13/15 absorbe el fallo de la fila nueva | §2: fila OBLIGATORIA + ≥14/15 + e2e vinculante |
| Sol-3 med | sin paridad EN en desiderativas | §1: formas EN |
| Sol-4 med | gramática sin anclaje terminal (continuaciones técnicas) | §1: frontera + 6 negativos técnicos |
| Sol-5 med | pieza C sobre-ingenieriza; alcance justificado = pending_aviso | §3: acotada |
| Sol-6 men | s316e no prueba «todo lo demás byte-idéntico» | §1: framing |
| Fable-1 crít | relabel-sin-prompt ≠ v2.1 (analogía falsa): la fila nueva fallaría | §2: PROMPT v3 + cohorte v3 |
| Fable-2 crít | (=Sol-2 afilado) GO nominal con el caso motivador en rojo | §2 |
| Fable-3 med | «R8 lo sirve» no medido + cruce `_SWITCH_FRASE` sin analizar | §2: medir y estampar |
| Fable-4 med | ancla `\??$` rompe con el «.» de Whisper — hueco VIVO | §1: tolerancia terminal, gateada |
| Fable-5 men | colocación estático/dinámico sin definir | §1 |
| Fable-6 men | precedente s322 #76 sobredimensionado | §1: FLAG adjudicado |
| Fable-7 men | la observación es «sí» tras RESPUESTA — pending-q no la cubre | §3: censo de 3 casos |

## 6 · Build (B1-B6)

B1 regex v2 + rama dinámica + flag + inventario P1 + tests (formas/negativos/puntuación) ·
B2 prompt v3 + cohorte v3 + runner (fila obligatoria) + RUN · B3 e2e GB2 + cruce guardia ·
B4 GB0/GB1 + suite + MT · B5 recibos + docs · B6 PR + mergeabilidad verificada.
