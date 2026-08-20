# s331 · M4 — gates G1-G4 COMPLETOS (20-21 ago 2026, noche) · veredicto de SHIP

> G1 detallado en `s331_g1_resultado_v1.md`. Recibos: `s331_g1_{off,a,af,acf_v2,c_v2}_v1/2.json`
> · `s331_g2_v1.json` + `s331_g2_hp018_{off,on}.txt` · `s331_g3_v1.json` ·
> `s322_railway_censo_v1.json` + sonda dirigida IDENTITY. Todas las conductas citadas
> fueron LEÍDAS (DEC-092b).

## Veredicto por gate

| Gate | Resultado | Nota |
|---|---|---|
| **G1** replay hilo real | **PASS todos los brazos** (off reproduce; a localiza pool-entry loss; af sirve familia; acf 7/7; c 6/6) | 2 bugs cazados y arreglados EN el gate (pool-entry ⇒ IDENTITY_FETCH; `turn_identity=None` en flujo principal) |
| **G2** sweep-39 composición | **0 regresiones reales** — señal-por-sets adjudicada: 2 aditivas de familia + hp018 leído (ON igual-o-mejor) | Ruido OFF-vs-OFF 23/39 con **ventana SUCIA declarada** (fallos de canal Supabase en 10-11/39); confirmación en ventana sana recomendada; centinelas hp009/hp001 en-ruido (no atribuibles) |
| **G2-MT** flows conversacionales | **52/52 PASS con los 4 flags** | `test_multiturn_vs_gold --contract` |
| **G3** conducta A/B 6 reps | **ON 6/6 sin-amnesia (kidde) + 6/6 reconocimiento (mixto)** — estabilidad del lado ON | Matiz de instrumento DECLARADO: el check determinista de OFF no caza variantes de fraseo («¿qué modelo concreto del X tienes instalado?» rep0 OFF, leído) — el contraste OFF↔ON lo establecen las LECTURAS de G1+G3, el gate pre-registrado era el lado ON |
| **G4** censo Railway | **PASS de primera mano**: worker `IDENTITY_RESOLVE=on` + `POLICY=replace`; NINGUNA flag s331 presente (prod byte-idéntica confirmada) | Censo estándar «OK sin desviaciones» |

## Lo que el gate cambió del plan (y quedó cableado esta noche)

1. **`IDENTITY_FETCH` entra al lote de ship** (4º flag): el brazo A midió que la
   identidad perfecta NO basta — pérdida de entrada-al-pool (clase DEC-084) con
   `allowed_sources` perfecto. Re-apertura LEGÍTIMA del seam s93 (su NO-OP fue en
   famtie-39; la métrica de hoy es este hilo, donde el selector léxico casa
   literalmente). Medido af/acf: GO en esta clase.
2. **Población de `turn_identity` en rama A y carry** — el hueco que ningún unit test
   veía (95 dirigidos verdes antes y después) y el gate sí.

## Residuales declarados (ninguno bloquea el ship; entran al seguimiento post-flip)

- T2 con evidencia solo-de-variante-hermana: pide confirmación en vez de declarar
  alcance (el fetch aún no había rellenado en T2; wording del nivel-RESUELTO afinable).
- T3 pregunta el ASPECTO de programación en vez de dar overview — clarify legítimo, se
  observa con tráfico.
- Ventana sucia de G2 → re-run de confirmación en ventana sana (barato, composición).
- Regex de amnesia del G3 (instrumento) infra-caza variantes de fraseo en OFF.

## SHIP — listo para el lote de Alberto

**Railway worker, añadir 4 variables**: `F1_RESOLVE_GOVERNED=on` ·
`F1_MENTION_PRECEDENCE=on` · `GENERATOR_NO_REASK=on` · `IDENTITY_FETCH=on`
(las IDENTITY_RESOLVE ya están). Tras el flip: **verificación en producción patrón
DEC-099 = re-lanzar la conversación real de la Kidde en Telegram** y ver el hilo
responder programación de la 2X-AF1-FB-S a nivel familia sin re-preguntar la variante.
Rollback = quitar las 4 variables (flags default-off, byte-idéntico probado).
