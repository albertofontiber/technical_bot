# s316b — Fix de #70, etapa 1: guardia de cambio-de-marca EXPLÍCITO (contra el instrumento)

> ## Corrección post-dúo (ronda 4) — leer ANTES del resto
>
> El diseño de abajo se cableó y el dúo lo devolvió **NO-SÓLIDO**. Dos defectos MEDIDOS
> end-to-end, ambos verificados por mí:
>
> 1. **`FUEGO` es un fabricante REAL de la DB** (1 doc) y el resolutor casaba «fuego», la
>    palabra más común del sector ⇒ «y ahora la central de fuego no rearma» borraba el
>    contexto y convertía un turno contestado en un clarify. **8/19 consultas técnicas
>    plausibles disparaban en falso.** El fix era PEOR que el bug.
> 2. La muletilla **«vamos a ver»** convertía compatibilidad en switch, y mi control usaba
>    la forma desnuda ⇒ era vacuo frente a esa clase (2ª vez que caigo en control vacuo).
>
> **Corregido precisión-primero**: resolutor ESTRICTO en la guardia (nombre completo; la
> heurística de primera-palabra de `_marca_en_consulta` existe para un contexto ya
> pre-gateado y es insegura a máximo alcance), `_MARCAS_AMBIGUAS`, `vamos` fuera, replies
> de feedback excluidos, pre-gate barato antes de tocar DB (**0,54 s en frío por mensaje**
> que se me había colado), y test de wiring acotado a `run_bot`.
>
> **La sección «Qué NO dispara» de abajo era un over-claim** y el documento no declaraba
> ningún gap de falsos positivos. Los gaps reales están al final.
>
> **Medición de precisión sobre datos REALES** (68 consultas distintas de `query_logs`,
> abr–ago): 7 disparos, **7 legítimos, 0 falsos positivos**. No exonera nada — esa muestra
> es Alberto probando con códigos de modelo, no técnicos escribiendo lenguaje de campo;
> por eso la corrección se hizo igual.

**Qué es.** El fix de la causa (1) de #70 —ceguera de ruta— construido CONTRA el
instrumento (`tests/test_s316_transport_state_instrument.py`): el testigo xfail debe pasar
a XPASS y promocionarse a contrato en el mismo cambio. La causa (2) —la conflación
`brand_compatibility_in_window` de la política— queda FUERA (etapa 2, exige gate MT
propio); su caso queda documentado con un SEGUNDO testigo xfail nuevo.

**OBJETIVO + MÉTRICA**: el testigo A→B→C del instrumento en verde (sin marcador), los
controles (causal, compatibilidad, misma-marca) en verde, y suite completa verde. Sin
lever: no toca retrieval ni la política; el eval single-turn no se mueve por construcción.

## Diseño (las restricciones de DEC-197/TECH_DEBT #70, aplicadas una a una)

**Mecanismo**: `TypeHandler(Update, guardia)` en **grupo −1** — corre ANTES de todo
handler para TODO update de texto; no responde, no bloquea (los grupos siguientes corren
igual). Punto único estructural: la ruta nº7 lo hereda sin convención. `handle_voice` es
el único caso especial (la guardia no puede leer audio): llamada explícita al núcleo
síncrono tras la transcripción, antes de `_process_query`.

**Predicado — dispara SOLO si**:
1. La consulta declara cambio explícito: frase de switch («pasemos a», «cambiando a»,
   «ahora con»…) con una marca DETRÁS de la frase (posición, no primera-marca-del-texto —
   el bug «pasemos de Kidde a Morley» resolvería Kidde), **o** intención de inventario
   (`_intencion_inventario`) con UNA sola marca mencionada.
2. Sin token de producto REAL: `extract_product_models` filtrado por `NON_PRODUCT_CODES`
   (RS-485/EN-54 no suprimen la guardia — restricción 5).
3. Hay estado que invalidar: `mt_working_state.last_target_models` **o** el legacy
   `last_detected_models` (rollback-safe: cubre AMBOS regímenes — restricción 1).
4. La marca destino ≠ marca del estado: `DeterministicConversationPolicy._same_manufacturer`
   (colapso Honeywell — restricción 6) **extendido con identidad directa**
   marca==fabricante (el mapa del impl solo tiene 4 entradas; sin la extensión,
   «¿qué más centrales Kidde tienes?» con estado Kidde LIMPIARÍA contexto legítimo).
   Si ninguna marca del estado es resoluble → **fail-open** (no limpia).

**Efecto**: `mt_working_state = WorkingState()` (reset COMPLETO — restricción 3: dejar
`last_query` residual produce el «Ha pasado un rato» mentiroso) + `pop("last_detected_models")`
(mata el carry legacy). NO toca `last_query`/`last_response` legacy (los consume el
feedback) ni `last_query_log_id`.

**Qué NO dispara (controles del instrumento)**: compatibilidad («¿es compatible con
Morley?» — ni switch ni inventario), misma marca («¿qué más centrales Kidde tienes?»),
catálogo genérico (sin marca), `manufacturer_mismatch` (lleva token de modelo real).

## Lo que NO arregla (declarado)

- **El fall-through** («¿y en Morley cómo se hace el reset?»): ni switch ni inventario —
  es la causa (2), la política. Segundo testigo xfail NUEVO lo deja demostrable.
- Cambio de marca **por voz**: cubierto vía la llamada en `handle_voice`, pero la frase
  hablada pasa por ASR — sin gold de voz, sin garantía medida.
- La heurística de switch es un léxico ES: formas EN y giros no listados no disparan
  (fail-soft: se arrastra, como hoy).
