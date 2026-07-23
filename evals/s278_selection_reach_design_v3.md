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

---

## ADDENDUM r3 (adjudicación Sol 6 + Fable 5 — cierra el diseño; build autorizado)

**Decisión de proceso:** r3 convergió (Fable: SÓLIDA-CON-CAMBIOS-MENORES; Sol: 2 críticos que
son líneas de especificación completables). Una 4ª ronda completa sería ritual; estos 11 puntos
entran como spec vinculante y el build los pinea con tests. Contradicción factual Sol↔Fable
sobre el gate pre-fetch RECONCILIADA por regla C: ambos ciertos — el flujo ACTUAL salta antes de
derivar anchors/plan (Sol, :1377-1387 vs :1388-1427/:466-469), Y planner+anchors son funciones
locales puras re-ejecutables (Fable). Spec resultante en A2.

- **A1 [Sol#1, census]:** freeze-contract del census AMPLIADO: fingerprint de corpus
  (chunks_v2/documents — reutilizar el patrón s107_corpus_fingerprint) verificado ANTES y
  DESPUÉS de cada par v4/v5 (pares back-to-back por query; si el fingerprint cambia mid-census,
  se invalida y repite el par) + hash de la función SQL desplegada
  (pg_get_functiondef(document_local_snapshot_v3) sha256) estampado.
- **A2 [Sol#2 + Fable-verificación]:** plumbing del caso lane-saltado ESPECIFICADO: la vía
  post-composición re-deriva anchors (mismas funciones locales de
  post_rerank_coverage:1388-1427) y el plan (build_document_local_query_plan, pura) — $0, sin
  RPC — y SOLO entonces evalúa el gate; el fetch propio ocurre después si el gate pasa. El
  receipt estampa `facet_plan_rederived: true` en ese path.
- **A3 [Sol#3, attest]:** el binding de no-cobertura es la VISTA COMPLETA: sha256 de
  (ids ordenados + content-sha por fila) de la vista servida al momento de evaluación; `_attest`
  recibe la vista compuesta real, exige igualdad EXACTA del conjunto y re-verifica contenidos.
  Omitir una fila servida ⇒ attestation inválida.
- **A4 [Sol#4 + Fable#N4, orden]:** «cobertura» = GRADO entero: máx términos-distintos-de-la-
  need-group cubiertos por alguna fila servida bajo la regla de ventana (0..6). Elegible solo si
  grado < N_FACET. Orden entre grupos: grado asc → índice asc. Candidato que satisface varios
  grupos → se asigna al PRIMER grupo según ese orden. «Densidad» = span mínimo en chars que
  contiene los hits de la ventana (asc). Todo determinista, cero libertad de build.
- **A5 [Sol#5 + bordes del trim]:** trim con mínimo 1 término por grupo; si aún >480, se
  eliminan GRUPOS enteros desde el último; si la base (anchors) ya excede 480 ⇒ `plan None` con
  receipt (conducta existente). Test pinea los tres bordes.
- **A6 [Fable#N1, perfil v4]:** los 4 acoplamientos enumerados y testeados: (i) ramas
  profile-literal de validate_release_contract incluyen v4 (aislamiento de lanes +
  MUST_PRESERVE), (ii) gate `IDENTITY_RESOLVE_POLICY=replace` aplica a v3 Y v4, (iii)
  config.py exporta `DOCUMENT_LOCAL_SELECTION_V2`, (iv) mensaje de producción lista v4.
- **A7 [Fable#N2, dead-fetch]:** gate del own-fetch = «≥1 need-group NO cubierta con ≥N_FACET
  términos en el grupo»; grupos de 1-2 términos excluidos del orden y del gate.
- **A8 [Fable#N3, orden vía↔reserve]:** la vía corre DESPUÉS de `_append_obligation_warning_
  reserve` (ve la vista final, reserve incluida). Pre-registrado.
- **A9 [Fable#N5, enum]:** `facet_fetch` cubre las causas del own-fetch fallido:
  `own | reused | skipped_no_uncovered_group | skipped_no_plan | skipped_scope_overflow |
  skipped_no_anchors`.
- **A10 [Fable pins]:** el own-fetch reutiliza `TIMEOUT_SECONDS=2.0` y `MAX_HTTP_REQUESTS=1`
  del lane; el waterfall «al otro scope» queda pineado a `SOURCE_LIMIT=2` (assert en código).
- **A11 [Sol#6, wording]:** el aislamiento del §0 se afirma como EQUIVALENCIA verificada (test
  de byte-igualdad del v4 cargado por el validador nuevo + oráculo byte-inerte), no como
  no-alcanzabilidad del código común.
