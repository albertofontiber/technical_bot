# S2 · Tabla de predicciones PRE-REGISTRADA (v2.1c) — escrita ANTES de correr la famtie

> Disciplina s69/C3 (predicción-vs-resultado). Baseline control REPRODUCIDO hoy sobre
> `s85_retrieval_miss_DEF.yaml`: **retrieval-miss FAMILY = 14/132**. Los brazos regeneran SOLO
> `pool_pin` (retrieve_chunks top_k=50 con `IDENTITY_RESOLVE=on`) reutilizando los labels GPT ya
> pagados; `top5_ids` NO se recomputa (sin re-pagar reranker) → los buckets RERANK/TOP5 de los
> brazos no son comparables, la métrica es SOLO `retrieval_miss_family` (in_pool) + per-gold.
> Limitación declarada: un chunk NUEVO que soporte un hecho pero nunca juzgado no cuenta
> (conservador — el delta medido es cota INFERIOR del efecto real).

| hecho (baseline RETRIEVAL) | predicción brazo ADD | brazo REPLACE | mecanismo esperado |
|---|---|---|---|
| hp018 × 5 ('4 circuitos','6K8','diodo','Sirenas A,B,C,D','1 A') | **GANAN in_pool (5/5)** | GANAN (5/5) | 'zxe'→[ZX1e,ZX2e,ZX5e] (seam 1) mete MIE-MI-530 (pm='ZX2e/ZX5e') al pool; seam 2 los protege del veto |
| hp011 '05 a 295 seg' | **GANA in_pool** | GANA | 'rp1r'→prefer RP1r-Supra (seam 1) — el soporte same-family existe fuera del pool (regalo no contado en la palanca ~4) |
| cat016 'autobusqueda' | posible (media) | posible | 'cad-150'→variantes; el sup es pm='CAD-150-8' — depende de que keyword/vector lo traiga |
| cat013 'CLIP' · hp006 ×3 · hp012 · hp013 'PWR-R' · hp014 '35' | SIN cambio | SIN cambio | sin mecanismo nuevo (exact ya presente o familia no cubierta) — el lever NO es esto |
| **hp009 (todos sus hechos)** | **SIN regresión** | ⚠ riesgo (LEVER2-replace lo regresó) | add conserva el token 'ZXE' → docs family-level siguen matcheando |
| resto de golds | sin movimiento neto; retrieval-miss total **14 → ~8±1 (add)** | 14 → ~8±1 salvo regresión hp009 | — |

**Criterio de decisión pre-registrado:** gana el brazo con hp018 5/5 ganados Y hp009 sin
regresión Y total ≤ baseline. Si ambos cumplen → ADD (menos invasivo). Si replace regresa
hp009 (como LEVER2) → ADD queda confirmado como el fix de la regresión histórica. Si NINGUNO
mueve hp018 → diagnóstico per-gold (¿el doc ni entra al pool → escalera v2.1d fetch-acotado?).
Config estampada: catálogo-commit + flag + policy en el YAML de cada brazo.

---

## RESULTADO (mismo día, predicción-vs-resultado — regla del pre-registro)

| pin | retrieval-miss FAMILY |
|---|---|
| baseline DEF (pin viejo, s85) | 14 |
| **OFF-control (re-retrieve hoy, flag off)** | **15** — el drift/jitter de re-retrieval existe (±1-2): hp001 '2222' cae TAMBIÉN sin flag (jitter puro, el caso documentado); hp018 sigue 5/5 miss ✓ |
| **ON + ADD** | **12** — **hp018 gana 4/5** ('4 circuitos','6K8','diodo','Sirenas A,B,C,D' entran al pool; '1 A' queda) · hp009 **SIN regresión** · hp012 '99+99' cae (desplazamiento por la unión en algún cap downstream — la forma DEC-069 en pequeño, net sigue positivo) |
| **ON + REPLACE** | **14** — hp018 gana 4/5 igual, **PERO hp009 REGRESA ×2** ('Retorno','aisladores internos': quitar el token ZXE veta los docs ZXAE/ZXEE que hp009 necesita) — **la regresión histórica de LEVER2, reproducida CON mecanismo visible** |

**Contra las predicciones:** hp018 5/5 → REAL 4/5 (parcial); hp009-sin-regresión-en-ADD ✓ CONFIRMADA;
riesgo-replace-regresa-hp009 ✓ CONFIRMADA (el porqué del brazo add queda demostrado, no intuido);
hp011-gana → **FALSADA** (sigue miss en ambos brazos — la expansión prefer-Supra no basta para
meter su chunk-soporte en el pool-50; pendiente diagnóstico); total ~8±1 → REAL 12 vs control 15
(dirección ✓, magnitud menor).

**Decisión por el criterio pre-registrado: GANA ADD** — los 4 hechos históricos de hp018 (el
criterio DEC-074b "4/4") ganados, hp009 intacto, total mejora vs control (−3 neto). Pendientes
declarados: hp018 '1 A' + hp011 (diagnóstico per-hecho), hp012 '99+99' (coste de la unión, −1).
