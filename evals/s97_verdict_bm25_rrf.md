# s97b · Veredicto a revisar: "NO re-medir BM25/RRF ahora" (pregunta de Alberto)

> Pregunta de Alberto: ¿descartamos BM25 y RRF con la métrica equivocada (# PASS) y con el
> pipeline sucio (categoría + identidad)? ¿Tiene sentido re-probarlos para adecuarnos a BP?
> Mi veredicto (ABAJO) dice que no ahora. El dúo debe atacarlo — defiendo en parte
> mediciones y decisiones propias.

## Claims del veredicto (con anclas)
1. **BM25: veredicto limpio, no re-medir.** DEC-085 (s93, no s50) se midió en
   retrieval-miss POST-NOCAT con matriz pre-registrada → NO-GO 1/11; mecanismo
   métrica-independiente: "los tokens-aguja NO están en la PREGUNTA → cualquier ranker
   léxico sobre-la-query hereda el techo". Las dos sospechas de Alberto (métrica PASS +
   pipeline sucio) NO aplican a este lever.
2. **RRF: la sospecha de Alberto es correcta en la forma** — DEC-050 fue PASS + pre-NOCAT
   y el digest lleva la cláusula "re-medir, no recordar" (fila CE/MERGE) → re-medirlo
   estaría PRE-AUTORIZADO. **Pero el delta esperado hoy ≈ 0:** los 6 misses residuales
   son hechos cuyos soportes NO entran por ningún canal (trace s97: channels:0 en todas
   las etapas, salvo hp018 borderline) → la fusión no puede rescatar lo que ningún canal
   devuelve. Riesgo real: el re-barajado de PASS-control (parte de mecanismo de DEC-050,
   transfiere).
3. El valor fuera-del-eval del orden inter-canal ya se cobró en su versión barata
   (tie-break s97: +0.12s, famtie 7→6, 0 regresiones).
4. **Trigger correcto = queries reales** (TECH_DEBT #71): cuando query_logs tenga
   técnicos de verdad, pase de calidad de retrieval sobre queries reales = el instrumento
   justo para re-medir RRF (famtie-real + bvg).
5. Conclusión: no ahora — no "porque está settled" sino por delta-esperado-cero medible;
   BP-conformance sin fallo medible = rigor mal dirigido (lección s27).

## Puntos débiles que YO ya le veo (el dúo debe verificar o ampliar)
- **¿Conflación en el claim 1?** DEC-085 midió BM25-sobre-la-PREGUNTA (re-ruteo/find).
  La pregunta de Alberto venía de los stamps planos = ¿scoring de lo que el canal léxico
  YA encuentra (ts_rank por-resultado en vez de stamp)? Eso es OTRO mecanismo, no
  DEC-085. ¿Mi respuesta lo tapó? (Mitigante posible: el tie-break coseno ya ordena
  dentro del canal léxico — ¿un ts_rank por-resultado añadiría algo medible sobre eso?)
- **¿El "channels:0" es evidencia suficiente?** Es UN run de trace (jitter declarado);
  hp018 es borderline documentado. ¿Los K=3 runs de s97 confirman que los 6 residuales
  no entran por ningún canal, o lo estoy extrapolando de un run?
- ¿Hay algún mecanismo por el que RRF/scoring-real SÍ pudiera mover famtie hoy que no
  esté viendo (p.ej. cambiar qué entra al top-50 vía el orden pre-corte)?

---

## VEREDICTO DEL DÚO (2026-07-05 · sub-agente 5 + cross-model 6, solapan 2 → 9 únicos)
**La CONCLUSIÓN ("no re-medir ahora; trigger = queries reales") SOBREVIVE en ambos lados.
Dos de mis ARGUMENTOS no:** (1) [ambos] la conflación BM25 era real — DEC-085 zanja el
find-desde-la-pregunta; el scoring-por-resultado nunca se midió. El sub-agente verificó
que el mitigante es MÁS fuerte de lo que declaré: ts_rank es indefinido en los canales
metadata-regex, el único path rankeable-con-modelo es ILIKE cuya conversión a FTS ES la
celda {con-modelo} que DEC-085 ya midió NO-GO, y el orden de lo devuelto lo cubre el
tie-break → NO existe un brazo ts_rank barato con diana hoy. (2) [cross] "la fusión no
puede rescatar" sobre-generalizado — el propio tie-break lo refuta como mecanismo; lo
correcto: los residuales ACTUALES no son de clase ordenable (verificado en código: el
merge no trunca, RRF solo re-ordena lo devuelto → delta≈0 se sostiene).
**Hallazgo NUEVO del sub-agente (H1, verificado regla-C):** hp018·'1 A' se SIRVE en el
top-5 3/3 — es miss de CONTABILIDAD (doc tagueado ZXAE/ZXEE ≠ familia ZXe) → fix = packet
doc_map de Alberto, no retrieval. El residual real: 5 no-entran + 1 identidad-tag.
**Enmiendas aplicadas:** colateral DEC-050 degradado a prior (magnitud no medida
post-NOCAT); "valor cobrado" → "cobrado en famtie, bvg pendiente y ES el test del
colateral"; evidencia "no entran" anclada en convergencia s93+s95+s97 (no un trace único).
