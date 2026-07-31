# s288b — LEVER ONTOLOGÍA de la lane hyq (v3 SELLADO; r2 Sol focused 4/4 incorporados)

**r2 (Sol focused sobre v2, 1 crítico + 3 medios, 0 FP)**: (i) el par (v4,v5) solo es
transferible CON su tercera pieza — v5 desactiva la alineación query-card porque rerank_pool
impone la barrera `_query_card`; la lane hyq DEBE adoptar la barrera equivalente (≥1 card con
query_term_hits, umbral espejo del de rerank_pool) o relajaría el gate también para los
arquetipos preexistentes; (ii) la tabla §2 se regenera con los NOMBRES EXACTOS del runtime
(la abreviada dispararía el STOP literal siempre); (iii) LANE_PAIRS necesita EXTRACTOR
(v4-retrieval = lista de objetos, el test espera mapping → TypeError sin él) + introspección
del puntero real — trabajo declarado, no «verde por construcción»; (iv) el gate-0 se RE-EJECUTA
con receipt sellado (JSON con queries+resultados committeado), no narrado.

**v2 reescribe v1 tras el dúo r1** (Sol 5 hallazgos [2 críticos] + Fable 7 [2 críticos] — CONVERGEN
en el crítico: v1 omitía el prior-art in-repo). El lever YA NO autoriza arquetipos: **la ontología
que v1 proponía crear YA EXISTE** — `intrinsic_safety` bilingüe con stems en
`config/retrieval_facets_v4.yaml:5-12` (su patrón matchea cat010 directo), `stem_prefixes` nativo
del schema (query_facets.py; v2/v4/v5 lo usan), cards para los 9 arquetipos en
`config/evidence_coverage_facets_v5.yaml`. Las piezas A y B de v1 se DISUELVEN.

## 0. LEVER v2 = CAMBIO DE PAR DE CONFIGS de `doc_scoped_hyq_coverage`
De **(retrieval v1, cards STRICT_ALIGNED=evidence v4)** → **(retrieval v4, cards evidence v5)** —
el PAR ya probado en la lane hermana `rerank_pool_coverage` (retrieval v4 + POOL_COMPLEMENT v5).
Cero ediciones a configs: v1/v2/v3/v4-retrieval y v2/v4/v5-evidence quedan **byte-INTACTAS**
(esto disuelve el crítico-2 de Fable: la paridad structural v4→v2 no se toca). MÉTRICA =
mecanismo (probe receipts, patrón F3.2); el outcome llega con la lane ON (A3). **Honestidad
DEC-163 (Sol-4): cat010#0 sigue clasificado rerank/lexical-distractor en el mapa de campaña —
este lever abre una vía de COBERTURA; no re-clasifica el miss hasta medir outcome.**

## 1. GATE-0 EJECUTADO (VERDE, 31-jul): la diana tiene material
Docs de cat010 resueltos: `IS5001-F_IS-mA1_EN` (2b694083…) + `manual IS MA1` (a6b9dc84…) —
ambos ACTIVOS + sha real (post P-A) + surrogates hyq: 48 filas (16 con padre vivo post-dedup) y
49/49. NO es doble-bloqueo clase hp013.

## 2. DIFF PRE-REGISTRADO v1→v4 (39 dev, computado ANTES del build; ESTE es el set esperado
## EXACTO — cualquier flip extra en build = STOP [Sol-2: no adjudicación post-hoc])
10 cambios / 29 sin cambio:
| qid | v1 | v4 | adjudicación pre-build |
|---|---|---|---|
| cat010 | None | intrinsic_safety | DIANA in-class ✓ |
| hp013 | None | replace_without_loss | clase conjugación («se cambia», stem `cambi`) ✓ — sigue sin-gate (surrogate PWR-R ausente) |
| cat007 | fault_reset | loop_eol_topology | re-ruteo DELIBERADO de la ontología compartida (EOL más discriminante) ✓ |
| cat008 | connect_install | loop_eol_topology | ✓ — es la pregunta RFL/47kΩ: semánticamente correcto |
| cat009 | connect_install | loop_eol_topology | ✓ |
| cat013 | connect_install | compatibility | ✓ («¿puedo usar/montar…?») |
| hp008 | None | compatibility | entrada nueva in-class ✓ |
| hp002 | None | fault_reset_recovery | entrada nueva (patrón «presenta/indica fallo») ✓ |
| hp009 | None | loop_eol_topology | ✓ CON NOTA-CENTINELA: hp009 es el centinela histórico de conducta (clarify); lane OFF hoy — el gate de A3 DEBE re-verificar hp009 antes de encender |
| cat023 | program_delay | None | PIERDE entrada — patrón conjuntivo anti-overtrigger de v4, deliberado; cat023 no es diana de campaña; ACEPTADO y declarado |

## 3. BUILD (mínimo; nada de configs)
1. `doc_scoped_hyq_coverage`: puntero de facets → v4 · puntero de cards → v5 + **barrera
   query-card espejo de rerank_pool** (r2-i: parent servible exige ≥1 card con query_term_hits
   al umbral que rerank_pool usa — leer su valor exacto y espejarlo; rechazo trazado
   `no_query_aligned_card`).
2. **LANE_PAIRS del test de paridad EXTENDIDO con el par de ESTA lane** (v4-retrieval →
   v5-cards) **+ el extractor que r2-iii exige** (v4 declara lista de objetos; el test espera
   mapping) + introspección del puntero real del módulo (no hardcodear el path dos veces).
3. **Trazabilidad del descarte sin-card** (Fable-4): `if not cards: continue` → rejection
   `no_matching_card` en `parents_rejected` (cierra el falso-«corpus», feedback_corpus_gap).
4. **Fix del probe F3.2** (Fable-4, bug confirmado en receipts: `card_excerpt_heads: [""]`):
   leer `quote` (la clave real de la card) además de excerpt/content.
5. `query_alignment_min_terms` de intrinsic_safety en v5: LEER lo que v5 declara y REPORTARLO;
   si es 0/default → adjudicar valor con nota (Fable-5) — sin editar v5 en este lever si ya
   trae valor.

## 4. GATES (post-build, $0, 39 dev only)
(1) Re-run del diff de asignación == tabla §2 EXACTA (flip extra = STOP). (2) Sintéticos
negativos: «consumo por lazo/Ah» NO captura (empírico Fable: capacity gana) + el caso-sombra
«¿cómo se cambia el retardo…?»→replace es COMPORTAMIENTO HEREDADO de v4 (las lanes hermanas
ya viven con él) — declarado, no-STOP de este lever. (3) Probe mecanismo cat010 (patrón F3.2
con fixes §3.3-4): entra + sirve parents con cards intrinsic_safety + quotes contienen
valores IS (Ui/Ii/Pi/Ci/Li o alimentación) — si sirve-sin-valor → `append_view_truncated`-class,
NO «corpus». (4) Sweep 39 de entrada a lane == tabla §2. (5) Suite completa + paridad del par
nuevo + **inertness por BYTES: sha de las 7 configs de facets sin cambio**. Freeze del probe:
receipts de lane (hyq_rows_sha256 = filas consumidas — Sol-3: fingerprint de FILAS, no
conteos) + commit + fingerprint corpus estampado.

## 5. DESCARTADAS / FUERA DE SCOPE
Autorar `power_supply_parameters` (duplicaba la ontología, mezclaba 2 clases, monolingüe —
crítico convergente r1) · enumerar conjugaciones a mano (stem_prefixes es el mecanismo nativo) ·
editar v4/v5/v2/v3 (byte-intactas) · activación de la lane / hp009-conduct / outcome (A3) ·
cat023 rescue (declarado aceptado) · surrogates nuevos (H5).

## 6. RIESGOS
1. v4 hereda sus propios trade-offs (caso-sombra retardo; cat023) — adoptados con la ontología,
   declarados. 2. hp009 en loop_eol = interacción de conducta LATENTE hasta A3 (nota-centinela
   §2). 3. `CANONICAL_HYQ_COVERAGE` es env-condicional (Railway no verificado — ship config la
   lleva off por r2-1/DEMO_FLAGS; declarado). 4. Los 16/49 padres vivos del doc EN de cat010:
   la navegación puede seleccionar padres dup-marcados de ese doc → la exclusión F2 ya los
   filtra en servidor; si la selección se queda corta se verá en el probe (no en silencio).

## 7. PROTOCOLO
r1 (ambos lados) + r2 (Sol focused) HECHOS — 16/16 confirmados 0 FP; ESTE v3 = spec sellado.
Build §3 (con: tabla §2 regenerada a nombres runtime EXACTOS pre-gates + gate-0 re-ejecutado
con receipt JSON sellado) → gates §4 (el gate 1 compara contra la tabla REGENERADA; añadir
gate 2b: sweep de CARDS sobre los 39 — ningún parent servido sin query-aligned card, el
control de falsos-appends que r2-i señaló) → tally final → DEC/digest. Stop-lines habituales;
held-out embargado.
