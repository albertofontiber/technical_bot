# S108 failure-stage reconciliation

Conservative reconciliation of the 36 frozen non-OK rows. Candidate status is not official OK credit.

- Official baseline: **93/127 unchanged**
- Retrieval facts: **7**
- Measurement replay ready: **2**
- Structural R2 precondition ready: **3**
- Structural exploratory discoveries: **1**
- Doc-scoped HYQ unique resolutions: **1**
- Retrieval unresolved in merged evidence: **0**
- Retrieval stage accounted: **7/7**
- Cached synthesis successes: **1**

| Key | Baseline | Candidate status | Next lane |
|---|---|---|---|
| `cat001#3:32 / 25 / 20` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `cat007#3:2 A / 0,5 A` | `retrieval-miss` | `measurement_replay_ready` | `bounded_frozen_judge_replay` |
| `cat007#4:10^5` | `retrieval-miss` | `measurement_replay_ready` | `bounded_frozen_judge_replay` |
| `cat008#3:1/2/3/4 lazo; 6-7 entrada A` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `cat010#0:24V dc` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `cat013#0:bucle cerrado` | `corpus-gap` | `unchanged` | `document_extraction` |
| `cat013#1:CLIP` | `corpus-gap` | `unchanged` | `document_extraction` |
| `cat016#1:menu ZONA + ELEMENTO` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `cat017#2:licencia CLIP por lazo` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `cat017#4:CLSS` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `cat018#1:pestana Programacion: Zona + CBE` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `cat018#2:Tipo SW / asociacion CBE` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `cat018#3:Apendice A` | `meta-ref` | `unchanged` | `excluded` |
| `cat020#2:manual de variaciones Espana` | `meta-ref` | `unchanged` | `excluded` |
| `hp001#2:1111` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp002#3:7.6.1` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp003#0:12V` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp003#1:cable puente` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp005#3:CIRCUITO SIRENA` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp006#1:Tierra` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp006#2:ISO-X` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp009#0:Retorno` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp010#1:Nivel 3` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp011#0:ABORT` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp011#1:r.I` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp011#2:05 a 295 seg` | `retrieval-miss` | `r2_precondition_ready_cached_synthesis_miss` | `synthesis_repair_with_cached_context` |
| `hp011#3:enclavadas` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp012#3:4 lazos / 792` | `retrieval-miss` | `doc_scoped_hyq_retrieval_precondition` | `rerank_and_provenance_gate` |
| `hp013#0:EEPROM` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp013#1:PWR-R` | `retrieval-miss` | `exploratory_structural_retrieval_precondition` | `freeze_discovery_then_bounded_synthesis` |
| `hp014#3:35` | `retrieval-miss` | `cached_synthesis_success_pending_protected_regression` | `protected_regression_and_atomic_judge` |
| `hp015#2:32` | `synthesis-miss` | `unchanged` | `answer_coverage` |
| `hp017#1:instruccion de entrada` | `retrieval-miss` | `r2_precondition_ready_cached_synthesis_miss` | `synthesis_repair_with_cached_context` |
| `hp017#2:Editar Configuracion` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp018#1:6K8` | `rerank-miss` | `unchanged` | `evidence_selection` |
| `hp018#4:1 A` | `rerank-miss` | `unchanged` | `evidence_selection` |

Gate: **GO_RETRIEVAL_7_OF_7_PRECONDITIONS_TO_DOWNSTREAM_GATES**
