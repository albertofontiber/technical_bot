# s49 — Diseño del esquema del ruler para Track B (backbone) — PARA REVISIÓN ADVERSARIAL

> Artefacto a atacar ANTES de cablear (Protocolo 3; esquema-del-ruler = zona de dolor →
> sub-agente Claude + cross-model GPT-5.5). Decisión de impacto MEDIO-en-zona-de-dolor.
> Canónico del rumbo: `PLAN_RAG_2026` bloque s48 + `DECISIONS` DEC-021 §C/§F + DEC-022e.

## 0. Contexto (qué se decidió, qué desbloquea)
- s48 (DEC-022) cerró el diagnóstico de retrieval y DIFIRIÓ dos A/B (context→generator
  pre-registrado en `docs/PREREG_ab_context2gen.md`; ablación de contextual-retrieval) a que
  exista un **eval ampliado con DIVERSIDAD estratificada** — el smoke s48 falló por muestra
  homogénea (content-claro), no por N.
- s49 = Track B. Alberto eligió **"backbone + decidir luego"**: esta sesión SOLO la espina
  dorsal barata e infraestructural, común a ambos caminos posteriores (camino-corto-A/B vs
  base-completa DEC-021 §C). El bulk de autoría (22→~60-100) se decide DESPUÉS, con el backbone
  montado y validado.
- El ruler hoy = **22 golds, todos `verificado`** (`evals/gold_answers_v1.yaml`): 20 answer /
  1 clarify (hp004) / 1 answer-con-conflicto (hp012). **Conductas `admit` y `refuse-inference`
  = 0 golds.** No existe campo `split` ni `estrato`.

## 1. Alcance del backbone (lo que SÍ entra esta sesión)
1. **Esquema**: añadir `split` + `estrato` a `scripts/gold_store.py` (KNOWN_FIELDS + FIELD_ORDER
   + validación tiered) + helpers `dev()`/`heldout()` simétricos a `verified()`.
2. **Tests**: crear `tests/test_gold_store.py` (no existe test del esquema hoy; `test_validator.py`
   es del validador anti-alucinación, no del ruler).
3. **Retrofit** de los 22 con `estrato` (derivado de su contenido real) + `split`.
4. **Embargo en el harness**: `scripts/test_bot_vs_gold.py:126` lee el YAML directo e itera TODOS
   los golds → añadir filtro que EXCLUYE `held-out` por defecto + flag `--include-heldout`.
5. **Rebanada vertical**: autorar 2-3 golds NUEVOS de estratos vacíos (content-pobre / oem-relabel)
   end-to-end por el pipeline C4 (`locate_fact.py` + `cross_generate.py` + `gold_store.upsert`) →
   valida que esquema+pipeline aguantan antes del bulk (lo exige `gold_store.py:8` "esquema v2
   DRAFT hasta que la rebanada lo valide" + RULER_DESIGN §4).

## 2. Decisiones de diseño (con alternativas)
**D-A. `split` y `estrato` van TOP-LEVEL** (no dentro de `_provenance`).
- Por qué: `_provenance` = autoría/verificación (fuente, localización, fecha); `_usage` = coste
  (`{in,out}` tokens). `split`/`estrato` son metadata de DISEÑO del eval (partición + cobertura),
  consultadas por el harness y por análisis per-estrato. DEC-021 §C dice "marcador `split`".
- Alt descartada: anidar en `_eval:{}` — más indirección sin beneficio; el harness tendría que
  bajar un nivel. Top-level es simétrico a `conducta_esperada` (también eje de clasificación).

**D-B. `split` ∈ {dev, held-out}; ausente = dev; embargo en el harness.**
- Los 22 actuales YA fueron inspeccionados/tuneados (s33-s48) → **TODOS son `dev` por
  construcción** (no se puede meter retroactivamente en held-out un gold ya visto sin violar el
  embargo). El **held-out solo se puebla con autoría NUEVA embargada**.
- Embargo = enforcement PARCIAL: el harness excluye `held-out` salvo `--include-heldout` (la
  corrida final única). El resto (no inspeccionar respuestas del bot sobre held-out para tunear)
  es disciplina, no enforce-able (declarado, como los caps auto-vigilados de CATALOG_PLAN §1).
- Matiz de embargo: AUTORAR un gold held-out (verificar su FUENTE) es lícito; lo prohibido es
  correr el bot sobre él y ajustar lever/marcado según el resultado, o seleccionarlo por dificultad
  observada. El embargo es sobre el USO posterior, no sobre la autoría.

**D-C. `estrato` = LISTA de tags de vocabulario CONTROLADO (multi-tag, no enum único).**
- Por qué multi-tag: un gold puede ser multi-doc Y es-en Y oem a la vez. Un enum único forzaría
  elegir y perdería cobertura cruzada.
- Por qué controlado (set cerrado, validado): evita el sprawl de tags libres (un `estrato:
  "multidoc"` vs `"multi-doc"` rompería el conteo per-estrato).
- Vocabulario propuesto (reconcilia PREREG + rejilla CATALOG_PLAN §4 + RULER_DESIGN §2):
  - *retrieval/generación*: `content-pobre`, `multi-doc`, `tabla-matriz`, `scan-ocr`, `diagrama`
  - *idioma/mercado*: `es-en`, `conflicto-es-us`
  - *identidad-producto (escala/F3)*: `oem-relabel`, `familia-ambigua`
  - *control*: `control-pass` (PASS estable = control de no-regresión del A/B)
- **NO duplicar la conducta en estrato**: admit/refuse-inference/clarify son `conducta_esperada`
  (eje propio); la cobertura de conductas se mide sobre ese campo. `estrato` es ortogonal.
- Lista vacía permitida (answer-genérico sin dificultad marcada).
- Alt descartada: dict de ejes (`{contenido:[], idioma:, dificultad:}`) — más estructura de la
  necesaria para filtrar/contar; plano basta. El dúo: ¿de acuerdo o el dict aporta?

**D-D. Validación tiered (sigue el patrón de `gold_store.py:101`).**
- `split` presente e inválido → ERROR. `estrato` con tag fuera del vocabulario → ERROR. NO exigir
  que estén presentes (no romper los 22 hasta el retrofit, que va en el MISMO PR).
- Añadir ambos a KNOWN_FIELDS + FIELD_ORDER (si no, se marcan "cruft a limpiar" en `:97`).

## 3. Lo que se DIFIERE (auto-pushback — recorte de scope vs mi propuesta inicial)
Mi propuesta inicial del backbone incluía run-manifest + §A wiring. Pregunta-cero (¿cambia una
decisión AHORA?): **NO** en este backbone, porque NINGÚN A/B corre esta sesión. Construirlos ahora
= aparato no-usado (lección s27: pre-registro de un SWAP ya decidido).
- **run-manifest completo (freeze-contract §F) → DIFERIDO al primer A/B** (es lo que consume el
  manifiesto). En el backbone solo dejo el gancho: el stamp de config de s46 (`{meta,results}`)
  ya existe; cuando corra el A/B se extiende para incluir el `split` corrido. NO construir el
  manifiesto entero especulativamente.
- **§A wiring (`verify_citations.py` → suite + agregación + umbral) → CANDIDATO a diferir.** Es
  DoD-de-medición (DEC-021 §A); se aplica al medir un lever, y no hay lever en el backbone. PERO
  es independiente del tamaño del eval (funciona con 22) y la rebanada vertical podría usarlo para
  validar el DoD sobre los golds nuevos. **Pregunta abierta al dúo:** ¿incluirlo (barato, valida el
  DoD en la rebanada) o diferirlo (anti over-engineering, no hay lever)?

## 4. Gaps / riesgos declarados de entrada
- (a) **Sintético ≠ distribución real** (sin usuarios; query_logs = ecos del propio eval —
  CATALOG_PLAN gap (c)). El held-out mitiga overfit-al-instrumento, NO la representatividad.
- (b) **Señal gruesa**: held-out ~20-30 da smoke/generalización, no per-slice fina (asumido
  DEC-021 §C). El backbone NO promete N todavía (eso es el bulk, decisión posterior).
- (c) **El localizador es el eslabón más débil** (RULER_DESIGN gap (a)); a escala 22→100 el riesgo
  de golds mal-localizados (los FP de s43 hp002/hp006) se multiplica. La rebanada vertical + el
  dúo C3 + spot-check humano son la mitigación; NO se elimina.
- (d) **Embargo = disciplina + enforcement parcial** (solo el filtro del harness es duro).
- (e) **Retrofit de estratos sobre los 22 = juicio del autor** (¿es hp001 "multi-doc"? ¿"content-
  pobre"?) → riesgo de etiquetado inconsistente. Mitigación: criterios escritos por tag + el dúo
  revisa una muestra del retrofit.

## 5. Por qué BP + estructural + escalable
- BP eval-driven: split dev/held-out con embargo es estándar para generalización; estratos para
  poder dirigido por slice (PREREG).
- Estructural: toca la PUERTA única (`gold_store`) + el esquema, no parchea golds a mano (D10).
- Escalable: vocabulario controlado de estratos + helpers = la base sobre la que el bulk autora
  60-100 sin re-decidir el esquema. No toca índice → paralelo-seguro (DEC-021 §F).

## 6. Dónde quiero bite (no rubber-stamp)
1. ¿`estrato` plano-multi-tag es correcto, o falta un eje (p.ej. dominio gas/llama/aspiración)
   que el A/B/F3 necesitará y que duele añadir después?
2. ¿El vocabulario de estratos cubre los 5 estratos del PREREG sin huecos ni solapes ambiguos?
   (¿`content-pobre` es objetivable o es un juicio circular "donde el blurb ayudaría"?)
3. ¿`split` top-level + ausente=dev + embargo-en-harness es la forma correcta, o hay un fallo
   de embargo que se me escapa (p.ej. que algún script lea el YAML directo y cuente held-out)?
4. ¿Diferir run-manifest y §A wiring es pregunta-cero correcta, o estoy recortando un cimiento
   que luego duele (el A/B necesita el freeze-contract y lo voy a improvisar)?
5. ¿La rebanada vertical de 2-3 golds NUEVOS valida de verdad el esquema+pipeline, o es teatro
   (RULER_DESIGN §2 avisa: con `page` pre-fijada NO se testea el caso duro del localizador)?

---

## 7. Resoluciones tras el dúo (v2 — ANTES de cablear)
Dúo s49 = cross-model GPT-5.5 **6/6 confirmados** + sub-agente Claude **5/5**, **0 FP**, severidad
máx = crítico. Veredicto: **NO-SÓLIDA** (convergente en el crítico). Log: `adversarial_review_log.jsonl`.
Todos los bites adoptados (ninguno rechazado). Verificado regla C donde es código.

1. **[CRÍTICO — embargo en la PUERTA, no en el harness]** (ambos; verificado regla C). El embargo
   solo en `test_bot_vs_gold.py` deja held-out EXPUESTO en `gold_store.verified()`, que usan los
   **4 consumidores del juez del A/B**: `atomic_scorer.py:408`, `judge_kruns.py:82`,
   `judge_disagreement.py:99`, `characterize_factual_variance.py:83`. + la autoría entra
   `estado=verificado` (`author_atomic_facts.py:14`) → held-out nuevo lo recoge `verified()`. + 4
   lectores-directos del YAML (`audit_retrieval_funnel:62`, `retrieval_eval:46`, `test_bot_vs_gold:51`,
   `validate_s29_burial:47`). **FIX:** `verified(include_heldout=False)` excluye held-out por defecto
   → cubre los 4 consumidores del juez SIN tocarlos (hoy no-op: 0 held-out); la corrida final pasa
   `True`. + helpers `dev()`/`heldout()`. + filtro split en `test_bot_vs_gold`. Lectores-directos de
   DIAGNÓSTICO (audit_funnel/retrieval_eval/validate_s29_burial) → declarar gap + `TECH_DEBT` migrar
   a la puerta (no son el camino que DECIDE el lever; over-scope migrarlos ahora).
2. **[FRAMING crítico — §A wiring]** (sub-agente). "Abierto al dúo" = subcontratar el corte que mi
   pregunta-cero ya contesta. **DECIDIDO: DIFERIR §A wiring** (mismo argumento que run-manifest: es
   DoD-de-medición, no hay lever en el backbone). No queda "abierto".
3. **[content-pobre circular]** (ambos). No "donde el blurb ayudaría" (construye el resultado dentro
   del estrato). **FIX:** definición operacional OFFLINE, medible sin correr el generador →
   *"el valor del hecho core NO está en el body del `content` del chunk recuperado (vive en
   `section_title`, tabla-imagen, o solo en el `context`-blurb)"*. Escrita en criterios-por-tag.
4. **[vocab 1:1 con PREREG]** (cross-model). No diluir: mantener `fragmento-truncado` separado de
   `content-pobre`; `es-en` = vocabulary-mismatch con criterio explícito (dato en EN / término
   difiere ES↔EN). Vocabulario v2 abajo.
5. **[split obligatorio post-retrofit]** (cross-model). `ausente=dev` permanente = exposición
   silenciosa. **FIX:** el MISMO PR retrofita los 22 + endurece: `split` faltante en `verificado` →
   ERROR (legacy no-verificado tolerado).
6. **[control-pass FUERA de estrato]** (cross-model). Es estado histórico (circularidad temporal),
   no propiedad de contenido. **FIX:** el control de no-regresión se selecciona en tiempo de A/B
   (los PASS del baseline congelado), NO se hornea como tag. Sale del vocabulario.
7. **[rebanada vertical honesta]** (ambos). Valida forma-de-esquema + pipeline `upsert`, NO el
   localizador (el riesgo dominante al escalar). **FIX:** la rebanada incluye **≥1 caso de
   localización dura** (multi-doc o scan real) con cross-model + spot-check; se declara qué valida
   y qué no. + 1 gold marcado `held-out` para probar el embargo end-to-end.
8. **[run-manifest diferido → declarar]** (cross-model). Hasta que exista manifest/log de corridas,
   embargo = filtro-de-puerta (DURO) + disciplina (no inspeccionar). Declarado como gap.
9. **[no añadir eje-dominio]** (sub-agente). Confirmado NO añadir gas/llama (over-build; mi sospecha
   #1 era infundada en esa dirección). El hueco real (refuse-inference sin estrato análogo) es eje
   `conducta_esperada`, no del backbone.

### Vocabulario `estrato` v2 (controlado, 1:1 con PREREG)
`content-pobre` · `fragmento-truncado` · `multi-doc` · `tabla-matriz` · `scan-ocr` · `diagrama` ·
`es-en` · `conflicto-es-us` · `oem-relabel` · `familia-ambigua`. **(SIN `control-pass`.)**
