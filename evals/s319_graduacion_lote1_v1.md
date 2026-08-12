# s319 PR-B — Graduación de flags, lote 1 (v2 tras dúo r18: 7 + 1 pareja)

> **v1→v2 (dúo r18: Sol 5 · Fable 5, convergentes en el acoplamiento, 0 FP — NO
> SÓLIDO ambos, TODO aplicado):**
> 1. **El acoplamiento que mi lote rompía** (Sol M1 ≡ Fable F1): RERANK_TOP_K=10
>    se validó EN PAREJA con LLM_MAX_TOKENS=3500 (DEC-092b: «0 truncado con
>    3500»; a 2048 cat019 truncó `stop=max_tokens`) — mi default 10+2048 era la
>    combinación MEDIDA como mala. → LLM_MAX_TOKENS entra al lote **a su valor
>    RECIBIDO (3500)**, no al de Railway (8000, SIN recibo — Fable verificó mi
>    claim: 0 hits; la discrepancia sigue adjudicable, producción no cambia).
> 2. **SELECTION_BLOCK FUERA del lote** (Sol M2): DEC-101 lo dejó «candidato
>    pendiente de GO» con cat021 flaky — Railway=on es estado operativo, no
>    veredicto. Default vuelve a off (producción intacta: su env var manda).
> 3. **Parser ESTRICTO en los guards de seguridad** (Sol M3): un typo en Railway
>    degradaba WIRING_TOPOLOGY_GUARD/ANTI_DIAGRAM_INVENTION a no-op SILENCIOSO
>    — contrario al precedente HYQ fail-fast. → `_guard_estricto` (RuntimeError
>    ruidoso; el getenv literal queda en el call-site para el censo L2b).
> 4. **«OFF definitivo» era «OFF recomendado»** (Fable F2): la recomendación D1
>    del paquete diferido s286 sigue sin adjudicar — FOLLOWUPS se gradúa por
>    métrica (10/10→0/12) + estado Railway APLICADO, con la cita honesta.
> 5. **Ancla de ENUNCIADOS corregida** (Fable F3): el recibo del ship es la fila
>    A3 del LEVER_DIGEST (PR #111 + Railway=on + verificado en prod 5-jul), no
>    DEC-090 a secas (que decía «el ship queda en manos de Alberto»).
> 6. Docstrings/comentarios stale reconciliados (generator, retriever, config,
>    wiring_topology_guard) + header del registro al censo real (97) + DEC-210
>    escrito (la referencia fantasma de los tests ya existe).

**Regla del lote** (propuesta v2, dúo r17): SETTLED con métrica + valor VIVO en
Railway (verificado por API, patrón DEC-195) + cero intención de volver. El
default cambia EN CÓDIGO; las vars de Railway no las toco — quedan redundantes
(inofensivas) y la lista de retirables es de Alberto.

## El gate de pre-verificación DISPARÓ (para esto existe)

`LLM_MAX_TOKENS`: Railway = **8000**, DEC-092b = 3500. **El 8000 no tiene recibo
en DECISIONS** (grep completo) — producción evolucionó sin veredicto documentado.
**FUERA del lote**: graduar 3500 degradaría producción en silencio si la var se
quitara; graduar 8000 consagraría un valor sin recibo. → mini-veredicto propio
pendiente (¿fue deliberado con el swap de modelo? adjudicación Alberto).

## Los 8 graduados (default viejo → nuevo = Railway verificado)

| Flag | Cambio | Evidencia | Evaluación |
|---|---|---|---|
| GENERATOR_PROMPT_VARIANT | base → fidelity | DEC-098 (+3/0 fact-level) | runtime |
| RERANK_TOP_K | 5 → 10 | DEC-092b (11/13 rescatados, 0 regresión) | import (config) |
| ENUNCIADOS_MULTIVECTOR | off → on | DEC-090 (4/4) + verificado prod | runtime |
| HYQ_TABLE | off → on | DEC-099 (flips 2/2) + verificado prod | **import** (fail-fast tipo) |
| GENERATOR_SELECTION_BLOCK | off → on | DEC-101 (cat022 FALLO→PASS) | runtime |
| GENERATOR_FOLLOWUPS | on → off | DEC-162e (10/10→0/12, «OFF definitivo») | runtime |
| ANTI_DIAGRAM_INVENTION | off → on | DEC-162a (peligro 10/10→0/20) | runtime |
| WIRING_TOPOLOGY_GUARD | off → on | DEC-162a (supresiones 0/48) | runtime |

Excluidos además del lote (r17): GENERATOR_DIRECT_FIRST y
VISUAL_ASSETS_LISTING_GATE (asentamiento sin métrica — categoría distinta si se
quiere); CONVERSATION_POLICY/ORCHESTRATOR_PATH van en PR-C con su cirugía.

## Onda expansiva medida (suite completa)

11 tests rojos de 3.829 — **todos tests que codificaban el contrato viejo**
(«default off», «default es base»), cero roturas de fakes/canales. Actualizados
uno a uno al contrato nuevo, manteniendo SIEMPRE el test del mundo legacy por
env explícito (la graduación cambia el default, no borra la vuelta):
- `test_s69_prompt_variant`: el byte-idéntico histórico ahora exige pinear el
  trío de prompt; nuevo test del default ship compuesto.
- `test_s286_conducta_fixes`: default = fidelity+followups-off+anti-on (exacto,
  byte-comparado) + test nuevo de que el legacy sigue construible.
- `test_s103_selection_gate`: fixture autouse pinea el mundo legacy (los tests
  miden el AISLAMIENTO del bloque de selección, no los otros flags).
- `test_enunciados_multivector`: default-on + off-explícito; el assert «1
  llamada» era falso con HYQ también on — ahora asserta «sin RPC de enunciados».

Suite final: **3.832 passed / 46 skipped**. P1/release-config: sin cambios
(SAFE_DEFAULTS/REQUIRED_EXACT_VALUES pinean sus propios env en los runs P1 —
verificado corriendo la batería en la suite).

## Riesgo residual declarado

- CI/dev-local sin vars pasa a conducta SHIP (es el objetivo — pero un dev que
  esperara el mundo viejo sin env se sorprenderá; el registro de flags es la
  referencia).
- El mundo legacy queda como env explícito, no como default: si un flag
  graduado tuviera que volver, es UNA var en Railway (mismo rollback de
  siempre) — nada se borra del código en este lote.
