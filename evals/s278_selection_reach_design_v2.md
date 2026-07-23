# s278/s279 — Diseño: alcance de selección del lane document-local (v2, POST-dúo r1)

**Estado:** v2 tras adjudicar el dúo r1 (Sol 8 + Fable 9; C1 sólida-con-cambios, C2/C3
NO-sólidas — `evals/s278_selection_reach_duo_r1_adjudication_v1.yaml`). Incorpora los 11 fixes.
PENDIENTE dúo r2 antes de build. Gobernanza: decisión B de Alberto (DEC-151, release retenida).
**Métrica:** ítems P1 de cat017 (sitio/edificio+.bin, chunk `b7633e98` p5) y cat019 (span
«sirenas o módulos de control», chunk `f68f2d40` p10 [2699,3008)) servidos; no-regresión de
clases existentes; oráculo baseline byte-inerte; controles hp009/hp002 + control negativo nuevo.
**Precondición cumplida:** compuerta de DATOS cerrada (DEC-150/151: 7 docs identity-complete,
RPC v3 canónico vivo, flip Python hecho).

## Compuerta 1 — truncado combinado determinista del overflow (fix F4+sol#7+sol#4)

**Mecanismo (respecificado):**
- Por-scope: si el RPC devuelve `candidate_limit+1` filas (=señal de overflow), el cliente
  CONSERVA el scope con sus primeras `candidate_limit` filas (orden `chunk_index` que el RPC ya
  garantiza) en vez de descalificarlo. Receipt: `candidate_truncated: true`,
  `observed_rows: >=65` (el RPC no expone totales — decisión explícita: SIN cambio SQL; el
  lower-bound es honesto, adjudicación RPC-SIN-TOTALES).
- **Combinado (F4):** `TOTAL_CANDIDATE_LIMIT=64` deja de ser descalificación total. Reparto
  determinista por scope: `floor(64/n_scopes)` filas por scope en orden estable de autoridad
  (source_file asc), resto de cupo al primer scope; dentro de cada scope, orden `chunk_index`.
  Con SOURCE_LIMIT=2 ⇒ 32/32. cat017 (HOP-138-8ES + 9ES) queda cubierto por construcción.
- **Sesgo declarado (sol#7):** el corte por `chunk_index` favorece el inicio del manual. Es el
  patrón determinista aceptado (vNext §1b) y el residual es MEDIBLE: el census (§Verificación)
  incluye el challenge de posiciones tardías (spans objetivo sintéticos en p>64ª fila) y estampa
  cuántos candidatos quedan fuera por doc. NO se promete recall total; se promete visibilidad.
- Fail-closed conservado donde protege: attestation por-fila intacta; `plan is None` (tsquery
  irrepresentable) sigue apagando el lane CON receipt visible (`blocked_tsquery_unrepresentable`).

**Ficheros:** `document_local_coverage.py` (:724-781 overflow por-scope; :53/:766-768/:1132-1134
cap combinado). Constantes nuevas: ninguna (64 se mantiene; cambia la semántica de exceso).

## Compuerta 2 — vía complementaria por-faceta con PRESUPUESTO PROPIO (fix F3+F5+F6)

**Mecanismo (respecificado — patrón reserve DE VERDAD):**
- La vía por-faceta NO compite dentro de `MAX_APPENDED=4` ni toca `APPEND_LIMIT=1` del lane:
  presupuesto propio `FACET_COMPLEMENT_BUDGET=1` (máx 1 fila por RESPUESTA, no por faceta),
  espejo exacto de `OBLIGATION_WARNING_RESERVE_BUDGET` (`post_rerank_coverage.py:122-124`).
  Aritmética declarada: vista servida = rerank top-k + ≤4 (cap global) + ≤1 (reserve hp002)
  + ≤1 (facet complement). Cero desplazamiento posible por construcción; el coste es +1 fragmento
  máximo (medible en la pasada).
- **Elegibilidad (pre-registrada AQUÍ, antes de todo probe — F5):** candidato elegible-por-faceta
  si su mejor ventana de 360 chars cubre **N_FACET=3 términos DISTINTOS de UNA MISMA need-group**
  del plan Y esa need-group no tiene ya cobertura ≥3 en la vista servida (criterio de "cubierta":
  la misma regla de ventana aplicada a las filas ya servidas).
- **Regla de ranking (pre-registrada — F5):** entre elegibles de la misma need-group:
  `terms_hit` desc → densidad (terms_hit / longitud de ventana usada) desc → `chunk_index` asc.
  Sin excepciones ni pesos tuneables. Si el probe real no selecciona el span esperado, la regla
  NO se ajusta: se reporta el resultado y se adjudica (anti gold-tuning, gap #1 del v1).
- **Attestation distinguida (F6):** la fila por-faceta se estampa
  `facet_complement_validated: true` + `facet_eligibility: {need_group_index, terms_hit,
  window_bounds}` — NUNCA `local_semantic_validated` (esa vara es del gate-6). El receipt
  downstream (`_attest`) verifica la clase correcta; la prose_source_card sobre fila por-faceta
  hereda TODOS los checks del dúo r2 de §4 (prosa-idad positiva incluida — sin burla del
  anti-fila-parcial).
- **Stemming-gate (F9):** el gate cliente es token-exacto foldeado; los términos de need-groups
  nuevos se eligen contra las superficies REALES de los chunks objetivo (p.ej. `licencia`,
  `sitio`, `edificio`, `bin`, `alta`, `configuracion` — verificar formas exactas en el build,
  declarando en el config las variantes de superficie dentro del cap-6).

**Ficheros:** `rerank_pool_coverage.py` (vía de elegibilidad por-faceta junto a `_query_card`),
`post_rerank_coverage.py` (presupuesto propio + attest de la clase nueva),
`document_local_coverage.py` (receipt). Flag: la vía vive bajo el lane document-local ya
perfil-gobernado (v3) — sin flag nuevo; off ⇒ inerte por el perfil.

## Compuerta 3 — facetas multi-match SOLO en el path del lane (fix F1+F2+F7)

**Mecanismo (respecificado):**
- **Fork versionado (F2):** fichero NUEVO `config/retrieval_facets_v5_document_local.yaml` =
  v4 byte-copiado + arquetipo `commissioning_setup` + `multi_match: {enabled: true, max: 2}`.
  `retrieval_facets_v4.yaml` queda BYTE-INTACTO y sigue siendo lo que consumen pool, structural,
  hyq y el propio lane con la vía OFF. SOLO el path flag-gated del lane document-local carga v5
  (import condicional, patrón config-por-vía). `query_facets.expand_query_facets` gana un modo
  `multi_match` explícito (parámetro, default first-match — firma retrocompatible; el enforcement
  first_match actual queda para v4).
- **Cap por-vía (F1):** `MAX_NEED_GROUPS` NO cambia globalmente. El path v5 usa
  `MAX_NEED_GROUPS_MULTI=5` (3 primaria + ≤2 del segundo arquetipo) SOLO al construir el plan
  del lane. Guardas medidas: el `need_clause` de pares con 5 grupos = 10 pares — test obligatorio
  `plan is not None` (MAX_TSQUERY_CHARS=480) para los 13 QIDs + los controles con v5 activa; si
  algún plan cae a None, el build DEBE recortar términos por grupo (no subir el límite de chars)
  y re-testear.
- **Census OBLIGATORIO (F7 — resuelto por código, no opinión):** multi-match cambia el tsquery
  de toda query multi-tema ⇒ paso obligatorio del build: census de selección con pools/fixtures
  congelados ($0) comparando v4-solo vs v5-en-lane sobre TODAS las queries del set (13 QIDs +
  golds dev): qué scopes/candidatos/elegibles cambian, con clasificación estable/mejora/pérdida
  y adjudicación de cada pérdida ANTES del smoke pagado.

## Verificación (escalera completa, con los controles nuevos)

1. Tests unitarios por compuerta + los obligatorios del dúo: `plan is not None` ×13 QIDs con v5;
   reparto 32/32 del truncado combinado; presupuesto propio no desplaza (fixture con 4 huecos
   consumidos + reserve + facet ⇒ 6 fragmentos, ninguno expulsado); attestation
   `facet_complement_validated` ≠ `local_semantic_validated`; prosa sobre fila por-faceta pasa
   los negativos del dúo r2 §4.
2. **Control negativo nuevo (F6):** query fuera-de-tema sobre MC-380 con las 3 compuertas ON ⇒
   0 filas por-faceta servidas (pre-registrado: si sirve algo, el diseño falla — no se ajusta el
   umbral para que pase).
3. Census de selección $0 (obligatorio, F7) + challenge de posiciones tardías (F4/sol#7).
4. Oráculo baseline byte-inerte (perfil off) + brazo EC intacto.
5. Probes reales cat017/cat019 (path real, $0): el span p10 y el chunk p5 elegibles y servidos
   — resultado ADJUDICADO contra la regla pre-registrada, no ajustado.
6. Smoke dirigido (~$0.5) → pasada final 13 QIDs+hp009/hp010 (~$3) → lectura de Alberto →
   merge #184 + flip = release.

## Gaps declarados

1. El reparto 32/32 puede dejar fuera un span tardío de un doc grande cuando hay 2 scopes
   (residual del truncado, visible en receipt y medido en census).
2. N_FACET=3 y el ranking quedan pre-registrados SIN probar contra el caso real todavía — a
   propósito (anti gold-tuning): el probe §5 adjudica, no calibra.
3. `MAX_NEED_GROUPS_MULTI=5` puede acercar tsqueries al límite de 480 chars en queries verbosas;
   el test §1 lo caza y el recorte declarado es por-términos, no por-límite.
4. La cola post-release NO cambia: hp018 «en serie» (mirar antes del merge), hp011 «ri»,
   hp012 framing ES/US, FAAST doc I56.
