# s279 — Enmienda A5' al trim del plan v5 (POST-census, PRE-dúo focal)

**Qué pasó.** El census fase IV (freeze-contract A1, `s279_selection_census_report_v1.md`)
adjudicó los dos probes NOT_SELECTED. Para cat017 la causa es una **inconsistencia interna del
diseño v3**, no un fallo de calibración: la regla A5 (trim round-robin DESDE EL ÚLTIMO grupo,
mínimo 1 término) y la regla A7 (gate solo para grupos con ≥N_FACET=3 términos) se contradicen —
el arquetipo del multi-match es SIEMPRE el último grupo (así lo fija §3 para no mover la faceta
primaria), luego el trim lo recorta primero y lo deja bajo el umbral del gate **para cualquier
arquetipo nuevo, en cualquier query larga**. Medido: cat017 tsquery 688→445, grupo commissioning
`[sitio edificio licencia bin alta portal]` → llegó al gate como `[sitio, edificio]` (2) →
excluido por A7; el chunk diana contiene licencia/bin/portal (verificado contra la quote real).

**Enmienda A5' (corrección de coherencia, NO calibración al gold):**
- El trim NO puede reducir un grupo por debajo de `N_FACET=3` términos si el grupo tenía ≥3
  antes del trim (los grupos de 1-2 términos quedan como estaban: fuera del gate por A7).
- Orden del trim sin cambios (round-robin desde el último), pero saltando los grupos que ya
  están en su suelo (3 para gate-elegibles, 1 para el resto).
- Si con esos suelos el tsquery sigue >480: se eliminan GRUPOS ENTEROS desde el último
  (sin cambios respecto a A5); base >480 ⇒ plan None con receipt (sin cambios).
- Justificación de no-tuning: la regla se deriva de la CONSISTENCIA A5↔A7 (un grupo que el gate
  puede usar no debe ser degradado por el trim por debajo de lo que el gate exige), no del
  resultado del probe. Aplica simétricamente a TODOS los grupos gate-elegibles, primarios
  incluidos.

**Lo que la enmienda NO toca (y queda adjudicado como residual):**
- **cat019: NOT_SELECTED se mantiene.** Su span reparte los hits entre grupos (≤1-2 por grupo);
  bajo N_FACET=3-de-un-grupo no es alcanzable, y NO se afloja el umbral tras ver el resultado.
  Residual declarado de la ronda: 1 ítem de los 29 (hp017-clase «sirenas o módulos de control»)
  sin mecanismo general que lo sirva sin riesgo de sobre-selección (el control on-topic-adyacente
  dispara ya en cota superior con vista vacía).
- **H0 (identidad aguas arriba):** 12/15 QIDs no alcanzan el lane por `backfill:*`/lineage —
  workstream post-release «campaña de backfill de identidad» (conecta con el activo s83), fuera
  de esta ronda.

**Verificación de la enmienda:** tests del trim actualizados (suelo 3 pineado + los 3 bordes
A5 intactos) → census re-run SOLO probes+controles ($0) → si cat017 pasa a SELECTED con las
reglas generales, adjudicado; si no, se reporta tal cual. Después: oráculo baseline + smoke +
pasada final.
