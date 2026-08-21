# s333 · Gate del clasificador CORRECCION/NUEVO — GO en cohorte v2.1 (21-ago-2026)

> Recibos: `s333_gate_result_v1.json` (NO-GO, 3 falsas) · `s333_gate_result_v2.json`
> (NO-GO, 1 falsa) · **`s333_gate_result_v2_1.json` (GO)**. Prompt y cohorte congelados
> por SHA en cada recibo (DEC-126). Regla K pinnada en el YAML: negativa falla con
> CUALQUIER voto CORRECCION; positiva pasa con mayoría ≥2/3; None=NUEVO.

## La secuencia (sin gate-shopping: cada iteración la adjudicó ALBERTO, vía v2 §5)

| ronda | resultado | qué cambió y QUIÉN lo adjudicó |
|---|---|---|
| v1 (prompt v1, gold mío) | **NO-GO**: 12/12 positivas, 3 falsas | Las 3 eran límites de MI gold. Alberto adjudicó una a una: re-preguntas completas con marca cambiada (ES/EN) = NUEVO (se responden tal cual); «vale, pues busca en Notifier» = CORRECCIÓN (reconstruir). Su frontera: **¿el mensaje se sostiene solo?** |
| v2 (prompt v2 con SU frontera + relabel N16→P13) | **NO-GO**: 13/13 positivas, 1 falsa | La falsa restante («mejor dime algo de Morley», 3/3) es la MISMA clase que la P13 que él adjudicó — el clasificador fue más consistente con su frontera que mi gold. Alberto: **corrección** (el «mejor» ancla a la petición previa). |
| **v2.1** (relabel puro N14→P14, prompt INTACTO) | **GO: 14/14 positivas · 0 falsas · guarda 2/2** | Nada más que el relabel adjudicado. |

Brazo Haiku (informativo, v1): 13 falsas CORRECCION ⇒ descartado con métrica PROPIA
(no heredada). Latencia Sonnet servida: p50 ~1,1-1,3 s · p95 ~2-4 s (recibos) — solo en
la población de misses, contra turnos RAG de ~28 s.

## e2e del camino LLM (clasificador REAL, cue retirado del léxico en harness)

Replay del hilo real de la mañana (clase `57b8d482`): T1 «¿Qué centrales ID tienes?» →
T2 «sí, dije Kidde» con el léxico sin cues de «decir» (fuerza el miss de la plantilla) ⇒
`rationale=brand_correction_llm` (decisión real `correccion` en 1426 ms) ·
qfr = «¿Qué centrales ID tienes? (el usuario corrige: la marca es Kidde)» ·
`Asuncion(marca_corregida, Kidde)` · respuesta NO vacía con contenido Kidde Commercial.
Matiz de instrumento LEÍDO (DEC-092b): la respuesta menciona «ID3000» solo para ACLARAR
que Kidde no tiene esa denominación — no es cross-brand; el check naive de regex lo
marcaba y la lectura lo adjudica correcto.

## Estado del lote

- Tests dirigidos post-prompt-v2: 50/50 (módulo+seam+plantilla s332). Suite completa
  verde en el commit del build (4853+1 censo arreglado); CI de la PR re-corre entera.
- **SHIP LISTO**: merge de la PR #329 → Railway redespliega (flags off = byte-idéntico)
  → flip de Alberto: **`F1_CORRECCION_LLM=on`** (con `F1_MARCA_CORRECCION=on` ya viva).
  Rollback = quitar la var. Verificación DEC-099: conversación real con un fraseo NO
  tabulado (p.ej. «que no hombre, que es Kidde») ANTES de añadirlo al léxico.
- Pendiente declarado sin construir: `pending_aviso` (el «sí» pelado) — diseñado,
  esperando observación.
