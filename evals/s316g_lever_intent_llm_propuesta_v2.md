# s316g v2 — Lever INTENT_LLM: especificación completa tras la ronda 10 (DISEÑO VIGENTE)

> ## Estado tras el gate y la ronda 11 (leer primero)
> - **Modelo del lever = `claude-sonnet-4-6`** (Haiku NO-GO en el gate: 2 falsos SWITCH,
>   uno claro en EN). Cifras reales: ~$0,003/disparo · p50 1,3 s / p95 4,4 s medidos con
>   el cliente servido (timeout 6 s, max_retries=0). Las menciones a Haiku/300-500 ms de
>   abajo quedan como registro del diseño pre-gate.
> - **El FLIP queda BLOQUEADO por dos gates pendientes** (Sol r11): (1) el paquete de
>   observabilidad en `rag_trace` (esquema cerrado: builder+validador+allowlist+tests —
>   hasta entonces la decisión va a log estructurado); (2) el e2e del camino servido
>   (cliente frío, timeout, fail-open) con recibo. Sin ambos, el flag NO se enciende.
> - Paridad gate↔serving reparada en r11: exención `all()` sobre marcas mencionadas
>   (el caso mixto de la cohorte ya llega al clasificador), tokenización con guion
>   (Pepperl-Fuchs), lever alcanzable desde la rama same_mfr con marca ajena presente.

**Qué es.** El v1 fue NO-SÓLIDO ×2 con veredicto de dirección («la arquitectura apunta a
SÓLIDO con las reparaciones»). Este v2 integra los 17 hallazgos (Sol 7 · Fable 10, regla
C aplicada — los anclados en código, verificados). El objetivo, la auditoría de levers y
las alternativas del v1 siguen vigentes.

## Lo que la ronda tumbó y cómo queda

### 1. El gate del JUICIO: cohorte congelada (Sol CRÍTICO — el corazón de la ronda)

Mi gate estubeaba la decisión que constituye el lever: probaba cableado, no juicio. Queda:

- **`evals/s316g_intent_cohort_v1.yaml`**: ~40 casos etiquetados `COMPAT`/`SWITCH`,
  CONGELADOS antes de medir. Población: los contraejemplos de las 5 rondas (tildes,
  muletillas, «en» vs «con», «¿Morley tiene app?», «vamos a ver si es compatible…»),
  el caso orgánico, elípticos («¿y con X?»), y **≥8 casos EN** («switch to Morley»,
  «and on Kidde, how…») — el «ES/EN gratis» del v1 pasa de claim a medición (Sol M6).
- **Umbral PREDECLARADO y ASIMÉTRICO**: un falso `SWITCH` rompe compatibilidad legítima
  (grave); un falso `COMPAT` es la conducta de hoy (benigno). Gate:
  **falsos SWITCH = 0/K en los casos COMPAT** (K=3 repeticiones por caso, estabilidad) y
  accuracy global ≥90%. Si falla → NO-GO del flip, el flag se queda OFF, y el diseño
  vuelve con otro modelo o prompt — **anti-gate-shopping: sin re-tunear el prompt contra
  la cohorte** (patrón DEC-126); una revisión del prompt = cohorte nueva congelada.
- Coste: ~40×3×$0,0002 ≈ **$0,03**. Script: `scripts/s316g_intent_cohort_gate.py`,
  recibo JSON versionado.
- **DEC-102 se cita SOLO como heurística de coste** (Sol M5 · Fable menor): aquel GO
  midió a Haiku generando enunciados; el juicio de intención lo establece ESTA cohorte.

### 2. La extensión de misma-marca, corregida (Fable — verificado contra el catálogo)

`classify_model_manufacturer` devuelve el nombre COMPLETO («Argus Security») y el token
de la rama B es la palabra PRIMARIA («argus») — 8/26 fabricantes son multi-palabra. La
comparación del v1 fallaba y una pregunta de misma-marca Argus habría pagado Haiku (y un
«switch» erróneo tiraba el estado). Queda: normalización a palabra-primaria (la MISMA de
`_config_brand_tokens`): `token == classify(m).split()[0].lower()`. Estados multi-modelo:
la exención aplica si el token casa con **cualquiera** de las marcas del estado;
`classify→None` se ignora (si NINGUNA resuelve → no hay exención posible y decide el
LLM, fail-open declarado). Y la exención vive **DENTRO de la rama del lever** (solo
corre antes de llamar al LLM): con `intent=None` el camino es BYTE-IDÉNTICO a hoy — el
claim de OFF-inerte que Sol m7 demostró falso en el v1, ahora verdadero por construcción.

### 3. Colisión de dominio en `BRAND_TOKENS` (Fable): la guarda que faltaba

La guardia del transporte tiene `_MARCAS_AMBIGUAS` + test de colisión; la rama B no —
un `fuego.yaml` futuro metería «fuego» en el vocabulario de la política y el lever
convertiría cada mención de fuego en una llamada a Haiku con riesgo de switch-que-borra.
Queda: la rama del lever EXCLUYE tokens de `_MARCAS_AMBIGUAS` (importada del plan, una
sola lista) + **test de colisión espejo para `BRAND_TOKENS`** (si config mete una marca
del vocabulario del dominio, CI rompe y obliga a declararla).

### 4. Contrato del parser y del prompt (Fable + Sol)

- **El transporte normaliza; la política solo ve `{compat, switch, None}`**: el callable
  hace `strip().upper()`, acepta exactamente `COMPAT`/`SWITCH` (con tolerancia a
  puntuación final), y CUALQUIER otra cosa → `None`. La política trata todo valor fuera
  del contrato como `None` (defensa en profundidad).
- **Inputs del prompt**: pregunta cruda + modelos del estado + **la marca del estado ya
  resuelta** (la señal decisiva, computada gratis en la rama; si `classify→None`, se
  declara «marca desconocida» en el prompt). `last_query` NO se manda (minimización).
- **Async** (Sol M2): `resolve_conversational_turn` corre HOY en el event loop
  (`:1102`); una llamada síncrona de 3 s lo bloquearía entero. Con el flag ON, la
  resolución se mueve a `await asyncio.to_thread(...)` (patrón de `:1183`); con OFF, el
  camino actual intacto.

### 5. El gate de CABLEADO: cirugía declarada del harness (Fable — el v1 no lo declaraba)

`run_contract` llama a `resolve` sin `intent` y el schema no puede fijar el stub por
turno. Alcance añadido: campo **`stub_intent`** por turno en el YAML (validado por
`validate_schema`), `run_contract` construye el stub determinista y **asevera que fue
llamado cuando el turno lo declara** (verde-vacuo fuera — la lección del testigo de fase
B, Fable menor); los golds ganan aserción de **`rationale`** (distingue
`brand_compat_confirmed_llm` de `brand_compatibility_in_window` y del fail-open).
`IntentFn` entra en las TRES superficies del precedente `rewrite` (Protocol + Stub +
`resolve_conversational_turn`) — contrato congelado tocado, DECLARADO.

### 6. Golds (Fable): mt15, y el path no-servida CONSERVA un gold

- mt13 t2 → «¿es compatible con equipos **Morley**?» · t3 → «¿y con **Notifier**?»
  (cadena de alcanzabilidad de producción verificada por Fable) · t4 queda.
- **t2b NUEVO en mt13: «¿es compatible con detectores cofem?»** — cofem está en
  `BRAND_TOKENS`, NO en `_MANUFACTURER_NAMES` ni en DB ⇒ SÍ llega a la rama B en
  producción (Fable verificó la cadena): el path marca-no-servida-alcanzable conserva
  gold (carry esperado, con o sin lever).
- **`mt15_fallthrough_switch` NUEVO** (mt14 existe — colisión): contexto NC-PF2 →
  «¿y en Morley cómo se hace el reset?» → `stub_intent: switch` → STANDALONE.
- Estados multi-marca: un turno del gold los declara (la exención multi-modelo de §2).

### 7. Observabilidad con su alcance real (Sol M4)

`rag_trace` es esquema CERRADO y el sink descarta trazas inválidas: estampar
`intent_llm {decision, ms}` exige builder + validador + allowlist + tests. Entra al
alcance del build como paquete propio — no una nota. `timings` NO se toca (4 etapas
contractuales); el ms del intent va en su clave.

### 8. Cifras con fuente (Fable): el «19%» queda medido y versionado

La medición de s316b (68 consultas reales distintas → 13 nombran marca sin modelo) se
re-ejecuta y VERSIONA como `evals/s316g_poblacion_rama_b_v1.json` en el build; hasta
entonces la cifra se cita como «medición de sesión, recibo pendiente». RGPD (Fable):
mismo encargado (Anthropic) y riesgo incremental ~0, pero el flujo nuevo se ANOTA en la
matriz (`RGPD_LIFECYCLE_MATRIX_TEMPLATE.md`) — una línea, con el [DECIDIR] de Alberto
intacto.

## Secuencia del build (gates en orden, cada uno corta)

1. Cohorte congelada + script + **gate del juicio con Haiku REAL** (~$0,03). Si falla →
   NO-GO, flag nunca se enciende, fin honesto.
2. Cirugía del harness (stub_intent + rationale + aserción de-llamada) + golds mt13/mt15
   → contrato re-congelado, 48/48 + nuevos en verde con OFF byte-idéntico.
3. Seam en la política (3 superficies) + rama del lever (exención corregida + exclusión
   de ambiguas + decisión) + transporte (flag, callable, to_thread, traza) + tests.
4. Dúo sobre el DIFF (la lección FUEGO). Suite completa.
5. e2e puntual con Haiku real (~$0,01) → recibo → **decisión de flip de Alberto**.

## Gaps que quedan declarados

Fail-open reproduce el bug si Haiku falla (best-effort, correcto por diseño); latencia
+300-500 ms en la rama (se mide en la traza, no estimada); marcas fuera de
`BRAND_TOKENS` no entran a la rama B (residuo declarado); el juicio REAL solo se
garantiza al nivel de la cohorte (~40 casos) — la producción lo medirá vía traza.
