# s103 — Diseño «displacement-landing» v2.1 — **VEREDICTO: NO-GO (gate pre-declarado, medido same-day)**

> **RESULTADO (9 jul 2026, judge-free, A/B same-day old@29695cf vs fix):** el mecanismo hace
> EXACTAMENTE lo diseñado y el gate falla en 3 de sus puntos → revertido por pre-registro
> (seam reproducible: `evals/s103_displacement_seam.patch`; artefactos `s103_displacement_*`).
>
> | Gate | Resultado |
> |---|---|
> | 1 diana | cat022 **3/3 recuperados** ✅ · hp018 p21 ❌ (es cola-vectorial: el precio del canal por diseño; tampoco estaba bajo old) |
> | 2a anclajes (109 facts, 39 golds) | +1/−0 ✅ (null 0/0) |
> | 2b composición ganados | **hp011 FUERA del null** (3 served-v2.2 evictados; null 0/0) ❌ · hp015 dentro (jitter) |
> | 3 negcontrol | **EXCESS-HIGH 7→9 (4→6 golds), SUBE** ❌ (esperado: bajar; cat021 ganado con excess rank 21) |
> | 3b trim-rate | hp018 REAL 5→2: cortó el surrogate 6K8 (0.454 vs 0.457, 3 milésimas) — la sim-pregunta no ve valor |
> | 4 flips shippeados | cat016 ✅ · **hp018·6K8 PERDIDO → rompe el gate de aceptación DEC-099** ❌ |
> | 6 pytest | 466 verdes con fix; 462 baseline post-revert ✅ |
>
> **Lección estructural (lo que este NO-GO compra):** los 50 slots los paga alguien SIEMPRE; los
> 4 ejes observables en el pipeline — canal (v2.1), score (r1), sim-pregunta (trim 6K8), posición
> de interleave (negcontrol↑) — son TODOS ciegos al valor. El único discriminador restante en
> esta etapa es FAMILIA/identidad: en hp018 la cola protegida era junk cross-family (MIE-MI-310)
> y en cat022 la cola desplazada era gold same-family (MNDT72x). → **El landing correcto es
> family-aware y su prerequisito es el entity-linking (DEC-074): primer consumo medible del
> workstream §3 del plan s103.** cat022×3 queda como clase objetivo PROBADA recuperable
> (chunk-level 3/3) — el target del lever era correcto; el eje del landing, no.
>
> ⚠ ANTI-OVERFIT (G4, declarado): la iteración apuntó a los 6 diana de los MISMOS golds dev que
> midieron el canal; el NO-GO viene de los CONTROLES amplios (negcontrol 39, flips, null) — el
> guardarraíl funcionó exactamente como se diseñó.

## (histórico) Diseño v2.1 (post-dúo r1+r2) — tal como se cableó y midió

**Veredicto del dúo:** r1 (v1) = CABLEAR-CON-CAMBIOS ×2 lados → v2; r2 (v2) = CABLEAR-CON-CAMBIOS
×2 lados, convergentes → v2.1 (este doc). Total 14 findings, 0 falsos positivos (tally en
`evals/adversarial_review_log.jsonl`). Nota de tiering (Alberto s102 validada en vivo): el
sub-agente r2 REPITIÓ la cita errónea `:2456` del sub-agente r1 y fue el cross-model quien la
corrigió — mismo-árbol = mismo blind spot.

## Contexto (diagnóstico medido s102 — el canal hyq está SHIPPEADO, no se re-litiga)

- **Descuento 1 (correcto, medido)** — `retriever.py:1010`: la cuota compra la cola del PROPIO
  canal vectorial, por RANK.
- **Descuento 2 (el bug)** — `retriever.py:1615`+`1626`: presupuesto del diversify reducido →
  doble apretón (slots del interleave + `max_per_source`, `:2423`) → pierde PROFUNDIDAD del
  doc-respuesta. Factura v2.2 (matriz `evals/s103_transition_matrix.json`): **5 hechos
  chunk-level** (cat022#0/#1/#2 + hp018#2/#3 — chunks verificados: MNDT723 p58/p10, MNDT722
  p14, MIE-MI-530 p21) **+ 1 de composición** (hp018#0, in_pool:true, muere en síntesis por
  composición servida — se VIGILA, no es evidencia chunk-level; corrección r2 cross-model).

## Mecanismo v2.1

En Step 5a (`retriever.py:1612-1626`):

1. **Diversify a `top_k` COMPLETO** (interno INTOCADO, consenso s59 ×2).
2. **Pre-truncado** `merged = merged[:top_k]` antes del shortfall. Rutas oversize reales:
   early-returns `:2314`/`:2337` + merge `stamps` ignora `cap` (`:1123-1138`) + `vector_search`
   a `effective_top_k` (`:1414`). (La cita `:2456` de r1 era errónea — el while garantiza
   `result ≤ top_k`; corrección r2 cross-model.)
3. **Eviction por POSICIÓN DE COLA** (desde el final hacia arriba), candidato =
   `_channel=='VECTOR'` **∧** no `_hyq_boosted` **∧** no `_swapped_from_surrogate` **∧**
   **su `source_file` tiene ≥2 chunks en el pool actual** (contrato sole-representative,
   convergencia r2 ×2: la versión "G1-safe de fábrica" era sobre-claim en pools
   protected-heavy / n_sources grande / model-filter fail-open). Guard `if c.get("id")`
   (r2 sub-agente F3). Sin knobs: es contrato, no parámetro.
4. **Fallback: TRIM del aside** (peores sim-pregunta fuera) si faltan candidatos. La cuota
   jamás desplaza canales no-vectoriales; si no hay cola vectorial elegible que pague, se
   encoge — y el gate MIDE ese encogimiento (trim-rate, abajo), porque un aside que muere en
   silencio satisfaría trivialmente el negcontrol (r2 sub-agente F2).
5. Dedup aside-gana intacto (fix #1 dúo s102).

Matices declarados (r2): el marcador `_hyq_surrogate`/`_hyq_boosted` solo es determinista en la
copia VECTOR — un dual pierde el stamp hyq en el dedup keyword-first, pero la copia superviviente
tiene `_channel!='VECTOR'` → protegida igual (F4). Path duplicado hyq×enunciados pre-existente:
v2.1 no lo empeora (F5, info).

## Alternativas descartadas

- **A1 sin carve-out:** anula el canal (medido s102: hp018·6K8 RECALL→DIVERSIFY). 
- **A2 crecer el pool:** contradice la competencia-de-slots MEDIDA por el negcontrol del piloto
  (no "viola el contrato de tamaño" — el identity-fetch ya extiende acotado, `:1643-1667`).
- **A3 proteger surrogates dentro del diversify:** consenso s59 ×2.
- **A4 eviction por score:** escalas incomensurables (`:1328-1331` swap, `:999` boost); en
  pools oversize arrasa el canal vectorial (r1 CRÍTICO).
- **A5 fallback cola global:** scores incomensurables + empates de stamp evictan mejor-rankeados
  (sort estable). Sustituido por trim-aside medido.

## Gaps / riesgos

- **G1 (contrato, no claim):** sole-reps protegidos por construcción vía la 4ª condición del
  candidato. Test explícito protected-heavy.
- **G2:** `_hyq_boosted` excluidos (marcador `:1000`).
- **G3:** bajo `quota` el dual conserva registro VECTOR (`:1112`) — inerte en prod (stamps).
- **G4 — ANTI-OVERFIT FLAG (obligatorio a Alberto):** iteración sobre los MISMOS golds dev que
  midieron el canal. Contrapeso: negcontrol 39 + famtie + trim-rate, no solo los 6 diana.
- **G5 (ampliado r2):** el trim dispara cuando #candidatos < n_evict — incluye pools swap-heavy
  (ENUNCIADOS on en demo) y boosted-heavy, no solo keyword-dominados. Medido explícitamente
  (gate 3b) + flips shippeados vigilados (gate 4).

## Gate (declarado ANTES de cablear; base `evals/s103_transition_matrix.json`)

1. **Probe chunk-level judge-free** (patrón `s102_hyq_negcontrol_table.py:_pool`, actual-vs-fix):
   los chunks desplazados (cat022: MNDT723 p58/p10, MNDT722 p14; hp018: MIE-MI-530 p21) vuelven
   al pool-50.
2. **5 diana chunk-level** mejoran su in_pool; **hp018#0** se vigila vía composición servida.
   Composición de los golds de los 12 ganados: dentro del null OFF-vs-OFF.
3. **Negcontrol re-run:** EXCESS-HIGH ≤ v2.2 (esperado: baja). **3b (r2):** distribución
   `n_hyq_in_pool` + **trim-rate** actual-vs-fix en los 39: trim-rate esperado ≈0; trim en >2
   golds = investigar ANTES de ship (el aside no puede morir en silencio).
4. **Famtie amplio** + flips shippeados vivos (cat016·autobúsqueda, hp018·6K8).
5. **Config-stamp exhaustivo en cada artefacto** (r2): git SHA + CHUNKS_TABLE + MERGE_STRATEGY +
   ENUNCIADOS_MULTIVECTOR + HYQ_TABLE + HYQ_PILOT_FILE + NEIGHBOR_WINDOW + IDENTITY_RESOLVE/
   POLICY/FETCH + RPC_SUFFIX + RERANK_TOP_K + RERANKER_BACKEND + LLM_MAX_TOKENS.
6. `pytest -q` verde. **bvg + assessment (smoke→full, fila scoreboard) SOLO si 1-5 pasan.**

## Tests

- `test_hyq_channel.py:190` invertido: diversify recibe `top_k` completo; aside fuera, boosted dentro.
- NUEVO pass-through mixto oversize: top-coseno VECTOR sobrevive; eviction solo cola; pool ≤ top_k.
- NUEVO exclusiones: boosted/swapped en cola no se evictan.
- NUEVO contrato sole-rep: el único VECTOR de un source NO se evicta (cae al siguiente candidato).
- NUEVO protected-heavy: sin candidatos suficientes → trim del aside (mejores sim-pregunta quedan);
  ningún canal no-vectorial pierde slots.
- `:136` y `:150` intactos (trazados a mano por r2: siguen verdes).

## Piezas

- `src/rag/retriever.py` Step 5a — único punto de cableado.
- `tests/test_hyq_channel.py` — contratos de arriba.
- `scripts/s103_displacement_probe.py` — probe gate 1-3b, config-stamped.
