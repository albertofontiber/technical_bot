# s335 · Resultado de gates — fraseos de inventario (pieza A) + anafórica v3 (pieza B)

> Ejecutado 21-ago-2026. Diseño vinculante: `evals/s335_propuesta_v2.md` (dúo 13/13
> adjudicado, ts=2026-08-21T14:40:14). Recibos JSON: `evals/s335_gate_result_v3.json`
> (cohorte) y `evals/s335_gb_result_v1.json` (GB1/GB2).

## Pieza B — gate de cohorte v3 (prompt v3 + fila obligatoria): **GO**

- **Positivas 15/15** (barra pre-registrada ≥14/15) · **falsas 0/22** (barra 0) ·
  **guarda model-token OK** (2/2, fn-bomba sin invocar).
- **Fila OBLIGATORIA p15** («Y ahora quiero ver las de Morley.», cita prod
  `fabef50b`, adjudicación del owner): **3/3 votos CORRECCION** — la regla nueva
  del runner (`obligatorias_ok`, no absorbible por holgura) pasó por sí misma,
  no por agregado (cierre real de Sol-2/Fable-2).
- La regla anafórica del prompt v3 discrimina sin romper la frontera: N6
  («ahora quiero ver detectores Notifier» — CON sustantivo, se sostiene solo) y
  N22 («I want to see Notifier catalogs») siguen `nuevo` 3/3.
- Latencia del brazo: p50/p95 en el recibo JSON. Freeze: cohorte+prompt SHA en
  `freeze` (DEC-126: prompt nuevo = cohorte v3 re-congelada ENTERA, sin herencia).

## Pieza A + B — GB1/GB2 (`scripts/s335_gb.py`): **21/21 PASS, 0 fallos**

GB1 (plan puro, flag `INVENTARIO_FRASEOS`):
- ON: «Quiero ver las centrales de Morley.» (punto de Whisper), «dime qué
  centrales de Morley tienes.», «I want to see Morley panels/catalogs», «show me
  Morley panels» → **ruta inventario**. OFF: conversacional (no-cambio byte).
- Los **6 negativos técnicos** (Sol-4: mismo prefijo desiderativo + continuación
  técnica, p.ej. «…tienen salida de relé») → conversacional (RAG) en AMBOS
  regímenes. Replay turno 1 («¿Qué centrales de KIDDE tienes?») → inventario en
  ambos (superconjunto verificado).

GB2 (R8 → clasificador REAL → RAG real):
- (a) La anafórica NO la traga el atajo (sin sustantivo de inventario) y la
  guardia PRESERVA con estado R8 (`models=()`), flag on y off.
- (b) **Cruce `_SWITCH_FRASE` MEDIDO** (Fable-3): con modelos BINDEADOS
  («NC-PF2») el plan da INVALIDAR/Morley → el estado muere ANTES de resolve y el
  clasificador queda SIN población (sin `last_query`). La población real del cue
  anafórico son los estados con `models=()` (R8/frescos) — la vía de `fabef50b`.
  Conducta de HOY, independiente del flag; estampada, no presumida.
- (c) Clasificador real sobre estado R8: `correccion` (1576 ms) →
  `brand_correction_llm` + override reconstruida — la fila p15 confirmada
  END-TO-END a través de `resolve`, no solo en el módulo.
- (d) RAG sobre la override: respuesta **Morley-IAS no vacía** (ZX50 …) y
  **sin cross-brand** (kidde ausente).

**LIMITACIÓN DECLARADA (Sol-1, honesta):** la respuesta de (d) es síntesis RAG —
NO el listado gobernado del atajo (inalcanzable desde F1; oráculo s333): lista
potencialmente PARCIAL (clase s307). La vía gobernada y completa es la pieza A
cuando la petición se formula entera. Ninguna de las dos vías se vende como la otra.

## GB0 — no-cambio con flags off

- Suite completa: **4932 passed** (1 fallo `test_s324g_margen_max_rows` NO
  reproduce en aislamiento — pasa; test dependiente de red/Supabase, ajeno al
  diff). Dirigidos de no-cambio en `tests/test_s335_inventario_fraseos.py`
  (nuevas fraseos NO entran con flag off; ancla `\??$` sigue rota con OFF —
  documentado como contrato del default).
- **MT 52/52** (`scripts/test_multiturn_vs_gold.py`, 22 flujos, 13/13 clases).

## Huecos conocidos (declarados, no vendidos)

1. **Negación compartida**: «no quiero ver las centrales de Morley» matchearía la
   forma nueva — misma clase de hueco que la forma EXISTENTE «no quiero el
   listado de Morley» (sin ancla) tiene HOY. No es clase nueva; queda para
   frontera futura si se observa.
2. **Pregate EN-plural**: `_PREGATE_INVENTARIO` no cubre «catalogs/lists» en
   plural — para marcas NO curadas (solo-DB) las formas EN con esos sustantivos
   no llegan al 5-bis. Las marcas curadas (la población GB1) no lo sufren. El
   pregate es compartido con la guardia y NO se ensancha sin gate propio.
3. **Gramática censada**: cláusulas relativas («las centrales que tienes de…»)
   y desiderativas con «información/manuales» quedan fuera a propósito
   (frontera conservadora); el fallback es el RAG de siempre, nunca una
   respuesta peor.
4. La transición INVALIDAR de la guardia con las formas nuevas comparte
   predicado (`marca_destino` con `fraseos`) — la MECÁNICA de invalidación no se
   tocó (cubierta por s316); solo cambia la población del predicado con flag ON.
