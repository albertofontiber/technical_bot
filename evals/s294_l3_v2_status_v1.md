# s294 · L3 v2 (gatillo compuesto «siempre») — estado tras cumplir 5 de las 6 condiciones

**Nada cableado en `src/`.** Todo lo de abajo es medición determinista + dos adjudicaciones
ciegas del cross-model. La decisión de seguir o parar es de Alberto: yo soy la parte
interesada.

## Las seis condiciones que el dúo puso a la v2 (DEC-171)

| # | condición | estado |
|---|---|---|
| **F1** | seam por-parámetro (sin tocar `mp_lexicon`) | **verificado suficiente, no cableado**: `_sentence_has_finite_verb` = True en las 5 formas candidatas ⇒ el átomo pasa la whitelist sin exención. La v1 moría SOLO porque `_mandatory_triggers` devolvía `[]` en los dos sitios (`must_preserve:608` detector y `:1990` whitelist) |
| **F6** | lista cerrada de imperativos | **hecho**: congelada desde el modo `discover` (cada entrada observada, n≥2). Y la adjudicación r1 **eliminó la forma B** entera |
| **F4** | censo out-of-sample | **hecho**: 1.552 chunks del corpus con «siempre»/«always», reproducible |
| **F5** | ES/EN | **hecho** — y su solución **destapa un problema nuevo** (ver abajo) |
| **F3** | guard de integridad de span | **construido** al listón del adjudicador; excluye 23 capturas corpus-wide |
| **F7** | adjudicación ciega + regla de daño | **r1 = STOP** (12/61) → rediseño → **r2 = 1/60** … que por la regla **es STOP otra vez** |

## Adjudicación ciega (cross-model, taxonomía pre-registrada, diana incluida sin marcar)

| ronda | gatillo | espurias | precisión | reparto |
|---|---|---|---|---|
| **r1** | s292 (formas A+B) | **12 / 61** | 80,3% | forma B 11 · forma A 1 · clases: `span_roto` 8, `descriptivo` 2, `nota_de_diseno` 2 |
| **r2** | v2 (solo A + guard de span + exclusión UI) | **1 / 60** | **98,3%** | clase `duplicado` |

La **diana salió `legitima` a ciegas en las dos rondas** («exige desconectar el magnetotérmico
antes de trabajar en la central»).

## Por qué el STOP de r2 NO se puede reinterpretar

La única espuria es una **pareja de contención** en el mismo chunk (`c2f21e0e`): la frase B es
la frase A más una coletilla. Medido en el código, no supuesto:

- `_near_duplicate_span(A, B)` = **False** en ambos sentidos ⇒ el apéndice **emitiría las dos**.
- Por qué falla: solape SequenceMatcher **0,908 ≥ 0,90 ✓**, números iguales ✓, pero el **set de
  tokens difiere en uno** (`tipo`) — y el guard, por diseño deliberado de s271, conserva ambos
  cuando un token difiere («sirena» vs «fuente» = hecho técnico distinto). Aquí no son hermanas:
  **una contiene a la otra** (`B.startswith(A)` = True). Es un **punto ciego de contención**.
- Ese guard es **maquinaria compartida con la lane L2 viva en producción**.
- **Pero el defecto NO dispara hoy**: 0 parejas de contención con el léxico actual sobre los
  **398 chunks servidos** de los 39 golds. Lo introduciría L3.

## El hallazgo nuevo, y el que más pesa: duplicado CROSS-LINGÜE en la propia diana

Sobre la superficie real de emisión (los 398 servidos), el gatillo v2 dispara **3 veces en 2
chunks**, y las tres están en el MISMO manual de la CAD-150:

1. `eaa39792` p.8 (ES) — **la diana**: «Desconecte siempre la magneto térmico bipolar exterior
   antes de manipular la central.»
2. y 3. `7849231c` p.20 (EN) — sus gemelas: «Always disconnect the mains power before handling
   the panel.» · «Always connect the mains first and then the batteries.»

**Los dos chunks se sirven en la MISMA respuesta de hp003** (verificado en `served_ids`), y el
cap de familia MANDATORY es 2 ⇒ el apéndice emitiría la obligación **en español y su gemela en
inglés**, en una respuesta en español. `_near_duplicate_span` no puede cazarlo: idioma distinto,
tokens distintos. Es consecuencia DIRECTA de satisfacer F5 (el léxico se declara bilingüe).

## La bifurcación (decisión de Alberto)

**(A) Parar L3 v2 aquí y pasar al lever B de `cat017#2`.** El lever B tiene retorno probado
(alcanzabilidad 0/5 → 5/5) y no toca ni el léxico ni el dedup compartidos. — **Mi
recomendación**: L3 v2 necesita **dos** cambios en maquinaria compartida con la lane viva
(política de idioma del apéndice + dedup por contención), cada uno con su dúo y su gate, para
entregar **1 hecho**; y «radio a serving» es exactamente la clase que mató la v1.

**(B) Seguir L3 v2** aceptando ese alcance: política de idioma (emitir solo spans del idioma de
la respuesta, o preferir ES cuando exista gemela) + extensión del dedup a contención. Ambas son
mejoras legítimas y estructurales de la lane L2 —el punto ciego de contención es real—, pero
hoy **no tienen justificación independiente**: 0 casos con el léxico actual.

## Lo que queda escrito pase lo que pase

- El **punto ciego de contención** de `_near_duplicate_span` (latente, medido, con su causa
  exacta) y el **hueco de política de idioma** del apéndice: dos defectos reales de la lane L2
  viva, encontrados sin tocarla.
- El gatillo v2 y su censo reproducible: si algún día se retoma, la medición ya está.
