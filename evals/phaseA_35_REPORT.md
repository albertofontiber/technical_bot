# Fase A (noche s38) — #35 juez-LLM de completitud de prosa · DATOS CRUDOS para sign-off (B1)

> **NO está validado.** Esto es evidencia cruda para que Alberto firme (o no) en B1. Sin narrativa
> de "mejora": los datos, y los rescates a spot-chequear.

## Qué se construyó
`scripts/atomic_scorer.py`: overlay LLM (`--prose-llm`, **DEFAULT OFF**) que, sobre hechos de PROSA
que el matcher mecánico marcó AUSENTES (solape de palabras < 0.8), pregunta a GPT-5.5 si el bot los
CUBRE por significado. Solo **RESCATA** (False→True), nunca baja. `match_fact` mecánico **sin tocar**.

## Equivalencia (mecánico idéntico sin el flag)
El overlay está gated en `prose_client is not None` (None sin `--prose-llm`) + función nueva no-usada +
param opcional default None. El camino mecánico es **byte-idéntico** por construcción. Verificado: el
módulo carga, `--help` ok, y el run mecánico produce los veredictos de siempre (abajo, "before").

## Bug cazado AL CORRER (no solo razonar)
La 1ª corrida de `--prose-llm` disparó **también** el eje factual (hp005/11/13/20 → "alucinación")
porque el check factual estaba gated en `if client:` y `--prose-llm` construye client. **FIX**: gatear
el factual en `args.llm` (no en que exista client). Re-corrido limpio → tabla de abajo.

## Before/after (mismos answers cacheados k5; eje COMPLETITUD aislado, factual OFF)
| qid | mecánico (before) | prose-LLM (after) | Δ |
|---|---|---|---|
| hp003 | core 2/4 | core **3/4** | +1 |
| hp005 | core 2/4 | core **3/4** | +1 |
| hp007 | core 4/7 | core **6/7** | +2 |
| (otros 16) | = | = | sin cambio |

- **Ningún veredicto cambió de CATEGORÍA** (los 3 siguen PARCIAL; #35 NO infló ningún FALLO→PASS).
- **NO sobre-acreditó conducta**: hp013/17/19 siguen FALLO-admite; los admit/clarify intactos.
- → #35 se comporta conservador: solo sube el conteo de completitud dentro de PARCIAL.

## Los 4 rescates — SPOT-CHECK de Alberto (¿paráfrasis legítima o over-credit?)
1. **hp003** valor=`'rojo y negro'` (overlap 67%) → CUBIERTO. *(colores cable batería; plausible)*
2. **hp005** valor=`'misma zona o subzona'` (75%) → CUBIERTO. *(coincidencia de zona; plausible)*
3. **hp007** valor=`'cada 3 meses'` (67%) → CUBIERTO. *(frecuencia mantenimiento; plausible)*
4. **hp007** valor=`'cada 2 años'` (67%) → CUBIERTO. ⚠️ **SOSPECHOSO**: revisar si el bot dice de
   verdad "cada 2 años" o lo confunde con "anual" (mismatch de frecuencia = over-credit). Si es
   over-credit → #35 necesita endurecer el prompt (ser más estricto con valores numéricos en prosa).

## Criterio de aceptación B1 (de `docs/CATALOG_PLAN.md`)
(i) ningún FALLO→PASS espurio ✅ (ninguno); (ii) flips de completitud = paráfrasis correcta verificable
→ **3/4 plausibles, 1 a verificar (hp007 'cada 2 años')**; (iii) sin sobre-acreditar admit/refuse ✅.
**Tu llamada**: si el #4 es over-credit, endurecer el prompt de prosa antes de usar #35 en el catálogo.

## Ficheros
`evals/phaseA_35_mechanical.txt` (before) · `evals/phaseA_35_prosellm.txt` (after, con el detalle
por-hecho). Branch `eval/s38-night-catalog`. Nada tocó prod ni se mergeó.
