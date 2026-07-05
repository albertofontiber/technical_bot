# s98 · Plan de continuación (post-challenges de Alberto, 5 jul) — PARA EL DÚO

## Directivas de Alberto (decididas, no a debate)
1. **hp009/hp018 = caso B**: MIE-MI-310 (ZXAE/ZXEE) NO sirve a ZXe → los golds citan el doc
   equivocado → **búsqueda exhaustiva del manual ZXe real + re-escribir el/los gold**.
2. **tie-break**: dejar el código, **flag OFF** (no shippear ahora; el rerank lo desbloquea).
3. **research con fuentes** para entender la BP del gap de vocabulario / próximo lever.

## Plan propuesto
- **P1 — Gold re-authoring (hp009 EOL-resistance ZXe + hp018 '1 A' ZXe):** procedimiento
  canónico RULER_DESIGN §2 — localización EXHAUSTIVA de TODOS los manuales ZXe (MIE-MI-530
  y familia, ES+EN) → grep del valor → render píxel + cross-model → adjudicación Alberto →
  re-escritura vía `gold_store`. Resultado posible: (a) el ZXe real documenta el dato →
  re-citar el doc correcto; (b) no lo documenta → el dato no es servible para ZXe → el gold
  pasa a admit/revisión. **Guardarraíl (declarado): el gatillo del re-write es GROUND-TRUTH
  de identidad (MIE-MI-310≠ZXe), NUNCA "que pase el sistema" — chunks_v2 jamás criterio.**
- **P2 — Merge a main (stop-line Alberto):** tie-break flag-OFF-inerte (documentado DEC-091b
  "bloqueado por rerank", como IDENTITY_FETCH) + catálogo doc_map + golds re-tipados s97c +
  golds re-escritos P1. `main` queda con el código inerte + los datos buenos.
- **P3 — Research sourced (adversarial, patrón s95):** BP del gap de vocabulario query↔doc,
  con foco en las DOS clases del residual: **"recuperado-no-servido" (rerank)** vs
  **"no-recuperado" (document-side)**. Verificar con fuentes: (a) rerankers que razonan
  relevancia (LLM-rerank prompt/modelo, cross-encoders SOTA); (b) hypothetical-questions /
  proposition-indexing estado-del-arte 2024-25; (c) ¿hay BP más nuevo que Doc2Query(2019)/
  Dense-X(2023)?; (d) ¿embedders instruction-tuned cierran el gap más barato?
- **P4 — Próximo lever (gateado por P3 + GO de Alberto):** HIPÓTESIS a validar/refutar: el
  **rerank** es la mayor relación leverage/coste (arregla la clase "recuperado-no-servido"
  como hp001 + desbloquea el tie-break ya construido). Antes de gastar: correr el split
  "no-servido vs no-recuperado" sobre los residuales-core (instrumento TECH_DEBT #72) para
  decidir con dato dónde va el euro, no por la conclusión de hoy.

## Preguntas explícitas para el dúo
1. ¿El orden P1→P2→P3→P4 es correcto? ¿algo mal secuenciado (p.ej. merge antes de re-write)?
2. **¿Me estoy enamorando de la conclusión de hoy (el rerank)?** El diagnóstico hp001
   (recuperado-no-servido) es de 1 gold. ¿Es sólido inferir "el rerank es la mayor palanca"
   de un caso, o hay sesgo de reciente-y-vívido? ¿Qué evidencia lo confirmaría/refutaría?
3. **P1 riesgo de circularidad:** re-escribir un gold que "falla" roza el anti-patrón de
   editar el ruler para que el sistema pase. El gatillo aquí es identidad (MIE-MI-310≠ZXe),
   no retrieval — ¿es defendible, o hay riesgo de que "MIE-MI-310≠ZXe" sea a su vez frágil y
   estemos re-escribiendo sobre arena? ¿Cómo lo blindamos?
4. ¿Falta algún paso (p.ej. auditar los otros 21 top-5 que el tie-break cambió y no
   flipearon PASS, por si esconden más hp001-clase antes de cerrar el veredicto)?
