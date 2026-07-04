# T1 · RUN — pre-registro (escrito ANTES de lanzar el pase)

> GO de Alberto (3-jul): T1 con vintage p1 (claude-sonnet-4-6, prompts v1 congelados,
> temperature=0) + side-by-side Sonnet 5 (candidato p2) en ~10 docs para decidir T2-T3.
> Selección determinista: `evals/t1_selection.json` — **36 docs, coste proyectado $100**
> (14 piloto [gate reproducción] + 15 unseen [Aritech isPerfect=0.30, Kidde 0.35, ES 0.47
> — estrés de layout] + 7 marca-gold). Batch: `enunciados-v1:T1:p1` (rollback selectivo).

## Gates PRE-REGISTRADOS (plan s94b v2 + DEC-087)
| gate | criterio | si falla |
|---|---|---|
| **G1 reproducción** (el duro) | famtie con `ENUNCIADOS_MULTIVECTOR=on` ≤8, con **≥4 de los 6 flips de DEC-086** reproducidos | NO se lanza T2; diagnóstico prompt/pipeline; rollback opcional |
| **G2 no-regresión** | famtie flag-on sin nueva-miss fuera de ±2 (132 facts) | rollback batch + diagnóstico |
| **G3 panel (demo real, flag off)** | compare vs pin: <20% de queries con overlap<0.8 (suelo medido: 0/59, peor 0.98) | investigar antes de seguir |
| **G4 QA/cobertura** | umbral por-marca CALIBRADO con los primeros ~20 docs (banda mediana ±10 pts); cobertura reportada por doc | marca fuera de banda → su lote se revisa antes de T2 |
| **G5 muestreo estratificado** | ~10-15/estrato (marca × isPerfectTable) sin mispairing sistemático | prompt p2 para esa marca (vintage marcado) |

## Predicciones (antes de correr)
- Reproducción: 5-6 de los 6 flips (mismo prompt/modelo; el ±1 por jitter hp001-clase).
- QA-rate: banda 75-90% por marca (el smoke dio 78% en doc denso); Aritech/Kidde (isPerfect
  bajo) en la parte baja de la banda.
- Panel flag-off: 0 alertas (el invariante excluye surrogates del servicio; el único canal
  de efecto es el post-filtro HNSW del RPC — esperado ~nulo).
- Coste real: $80-110 (proyección $100 ±10%).
- Side-by-side p2 (Sonnet 5, ~10 docs, DRY): predicción — QA-rate de p2 ≥ p1 con delta
  pequeño (+0-5 pts); si p2 gana con margen → T2-T3 con p2 (vintage marcado).

## Side-by-side p1 (Sonnet 4.6) vs p2 (Sonnet 5) — 6 docs unseen, DRY, pareado
| métrica | p1 (Sonnet 4.6) | p2 (Sonnet 5) | Δ |
|---|---|---|---|
| QA-rate (ins/gen) | 90.0% (404/449) | **92.6%** (522/564) | **+2.6 pts** (p2 gana 4/6 docs) |
| cobertura media | 0.961 | **1.000** | **+3.9 pts** (p2 cubre 6/6 docs al 100%) |
| enunciados útiles | 404 | **522** | **+29%** |
| pricing $/MTok (in/out) | $3 / $15 | $3 / $15 — **intro $2 / $10 hasta 2026-08-31** | Sonnet 5 ≤ coste, más barato con intro |

**Veredicto (criterio pre-registrado "p2 ≥ p1 con margen → T2-T3 con p2"): CUMPLIDO — p2 gana en las 3 métricas Y cuesta menos.** Fixes de compat Claude-5 aplicados (sin `temperature`, ThinkingBlock). Recomendación T2-T3: **Sonnet 5 (p2)**.

**Dos honestidades declaradas (no zanjadas por el side-by-side):**
1. El **+29% de volumen** es más celdas findable (QA-OK, no verbosidad — el gate lo filtra) PERO también +29% de chunks en el índice → más coste de embedding + mayor riesgo de desplazamiento. **Gate: el panel G3 debe confirmar que el volumen extra no mueve queries sanas antes de comprometer T2-T3 a p2.**
2. p2 corre con **temperature default (no pineada)** — la familia Claude-5 la deprecó; menos reproducible run-a-run que p1 (temp=0). Lo absorbe el QA-gate + idempotencia-por-batch, pero el vintage p2 se marca en el batch (`enunciados-v1:T2:p2`) para mezcla visible.

## Resultados
- Pase p1: **14/14 docs, 21.995 enunciados** insertados (Sonnet 4.6, batch T1:p1). QA-rate
  por-doc 75-95% (mediana ~89%); cobertura 0.42-0.91 (mediana ~0.62). Invariante intacto
  (0 surrogates sin parent_id).
- Side-by-side p2: ✅ (arriba) — Sonnet 5 gana; recomendación T2-T3 = Sonnet 5.

### ⚠️ GATE G1 (reproducción): **FALLA — y destapa un fallo ARQUITECTÓNICO del enfoque**
| medición | retrieval-miss |
|---|---|
| baseline pre-T1 (control limpio, s94) | **12** |
| control post-inserción (multivector OFF, ef_search 120) | **19** ⚠ |
| control post-inserción + iterative_scan (fix pgvector 0.8) | **17** (recupera parcial) |
| multivector ON (swap surrogate→padre) | **13** |
| flips DEC-086 reproducidos | **2/6** (criterio ≥4/6 → FALLA) |

**Causa raíz (confirmada por composición del índice):** los 21.995 surrogates entraron al
MISMO índice HNSW que los 22.339 chunks reales (índice casi ×2, 47% surrogates). Con
`ef_search=120`, el traversal explora 120 candidatos de los que ~la mitad son surrogates
que el filtro `parent_id IS NULL` descarta DESPUÉS → ~60 chunks reales efectivos vs 120 →
**recall de los chunks ORIGINALES cae (12→19)**. `iterative_scan` (el fix estándar de
pgvector 0.8) solo recupera a 17 — no basta. Y el multivector (13) queda NETO PEOR que el
baseline limpio (12): la dilución + el enterramiento del enunciado relevante entre sus
miles de hermanos del mismo doc anulan el beneficio que el piloto s94 midió con 251
surrogates dispersos y dirigidos.

**Por qué el piloto s94 NO lo vio:** 251 surrogates transitorios (dilución despreciable) +
dirigidos solo a las regiones-de-hecho. A escala de docs-enteros el mecanismo se ahoga.

**Lo que T1 compró (~$50-75): cazó un fallo de arquitectura ANTES del gasto de corpus
($150+).** Es el diseño de tramos funcionando exactamente para esto.

**Fallo latente cazado de paso + arreglado:** la FK `chunks_v2.duplicate_of` no tenía
índice de soporte → cada DELETE hacía seqscan por-fila (timeout al borrar el batch).
Añadido `idx_chunks_v2_duplicate_of` (migración 009) — mejora permanente.

**Restauración (rollback documentado) + hallazgo operativo:** 21.995 enunciados volcados a
`evals/t1_surrogates_dump.jsonl` (preserva el trabajo) → batch borrado → RPC revertido a 007
(sin iterative_scan) → schema T0 CONSERVADO (infra válida). **CLAVE: borrar las filas NO
restauró el recall (control post-delete = 17) — pgvector deja los vectores borrados como
FANTASMAS en el grafo HNSW hasta VACUUM.** `VACUUM chunks_v2` → **control = 12, lista de
misses IDÉNTICA al baseline s92** (demo restaurada, dilución confirmada al 100%). Migraciones
DB del episodio: 008 (iterative_scan, diagnóstico) → 009 (idx duplicate_of, PERMANENTE) →
010 (revert RPC a 007) → VACUUM. Estado final = pre-T1 + el índice 009 nuevo.

### Veredicto: NO-GO al enfoque "surrogates en el índice compartido". Redesign necesario.
El mecanismo (enunciados→findability) sigue vivo — el piloto s94 lo midió — pero NO puede
compartir el HNSW con los chunks reales. Opciones de redesign (→ dúo + decisión Alberto):
- **A) Tabla/índice HNSW SEPARADO para surrogates** — el canal multivector busca ahí y hace
  swap al padre; el índice real queda limpio (12). El fix propio.
- **B) Índices HNSW PARCIALES** (uno WHERE parent_id IS NULL, otro WHERE NOT NULL) en la
  misma tabla — el RPC usa el que toca. Menos invasivo que tabla nueva.
- **C) Generación DIRIGIDA** (no docs-enteros) — reduce el volumen y el enterramiento;
  combinable con A/B.
Coste ya gastado: ~$50-75 (T1) — sin pérdida de aprendizaje. Nada de T2-T3 hasta redesign.
