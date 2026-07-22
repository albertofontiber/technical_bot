# s278 — Diseño vNext: cerrar los 29 FAIL de la P1 `b92ff51` (v1, PRE-dúo)

**Estado:** BORRADOR para revisión adversarial (Protocolo 3: Fable + Sol). NO cablear antes del dúo.
**Gobernanza:** DEC-148 (Alberto, 22 jul 2026) — se conserva el trabajo s277, se desmonta la
ceremonia procesal. Verificación = tests + oráculo offline ($0) + una pasada de harness (~$3) +
Alberto mira y mergea. Sin segundo gate de receipts, sin P1 ceremonial nueva.
**Insumos:** `docs/HANDOFF_P1_B92FF51_2026-07-22.md` §5/§8 (mapa de los 29 FAIL + fuentes exactas) ·
census s278 (`evals/s278_identity_census_report.md`, verificado adversarialmente: CONFIRMADO con 2
salvedades de lectura) · DEC-147 (split causal).

## 0. Objetivo y criterio de éxito

Los 29 FAIL son ítems semánticos reales sobre 13 preguntas (17/27 respuestas con ≥1 fallo).
Criterio de cierre de la release C1 (nuevo, DEC-148):

1. Oráculo offline sobre commit limpio: **62/62 PASS preservados + 93/93 checks + los FAIL
   postgeneración corregidos** (subset del oráculo; ver §6 — el oráculo NO puede acreditar fixes
   de fuente/contexto).
2. Suites verdes (los 4 fallos raw-hash/CRLF Windows conocidos no cuentan).
3. **Una pasada de harness pagada (~$3)** sobre los 13 QIDs → lectura humana de Alberto.
4. Merge #184 + flip de `COVERAGE_RELEASE_PROFILE` en Railway = release (decisión de Alberto).

## 1. Identidad determinista (hp018:r1 — 5 FAIL)

### 1a. Política `replace` con guard estructural de miembros-candidate
El census (845 unidades) mostró: `replace` no vacía ni pierde familia consumible en ningún caso
medible catálogo-side; los drops reales (ZXe→MIE-MI-310, CAD-150→CAD-150R, B500→SMB500) son
exactamente la clase del bug hp018. El único agujero real: **umbrella con miembro `candidate:true`**
(FAAST/faast-8100e, Dimension/dx*e) — la expansión filtra el candidate y bajo `replace` sus docs
quedan inalcanzables por la vía de identidad.

**Diseño:** `IDENTITY_RESOLVE_POLICY=replace` global PERO con guard estructural en la resolución:
un token de umbrella solo entra en `drop_tokens` si **todos** sus miembros declarados son
consumibles (candidate:false + activo). Si algún miembro es candidate → fail-open para ESE token
(se conserva el token, comportamiento `add` local). Data-driven, sin hardcode por familia, escala a
catálogo imperfecto (30+ fabricantes). Las 3 adjudicaciones de datos de Alberto (FAAST, ZXR
membership, G-100-R alias-vs-paraguas) LIMPIAN los datos cuando lleguen; el guard queda.

- Regresiones existentes que deben seguir verdes: `test_zxe_replace_expulsa_legacy_zxae_zxee_y_conserva_familia`,
  `test_hp009_replace_conserva_match_family_level`, `test_brazo_replace_retira_el_paraguas`.
- Nuevas: guard candidate-member (FAAST no dropea), umbrella limpia sí dropea, homónimo prefer
  (RP1r) intacto.
- Flip del env en Railway/demo: `IDENTITY_RESOLVE_POLICY=replace` — reversible (var).

### 1b. Determinismo + autoridad en `content_search` (el `LIMIT` sin `ORDER BY`)
El plan físico podía decidir qué manual entra (mecanismo probado del hp018:r1). El orden alfabético
solo estabiliza; NO selecciona autoridad (handoff §8.1).

**Diseño:** over-fetch + rank de autoridad + corte:
1. `LIMIT` interno sube (10→40) — over-fetch barato;
2. rank determinista ANTES del corte final: (i) lifecycle del documento (activo > superseded,
   vía documents si la señal existe; si no existe para el doc → neutro, fail-open), (ii) desempate
   estable `source_file, page_number, id`;
3. corte al tamaño original DESPUÉS del rank.
El paso (ii) garantiza determinismo aunque (i) sea neutro. Sin DDL; solo query/código + tests con
negativos multi-revisión (v.04 vs v.07 de hp011 como fixture — ya hay lifecycle aplicado DEC-144).

## 2. Catálogo INSPIRE (cat017 — 2 FAIL) + detectabilidad (hallazgo census)

### 2a. Gobernar las 7 identidades INSPIRE
Data-only (`data/catalog/*.jsonl`): products `notifier:inspire-e10`/`notifier:inspire-e15` +
aliases (`E10`, `E15`, `INSPIRE E10`, `INSPIRE E15`, `Notifier INSPIRE E10/E15`) + umbrella
`INSPIRE → {e10, e15}` + `doc_map` binding al doc `80e1b7d2` (HOP-138-8ES issue 6, la fuente exacta
del `.bin`/licencia ya viva). La puerta `gold_store`/catalog_store valida. Nota honesta del
handoff: el catálogo NO es el arreglo completo de cat017 (el snapshot v2 también rechaza el doc
por lineage NULL → §4); pero sí es la mitad retrieval (detect() deja de dar []).

### 2b. Los 58 aliases gobernados-indetectables (bug de datos/regex, hallazgo s278)
La clase separadora `_SEP=[-\s/.+]` no cubre `( ) , : _ ° – −` → 57 aliases + umbrella con
stopword no matchean su propia superficie. **Diseño:** extender la normalización del builder del
patrón para que cada alias elegible genere una superficie matcheable (escape de puntuación o
normalización a separador), + **round-trip test sobre TODOS los alias detector-elegibles** (hoy
solo muestrea canonicals — por eso no estaba pineado). Riesgo FP: paréntesis/comas son frecuentes
en texto libre → el round-trip se acompaña de un negative-set (frases sin el alias no deben
matchear). Si un alias resulta intrínsecamente ambiguo → se excluye CON registro (no silencioso).

## 3. Reserva obligation-aware (hp002 — 1 FAIL)

El chunk warning (ASD535 p121, `5b6a3a19`) estaba en el pool de r1 (#28) y no se sirvió: la
puerta de 6 términos de `_query_card` dejó `eligible_rows=0` y pool-coverage corre tarde bajo el
cap global de 4 appends. **Diseño (handoff §8.3, sin cambios de fondo):** reserva de MÁXIMO 1
callout de warning, solo para preguntas procedimentales/diagnósticas, en scope canónico del doc
servido, ANTES del cap global (presupuesto propio de 1), revalidando el chunk exacto. Negativos:
pregunta no-procedimental, cross-family, control hp009. Flag propio default-off hasta el gate.

## 4. Autoridad/lineage cat019 (2 FAIL) — code-side primero

El span está vivo (`f68f2d40`, CAD-250 MC-380 p10, offsets [2699,3008)). Bloqueos reales:
1. **Identidad de blob:** `documents.source_pdf_filename` = `...-c.pdf` vs chunks/doc_map `...-c`
   (sin extensión). Fix CODE-SIDE: comparación canónica fail-closed (strip de extensión declarado
   en UN sitio, con test de tampering) — NO relajar igualdad en general, NO tocar DB.
2. **`doc_type`/lineage NULL:** la cadena predecessor→active existe (S64/DEC-045). El snapshot v2
   rechaza `unverified_document_lineage`. Fix mínimo: el verificador acepta lineage cuya cadena
   esté completa y hasheada aunque `doc_type` sea NULL **si** el resto de la attestation cuadra
   (declarándolo en el receipt como `doc_type_null_accepted`), O un data-fix de 2 filas en
   Supabase (UPDATE doc_type) — decisión en el dúo; default = code-side (sin mutación live).
3. **Serving de prosa:** el serving actual solo admite `markdown_pipe_row_v1`. Se añade un source
   card de PROSA general: atestado por documento+extracción+source+chunk+content-hash+quote-hash
   y bounds, selección complementaria (nunca lookup por QID). Es la pieza que comparte mecánica
   con el Evidence Contract (§5) — se diseña como el mismo primitivo de "span atestado".

## 5. Evidence Contract v1 (los ~17 FAIL de omisión post-fuente)

Nueva versión default-off y byte-inerte off (no muta `coverage_c1_v1/v2`). Runtime SIN QID/gold.

**Mecanismo (2 fases sobre el seam actual del generador):**
- **Pre-writer (reserva):** del contexto servido se construye un ledger de obligaciones por clase:
  `safety/mandatory` (warnings, bloqueos, avisos) · `procedure/precondition` ·
  `relation/table` (filas/columnas ligadas a la pregunta) · `attribution/conflict`
  (valores por región/documento que difieren) · `universal/compound` (cualificadores AND/rangos) ·
  `arithmetic` (derivaciones trazables, p.ej. 4×(99+99)=792 SOLO si ambos operandos están en la
  fuente y la derivación se declara). Spans de alta obligación se reservan y agrupan adyacentes.
- **Post-writer (validación fail-closed):** cobertura de las obligaciones aplicables, cita local
  inline válida (hp005), disclosure de conflicto declarado-vs-enumerado (hp017 "seis vs siete"),
  detección de contradicción. Solo puede ANEXAR afirmaciones exactas ligadas a fuente (verbatim
  span + cita) o marcar `disclose`/`abstain` — nunca parafrasear sin ancla. Un único writer;
  verifier inicial `accept | clarify | disclose | abstain`.
- **Reuso multi-turn (DEC-136):** el verifier y el ledger se diseñan transport-neutral, sin estado
  conversacional ni DDL — el orquestador futuro los consume tal cual.

**Cobertura honesta sobre esta P1 (handoff §8.5):** 12/29 con evidencia directa ya servida + 5/29
compuestos + 2/29 aritméticos trazables = techo ~19/29 desde postgeneración; el resto (~10) son
los fixes de fuente §1-§4. NO prometer 29/29 desde el contrato.

**Familias ya medidas que NO se repiten** (LEVER_DIGEST/DEC-147): checklist S206 genérico ·
multiwriter S216 · writer frontera · full-answer revision S219-221 · enforcement S122 a ciegas ·
flags must-preserve DEC-134 (familia exhausta). El Evidence Contract se diferencia: opera sobre
EVIDENCIA FUENTE (spans/hashes), no sobre checklist de la pregunta ni reescritura libre; es
append-exacto/fail-closed, no revisión. El dúo debe atacar exactamente esta distinción.

## 6. Verificación por tramo (qué instrumento acredita qué)

| Tramo | Instrumento | Coste |
|---|---|---|
| §1a/§2a/§2b (catálogo/resolver) | tests + census re-run (offline) | $0 |
| §1b (determinismo/autoridad) | tests con fixtures multi-revisión | $0 |
| §3/§4 (reserva/serving) | tests + probes GET read-only si hace falta | ~$0 |
| §5 (postgeneración) | **oráculo offline** (62/62+93/93 + FAILs postgen corregidos) | $0 |
| Fixes de FUENTE (§1-§4) e2e | el oráculo NO los ve (contexto congelado) → **pasada harness 13 QIDs** | ~$3 |
| Cierre | lectura de Alberto + merge #184 + flip Railway | — |

## 7. Gaps declarados

1. El oráculo offline no acredita fixes de contexto (limitación intrínseca del seam congelado);
   la pasada de harness final es el árbitro e2e y NO es réplica-exacta de la P1 (sin fence).
2. `doc_map` cubre 861/1014 docs → el guard §1a protege catálogo-side; un doc sin fila doc_map
   con tag paraguas-forma en DB puede seguir perdiéndose bajo replace (infra-contado; el harness
   final lo detectaría en los QIDs medidos, no en general).
3. Las 3 filas de datos del census esperan adjudicación de Alberto; el guard §1a las hace no-bloqueantes.
4. Coste Sol del dúo (~$1-3) entra al ledger provisional (spent_so_far documentado ≈$9,86 + rondas
   s277 sin importe; techo 100).
