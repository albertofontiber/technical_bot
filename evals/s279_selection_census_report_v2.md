# s279 — Censo de alcance de selección (document-local) — v2

Instrumento: `scripts/s279_selection_census.py`. Read-only, **0 llamadas a modelos/embeddings de pago, 0 escrituras**. El censo ADJUDICA (no calibra): aplica A4/A5/A7 y N_FACET=3 exactamente como están construidos.

## Freeze-contract (A1)

- commit HEAD: `9d26141f19d47b0b7cb21f4bd1aa42a6bc808a64` (worktree dirty: True)
- perfiles: v4=`coverage_c1_v3` (flag off) · v5=`coverage_c1_v4` (flag on)
- v4 config `config\retrieval_facets_v4.yaml` sha256-LF `fcc5aa7ade886a864cdd654757a79709136968c3d010ffde8a94dc0eae0401bb`
- v5 config `config\retrieval_facets_v5_document_local.yaml` sha256-LF `9c25664cbbf262f34767785ccb09c34b0ae3683ec24c3a5a970f0425d201dff9`
- RPC: `document_local_snapshot_v3` · functiondef sha256 `c691d094ef81e832f65a39f6107410046152ff50d3d84548c0b9fab33bfe2275` (len 17991; read-only pg_get_functiondef via Supabase SQL, project izooestgffgscdirkfia, 2026-07-23 (PostgREST cannot evaluate it; live RPC schema field re-confirmed))
- RPC schema re-confirmado en vivo: `document_local_snapshot_v3` · migración propuesta sha256-LF `aa4bf78c98798c61e09df5ac9bbf4f012371571bba877e7cea8cfacc05805290`
- selector: N_FACET=3 · FACET_COMPLEMENT_BUDGET=1 · CANDIDATE_LIMIT=64 · SOURCE_LIMIT=2
- corpus fingerprint: chunks_v2=25090 (max created_at 2026-06-09T19:15:25.848279+00:00) · documents=1171 · sha256 `aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d`
- queries: 18 · generado 2026-07-22T23:28:06.746479+00:00

## Deviaciones declaradas (honestidad > resultado)

- **D1 (provenance de anchors).** El anchor de producción sale del *reranked prefix*/structural, que exige el retrieve→rerank de pago (LLM + embedding Voyage). Bajo el contrato $0 el censo FIJA el SCOPE de forma determinista: probes → documento activo que contiene el chunk-diana; governed → ruta real `governed_source_contract`; resto → catálogo `resolved_documents` ∩ fuente del gold (revisión activa/es). El scope determina el snapshot RPC → alcance/waterfall/overflow/plan son FIELES; solo la etiqueta de ruta del anchor es proxy.
- **D2 (vista servida).** La compuerta por-faceta (A4/A7) gradúa cobertura sobre la vista SERVIDA (prefijo+coverage), también de pago. El censo corre la compuerta con vista servida VACÍA = cota superior más permisiva (todo grupo ≥N_FACET tratado como no-cubierto, grado 0). Corolario: un diana NO-seleccionado con vista vacía es definitivamente no-seleccionado (falla por alcance/elegibilidad/ranking, nunca por cobertura); un diana seleccionado con vista vacía es solo *seleccionable*.

## Probes cat017/cat019 (§4.5) — veredicto adjudicado

### cat017 — diana `b7633e98-b011-4035-9548-a564c71e70ac`
- **Veredicto: NOT_SELECTED**
- target eligible but lost intra-group ranking to a01755a8-07ee-4bfe-9ea1-2910327072ff (chunk_index 46, group 0, 3 terms)
- alcance de candidato: v4 cands=24 (overflow False) · v5 cands=29 (overflow False) · clase delta **GAIN**
- diana en v5: chunk_index 4, candidate_rank 1; terms_hit por grupo: g0(4t,gated=True)=1, g1(4t,gated=True)=None, g2(3t,gated=True)=None, g3(3t,gated=True)=3
- gate vista VACÍA (cota superior): sirvió `a01755a8-07ee-4bfe-9ea1-2910327072ff` (grupo 0, 3 términos, is_target=False)
- gate vista=ganador-del-lane (subconjunto REAL): status=`ok` → sirvió `b7633e98-b011-4035-9548-a564c71e70ac` (grupo 3, 3 términos, **is_target=True**); grades [1, 3, 0, 0]

### cat019 — diana `f68f2d40-cad2-4a0f-9045-9637928456aa`
- **Veredicto: NOT_SELECTED**
- target is a candidate but NOT eligible: no ≥N_FACET(=3) window on any A7-gated (≥3-term) need-group (max terms_hit in target=1). Per-group: ['g0(6t,gated=True):terms_hit=1', 'g1(6t,gated=True):terms_hit=None', 'g2(6t,gated=True):terms_hit=1']. Facet winner = 3d0273cf-dd42-4e48-89c3-a37e588396ca (chunk_index 88, group 2, 3 terms).
- alcance de candidato: v4 cands=0 (overflow True) · v5 cands=64 (overflow True) · clase delta **GAIN**
- diana en v5: chunk_index 14, candidate_rank 2; terms_hit por grupo: g0(6t,gated=True)=1, g1(6t,gated=True)=None, g2(6t,gated=True)=1
- gate vista VACÍA (cota superior): sirvió `3d0273cf-dd42-4e48-89c3-a37e588396ca` (grupo 2, 3 términos, is_target=False)
- gate vista=ganador-del-lane (subconjunto REAL): status=`ok` → sirvió `3d0273cf-dd42-4e48-89c3-a37e588396ca` (grupo 2, 3 términos, **is_target=False**); grades [2, 2, 1]
- reto tardío (v5, CAD-250_Manual-Configuracion-MC-380-es-2026-c.pdf): matched=81, kept=64, fuera del corte=17 (chunk_index [103, 104, 105, 108, 110, 117, 118, 121, 123, 125, 126, 127, 128, 129, 131, 133, 134])

## Controles negativos (§4.2)

### ctrl_offtopic_mc380
- query: ¿Como se configura la grabacion continua y la deteccion de movimiento en la camara CCTV Hikvision DS-2CD2143?
- v4 cands=0 · v5 cands=0 (overflow v4=False→v5=False)
- gate (vista VACÍA, cota superior): status=`None` → NO sirvió
- gate (vista=ganador del lane, cota inferior): status=`None` → **rechazó por ventana/grado** (punto de fallo verificado)
- elegibilidad EVALUADA (por grupo ≥N_FACET): n/a

### ctrl_ontopic_adjacent_mc380
- query: ¿Como se crea y configura una zona en la central Detnov CAD-250 (MC-380) y como se asignan los equipos y detectores a esa zona?
- v4 cands=0 · v5 cands=64 (overflow v4=True→v5=True)
- gate (vista VACÍA, cota superior): status=`ok` → **SIRVIÓ** id=3d0273cf-dd42-4e48-89c3-a37e588396ca (grupo 2, 3 términos)
- gate (vista=ganador del lane, cota inferior): status=`no_eligible_candidate` → **rechazó por ventana/grado** (punto de fallo verificado)
- **HALLAZGO (adjacent):** bajo la vista más permisiva el gate SIRVE una fila por-faceta para una query adyacente. Bajo la vista con el ganador del lane servido el gate rechaza (grade). La salvaguarda contra over-selección de queries adyacentes depende ENTERAMENTE de la cobertura de la vista servida REAL (D2), no observable a $0.
- elegibilidad EVALUADA (por grupo ≥N_FACET): g0(6t,gated=True):elig=0,max_hit=2; g1(6t,gated=True):elig=0,max_hit=2; g2(6t,gated=True):elig=2,max_hit=3

### ctrl_ontopic_adjacent_verbose_mc380
- query: ¿Como se cablea y se da de alta un lazo, se crea un sitio y edificio con licencia, y se programa una maniobra causa-efecto con entradas y salidas en la central Detnov CAD-250 (MC-380)?
- v4 cands=36 · v5 cands=40 (overflow v4=False→v5=False)
- gate (vista VACÍA, cota superior): status=`no_eligible_candidate` → NO sirvió
- gate (vista=ganador del lane, cota inferior): status=`no_eligible_candidate` → **rechazó por ventana/grado** (punto de fallo verificado)
- elegibilidad EVALUADA (por grupo ≥N_FACET): g0(3t,gated=True):elig=0,max_hit=1; g1(3t,gated=True):elig=0,max_hit=1; g2(3t,gated=True):elig=0,max_hit=1; g3(3t,gated=True):elig=0,max_hit=2

## Tabla por query (v4 vs v5)

Nota: la clase delta cuenta la fila por-faceta v5 con vista servida VACÍA (cota superior). Como bajo esa vista todo grupo ≥N_FACET está no-cubierto, el complemento por-faceta dispara ampliamente ⇒ **el conteo de GAIN está inflado**; la columna `facet(vacía→lane)` muestra el gate bajo ambas vistas para desinflarlo.

| qid | modo scope | v5 RPC status | v4 cands | v5 cands | Δvol | overflow v4→v5 | plan Δ | clase | facet(vacía→lane) |
|---|---|---|---:|---:|---:|---|:--:|---|---|
| cat001 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage', 'unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| cat017 | probe_target_document | fetched | 24 | 29 | +5 | False→False | sí | GAIN | sirvió→sirvió |
| cat018 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| cat019 | probe_target_document | fetched | 0 | 64 | +64 | True→True | sí | GAIN | sirvió→sirvió |
| hp002 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp003 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp005 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage', 'unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp011 | governed_source_contract | fetched | 49 | 49 | +0 | False→False | sí | GAIN | sirvió→sirvió |
| hp012 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage', 'unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp013 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp014 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp017 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp018 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp009 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| hp010 | catalog_gold_source_pinned | unverified_document_lineage ['unverified_document_lineage'] | 0 | 0 | +0 | False→False | sí | LANE_BLOCKED | no_eligible_candidate→no_eligible_candidate |
| ctrl_offtopic_mc380 | control_mc380_pinned | blocked_tsquery_unrepresentable | 0 | 0 | +0 | False→False | no | LANE_BLOCKED | n/a→n/a |
| ctrl_ontopic_adjacent_mc380 | control_mc380_pinned | fetched | 0 | 64 | +64 | True→True | sí | GAIN | sirvió→no_eligible_candidate |
| ctrl_ontopic_adjacent_verbose_mc380 | control_mc380_pinned | fetched | 36 | 40 | +4 | False→False | sí | SAME | no_eligible_candidate→no_eligible_candidate |

## Pérdidas / ganancias adjudicadas (una a una)

- **cat017 [GAIN]**: v4_sem=79faef35-68cf-4631-8e18-7d6d8ef09790 → v5_sem=79faef35-68cf-4631-8e18-7d6d8ef09790 + v5_facet=a01755a8-07ee-4bfe-9ea1-2910327072ff; gained=['a01755a8-07ee-4bfe-9ea1-2910327072ff'] lost=[]
- **cat019 [GAIN]**: v4_sem=None → v5_sem=d27aaa9e-a6e1-4245-a3f3-2cdef3f5be4c + v5_facet=3d0273cf-dd42-4e48-89c3-a37e588396ca; gained=['3d0273cf-dd42-4e48-89c3-a37e588396ca', 'd27aaa9e-a6e1-4245-a3f3-2cdef3f5be4c'] lost=[]
- **hp011 [GAIN]**: v4_sem=475a8f18-7c69-4c7a-8111-45bd67334c96 → v5_sem=475a8f18-7c69-4c7a-8111-45bd67334c96 + v5_facet=18140a8a-ab2c-40d4-a81f-2532fbe1b838; gained=['18140a8a-ab2c-40d4-a81f-2532fbe1b838'] lost=[]
- **ctrl_ontopic_adjacent_mc380 [GAIN]**: v4_sem=None → v5_sem=3d0273cf-dd42-4e48-89c3-a37e588396ca + v5_facet=3d0273cf-dd42-4e48-89c3-a37e588396ca; gained=['3d0273cf-dd42-4e48-89c3-a37e588396ca'] lost=[]

## Hallazgos estructurales inesperados

- **H0 — la maquinaria s279 (C1/C2/C3) es INALCANZABLE para la mayoría del set P1 por una compuerta de identidad AGUAS ARRIBA, ajena a la lógica de selección.** Con anchors CHUNK-derivados (fieles a producción), de los 15 QIDs no-control medidos (13 P1 + hp009/hp010) el RPC resuelve autoridad para solo ['cat017', 'cat019', 'hp011'] = 3 documentos servibles (los 2 docs-probe con el data-fix de identidad s278 + el doc RP1r del contrato gobernado). Los otros 12 son rechazados por el RPC con ['unverified_document_lineage'] (0 candidatos en ambos brazos ⇒ `LANE_BLOCKED`, NO «SAME»). Bajo ese rechazo uniforme hay DOS estados de identidad de corpus PRE-existentes (auditados read-only, `scope_identity_audit` en el JSON): (a) **['cat018', 'hp002', 'hp003', 'hp005', 'hp009', 'hp010', 'hp012', 'hp013', 'hp018']** con `source_pdf_sha256='backfill:*'` (placeholder, no 64-hex) + language/doc_type NULL; (b) **['cat001', 'hp014', 'hp017']** con blob/idioma/doc_type completos pero lineage con `authority_status != 'verified'`. En AMBOS el gate proximal del RPC es `unverified_document_lineage`. → Los levers de selection-reach solo pican donde el documento está identity-completo Y lineage-verificado (hoy = 3 docs). El unlock real es un backfill de identidad + verificación de lineage más amplio, NO un ajuste de C1/C2/C3.

- **H1 — el lever `commissioning_setup` de C3 nace muerto para su propio diana (cat017).** El arquetipo v5 se añadió (design §3) para recuperar el gap CLSS «crear sitio/edificio + licencia .bin». Su need declara 6 términos (sitio/edificio/licencia/bin/alta/portal), pero: (i) `alta` es token de la query → excluido del grupo; (ii) el trim A5 (round-robin desde el ÚLTIMO grupo) retira PRIMERO `portal`, `bin`, `licencia` — los tokens que el propio design verificó contra el chunk-diana. Resultado: el grupo llega a la compuerta como [] (<N_FACET=3), que A7 EXCLUYE del gate por definición, y cuya elegibilidad (ventana ≥3 términos distintos) es inalcanzable con solo 2 términos. El diana b7633e98 SÍ contiene sitio+edificio (terms_hit=2), pero 2<3. Trim aplicado: terms_removed=[{'group_index': 3, 'term': 'portal'}, {'group_index': 2, 'term': 'safety'}, {'group_index': 1, 'term': 'shield'}, {'group_index': 0, 'term': 'polarity'}, {'group_index': 3, 'term': 'bin'}, {'group_index': 2, 'term': 'limits'}, {'group_index': 1, 'term': 'circuito'}, {'group_index': 0, 'term': 'terminals'}, {'group_index': 2, 'term': 'instalacion'}]. → El lever no puede disparar por construcción para su caso objetivo; N_FACET no es el único bloqueo (el techo de terms_hit del grupo ya es < N_FACET).
- **H2 — C1 (waterfall) SÍ recupera alcance de candidato en cat019, pero no el span-diana vía facet.** v4 descarta el scope MC-380 entero por overflow (0 candidatos); v5 conserva 64 (matched total=81, fuera del corte=17). El diana f68f2d40 (chunk_index 14) sobrevive (candidate_rank 2), PERO su ventana tiene terms_hit≤1 para todo grupo → NO elegible (N_FACET=3). La ganancia de C1 es real a nivel de POOL; la vía por-faceta no convierte esa ganancia en el span-diana. La recuperación de cat019 dependería del selector SEMÁNTICO (no medido a fondo aquí) o de bajar N_FACET (NO se toca).
- **H3 — la fila por-faceta dispara casi universalmente bajo vista servida vacía.** Es un artefacto de la cota superior (D2), no una ganancia de producción: con la vista = ganador del lane, varias disparadas se convierten en `skipped_no_uncovered_group`. Toda lectura de «GAIN por-faceta» debe leerse contra la columna `facet(vacía→lane)`.

## Totals

- queries: 18 · medidas: 18 · sin scope $0: 0 []
- clases delta: {'LANE_BLOCKED': 13, 'GAIN': 4, 'SAME': 1}
- scopes en overflow (v5): 2
- probes: {'cat017': 'NOT_SELECTED', 'cat019': 'NOT_SELECTED'}
- controles (sirvió bajo vista vacía / vista=lane): {'ctrl_offtopic_mc380': {'empty': False, 'lane_served': False}, 'ctrl_ontopic_adjacent_mc380': {'empty': True, 'lane_served': False}, 'ctrl_ontopic_adjacent_verbose_mc380': {'empty': False, 'lane_served': False}}
- fila por-faceta disparó: vista vacía 4/18 · vista=lane 3/18 (desinflado)
- fingerprint estable en todos los pares: True
