# Pre-registro — A/B del lever context→generator (s48, diferido a Track B-dev)

> Pre-registro escrito ANTES de medir, para que el A/B no sea exploratorio (anti p-hacking;
> protege el embargo del held-out). Canónico: `DECISIONS.md` DEC-022. **Estado: PENDIENTE de
> ejecutar — espera el eval ampliado (Track B).**
>
> ⚠️ **PENDIENTE DE RECONCILIAR (s50, DEC-025):** este PREREG **pre-selecciona** por estrato
> `content-pobre`, que s50 demotó a causa post-hoc (era la fuente del vicio chunk-peeking). El reframe:
> el A/B corre sobre golds de DIMENSIÓN DE FALLO y se ve DÓNDE ayuda B (post-hoc resultan content-pobre),
> NO se pre-selecciona content-pobre. **NO correr este A/B sobre el PREREG viejo** — reconciliar primero
> (gatillo: antes del 1er A/B-lever; freeze-contract).

## Hipótesis
Incluir el blurb de contextual-retrieval (`chunk['context']`, B7) en el prompt del generador
—además del `content`— mejora la COMPLETITUD/precisión de la respuesta **en casos donde el
`content` del chunk es pobre/ambiguo**, SIN aumentar la invención. Default actual: el blurb solo
vive en el retrieval (embedding/FTS), no en la generación (`generator.py:411`).

## Por qué se difiere (s48)
Smoke sobre hp005/hp013 (content-claro): A≈B, el bot ignora el blurb, 0 fabricación, generador
no-determinista. Señal débil — PERO el smoke usó casos homogéneos de content-claro, que no cubren
los estratos donde el mecanismo podría actuar (refutación del cross-model, dúo s48). Medirlo bien
exige el eval ampliado con diversidad estratificada; con los 22 actuales no hay poder ni cobertura.

## Diseño (a ejecutar en Track B-dev)
- **Brazos:** A = generador actual (`GENERATOR_INCLUDE_CONTEXT=0`); B = con blurb (`=1`, marcado
  "orientativo, no-citable").
- **Set:** SOLO el **DEV** del eval ampliado. El **held-out NO se toca** — ni para decidir, ni para
  tunear el marcado, ni para seleccionar casos. Se usaría UNA sola vez, al final, si el lever pasa en dev.
- **Estratos pre-definidos** (la clave del poder es la diversidad, NO el N bruto): content-pobre /
  fragmento-truncado · multi-doc · vocabulary-mismatch ES/EN · OEM-relabeling · conflicto España-vs-US.
  + un estrato de **PASS-actuales como control de no-regresión**.
- **Freeze-contract:** retrieved-contexts congelados (idénticos para A y B; solo varía la inclusión del
  blurb) · juez GPT-5.5 + K-mayoría (K≥5, el generador es no-determinista) · mismo índice/corpus/
  embeddings · run-manifest persistido.
- **Métricas (2 ejes, DEC-001):** Δ veredictos (PASS/PARCIAL/FALLO) **por estrato** + eje
  no-fabricación (completitud↑ SIN invención↑). Excluir los casos inestables del juez del cómputo de Δ.

## Criterio de activación (decidido ANTES de medir)
- **Shipear** si: Δ veredictos > ruido del juez (K-mayoría) en ≥1 estrato, SIN regresión en
  PASS-control, SIN aumento de invención, en DEV; confirmado una vez en held-out.
- **Cerrar el lever** si: Δ ≈ 0 en todos los estratos (incl. content-pobre/multi-doc/ES-EN) →
  débil-por-diseño confirmado con población diversa (no solo con el smoke homogéneo de s48).
- **Pre-requisito de implementación (si shipea):** el retriever debe devolver `context` en TODAS
  las ramas — hoy solo la rama vector (RPC); keyword/content lo omiten en su SELECT (deuda s48).
