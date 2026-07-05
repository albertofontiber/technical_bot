# s97c · Packet de repaso de golds hp011/hp014/cat016 (para adjudicación de Alberto)

> Procedimiento: el MISMO pipeline de autoría original (RULER_DESIGN §2, releído punto por
> punto) con Fable 5 en el rol de Opus + GPT-5.5 como cross-lector en frío de los renders
> (`cross_verify_image.py`). Renders 170dpi en `logs/render_s97c/`; transcripciones GPT en
> `evals/s97c_gpt_*.txt`. Lente adjudicada por Alberto: "¿qué exige realmente esta
> pregunta según el manual?" (chunks_v2/retrieval JAMÁS criterio — DEC-025).

## Resultado global
**12/12 hechos core verificados al píxel con doble señal (Fable+GPT: acuerdo pleno).
0 errores de anclaje** (incl. el '35' de hp014, que SÍ atribuye bien la resistencia al
LAZO con su método B+/B−→A+/A−). Los hechos de Opus son fieles a la fuente.
**3 re-tipados propuestos (uno por gold) + 1 observación de hecho faltante.**

## hp011 (RP1r: "tras descargar extinción no vuelve a normal al resetear — ¿qué comprobar?")
| hecho | fuente (verificada) | veredicto |
|---|---|---|
| ABORT | p.44: "por defecto enclavada… rearme manual" | **MANTENER core** (causa directa) |
| r.1 | p.63: tabla completa ('--'/00-default/01-30) | **MANTENER core** (es lo preguntado) |
| '05 a 295 seg' | p.56: fila de spec del parámetro t.A | **core→supplementary** — el rango es especificación; para "qué comprobar" lo que actúa es que el soak time existe y puede mantener el circuito activo |
| enclavadas | p.53: "todas las averías por defecto enclavadas… rearme manual" | **MANTENER core** |
**OBSERVACIÓN (autoría nueva, tu call):** la misma tabla de t.A (p.56) tiene la fila
"**- - : Circuito activado hasta rearme de la central (por defecto)**" — para ESTA
pregunta es posiblemente el dato más relevante de la página (explica directamente el
síntoma) y el gold no lo captura. Opcional añadirlo como hecho core.

## hp014 (ID2000: "¿cómo se conecta un módulo de aislamiento en el lazo?")
| hecho | fuente | veredicto |
|---|---|---|
| '25' | p.16: "no más de 25 equipos entre aisladores (20 si FET)" | **MANTENER core** |
| continuidad | p.16 §4.2: "continuidad ANTES de conectar los aisladores" | **MANTENER core** |
| terminales 2 y 4 | p.42: "cortocircuitando los terminales 2 y 4 de cada aislador" | **MANTENER core** |
| '35' | p.14: resistencia máx del LAZO (cableado GENERAL, ítem e) | **core→supplementary** — prerrequisito de cableado del lazo, no paso del procedimiento del aislador; y el procedimiento (p.42) tiene sus PROPIOS umbrales (14,5-35,5Ω según detección duplicada). Anclaje CORRECTO (lazo, no pantalla) — solo cambia el peso |

## cat016 (CAD-150: "¿cómo se da de alta un detector nuevo y cómo se prueba?")
| hecho | fuente | veredicto |
|---|---|---|
| autobusqueda | 55315013 p.9: alta vía autobúsqueda en menú BUCLE (nota: el manual tiene el typo "aubusqueda" en 1 de 2 menciones) | **MANTENER core** |
| menú ZONA + ELEMENTO | p.9 + usuario §3.1.x | **MANTENER core** |
| modo prueba | usuario p.13 §3.1.1.5: prueba sin rearmar, sirenas unos seg | **MANTENER core** |
| '20 minutos' | p.13: "si transcurridos 20 min sin disparo → vuelve a normal anulando la prueba" | **core→supplementary** — comportamiento de EXPIRACIÓN del modo prueba; no define "cómo se prueba" |

## Qué cambia si adjudicas los 3 re-tipados
- famtie: NADA (instrumento pineado; comparabilidad intacta). Los 3 hechos siguen contando
  como datos de encontrabilidad.
- Eje completitud (atomic) + contexto del juez: esos golds se evalúan por sus cores
  restantes (los procedimientos/causas que las preguntas piden) — la dirección exacta de
  tu adjudicación de CLIP.
