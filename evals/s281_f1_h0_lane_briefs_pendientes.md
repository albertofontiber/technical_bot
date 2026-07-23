# s281 — briefs de las lanes PENDIENTES DE RELANZAR (GO de Alberto dado, pausa por internet)

**Contexto del GO (Alberto, 23-jul tarde):** "asegura que el diseño es Best Practice de este
tipo de RAGs, no escatimes en 'diseños económicos'. OK a correr Fase 1 y H0 en paralelo".
Upgrades derivados del mandato (decididos, van en los briefs): (1) el rewrite de MT-1a arranca
en SONNET (tier de generación), solo baja si la eval demuestra paridad — optimizar DESPUÉS de
medir; (2) vara MT-1b pre-registrada con juez GPT-5.5 K=3 en veredictos de comportamiento +
aserciones deterministas $0 (contrato) donde aplique.

Las DOS lanes se lanzaron y se pararon a los segundos (cero trabajo perdido). Al retomar:
relanzar FRESCAS en Opus con los briefs de abajo, en el worktree Technical Bot-s281
(rama claude/s281-mt0). El texto completo de cada brief está en la traza de la sesión; este
fichero resume el CONTRATO de cada una para reconstruirlos sin la traza si hiciera falta.

## Lane MT-1b — construir la eval multi-turn (ANTES que MT-1a; $0, sin pasadas pagadas)
- evals/multiturn_golds_v1.yaml: flujos por clase — follow-up detalle · pronombre · cambio
  producto explícito (gana al historial) · corrección · no-contestable→admit · reinicio tema ·
  carry-forward-1h $0 · códigos técnicos byte-intactos en rewrite · 2 conversaciones aisladas ·
  clarify solo-si-diverge (s79/s80). Entidades REALES reusando golds existentes (no inventar specs).
- scripts/test_multiturn_vs_gold.py: conduce flujos por el ORQUESTADOR (TurnRequest→run_turn)
  sobre FakeConvoStore; modo --contract ($0, aserciones deterministas + detección de stub de
  src/orchestrator/conversation_policy.py [Protocol que MT-1a implementará — lo define esta lane])
  y modo --e2e (pagado, juez K=3, NO ejecutar en la lane).
- evals/s281_mt1b_vara_preregistro.md: umbrales de gates F1 (routing/rewrite/no-regresión vs
  baseline 12-25-2/clarify-indebido/coste por ruta con rewrite=Sonnet) + freeze.
- Suite completa foreground al final (baseline 3158/0). Sin commits; informe con la interfaz
  exacta de conversation_policy.

## Lane H0-census — census de identidad + plan de backfill ($0, DB SOLO LECTURA)
- scripts/s281_h0_identity_census.py (RO, determinista, correr 2×): (1) documents con shas
  backfill:*/lineage NULL por clase y marca; (2) product_model unknown/NULL por manufacturer y
  source_file (clase ZXSe: MIE-MI-600 = 88 chunks verificados); (3) cruce con data/catalog
  (docs sin mapeo a producto); (4) cruce con bot_sources de los QIDs del baseline
  (evals/bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml) = impacto directo; (5) volumen
  desbloqueable por clase. Buscar el activo s83 (mapa doc→modelos ~2761 productos) en ramas/
  data/ — si no está, declararlo.
- evals/s281_h0_identity_census_report_v1.md: tabla por clase + PLAN priorizado en tramos con
  PROPUESTAS SQL (jamás aplicar; [ALBERTO] las decisiones de producto, p.ej. split D1 ZXSe por
  nº de lazos según su ground-truth s78). Estilo/rigor de scripts/s279_selection_census.py.
- Territorio con prefijo s281_h0_ para no chocar con MT-1b.
