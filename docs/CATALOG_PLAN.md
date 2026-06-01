# Plan maestro — crecer el ruler como instrumento diagnóstico (s38.5)

> **Estado: MAESTRO** (cerrado tras 3 pasadas del dúo adversarial; traza en §8). v1/v2 fueron NO
> SÓLIDO por fallos estructurales; v3 por contratos de implementación; v4 los reconcilia y declara
> honestamente lo que se resuelve en el build SUPERVISADO (B2). Un plan no sobre-especifica
> implementación — la enruta.

## 0. Principios rectores
- **Frontera de autonomía**: automatizar lo seguro; supervisar lo caro-si-falla. *Construir* ≠ *confiar*.
- **Circularidad**: GPT-5.5 (linaje ≠ bot=Sonnet) **MITIGA** al co-generar; NO la rompe (el orquestador
  Claude aún mina/filtra/ensambla). El **sign-off humano del scorer (B1)** es el único corte fuerte.
- **North-star de automatización** (Alberto): tender a alta de preguntas **push-button** (matriz de
  taxonomía auto-selecciona celda → 3-bandas → gold). Honesto: hoy NO es push-button — los casos duros
  (scans/diagramas/conflictos) no se detectan solos de forma fiable; es la **dirección**, no el estado.
- **Invariante de seguridad**: todo en RAMA; cero merge/deploy/escritura-a-prod. `gold_store.upsert`
  escribe un **YAML local** (`evals/gold_answers_v1.yaml`), no Supabase. Localización a chunks_v2 = SELECT.
- **Baseline reconciliado**: AC-220 (PR #24) + filtro de idioma YA están en prod → **el baseline s37
  (8 FALLO/10 PARCIAL/0 PASS) está SUPERSEDED**. El catálogo mide el **estado ACTUAL** de prod; cualquier
  delta de lever futuro se mide contra un baseline FRESCO sobre el catálogo crecido, no contra s37.

## 1. Contrato operativo (honesto sobre enforcement)
- **Caps de gasto AUTO-VIGILADOS** (no hay harness que aborte; yo trazo y paro): ≤ ~$15 noche (A) /
  ≤ ~$40 bulk (C). El backstop DURO real es el invariante §0 (rama) + la revisión de la mañana.
- **Concurrencia**: 1 en A (sin fan-out); máx 4 en C.
- **Timebox**: A ≤ 3 h; C ≤ 6 h. Excedido → parar, informe parcial.
- **Resumibilidad**: `gold_store.upsert` reescribe el YAML entero por gold; **NO es atómico a prueba de
  crash** (un fallo a media-escritura puede corromper el YAML) → mitigación: copia de respaldo del YAML
  antes de cada upsert; la revisión de la mañana valida integridad. (Para 6-8 no se monta Workflow/journal.)
- **Mínimo viable** declarado por fase.

## 2. Fases por frontera de supervisión

### FASE A — ESTA NOCHE (autónoma, sin input). LO ÚNICO.
- **A1 · Construir el juez-LLM de completitud (#35)** en `atomic_scorer.py` **detrás de flag
  `--prose-llm` (DEFAULT OFF)** + **test de equivalencia** (los 19 en modo mecánico antes/después del
  cambio = idénticos → el modo nuevo no contamina el scorer existente). Correrlo sobre **los 19 +
  hp003/hp007** → emitir **DATOS CRUDOS por-gold**: `qid · veredicto_viejo · veredicto_nuevo · hechos
  que cambiaron · texto-del-bot vs hecho`. **SIN narrativa de "mejora"** (anti rubber-stamp).
- **No declarar validado. No usar para nada.** Mínimo viable de la noche = A1 con datos crudos + test
  de equivalencia verde.
- **Mecanismo**: sesión autónoma simple. Stop+flag ante cualquier fallo. Rama `eval/s38-night-catalog`.

### FASE B — MAÑANA (supervisada, contigo).
- **B1 · Sign-off de #35** con criterio de aceptación: (i) ningún FALLO→PASS espurio; (ii) los flips
  PARCIAL→PASS = paráfrasis correcta verificable; (iii) muestreo de admit/refuse/conflict/gap sin
  sobre-acreditar. Sin sign-off → fallback mecánico (completitud = suelo).
- **B2 · Especificar+construir el pipeline de autoría** (contratos que NO se hacen de noche):
  - **Mecanismo C4** (cross-check de ubicación, ver C4) — incluida la **ruta-(b) semántica per-manual**
    (NET-NEW: definir embedder/umbral) y el **2º lector de valores** (ver C4.4).
  - **Contrato refuse-inference** (universo documental, OEM, ausencia-válida-vs-corpus-gap).
  - **Contrato admit/ausente-probado** (misma carga de prueba de ausencia — el dúo señaló que faltaba).
  - **`cross_generate.py`** (GPT-5.5 generador).
- **B3 · Confirmar la rejilla** (§4) + elegir subconjunto del run (~6-8).

### FASE C — EL GRUESO (mañana, lo más autónomo posible; tú presente).
Por celda (~6-8; loop resumable, no Workflow):
- **C1 · Minar fuente**: render del contenido duro. Routing scan/clean **emergente del render** (grep
  pre-filtro; grep-cero + render-con-contenido = scan → regla de scans). NO clasificador per-página (#10).
- **C2 · Co-generan Claude + GPT-5.5** desde el excerpt (mitiga circularidad).
- **C3 · Critica el dúo** (sub-agente fresco + GPT-5.5): verificable / premisa / duplicado /
  ¿solo-sondea-lo-cómodo? → descartar.
- **C4 · Gold source-verified con cross-check de UBICACIÓN + LECTURA:**
  1. **Localización por 2 rutas**: (a) grep término/identificador (`pdf_grep`) + (b) similitud semántica
     per-manual (B2). Ambas devuelven página **física** del PDF (migración 006: `page_number` = índice
     físico; pdf_grep = físico → mismo sistema).
  2. **Convergencia por CONTENIDO** (no por nº de página): la página candidata, **renderizada**,
     contiene el hecho; si las rutas apuntan a páginas cuyo render NO coincide → `needs_human`.
  3. **Render ± 1 vecina** → confirmar que el hecho está en la reclamada y **no** igual en las vecinas
     (caza el off-by-one de hp005/17/18).
  4. **Lectura de VALORES con DOBLE señal** (lección 7-segmentos: el VLM comparte el sesgo OCR/display):
     cada valor CORE numérico/código se confirma con (i) lectura cross-model del render **y** (ii) match
     determinista del valor en el texto extraído de esa página; si la página es scan (sin texto) →
     2ª lectura cross-model independiente, y si discrepan → `needs_human` para ese valor. Prosa
     no-crítica = lectura simple.
  5. Hechos atómicos + conducta por principios (**surfacear conflictos ES-US, NO resolver**) →
     `gold_store.upsert`; `needs_human`/`corpus-gap` lo irreducible.
- **Piloto** (~3-5 primeras, tipos duros): funnel + scorer FIRMADO → checkpoint (¿discrimina? +
  spot-check de ubicación) antes de seguir.
- **Diagnóstico end-to-end** (deliverable): las limpias por `test_bot_vs_gold` → `atomic_scorer`
  (#35 firmado) → veredicto + localización del fallo por hecho (RETRIEVAL/RERANK/SÍNTESIS/CORPUS-GAP),
  sobre el estado ACTUAL de prod (no vs s37).
- **Adversarial sobre el OUTPUT** + informe.
- **Alcance ~6-8** este run; 20 = objetivo a varios runs.

### FASE D — Iterar.
- Crecer a 20 por cobertura de taxonomía.
- **Levers**: SOLO con árbitro firmemente validado; dirigidos por diagnóstico; en rama; reportados,
  no shippeados; medidos contra baseline FRESCO. NO en el run inicial.

## 3. Roster + a implementar
**Agentes**: Claude-orquestador; sub-agentes (generador / crítico / scorer-builder); GPT-5.5
(co-generador + cross-verify visual + crítico). **Reutilizo**: gold_store, author_atomic_facts,
render_pdf_page, cross_verify_image, pdf_grep, audit_retrieval_funnel, test_bot_vs_gold, atomic_scorer,
adversarial_review+briefing, model_catalog, Supabase MCP (SELECT).
**A IMPLEMENTAR**: (1) juez-LLM #35 detrás de flag default-off + test equivalencia [**Fase A**];
(2) mecanismo C4 (localización 2-rutas, convergencia-por-contenido, render±1, doble-lectura de valores)
[B2]; (3) ruta-(b) semántica per-manual [B2]; (4) contrato+check refuse-inference [B2]; (5) contrato
admit/ausente-probado [B2]; (6) `cross_generate.py` [B2]. *(NO per-página; NO Workflow para 6-8.)*

## 4. Rejilla — 19 celdas (Q20 fuera; confirmar en B3). ★ = sugeridas primer run.
| Tier | # | Tipo | Fabricante/dominio | Conducta |
|---|---|---|---|---|
| **A — calidad (mide al bot)** | 1★ | Procedimiento multi-doc | Notifier PEARL | answer/multi-doc |
| | 2 | Procedimiento multi-doc | Notifier PEARL | answer/multi-doc |
| | 3 | Procedimiento multi-doc | Notifier ID3000 | answer/multi-doc |
| | 4 | Procedimiento multi-doc | Morley DXc | answer/multi-doc |
| | 5★ | Especificaciones (tabla) | Gas CS4/S3 (dominio nuevo) | answer |
| | 6 | Especificaciones (tabla) | Gas CS4/S3 | answer |
| | 7★ | Especificación EN | FAAST LT-200 (eje ES/EN) | answer |
| | 8★ | Tabla/matriz dura | Notifier | answer |
| | 9 | Tabla/matriz dura | Detnov | answer |
| | 10 | Proceso/programación | Detnov | answer |
| | 11 | Proceso/programación | Morley | answer |
| **B — gap-diagnóstico (render ANTES de etiquetar)** | 12★ | OCR/scan | scan conocido | answer **o** corpus-gap *(tras render)* |
| | 13 | OCR/scan | scan conocido | answer o corpus-gap *(tras render)* |
| | 14 | Cableado/diagrama | a elegir | render decide; NO pre-etiquetar por diagram_url=NULL |
| | 15 | Cableado/diagrama | a elegir | render decide |
| **C — conductas** | 16★ | Admit (ausente-probado) | a elegir | admit *(contrato B2)* |
| | 17 | Admit (ausente-probado) | a elegir | admit *(contrato B2)* |
| | 18★ | Refuse-inference cross-brand | Notifier↔Detnov | refuse-inference *(contrato B2)* |
| | 19★ | Clarify (familia ambigua) | a elegir | clarify |

*answer-con-conflicto: cubierto por hp012 (n=1, ES-vs-US) = **cobertura MÍNIMA de la clase** → añadir
una 2ª (mercado/idioma) en un run posterior; no ahora.*

## 5. Stop conditions
- ≥3 golds seguidos → `needs_human` → STOP + flag.
- **C4**: rutas divergen en CONTENIDO / valor con doble-señal discrepante → `needs_human`, no fabricar.
- Scorer #35 sin sign-off (B1) / test de equivalencia rojo → no usarlo, fallback mecánico (suelo).
- Cap auto-vigilado / timebox / concurrencia excedido → parar, informe parcial limpio.
- Regla C antes de cada afirmación del informe.

## 6. Gaps declarados (asumidos)
- (a) **Localizador = eslabón más débil** → mitigado con C4 (2-rutas + convergencia-por-contenido +
  render±1 + doble-lectura de valores), NO eliminado.
- (b) **Circularidad MITIGADA, no rota** (Claude ensambla; GPT-5.5 co-genera). El sign-off humano (B1)
  es el único corte fuerte.
- (c) **Sintético ≠ distribución real** (sin usuarios; query_logs descartadas = ecos del propio eval).
- (d) **Tier B mide el CORPUS** → corpus-gap SOLO tras render-verificar.
- (e) **Caps auto-vigilados, no harness-enforced**; el backstop duro es la rama + revisión de la mañana.
- (f) **Lectura VLM** sigue siendo un riesgo en scans/displays incluso con doble-señal → residual a
  spot-check humano en valores críticos cuando la doble-señal no converge.
- (g) **Contratos de C4/refuse/admit** se nailan en B2 supervisado — no en este doc (un plan enruta,
  no sobre-especifica).

## 7. Próximo paso inmediato
ESTA NOCHE = solo **Fase A** (#35 detrás de flag-off + datos crudos), si hay luz verde. Mañana: B1
(sign-off) → B2 (construir contratos) → C (autorar ~6-8 + diagnóstico).

## 8. Traza del review
- **v1 NO SÓLIDO**: scorer build+use+validate misma noche; over-scope 20.
- **v2 NO SÓLIDO**: C4 etiqueta-sin-mecanismo; §0 over-claim de framing; reuse falso de diagnose_corpus.
- **v3 NO SÓLIDO**: AC-220 ya aplicado (framing stale + baseline s37 superseded); C4 convergencia por
  nº-de-página frágil; lectura VLM sin doble-señal; admit sin contrato; #35 sin flag; caps sin enforcement.
  *(Regla C: el "coordenadas incompatibles" del sub-agente era FP parcial — migración 006: ambos físicos
  → fix = converger por contenido.)*
- **v4 (MAESTRO)**: todo lo anterior reconciliado; lo no-especificable en un plan → declarado como
  contrato de B2 supervisado (§6g). Feedback Alberto integrado: noche/mañana split; #20 fuera; per-página
  fuera; legacy fuera (#38 + juez-opaco aparte); push-button = dirección.
