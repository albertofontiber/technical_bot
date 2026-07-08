# s101 — Decisiones que requieren tu input (cada una con recomendación)

> Se APENDIZA durante la noche. Las "tomadas-inequívocas" van al final para tu validación.

## D1 · Recarga OpenAI — ✅ RESUELTA (Alberto recargó antes de dormir)
Full v2 RELANZADO limpio y serializado (~00:30). Desbloquea también: cross-model del dúo (pendientes:
dual-soporte final, tiebreak port, iteraciones hyq) + jueces semánticos (hp020-'4y8', cat013 probe) +
Fase 2. La cola nocturna se re-secuencia: full v2 primero (solo), cross-models después.

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

- **[inequívoca, ~01:00] TIEBREAK = NO-GO DEFINITIVO (2ª medición, ahora CON ancho-10 — cierra la
  hipótesis abierta de DEC-091b)**: hp012 SÍ flipea, PERO el centinela hp001 regresa ('1111' sale del
  top-10 servido) + control negativo 9 EXCESS-HIGH/null=0 (el re-barajado de s97 reproducido). El
  tripwire pre-registrado de DEC-091 dispara otra vez → lever CERRADO (LEVER_DIGEST se actualiza al
  cierre); código flag-OFF en rama, jamás a demo; hp012 al residual declarado.
  Artefacto: `evals/s101_tiebreak_measure.yaml`.
- **[inequívoca, ~01:15] hyq-extensión MIDT180/MIDT190 medida**: hp014 ya estaba IN-POOL (su chunk
  real MIDT180-p68 incluido → es clase juez/relación, el dual-soporte del full v2 lo arbitra);
  cat013 confirmado IDENTIDAD (query CAD-150 vs doc ID3000 — ni hyq ni léxico lo puentean →
  workstream DEC-074, como ya estaba). El lever hyq queda en 2 flips netos (cat016, hp018-6K8).

## D6 · Ship del fidelity-block (GENERATOR_PROMPT_VARIANT=fidelity) — NUEVO, medido esta noche
A/B fact-level (13 golds synth-miss, brazo fidelity ×2 gens, árbitro dual): **+3 rescates
(hp002·hp006·hp010) − 0 regresiones**. Neto positivo, coste ~0 (bloque de prompt), pero NO es el
rompe-bucket (21 still-miss: clusters hp011×4, cat021×3-variantes, cat017/cat018-procedimientos).
DEC-051 lo midió NO-GO en PASS; a nivel-hecho es net-positivo — el patrón DEC-092b (la vara importa).
**Recomendación: SHIP-candidato** → gate bvg de no-regresión (invención especialmente: el bloque tiene
anti-sobre-alcance y midió 0 regresiones, prometedor) + tu GO. Artefacto: `evals/s101_fidelity_measure.yaml`.
- **[nota H5, s102]** `s101_fidelity_measure.py` quedó mixed-version tras v2.1 (su +3/0 se midió pre-v2.1 y es válido como medición congelada; re-runs futuros necesitan su propia copia del juez).

## D4 — ✅ RESUELTA (Alberto, s102): cat020 MANTENER core · hp009-'aisladores internos' DEMOTE a supp
Aplicación: el demote de hp009 se aplica vía gold_store AL CERRAR el full v3 en curso (no invalidar su
partial). cat020 queda como está. El v3 aún cuenta hp009-aisladores en el denominador (nota de lectura).

### s102 (tarde 8-jul) — L2c demote-TOC + instrumento v2.2 + higiene hyq
- **L2c (demote de páginas de índice en el rerank) = NO-GO** con la métrica del mandato (GO=reducción
  de bucket): 0 gains, superficie ~1-2 TOCs servidos/run, churn 11/39 del orden del ruido. DEC-096.
  **Colateral importante: el LLM-rerank NO es determinista ni a temperature=0** (2 golds con input
  idéntico cambiaron slots) — norma nueva para futuros A/B de rerank (control OFF-vs-OFF o N-reps).
- **La heurística TOC pasa al instrumento (v2.2, cierra H4)**: anclas-TOC ya no acreditan soporte
  (inflaban synthesis-miss); red dual re-adjudica; `instrument: v2.2` estampado en el artefacto.
  El próximo full estrenará la fila v2.2 del scoreboard.
- **Patrón seam-a-patch**: ni el tiebreak (cerrado) ni el seam TOC (NO-GO) viajan a main — patches
  reproducibles en evals/ + guards fail-fast en sus scripts de medición.
- **Higiene hyq (S4 del dúo)**: un error de API ya no marca el chunk como done-para-siempre
  (reintenta al siguiente tramo + fail-fast a 20 errores). Al cierre de tramos: pasada
  retry-empties (~848 registros históricos `[]`, ~$3) + dedup por chunk_id en el build de la tabla.
- **Dúo completo corrido** (sub-agente 7 hallazgos/1 crítico confirmado + cross-model 6/4 confirmados,
  1 FP); tally completo en adversarial_review_log.jsonl. El crítico: mi claim "temp=0 ⇒ delta=solo
  el lever" refutado por mis propios datos → framing corregido en yaml+docstrings+DEC.

## D7 · Gold hp014 con `targets: []` vacío (hallado en la verificación de corpus-gaps s102)
El hecho hp014#2 ('terminales 2 y 4') aterrizó corpus-gap FALSO porque el gold no declara
targets → el check de corpus no tenía manual donde mirar. El hecho está LITERAL en MIDT180 p.44
(verificado píxel: "cortocircuitando los terminales 2 y 4 de cada aislador"); el hecho '35'
(≤35Ω) también vive en MIDT180 (s101).
**Recomendación: añadir `targets: [MIDT180]` al gold hp014 vía gold_store con el checklist de
localización** (es completar metadata verificada, no re-autoría). Con tu OK lo aplico — o lo
aplico yo directamente si lo consideras inequívoco (es la clase "gold-metadata incompleta", no
cambia valor/texto de ningún hecho).

### s102 (tarde-2, 8-jul) — L4 selection-block: NO-GO tal-cual-medido (DEC-097)
- Construí y medí el bloque de generación para el cluster cat021 («¿qué modelo pido?» → enumerar
  variantes divergentes). **NO-GO**: cat021 base HOY ya transmite los 4 hechos (el miss del v3
  depende de la COMPOSICIÓN servida — estocástica por DEC-096b — y dada la mala, la generación
  falla estable) + shift conductual 1/2 en hp009 (clarify en pregunta de propiedad).
- **El dúo me corrigió el framing DOS veces** (over-claim "ambas gens" + pre-suponer "serving-side"):
  reapertura honesta = FORK con replay — el instrumento ahora persiste topk_ids/served_ids para
  que una composición-que-falla sea replayable.
- Seam → patch (patrón consolidado); src/tests limpios; nada shippeado.
- **Para ti**: la clase «consulta de selección» es una dimensión conductual que crecerá con 30+
  fabricantes — candidata a golds futuros autorados desde FUENTE (DEC-025), si te encaja.
