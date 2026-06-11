# s61 — Diagnóstico del NO-GO del gate (mecanismos verificados)

**Veredicto del gate: NO-GO por D2** (regla pre-registrada: ambas ganancias
demostradas de s59 perdidas en la vista del CE). **D1 LIMPIO: 0/6 unánimes
fail-both** — el swap NO destroza el statu quo; pierde el upside.
Artefactos: `s61_gate_report.yaml` (veredicto) + `s61_gate_pools.json` +
`s61_gate_reranks.json`. Diagnóstico reproducible con los scripts
`_tmp_s61_{d2,hp001,dup}_diag.py` (locales, borrados tras la sesión; la
evidencia queda citada aquí).

## hp001 — pérdida de POOL (no del reranker): frontera del corte vectorial + drift de embed_query

- Las anclas (candado / 2222 / 1111) están en **0 de los 38 chunks** del pool
  L-i@ef120 fresco — el control LLM-sobre-el-mismo-pool tampoco las tiene: el
  reranker es INOCENTE de esta pérdida.
- El chunk ganador de s59 (`MI_372` p29, candado+2222) entró en s59 por el
  **canal vectorial** con coseno 0.52199 (sin stamp). HOY ese mismo chunk está
  en **rank 54** del canal (corte: 50) con coseno **0.5191** → la similarity
  de la MISMA query contra el MISMO chunk almacenado se movió **0.0029 entre
  sesiones** = dado de `embed_query` (Voyage no bit-estable). La nota del v4
  §0.3 lo había observado a nivel de 7º decimal (cat020); el drift real
  alcanza el **3er decimal**, y en la cola del ranking (chunks separados por
  milésimas) eso mueve la MEMBRESÍA del pool en la frontera del corte.
- Conclusión: la "ganancia demostrada" hp001 era **frontera-frágil de
  nacimiento** (rank ~50±5). No es recuperable por NINGÚN reranker; afecta
  IGUAL al plan B (MERGE v4) — es pre-merge. Se une a los "3 hechos rank
  56-70" que el v4 declaró fuera del techo → ya son 4 hechos demostrados en
  rank 51-70 (un ciclo futuro "profundidad/estabilidad del canal vectorial"
  tendría mecanismo medido 4 veces, no tuning).

## cat012 — efecto real del SWAP: near-duplicates monopolizan el top-5 del CE

- Las anclas de la tabla de consumos (h2: 24/72; h3: 179/345) **SÍ están en el
  pool** (rank 19/21/25, cosenos 0.65-0.68) y el **LLM-modal sobre el mismo
  pool SÍ las sube** (pos 1 y 3 de su top-5). El CE no: llenó su top-5 con 5
  chunks stamp-0.8 de contenido CASI idéntico — la fórmula §11 de baterías
  repetida en **3 revisiones del manual AM-8200** que conviven en el corpus
  (`AM 8200G Rv3` / `AM-8200` / `AM 8200N RV4`).
- Mecanismo estructural: un cross-encoder puntúa pares (query,doc)
  INDEPENDIENTES → contenido casi-duplicado obtiene scores casi idénticos y
  monopoliza el top-k (sin noción de redundancia). El LLM listwise ve la lista
  entera y diversifica implícitamente. Con 30+ fabricantes (más revisiones
  conviviendo), esto EMPEORA.
- No hay fix quirúrgico: los duplicados EXACTOS por content-hash son
  marginales (3/39 pools, 1 chunk c/u; cat012 NO incluido) — esto es
  **near-duplication por revisiones sin supersesión = TECH_DEBT #43**, deuda
  de CORPUS (congelado este ciclo). Un MMR/diversificador post-CE sería un
  lever nuevo con su propio ciclo.

## Colaterales medidos (gratis en el gate)

- **Corte-a-50 muerde 9/39** @ef120 (vs 4-8 en s58/s59 — más candidatos, más
  presión en la frontera; cat022-unánime incluido, que aun así retuvo anclas).
- **Latencia rerank**: CE p50=0.39s / p95=0.90s vs LLM p50=2.06s / p95=5.06s
  (~5× más rápido, como el diseño esperaba).
- **Determinismo CE con la representación final (header 2.0): 39/39 réplicas
  idénticas; orden-permutado: igual en todos los críticos aplicables** — los
  supuestos del gate-D se sostienen con el doc nuevo.
- **Churn vs frozen-s58: 35/39** (firma enmendada) — el A/B habría corrido con
  casi todo mover, regla-1 muy expuesta.
- cat014 short-circuit: paridad confirmada. 0 fail-opens, 0 llm-padded.

## Implicación para el ciclo (cuadro de decisión)

1. **Techo real del lever recortado**: hp001 fuera del alcance de cualquier
   reranker → techo +1-frágil (cat012, recuperable solo tratando
   near-duplicates) o +0. SHIP=Δ_net≥+2 de la tabla = inalcanzable de facto;
   solo quedaría la celda F7 (SHIP-por-estabilidad, Δ_net≥0).
2. **El claim de estabilidad queda RECORTADO con dato nuevo**: el CE elimina
   el dado del RERANKER (el componente mayor, 3/12 golds medido s60), pero el
   **dado de POOL-frontera** (embed_query, drift al 3er decimal) persiste con
   cualquier reranker — el producto puede seguir dando distinto top-5 entre
   días vía la cola del pool. "Matar el dado" era parcialmente alcanzable.
3. **El plan B hereda lo peor**: MERGE v4 @ef120 pierde hp001 igual (pre-merge)
   Y conserva el dado del reranker LLM. Su caso es hoy más débil que cuando se
   congeló.
4. El gate costó ~$1.5 y ~40 min, y evitó un A/B (~$30-50, horas) con
   desenlace casi seguro GRIS/ROLLBACK — la calibración DEC-016b funcionó.
