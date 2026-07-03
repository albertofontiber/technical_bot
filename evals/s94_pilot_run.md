# s94 · RUN del piloto — predicciones PRE-REGISTRADAS (escritas TRAS F0, ANTES de F1)

> Spec: `evals/s94_pilot_spec.md` v2 (post-dúo). Testbed F0: `evals/s94_f0_testbed.json` —
> 10 hechos (4 tabla / 6 prosa-datos), TODOS medibles (padre acreditable pre-mapeado;
> los 2 duplicados de s93 no dejan hechos incontables: hp001 tiene primario votado,
> hp011 conserva 1 acreditable). 12 docs, todos en el store.
> **Freeze:** voyage-4-large doc/query · HYDE off · receta R2 = blurb-B7-del-padre +
> enunciado (la del 2/4) · LLM extracción claude-sonnet-4-6 · pin base
> `s92_retrieval_miss_ON_add.yaml` (famtie 12) · catálogo en git · batch
> `extraction_sha256='s94-pilot:*'`.

## Clasificación F0 (base declarada por hecho en el JSON)
tabla (4): hp006 'ISO-X' · hp011 '05 a 295 seg' · hp013 'PWR-R' · hp018 '1 A'
prosa-datos (6): cat013 'CLIP' · cat016 'autobusqueda' · hp001 '2222' ·
hp006 'Fallo de Tierra' · hp012 '2 lazos / 396' · hp014 '35'
[Nota honesta: hp018 clasificado por base DECLARADA (sin match literal — bake-off);
hp012 '2 lazos/396' ídem (el enunciado ganador del track C venía de párrafo de capacidad).]

## Predicciones por brazo × clase (ANTES de correr F1/F2/F3)
| brazo | clase tabla (n=4) | clase prosa-datos (n=6) | mecanismo esperado |
|---|---|---|---|
| **R2 enunciado LLM** | **ganan 2-3** (hp011 ya cruzó en track C con esta receta; hp018 falló allí — el QA-fila + extracción dirigida puede recuperarlo; ISO-X plausible) | **ganan 2-4** (hp012 ya cruzó en track C; FdT cruzó en B con span→enunciado debería; cat013/cat016/hp001/hp014 inciertos — vocabulario operativo) | el enunciado con producto+sección cierra el vocab-gap |
| **R1 plantilla** | aplica a 3-4 (rows presentes), **ganan 1-3** | N/A (solo tablas) | pairing cabecera=valor ≈ enunciado (prior Pinecone) |
| **R3 resumen/tabla** | **ganan 0-2** (mejor donde la query es funcional: hp011 opciones-extinción, hp013 batería) | N/A-mayormente | el resumen matchea el REGISTRO de la pregunta |

- **Headline esperado (R2): 4-7/10.** GO-tabla (≥2 de 4): esperado SÍ. GO-prosa (≥2 de 6): borde.
- **Delta-check prefijo (antes de F2):** predicción — el prefijo-store mueve el coseno más
  que la tie-band ±0.003 en ≥2 de los 4 hechos track C (por eso R2 corre con blurb-padre).
- **Empate R1-vs-R2 en tabla:** diferencia de 1 hecho = ruido → gana R1 por coste (pre-registrado).
- **F3 guard:** nueva-miss fuera de ±2 sobre las 132 → NO-SHIP. Cada no-flip → triage `_trace`.

## Resultados (predicción-vs-resultado por fase)

### F1 — generación + QA (368 candidatos: R1 104 · R2 253 · R3 11; coste LLM ~$3)
- **Bug de instrumento cazado por regla-C (QA v1 → v2, declarado):** el QA v1 tumbaba el
  93% de R1 y el 50% de R2 por un fallo sistemático — trataba el nombre del PRODUCTO
  (discriminador EXIGIDO por el spec, inyectado desde metadata adjudicada del chunk) como
  token inventado cuando la tabla fuente no repite el modelo. **v2 = whitelist de metadata
  inyectada (pm/manufacturer/source_file) + resto de tokens estrictos + fact-bearing para
  hechos compuestos + fuente nivel-página.** Re-QA sin re-pagar LLM (v1 en `.v1.bak`).
- **QA v2: R1 0 fallos (por construcción) · R2 2 fallos REALES (el gate anti-alucinación
  muerde sin falsos positivos) · R3 0.** 29 candidatos fact-bearing QA-OK en 9/10 hechos
  (hp012 '2 lazos/396' sin candidato *detectable*: el enunciado dice "dos" en letra —
  límite del detector declarado; F3 lo mide igual vía famtie/padre).
- **Delta-check H4 ✓ predicción confirmada:** prefijo-store mueve el coseno 0.010-0.054 ≫
  tie-band en 3/3 medibles → R2 corre con blurb-padre (pre-registrado).

### F2 — probe (PRIORIZACIÓN; frontera proxy = sim#50 del canal real)
- **Corrección de instrumento (v1→v2, regla-C):** el gate fact-bearing era erróneo para el
  diseño SWAP (el flip lo da CUALQUIER surrogate del padre; el hecho juzgado vive en el
  padre). v2 = todos los QA-OK, dos niveles reportados.
- **Cruzan el proxy: R2 3/10** (hp006-FdT 0.592 · hp011 0.543 · hp012 0.608 — los 2
  ganadores del track C REAPARECEN) · **R1 1/10** (FdT 0.585) · **R3 0/10** (máx 0.522).
  Nadie se mata (R3 no llega a extremo-consistente); decide F3.

### F3 — famtie ON/OFF vs control mismo-día (predicción-vs-resultado)
Control HOY (sin inserts, flag off): **12** — lista IDÉNTICA al pin s92 (cero jitter, baseline limpio).

| brazo | famtie | flips testbed (10) | clase tabla (4) | clase prosa (6) | nuevas-miss | predicción → real |
|---|---|---|---|---|---|---|
| **R2 enunciado LLM** (251 surr.) | **12 → 6** | **5/10** (PWR-R · '1 A' · '35' · '2 lazos/396' · FdT) **+ colateral hp012 '99+99'** (clase diversify, fuera de testbed) | **2/4 ✓ GO-tabla** | **3/6 ✓ GO-prosa** | **0** (subconjunto estricto del control) | tabla 2-3→2 ✓ · prosa 2-4→3 ✓ · headline 4-7→5 ✓ |
| R1 plantilla (104 surr.) | 12 → 10 | 2/10 (FdT · '35') | **0/4 — predicción 1-3 FALSADA** | 2/6 | 0 | R1 NO compite: no hay empate, R2 gana el sub-decisor de coste |
| R3 resumen/tabla (11 surr.) | 12 → 8 | 4/10 ('2222'\* · FdT · **ISO-X** · '35') | 1/4 (ISO-X — que R2 no ganó) | 3/6 | 0 | 0-2→4: FALSADA al alza (11 surrogates, 4 flips — eficiencia notable) |

\* hp001 '2222' es el borderline documentado (padre→final en triage de R1/R2 con famtie-miss
en el mismo run): su flip en R3 puede ser jitter — lectura conservadora R3=3-4.

**Triage de los no-flips (H1 — el porqué de cada NO, no solo el conteo):**
- hp011 '05 a 295 seg': el padre ENTRA por el swap y muere en diversify → **mecanismo VIVO,
  killer = lever pipeline** (misma clase que '99+99'; backlog diversify, NO ingesta).
- cat013 'CLIP' · cat016 'autobusqueda' · (ISO-X para R2): padre→NUNCA — el mecanismo no
  alcanza ahí (coherente con el probe F2: cos 0.44-0.52 lejos de la barra).
- Nota de instrumento: "surrogate→NUNCA" en el triage es ESPERADO (el swap corre antes del
  primer stage del trace) — la presencia del padre ES la huella del surrogate (en control
  los padres jamás entran a canal, paso-0 s93).
- Unión R2∪R3 (no medida combinada — declarado): cubriría 7/10 + '99+99' → famtie ~4-5.
  Residual sin mecanismo: CLIP, autobusqueda (vocabulario operativo puro) + hp011 (diversify).

### F4 — decisión (para Alberto)
- **GO del mecanismo, criterio pre-registrado CUMPLIDO en las 3 barras (R2):** headline 5≥3 ✓
  GO-tabla 2/4 ✓ · GO-prosa 3/6 ✓ · guard 0 nuevas-miss ✓. **La famtie pasaría 12 → 6
  (−50%) solo con R2; ~4-5 con R2+R3.**
- **Brazo recomendado: R2 (enunciado LLM) + R3 como complemento barato** (11 resúmenes → 4
  flips; es además el patrón canónico de vendors). R1 descartado por medición (0/4 tabla).
- **Coste de escalar (estimación por-doc DECLARADA, no medición):** piloto ≈ $0.15-0.25/doc
  (12 docs, ~$2-3 LLM) → corpus 1.069 docs ≈ **$160-270 LLM** + embeddings marginales +
  **QA como línea APARTE** (gate automático fila-nivel es $0; muestreo humano/agente de
  fidelidad a presupuestar ~$10-30). Dentro de la banda ~$150-300 estimada en s93.
- **Effect-size corpus-wide = ESTIMADO** (extrapolación por-doc del testbed; H8) — la
  decisión de presupuesto es sobre "mecanismo GO con 5/10 medidos + estimación", no sobre
  una medición corpus.
- **Nada shippeado**: los surrogates se insertaron y REVIRTIERON por brazo (rollback
  verificado 0 restantes ×3); `PILOT_PARENT_SWAP` default off (5 tests); el ship real
  (pase corpus + multi-vector en producción) queda gateado por: (1) decisión de presupuesto
  de Alberto; (2) bvg PASS-control ±2 antes de encender nada en demo (coste juez, gate
  Alberto).
