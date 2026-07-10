# s104 — R2 corpus-wide (enunciados): diseño de ejecución — PARA REVIEW ADVERSARIAL

**Estado: PROPUESTA, no ejecutada. GO explícito de Alberto (10-jul)** con dos mandatos: (1)
minuciosidad para NO gastar dos veces sobre el corpus actual; (2) abierto a ejecutar con modelo
más barato SI no pierde calidad. Impacto ALTO en zona de dolor (corpus/índice) → dúo obligatorio.

## Base medida (Protocolo 4 — no se re-litiga)

- **Mecanismo GO** (DEC-085/086, bake-off s93 + piloto s94): reescribir data-items (tablas/specs)
  como ENUNCIADOS = el único mecanismo que paga en el bucket vocabulario (famtie 12→6; R1
  plantilla 0/4 DESCARTADO; R3 resumen complemento).
- **Arquitectura GO y EN PROD** (DEC-089/090): tabla separada `chunks_v2_enunciados` + HNSW
  propio + colapso Dense-X al padre (fail-closed: sin padre recuperable, el enunciado no se
  sirve). `ENUNCIADOS_MULTIVECTOR=on` en Railway desde s96, verificado en query_logs.
- **Anti-lección DEC-088 (s94c)**: surrogates en el índice COMPARTIDO = dilución = NO-GO. La
  tabla separada lo resuelve POR CONSTRUCCIÓN — pero ver «riesgo de escala» abajo.
- **Activos ya pagados y VERIFICADOS hoy**: T1 (14 docs densos, 21.995 enunciados Sonnet-p1,
  QA-passed) **ya cargado en prod** (count exacto 21.995 en la tabla A3; muestra parent_ids
  23/23 vivos). El dump `evals/t1_surrogates_dump.jsonl` queda como respaldo.
- **Maquinaria ya construida** (`scripts/enunciados_pass.py` + `enunciados_qa.py`): tramos con
  idempotencia (DELETE por `ingest_batch` → insert), rollback selectivo por tranche, prompt v1
  CONGELADO (el del piloto medido), QA **DETERMINISTA** por enunciado (fidelidad: todo token
  numérico/código debe existir en la región fuente + anti-mispairing a NIVEL DE FILA, calibrado:
  caza 2/2 alucinaciones del piloto), cobertura por página, muestreo estratificado, cascade por
  `extraction_sha256` (re-ingesta futura de un manual arrastra sus enunciados), `--model`
  override declarado (precedente side-by-side p2).

## Alcance y coste (contado HOY del store local, no estimado de memoria)

Store `agent_anthropic-sonnet-45`: 1.069 docs · **997 con data-items** · **46.938 data-items**
(predicado del pase: `rows` o ≥3 tokens-valor; 16.170 con tabla) · ~29M chars input (cap 8K/item).

| Ruta | Generación restante (~983 docs) | Total con gates |
|---|---|---|
| Sonnet 4.6 (la del piloto) | ~$350 | ~$400 |
| **Haiku 4.5 (propuesta)** | **~$115** | **~$165** |

(+ embeddings Voyage ~$2 para ~150-250K enunciados nuevos; QA $0 — determinista.)
Proyección de volumen: T1 rindió ~5,6 generados/item, ~78% QA-pass → el corpus completo puede
acabar en **~150-250K filas** en la tabla A3 (vs 25K chunks reales — la separación de índices
existe exactamente para esto).

## Por qué Haiku NO pierde calidad (y cómo se VERIFICA, no se asume)

1. **La calidad de fidelidad no depende del generador**: el QA determinista rechaza cualquier
   enunciado cuyos tokens-valor no existan en la fuente con su discriminador en la misma fila.
   Un generador flojo no puede colar alucinaciones; solo puede RENDIR menos (más qa_fail, menos
   cobertura) — y eso es medible por doc, barato y sin juez.
2. **PILOTO DE EQUIVALENCIA pre-declarado (gate G0, ~$5)**: side-by-side Haiku-vs-Sonnet sobre
   ~10 docs estratificados (marca × con/sin tabla × ES/EN), `--dry` (sin insertar). Métricas
   judge-free: QA-pass-rate, cobertura/página, enunciados/item, longitud media. **Banda de
   equivalencia declarada ANTES de correr: Haiku ≥ 90% del QA-pass-rate de Sonnet Y cobertura
   ≥ 95% de la de Sonnet, por estrato.** Si pasa → Haiku corpus-wide. Si falla en tablas pero no
   en prosa (o viceversa) → ruta MIXTA por tipo de item (declarada, no tuning). Si falla en
   general → Sonnet (~$350, dentro del GO de Alberto pero se le reporta antes).
3. Vintage visible: `ingest_batch = enunciados-v1:<tranche>:h1` (h=haiku) — conviven con los
   T1 Sonnet-p1 sin ambigüedad; rollback selectivo por vintage.

## No-gastar-dos-veces (mandato 1)

- **Dump-before-insert INSTITUCIONALIZADO**: cada tramo escribe
  `evals/enunciados_dump_<tranche>.jsonl.gz` ANTES de insertar (la lección T1: el dump salvó
  $30+ de re-generación). Sin embeddings (recomputables por ~$2; el texto es el activo caro).
- **Ledger de progreso** `evals/enunciados_ledger.json`: doc → {sha, tranche, items, insertables,
  coste_estimado, ts}. Resume tras cualquier interrupción SIN re-generar (skip por sha presente).
- **Idempotencia ya construida**: re-correr un tramo = DELETE por batch + insert (no duplica).
- **Incrementalidad futura**: docs nuevos del corpus → solo ellos (skip por sha en ledger);
  manual re-ingestado → su sha cambia → cascade borra los viejos → re-generar SOLO ese doc.
- T1 NO se re-genera ni se toca (ya en prod, vintage Sonnet-p1 declarado).

## Ejecución por tramos (con gates que pueden PARAR el gasto)

- **G0 — piloto de equivalencia** (~10 docs, ~$5, dry): banda arriba. PARA si Haiku falla y
  Sonnet-total no se autoriza de nuevo.
- **T2 — tramo de señal** (~60-80 docs, ~$8-10 Haiku): prioriza los docs de las FAMILIAS del
  testbed s94 + los 12 retrieval-miss v3 (medible pronto — tramo de MEDICIÓN declarado, el
  anti-overfit lo cubren los gates amplios de abajo). **Gate T2 (judge-free)**: (a) los flips
  del testbed s94 reproducen con la mecánica de prod; (b) famtie-probe: los retrieval-miss
  anchorables mejoran su in_pool; (c) **control anti-dilución a escala**: pools de 6-8 golds OK
  sin relación (patrón old-vs-new de s103: anclas-OK en pool/servido dentro del null) — la
  lección hyq-corpus-wide (el gate v1 0/2: la escala EXIGIÓ un fix) aplicada aquí ANTES de
  seguir gastando.
- **T3..Tn — resto por densidad de items** (lotes ~150 docs, checkpoint/ledger tras cada lote,
  coste estampado). Spot-check muestral estratificado por tramo (el sampler ya existe).
- **Gate final (judged, tras carga completa)**: bvg K=3 no-regresión (patrón s103, ~$25) +
  assessment smoke→full → fila v4 del scoreboard.

## Riesgos declarados

- **R-escala (el mayor)**: T1=22K filas ya sirve en prod; el corpus completo ≈ 150-250K filas
  en la tabla A3. La separación de índices elimina la dilución del índice REAL (DEC-088→089),
  pero la competencia INTERNA del canal enunciados a 10x (su RPC match + keep-max por padre +
  fusión sort-mixto comensurable) NO está medida a esa escala — precedente directo: el canal
  hyq necesitó family-parity al pasar de piloto a corpus (gate v1 0/2). Por eso el gate T2(c)
  corre ANTES de gastar el grueso, y el gate final re-verifica. Mitigación conocida si aparece:
  el patrón family/parity de hyq (012) es portable al RPC de enunciados.
- **R-yield Haiku**: cubierto por G0 con banda pre-declarada y ruta mixta como fallback.
- **R-store≠corpus**: el pase salta docs sin chunks en DB (`sin chunks en DB` declarado) y el
  QA de cobertura lo reporta por doc; docs del corpus SIN extracción en el store (1.170 vs
  1.069) quedan FUERA de R2 v1 — declarado, no silencioso (lista al ledger).
- **R-formatos del store**: ~1 doc ilegible detectado en el conteo; el pase ya lo trata
  (skip declarado). El conteo de items usa el MISMO predicado del pase (verificado hoy).
- **Presupuesto**: tope de ejecución ~$180 todo-incluido por la ruta Haiku; si G0 fuerza
  Sonnet (~$400) → STOP y reporte a Alberto ANTES de gastar (su GO citó $160-270).

## Piezas a tocar (mínimas — la maquinaria existe)

- `scripts/enunciados_pass.py`: añadir dump-before-insert + ledger + lotes con checkpoint
  (cambios de ORQUESTACIÓN, el núcleo generación/QA/insert queda intacto).
- `scripts/s104_r2_equiv_pilot.py` (G0): side-by-side sobre muestra estratificada, banda
  pre-declarada, artefacto comparativo.
- Gates T2: reutilizan instrumentos existentes (famtie-probe patrón s103, testbed s94_f2/f3).

---

## v2 — CONSOLIDACIÓN post-dúo (cross-model 5/5 + sub-agente 13; 0 FP; 3 bugs de código verificados)

**Veredicto dúo: EJECUTAR-CON-CAMBIOS (×2 lados).** Cambios adoptados ANTES de G0:

### Pipeline corregido (X1 CRÍTICO)
`enunciados_pass.py` inserta en `chunks_v2` (el índice COMPARTIDO del NO-GO DEC-088; :76/:222/:251).
**El pase corpus-wide JAMÁS inserta**: modo `--to-dump` (generación+QA → `evals/enunciados_dump_<tranche>.jsonl`)
y la carga la hace SOLO el loader A3 generalizado (patrón `s95_pilot_a_load.py`: dump→embed
Voyage receta-D8→insert `chunks_v2_enunciados` con bisección). Dos mitades, un solo camino de
escritura, el de la arquitectura validada.

### Claims degradadas con precisión (X2/F1)
- El QA determinista garantiza **fidelidad de VALORES** (token-nivel + anti-mispairing fila).
  **NO garantiza ATRIBUCIÓN** (excluye palabras-con-dígitos de los discriminadores → los nombres
  de modelo no participan; pm del padre en whitelist; pm corpus conocido-mal a nivel variante) ni
  caza enunciados sin tokens materiales (auto-pass). Mitigaciones: (a) guard en el pase — pm
  falsy o "unknown" NO se inyecta como {producto} (frase sin atribución > atribución falsa);
  (b) **panel semántico muestral en G0** (~40 enunciados/brazo estratificados, dimensiones:
  atribución correcta + utilidad + equivalencia Haiku↔Sonnet — los leo yo, $0);
  (c) ledger cuenta docs-con-pm-unknown (la clase queda visible, no silenciosa).
- **Cascade** = FK `parent_id → chunks_v2(id) ON DELETE CASCADE` (011:25): la re-ingesta de un
  manual SÍ arrastra sus enunciados (vía borrado de sus chunks), pero la incrementalidad por
  sha = tooling explícito del ledger, no contrato DB (X4).
- **Family-parity NO es mitigación conocida** para el canal enunciados (filtros distintos:
  `filter_product` exacto vs patrón-texto) — si T2(c)/gate-final exhiben el modo de fallo de
  escala, su fix es DISEÑO NUEVO con su propio gate (X5).

### Fixes de código pre-G0 (verificados por el dúo)
1. `_temp_kw` (F3): «claude-haiku-4-5» contiene "-5" → Haiku correría SIN temperature=0
   (confound del G0 + rompe receta pineada). Predicado corregido a familia-5 real.
2. Vintage parametrizado (F4): `enunciados-v1:<tranche>:<vintage>` (p1=Sonnet, h1=Haiku) —
   rollback selectivo por vintage REAL, no prometido.
3. `sha_of` (F6): mapa doc→sha EXACTO con assert de unicidad (el substring first-match a 983
   docs = items de OTRO manual con fidelidad-QA en verde — la clase más venenosa).
4. Guard {producto} unknown (F1).
5. Tope de gasto DURO (F10): el loop del pase corta al superar el presupuesto acumulado del
   ledger (`--budget-usd`, default 180).
6. Clase CHAFF contada (F8): historial-de-revisiones/nº-documento (evidencia en el propio T1)
   pasa QA y engorda el índice; se cuenta por doc en el ledger y SE EXCLUYE del numerador de
   las métricas G0 (un Haiku verboso no puede ganar el G0 con chaff). Filtro duro = decisión
   post-G0 con el conteo en la mano (no tuning a ciegas).

### G0 re-especificado (X3/F9/F13)
- Muestra ~16-20 docs estratificados (marca × tabla/prosa × ES/EN), bandas AGREGADAS (los
  estratos n≈1-2 son ruido): QA-pass-rate Haiku ≥ 90% del de Sonnet · cobertura/página ≥ 95% ·
  **enunciados-útiles/item (sin chaff) ≥ 85%** · hechos-por-tabla (tokens-valor distintos
  cubiertos) ≥ 90% + panel semántico (b). Dry — sin insertar nada.
- **Pre-check T2 (F13)**: verificar ANTES que los docs-ancla de los 12 retrieval-miss v3 están
  en el store con data-items (101 docs del corpus sin store + 72 sin items) — si falta alguno,
  T2(b) se declara ininterpretable para ese fact (no silencioso).
- Proyección al techo REAL (F13): 5,83 insertables/item · QA-pass 87,4% (manifest T1) →
  **~260-270K filas** — el plan de escala usa ese número, no 150-250K.

### Escala y operación (F5/F7/F11/F12/F2)
- `ef_search=120` vs `match_count=200` del RPC de enunciados: el fetch YA trunca a ~120 hoy.
  Decisión explícita en T2: medir unique-parents post-colapso por tranche (telemetría en el
  probe anti-dilución que corre **tras CADA tranche**, no solo T2) y decidir ef/match con dato.
- Ledger reconcilia contra DB (count por doc) antes de skip (F7 — el skip ciego es más débil
  que el --resume actual); pre-seed con los 14 shas de T1 (F11 — un T1-doc re-procesado en
  otro batch duplicaría filas servidas).
- VACUUM de `chunks_v2_enunciados` tras rollbacks/re-runs y SIEMPRE antes del gate final
  (fantasmas HNSW medidos, DEC-088).
- **T3..Tn re-declarado como APUESTA ANTICIPATORIA (F2)**: el valor-para-queries-reales del
  tail no está medido (caveat DEC-089(3) vigente); el GO de Alberto lo cubre, y hay STOP
  post-T2 declarado: si T2(b) sale débil (<2 de los retrieval-miss anchorables mejoran su
  in_pool), se PARA y se reporta antes de gastar el tail (~$100).

---

## G0 — VEREDICTO (10-jul, artefacto `evals/s104_g0_verdict.json`)

**Bandas: 3/4 PASAN** (QA-pass Haiku 0.879 > Sonnet 0.861 · útiles/item 0.98 · hechos-por-tabla
0.94) · **cobertura 0.925 < 0.95 NO-PASA** → **ENMIENDA DECLARADA en vez de ruta-mixta**, con
diagnóstico: (a) 13/16 docs con cobertura IDÉNTICA entre brazos; el gap vive en 2 docs de
denominador pequeño (SG200-IS EN: 0.75→0.25 con TODAS las páginas generadas — el QA mató más
en ese doc EN; TIDT096: Haiku cubre 2 páginas que Sonnet dejó a 0); (b) Sonnet-solo también
deja ~20% de páginas-tabla sin cubrir (0.799) → la ruta mixta (+$85) NO arregla la clase que
la banda temía (skip sistemático de tablas — NO existe); (c) el panel semántico de 40 pares
(leído): atribución correcta en todos, especificidad comparable, y cazó un fallo de SONNET
(meta-línea conversacional "Por favor, comparte el texto…" que pasa QA por no tener
tokens-valor — la clase ciega F2/X2 EXISTE y era del brazo caro).
**Decisión: Haiku corpus-wide** + filtro meta-líneas determinista (ambos brazos, contador) +
telemetría `uncovered_pages` por doc (mantiene abierta la REPARACIÓN dirigida con Sonnet como
contingencia si el gate T2(b) muestra misses ligados a cobertura — no se construye especulativa).
Coste real de brazos G0: Sonnet $3.49 vs Haiku $0.86 (4x). Decisión no-bloqueante reportada a
Alberto en lote (su mandato s104).

---

## GATE T2 — VEREDICTO: NO-GO A ESCALA → ROLLBACK A T1 (10-jul; el gate hizo su trabajo ANTES del tail)

**Generación T2: ÉXITO operativo** (81/81 docs, 0 errores, 45.889 enunciados QA-passed al dump,
~$9.7 Haiku; el doc ambiguo HLSI-MN-103 resuelto por ancla-DB; cinturón por-doc estrenado).
**Carga: 49.207 filas (T2+G0H) → tabla A3 a ~71K. Y el gate anti-dilución DISPARÓ:**

- **T2(b) famtie: 0 ganancias de ancla** en los 39 pools (STOP pre-declarado: "<2 mejoran" → PARA).
- **T2(c): 2 anclas OK PERDIDAS** (hp005#2 «misma zona o subzona», hp006#2 «ISO-X» — victoria del
  propio piloto R2 en s94) + served-churn en cat021/hp005/hp006 + 8 golds con menos surrogates hyq.
- **Mecanismo DIAGNOSTICADO** (probe pre/post + DB): crowding INTERNO del canal a escala —
  hp005/hp006: entraron 0 / salieron 5 y 3 (los padres-enunciado deduplican keep-max contra hits
  existentes y desplazan la cola vectorial cruda dentro del cap de fusión = pérdida pura);
  cat021: 12 entraron / 13 salieron, inundado por docs 40-40 (incl. el guide EN del 40/40R —
  el mismo doc del episodio s103b). El sort-mixto SIN CUOTA del canal enunciados (medido bien
  a 22K, DEC-089) no aguanta 71K: **la misma clase de fallo que el canal hyq resolvió con
  FUSIÓN POR CUOTA** — el precedente que este diseño declaró como riesgo mayor.

**Acciones ejecutadas:** rollback DELETE por batch (T2:h1 + G0H:h1) → tabla a 21.995 (T1 exacto)
+ VACUUM directo-PG (fantasmas HNSW, DEC-088). Prod restaurado al estado que TODAS las
mediciones de hoy asumen. **El tail (~900 docs, ~$95) NO se gasta** hasta el fix.

**Lo que NO se pierde:** los 45.889 enunciados T2 (+8.960 G0/SMOKE) están QA-passed en dumps —
el activo caro está pagado y a salvo; el fix es de SERVING (canal), no de generación. Re-carga
post-fix = ~$1 de embeddings.

**Siguiente (diseño nuevo con su propio gate, dúo obligatorio):** cuota del canal enunciados en
la fusión (espejo del patrón hyq DEC-099: presupuesto propio + barra; opciones a evaluar:
cuota fija de swapped-parents por query · cap por-doc en el colapso · barra de sim escalada).
Gate de re-carga = ESTE MISMO probe pre/post (los artefactos pre_t2/post_t2 quedan como
referencia del modo de fallo).
