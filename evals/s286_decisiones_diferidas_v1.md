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

## D9 — Telemetría: DDL `answer_feedback` + vistas de salud (TU PASTE)
Paquete construido tras dúo r1 (Sol 8 + sub-agente 10 hallazgos, 0 FP) + r2 GO-BUILD:
`evals/s286_answer_feedback_ddl_v1.sql` (tabla con FK ON DELETE CASCADE → tu borrado RGPD
sigue funcionando; UNIQUE por (respuesta, usuario) = taps idempotentes con toggle; hardening
RLS patrón completo con postcondiciones que abortan; vistas `bot_health_daily/semanal`
security_invoker; ROLLBACK comentado al final). **Acción: paste en el SQL editor cuando
revises el lote.** Sin el paste, los flags de telemetría no se encienden (el resto del bot no
depende de la tabla).

## D10 — Telemetría: TERMS_VERSION v1→v2 (efecto visible)
Los términos ahora listan la valoración 👍/👎 → el bump obliga a re-aceptar `/accept` a los
usuarios demo existentes (hoy: tú). Es 1 mensaje de fricción, deliberado (barato hoy, caro con
técnicos). **Se despliega con el merge; no requiere gesto tuyo más allá de re-aceptar.**

## D11 — Telemetría: logging ligero de rutas directas (BOT_DIRECT_LOGGING) — NO construido
Los turnos pre-pipeline (saludo/catálogo/fabricante-ausente/clarify/F1-directo) NO loguean →
«adopción» subcuenta el onboarding. El digest lo declara. Construir el logging ligero
(`category='direct'`, ~5 rutas) es ~1h cuando lo decidas; las vistas YA lo excluyen del
volumen RAG (interlock listo). **Recomendación: construirlo antes del primer técnico real;
no urge en demo.**

## LOTE DE ONs DE RAILWAY (cuando el arco cierre — un solo gesto tuyo)
`ANTI_DIAGRAM_INVENTION=on` · `WIRING_TOPOLOGY_GUARD=on` · `GENERATOR_DIRECT_FIRST=on` ·
`GENERATOR_FOLLOWUPS=off` (si D1 ok) · `VISUAL_ASSETS_LISTING_GATE=on` — todo tras la
re-baseline v4 verde + runner e2e; con el merge de la PR de la rama.
**Telemetría (tras tu paste D9):** `TELEGRAM_FEEDBACK=on` (keyboard 👍/👎) ·
`BOT_ERROR_LOGGING=on` (filas de error allowlisted) · `INTERNAL_TELEGRAM_IDS=<tu id>`
(segmenta dogfooding en el digest; sin él, el digest cuenta todo como técnico).
