# S270 — Review de SHIP del contrato must-preserve (dúo, ronda única)

Objeto: merge a main de la rama `claude/s270-gold-adjudication` con el mecanismo v3
(`src/rag/must_preserve.py` + cableado en generator.py, flag `MUST_PRESERVE_CONTRACT`
default-off) + la adjudicación DEC-125 + los artefactos de la campaña de probes (DEC-127).

Evidencia del ship: 3 probes pareados (prereg con probe_number visible; cambios funnel-driven
validados en poblaciones frescas seeds 269-274): 1 conversión estable (obl_b6f6 3/3 en v2 Y v3),
0 regresiones protegidas y 0 conflictos nuevos en 36 réplicas; Etapa 3 ruta viva: 5/5 smoke
golds monotónicos, 0 apéndices espurios ($0.61); suite 1984+ verde.

Preguntas (bite con ancla fichero:línea):
1. ¿Algún defecto de CÓDIGO en must_preserve.py v3 (grounding fold-tolerante `ground_hybrid_span`,
   disclosure dos-lados, priorización `_select_for_appendix`, paridad display) que haga el
   default-off inseguro al merge o el ON inseguro en demo?
2. ¿El cableado en generator.py mantiene byte-identidad con flag off y fail-open real?
3. ¿La cadena de preregs/gates de los 3 probes tiene algún hueco que invalide el claim
   "0 regresiones/0 conflictos" o el claim de conversión estable de b6f6?
4. ¿La decisión de DETENER la iteración y el mapa residual por-clase (DEC-127) omiten algún
   riesgo material para el merge?
NO es objeto: re-litigar el rumbo (DEC-121/122/125/126 adjudicados por Alberto).
