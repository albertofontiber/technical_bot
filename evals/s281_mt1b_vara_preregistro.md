# s281 — MT-1b vara pre-registrada (gates de Fase 1 multi-turn)

**Lane:** MT-1b (construir la eval multi-turn ANTES de MT-1a). **Estado:** eval +
interfaz construidas $0; la policy (`src/orchestrator/conversation_policy.py`) es
STUB hasta MT-1a. **Autoridad de umbrales:** diseño v2 §4 [FIX-UMBRALES] +
[FIX-PARIDAD] (`evals/s280_multiturn_design_v2.md`), adjudicación dúo r1
[GATES-F1-UMBRALES] (`evals/s280_multiturn_duo_r1_adjudication_v1.yaml`). Este doc
CONGELA la vara ANTES de ver resultados de la policy real (pre-registro honesto).

## 0. Objetivo de HOY + su MÉTRICA (Protocolo 2 §5)

Medir si la Fase 1 (clasificador determinista + rewrite gateado) da conversación
útil SIN regresar el single-turn. **Métrica conversacional de HOY** = la eval
MT-1b: (a) exactitud de ROUTING (determinista, $0) y (b) fidelidad de REWRITE +
CONDUCTA del último turno (juez, `--e2e`). NO es una tasa PASS de respuesta-única
(eso es el harness single-turn, que aquí entra SOLO como gate de no-regresión).

- **Lever tocado:** conversación multi-turn (NUEVO; no había vara). No re-abre
  ningún settled-en-PASS ni el NO-GO S95 de deep-lookup (ese fue utilidad de
  respuesta-única — ver §6/DEC-154).
- **Métrica del baseline de no-regresión citado:** single-turn 39 golds =
  **12 PASS / 25 PARCIAL / 2 FALLO** bajo `c1_v4` (single-pass, juez GPT-5.5,
  `evals/bot_vs_gold_39_baseline_coverage_c1_v4_s281.yaml`). Coincide con el
  objetivo del gate de no-regresión (misma vara, mismos QIDs). Un settled-en-PASS
  del single-turn NO zanja el routing multi-turn: son ejes distintos.

## 1. Contrato de freeze (per-eval, DEC-023/021§F)

Se congelan ANTES de la corrida de cierre de Fase 1: corpus + índice + embeddings
(`chunks_v2`/Voyage-1024) + **juez GPT-5.5 K=3 mayoría** (freeze DEC-023, NO se
cambia) + seeds + config de release + `evals/multiturn_golds_v1.yaml` (hash del
fichero) + el prompt del rewriter económico + tier del rewriter (Sonnet). El
ROUTING se asevera en `--contract` ($0, determinista, sin juez); el juez SOLO
puntúa lo que exige LLM (rewrite + conducta). Cambiar el juez o el corpus = nueva
vara.

## 2. Umbrales de gates F1 (PRE-REGISTRADOS)

| # | Gate | Umbral | Modo | Cómo se mide |
|---|---|---|---|---|
| G1 | Precisión clasificador **standalone vs dependiente** | **≥95%** | `--contract` $0 | binario sobre los 31 turnos MT-1b (standalone = ruta STANDALONE; dependiente = las otras 4). n=31 ⇒ ≤1 error tolerado |
| G2 | Exactitud de **ruta fina** (5 rutas) | **≥90%** | `--contract` $0 | ruta resuelta == gold sobre los 31 turnos |
| G3 | **$0-guarantee**: coste en standalone + carry-forward | **= 0 llamadas LLM** | `--contract` $0 | invariante `requires_llm_rewrite==False` en TODA ruta ≠ REWRITE (enforced en `TurnResolution.__post_init__`) |
| G4 | **clarify-indebido** en turnos standalone/answerable | **<5%** | `--contract` $0 | ningún turno con conducta esperada `answer` sale `clarify` (pinea DEC-092: invariante→answer, p.ej. `mt10b`) |
| G5 | **Gate producto-explícito**: no-fuga de historial | **0 fugas** | `--contract` $0 | `must_not_target` vacío en cambio-explícito / corrección / reinicio (`mt03/mt04/mt06`) |
| G6 | **Códigos verbatim** en rewrite + trampa RS-485 | **0 mutaciones / 0 falsos cambios** | `--contract` $0 (verbatim) + `--e2e` (rewrite) | `query_for_retrieval_preserves` + `codes_must_preserve`; `NON_PRODUCT_CODES` no dispara cambio de producto (`mt08b`) |
| G7 | **No-regresión single-turn** | **≥ baseline 12P/25p/2F** (0 PASS→peor) | harness single-turn (`test_bot_vs_gold.py`, misma vara) | mismos QIDs, mismo juez; el orquestador entra por debajo del seam (paridad byte, [FIX-PARIDAD]) |
| G8 | **Corrección del rewrite** (fidelidad source-bound) | **0 entidades inventadas** en muestra adjudicada | `--e2e` + adjudicación Alberto | juez K=3 + revisión humana de la muestra REWRITE (`mt02/mt08`) |
| G9 | **Conducta del último turno** (answer/admit/clarify/refuse) | **coincide `expected_behavior`** | `--e2e` juez K=3 | `mt05` admit, `mt10` clarify, `mt10b` answer |
| G10 | **Latencia p50 por ruta** | **declarada** (no umbral; observabilidad) | `--e2e` | p50 de standalone / carry-forward ($0) vs rewrite (1 llamada) |
| G11 | **Coste por ruta** | standalone+carry-forward **0**; dependiente **≤1** llamada económica | `--contract` (conteo) + `--e2e` (coste real) | rewrite=Sonnet; se estampa en el DEC de cierre |

**G1-G7 son BLOQUEANTES de merge de Fase 1** (medibles $0, sin API). G8-G11 se
resuelven en la corrida `--e2e` de cierre (pagada, fuera de esta lane).

## 3. Cobertura de la eval (15 flujos / 31 turnos / 10 clases)

followup_detalle · pronombre · cambio_producto_explicito · correccion ·
no_contestable_admit · reinicio_tema · carry_forward_1h (dentro/fuera de ventana) ·
codigos_tecnicos (verbatim + trampa RS-485) · dos_conversaciones_aisladas ·
clarify_solo_si_diverge (diverge→clarify / invariante→answer). Entidades REALES
reusadas de `gold_answers_v1.yaml` (+ GT de memoria para ZXSe/out-of-corpus).

## 4. Instrumento y su validación (anti-ritual)

`scripts/test_multiturn_vs_gold.py --contract` conduce cada turno por el
ORQUESTADOR (`run_conversational_turn` sobre `FakeConvoStore`, adapters replay,
$0) y asevera la `TurnResolution` de la policy contra el gold. **Dientes probados**
(`tests/test_multiturn_golds_contract.py`): una policy de referencia determinista
GENUINA (no mira el gold) satisface los 15 flujos (FAIL=0) y una policy errónea
los tumba (FAIL>0). El aislamiento de 2 conversaciones se ejerce a nivel
orquestador (CAS/orden/dedup), no transporte (diseño §9).

## 5. Interfaz que MT-1a implementa

`src/orchestrator/conversation_policy.py` (esta lane la define): `ConversationPolicy`
Protocol, un método `resolve(query, turn_models, available_models, working_state,
now, rewrite=None) -> TurnResolution`. MT-1a reemplaza `default_policy()` (y añade
la clase concreta) SIN tocar dataclasses/enum. Detalle exacto en el informe de la
lane + docstrings del módulo.

## 6. Fase 2 (multi-hop) — herencia del veredicto (DEC-154, Alberto 23-jul)

**El gate de la Fase 2 (multi-hop bounded) se medirá sobre la MÉTRICA
CONVERSACIONAL de esta eval (MT-1b) + eval orgánico** (llega ~sept). **El NO-GO
S95 fue de utilidad de RESPUESTA-ÚNICA (deep-lookup) y NO se hereda** al eje
conversacional: multi-hop bajo router/budget cerrado sobre working state es un
lever distinto del agente-libre que S95 descartó. Fase 2 no se abre sin pasar
Fase 1 (G1-G9) + lectura de Alberto (diseño v2 §0).

## 7. Qué NO cubre la eval (gaps declarados)

1. **Dev-eval, sin tráfico orgánico** (diseño §5.2): n=31 turnos ⇒ G1/G2 son
   DIRECCIONALES; el gate estadístico real requiere el orgánico de ~sept. No se
   sobre-interpreta un 95% sobre 31.
2. **`--e2e` NO ejecutado en esta lane** ($0): G8-G11 quedan especificados +
   gateados (`MT1B_E2E_CONFIRM`), sin pasada pagada. La corrida de cierre los mide
   con freeze y estampa coste.
3. **Detección de marca fuera de corpus** (`mt05b`, Bosch FPA-1200):
   `extract_product_models` NO la reconoce (regex). El gold exige no-fuga del
   producto previo + conducta admit; satisfacerlo requiere detección de marca
   catálogo-aware (dependencia DEC-069, 2-etapas entity-linking) que MT-1a debe
   aportar — declarado como dependencia, no como capacidad ya presente.
4. **Trampa RS-485 conocida**: `extract_product_models('RS485')->['RS-485']` es un
   falso positivo REAL del detector (verificado). El gate G6 lo pinea vía
   `NON_PRODUCT_CODES`, pero esa lista es SEED, no exhaustiva — otros códigos de
   bus/protocolo pueden reincidir hasta el catálogo gobernado.
5. **Working state durable**: la eval modela el working state en memoria del
   harness (migración del carry-forward-1h, diseño §8). La persistencia real en
   `convo.conversation_snapshots` es MT-0d/DDL, gateada por la matriz RGPD — aquí
   NO se toca DB.
6. **Rewrite content**: en `--contract` la ruta REWRITE se asevera (que SE elige y
   que `requires_llm_rewrite=True`) pero NO se produce el texto ($0). La calidad
   del rewrite es G8, `--e2e`.
