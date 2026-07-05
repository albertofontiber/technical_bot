# s98 · Funnel por-FACT de los NO-PASS (config shipped: A3 on, tiebreak off)

> Unidad = fact CORE (lo que la respuesta DEBE contener). Etapa = dónde muere en el
> pipeline. 24 golds NO-PASS (s97ctl), 96 facts-core. Método: needle-famtie para
> pool/top5 + matcher atómico para "está en la respuesta servida" (mayoría de 5 runs).

## Distribución global (96 facts-core)
| # | clase | lever |
|---|---|---|
| **70** | **SERVIDO-pero-juez-FALLA** (el fact SÍ está en la respuesta; el gold falla por OTRO motivo) | gold/juez — NO pipeline |
| 13 | SÍNTESIS lo suelta (llegó al top-5, el generador no lo escribió) | síntesis |
| 8 | RERANK lo tira (en pool, no top-5) | **rerank (clase hp001)** |
| 3 | NO-RECUPERADO (no entra al pool) | document-side |
| 2 | INDET (facts cualitativos None) | — |

## Lectura HONESTA (el 70 no son 70 problemas)
- **El pipeline mayormente FUNCIONA:** 70/96 facts llegan a la respuesta. Los golds que
  fallan lo hacen por gold/juez/completitud, NO por falta de recuperación → **confirma el
  plateau gold/juez de DEC-070/073, ahora al nivel de fact.**
- **Caveat crítico:** per-fact ≠ per-gold. Un gold con 5 facts servidos + 2 perdidos FALLA
  (le faltan 2), y esos 5 servidos cuentan como "servido-pero-falla" aunque la culpa sea de
  los 2 perdidos. Rollup por-gold: **9 golds NO-PASS tienen TODOS sus core servidos y aún
  fallan = gold/juez puro** (fidelity/juez-bias/conducta); **15 golds tienen ≥1 fact perdido**
  = potencialmente pipeline-arreglables (cota superior — arreglar el fact no garantiza PASS).
- Caveat 2: el matcher de prosa puede dar falsos-positivos en facts cualitativos → el "70"
  es cota alta; los facts-ancla (números/códigos) son la señal fiable.

## Los 24 facts que el bot DEBERÍA haber incluido y no incluyó (accionables)
**RERANK lo tira (8 — la clase hp001, lever P4):** cat001·'40' · cat010·'24V dc' ·
hp002·'7.6.1' · hp003·'12V' · hp005·'CIRCUITO SIRENA' · hp006·'ISO-X' · hp009·'Retorno' ·
hp017·'instruccion de entrada'.
**SÍNTESIS lo suelta (13 — llegó al top-5, no se escribió):** cat001·'32/25/20' ·
cat011·'seguridad intrínseca' · cat011·'iónico' · cat016·'menu ZONA+ELEMENTO' ·
cat017·'159+159' · hp009·'aisladores internos' · hp010·'Nivel 3' · hp010·'nuevos/eliminados' ·
hp011·'ABORT' · hp011·'enclavadas' · hp012·'4 lazos/792' · hp017·'seis tipos retardo' ·
hp018·'4 circuitos'.
**NO-RECUPERADO (3 — document-side):** cat016·'autobusqueda' · hp011·'r.1' · hp012·'99+99'.

## Sizing de los levers (para decidir dónde trabajar)
- **RERANK (P4): ~8 facts** across ~8 golds. Real y limpio (+ desbloquea el tie-break), pero
  MODESTO — no es donde está el grueso del PASS.
- **SÍNTESIS: ~13 facts** (el generador tiene el chunk y no escribe el dato). Mayor bolsa —
  "vendrá después" (decisión Alberto).
- **GOLD/JUEZ: ~9 golds** con todo servido y fallan = el plateau, no pipeline.
- **DOCUMENT-SIDE: 3 facts** (hypothetical-questions).
