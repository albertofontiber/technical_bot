# s286 — PAQUETE DE DECISIONES DIFERIDAS (revisión por lotes de Alberto, no bloqueantes)

> Directiva 29-jul: lo no-bloqueante se empaqueta. Cada ítem lleva mi recomendación y el estado
> por defecto si no dices nada (statu quo salvo indicación). Los ONs de Railway van en su lote
> aparte al final del arco.

## D1 — Default de los follow-ups («También puedo ayudarte con…») [lever 5.2, medido]
A/B 24-gens: coletilla base 10/10 → tratado 0/12, sin pérdida de contenido. Los follow-ups
fueron diseño tuyo antiguo (feedback_conversation); tu 5.2 los marcó genéricos.
**Recomendación: OFF definitivo** (GENERATOR_FOLLOWUPS=off en el lote de ONs). Nota: el fix del
parser hace que, si se mantienen ON, ya no amputen la respuesta (~50% lo hacían).

## D2 — Gemelos EN del P2 (chunks `7a9022bd` «FL/dL», `866cd4eb` «Additional Opinions/PS»)
Glitches de etiqueta 7-segmentos en la guía rápida EN (semántica CORRECTA, sin default
invertido). Servibles a queries EN.
**Recomendación: patch de etiquetas en el próximo lote de corpus** (mismo mecanismo staging;
~15 min). Alternativa: declarar EN fuera de scope de calidad fina.

## D3 — kmajority a vara v4
`bvg_kmajority.py` conserva su propia vara (con SU truncación JUDGE_TRUNCATION — auditar si es
la clase [:3000]) y hashes de instrumento. No se usa en la re-baseline (single-pass).
**Recomendación: alinear a v4 + auditar truncación ANTES del próximo uso de K-mayoría** (gates
de lever). Registrado como deuda de instrumento.

## D4 — struck_ocr vs literales supervivientes
Tras la limpieza, los ~~ que quedan son LITERALES (arte ASCII, punteros CBE) y la política
struck-OCR del EC (`~~(.*?)~~` non-greedy) los maneja mal si alguna vez los toca.
**Recomendación: TECH_DEBT** (la política casi no tiene ya superficie; fix cuando se re-visite
el EC).

## D5 — Fuga hyq a nivel SQL
El fix python cierra el serving; el RPC `match_chunks_v2_hyq` sigue devolviendo hijos de
duplicados (filtrados después). **Recomendación: filtro en el RPC en la próxima migración DB**
(higiene, no urgente).

## D6 — Canal FTS search_chunks_text v1 (sin filtro de duplicados)
El código llama a _v2 (filtra). Las funciones v1 siguen en la DB sin uso conocido.
**Recomendación: DROP en la próxima migración** (reduce superficie).

## D7 — Re-anclaje del corpus fingerprint
`corpus_fingerprint_v1()` cambió por diseño (contenidos+vectores nuevos). Se re-captura al
cerrar el corpus del arco (post t.Fi) y se re-anclan los seals que lo consumen (C1/s107) con
nota en DECISIONS. **Se ejecuta solo; aquí solo para tu visibilidad.**

## D8 — El A/B del guard corrió con lanes de coverage en off
Células pareadas → la conclusión (A'+C' 0/20) es internamente válida; la paridad completa la
re-valida la re-baseline v4 + runner e2e antes de tus ONs. Declarado por transparencia.

## LOTE DE ONs DE RAILWAY (cuando el arco cierre — un solo gesto tuyo)
`ANTI_DIAGRAM_INVENTION=on` · `WIRING_TOPOLOGY_GUARD=on` · `GENERATOR_DIRECT_FIRST=on` ·
`GENERATOR_FOLLOWUPS=off` (si D1 ok) · `VISUAL_ASSETS_LISTING_GATE=on` — todo tras la
re-baseline v4 verde + runner e2e; con el merge de la PR de la rama.
