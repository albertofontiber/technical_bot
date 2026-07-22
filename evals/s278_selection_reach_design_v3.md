# s279 — Diseño: alcance de selección del lane document-local (v3, POST-dúo r2 — BUILDABLE)

**Estado:** v3 tras adjudicar r2 (Sol 7 + Fable 8 — `s278_selection_reach_duo_r2_adjudication_v1.yaml`;
los 12 fixes incorporados abajo con su id). Pendiente dúo r3 FOCALIZADO en el delta v2→v3.
**Métrica y precondiciones:** sin cambios (ítems P1 cat017/cat019; no-regresión; baseline
byte-inerte; datos cerrados DEC-150/151). **Límite de alcance declarado [ES-ONLY]:** el lane
document-local es ES-only por contrato; multi-match EN queda fuera de alcance de esta ronda y
así viaja a release-notes.

## 0. Gating y perfil [PERFIL-CAPACIDAD]

- Flag profile-owned NUEVO: `DOCUMENT_LOCAL_SELECTION_V2`. Perfil atómico NUEVO
  `coverage_c1_v4` = flags de v3 + este. `coverage_c1_v3` queda semánticamente CONGELADO
  (cero cambio para v2/v3); el flip de release pasa a `coverage_c1_v4`. Todas las conductas de
  esta ronda (C1/C2/C3) leen ESTE flag; off ⇒ byte-inerte (el código nuevo ni se alcanza).

## 1. Compuerta 1 — truncado combinado work-conserving [WATERFALL]

- Por-scope: overflow (RPC devuelve `candidate_limit+1`) ⇒ conservar las primeras
  `candidate_limit` filas por `chunk_index` (orden garantizado por SQL, verificado) con receipt
  `candidate_truncated: true, observed_rows: ">=65"` (sin cambio SQL — decisión adjudicada).
- Combinado: **waterfall determinista** — cupo global 64; asignación inicial
  `floor(64/n_scopes)` por scope en orden estable (`source_file` asc); cada scope toma
  `min(observadas, cupo)`; el remanente se reasigna al otro scope (una pasada, determinista).
  10+65 ⇒ 10+54=64. Sin cláusulas muertas. La cobertura del carrier de cat017 se DEMUESTRA en
  el census, no "por construcción".
- `plan is None` sigue apagando el lane CON receipt `blocked_tsquery_unrepresentable`.

## 2. Compuerta 2 — vía complementaria por-faceta [VIA-INALCANZABLE · ATTEST · TIEBREAK]

**Colocación (H1):** la vía corre **POST-composición**, en el punto exacto del patrón reserve
(`_append_obligation_warning_reserve`), con presupuesto propio `FACET_COMPLEMENT_BUDGET=1`
fuera de `MAX_APPENDED=4`. Fuente de candidatos:
- si el lane document-local CORRIÓ: reusa su candidate-pool cacheado ($0 extra);
- si fue SALTADO por capacidad Y el plan tiene ≥1 need-group sin cubrir: **UNA llamada RPC
  propia GET-only** (coste declarado: +1 request, ~2s worst-case, solo en ese caso);
- receipt del origen: `facet_fetch: own | reused | skipped_no_uncovered_group | skipped_no_plan`.

**Plumbing (H2):** la evaluación de elegibilidad recibe el PLAN del lane por la firma (el que
se construyó con v5 si C3 está activa); no pasa por el delegado `select_rerank_pool_coverage`
(v4 hardcodeado).

**Elegibilidad y ranking (pre-registro TOTAL — TIEBREAK):**
- Elegible: mejor ventana de 360 chars con ≥`N_FACET=3` términos DISTINTOS de UNA need-group
  no-cubierta ("cubierta" = la misma regla de ventana sobre las filas YA SERVIDAS de la vista
  compuesta, computable en este punto porque la composición ya ocurrió — H1 lo habilita).
- Orden entre need-groups: cobertura asc (0-cubiertas primero) → índice de grupo asc.
- Dentro del grupo: `terms_hit` desc → densidad desc → `chunk_index` asc → `source_file` asc
  → `id` asc. Sin pesos. El probe ADJUDICA, no calibra.

**Attestation re-derivable (sol#3):** la fila por-faceta se estampa
`facet_complement_validated: true` + `{plan_sha256, need_group_index, need_group_terms,
window_bounds, quote_sha256, served_row_ids_at_eval}`. `_attest` re-corre la regla de ventana
sobre el contenido del candidato y re-verifica la no-cobertura contra los `served_row_ids`
registrados (visibles en la vista compuesta). La fila SIRVE por las clases existentes: pipe-row
si es derivable; si no, prose_source_card con TODOS los checks del dúo r2 de §4 (prosa-idad
positiva incluida). La vía cambia SELECCIÓN, nunca clases de serving.

## 3. Compuerta 3 — facetas v5 solo-lane [SEAM-DELEGADO · VALIDADOR · TRIM]

- Fork `config/retrieval_facets_v5_document_local.yaml` con `schema:
  retrieval_facets_v5_document_local`, v4 byte-intacto. **Cambio declarado del validador común**
  (`query_facets._load`): whitelist + policy-check condicionado por schema (`first_match`
  obligatorio ≤v4; `multi_match {max: 2}` solo en v5). Blast-radius: el validador es compartido —
  guardado por suite completa + oráculo byte-inerte + test de byte-igualdad del v4 cargado.
- Solo `build_document_local_query_plan` bajo el flag §0 carga v5; `MAX_NEED_GROUPS_MULTI=5`
  por-vía; test `plan is not None` ×13 QIDs + controles.
- **Trim pre-registrado [TSQUERY-TRIM]:** si el tsquery supera 480 chars: round-robin desde el
  ÚLTIMO grupo, retirando el último término de cada grupo, hasta caber. Test lo pinea; jamás se
  ajusta post-resultado.
- Arquetipo `commissioning_setup`: 6 términos elegidos contra las superficies REALES de los
  chunks objetivo (verificación en build; token-exacto cliente vs stemming FTS declarado)
  [STEMMING-GATE].

## 4. Verificación (escalera con observabilidad real) [CENSUS · CONTROL-NEGATIVO · CONTROLES]

1. Tests unitarios por compuerta + los obligatorios del dúo (plan-not-None ×13; waterfall
   10+65⇒64; presupuesto propio no desplaza — fixture ALCANZABLE post-composición; attest
   re-derivable con tampering de cada campo; prosa por-faceta pasa los negativos §4; byte-igualdad
   del v4 cargado por el validador nuevo).
2. **Controles negativos ×2 (pre-registrados):** off-topic sobre MC-380 (sanidad, 0 trivial) +
   **on-topic-adyacente** sobre MC-380 que DEBE alcanzar la evaluación de elegibilidad con
   candidatos presentes y rechazar por ventana/cobertura — punto de fallo verificado en trace.
   Si sirve algo, el diseño falla (no se ajusta el umbral).
3. **Census de selección con snapshots RPC VIVOS read-only** ($0 en modelos) [CENSUS]:
   freeze-contract completo (commit, sha de v4 y v5, nombre del RPC, lista de queries — 13 QIDs
   + golds dev —, versión del selector); por query: candidatos v4 vs v5 (delta de volumen por
   doc, efecto sobre overflow/truncado — interacción C3→C1 medida), elegibles, seleccionados;
   challenge de posiciones tardías; cada pérdida ADJUDICADA antes de gastar.
4. Oráculo baseline byte-inerte (perfiles ≤v3 intactos) + brazo EC intacto.
5. Probes reales cat017/cat019 (path real, $0) — adjudicados contra las reglas §2, no ajustados.
6. Smoke dirigido (~$0.5) → pasada final 13 QIDs + **hp009/hp010** (~$3; hp002 va en fixtures
   unitarios + test de convivencia con la reserve) [CONTROLES] → lectura de Alberto → merge #184
   + flip `coverage_c1_v4` = release.

## 5. Gaps declarados

1. Residual del truncado: spans más allá del cupo waterfall de su scope (visible en receipt,
   medido en census con challenge tardío).
2. La llamada RPC propia de la vía (caso lane-saltado) añade +1 GET/~2s SOLO en ese caso —
   coste declarado, medido en la pasada.
3. N_FACET=3 y todos los órdenes quedan pre-registrados sin calibrar contra el caso real (anti
   gold-tuning): el probe §5 adjudica.
4. ES-only (límite de alcance del lane, declarado arriba).
5. Cola post-release sin cambios (hp018 «en serie» — antes del merge —, hp011 «ri», hp012
   framing ES/US, FAAST doc I56).
