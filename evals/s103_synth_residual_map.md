# s103 — Mapa del synth residual (8 facts, v2.2) — tarea §2 del plan s103

Fuente: `evals/s100_factlevel_full.yaml` (v2.2, 59fe1a2). Extracción mecánica per-fact.

| fact | submotivo (votos) | stability | familia | forma |
|---|---|---|---|---|
| cat008#3 terminales lazo M710 | contradicted 5/5 | stable-miss | ID-3000/M700 | cableado (bornes) |
| cat016#1 menú ZONA+ELEMENTO | omitted 5/5 | stable-miss | CAD-150-8 | paso procedimental |
| cat017#2 licencia CLIP | omitted 5/5 | stable-miss | INSPIRE E10 | paso procedimental |
| cat018#1 pestaña Zona+CBE | omitted 5/5 | stable-miss | AM-8200 | paso procedimental |
| cat018#2 Tipo SW / CBE | omitted 5/5 | stable-miss | AM-8200 | paso procedimental |
| hp005#1 COINCIDENCIA 2 EQUIPOS | omitted 4/5 | stable-miss | ID3000 | paso procedimental (perdido v3→v2.2, NO atribuido a hyq) |
| hp012#2 2 lazos/396 | hedged 5/5 | **flip** | AM2020/AFP1010 | multi-doc ES (residual declarado hp012) |
| hp018#0 ZX5e 4 vs ZX2e 2 | contradicted 5/5 | **flip** | ZX2E/ZX5E | **variante-divergente** — DIANA del lever displacement (composición) |

## Respuestas a las preguntas del plan (§2)

1. **¿Estables vs ruido de rerank (DEC-096b)?** 6/8 stable-miss — el residuo es REAL, no ruido.
   Los 2 flip: hp018#0 (diana displacement) y hp012#2 (residual declarado, lever tie-break CERRADO s101).
2. **¿Cluster cat021 en otras familias?** NO reaparece. Único fact variante-divergente = hp018#0,
   ya atribuido a composición-por-desplazamiento (lever §1). **El fork cat021 (DEC-097) NO se reabre.**

## Conclusión (mapa ANTES de lever — cumplido)

- NO se propone lever synth nuevo en s103. La clase dominante (5×omitted procedimental) es la
  clase DEC-094 "omitted/hedged ~10" cuyo sub-motivo está CONTAMINADO por scope/gold →
  el paso previo obligado es gold-review por-hecho (eje gold/juez, ADVISORY), no un lever de
  generación a ciegas.
- hp018#0 se juzga en el gate del lever §1 (si la composición servida mejora al aterrizar el
  desplazamiento, puede flipear sin tocar generación).
- cat008#3 (bornes, contradicted estable) = clase datos-detalle/vocabulario (DEC-085/086) — ya
  cubierta por el lever enunciados R2 corpus-wide (gateado a presupuesto, §4 del plan).
