# S269 — Review del BUILD Track 2 (Etapa 1) — brief para el dúo

Objeto: los 3 commits del build (`559143f` módulo+cableado, `f6ba3a6` cohorte+labeler+gate,
`c8de045` freeze-hash CRLF) que implementan el diseño v2 dúo-adjudicado
(`evals/s269_synthesis_portfolio_design_v1.md` — vuestra ronda anterior, 18/18 aplicados).

Ficheros nuevos/tocados: `src/rag/must_preserve.py` · cableado en `src/rag/generator.py`
(flag `MUST_PRESERVE_CONTRACT` default-off, `src/config.py`) ·
`scripts/s269_build_structural_cohort.py` · `evals/s269_structural_cohort_v1.jsonl` (108 filas:
20/20/20/8 por familia + 20 negativos-cribados + 20 azar-puro) ·
`evals/s269_structural_cohort_prereg_v1.yaml` · `scripts/s269_label_structural_cohort.py`
(dual Luna+Haiku, preflight $1.64) · `scripts/s269_stage1_gate.py` · `tests/test_must_preserve.py`
(43 tests; suite completa 1906 pass / 4 CRLF pre-existentes).

Preguntas de review (bite concreto, ancla fichero:línea):
1. **Fidelidad al diseño v2**: ¿el build implementa los 6 endurecimientos de vuestra ronda
   (gate recall por-familia; attestation identidad doc_map fail-closed; no-claim de
   "0 regresiones por construcción"; caption sin "verificada"; léxico F-MANDATORY sin "antes de"
   solo; F-COUNT→disclose)? ¿Algún NO-OP silencioso o desviación no declarada?
2. **Anti-contaminación**: ¿la cohorte Etapa 1 está de verdad limpia de los 4 targets/golds/
   cohortes consumidas (exclusiones 247/1007 docs)? ¿El pre-screen con el propio detector
   introduce circularidad que el brazo azar-puro no controle? ¿El gold dual (Luna+Haiku) es
   de verdad independiente del detector?
3. **Cableado generator**: con flag off, ¿byte-idéntico garantizado? Con flag on, ¿fail-open
   real (excepción → respuesta intacta)? ¿El binding usa fragmentos SERVIDOS y citas reales
   del pipeline actual (no una abstracción que no existe en runtime)?
4. **Detectores**: falsos disparos evidentes sobre texto real de manuales (fechas, números de
   sección, listas de accesorios, tablas de aprobaciones); ¿la exclusión 7-segmentos es
   demasiado amplia o estrecha?
5. **Gate**: ¿`s269_stage1_gate.py` puede declarar GO con un detector degenerado
   (ultra-restringido o ultra-permisivo)? ¿Los umbrales del prereg se leen del prereg
   (anti-tamper) o están duplicados?

Contexto de proceso: Etapa 2 (probe a los 4 targets) NO se ejecuta hasta adjudicación formal
de Alberto de la reapertura s222/s223 — está estampado en el gate. Esta review es del
instrumento y del módulo, no del rumbo (el rumbo ya pasó su ronda).
