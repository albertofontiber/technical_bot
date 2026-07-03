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

## Resultados (se rellenan al medir)
- Pase p1: pendiente
- Gates G1-G5: pendiente
- Side-by-side p2: pendiente
- Coste real: pendiente
