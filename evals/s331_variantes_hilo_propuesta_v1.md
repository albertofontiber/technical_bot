# s331 · Propuesta — La variante del técnico muere dos veces: binding gobernado a nivel de TURNO + conducta de hilo

> **Estado: PROPUESTA para dúo adversarial (Protocolo 3 — MEDIO/ALTO en zona de dolor:
> retrieval/catálogo/legacy). NADA cableado.** Flags default-off = byte-idéntico.
> Caso semilla: hilo real Kidde 2X-AF1-FB-S (18-ago-2026, 👎 de Alberto). GO de Alberto
> al plan de ataque: s331 (20-ago). Autor: sesión s331.

## 0 · TL;DR

Un técnico dice su variante exacta («tengo la 2X-AF1-FBS») y el bot, dos turnos después,
le pregunta «¿qué variante exacta del 2X-AF1 tienes instalada?». No es un fallo de corpus
ni de retrieval semántico: **la variante se destruye al LEER (extracción legacy trunca a
familia) y al ARRASTRAR (el hint del hilo solo lleva lo bindeado)** — mientras el resolver
GOBERNADO, vivo en producción para retrieval, la detecta perfectamente incluso en la
grafía ASR sin guiones. La propuesta: **(A)** que el turno conversacional consuma la MISMA
resolución gobernada que ya usa retrieval (flag `F1_RESOLVE_GOVERNED`), **(C.1)** que el
hint lleve la mención no-resuelta del usuario (flag `HINT_SURFACE_MENTION`), **(C.2)**
regla de generación anti-re-pregunta con trigger en código (flag `GENERATOR_NO_REASK`).
Cero piezas nuevas de infraestructura: es CABLEAR lo que existe. Gates pre-registrados
G0-G4 + verificación en producción re-lanzando la conversación real.

## 1 · El caso real (verificado en `query_logs`, 18-ago-2026)

| # | id | UTC | route | usuario (voz→ASR) | bot |
|---|----|----|-------|--------------------|-----|
| T1 | `b81a8af9…1e47` | 21:42:31 | `catalog_shortcut` | «¿Qué centrales de Kidde tienes?» | Lista «Kidde — central (36 de 156)» **incluyendo 2X-AF1-FB-S** |
| T2 | `e046836f…89ea` | 21:43:15 | `rag` | «Sobre la 2X-AF1-FBS.» | «¿Qué necesitas exactamente de la 2X-AF1-FBS: especificaciones…, programación…?» |
| T3 | `4fbca15f…3c71` | 21:43:53 | `rag` | «Programación principalmente.» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** |
| — | (feedback) | 21:44 | 👎 | «Si ya te he dicho que la que tengo es la FBS, ¿no debería estar información suficiente?» | — |

El propio bot ofreció «programación» como opción en T2 y, cuando el usuario la eligió,
volvió a pedir la variante que T2 ya contenía. **TECH_DEBT #49, trigger (c) — «queja de
técnico por arrastre/colisión de variante» — DISPARADO.** Es tráfico real del piloto, la
clase «técnico que lee la etiqueta de su central» completa, no un gold sintético.

## 2 · Diagnóstico mecánico (sondas $0, reproducibles)

**(D1) La extracción legacy trunca a familia — en el turno que CONTIENE la variante.**
`extract_product_models` (`src/rag/retriever.py:92`) une `data/model_catalog.json`
(derivado del CORPUS: en la familia AF1 solo existe `2X-AF1-S`) + regex seed. El
«2X-AF1» sale del **alias de familia** `_base_aliases("2X-AF1-S")` (`src/rag/catalog.py:75-84`);
el seed devuelve `[]`. Sonda:

```
extract_product_models("Sobre la 2X-AF1-FBS.")  == ['2X-AF1']   # también con la grafía canónica 2X-AF1-FB-S
MODEL_PATTERN.findall(...)                       == []
```

El alias de familia NO es el bug (existe para que una query de familia recupere
variantes); el bug es que la resolución GOBERNADA no participa en el turno.

**(D2) El estado del hilo guarda las palabras del usuario y nadie las usa.**
`WorkingState.last_query` conserva «Sobre la 2X-AF1-FBS.» (`conversation_policy_impl.py:721-747`),
pero `_carry_forward` (`:442-451`) construye el turno solo con los modelos bindeados:
T3 llegó a retrieval+generación como `«Programación principalmente. (contexto: 2X-AF1)»`.

**(D3) El resolver gobernado detecta la variante — incluso en grafía ASR.**
`catalog_resolver.detect("Sobre la 2X-AF1-FBS.") == ['2x-af1-fbs']` (regex generada del
catálogo, separador-insensible, longest-first; `src/rag/catalog_resolver.py:231`). No está
en cuarentena (`config/identity_quarantine_v1.yaml`: 0 tokens `2x`).

**(D4) El resolver corre en retrieval, pero re-escanea la QUERY — y el hint de T3 ya no
contenía la variante.** `retriever.py:1859`: `models, _identity_res =
_resolver.resolve_for_retrieval(query, models)` — una llamada por query, DELIBERADAMENTE
fuera de `extract_product_models` («se llama en 3 sitios», comentario s91 en `:1853-1858`).
En T2 retrieval pudo resolver la variante internamente; **el estado conversacional, el hint
y el stamp `product_models` se alimentan de la extracción legacy** (`telegram_bot.py:1933`)
y arrastraron la familia. En T3 el resolver no tenía ya nada que detectar. El resolver fue
silenciado por el hint de su propio pipeline.

**(D5) Los datos y los manuales EXISTEN — el final del túnel está pagado.**
`data/catalog/products.jsonl`: `kidde:2x-af1-fb-s` **activo** (gate GT 19/19 PASS, §0
adjudicado por Alberto 14-ago). `data/catalog/doc_map.jsonl`: la variante mapea como
`primary` a ≥4 docs de familia en corpus (installation EN+ES, operation ES, quick guide ES
— esta última por regla adjudicada por Alberto 16-ago: «la guía es de la FAMILIA 2X-A»).

## 3 · Diseño propuesto (3 flags, default-off = byte-idéntico)

### A · `F1_RESOLVE_GOVERNED` — el turno consume la resolución gobernada

- **Dónde:** el call-site del path conversacional (`telegram_bot.py:1933` /
  seam F1), NO dentro de `extract_product_models` (respeta la decisión s91 «una llamada
  por query»; los otros 2 call-sites no cambian).
- **Qué:** `turn_models = resolver.resolve_for_turn(query, extract_product_models(query))`
  — wrapper fino sobre la MISMA resolución de `resolve_for_retrieval` (detección +
  canonicalización + política replace/add + cuarentena + regla monótona s287), **sin** los
  efectos seam-2 (ni `allowed_sources` ni fetch). Devuelve canónicos
  (`2X-AF1-FB-S`) para estado, hint y stamp.
- **Punto fijo:** el hint del turno siguiente lleva el canónico → `detect` lo re-encuentra
  → misma resolución. Estable por construcción; test de idempotencia en G0.
- **Gating de entorno:** activo solo con `IDENTITY_RESOLVE=on` (el mismo flag/postura C1
  de producción); con `off` → passthrough exacto de hoy.

### C.1 · `HINT_SURFACE_MENTION` — la mención no-resuelta viaja en el hint

- `advance_working_state` guarda además `last_unresolved_mention`: token(s) con forma de
  modelo presentes en la query del usuario que la resolución NO bindeó (diff conservador a
  nivel token, no la frase entera). `_carry_forward` los añade:
  `«(contexto: 2X-AF1-FB-S)»` o, sin binding, `«(contexto: 2X-AF1; el usuario mencionó
  "2X-AF1-FBS")»`.
- Cubre la clase que A no puede: variantes AÚN fuera del catálogo (la próxima marca del
  ala larga) y grafías ASR no normalizables. Con A funcionando, C.1 es la red.
- **Lock-step declarado:** `WorkingState` es diseño congelado MT-1a espejado en el harness
  MT-1b — se cambian AMBOS o ninguno.

### C.2 · `GENERATOR_NO_REASK` — conducta: no re-preguntar lo que el hilo ya dice

- Regla inyectada al prompt del generador **solo cuando el turno lleva hint/mención**
  (trigger en CÓDIGO, lección DEC-097: prompt-gated sobre-disparó hp009): «el contexto ya
  identifica el producto (X): no vuelvas a preguntar por él; si tu evidencia es de
  familia, responde declarando el alcance y señala qué puntos varían por variante».
- No toca el clarify determinista de la política (rama E, clarify-solo-con-divergencia-real
  sigue intacto — es upstream y $0).

### B · Residual de datos (Alberto, NO bloquea)

Los productos, el doc_map y la regla de familia YA están adjudicados (14/16-ago). Queda
como packet aparte la pregunta DIFERIDA del paraguas «2X-A» (token de familia como término
resoluble) — mejora menciones a secas «la 2X-A», no este caso.

## 4 · Gates pre-registrados (nada se enciende sin pasarlos)

| Gate | Qué mide | Criterio | Coste |
|------|----------|----------|-------|
| **G0** unit ($0) | Binding: cohort de variantes canónicas + grafías ASR (2X-A completa + muestra de los 80+ pares de #49: Argus SG*-IS, Aritech 2X-AT-F2-*, Notifier…) + idempotencia hint→detect + **flag-off byte-idéntico** (patrón equivalencia s316e) | 100% cohort al canónico esperado; off = conducta actual exacta | $0 |
| **G1** replay | Replay congelado del hilo real (T1-T3 por id) con flags ON por el path harness F1+serving | T3 sale del bucle: respuesta de programación con alcance de familia, o decline honesto; **cero preguntas de variante**; OFF reproduce el bucle | ~$1-2 |
| **G2** no-regresión | sweep-39 composición servida ON-vs-OFF con control de ruido (DEC-096: rerank no determinista → OFF-vs-OFF o N-reps) + **centinela hp009 a nivel hecho** (historia REPLACE/DEC-091b) + famtie + flows MT existentes (`scripts/test_multiturn_vs_gold.py`, mt05b pinned) + latencia p50/p95 (presupuesto +≤100 ms) | 0 regresiones reales (verificación leyendo respuestas, regla DEC-092b); MT flows verdes | ~$5-10 |
| **G3** conducta | A/B 24 gens (patrón DEC-162e) para C.2: hilos con/sin variante previa | re-pregunta 0/N con dato presente; clarifies legítimos SOBREVIVEN (centinela hp009-conducta) | ~$3-6 |
| **G4** pre-ship | Censo Railway (`scripts/s322_railway_censo.py`): `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` REALES en el servicio worker | confirma la asunción C1/s281 | $0 |
| **Ship** | PR (draft ya en rama `claude/synthesis-miss-attacks-p6ox9p`) → merge Alberto → flags ON por lote Railway → **verificación en producción re-lanzando la conversación real** (patrón DEC-099, query_logs) | la misma secuencia T2→T3 responde programación sin re-preguntar | ~$0 |

## 5 · Alternativas consideradas y descartadas

1. **Historia completa del hilo al generador** — re-abre el arrastre de producto que
   INTENT_LLM acaba de cerrar (gate 40/40, DEC-203/204); cambia la vara de TODO lo medido
   single-turn (DEC-154 separó las fases a propósito); coste/latencia en cada turno.
2. **Prompt-only (solo C.2, sin A/C.1)** — el generador seguiría CIEGO a la variante:
   pedirle que no pregunte lo que no sabe = invención o familia sin declarar.
3. **Resolver DENTRO de `extract_product_models`** — revierte la decisión s91 «una llamada
   por query» (`retriever.py:1856`), triplica resolución en los 3 call-sites y mezcla
   semánticas detector/resolver.
4. **Quitar el alias de familia `_base_aliases`** — el alias es correcto para recall de
   familia; eliminarlo regresa las queries de familia y NO da el binding de la variante
   (la variante no está en el catálogo de corpus: no hay nada que matchear).
5. **Variantes en el prompt de Whisper** — medido NO (DEC-233: prompt saturado 990/1000,
   añadir diluye). Además `normkey` ya absorbe FBS↔FB-S sin tocar el ASR.
6. **Re-ingesta por variante** — no existen manuales por variante (el fabricante publica
   familia: 4 docs 2X-A mapeados). Es un problema de MAPEO, no de corpus.
7. **Esperar al re-censo del piloto (~200 msgs)** — el trigger #49(c) ya disparó con caso
   real; el coste de esperar son 👎 de DGs sobre una clase entera («técnico que lee su
   etiqueta»).

## 6 · Riesgos y gaps declarados

1. **hp009-clase (sobre-filtrado REPLACE):** binding más fino ⇒ filtro más estrecho. El
   resolver ya trae la regla monótona s287 y **G2 lleva centinela hp009 a nivel hecho**.
2. **Semántica del stamp `product_models` cambia** (canónicos con variante): revisar
   consumidores (panel/clasificación no lo usan — verificar en G0; INTENT_LLM: población
   de la rama ambigua puede moverse — declarado, medible en su tasa `intent` del trace).
3. **Lock-step MT-1a↔MT-1b** (WorkingState + harness espejo): se cambian juntos, con test.
4. **`IDENTITY_RESOLVE=on` en prod es ASUNCIÓN** (digest/C1 s281, perfil
   `release_profiles.py:329` lo exige) — G4 la verifica ANTES de gates e2e; si estuviera
   off, A queda supeditado a la decisión ya tomada en s281 (encenderlo no es de esta
   propuesta).
5. **Ruido del rerank en G2** (DEC-096) — control OFF-vs-OFF o N-reps, pre-registrado.
6. **C.1 mete texto no validado del usuario en el hint** — mismo canal que la query (ya es
   texto del usuario); el cambio de FORMA del prompt lo mide G3.
7. **Cobertura de «programación» en el manual de familia no verificada a nivel contenido**
   — G1 lo mide; decline honesto con alcance es resultado ACEPTABLE del gate (lo
   inaceptable es el bucle).
8. **Latencia** — una resolución extra por turno (regex cacheada en módulo; presence
   lookup con TTL); presupuesto p50 +≤100 ms, medido en G2.

## 7 · Settled citados y su métrica (Protocolo 2.5 — coinciden con el objetivo de HOY)

| Settled | Métrica del veredicto | Relación con esta propuesta |
|---|---|---|
| DEC-069 consumo aditivo del pool = NO-OP-con-regresión | retrieval-miss (pool) | NO se toca el pool: A alimenta la lista `models` = el seam VÁLIDO medido (LEVER2, hp018 4/4) |
| DEC-084/091b REPLACE sobre-filtra con linking incompleto | famtie/hp009 | Esto COMPLETA el linking query-side a nivel turno; hp009 = centinela G2. Retoma el «fix aparcado» de 091b, no lo contradice |
| DEC-074 BP entity-linking 2 etapas | (workstream) | Integración turno-side pendiente del BP; catálogo/doc_map/re-tags ya ejecutados (DEC-212-215) |
| DEC-154 utilidad conversacional | vara MT propia | G1/G2-MT son la vara; el single-turn no se re-litiga |
| DEC-233 marcas por voz | conducta/ASR | Fuera de alcance salvo que `normkey` absorbe FBS↔FB-S; la tabla de confusiones observadas sigue su curso |
| DEC-096 rerank no determinista | A/B rerank | Diseña el control de ruido de G2 |
| TECH_DEBT #49 | (deuda, trigger) | Trigger (c) disparado 18-ago — esta propuesta lo ejecuta con el instrumento que s72 no tenía (catálogo gobernado) |

## 8 · Contrato

**BP**: una sola fuente de verdad de identidad (catálogo gobernado, DEC-074) consumida por
TODAS las capas — retrieval ya la usa; el turno conversacional es la capa que falta.
**Estructural**: ataca la raíz (binding/estado), no el síntoma (el caso Kidde); C cubre la
clase residual por diseño. **Escalable**: marca nueva = entra al catálogo y el turno la ve
sin código nuevo; sin curación per-familia en código.

## 9 · Coste y secuencia

Fase 0 (este doc + dúo Sol xhigh + Fable emparejado): ~$3-6 · Build A+C flag-off + G0:
1 sesión · G1-G3: ~$10-18 · G4+ship+verificación prod: ~$0. Todo en rama
`claude/synthesis-miss-attacks-p6ox9p` (PR draft); merge y flags Railway = Alberto.
Prioridad global intacta: el paquete del abogado va primero.
