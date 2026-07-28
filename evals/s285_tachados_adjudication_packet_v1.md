# s285 — Packet de adjudicación: semántica de los tachados `~~` en el corpus

> **Tu tarea (~10-15 min):** abrir **5 páginas de PDF** (citadas abajo con fichero + página) y
> responder UNA pregunta por clase: *¿en el PDF original ese texto está realmente TACHADO, o es
> énfasis (negrita / cursiva / subrayado) que el pipeline de conversión renderizó como tachado?*
> Marca `[ ]` por clase. Nada se cambia en DB ni en el pipeline con este packet — es la decisión
> de datos que desbloquea el diseño (gateado por dúo) posterior.

## Por qué importa (DEC-159)

El corpus servible contiene ~700 chunks con marcas `~~texto~~`. El significado cambia TODO:

- Si `~~` = **tachado real** (contenido eliminado por revisión del fabricante) → el texto debe
  retirarse o marcarse obsoleto. Ejemplo del peligro inverso: `... ~~no~~ están homologados según
  EN` → si el "no" está de verdad tachado, la frase vigente afirma que SÍ están homologados.
- Si `~~` = **énfasis mal renderizado** (el PDF subraya o pone en negrita la palabra) → hay que
  limpiar las marcas y CONSERVAR el texto. El mismo ejemplo: el fabricante enfatiza el "**no**"
  («NO están homologados») — quitarle el "no" sería la inversión de seguridad que el dúo bloqueó.

Es también la raíz de **hp011** (uno de los 3 FALLO del baseline): el artefacto «t.Fi» nace de
texto tachado/OCR en el TD de Securiton HLSI-MA-103.

## Distribución en vivo (28-jul, solo docs activos)

| clase | docs | chunks con `~~` | de ellos con `~~no~~` (la clase peligrosa) |
|---|---|---|---|
| **Securiton TDs** (descripciones técnicas, p.ej. ADW535) | 4 | 154 | **52** |
| **Notifier** (manuales legacy 15xxx SP + AgileIQ + otros) | ~85 | ~390 | 11 |
| Resto (Kidde, System Sensor, Aritech, Morley, Detnov…) | ~60 | ~160 | 1 |

## CLASE 1 — Securiton TDs · la que decide hp011 y la clase `~~no~~`

Abre **`ADW535_TD_T140358es_e`** (Descripción técnica ADW 535, español) y mira:

- **p. 16**: «El restablecimiento *in situ* `~~no~~` provocará la reinicialización de una CDI…»
- **p. 20**: «Los valores definidos en ellas … `~~no~~` están homologados según EN.»
- **p. 24**: «Para `~~continuar~~` con el reset … es necesario pulsar `~~el~~` botón `~~«OK»~~`…»
- **p. 9**: «XLM 35 Módulo SecuriLine (`~~no homologado conforme a UL/ULC~~`)»

**Mi lectura (a confirmar por ti):** en p.16/p.20 la frase SOLO tiene sentido CON el "no" (avisos
de precaución); en p.24 «el botón "OK"» tachado de verdad dejaría la instrucción sin verbo ni
objeto. Todo apunta a énfasis/subrayado mal renderizado, no a tachado editorial.

**TU MARCA — en el PDF original esto es:**
`[X] énfasis/subrayado (conservar texto, limpiar marcas)` ·
`[ ] tachado real (contenido eliminado)` ·
`[ ] mixto (anota páginas):`

## CLASE 2 — Notifier legacy (manuales 15xxx SP)

Abre **`15037SP`** (LCD-80, español) y mira:

- **p. 10**: «`~~Ejemplo:~~` Ajuste el LCD-80 para un tamaño de cuatro direcciones…»
- **p. 30**: «`~~LCD-80 ajustado para etiquetas de 20 caracteres:~~`»
- **p. 37**: «`~~Cuando el Blindado del EIA-485 esta en conducto:~~` conéctelo a…»

(También `15088SP` p. 100: «`~~Notas~~`» como título de sección.)

**Mi lectura (a confirmar):** son TÍTULOS y etiquetas de párrafo — en los manuales Notifier de esa
época los encabezados van subrayados; el conversor los volvió tachados. Un «Ejemplo:» tachado de
verdad no tiene sentido editorial.

**TU MARCA:** `[X] énfasis/subrayado` · `[ ] tachado real` · `[ ] mixto: ______`

## CLASE 3 — Resto del corpus (~160 chunks dispersos)

Si las clases 1 y 2 confirman «énfasis mal renderizado», propongo adjudicar el resto POR
ARRASTRE con verificación por muestreo (mismo patrón LQAS barato que el T2) — sin sentada extra
tuya. Si alguna clase sale «mixto», ese subconjunto se trata aparte.

**TU MARCA:** `[X] de acuerdo con arrastre+muestreo` · `[ ] quiero ver muestras también`

## Qué pasa según tu respuesta

- **Todo «énfasis»** → diseño de limpieza de marcas `~~` conservando texto (transformación
  determinista, reversible, gateada por dúo — es la condición que DEC-159 exigía), re-render de
  los chunks afectados, y re-medición de hp011. La inversión de seguridad queda estructuralmente
  descartada porque NO se elimina texto.
- **Algo «tachado real»** → ese subconjunto se marca obsoleto (lifecycle), nunca se sirve, y el
  resto sigue el camino anterior.
- **P2 relacionado (recordatorio):** el chunk corrupto `2113ac69` (HLSI-MA-103 p2, duplicado
  ri/4.1.2) se adjudica junto a esto — si confirmas Clase 1, el patch de ese chunk entra en el
  mismo diseño.
