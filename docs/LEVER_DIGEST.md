# Levers — veredicto vigente (digest inyectado por el hook `SessionStart`)

> **Qué es.** Lookup para NO re-litigar levers ya medidos ni negar hechos estructurales ya
> establecidos. El hook `SessionStart` (`.claude/hooks/inject_lever_digest`) inyecta este
> archivo en contexto cada sesión, así está presente SIN depender de que me acuerde de abrirlo.
>
> **Regla de lectura.** El **"settled" tiene MÉTRICA**: un veredicto en PASS NO zanja el mismo
> lever medido en retrieval-miss (ni al revés). Antes de proponer/opinar/NEGAR sobre un lever,
> cita la métrica del veredicto y verifica que coincide con el objetivo de HOY.
>
> **Mantenimiento.** Fuente del detalle = `docs/DECISIONS.md` (los `DEC#`). Se **SOBRESCRIBE
> in-place** al cerrar sesión (paso del Protocolo 4 / Cierre), una fila por lever; NUNCA se apila.

| Lever | Estado · MÉTRICA | Veredicto (1 línea) | DEC |
|---|---|---|---|
| **L-i** = quitar el filtro de `category` en el canal vectorial | SETTLED en PASS · **APLICADO en retrieval-miss (s85, mergeado #94)** | `category` MUERTA desde el SWAP s44 (DEC-040). En **PASS**: ROLLBACK. En **retrieval-miss**: quitarlo = lever válido → **s85 `VECTOR_NOCAT` PERMANENTE mergeado a main** (limpieza de raíz, equivalencia 38/39). NO re-litigar. | 040·050·071·073 |
| **Contextual retrieval** (blurb B7 en el embedding) | SETTLED implementado · e2e nunca medido aislado | YA activo al 100% en chunks_v2; audit léxico 0/8; lever context→generator smoke-débil → diferido. NO está sin probar: está **implementado**. | 020·022 |
| **CE / cross-encoder rerank** (Voyage) | SETTLED · PASS | A/B = ROLLBACK pre-registrado (degrada la cola PARCIAL→FALLO); archivado. | 048 |
| **MERGE / cosine-ranking** del pool | SETTLED · PASS | gate-0 NO-GO (mecanismo confirmado pero re-baraja PASS-control). | 050 |
| **Lever de generación** (prompt variant / completitud) | SETTLED · PASS | A/B NO-GO (flag inerte, Δ_net=0). | 051 |
| **Identidad como lever de RECALL del eval** (detector / pre-filtro family-aware / índice inverso) | SETTLED ⊥ (funnel LÉXICO) · **RE-ABIERTO por el instrumento family-aware (s85)** | ⊥ medido con el funnel LÉXICO: detector ~0 (057), pre-filtro NO-OP (066), F1 índice-inverso NO-OP (069). PERO s85 (DEC-073): el instrumento family-aware corregido diagnostica **hp018 = MODEL-FILTER (4/14 misses)** = el `_filter_to_query_models` expulsa el manual correcto → identidad SÍ es causa de retrieval-miss real. ⇒ NO re-litigar el ⊥-léxico; SÍ **re-medir** un método de identidad con el instrumento nuevo (métrica distinta) + dúo+contrato. | 057·066·069·073 |
| **ef_search / broad-fallback** del canal vectorial | APLICADO · retrieval-miss | ef=40→120 aplicado (s59b); el broad-5 era el workaround del canal muerto. | 040 |
| **Cuello REAL del eval** (diagnóstico, no un lever) | MEDIDO (instrumento family-aware s85) | **SÍNTESIS = el cuello (103/132 hechos)**; retrieval-miss family-aware = **14** (RECALL-INTRADOC 8 within-doc/chunking · MODEL-FILTER 4 identidad · RECALL-GLOBAL 2 findability); corpus-gap≈0. | 070·071·073 |
