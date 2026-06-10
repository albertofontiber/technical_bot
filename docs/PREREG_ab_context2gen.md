# Pre-registro — A/B del lever context→generator (s48, diferido a Track B-dev)

> Pre-registro escrito ANTES de medir, para que el A/B no sea exploratorio (anti p-hacking;
> protege el embargo del held-out). Canónico: `DECISIONS.md` DEC-022. **Estado: PENDIENTE de
> ejecutar — espera el eval ampliado (Track B) con muestra relevante.**
>
> ✅ **RECONCILIADO s53 (DEC-033):** ya NO se pre-selecciona por `content-pobre` (demotado a causa
> post-hoc, DEC-025/032). El A/B corre sobre golds de DIMENSIÓN DE FALLO (eje de AUTORÍA, RULER §8)
> y se ve POST-HOC dónde ayuda B (los casos donde ayuda suelen RESULTAR content-pobre — predicción
> secundaria, NO población objetivo). La taxonomía de estratos quedó congelada en RULER §8 (DEC-033).

## Hipótesis
Incluir el blurb de contextual-retrieval (`chunk['context']`, B7) en el prompt del generador
—además del `content`— mejora la COMPLETITUD/precisión de la respuesta, SIN aumentar la invención.
**Predicción secundaria (post-hoc, NO criterio de selección):** la mejora se concentrará en casos
donde el `content` del chunk RESULTE pobre/ambiguo y el blurb aporte el marco de sección/documento.
Default actual: el blurb solo vive en el retrieval (embedding/FTS), no en la generación (`generator.py:411`).

## Por qué se difiere (s48)
Smoke sobre hp005/hp013 (content-claro): A≈B, el bot ignora el blurb, 0 fabricación, generador
no-determinista. Señal débil — PERO el smoke usó casos homogéneos de content-claro, que no cubren
los estratos donde el mecanismo podría actuar (refutación del cross-model, dúo s48). Medirlo bien
exige el eval ampliado con diversidad estratificada; con los 22 actuales no hay poder ni cobertura.

## Diseño (a ejecutar en Track B-dev)
- **Brazos:** A = generador actual (`GENERATOR_INCLUDE_CONTEXT=0`); B = con blurb (`=1`, marcado
  "orientativo, no-citable").
- **Set:** SOLO el **DEV** del eval ampliado. El **held-out NO se toca** — ni para decidir, ni para
  tunear el marcado, ni para seleccionar casos. Se usaría UNA sola vez, al final, si el lever pasa en dev.
- **Estratos pre-definidos** (la clave del poder es la diversidad estratificada, NO el N bruto; eje de
  AUTORÍA de RULER §8): multi-doc · síntesis-completitud · vocabulary-mismatch ES/EN · OEM-relabeling ·
  conflicto-revisión · conflicto España-vs-US. `content-pobre`/`fragmento` NO se pre-seleccionan — son
  RESULTADO post-hoc (dónde ayuda B se ve corriendo, DEC-033). **Gap de corpus declarado:** es-en/es-us
  TOPADOS por el corpus es-céntrico (DEC-026e) → lectura per-estrato pobre ahí, a DECLARAR, no a tapar.
  + un estrato de **PASS-actuales como control de no-regresión** (sub-contrato abajo).
- **Sub-contrato del PASS-control (pre-registrado, anti-circularidad — bite del dúo s53):** el set de
  control = golds que PASAN en el brazo A (baseline), seleccionados con el MISMO juez + K-mayoría +
  semillas del A/B y FIJADOS antes de mirar el brazo B (no se re-selecciona tras ver B = sesgo de
  selección del baseline).
- **Freeze-contract:** retrieved-contexts congelados (idénticos para A y B; solo varía la inclusión del
  blurb) · juez GPT-5.5 + K-mayoría (K≥5, el generador es no-determinista) · mismo índice/corpus/
  embeddings · run-manifest persistido.
- **Métricas (2 ejes, DEC-001):** Δ veredictos (PASS/PARCIAL/FALLO) **por estrato** + eje
  no-fabricación (completitud↑ SIN invención↑). Excluir los casos inestables del juez del cómputo de Δ.

## Criterio de activación (decidido ANTES de medir)
- **Shipear** si: Δ veredictos > ruido del juez (K-mayoría) en ≥1 estrato, SIN regresión en
  PASS-control, SIN aumento de invención, en DEV; confirmado una vez en held-out.
- **Cerrar el lever** si: Δ ≈ 0 en todos los estratos (incl. content-pobre/multi-doc/ES-EN) →
  débil-por-diseño confirmado con población diversa (no solo con el smoke homogéneo de s48).
- **Pre-requisito de implementación (si shipea):** el retriever debe devolver `context` en TODAS
  las ramas — hoy solo la rama vector (RPC); keyword/content lo omiten en su SELECT (deuda s48).

## Criterio de confirmación HELD-OUT (pre-registrado s57, ANTES de conocer ningún delta)

> Añadido al poblar el held-out (s57, gate del dúo: el "confirmado una vez en held-out" de
> arriba no definía qué cuenta como confirmar → con corrida ÚNICA y n~11, dejarlo abierto =
> interpretación post-hoc en el único punto sin re-tiro). **Alcance**: aplica al lever de
> generación que el gate s58 señale (este A/B o el 2×2 modelo×blurb del PLAN s59) — el
> criterio es agnóstico al brazo ganador.

- **Cuándo**: UNA sola corrida (`INCLUDE_HELDOUT=1`), solo si el lever PASÓ en dev, bajo el
  freeze-contract completo (mismo corpus+índice+embeddings+juez K-mayoría+seeds+config que el
  A/B dev; run-manifest persistido). Nada del held-out se mira antes; nada se re-corre después.
- **CONFIRMA** si: (1) el Δ GLOBAL held-out (brazo ganador vs baseline, mismos 2 ejes) tiene el
  MISMO SIGNO que el Δ dev, Y (2) sin invención nueva: 0 fabricaciones K-estables atribuibles
  al lever (eje no-fabricación; los casos juez-inestables se excluyen, como en dev).
- **NO-CONFIRMA** (el lever NO shipea aunque dev pase) si: Δ global de signo contrario, O ≥1
  fabricación nueva K-estable en el brazo del lever.
- **Zona gris** (Δ held-out ≈ 0 con dev positivo, sin fabricación): decisión de Alberto con los
  datos en la mesa; si shipea, se declara "confirmación DÉBIL" en DECISIONS (no se re-corre).
- **Estratos**: solo DIRECCIONALES (n≤3 por estrato en held-out) — se REPORTAN, no gatean.
- Los golds held-out de conducta-ausencia (admit/refuse) alimentan el eje (2) — son el
  guardarraíl de invención, no cuentan en el conteo per-estrato.

### Cláusulas C1/C2 — FIRMADAS por Alberto (10 jun 2026, s58b; pre-datos: ningún delta A/B existía)

> Origen: los 2 CRÍTICOS del cross-model del gate s58 (DEC-039f) — el criterio de arriba
> admitía DOS lecturas defendibles en el único punto sin re-tiro. Estas cláusulas lo hacen
> calculable de UNA sola manera; no cambian el criterio.

- **C1 (fórmula del Δ global — aplica a dev Y a held-out):** el Δ global se calcula
  únicamente sobre los golds `answer`/`answer-con-conflicto`, como **cambio medio ordinal
  pre-definido FALLO=0, PARCIAL=1, PASS=2** (brazo ganador vs baseline, mismos golds),
  con los K-inestables excluidos conforme a la regla de exclusión ya pre-registrada.
  Los golds `clarify`/`admit`/`refuse-inference` NO entran en el Δ: gatean exclusivamente
  el eje (2) de no-fabricación (el guardarraíl), donde aportan su señal.
- **C2 (decidibilidad de "0 fabricaciones K-estables"):** la condición se evalúa con el
  **eje no-fabricación del `atomic_scorer`** (mismas llamadas, `response_format` y
  agregación que en dev), corrido sobre las **generaciones PERSISTIDAS de ambos brazos**
  (el baseline s58 las persiste para esto — `evals/s58_generations.json`). El veredicto
  del juez cualitativo global NO basta para declarar presencia ni ausencia de fabricación
  (su FALLO mezcla invención / incompletitud / conducta equivocada).

### Cláusula R — extensión a LEVERS DE RETRIEVAL (s59; **PENDIENTE DE FIRMA de Alberto**)

> **Estado: escrita PRE-DATOS (10 jun 2026, s59 — ningún dato del A/B dev del lever de
> retrieval existía al escribirla; traza: dúo r2, `adversarial_review_log.jsonl`).
> La corrida held-out del lever de retrieval queda BLOQUEADA hasta la firma. El A/B dev
> (re-tirable) puede correr con su criterio pre-registrado (diseño s59 §3,
> `evals/_s59_lever_design_FINAL.md`).**
>
> Origen: el alcance firmado arriba dice "lever de generación", y su freeze-contract exige
> "retrieved-contexts congelados (idénticos para A y B)" — inaplicable por definición cuando
> el lever ES el retrieve (bite del dúo s59 r2: declararlo cubierto "sin cambios" habría
> obligado a improvisar en el único punto sin re-tiro).

- **R-alcance:** el criterio de confirmación held-out + C1 + C2 aplican también a levers de
  RETRIEVAL, con las sustituciones R1–R3 siguientes y NINGUNA otra.
- **R1 (brazos y qué se congela):** brazo BASE = los artefactos congelados del baseline s58
  (`s58_{frozen_contexts,generations,judgments}.json` — ya corridos; no se re-tiran). Brazo
  LEVER = pipeline completo retrieve→rerank→generate al **commit pinned** del lever con su
  config DB declarada en el run-manifest (p.ej. `ef_search` por `pg_proc.proconfig`).
  Se congela TODO lo que no es el lever: corpus (fingerprint de filas s58), embeddings,
  golds, juez + prompts + `response_format` + K + seeds, generador, reranker y scorer.
  Los retrieved-contexts del brazo LEVER se PERSISTEN (hidratados, como s58) — la cláusula
  de "contexts idénticos" se sustituye por "pipeline íntegro pinned + contexts persistidos".
- **R2 (conjunto de medición — una sola lectura):** C1 se calcula sobre los **pares
  completos**: golds `answer`/`answer-con-conflicto` con veredicto modal **K-estable
  (modal ≥3/5) en AMBOS brazos**. Los inestables en cualquiera de los dos brazos se
  excluyen del Δ y se reportan (cuántos, cuáles, en qué brazo). Se reportan Δ medio (C1)
  y Δ_net (suma); con el conjunto fijo ordenan igual.
- **R2-bis (guardarraíl de estabilidad — la exclusión no puede ocultar degradación
  inducida; bite del cross-model s59):** se cuentan las transiciones de estabilidad
  entre brazos sobre answer-golds. En held-out: si las transiciones netas
  estable(BASE)→inestable(LEVER) son ≥2, la corrida cae a **ZONA GRIS forzosa**
  (nunca CONFIRMA automático), aunque el Δ sobre pares completos sea positivo.
  La inestabilidad inducida es señal de ruido del lever, no neutralidad.
- **R3 (C2 operativa con K=5):** unidad = gold con **fabricación K-estable** (≥3/5
  generaciones del gold contienen ≥1 claim atómico fabricado según `atomic_scorer`).
  El lado BASE se computa sobre `s58_generations.json` **ANTES de generar el brazo
  LEVER** (ciego al resultado). "0 fabricaciones nuevas" = ningún gold pasa de
  no-fabricación (base) a fabricación K-estable (lever).
- **R4 (equivalencia del instrumento — declarar el runner nuevo no lo aísla; bite del
  cross-model s59):** el brazo LEVER se produce con el runner parametrizado (run-id);
  la equivalencia con el instrumento del baseline se PRUEBA, no se declara: (a) las
  fases generate/judge/report no cambian de código (el diff del runner es solo
  selección de paths/run-id, revisable en el PR); (b) los SHAs de prompts del juez +
  `response_format` + alias resuelto del modelo se verifican EN RUNTIME contra
  `s58_run_manifest.json` y la corrida ABORTA si difieren; (c) config del generador
  (modelo, temp, max_tokens) idéntica en el manifest del lever.
- Lo NO sustituido rige igual: corrida ÚNICA `INCLUDE_HELDOUT=1` solo si dev pasa;
  mismo-signo + sin-invención-nueva para CONFIRMAR; zona gris = decisión de Alberto;
  estratos solo direccionales.

**Firma Alberto:** ____________________  (pendiente)
