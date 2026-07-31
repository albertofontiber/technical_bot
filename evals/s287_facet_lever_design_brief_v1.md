# s287 — Lever de FACETA (DEC-164b): abrir el gate de arquetipo para la clase «diferencia-entre-variantes / semántica-de-sufijo»

## HALLAZGO (auditoría DEC-164, verificado con trazas + llamadas deterministas)
La lane structural (`same_blob_structural_neighbor_coverage_v1`) tiene los anchors de
cat022#0/#1 a 1-8 chunk_index de seeds SERVIDOS (mismo doc+sha, dentro de max_gap:8) y NO
dispara porque `expand_query_facets(cat022) → archetype=None` (ninguno de los 9 arquetipos de
`config/retrieval_facets_v3.yaml` cubre la clase) → `require_evidence_facet` fail-closed
(`structural_neighbor_coverage.py:277-283`: sin facet match, todo candidato se descarta).

## RECOMENDACIÓN
Arquetipo NUEVO en `config/retrieval_facets_v3.yaml` (SOLO config; cero código de lane):
`variant_differentiation` — triggers: «diferencia entre X y Y», «qué significa el sufijo»,
«en qué se diferencian», comparativas de variantes de una familia; evidence facets: celdas de
tablas comparativas/specs por-variante (patrones tipo sufijo→atributo, bandas/rangos con
unidades, columnas con-BIT/sin-BIT). Radio/caps/cuota/diversify INTOCADOS; `require_evidence_
facet` sigue (el arquetipo nuevo lo alimenta, no lo apaga); fail-closed intacto para el resto.

## GATES (deterministas primero)
1. `expand_query_facets` sobre las 39 queries: SOLO la clase diana cambia de archetype
   (lista exacta de cambios; cualquier query fuera de la clase que gane arquetipo = STOP).
2. Probe de lane en cat022 ($0): appends aparecen y las anclas son las celdas IR
   (`74cc9f95`/`c94d2270`/`36ca37d0`/`a6eae6a1` candidatas).
3. Centinelas 6 + sweep-39 de composición (los appends solo cambian donde el arquetipo dispara).
4. Smoke dirigido ×2 (cat022 + 2 controles) — estabilidad.

## RIESGOS DECLARADOS
1. Sobre-disparo del trigger en queries no-comparativas (el gate 1 lo caza; wording del
   trigger = superficie principal de review). 2. Calidad de las evidence facets: si matchean
   texto genérico, la lane apendiza ruido en la clase (gate 2-3). 3. Sellos: verificar si
   `retrieval_facets_v3.yaml` está pineado por recibos C1 (inventariar ANTES; la lane config
   sí lo está). 4. El OK-blando de «BIT» NO se persigue con esto (varianza de juez, otra cosa).

## ALTERNATIVAS DESCARTADAS
- Ampliar radio/max_anchors: toca parámetros sellados de la lane y es la clase hp012/hp013
  (lever separado, seed-proximity). - archetype=None→default-open: quita el fail-closed
  global = apendizaría sin criterio en TODA query sin arquetipo. - Re-litigar diversify:
  falsificado en DEC-164a.

# ══════ v2 SPEC SELLADO (dúo: Fable 8 [F1 crítico NO-OP] + Sol 5-6 — convergen) ══════
1. **[F1] DOS ficheros, no uno**: arquetipo `variant_differentiation` en `retrieval_facets_v3.yaml`
   Y entrada gemela en `config/evidence_coverage_facets_v4.yaml` (STRICT_ALIGNED_CONFIG — sin
   ella el gate fail-closed descarta todo = NO-OP; prueba: compatibility/battery_sizing están
   en v3 y no en evidence-v4 y nunca pasan).
2. **[F2] Diff esperado PRE-REGISTRADO = {cat022} SOLO** — cualquier otra query que gane
   arquetipo (cat011/cat021 son las adyacentes) = STOP, sin racionalización post-hoc.
3. **[F3/Sol] Posición: AL FINAL de la ontología first_match** + test identidad-de-prefijo
   (patrón del test v5: payload[:-1] == payload_anterior).
4. **[F4/Sol] Triggers con FRONTERA DE PALABRA y BILINGÜES ES/EN** (lookahead
   diferencia+entre / difference+between / sufijo / suffix; JAMÁS stem `diferenc` — trampa
   «diferencial» del vocabulario PCI). Alcance declarado ES+EN.
5. **[F6] Evidence facets = vocabulario de CLASE encodable** (schema sin dígitos):
   [version, modelo, descripcion, bit, prueba, incorporada, sensor, longitud, onda, espectral,
   suffix, model, built, test] con min_distinct_terms:2 + required_any discriminativo
   [bit, incorporada, version/…] — NO calcadas del doc Spectrex (anti gold-specific).
6. **[F8] Consumidor colateral declarado**: el shadow observer del bot (telegram_bot:780,
   fail_open) consume v3 → su telemetría cambia; impacto bajo, anotado. Sellos C1 NO bloquean
   (compara blobs del commit sellado — F7 verificado).
7. **Gate 3 real [Sol]**: el artefacto sweep-39 de P1 NO sirve aquí — sweep FACET-aware:
   expand_query_facets×39 (diff exacto vs pre-registro) + probe de lane en cat022 + centinelas.
8. Erratas del hallazgo corregidas: v3 tiene 7 arquetipos (no 9).

# ══════ ENMIENDA post-STOP: F2 re-sellado {cat005, cat022} ══════
El gate (a) del build paró en legítimo STOP: el diff real fue `{cat005, cat022}` contra el
pre-registro `{cat022}`. Enmienda declarada a Alberto y sellada ANTES de re-correr (no
racionalización post-hoc: el STOP se respetó, el pre-registro se re-sella explícitamente y la
razón queda escrita aquí).

- **Nuevo F2 = `{cat005, cat022}`.** Cualquier tercera query que gane arquetipo sigue siendo STOP.
- **Motivo — cat005 es MIEMBRO GENUINO de la clase, no un falso positivo:** su enunciado es
  «…¿y **en qué se diferencian** las versiones digital y analógica?» → una comparativa de
  variantes de una misma familia (Fidegas CS4), exactamente la clase que el arquetipo define. El
  error estuvo en el CONTEO del pre-registro (se enumeró la clase leyendo sólo cat022), no en el
  trigger. El trigger `\ben\s+que\s+se\s+diferencian\b` es **español natural** y se **CONSERVA**:
  estrecharlo para que sólo cazara cat022 sería overfit al gold diana — el lever tiene que servir
  a la clase, no a una fila del eval (escala a 30+ fabricantes).
- **cat005 = CONTROL PROTEGIDO.** Estado en el run v3 (`evals/s100_factlevel_full_v3_20260729.yaml`):
  `hist = {OK: 6, …}` = **6/6 OK** con `appended_n = 0` / `coverage_status = no_append`. Es la
  query de la clase que HOY ya está perfecta: no hay nada que ganar y todo que perder.
  Contrato: **cualquier regresión en cat005 = STOP del lever** (no se «compensa» con cat022).
  Gate (b) se extiende a cat005: si la lane le apendizara **ruido genérico** → STOP; si no
  selecciona nada, o selecciona celdas de comparativa por-variante que pasan el
  `required_any [bit, incorporada, version]`, sigue.
- **DESCARTADO: mutilar F4** (recortar los triggers ES para forzar el diff a `{cat022}`). Es la
  alternativa que «hace pasar el gate» y la peor: convierte el arquetipo de clase en un
  reconocedor de un gold, deja `en qué se diferencian` sin cubrir para el resto del corpus, y
  esconde el verdadero riesgo (¿apendiza bien en la clase?) en vez de medirlo. Se elige medir
  cat005 con protección explícita en lugar de dejarlo fuera del alcance.
- **DESCARTADO: excluir cat005 del alcance** vía un anti-patrón/negative-lookahead sobre
  «versiones digital y analógica»: mismo overfit, con la deuda añadida de un anti-patrón que
  nadie podrá justificar en 6 meses.
- Alcance sin cambios en lo demás: centinelas 7/7, radio/caps/cuota/diversify intocados,
  `require_evidence_facet` fail-closed intacto, lane shadow-only.

# ══════ FIX post-STOP-b2: `version` fuera de `required_any` (homógrafo norma); control cat005 re-adjudicado ══════
El gate (b.2) paró en STOP legítimo: la lane seleccionaba para **cat005** (CONTROL PROTEGIDO,
6/6 OK con `appended_n=0`) la pág. 13 del manual Fidegas S/3-2 — una **DECLARACIÓN UE DE
CONFORMIDAD**, no una celda de comparativa. Aprobaba el fail-closed con
`term_hits = [descripcion, sensor, version]`, donde `version` venía de «con respecto a la
**versión** EN 60079-0:2009» = **EDICIÓN DE UNA NORMA**, no una variante de producto.

- **FIX (candidato (i) del informe del gate, declarado a Alberto):** en
  `config/evidence_coverage_facets_v4.yaml`, faceta `variant_attribute_matrix` →
  `required_any: [bit, incorporada]`. **`version` PERMANECE en `terms`** (sigue contando para
  `min_distinct_terms`, sigue siendo vocabulario legítimo de la clase); lo que pierde es el poder
  de **sostener sola** el fail-closed. `bit`/`incorporada` sólo aparecen en una comparativa
  por-variante real («la función de Prueba **incorporada** (**BIT**) sólo se incluye en…»).
- **Por qué es de RAÍZ y no un parche:** el gap no era «un chunk malo», era un **homógrafo con
  poder de veto** en el discriminativo. Se corrige en el eje que lo causa (qué término puede
  autorizar por sí solo), no con un anti-patrón contra el doc Fidegas ni con una exclusión por id
  — ambos serían overfit invisible en 6 meses. Escala: cualquier manual con declaración de
  conformidad (todos los de ATEX) dejaba de ser candidato por la misma razón estructural.
- **Efecto medido, no supuesto** (re-run completo del gate, mismos seeds/blobs):
  - **cat005 → 0 anclas seleccionadas.** El único candidato (`38b894d1`) cae por `required_any`:
    sus hits no incluyen `bit` ni `incorporada`. Control **intacto** (`appended_n` sigue 0), y su
    adjudicación manual queda **retirada** (`RETIRED_CONTROL_ADJUDICATIONS` en el gate) porque el
    ancla ya no se selecciona — no se reutiliza una llamada vieja sobre una selección nueva.
  - **cat022 rank-1 `74cc9f95` SOBREVIVE** (celda IR pre-declarada, gap 3, pág. 8 de
    `MNDT722_40-40L`): tiene `bit` + `incorporada` + `prueba` del span
    «Existen dos versiones… S40/40L4 funciona a 4,5 µm… la función de Prueba incorporada (BIT)
    sólo se incluye en los modelos S40/40LB y 40/40L4B».
  - **DECLARADO — el rank-2 `255948d3` («# Tablas», `MNDT723_40-40U`) NO cae:** sigue pasando
    `required_any` porque su cola contiene una frase de comparativa GENUINA
    («…S40/40UB, este último incluye además la función de Prueba incorporada (BIT)»), de donde
    salen `bit`/`incorporada`. Es un chunk **mixto** (índice-de-tablas + intro con la comparativa),
    no un falso positivo del discriminativo, y es de un manual **hermano** (serie 40/40U, no la
    40/40L de la pregunta). El fix no lo toca, y no debía: filtrarlo exigiría un criterio de
    pureza-de-chunk (TOC-ness) o de doc-matching, que es **otro lever** (clase TOC/índice) y no
    se cuela aquí. Queda como GAP ABIERTO declarado, no como ruido silenciado.
- **DESCARTADO — quitar `version` también de `terms`:** perdería vocabulario real de la clase
  («versiones digital y analógica», «Tabla 2: Versiones del detector») sin ganar nada: el veto ya
  lo cierra el `required_any`.
- **DESCARTADO — negative-lookahead contra `EN 6\d{4}` / «norma»:** anti-patrón que codifica un
  documento concreto en la ontología de clase, con dígitos (el validador de
  `evidence_coverage.py:84` los prohíbe en `terms` precisamente por esto).
- **DESCARTADO — endurecer `min_distinct_terms` a 3:** global al fichero, tocaría los 5
  arquetipos pre-lever (prefijo sellado por test de identidad) para arreglar uno nuevo, y el
  texto normativo casaba 3 términos de todas formas → no habría cerrado el leak.
- **Contrato del test:** el `xfail(strict=True)`
  `test_norm_edition_version_is_the_open_required_any_leak` pasaba a XPASS con el fix → se
  **invierte** (marcador retirado, nombre y aserciones pinean el comportamiento nuevo: texto de
  norma con `[descripcion, sensor, version]` NO pasa) + un test nuevo pinea que `version` sigue en
  `terms` y que una comparativa por-variante real sigue casando.
