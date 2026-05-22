# Calibración del judge v2 — instrucciones

Calibración humana completa del judge del eval, sobre las 52 preguntas del eval del **2 mayo 2026** (`logs/eval_20260502T152857Z.json`). Output: judge agreement rate vs Alberto + lista priorizada de sesgos del judge a corregir.

## Por qué hacemos esto

El judge actual reporta **51/52 PASS (98%)** pero ningún caso está validado por humano (`verified: false` en todo el YAML). Sin gold standard, no sabemos si el judge tiene 98% de accuracy real o si simplemente comparte blind spots con el generator (ambos son Sonnet 4.6).

Audit cuantitativo del último eval (mapa de calor abajo):

- **39 de 52 casos (75%)** tienen discrepancia `keyword=FAIL ∧ judge=PASS` (flag `LENIENT?`)
- **1 caso (mc006)** tiene bug confirmado del judge: `behavior_match=False` cuando observed==expected
- **6 casos** son recalibraciones del YAML (originalmente `answer`, ahora `admit_no_info`) — vale la pena verificar si la recalibración fue legítima o si debíamos haber arreglado el bot

Calibrar las 52 nos da:

1. **Gold standard permanente** — esta validación se mantiene y se reutiliza para siempre
2. **Holdout split limpio** — separar ~10 calibration / ~42 eval después
3. **Lista priorizada de bugs del judge** para corregir el prompt

## Cómo trabajar los 5 archivos

Cada archivo cubre una categoría:

| # | Archivo | Casos | Tiempo estimado |
|---|---|---|---|
| 01 | `01_happy_path.md` | 20 | 60-75 min |
| 02 | `02_ambiguous_model.md` | 8 | 20-30 min |
| 03 | `03_missing_context.md` | 8 | 20-30 min |
| 04 | `04_not_in_db.md` | 8 | 20-30 min |
| 05 | `05_cross_manual.md` | 8 | 20-30 min |
| | **Total** | **52** | **~2h 30 min** |

Sugerencia de bloques (no obligatoria):
- Sesión 1: `01_happy_path.md` solo (el más grande y el más informativo)
- Sesión 2: `02 + 03` (ambos son "el bot debe clarificar")
- Sesión 3: `04 + 05` (ambos son "el bot debe admitir gap")

## Cómo evaluar un caso

Para cada caso lees: **query → conducta esperada → fragmentos F (los que vio el bot) → respuesta del bot → veredicto del judge + rationale**. Y rellenas las casillas al final:

```
### Tu calibración
- [ ] **De acuerdo** con el veredicto del judge
- [ ] **En desacuerdo** — yo diría: PASS / FAIL
- **Dimensión equivocada(s) del judge** (si aplica): ___
- **Nota / por qué:** ___
```

**Reglas de evaluación:**

1. **Faithful** — para cada afirmación factual del bot (número, sección, código, modelo, norma), verifica que ESTÁ en algún fragmento F. Paráfrasis y sinónimos cuentan. Si no está en ningún F, es alucinación. *No necesitas saber PCI — es lectura comparativa.*
2. **Behavior** — verifica si la conducta observada (responder / clarificar / admitir) coincide con la esperada del YAML. El header de cada caso te lo dice.
3. **Helpful** — el bot admitir honestamente "no tengo info" cuenta como helpful=True si los fragmentos no contienen la info. Helpful=False solo si el bot ignoró info que SÍ tenía visible.

**No necesitas verificar la respuesta contra el manual completo** — solo contra los fragmentos F que ves en el caso. El judge tiene visibilidad adicional (chunks V) pero su rationale te dice cuándo los usó. Si en algún caso el rationale menciona "el dato vive en V3" y necesitas ver V3, márcalo en tus notas y yo te lo traigo después.

## Flags automáticos que verás

Casi 3/4 de los casos tienen un flag de Claude marcando un patrón sospechoso. **Son pistas, no conclusiones**. Tu juicio independiente es lo que vale.

| Flag | Significado | Qué chequear |
|---|---|---|
| ⚠️ `keyword=FAIL ∧ judge=PASS` (LENIENT?) | El bot no acertó las keywords del YAML pero el judge le dio PASS | (a) ¿Usó un sinónimo legítimo que el YAML no anticipó? → judge tiene razón, fix YAML. (b) ¿Inventó con elegancia y el judge no lo detectó? → judge lenient, fix prompt del judge. |
| ⚠️ `keyword=PASS ∧ judge=FAIL` (STRICT?) | El bot acertó keywords pero el judge le dio FAIL | Verifica si el judge está siendo demasiado estricto (paráfrasis, citation marker confuso, tabla densa) |
| 🐛 `BUG candidato` | `observed_behavior == expected_behavior` pero el judge dice `behavior_match=False` | Es bug del judge confirmado. Lo fix después de la calibración. |
| 🔗 `miscitation flag activo` | El bot dijo algo correcto pero citó el F equivocado | Bug menor — no bloquea PASS — pero anota si te encuentras patrón. |
| `(notes YAML: Recalibrado...)` | La pregunta cambió de `expected_behavior` durante el desarrollo | Pregúntate: ¿la recalibración fue legítima o estábamos enmascarando un fallo del bot? |

## Mapa de calor por categoría

```
happy_path        20 cases · 16 flaggeados (15× LENIENT? + 3× RECAL)
ambiguous_model    8 cases ·  7 flaggeados (todos LENIENT?)
missing_context    8 cases ·  7 flaggeados (6× LENIENT? + 1× BUG mc006)
not_in_db          8 cases ·  2 flaggeados (los más limpios — buen sanity check)
cross_manual       8 cases ·  7 flaggeados (5× LENIENT?+RECAL + 1× RECAL + 1× LENIENT?)
```

`not_in_db` es la categoría más limpia — buena para confirmar que el judge sí acierta cuando todo va bien. Empezar por ella puede ayudarte a calibrar tu propio criterio antes de meterte en `happy_path`.

`cross_manual` está fuertemente sesgada por recalibraciones (7 de 8 cambiaron de `answer` a `admit_no_info` en sesión 22). Vale la pena revisar si esas recalibraciones fueron correctas — si no lo eran, el 96% baseline está inflado.

## Qué pasa después de que rellenes los 5 archivos

1. Yo proceso todos los `[x]` marcados y calculo:
   - **Judge agreement rate** vs Alberto (por categoría y global)
   - **Lista priorizada de sesgos del judge** (lenient en X tipos / strict en Y tipos)
   - **Lista de fixes concretos**: prompt del judge (rules adicionales) + bug `behavior_match` de mc006 + recalibraciones YAML que detectes mal
2. Implemento los fixes del judge y del runner.
3. Re-corro el eval con el judge fixeado y comparo: la nueva métrica primaria es **judge agreement con Alberto**, no el % PASS.
4. Hacemos el holdout split: ~10 casos `calibration_set.yaml` (para tunear judge en el futuro) vs ~42 casos `eval_set.yaml` (para medir bot — nunca se toca su `expected_behavior`).

## Si tienes dudas mientras rellenas

- Si un caso te confunde, **márcalo** ("dudoso") y sigue. Lo discutimos después.
- Si necesitas ver chunks V (los que el judge tiene pero el bot no), márcalo y te los traigo.
- Si encuentras un patrón sistemático (ej: el judge falla siempre que hay tabla), anótalo al inicio del archivo — es información valiosa.
