# s87 — Diagnóstico autónomo del cuello = SÍNTESIS · hallazgos

## Titular
**El "cuello = SÍNTESIS 103/132" (DEC-070/071/073) contaba hechos SINTETIZABLES (soportados por un
chunk del top-5), NO fallos de síntesis.** Midiendo la RESPUESTA actual directamente (instrumento
`synthesis_miss_judge.py`, juez GPT-5.5 K=5 a nivel-proposición, dúo-hardened; 2 gen para varianza): el pipeline
**sintetiza ~76-80% de los hechos en-contexto**; el cuello de síntesis ROBUSTO ≈ **16 stable-MISS → ~13-14 genuinos** (no 103),
una cola pequeña y HETEROGÉNEA. Refina (NO refuta) DEC-070/073 — es la re-caracterización que el PLAN
anticipaba ("puede re-caracterizar el número"). Atribución limpia: respuestas mejores que s67base con
el MISMO modelo/temp/tabla (verificado) → efecto de **VECTOR_NOCAT** (mejor retrieval → contexto más rico).

## Números (rep0, 1 generación; 39 dev, 103 SÍNTESIS by_target de 134 CORE)
| clase | n | qué es |
|---|---|---|
| **SYNTH-OK** | 82 | el bot transmite el hecho en-contexto (~90% fiable: 10/11 controles OK) |
| **SYNTH-MISS** | 20 | el hecho llega al generador pero la respuesta no lo transmite → certificado abajo |
| **NOT-IN-CTX** | 1 | el chunk-soporte cayó por `RELEVANCE_THRESHOLD`/jitter → retrieval/umbral, NO síntesis |

## Los 20 SYNTH-MISS, CERTIFICADOS (workflow 2-etapas: adjudica ciego + verifica adversarial; cross-model del juez GPT-5.5)
- **3-4 judge-FN** (el bot SÍ transmite, el juez GPT falló por ser muy estricto): cat011 '751' (=clarify
  correcto), cat016 'modo prueba', hp002 'reset inicial' [+ hp012 '10 lazos' contestado].
- **9 PARTIAL** (el bot transmite PARTE del hecho / omite granularidad): cat001 '1 o 2' (da "2", omite "1"),
  cat017 'licencia'/'CLSS', cat018 'Zona'/'Tipo SW', cat020, hp001 '1111', hp003 'cable puente', hp010.
- **~7 OMITTED genuinos**: cat013 'bucle cerrado', cat016 'ZONA+ELEMENTO', hp012 '99+99', hp013 'EEPROM',
  hp015 '32' (≈5 estables) **+ hp007 'cada 3/6 meses' = VARIANZA de generación** (el subset SÍ los transmitió).

**Mecanismo (de los ~16 reales, excl. judge-FN):**
- **completeness ~10** — el bot omite hechos secundarios/granulares. **Lever barato = prompt de completitud
  = SETTLED NO-GO en PASS** (DEC-051/s69, Δ_net=0). No hay lever barato nuevo aquí.
- **contradicts ~4 (FIDELIDAD, lo más interesante)** — el bot afirma algo INCONSISTENTE con el gold:
  · **hp001 '1111'**: dice que 1111 → "AJUSTES>AVANZADO"; el gold dice 1111=nivel USUARIO que NO da acceso avanzado.
  · **hp013 'EEPROM'**: dice "la config puede perderse"; el gold dice se CONSERVA en EEPROM (invertido).
  · **cat020**: limita 0-100% a OPT; el gold lo exige universal.
  · hp007 'cada 6 meses' (mezclado con varianza).
  → NO lo arregla un prompt de completitud; son errores de atribución/fidelidad (o matiz de gold) — per-caso.
- **hedge-defensive ~2** — el bot se escuda ("el manual no especifica X") pese al contexto: cat016 'ZONA+ELEMENTO',
  hp012 '99+99'. → posible anti-hedge prompt, N pequeño.

## Certificación del juez GPT-5.5 (dúo de agentes + trampa)
- **Over-credit (falso "conveyed"):** 1/11 controles = **hp018 '4 circuitos'**: el juez acreditó "4" pero la
  respuesta habla del producto EQUIVOCADO (ZXAE/ZXEE=MIE-MI-310, no ZX5e=MIE-MI-530) → es el issue de
  **IDENTIDAD/MODEL-FILTER conocido** (DEC-074, ~4 palanca), NO síntesis. ⇒ los ~4-5 "SYNTH-OK" de hp018 son
  espurios (my instrumento seedó de by_target, la tie laxa que la famtie ya corrigió a retrieval-miss=14).
- **Trampa (valor perturbado falso):** juez ESTRICTO en numéricos (7/7 valores falsos rechazados); único FP
  = negación semi-artefactual ('no enclavado'→'enclavado' con texto original) → cazado como punto blando.
- **Judge-FN (falso "omitido"):** ~3-4/20 (demasiado estricto con clarify/paráfrasis). **Ambas correcciones
  REDUCEN el cuello** → el ~15 es cota SUPERIOR conservadora.

## Caveats declarados
1. **Varianza de generación** (Sonnet temp=0 no-determinista, declarado en s67base): rep0=20 MISS, rep1=21 MISS,
   pero solo **16 stable-MISS** (omisión en AMBAS gen) · **9 flip** (MISS en 1 de 2, sensibles a estocasticidad:
   hp007 'cada 3m', hp001 '1111', hp015 '32', cat016 'modo prueba', cat018 'Apendice A', hp018 'diodo'/'sirenas'
   [identidad]) · **78 stable-OK**. ⇒ **cuello ROBUSTO = 16 stable-MISS**; −~2-3 judge-FN estables (cat011,
   hp002) − identidad-hp018 ≈ **~13-14 genuinos, bot-atribuibles**. Pipeline sintetiza ~76% robusto (78/103).
2. **Certificación por MUESTRA** (20 MISS + 11 controles), no los 103 individualmente; los 82 OK son spot-check
   (10/11 controles). Robusto al ±% en los 82.
3. **80% hechos transmitidos ≠ 80% PASS**: PASS es juez HOLÍSTICO (±2 ruido, s69) sobre la respuesta entera; un
   gold puede ser PARCIAL aunque transmita casi todo. **La relación fact-completeness↔PASS solo la da el eval PASS.**
4. Seed = by_target (103, tie laxa); la famtie canónica dio retrieval-miss=14. hp018 identity contamina el "OK".

## Recomendación de rumbo (Protocolo 2 — para Alberto; des-diferir PASS = TU gate)
1. **Des-diferir PASS ahora (medir el baseline actual).** El diagnóstico muestra que el pipeline mejoró
   materialmente (VECTOR_NOCAT) y el "cuello 103" era una cota, no fallos → el PASS actual probablemente subió
   mucho vs la última medición. No se puede planear el roadmap sobre un cuello sobre-estimado 5×. Tengo las
   respuestas frescas (rep0/rep1) → re-juzgar holístico es barato; **es tu gate, lo ofrezco, no lo corro solo**.
2. **NO hay lever barato de síntesis.** El cluster dominante (completeness) es settled-NO-GO en PASS; el resto
   es cola heterogénea (fidelidad×4 per-caso, hedge×2, judge-FN, varianza). "Atacar síntesis" como workstream
   está mis-dimensionado — la leverage real está en (A) catálogo/escala + retrieval foundational (DEC-074) + eval orgánico.
3. **3-4 fidelity-contradicts merecen un vistazo** (hp001 '1111', hp013 'EEPROM'): ¿error del bot, retrieval de
   sección equivocada, o matiz de gold? Per-caso, no un lever.

## Artefactos
`scripts/synthesis_miss_judge.py` (+ `_trampa.py`, `_calib_sample.py`, `_stability.py`), `evals/s87_synthesis_full.yaml`
(+ `_rep1`, `_subset`, `_trampa`), `evals/s87_calib_rows.json` + `s87_rows/`, workflow `s87-synthesis-adjudicate-lean`.
Dúo del brief: cross-model GPT-5.5 + sub-agente Opus (6/6, `adversarial_review_log`). reach≠PASS, NADA en prod.
