# s103b — Landing del desplazamiento hyq, v3.1 (post-dúo) — EXTENSIÓN ACOTADA del aside

**Veredicto dúo r1 (×2 lados, frescos): CABLEAR-CON-CAMBIOS convergente.** Cross-model 5/5
confirmados (CRÍTICO: los gates judge-free no medían el efecto real — rerank 50→60); sub-agente
9 (CRÍTICO ×2: 5/6 filas de mi tabla de predicción eran tautológicas bajo extensión + el spec
tenía DOS cableados incompatibles y uno era NO-OP silencioso en `:1649`). 0 falsos positivos.
v3.1 incorpora TODO.

## Qué es (y qué re-abre — declaración explícita)

El carve-out hyq de s102 RESERVA slots del diversify para re-adjuntar la cuota (aside) → doble
cobro medido (DEC-100: factura cat022×3; y el re-landing v2.1 por eviction = NO-GO medido).
v3.1: **no reservar nada** — el aside se re-adjunta como **extensión acotada** del pool
(`≤ top_k + HYQ_PILOT_QUOTA`), después del corte `base = merged[:top_k]`, el mismo idioma de
código que el identity-fetch (`retriever.py:1643-1668`).

**Esto RE-ABRE conscientemente la alternativa A2 que DEC-100 descartó** (razonada, no medida) —
re-litigación declarada, no extensión de canon. Lo que el canon realmente dice (corrección F1
sub-agente — sin citas empalmadas):
- `LEVER_DIGEST` fila aditivo: la regresión medida de DEC-069 fue **unión-dentro-de-pool-CAPADO**
  (hp012 desplazado). La fila separa explícitamente el brazo "fetch acotado" como medición NUEVA
  legítima; ese brazo se midió s93 = **NO-OP-en-famtie** (selector no elegía), rama cerrada.
- El comentario del código (`:1646-1648`) documenta la extensión como patrón que "nunca desplaza
  a nadie — el reranker decide".
- **Lo que NADIE midió: el reranker con +10 chunks competitivos SIEMPRE que el canal dispara
  (31/39)** — el identity-fetch es precedente de IDIOMA DE CÓDIGO, no evidencia operativa de
  no-daño (F2; flag default-off, nunca operado en demo). Ese hueco es exactamente lo que el
  gate discriminante de abajo mide ANTES del bvg.

## Cableado (ÚNICO — fix F4)

1. **Step 5a:** aside apartado ANTES del diversify (consenso s59: el interleave cortaría los
   surrogates — medido s102 gate v1) + dedup aside-gana (fix #1 dúo s102). El diversify corre a
   `top_k` COMPLETO. **NO se re-adjunta aquí.**
2. **Post-corte:** inmediatamente tras `base = merged[:top_k]` (`:1649`) y ANTES del bloque
   identity-fetch (así su `have` ve los ids del aside — F6, sin ventana de duplicado):
   - cinturón de **idioma ESTRICTO inline** (F5: el aside se apartó antes del Step 5c; el
     fail-open de `_filter_by_language` sobre lista corta se INVIERTE — mismo cinturón que el
     fetch `:1661-1665`). Lifecycle/model-filter ya aplicados (el aside pasó Steps 4b/5a-pre).
   - `base = base + aside_ok` + **traza `_tr("post_hyq_aside", base)`** (F7: los instrumentos
     de deathpoint no deben leer "muere en DIVERSIFY").
3. **Contrato de tamaño COMPUESTO por flags** (F6/F8): pool ≤ `top_k` + (`HYQ_PILOT_QUOTA` si
   canal ON y query-con-modelo) + (extras del fetch si `IDENTITY_FETCH=on`; default-off en demo).
   Con `top_k` pequeño (eval_rag 15, tests 5) la cuota absoluta pesa proporcionalmente más —
   declarado; la cuota es hiperparámetro del piloto pineado a prod top_k=50.

## Gates (pre-declarados; corrección F3 — separar sanity de DISCRIMINANTE)

**Sanity (pasan por construcción — se verifican, no discriminan):** diana cat022 3/3 · flip
6K8 vivo · hp011 pool = null · trim 0 · anclajes ≥ +1/−0 · negcontrol EXCESS-HIGH ≤ 7 (pool-60
lo mejora mecánicamente; se estampa el caveat).

**DISCRIMINANTE 1 (judge-free, ANTES de bvg) — served-churn null-corrected (norma DEC-096):**
por gold (39 dev): `rerank(pool_old)` ×2 = null del rerank (no-determinista medido DEC-096) ·
`rerank(pool_v3)` vs `rerank(pool_old)` = churn del top-10 servido. Métrica: churn EXCEDENTE
sobre el null, agregado y por-gold. Gate: excedente ≈ 0 en los golds OK de v2.2 (los 91 hechos
OK viven en el served-set); los golds con churn excedente → **leer las respuestas** (patrón
DEC-092b) antes de juzgar.
**DISCRIMINANTE 2:** bvg K=3 outcome (SOLO si D1 pasa; coste ~$20-30, dentro del tope $150).

**Artefacto F9 (regla C contra mi claim):** la degeneración de family-aware (cat022/hp011 sin
cross-family en pool → la cascada degenera a v2.1) se re-corre con script COMMITTEADO y lista
RESUELTA de modelos (mi probe inline usó la lista pre-resolver = inválido para hp018) →
`scripts/s103_family_tier_probe.py` + `evals/s103_family_tier_probe.json`.

## Coste declarado

- Rerank ve ≤60 chunks donde el canal dispara: +≤20% input/latencia de ESA llamada. El
  fallback-truncate del reranker serviría los primeros 10 del pool (aside al final fuera) =
  igual que hoy (posiciones 40-49 tampoco entran). Generador NO cambia (ve los 10 servidos —
  verificado `telegram_bot.py:460-479`).
- Scoreboard: el bucket in-pool gana +10 de ancho mecánico donde el canal dispara → **caveat
  estampado en la fila** si se llega al assessment (F8).

## Alternativas (por qué no)

- v2.1 eviction: NO-GO MEDIDO hoy (DEC-100). · Cascada family-aware: degenera a v2.1 donde no
  hay cross-family (artefacto F9); queda como candidato de HYGIENE en DEC-074, no de landing. ·
  Híbrido: cat022 seguiría perdida. · Status quo: cat022×3 perdidos + squeeze estructural.

## Piezas

`retriever.py` Step 5a (sin reserva) + post-`:1649` (aside estricto + traza) ·
`tests/test_hyq_channel.py` (contrato compuesto + extensión + idioma) ·
`scripts/s103_family_tier_probe.py` (F9) · `scripts/s103_served_churn_gate.py` (D1) ·
probes/instrumentos de hoy re-corridos (etiquetas v3).

---

## ADDENDUM post-medición (enmienda VISIBLE — findings F1/F2/F3/F5 del cross-model sobre el diff)

**Desviación del pre-registro, declarada:** el D1 pre-declarado (served-churn crudo) se corrió
con un instrumento de contraste INVÁLIDO (v1: `rerank(sin-aside)` vs `rerank(con-aside)` = mide
la PRESENCIA del canal ya shippeado, no el delta old-vs-v3; penalizaba el flip de cat016). Su
artefacto dice NO-PASA (65/8) y se conserva sin editar. El v2 corrigió el CONTRASTE (old-real vs
v3) y REFINÓ la métrica a pérdida-de-anclas-OK-en-servido (más ligada al mandato que el churn
crudo, que es propósito del lever, no daño). **Esto es un cambio de métrica post-declaración**:
el gate que se presenta como discriminante judge-free es el v2 (LOSS 0 / null 0 / GAIN +1) — el
lector debe saber que la métrica evolucionó y por qué. El bvg se corrió tras el v2 (no tras el
v1), y sus 2 regresiones flaggeadas se LEYERON (DEC-092b): cat024 = artefacto del juez (5ª
instancia); cat021 = REAL → tratada abajo.

**Acoplamiento declarado (F5):** el candidato de ship son DOS mecanismos con flags
independientes y rollback separado: (1) landing v3.1 (retriever; el canal HYQ_TABLE ya está on
en prod); (2) **bloque de selección CODE-GATED** (generator, `GENERATOR_SELECTION_BLOCK`,
default off) — fork DEC-097 ejecutado sobre su gatillo declarado (composición-mala reproducible:
el rerank-60 sirve el user-guide EN del 40/40R y la generación asume la variante). Cadena
medida: seam-prompt-gated cura cat021 3/3 PERO rompe hp009 2/3 (trigger textual sobre-dispara);
iteración de wording lo EMPEORA (3/3) → trigger movido A CÓDIGO (`_SELECTION_INTENT` regex +
`_assemble_system(query)`): sweep 39 dev = SOLO cat021 dispara; hp009 y toda spec/avería quedan
byte-idénticas POR CONSTRUCCIÓN (6 unit tests, $0). Por qué van juntos: la regresión cat021 es
CAUSADA por la composición v3.1; shippear (1) sin (2) banca cat022×3 rompiendo cat021.
