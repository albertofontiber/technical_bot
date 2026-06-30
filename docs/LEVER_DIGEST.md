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
| **L-i** = quitar el filtro de `category` en el canal vectorial | SETTLED en PASS · **VIVO en retrieval-miss** | `category` MUERTA desde el SWAP s44 (DEC-040). En **PASS**: ROLLBACK + MERGE+L-i′ NO-GO. En **retrieval-miss**: quitarlo = lever válido, net −12 (DEC-071). ⇒ NO re-litigar en PASS; SÍ vivo como bug de retrieval. | 040·050·071 |
| **Contextual retrieval** (blurb B7 en el embedding) | SETTLED implementado · e2e nunca medido aislado | YA activo al 100% en chunks_v2; audit léxico 0/8; lever context→generator smoke-débil → diferido. NO está sin probar: está **implementado**. | 020·022 |
| **CE / cross-encoder rerank** (Voyage) | SETTLED · PASS | A/B = ROLLBACK pre-registrado (degrada la cola PARCIAL→FALLO); archivado. | 048 |
| **MERGE / cosine-ranking** del pool | SETTLED · PASS | gate-0 NO-GO (mecanismo confirmado pero re-baraja PASS-control). | 050 |
| **Lever de generación** (prompt variant / completitud) | SETTLED · PASS | A/B NO-GO (flag inerte, Δ_net=0). | 051 |
| **Identidad como lever de RECALL del eval** (detector / pre-filtro family-aware / índice inverso) | SETTLED · retrieval-miss + PASS | ⊥ el cuello del eval: detector ~0 palanca (057), pre-filtro family-aware NO-OP (066), F1 índice-inverso NO-OP-con-regresión (069). Durable para findability/catálogo/30+, **NO** para recall del eval. | 057·066·069 |
| **ef_search / broad-fallback** del canal vectorial | APLICADO · retrieval-miss | ef=40→120 aplicado (s59b); el broad-5 era el workaround del canal muerto. | 040 |
| **Cuello REAL del eval** (diagnóstico, no un lever) | MEDIDO | **SÍNTESIS 63%** (no retrieval-vía-identidad); corpus-gap=0; el funnel léxico inflaba retrieval ~45%. | 070·071 |
