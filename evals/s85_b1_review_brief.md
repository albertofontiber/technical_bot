# s85·B1 — Revisión del diagnóstico FINAL de retrieval-miss (etapa-de-fallo × motivo)

**Qué reviso (Protocolo 3, zona de dolor retrieval; el output DIRIGE los levers de B2 → un MECE roto
propaga un lever mal elegido):** el diagnóstico `scripts/retrieval_miss_diagnose.py` tras 2 rondas de dúo.

## Contexto (verificado, no re-litigar)
- Baseline canónico: pasada definitiva 39/39 limpia (n_fail=0), pin del pool exacto. famtie family-aware
  = **14 retrieval-miss** (todos legítimos: soporte SAME-FAMILY en el manual pero no en el pool). CORPUS-GAP=1
  (hp011 'r.1', token-corto = FN residual del pre-filtro léxico del manual — servible, prior corpus-gap≈0).
- El tie family-aware corrige el error de hp018 (by-target acreditaba MIE-MI-310=ZXAE/ZXEE para ZXe/MI-530).

## El diagnóstico (v3, tras el dúo)
Por cada miss, clasifica por la ETAPA-DE-FALLO del pipeline REAL (vía `retrieve_chunks(_trace=...)`,
instrumentación inerte, 354 tests) — MECE: RECALL | MERGE | SUPERSEDED | MODEL-FILTER | DIVERSIFY |
LANGUAGE | DEPTH. K=3 corridas (moda + jitter, porque el retrieval de identidad puede ser inestable).
- Fix v2→v3: **trazar solo los val_chunks SAME-FAMILY** (antes trazaba los wrong-family que SÍ están en
  pool → falso IN-POOL para hp018). Y manual_pin tiene pm=None → fetch por-ID.

## Resultado (K=3 estable, jitter=[])
**RECALL 10 · MODEL-FILTER 4.**
- MODEL-FILTER 4 (hp018): `_filter_to_query_models` (resolución 'ZXE') expulsa el manual ZX2E/ZX5E correcto
  y mantiene ZXAE/ZXEE. Verificado: pool hp018 = determinista SOLO ZXAE/ZXEE, 0 ZX2E/ZX5E. → identidad.
- RECALL 10: el chunk-valor no lo surfacea ningún canal (motivos: within-doc/es-en/token-corto).

## Lo que el dúo DEBE atacar
1. **¿La ETAPA-DE-FALLO es MECE + fiable ahora?** El trace usa el pipeline real (no universos paralelos como
   v1). ¿Algún miss donde la etapa sea ambigua/mal-detectada? ¿El K=3 es suficiente para el jitter, o hay
   misses jittery no cazados (jitter=[] hoy)?
2. **¿El fix same-family es correcto?** ¿Filtrar val_chunks a same-family puede DEJAR FUERA el chunk-valor
   real en algún caso (p.ej. familia mal resuelta → val_chunks vacío → trace vacío → RECALL espurio)?
3. **¿RECALL vs MODEL-FILTER bien separados?** hp018 '1 A' salió RECALL (no MODEL-FILTER como los otros 4) —
   ¿correcto (su chunk ZX2E/ZX5E ni entra a channels) o artefacto?
4. **¿Los MOTIVOS (predicados independientes) son fiables?** `_lang` (es-en) sobre content[:800] con umbral;
   `token-corto` (len≤4); `within-doc`. ¿FN de es-en en tablas EN con poca prosa (el caso que más importa)?
5. **¿El diagnóstico es ACCIONABLE para B2?** RECALL→recall(HyDE/embedding/keyword/sinónimos+es-en),
   MODEL-FILTER→identidad. ¿El mapa lever es estructural/BP, o hay celdas vagas?
6. **CORPUS-GAP=1 (hp011 'r.1')**: ¿es realmente FN del pre-filtro léxico (token corto), o hay algo más?

## Gaps declarados
- CORPUS-GAP=1 residual (hp011 'r.1', token-corto).
- La resolución source-naming de la familia es un parche B0 (DEC-065 aparte); los miss-golds resuelven bien.
- El motivo es-en usa heurística de keywords (posible FN en tablas EN numéricas).
