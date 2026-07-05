# s97 · Veredicto de ship del tie-break — A ATACAR por el dúo

> El autor (Opus 4.8) concluye GO-marginal y necesita verificación independiente: la
> conclusión "churn benigno" CONVIENE a su sesgo pro-GO. Datos: `evals/s97{ctl,on}_*`.

## Resultado del gate bvg (2 brazos, A3 on en ambos, solo varía DIVERSIFY_TIEBREAK)
- **PASS-control: control 15 → tratamiento 14 (−1)**, dentro de banda ±2.
- **Invención (proxy conductas del juez): 9 → 8 conflicto** — no sube.
- **Churn: 26/39 golds cambian top-5. 5 flipan verdicto:**
  - ENTRAN en tratamiento: cat012, hp007
  - SALEN en tratamiento: cat021, hp001, hp013

## CLAIMS DEL AUTOR (a verificar/refutar contra los datos)
1. **"El churn es benigno":** en cat021/hp001/hp013 el tie-break desplazó chunks de BAJA
   relevancia (cat021: Tabla-28-cableado + reference-docs; hp001: usuario-p10-"primer
   arranque" + usuario-p21-"icono info contacto"; hp013: p25-"control estanqueidad" +
   p64-"puesta en funcionamiento") y promovió chunks config/pág-1 MÁS pertinentes → los
   flips son ruido de frontera K-mayoría, NO daño de contenido.
2. **"−1 indistinguible de 0":** es un solo run dentro del suelo ±2 (lección DEC-090).
3. **"NO es re-barajado PROFUNDO tipo DEC-050":** DEC-050 fue merge global mutante con
   colateral masivo; esto es tie-break within-source, churn neto −1, mecanismo lateral.
   → NO dispara la cláusula "re-barajado profundo = NO-GO sin racionalizar".

## PREGUNTAS PARA EL DÚO (bite anclado en los datos, no cortesía)
1. ¿Los 3 golds que caen son de verdad K-frontera / desplazamiento-de-basura, o el
   tie-break sacó un chunk LOAD-BEARING? Verifícalo: mira `s97{ctl,on}_frozen_contexts.json`
   (top5 por gold) + `s97{ctl,on}_judgments.json` (¿eran unánimes en control? ¿por qué
   FALLA el tratamiento — falta contenido o el juez fluctúa?) + el gold real de cada uno.
   cat021 era UNÁNIME 5/5 en control → ¿regresión real o coincidencia?
2. ¿"−1 dentro de ±2" + "26/39 top5 cambian" cuenta como el "re-barajado profundo" que el
   pre-registro (`s97_diversify_tiebreak.md`) marcó NO-GO? ¿O el autor está estirando
   "profundo" para esquivar su propio tripwire?
3. ¿Los que ENTRAN (cat012, hp007) son ganancias reales del tie-break o el mismo ruido en
   la otra dirección? Si son ruido, el "neto −1" es realmente "±ruido", no un pase.
4. ¿Falta alguna medición barata que zanjaría esto mejor que el juicio del autor (p.ej.
   K≥2 del PASS para separar señal de ruido antes de shipear)?
5. Veredicto: ¿GO (letra), NO-GO (tripwire), o "insuficiente — re-medir K≥2 antes"?
