# Rumbo s44 — propuesta a atacar: ¿A2 (fusión por composición de pool) es el lever correcto, y en qué secuencia?

> Propuesta para revisión adversarial (Protocolo 3, dúo). Autor = Claude. Te llega la
> propuesta, no su defensa. Ataca contrato / fallo-conocido / sobre-ingeniería.

## Contexto (decidido, NO a re-litigar)
- s43 cerró con **bulto = 8 FALLO confirmados** (DEC-017): hp001/05/08/09/11/13/19/20. SALVAGE no rebuild (DEC-016).
- DEC-016 CORRECCIÓN: el cuello es **MIXTO retrieval-pesado** (no "síntesis dominante"); el "burial de COMPOSICIÓN del pool" quedó **sin testear end-to-end**.

## Diagnóstico MEDIDO este turno (`_s44_dimension_burial.py`, eval-only, read-only)
Proxy = **rango vectorial puro** (coseno real, top-50, HyDE-off). NO es end-to-end.
De los **12 hechos del bucket RETRIEVAL** de los FALLO (vista TGT = manual-objetivo, la defendible; LAXO sobre-estima por palabras comunes en otros manuales):
- **6 BURIAL (A2-addressable) / 6 RECALL-MISS (A2 no ayuda)** — ~50/50.
- De los 6 burial: **solo 2 en vector-top15** (los salva un re-rank); **4 en rango 16-50** (solo los salva cambiar la COMPOSICIÓN del pool).
- Casos clave: **hp019** = burial limpio (chunk-con-valor en vector rank **1**, pero no llegó a top-5 en producción). **hp020** = **SÍNTESIS/over-admit** (el chunk con el procedimiento estaba en **top-5 rank 0**; el bot lo tenía y dijo "no especifica"). **hp013** = recall-miss. **hp001** = síntesis-probable (atribución no confirmada — Voyage cayó; spot-check humano sugiere que el bot eligió la clave 1111/manual-usuario sobre 2222/manual-admin).

## Mecanismo de burial — VERIFICADO en código
- `telegram_bot.py:447` retrieve_chunks(top_k=RETRIEVAL_TOP_K) → `:450` rerank_chunks(...): **el reranker opera sobre el pool YA recortado** → ciego a la composición.
- `retriever.py:1094` `merged.sort(key=similarity)` mezcla **escalas**: coseno real (~0.66) vs **constantes estampadas** 0.65/0.80/0.82/0.85 (líneas 407/458/491/516/973/1042). Luego `:1131 return merged[:top_k]`.
- → un chunk de **coseno-rank-1** (p.ej. hp019, sim 0.667) queda por DEBAJO de un keyword-chunk estampado 0.80/0.85 → enterrado fuera de merged[:15].
- `retriever.py:429` (comentario): el 0.82/0.85 se pone alto A PROPÓSITO para surfacear has_diagram/wiring → **constantes LOAD-BEARING** (guarda anti-omisión de diagramas), no ruido puro.

## Lever propuesto (A2)
Re-estampar **similitud real (coseno query·embedding)** sobre los candidatos del pool ANTES del sort de `:1094`, conservando las guardas (lifecycle/idioma/modelo/diversify), en vez de las constantes planas. Objetivo: que la composición de merged[:15] la decida la sim real, no el boost plano → rescatar los burial.

## Secuencia propuesta
1. **re-baseline K-mayoría** (DEC-015; el "antes" estable — el single-pass es ruido #37).
2. **build A2** tras flag (reversible).
3. **A/B K-mayoría**, vara = **NO-regresión** (no "mejorar"; riesgo de romper la guarda de diagramas).
4. **dúo adversarial** + **ship-gate G2** (sign-off humano).
5. Síntesis (hp020/hp001) = lever SEPARADO (G3), NO en s44 autónomo (generación = mal historial, DEC-001).

## Claims LOAD-BEARING (sobre estos descansa el rumbo — atácalos)
- **C1 (measure-first / DEC-005):** construir A2 sobre un proxy de RANGO vectorial ¿repite "decidir sobre proxy"? El script tiene un modo `--restamp` que **simula** A2 end-to-end-sobre-el-funnel (re-estampa sim real y re-clasifica) SIN construir nada. ¿Debe correrse el `--restamp` ANTES de comprometer el build de A2?
- **C2 (alcance de A2):** ¿re-estampar sim real sobre el pool actual alcanza los **4 hechos en rango 16-50**, o solo re-ordena los que YA están en merged? Si el fetch vectorial que alimenta `merged` es estrecho (~top-15), A2 NO los alcanza sin ADEMÁS ensanchar el fetch → el "rescate de 6 burial" estaría **sobre-afirmado** (real serían ~2).
- **C3 (prioridad):** medio bucket es recall-miss (A2 no ayuda) y síntesis es real (hp020 confirmado, hp001 probable). ¿Es A2 el lever de MAYOR valor, o es pulir retrieval mientras el cuello de síntesis —más duro— espera?
- **C4 (guarda load-bearing):** sustituir las constantes 0.82/0.85 por sim real ¿degrada la guarda de surfaceo de diagramas/wiring (`retriever.py:429`)? = vector de no-omisión convertido en tweak.
- **C5 (denominador):** uso la vista TGT (6 burial) vs LAXO (7). ¿Es TGT el denominador honesto o cherry-pick? Los hechos FUERTES (anchors de modelo/número) ¿son inmunes al artefacto?

## Contrato
BP + estructural (raíz) + escalable (30+ fab, ES/EN) + precisión>velocidad + sin sobre-ingeniería + todos los gaps declarados.
