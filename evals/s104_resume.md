# s104 — NOTA DE RETOMA (desconexión de internet ~10-jul)

## Qué estaba corriendo al desconectar (AMBOS se caen sin internet y AMBOS reanudan sin re-pagar)

1. **Pase T2 de R2** (81 docs eval-adjacent, Haiku, dump-mode). Checkpoint POR DOC
   (dump `evals/enunciados_dump_T2.jsonl` + ledger tras cada doc; pérdida máx = 1 doc en vuelo).
   **Retomar:**
   `python scripts/enunciados_pass.py --tranche T2 --docs evals/s104_t2_docs.txt --to-dump --model claude-haiku-4-5-20251001 --vintage h1 --resume --budget-usd 60`
   (el `--resume` salta lo ya pagado vía ledger+dump; snapshot de seguridad en
   `evals/enunciados_ledger.backup.json`)

2. **Assessment full v3** (post-ship DEC-101, fila del scoreboard). Resumible de su partial:
   `python scripts/factlevel_assessment.py full`
   (reanuda de `evals/s100_factlevel_full.partial.jsonl`; los golds ya juzgados no se re-pagan)

## Estado committeado (rama `eval/s100-factlevel-assessment`, pusheada @c7ff48c)

- **s103b SHIPPEADO por Alberto**: PR#116 merged + Railway `GENERATOR_SELECTION_BLOCK=on`
  (landing v3.1 extensión + selección code-gated, DEC-101). Smoke post-ship OK
  (`evals/s100_factlevel_smoke.yaml`, flags v3 estampados).
- **R2 (DEC-102 pendiente de escribir al cierre)**: diseño v2 en
  `evals/s104_r2_corpuswide_design.md` (leer entero: base medida + enmienda G0 + gates);
  G0 = Haiku GO (veredicto `evals/s104_g0_verdict.json`); T1 ya en prod (21.995, verificado);
  maquinaria: `enunciados_pass.py` (dump-only, 9 fixes dúo) + `s104_a3_load.py` (loader A3)
  + `s104_r2_equiv_pilot.py`.

## Cola tras T2 (pre-declarada — NO improvisar)

1. Gates T2 judge-free ANTES de gastar el tail: (a) flips testbed s94 reproducen;
   (b) famtie-probe de los retrieval-miss v3 (necesita el yaml del assessment full);
   (c) anti-dilución (patrón old-vs-new anclas-OK, cargar dump T2 vía
   `python scripts/s104_a3_load.py --dumps evals/enunciados_dump_T2.jsonl evals/enunciados_dump_G0H.jsonl`
   y probe pools). STOP declarado si (b) débil (<2 mejoran in_pool).
2. Si gates OK → T3+ (resto por densidad, lotes ~150 docs, mismo comando con listas nuevas;
   los docs de eval ya están; excluir ledger). Est. ~$95 restantes de generación.
3. Gate final: VACUUM tabla → bvg K=3 + assessment → fila v4.
4. Cierre: DEC-102 + LEVER_DIGEST fila enunciados (actualizar in-place) + PLAN/HISTORY/memoria.

## Presupuesto (ledger = fuente de verdad)

Sesión: ~$135 envelope original + R2 $4.5/~$180. Tope duro del pase: `--budget-usd`.
