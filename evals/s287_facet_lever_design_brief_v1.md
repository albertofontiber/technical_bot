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
