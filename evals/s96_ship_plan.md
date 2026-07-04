# s96 · Plan "cómo proceder" post-s95 (pre-registro **v2 POST-dúo**)

> v1 → v2: dúo completo (sub-agente Fable fresco 7 hallazgos + cross-model GPT-5.5 con
> tools 6; solapan en 2 → **11 únicos, 11 confirmados regla-C, 0 FP; 3 críticos**).
> Los 2 fixes de CÓDIGO ya están aplicados y testeados (no esperan al ship):
> **[H1 CRÍTICO]** fail-open propio del canal enunciados (sin él, un hiccup de Supabase
> en el RPC nuevo mataba el canal vectorial ENTERO en silencio — el "fallo que nadie
> había mencionado"); **[H3]** parser estricto de `ENUNCIADOS_MULTIVECTOR` ('true'/'1'
> eran OFF silencioso; typo → fail-fast — el ship es literalmente una env var en Railway).
> Tally: `evals/adversarial_review_log.jsonl` 2026-07-04 (2ª ronda).

## Propuesta (5 puntos)

### P1 — Gate bvg de A3 (~$10-20, CORREGIDO [H2 crítico ambos lados])
**Instrumento: `scripts/bvg_kmajority.py`** (K=5 + juez GPT-5.5 K-mayoría + partición
PASS-control/K-INESTABLE + run-manifest DEC-021§F) — v1 citaba `test_bot_vs_gold.py`,
que es el single-pass de DIAGNÓSTICO (un juicio por gold, sin ejes, sin banda de ruido
medida): con él, el criterio ±2 no tenía ancla. **El ±2 está medido con K-mayoría en
DEC-051(d)** (v1 citaba DEC-071 — cita errónea).
- **Dos brazos** control(off)/tratamiento(on), `BVG_RUN_ID` por brazo.
- **Build previo (pequeño, declarado — v1 lo presuponía sin existir):**
  (a) stamp en el manifest de `ENUNCIADOS_MULTIVECTOR` + count/fingerprint de
  `chunks_v2_enunciados` [H5: sin él, los artefactos no pueden probar qué brazo son —
  la clase de fallo que el propio manifest documenta para series_registry];
  (b) timing por query (NINGÚN harness emite latencia hoy [H2]);
  (c) el frozen `top5` de bvg_kmajority SÍ conserva `_swapped_from_surrogate` → la
  métrica "padre swapeado sobrevive al top-5 y se cita" ES computable ahí (no en TBG).
- **Ejes:** veredicto PASS/PARCIAL/FALLO (K-mayoría) + **eje invención vía
  `atomic_scorer --llm`** (v1 decía "sin subida" sobre un harness que no lo emite [H2]).
- **Criterio de ship:** Δ_net PASS-control tratamiento-vs-control dentro de ±2
  (no-inferioridad; ganancia no exigida — root-cause RETRIEVAL = 2/30); invención sin
  subida (atomic_scorer); latencia e2e añadida p50 <1s **medida end-to-end** (el coste
  flag-on real = 2º RPC + colapso de 200 + GET de hidratación de padres, y el swap corre
  en vector Y keyword — v1 lo enmarcaba como "~100-300ms del 2º RPC" [corregido]).
- **R3 de v1 RETIRADO [H4]:** era falso — `vector_search` corre UNA vez por query en el
  path de servicio (call-site único; los canales por-modelo son GETs léxicos que no tocan
  el RPC). Riesgo sobre-declarado, escrito sin verificar el código. Mea culpa registrada.
- **Si pasa → decisión de Alberto:** flag on en Railway (env var, reversible) +
  **[H7] post-flip: smoke del bot completo + verificación en producción-demo +
  verificación del flag efectivo** (parser estricto ya protege el typo). **Held-out:**
  bajo el modelo operativo s84 (DEC-071e: eval PASS diferido, stop-line tests-verdes) la
  corrida-única held-out NO se consume aquí — se declara explícitamente, no se omite.
- **Si degrada >2 → NO ship**, diagnóstico con el trace del top5 congelado.

### P2 — Deep-lookup (D): APARCAR flag-off — verificado limpio por el dúo
Sin residuos en el path de servicio (import lazy, parser fail-fast, default off).
**Re-encuadre multi-turn = HIPÓTESIS DE PRODUCTO, no conclusión de s95 [H6 + cross]:**
y el caveat viaja escrito — el fallo de SELECCIÓN medido (páginas razonables-pero-no-aguja
en el smoke hp013) TRANSFIERE al modo multi-turn; el modo sesión-de-dispositivo solo
arregla trigger y coste, no la puntería. Medición futura = query_logs reales.

### P3 — T2-T3: DIFERIDO demand-driven (sin cambios; coherente DEC-089(3)/DEC-049)

### P4 — Packet doc_map → Alberto (sin cambios; $0)
MIE-MI-310↔¿zxe? (DB: ZXAE/ZXEE) · MIDT190↔¿sdx-751? (DB: ID3000) · 15092SP↔¿hp012? (DB: INA).

### P5 — Diversify (hp011 + '99+99') como siguiente lever de eval; no se ejecuta sin GO.

## Estado de fixes del dúo
| # | fix | estado |
|---|---|---|
| H1 | fail-open propio del canal enunciados | ✅ APLICADO + test |
| H3 | parser estricto del flag | ✅ APLICADO + test |
| H2/H5 | P1 sobre bvg_kmajority + stamp manifest + timing + atomic_scorer | pre-registrado (build de P1, gateado por GO) |
| H4 | R3 retirado | ✅ corregido en este doc |
| H6/H7 | caveat selección multi-turn + post-flip/held-out | ✅ escritos arriba |
