# s328 — La regresión del gráfico, el gate de geometría, y la puerta con marca Fontiber

**Contexto**: Alberto abrió `/metricas` en escritorio y dijo que se veía «como con zoom». Era una
regresión mía de anoche (s327). Y pidió aparte que `/entrar` se vea como el login del Data Room.

**Estado**: cableado, sin commitear. Suite completa **4663 passed, 84 skipped, 0 fallos**. Impacto
MEDIO (render del panel expuesto a internet + gate nuevo en CI + superficie de la puerta).

> **Nota de proceso**: TODO fichero citado aquí existe ya en el árbol de trabajo. Es la regla que
> salió del hallazgo crítico de la ronda anterior (cité un artefacto de medición antes de crearlo):
> **el artefacto se versiona ANTES de citarlo**.

## Alcance (lee con tools; ancla fichero:línea)

- `dashboard/render.py` — `barras()` reescrita, bloque CSS del gráfico, bloque CSS «LA PUERTA»,
  `pagina()` con `clase_cuerpo`.
- `dashboard/app.py` — `pagina_entrar()` con el logotipo y el pie nuevos.
- `scripts/s328_panel_servidor_de_medida.py` — servidor con transporte doblado (NUEVO).
- `tests/test_s328_panel_geometria.py` — el gate de navegador (NUEVO).
- `.github/workflows/s328-panel-geometria.yml` (NUEVO).
- `tests/test_s327_panel_portada_movil.py` — dos tests nuevos de estructura.
- `TECH_DEBT.md` #94 (cerrada), `docs/PANEL_RESPONSIVE.md`, `docs/DECISIONS.md` DEC-249.

## Qué afirmamos (verifícalo o refútalo)

1. **La causa del «zoom» era tener DOS sistemas de coordenadas**: SVG fluido sin tope + rótulos en
   `<div>`s de 28 px fijos. Solo cuadraban cuando el SVG se pintaba a 1 unidad = 1 px. Medido sobre
   el código de s327 con Chromium: **×2,29 y 264 px de desalineo a 1440**; ×1,50 y 100 px a 768;
   **81 px a 390** (el móvil también estaba roto).
2. **El arreglo es por construcción, no por ajuste**: el rótulo va DENTRO del SVG ⇒ una escala. El
   CSS topa el ancho en `render.ANCHO_GRAFICO` y un test cruza la constante con la regla CSS.
   `barras()` ya no acepta `ancho` para que nadie mueva el `viewBox` sin mover el tope.
3. **El gate caza la CLASE, no mi arreglo**: la sonda de alineación busca el rótulo dentro del SVG
   *y también* en una columna HTML hermana. **Control negativo ejecutado**: 13 rojos con el render
   de s327, 39 verdes con el arreglo.
4. **La puerta no puede alcanzar al resto del panel**: todo cuelga de `body.entrada`; el resto sigue
   con el design system del war room.
5. **La CSP sigue intacta**: sin JavaScript, sin fuentes externas, sin atributos `style`. Por eso
   NO están el botón «Mostrar», ni la Playfair de Google Fonts.
6. **Nada de la puerta miente sobre lo que el panel hace**: no hay «¿olvidaste tu contraseña?» (no
   hay recuperación) ni «verificación en dos pasos» (no hay 2FA); el campo sigue siendo `Usuario`,
   no `Email`.

## Gaps declarados (no los re-descubras; atácalos si crees que son peores)

- El gate mide **Chromium**: Safari/iOS no entra, y el técnico en obra puede llevar un iPhone.
- El gate mide **geometría, no estética**.
- El rótulo se recorta a 16 caracteres; el texto completo va en el `<title>` de la fila.
- Con el tope, en una tarjeta muy ancha el gráfico deja hueco a su derecha. Es deliberado: la
  alternativa (crecer) es el bug.
- El servidor de medida usa credenciales de mentira **versionadas** en `scripts/`, incluido un
  registro scrypt con formato válido. No abre nada, pero está en el repo.

**Pregunta al revisor**: ¿hay algún camino por el que (a) el gráfico vuelva a tener dos escalas sin
que el gate se entere, (b) el CSS de la puerta se escape a otra página o abra la CSP, o (c) la
puerta afirme sobre seguridad algo que el panel no hace?


---

## v2 — qué cambió tras la ronda de Fable (5 hallazgos, 5 confirmados, 0 FP; veredicto NO SÓLIDO)

El revisor respondió a las tres preguntas del briefing con un «sí» a dos de ellas. Las claims 3 y 4
sobre-afirmaban, y una de ellas escondía un daño colateral que yo no había visto.

**F1 · [medio] El aislamiento de la puerta era convención, no construcción — y de paso rompí la
página de error.** `.entrar`, `.marca-puerta` y `.pie-puerta` NO colgaban de `body.entrada`, y
`class="entrar"` **ya se usaba** en la página de error (`app.py:1025`). O sea: mi
`.entrar { max-width:none; margin:0; }` le estaba cambiando el layout **hoy** a una página que
nadie estaba tocando. Verificado con grep antes de actuar. Cerrado en dos: la regla original de
`.entrar` restaurada para `_error`, todo lo de la puerta bajo `body.entrada`, y la 404
re-fotografiada con Chromium para comprobar que volvió a su diseño.

**F2 · [medio] El gate cazaba MI instancia, no la clase.** Tres huecos, los tres reales:
(i) un SVG sin `viewBox` se saltaba con `continue`, así que el test de alineación pasaba **en
vacío**; (ii) el rótulo de fuera se buscaba **por nombre de clase** (`.etiquetas`/`.etiqueta`) —
otra implementación de dos escalas con otros nombres pasaba en verde; (iii) solo cubre `barras()`.
Cerrado: la sonda ya no mira nombres de clase (los rótulos de fuera son «hojas con texto del
subárbol del padre del SVG», que es lo que es una columna de rótulos se llame como se llame), no
se salta ningún SVG, y si encuentra un SVG al que no puede medirle el ancho natural es **rojo**, no
salto. (iii) se declara sin arreglar: no se puede gatear un tipo de gráfico que todavía no existe.

**F3 · [medio] El gate podía quedar VERDE sin medir nada.** Si el `launch` de Chromium fallaba en
CI, `pytest.skip` → job verde. Es **el patrón de cobertura-que-miente que #94 vino a cerrar,
reintroducido dentro del propio arreglo de #94**. Cerrado con `PANEL_GEOMETRIA_EXIGIDA=1` en el
workflow: sin navegador es rojo; en local sigue saltando. **Verificado en los tres modos**:
exigido-sin-navegador = 2 failed + 45 errors · no-exigido-sin-navegador = 47 skipped · normal =
41 passed. Para poder ejercitarlo hubo que hacer sobrescribible la ruta del navegador
(`PANEL_CHROMIUM`): mi primer intento, con `PLAYWRIGHT_BROWSERS_PATH`, **no probaba nada** porque
la ruta estaba fija en el módulo.

**F4 · [menor] El control negativo era prosa.** «13 rojos con el render de s327» no se puede
reproducir desde el repo: ese render ya no está en el árbol, así que la única evidencia vivía en un
comentario. Es la misma clase que el hallazgo crítico de la ronda anterior. Cerrado de la única
forma que vale: el patrón roto se **reconstruye en una página sintética versionada**
(`_PAGINA_ROTA`) y dos tests exigen que la sonda la marque **y que NO marque el render vigente** —
sin la segunda mitad, una sonda que dijera «roto» siempre pasaría la primera. El discriminador
queda auditable desde el repo para siempre.

**F5 · [menor] El docstring de `render.py` citaba `script-src 'none'`** cuando la cabecera real es
`default-src 'none'` (`app.py:156`). Corregido.

**Lo que el revisor NO pudo verificar**, y así se queda: las cifras de Chromium sobre el render de
s327 (×2,29 y 264 px) son declaración mía. F4 es exactamente lo que arregla esa clase hacia
adelante — de aquí en adelante el discriminador es un test, no una frase.
