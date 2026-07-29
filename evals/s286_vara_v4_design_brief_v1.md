# s286 — Vara v4 del juez bvg: el juez VE core vs supplementary (T2b adjudicado por Alberto)

## OBJETIVO + MÉTRICA
Cerrar la clase «PARCIAL por supplementary» estructuralmente (4/20 PARCIAL del baseline v2 eran
cores-4/4; Alberto rechazó el parcheo selectivo (a)+(c) como tech-debt y adjudicó (b): pasar
`atomic_facts`+`tipo` al juez para TODOS los golds — sentada r2, marca ✏️ en T2). MÉTRICA: la
vara pasa de prosa-del-gold a **facts tipados**; se declara **vara v4 SIN comparabilidad hacia
atrás** (precedente v3, DEC-160) y se estampa en LA re-baseline única del arco. El JUEZ (modelo
GPT-5.5) NO cambia — freeze DEC-023 intacto; cambia solo su INPUT/instrucción (vara).

## DISEÑO
1. `judge()` recibe además `facts` = lista de atomic_facts del gold: `[{texto, tipo}]`
   (cita/valor/estado NO se pasan — ruido; el texto del fact es la exigencia).
2. `_JUDGE_USER` v4 añade tras la RESPUESTA GOLD:
   «FACTS DEL GOLD (tipados):\n- [CORE] …\n- [SUPP] …» + criterio nuevo:
   - **PASS** = todos los CORE cubiertos (o la conducta esperada no-answer correctamente
     ejecutada). **La ausencia de un fact SUPP JAMÁS baja de PASS por sí sola.**
   - **PARCIAL** = falta ≥1 CORE pero lo servido es correcto y útil.
   - **FALLO** = igual que v3 (incorrecto/alucina/conducta equivocada).
   - Un CORE cubierto con otras palabras/estructura CUENTA como cubierto (anti-formato).
3. La prosa `gold_answer` se mantiene como referencia de CONTEXTO (el juez la sigue viendo);
   los facts son la lista de exigencia. (Resuelve hp020(b): «CLSS comparte credenciales» es
   SUPP → ya no puede causar PARCIAL.)
4. Golds sin atomic_facts (¿hay?): fallback a vara v3 para esa fila + WARNING visible (censo en
   el build; si todos tienen facts, el fallback queda como guard).
5. Mismo cambio espejo en `test_multiturn_vs_gold.py` (comparte el defecto de contrato, como
   con el [:3000]) — se aplica el MISMO día para que la vara MT no diverja; su re-medición e2e
   queda para cuando toque (precedente DEC-160a).

## ALTERNATIVAS DESCARTADAS
- (a) statu quo + (c) reescritura selectiva de prosa: rechazada por Alberto (tech-debt que no
  se sostiene: «o lo hacemos para todos o el selectivo es tech debt»).
- Score numérico por-fact (contar cores cubiertos → umbral): más «medible» pero cambia el
  contrato de veredicto entero (PASS/PARCIAL/FALLO) y rompe TODA la maquinaria downstream
  (gates, gold_store usage, packets) — desproporcionado hoy.
- Dos jueces (facts + prosa) con fusión: coste ×2 por respuesta sin evidencia de necesidad
  (s47: 0 catches únicos del segundo juez).

## GAPS DECLARADOS
1. Los facts fueron autorados como átomos de exigencia pero NUNCA consumidos por el juez —
   puede haber facts con redacción no-autocontenida (dependen de la prosa). MITIGACIÓN: censo
   pre-build de facts «cortos» (<25 chars) o con referencias anafóricas («ver arriba», «dicho
   parámetro») → lista para revisión; si aparecen, se corrigen vía gold_store (mecánico, sin
   re-adjudicar contenido).
2. El delta del baseline puede ser POSITIVO artificialmente (la clase B desaparece por diseño)
   — DECLARADO: es el objetivo adjudicado, no inflado; la comparación honesta es dentro de v4.
3. Sesgo de lista: el juez podría degradar a checklist literal e ignorar equivalencias — el
   criterio anti-formato (§2) lo instruye explícitamente; el A/B de humo lo verifica.

## PLAN
1. Censo de facts problemáticos (gap 1) + fix mecánico si procede.
2. Implementar v4 en ambos harnesses + tests unitarios del formateo de facts.
3. Humo A/B barato: 6 qids conocidos (los 4 clase-B [cat008, hp003, hp008, hp020] + 2 controles
   PASS) × v3-vs-v4 × 1 — verificar que la clase-B se resuelve y los PASS no se caen por
   checklist-bias.
4. Dúo (eval/vara = zona de dolor) sobre brief+diff ANTES de la re-baseline.
5. LA re-baseline única (~$3) con la config-de-ship completa → línea de salida del OBJETIVO.
