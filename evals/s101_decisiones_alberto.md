# s101 — Decisiones que requieren tu input (cada una con recomendación)

> Se APENDIZA durante la noche. Las "tomadas-inequívocas" van al final para tu validación.

## D1 · Recarga OpenAI (BLOQUEA el scoreboard v2 y la Fase 2)
La cuota murió ~23:00 a mitad del full v2 (run en cuarentena). Sin ella: no hay scoreboard v2,
no hay jueces para synthesis (Fase 2), no hay cross-model del dúo.
**Recomendación: recargar ~$30-40** (full v2 limpio ≈ $25 con los duales + margen para re-mediciones
de Fase 2). Al recargar, lo corro serializado (lección de hoy: no en paralelo con otros runs de juez).

## D2 · Ship-path del mecanismo hyq (GO del piloto ya dado por los gates del prereg)
El piloto validó el mecanismo (cat016 + hp018-6K8 flip, control negativo limpio con barra 0.45).
El prereg dice: corpus-wide/activación = decisión TUYA, nunca auto-ship. Opciones:
  a) **Tabla A3-style** (`chunks_v2_hyq`, HNSW propio, patrón enunciados) + generación corpus-wide
     (~1.170 docs; estimar coste de generación Claude ~$40-80 + embed ~$2-5 + QA muestral) → ship-gate
     bvg de no-regresión. Estructural, escala-30+, el canal ya probado.
  b) Solo docs-de-demo relevantes (barato, parcial — no escala, sabor a parche).
  c) Aparcar hasta técnicos reales (el prereg contemplaba este gatillo).
**Recomendación: (a), gateado al bvg de no-regresión y a que el full v2 confirme la reducción del
bucket en el scoreboard.** El coste se estima ANTES (disciplina), y el corpus-wide se hace por tramos
con gates (lección DEC-088).

## D3 · Golds hp018-'1 A' y hp020-'nivel 2 o 3' (los 2 "NO_VAL_CHUNKS" del piloto)
Son no-anclables (single-digit / prosa) → el harness judge-free no puede localizar su chunk-valor de
forma estable, y el juez semántico está sin cuota. Además hp018-'1 A' arrastra la ambigüedad
ADD-coincidencia (DEC-091b).
**Recomendación: esperar cuota y medirlos con el juez semántico; NO tocar los golds.** Si al medirlos
siguen inestables, candidato a re-anclar el valor en el gold (p.ej. '1 A' → citar la fila de la tabla
con su contexto) — eso sería edición de gold y te la propondría aparte.

## D4 · cat020 y hp009-'aisladores' (scope-borderline del gold-review s100b, aún pendientes de ti)
Del gold-review: cat020-'0-100% normalizado' (Fable: demote con tu sign-off por la edición s89;
GPT-5.5: mantener) y hp009-'aisladores internos' (Fable: demote; GPT-5.5: mantener).
**Recomendación: cat020 mantener core** (la escala normalizada es parte de "nivel de alarma por
defecto y máximo") **y hp009-'aisladores' demotar a supp** (la pregunta pide la RFL; los aisladores
son contexto). Con tu OK los aplico vía gold_store.

---

## Decisiones INEQUÍVOCAS tomadas esta noche (para tu validación)
> (se apendizan conforme ocurran)

- **[ya validada por ti en vivo] hp011**: corpus r.i restaurado + r.S mantenido; gold r.1→r.I;
  script revert-safe; lección cross-model-vs-humano a memoria.
- **Run full v2 inválido en CUARENTENA** (`s100_factlevel_full_v2_INVALIDO_quota.yaml`) + fail-fast
  del juez primario muerto cableado (el próximo run aborta limpio).
- **Nada se shipea esta noche**: tiering incompleto (cross-model sin cuota) → todo flag-gated
  OFF/branch-local hasta el dúo completo.
