# S274 (Bloques C/D): callout-card convierte 0d6a — 146/154; familia de anexo exhausta para los 6 residuales

**Foto oficial (DEC-134): 146 OK / 6 synth / 2 retr / 154 (94,81%) — quedan +5 para 151 (98%).**
Cadena completa del bloque C/D ejecutada dentro del prereg dúo-adjudicado
(`evals/s274_bloquesCD_prereg_v2.yaml`), coste total **$1,51 / techo $15**, DB GET-only,
sin probe #5 (anti-overfit cumplido de prereg a cierre).

## Qué convierte

- **`obl_0d6a30948dfd` (hp017, bloque-warning mergeado DEC-125)** — el PAR C1:
  `COVERAGE_MANDATORY_CALLOUT` (card de callout-MANDATORY en campo propio de la vista
  servida, receipt exacto propio, `local_semantic_validated: False`) +
  `MP_MANDATORY_VERB_TRIGGER` (el gatillo-verbo `evite` cuenta como verbo conjugado en la
  whitelist; los gatillos-sustantivo jamás).
- **Probe #4 con brazos de ablación** (`evals/s274_probeCD_result_v1.json`, $0,60):
  `merged_warning_block` **3/3 en A-C1 vs 0/3 en A0**, generación fresca hp017 K=3 pareada
  mismo-día; idéntico en **A-ALL-det** (lo shippeable sin Haiku) → banking DESPLEGABLE
  det-only (regla Sol-C1). **0 daño en todos los brazos**: 0 protegidas caídas, 0 conflictos
  nuevos, anclas per-fact +0/−0 (STOP duro s104+s105 intacto), retrieval-invariante A-C1
  PASS, 0 diagramas-por-anexo (`VISUAL_ASSETS_REGISTRY=off` pineado).
- **Smoke vivo con la config candidata**: 5/5 monotónicos, 0 apéndices espurios ($0,64).
- Banking determinista SHA-pineado (patrón s272): `scripts/s274_bank_conversions.py` →
  `evals/s274_banked_funnel_v1.json`.

## Qué NO convierte (y queda cerrado con métrica)

- **C2 / `MP_SERVED_BINDING` NO-GO en P1** (Etapa-1 v9, cohorte fresca seed-277, 112 filas,
  exclusiones acumuladas v1+seed-270..276): `served_uncited_clean_fp = 24/105` — 26 anexos
  de **hermanos genuinos** / 1 target verificados por-fila. La clase seed-270 re-medida
  FALLA incluso con umbral reforzado ≥3 → **DEC-127 reforzado (2ª reconfirmación)**; el
  brazo A-C2 no llegó al probe.
- **Los otros 5 fixes: GO en P1, 0/3 en sus dianas en el probe** — D1a defline `=` (14/14),
  D1b F-RELATION det-side (shape 45/45), D1c stem (51/57), D2 token-distintivo (26/26,
  re-clase seed-271 = 0), todos con FP=0 en sus controles… y ninguna conversión en la
  generación real. Detalle por-id (qué fix y cómo murió):
  `evals/s274_bloquesCD_closeout_v1.yaml`.
- **Declaración estratégica (DEC-134): la familia mecanismo-de-anexo queda EXHAUSTA para
  los 6 residuales.** El camino a 151 exige OTRA familia — opciones para Alberto: gold
  round-2 con lente source-contract · serving-view generalizada (clase C1 para spans
  no-MANDATORY) · eval orgánico como árbitro de si los 6 importan en uso real.

## Ship (decisión de Alberto)

Config candidata = **solo el par de 0d6a**; el resto de flags s274 quedan default-off (sin
conversión que los justifique).

> Railway → variables: `COVERAGE_MANDATORY_CALLOUT=on` y `MP_MANDATORY_VERB_TRIGGER=on`
> (`MUST_PRESERVE_CONTRACT` ya on desde DEC-131) → 1 pregunta de smoke → rollback = quitar
> las 2 variables. Recibo vivo query_logs al encender (patrón DEC-131).

## Contenido del PR

- **Build P0** (commits previos de la rama): 7 fixes flag-gated por-fix + `mp_lexicon` +
  24 tests, byte-idéntico con todo off; dúo Sol 7/7 + Fable 5/5 (0 FP) adjudicado.
- **P1**: `scripts/s274_mutation_harness_v9.py` (+cohorte v9, prereg, results, gate
  `evals/s274_stage1_v9_gate_v1.yaml`; iteración de instrumento declarada: cross_count
  `cross[0]` / paridad display / defline bullet-label — flag-independiente).
- **P2**: `scripts/s274_probe_ablation.py` (10 brazos exactos del prereg, checkpoint
  resumible, gating por el gate P1) + result + réplicas.
- **P3**: smoke re-corrido con la config candidata (artefactos s270 actualizados in-place).
- **P4**: `scripts/s274_bank_conversions.py` + `evals/s274_banked_funnel_v1.json` +
  `evals/s274_bloquesCD_closeout_v1.yaml` + DEC-134 + PLAN + fila LEVER_DIGEST in-place.
- Tests nuevos: harness v9 (22) · probe ablation (17) · banking/closeout (6). Suite
  completa verde (solo los 4 CRLF pre-existentes s117/s131/s133, permitidos).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
