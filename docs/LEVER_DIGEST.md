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
| **Identidad como lever de RECALL del eval** (detector / pre-filtro / índice inverso / mapa data-driven) | SETTLED · **~4 de palanca (hp018), NO el cuello; BP = catálogo canónico 2-etapas (s86/DEC-074)** | Palanca de eval REAL = **~4 retrieval-miss (hp018 MODEL-FILTER)**; hp011 mis-diagnosticado (es within-doc); identidad ⊥ el cuello RE-CONFIRMADO. **LEVER2_IDENTITY** (curado) da hp018 4/4 pero es **quick-fix** (per-familia, no escala) + regresa hp009 → **NO shipear** (dúo NO-GO). **Mapa data-driven** (`family_scope`) net-negativo tal-cual (matching texto-libre frágil, −2 hp011). **BP = entity-linking 2 etapas** (catálogo gobernado + re-tag DOC canónico + resolución query-side híbrida + **clarify-on-ambiguity**, confirmado BP por literatura EVPI/CLAM) = workstream (A), 4-7 sesiones, ⊥ el PASS (cimiento escala-30+/catálogo). NO re-litigar; mapa-filtro y LEVER2 MEDIDOS net-neg/quick-fix. | 057·066·069·073·**074** |
| **ef_search / broad-fallback** del canal vectorial | APLICADO · retrieval-miss | ef=40→120 aplicado (s59b); el broad-5 era el workaround del canal muerto. | 040 |
| **Cuello REAL del eval** (diagnóstico, no un lever) | RE-CARACTERIZADO s87 (instrumento fact-in-answer, 2 gen) | **El "SÍNTESIS 103/132" era COTA de hechos SINTETIZABLES, NO fallos.** Midiendo la respuesta actual: pipeline sintetiza **~76-80%**; cuello de síntesis ROBUSTO = **16 stable-MISS (~13-14 genuinos)**, heterogéneo (completeness~10 [=lever gen NO-GO DEC-051] · contradicts~4 fidelidad · hedge~2), SIN lever barato. La mejora = **VECTOR_NOCAT** (mismo modelo/temp). retrieval-miss family-aware = **14** (INTRADOC 8 · MODEL-FILTER 4 identidad · GLOBAL 2). **Recomendación: des-diferir PASS (gate Alberto) — baseline probablemente subió.** NO re-litiga DEC-070/073 (refina). | 070·071·073·**075** |
