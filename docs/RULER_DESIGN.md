# Diseño del Ruler (eval / gold) y registro de decisiones

> Registro de decisiones (estilo ADR) del ruler del Technical Bot. Cada decisión
> lleva *alternativas + por qué*. Si alguien cuestiona "¿por qué lo hicimos así?",
> la respuesta está aquí. Creado en la sesión de repaso (30 may 2026), tras el
> hallazgo de s30 ("el ruler está parcialmente roto").
>
> Vocabulario: **ruler = gold = ground truth = eval set** (sinónimos).

---

## 0. Qué es y para qué

El **ruler** es el instrumento que mide si el RAG funciona. **Vive FUERA del RAG**,
nunca se despliega, el técnico no lo ve. Es la plantilla de respuestas correctas de
un examen; el RAG es el alumno; `scripts/test_bot_vs_gold.py` es el profesor.

- **Propósito = DIAGNÓSTICO**: cazar fallos *categóricos* (¿alucina? ¿admite cuando
  el corpus cubre? ¿mezcla cross-product? ¿maneja conflictos?) + dar confianza de
  piloto. **NO es un gate estadístico** de deltas finos (con n pequeño no podría
  serlo; s27 ya lo concluyó).
- **Por qué existe**: no hay técnicos reales en meses → el ruler es la **única
  señal** de "¿este cambio mejora o empeora el bot?".
- **Principio rector — independencia del camino de información**: el ruler lee la
  **FUENTE al píxel** (render, todas las modalidades), NO los chunks. Si compartiera
  los chunks del RAG, compartiría sus puntos ciegos y no podría juzgarlo (sería
  circular). Esa independencia es lo que le da autoridad.

---

## 1. Principios de conducta del bot (validados con Alberto)

**Jerarquía rectora**: **Seguridad (cero invención) > Honestidad (admitir lo que no
se sabe) > Utilidad (responder/guiar)**. En duda, gana la acción segura. Inventar es
el pecado cardinal (un técnico actuando sobre un dato inventado puede causar un fallo
de seguridad) — peor que no responder.

### Las 5 conductas
La `conducta_esperada` de cada gold se **deriva del resultado de la LOCALIZACIÓN en el
corpus**, NO del system prompt (ver Decisión D2).

| # | Conducta | Condición (qué encontró la localización) | Qué hace |
|---|---|---|---|
| 1 | **answer** | El corpus cubre la respuesta, clara y recuperable | Responde con valores exactos + cita [F] |
| 2 | **answer-con-conflicto** | Variantes en conflicto de **mercado/idioma** (ES vs US) — NO de revisión | Surfacea **ambas** + señala la discrepancia. No elige ganador |
| 3 | **clarify** | La pregunta exige elegir entre productos/variantes con respuestas distintas y no se especifica cuál | Espectro por confianza (ver abajo) |
| 4 | **admit** | El corpus no lo cubre | Reconoce el gap (tono propio) + registra |
| 5 | **refuse-inference** | Se pide una inferencia no documentada (compatibilidad cross-brand, "¿debería?", extrapolación) | No infiere; surfacea hechos documentados por producto, separados; redirige al fabricante |

### Parcialidad NO es una conducta (es recuento por hecho)
Cuando el corpus cubre *parte* de lo que la pregunta exige: **no se clasifica como
"parcial"** (sería un agujero que enmascara fallos de localización). Se resuelve a
nivel de **hechos atómicos**: cada hecho CORE está *presente (valor X)* o
*ausente-probado* (confirmado exhaustivamente que el corpus no lo tiene). El recuento
cae solo: todos presentes → answer; todos ausentes → admit; mezcla → answer que da
los presentes + **señala los ausentes** (sin inventarlos). Afirmar que un hecho falta
tiene la **carga de prueba MÁS ALTA** (localización exhaustiva), así que no es un
camino perezoso. Ver Decisión D5.

### Clarify = espectro por confianza de fuzzy-match contra el catálogo
(`data/model_catalog.json` es la fuente única — Decisión D6.)
- **Alta** (typo/separador/near-name único: "ID-3000"→ID3000) → **answer-con-asunción
  declarada** ("Asumo ID3000; si era otro, dímelo"). Ahorra round-trip, no es adivinar.
- **Media** (pocos plausibles) → clarify con **candidatos acotados del catálogo**.
- **Baja/amplia** (familia, muchos) → **pregunta abierta**, sin enumerar.

### Conflicto de revisión (mismo idioma) ≠ conflicto de mercado
- **Revisión mismo idioma (rev 3 vs rev 4 del mismo manual ES)** → **manda la última
  ("latest wins")**. NO es answer-con-conflicto. Es una regla de **datos/retrieval**:
  marcar `superseded` en ingesta + filtrar `status='active'` en retrieval (TECH_DEBT
  #4). **Gap actual**: chunks_v2 no tiene metadata de revisión → el RAG podría servir
  una revisión obsoleta hoy. El ruler aplica latest-wins también y **expone** el gap.
- **ES vs US (mercado/variante)** → answer-con-conflicto (surfacear ambos).
- Discriminador: ¿mismo documento en distinta revisión (latest wins) o documentos
  distintos para mercados distintos (surfacear ambos)?

### Qué NO es conducta (es tono/formato)
El framing cálido del "no tengo info" (gap propio, intenta recuperar, promete acción),
urgencia, follow-ups → **tono**, vive en el bloque FORMAT del prompt, **no se gradúa**
en el eje de conducta del gold.

---

## 2. Cómo se construye un gold (el pipeline de verificación)

1. **Localización exhaustiva y auditable** (el eslabón más débil — Decisión D3):
   buscar términos/identificadores en **TODOS** los manuales del fabricante relevante
   + existencia en chunks_v2 (por SQL/búsqueda directa, **no** el ranker del RAG = no
   circular). Más completa que el retrieval del RAG (legítimo: offline, una pregunta).
   Registrar en `_provenance` qué se buscó / encontró.
2. **Render del píxel** de la fuente (`render_pdf_page.py`), confirmando que es
   digital-native. **Nada de texto-solo**: el texto extraído de PDFs escaneados/OCR
   está corrupto (lección 7-segmentos: "r.i" era "r.1") y reproduciría el error.
3. **Lectura cross-model** con restricciones de dominio (ej. 7 segmentos:
   `1`≠`i`, `L`≠`i`, `5`=`S`). Desacuerdo residual → `needs_human`.
4. **Hechos atómicos** (core / supplementary); cada uno presente / ausente-probado.
5. **Conducta derivada de principios + localización**, independiente del prompt.
6. **Cobertura = existencia independiente en chunks_v2**. "En el manual pero NO en
   chunks_v2" (truncado/no ingestado) → conducta del bot = admit, PERO se marca
   **GAP DE CORPUS** (alimenta el lever de extracción, no es fallo del bot).

**Idiomas (enfoque ES + EN/US del proyecto)**: la localización **busca en ES Y en EN**
— una búsqueda solo-ES perdería el manual inglés (= el fallo de recall que evitamos) y,
peor, **no detectaría los conflictos ES-vs-US** (conducta 2, que exige encontrar AMBAS
versiones; la conciencia de idioma es lo que la habilita). Reglas: **scope = ES + EN**
(los idiomas que servimos); FR/DE/PT quedan fuera del answer — si un dato solo está en
FR/DE/PT no es servible → `admit` + nota, **no fingir cobertura** (alinea con la política
de idiomas + el filtro de s30). El **gold se redacta en ES** (audiencia técnica), con la
fuente (ES o EN) citada **verbatim**; preferencia: ES si está y basta, EN suplementa o
cuando no hay ES, ES≠EN → conducta 2. Riesgo: la traducción EN→ES del answer puede mover
matices (los valores/códigos son idioma-independientes y van seguros; vigilar la prosa).

**Estrategias de localización (REVISADAS tras el review adversarial — los supuestos del
v1 chocaban con el código; el review verificó 5 fallos, 2 anclados en código):**
1. **Respuestas solo en diagramas/imágenes**: NO depender de `has_diagram`/`diagram_url`
   — verificado: en chunks_v2 `diagram_url=None` para TODO el corpus (`reingest/index.py:61`,
   follow-up B4 pendiente) y `has_diagram`="la página tiene cualquier imagen" (sin precisión,
   `chunk.py:352`); las cifras 31%/84.9% de #9/#10 son de la tabla VIEJA. → para preguntas
   visuales, **render-browse directo** de páginas candidatas (multimodal); el pipeline de
   diagramas incompleto = **GAP DE CORPUS** (lever de extracción #10).
2. **Seguir el PRODUCTO**: **REUSAR `model_catalog.json`** — verificado: el catálogo YA hace
   split-compound (`AM2020`, `AFP1010`, `ZX2e/ZX5e` incluidos con `source:split-compound`); los
   50 "excluidos" son mayormente risky-acronym/junk, NO productos. **No re-implementar el split**
   (mi v2 atacaba un fantasma). Residual real: pure-alpha (`ZXAE/ZXEE`) ya declarado como gap.
   Modelo→fabricante real (relabeling OEM Securiton/Honeywell — hp002/011/013) vía el catálogo.
3. **Recall ROBUSTO, NO budget-bounded** (decisión Alberto s38: **definir bien los golds manda
   sobre el coste** — es autoría ONE-TIME, no per-query): grep barato ES+EN sobre **TODOS** los
   manuales del producto → **render de TODAS las candidatas** (sin top-K acotado) → solo el
   residual IRREDUCIBLE (diagrama/scan ilegible) → `needs_human`. Robusto > barato (un gold mal
   localizado envenena el árbitro entero).
4. **Grep sobre texto corrupto**: la fiabilidad del grep es **POR-PÁGINA, no por-doc** (un PDF
   nativo puede tener glifos corruptos —7-seg— sin ser escaneo). **REUSAR `diagnose_corpus.py`**
   (ya clasifica escaneado/imagen-heavy/texto-limpio/**mixto**); los manuales objetivo son
   UI-screenshot-heavy → `mixto`/`imagen-heavy` (texto fiable en unas páginas, píxel en otras)
   → enrutar **por página**, no un switch binario por-doc.
5. **Existencia ≠ usable**: existir en chunks_v2 es *necesario, no suficiente* — chunk
   presente pero inservible (matriz sin marcas #24, denso #18) → el **render decide** la
   usabilidad; presente-pero-inservible = **GAP DE CORPUS** (no fingir cobertura).
6. **Referencias cruzadas** ("ver Manual X" → así se alcanza hp017) + **todos los manuales
   del producto** (user/install/config — hp003/#11c) + **multi-parte** ensamblado (#4/#7) +
   **equivalencia unidades/formatos** (kΩ↔Ω, coma-ES↔punto-EN).

Reframe del review: 3 de estos (diagramas, OCR, denso) son **gaps de corpus reales** (chunks_v2
más incompleto de lo asumido) → el localizador NO los "arregla", los **DIFIERE** a needs_human +
GAP DE CORPUS (lever #10). Honesto: son diferimientos, no fixes. El "mínimo" del localizador =
lo que los golds del slice necesitan; lo demás se expande con **evidencia del slice**.

**OJO (límite del slice)**: los 19 golds actuales tienen la `page` ya fijada por el autor → la
rebanada vertical **NO testea el caso duro del localizador** (encontrar la ubicación de cero).
Para testearlo de verdad hace falta un test **ciego** (pregunta nueva, o ignorar la `page` del
gold). El slice valida sobre todo el esquema + hechos atómicos + scorer; el localizador necesita
su propio test ciego.

**Regla de scans / texto no extraíble (s33, Tier B hp009)**: si un manual devuelve casi-cero hits
de grep (p.ej. MIE-MI-300rv02: 1 hit en 107 pp), el grep es **INVÁLIDO** para ese doc — NO es
evidencia de ausencia (es la trampa OCR de D4 a escala de documento). Regla: anclar en **evidencia
POSITIVA del render** (otro manual digital-native del mismo producto, o el propio diagrama que
muestra la ausencia estructural — hp009: Fig 11/12/13 de MIE-MI-310 prueban que el lazo es bucle
cerrado sin RFL); si no hay evidencia positiva → `needs_human`. NO concluir "ausente" desde un grep
ciego al scan. Corolario para 30+ fabricantes: registrar la cobertura por-manual + si el doc es
digital/scan en `_provenance.localizacion`.

**Dos ejes de verificación separados**: el cross-model valida **LEER**; la búsqueda
exhaustiva valida **ENCONTRAR**. El primero no cubre al segundo.

**Cross-check de UBICACIÓN (s38, del review adversarial de C4 — refuerza ENCONTRAR + LEER):**
(a) **confirmación por CONTENIDO sobre el PREDICADO COMPLETO** (el hecho entero: valor + parámetro +
contexto/tabla — un número que aparece en otro contexto NO cuenta); (b) **render ± 1 vecina**
comparando el CONTEXTO del hecho (caza el off-by-one de hp005/17/18); (c) **lectura de valores CORE
con DOBLE SEÑAL (AND)**: cross-model del render **Y** match determinista del valor en el texto
extraído; en scan (texto corrupto) el match FALLA → `needs_human` (no fingir). **La ruta de ranking
SEMÁNTICO sobre chunks_v2 se DESCARTÓ por CIRCULAR** (compartiría el sustrato Voyage del bot → §0;
y es redundante: grep + render±1 + match ya cazan hp017/18). (d) **multi-página (minimizar
`needs_human`, Alberto s38)**: si el hecho aparece en varias páginas → registrar TODAS, anclar la de
más contexto; `needs_human` solo si difiere el PREDICADO real, no por multiplicidad.

**IMPLEMENTADO (s39, `scripts/locate_fact.py` = C4; `scripts/cross_generate.py` = co-gen GPT-5.5; DEC-010).**
Lecciones durables del build + del test ciego (hp017/05/12, que cerró el "test ciego del localizador" pendiente):
- **producto→manuales NO se deriva de `chunks_v2.product_model`** (estructuralmente sucio, clase del bug AC-220:
  doc-codes 'MPDT-280', separadores 'AM2020 y AFP1010', familia dispersa en ≥5 etiquetas → se pierde manuales del
  gold; verificado en hp012). C4 toma el SET de manuales **explícito del autor** + un **sugeridor dirigido por
  FILESYSTEM** (las carpetas `Manuales_*`, incluido `_Privado` que NO es dedup: 288 docs únicos). chunks_v2 SOLO
  para corpus-existence. (La alternativa "grep por carpeta del fabricante" NO escala: 2/23 fabricantes con carpeta.)
- **Doble-señal verificada en ambos sentidos**: cazó un misread de dígito Claude-200dpi '3240' vs GPT '3244' →
  resuelto '3244' a 400 dpi (el cross-model tenía razón). Para dígitos de tabla pequeños: re-render ≥350 dpi.
- **Anclas numéricas con frontera** (no substring crudo: '792'∈'13792'); **valor de prosa = substring contiguo**,
  no token-overlap (que explotó a 21 candidatas). El predicado se confirma por **valor + término de contexto co-ocurrentes**.

**Auditar también la PREGUNTA**, no solo la respuesta (premisa, sesgo, testabilidad).
Permitir **DESCARTAR** una pregunta mala (como hp016 en s27), no forzar su arreglo.

---

## 3. Scoring

- **3 ejes separados**: **factual** (¿inventó? — crítico/safety), **completitud**
  (cobertura de hechos CORE; no penaliza concisión-por-diseño), **conducta**.
- **Asimetría de seguridad** (del principio rector): **CUALQUIER alucinación = FALLO
  automático**, por completa que sea la respuesta; la incompletitud es PARCIAL, no
  FALLO. Inventar y omitir NO son iguales.
- **Bespoke**, reusando el **matcher ESTRICTO de PR#15** (números, códigos de modelo,
  normalización OCR) para lo mecánico; LLM solo para prosa irreducible. Cada veredicto
  atómico **transparente/auditable**.
- **Validación del scorer**: spot-check de sus veredictos vs juicio humano/cross-model
  en ~5 golds antes de fiarnos (como la calibración del juez s11/s15).

**Estado de implementación (s32)** — `scripts/atomic_scorer.py` + `scripts/strict_match.py`
(matcher PR#15 extraído, reusado) + `scripts/factual_gate_eval.py`/`evals/factual_gate_fixture.yaml`:
- **Completitud** mecánica con el matcher estricto (frontera de no-palabra en anchors → corrige
  el falso positivo substring `'40'∈'240'`). FUERTE en hechos con anchors (número≥2díg/código);
  DÉBIL en prosa (sinónimos, `valor` compartido, códigos 7-seg) → la prosa irreducible al LLM.
- **Factual** = check cross-model GPT-5.5 (`--llm`) acotado a los hechos: marca CONTRADICCIONES
  (no omisiones ni info extra; carve-outs anti-s13), juzga por significado no por etiqueta.
  Caracterizado: **5/5 recall + 4/4 especificidad** (fixture n=9 → indicativo, no exhaustivo).
- **Conducta** heurística mínima (a endurecer con golds de conducta).
- **Lección `valor`**: debe ser el IDENTIFICADOR DISTINTIVO del hecho, no una frecuencia/etiqueta
  compartida (hp007: 4 tareas anuales con el mismo "una vez al año" = indistinguibles). Regla de autoría.
Validado en la rebanada (hp007/11/17); el scorer transparente SUPERÓ al juez opaco en hp007 (que
penalizaba por dato obsoleto). Pendiente: completitud de prosa por LLM, re-autorar hp007, crecer
el fixture de recall. Ver TECH_DEBT #35.

**Estado de implementación (s40)** — completitud de prosa por LLM **HECHA y validada para el cabo B1** +
fix del matcher de rangos (`DECISIONS.md` DEC-011):
- **`atomic_scorer.py --prose-llm`** (#35): overlay GPT-5.5 que RESCATA hechos de prosa marcados ausentes
  por el mecánico (solo False→True = asimetría conservadora; sin el flag es byte-idéntico). Firmado en B1
  (s38) + **cabo cerrado (s40)**: hp007 'cada 2 años' = "bienal" del bot NO es over-credit; cat007 'no
  enclavado' NO se rescata (el bot ADMITIÓ). El prompt de prosa NO necesita endurecerse.
- **Fix del matcher de RANGOS** en `distinctive()` (`(?<!\d)` antes del signo): "110-230" ya no genera el
  anchor espurio "-230" (que fallaba la frontera de dígito de `_anchor_present` y `_value_on_page`) →
  **cat005 5/6→6/6**; los 19 golds intactos; +6 tests (`tests/test_strict_match.py`).
- **Limitación residual**: soltar el signo de una suma-sin-espacios es más laxo en el matcher COMPARTIDO
  (1/134 hechos = cat001; instrumentos de retrieval + scorer; impacto actual 0). El árbitro lee señal
  CATEGÓRICA + delta razonable; la calibración fina amplia sigue acotada por n. Ver DEC-011 + TECH_DEBT #35.

**Estado de implementación (s41)** — eje NO-FABRICACIÓN + ramificación por estado-del-hecho (`DECISIONS.md` DEC-012):
- **Eje NO-FABRICACIÓN** (`undue_inference_check`, cross-model GPT-5.5, gated `--llm`, binario, CONSERVADOR): caza que
  el bot AFIRME un hecho marcado `ausente-probado` (valor/compatibilidad/recomendación/inferencia; claims prohibidos
  en `_UNDUE_SYS`). Cierra el agujero del eje factual (solo-contradicción NO ve la fabricación sobre el vacío). Asimetría
  de seguridad: afirmar un ausente = FALLO. Es **más FRÁGIL que el factual** (opera sobre valor=null, sin ancla textual)
  → señal categórica, no fina; spot-check humano. NO es el juez opaco de D7: binario, acotado, conservador, auditable.
- **Ramificación por `estado`-del-hecho (C1)**: `score_gold` separa los `ausente-probado` (no cuentan en completitud,
  van al eje no-fabricación) de los `presente`. Aplica a TODO ausente-probado, viva en admit/refuse-inference o en un
  answer MIXTO (D5: hp006/09/13). `factual_check` ya NO recibe los ausente-probado (no son hechos presentes que contradecir).
- **refuse-inference** deja de caer a REVISAR (entra en `ANSWER_LIKE`): el bot debe RESPONDER (specs por-producto, medido
  por completitud) y NO inferir la relación (medido por el eje no-fabricación).
- **Orden del veredicto = asimetría de seguridad**: los FALLOS (contradicción / fabricación) se evalúan ANTES que los
  REVISAR (eje no evaluable) → un error en un eje no degrada un FALLO detectado en el otro (bug cazado por el dúo, P3 r2).
- **Lección de AUTORÍA (del spot-check de hp006)**: un hecho `ausente-probado` debe formularse QUIRÚRGICAMENTE (solo lo
  genuinamente ausente). Mezclar una nota sobre UN manual ("MFDT170 no menciona X") cuando OTRO sí lo cubre (MIDT170)
  induce un falso-positivo del eje no-fabricación. Pendiente: re-formular el hecho ausente-probado de hp006; aplicar al autorar #16/#18.
- Validado: re-baseline 7 FALLO/10 PARCIAL/2 REVISAR/0 PASS (19); 261 tests (+8 `tests/test_atomic_scorer.py`). Gaps en DEC-012.

---

## 4. Plan por fases

> **📍 Canónico:** el roadmap + estado GLOBAL vive en `PLAN_RAG_2026.md` (mapa canónico). Esto
> es el **sub-plan detallado de construcción del ruler**; PLAN apunta aquí para el detalle. Si
> discrepan sobre el rumbo, manda PLAN.

Estado al crear el doc (s31): Fases previas ya hechas esa sesión (3 herramientas, gate de
cuarentena, 3 golds verificados pendientes de retrofit a hechos atómicos, normas).
**Estado actual (s35): 19/19 verificados (RULER COMPLETO). Fase 3 (crecer el ruler) = trabajo
vigente, por cobertura-diagnóstica (`DECISIONS.md` DEC-003; método y nivel ahí).** — ver Fase 1/3 abajo.

- **Fase 0** — gold_store.py + **localizador exhaustivo** + esquema v2 + validación en
  CI + este doc. *(tareas #7, #9)*
- **Fase 1** — verificar/reparar los 19 al estándar nuevo (incl. auditar la pregunta).
  **TIER A + B + C COMPLETOS (s33): 19/19 verificados (RULER COMPLETO).** Tier A (12, answer-de-spec):
  hp001/02/03/05/07/08/10/11/14/17/19/20. Tier B (5, conducta): hp004/06/09/13/15. Tier C (2,
  conflicto/OCR): hp012/018. Cada uno render + (cross-model donde aplica) + hechos atómicos + `_provenance`.
  **HALLAZGO TIER B: los 4 "admit" estaban MAL → answer/answer-parcial** (hp004 era ya clarify:
  migración de vocab ask_clarification→clarify, NO un flip). hp015 (CCD-103 convencional →
  desconexión por ZONA, no por detector individual) y hp009 (lazo direccionable ZXe = bucle cerrado
  SIN resistencia de fin de línea; evidencia positiva en MIE-MI-310 Fig 11/12/13, MIE-MI-300 es scan)
  corrigen una PREMISA falsa. hp013 (ADW535: config en EEPROM no volátil → se conserva; respaldo =
  alimentación redundante PWR-R, no batería tampón; procedimiento de batería = ausente-probado) y
  hp006 (AFP-400 'Tierra': la instalación MIDT170 SÍ cubre detección MPS-400 + tabla de avería del
  lazo + aisladores ISO-X; el autor s27 solo usó la hoja NAM-232 + el PSU; gold_answer malformado
  limpiado) = answer-parcial. **Raíz = over-admisión del gold s27 por subsets de PDF demasiado
  estrechos** (idéntico a hp017) → infravaloró al bot en s28-30. Protocolo 3 (GPT-5.5 cross-model +
  sub-agente Claude) cazó 3 over-claims propios (hp015 "puentear" no documentado; hp013 inferencia
  placa-swap; "no batería tampón" poco anclado) → corregidos; 1 falso-positivo del revisor (hp006
  JP2, VERIFICADO en 50253SP 2-44 por rule C).
  **TIER C (s33, los 2 diferidos en s30 a "técnico+PDF"): RESUELTOS SIN TÉCNICO vía render.** hp012 =
  answer-con-conflicto: conflicto REAL ES-vs-US del AFP1010 (Notifier España MFDT280/MPDT280 = 2 lazos/396
  vs Notifier US 15088SP/1998 = 4 lazos/792; documentos distintos → surfacear ambos, no elegir; AM2020 10
  lazos/1980 y 99+99 disp/lazo consistentes). hp018 = answer: el gold s27 citaba el PRODUCTO EQUIVOCADO
  (MIE-MI-310 es ZXAE/ZXEE convencional/2000, NO el e-series ZXe) + 3 valores fabricados (ZX5e=5 salidas /
  EOL 10kΩ / 500mA) → re-anclado a MIE-MI-530 (ZX2e/ZX5e, digital-native, 64 chunks: 4 salidas / 6K8 / 1A).
  MI-310 es imagen-only (grep=0 hits → regla de scans §2: leído por RENDER, evidencia positiva). Protocolo 3
  (sub-agente Claude 13✓/0 FP + cross-model GPT-5.5) cazó 3 over-claims míos de FRAMING (no de valores):
  "variante de mercado" sin metadata de revisión, "ZXe excluye ZXAE/ZXEE", "fabricados en NINGÚN manual" →
  acotados. **LECCIÓN: el diferimiento de s30 a técnico era DEMASIADO AMPLIO** — render + cross-model
  resuelven conflicto/OCR; el técnico (D1) pasa a spot-checker, no es prerequisito. **Caveat hp009 (Tier B):**
  también usó MIE-MI-310 (ZXAE/ZXEE) para el lazo de la ZXe → la sustancia (el lazo direccionable no lleva
  RFL) se CONFIRMÓ al píxel contra MIE-MI-530 (f19 §3.4.3.1 Fig 9/10: bucle cerrado Inicio Lazo OUT + Retorno, sin RFL) y hp009 quedó RE-ANCLADO a MI-530 (MI-310/ZXAE-ZXEE como corroboración) en esta misma sesión. *(tarea #4)*
- **Fase 2** — scorer de hechos atómicos (3 ejes) + harness. **NÚCLEO HECHO (s32):**
  atomic_scorer (completitud mecánica + factual cross-model + conducta heurística),
  strict_match extraído, gate factual caracterizado (5/5,4/4 n=9). **Completitud-prosa por LLM
  (#35) HECHO en Fase A s38** (`atomic_scorer --prose-llm`, flag default-off, B1 firmado por
  Alberto); pendientes: re-autorar hp007 valor + endurecer conducta + factual no-determinista
  (TECH_DEBT #35/#37). *(tarea #8)*
- **Fase 3** — crecer el ruler: estratificado (fabricante/tipo/modalidad) + sesgado a coloquial +
  modos de fallo. **Ejecución VIGENTE = `CATALOG_PLAN.md`** (catálogo SINTÉTICO 3-bandas, DEC-008;
  sintético porque no hay técnicos-curadores y los query_logs = ecos del propio eval). *(tarea #5)*
- **Fase 4** — lever de generación: separar el prompt en bloques (GROUNDING_CORE +
  BEHAVIOR_POLICY + FORMAT), eval-validado; cazar política legacy. **change-1 REVERTIDO**
  (DEC-001); **reranker DESCARTADO como lever** (DEC-005: ningún lever de retrieval movió calidad
  end-to-end). Re-evaluar levers solo con el árbitro fiable + catálogo crecido. *(tarea #6)*
- **Lever de extracción/chunking** — diagnosticado por los GAP DE CORPUS del ruler;
  evidence-driven. Candidato: el render+multimodal del ruler como mejor extractor del
  contenido visual que LlamaParse pierde. *(tarea #10)*

**Principio INTERLEAVE (anti perfeccionismo de instrumento / pregunta cero)**: no
serializar. Construir el ruler **fiable-lo-suficiente** → tirar del lever que señale →
**demostrar mejora de producto** → y entonces seguir creciendo el ruler.

**Rebanada vertical antes de escalar**: pasar 2-3 golds COMPLETOS por todo el pipeline
nuevo (esquema → localización → render → hechos atómicos → scorer) → validar
end-to-end → solo entonces escalar a los 19 / nuevos.

---

## 5. Decisiones (D) — qué elegimos y por qué

- **D1. Crecer el ruler con golds que autora Claude (no esperar a técnicos).** Alt:
  esperar a técnicos (no hay en meses → congela todo). Por qué: es la única vía de
  señal ahora; el técnico, cuando llegue, pasa de *autor* a *spot-checker* de lo
  marcado + inyector de realismo.
- **D2. Conducta del gold desde PRINCIPIOS + corpus, NO desde el system prompt.** Alt:
  derivarla del prompt actual (lo propuse primero). Por qué rechazada: el prompt
  arrastra política legacy sub-óptima (s13-15); heredarla haría del ruler un *yes-man*
  que ratifica el bug y nunca lo detecta. Los principios se escriben de cero y se
  validan con Alberto. **Ojo**: los propios "principios" también eran legacy potencial
  → por eso se re-derivan de primeros principios, no del folclore de prompt-tuning.
- **D3. Localización exhaustiva y auditable como paso estructural propio.** Alt: el
  `pdfs_used` heredado / mi corazonada. Por qué: "saber dónde está la respuesta" ES un
  retrieval hecho a mano; si es débil, el ruler es débil (ya rompió hp017 con un subset
  estrecho, hp009 cita el manual equivocado). El cross-model valida *leer*, no
  *encontrar* → hace falta un eje propio.
- **D4. Render del píxel, no texto extraído, para verificar.** Por qué: el texto
  extraído de manuales escaneados/OCR está corrupto (7-segmentos) — "verificar" con él
  reproduciría el error del corpus. `pdf_grep` solo **localiza**, no verifica.
- **D5. "Cobertura parcial" NO es una conducta; se resuelve por hecho atómico.** Alt:
  añadirla como 6ª conducta (lo propuse). Por qué rechazada (challenge de Alberto):
  sería un cajón de sastre que además **enmascara fallos de localización**. Se mueve la
  decisión del nivel respuesta (fuzzy) al nivel hecho (binario: presente /
  ausente-probado). Afirmar ausencia = carga de prueba más alta.
- **D6. Clarify = espectro de confianza; candidatos del CATÁLOGO, no de los chunks.**
  Histórico: s14 descartó "listar candidatos" por (1) escalabilidad 30+ fabricantes,
  (2) no anclar, (3) consistencia, (4) la lista salía del top-k = incompleta/engaña.
  Reapertura (Alberto): ayuda al técnico con near-names. La objeción (4) ya no aplica:
  desde s28 hay catálogo (fuente única) → lista fiable y acotada. Mejor aún: alta
  confianza → answer-con-asunción (ahorra round-trip, no adivina).
- **D7. Scoring bespoke, NO RAGAS.** Por qué: las métricas core de RAGAS miden vs el
  contexto recuperado (chunks) = la circularidad que rechazamos; su descomposición es
  LLM = reintroduce varianza. Robamos la *idea* (corrección a nivel de claim TP/FP/FN),
  no el framework. Garantía de alineación: validar el scorer contra humano (sustituye
  al benchmark de RAGAS).
- **D8. No "sacar el system prompt" para comparar limpio.** Alt (Alberto): bot sin
  prompt como base. Por qué rechazada: el prompt contiene el *grounding* — sin él, el
  bot responde de conocimiento paramétrico → más alucinación + **enmascara fallos de
  retrieval** (parece que va bien porque "se lo sabe"). La calibración se hace con base
  **solo-grounding** (no sin-prompt), y solo como diagnóstico, no como métrica.
- **D9. Separar el system prompt en bloques — pero en Fase 4, no ahora.** Por qué BP:
  separación de concerns + habilita la ablación + escala + mapea a los ejes del scoring.
  Por qué no ahora: un refactor del prompt no es behavior-neutral y hay que
  eval-validarlo → necesita el ruler fiable primero (catch-22).
- **D10. gold_store + esquema + CI; fuera los throwaway scripts.** Por qué: editar el
  gold con un script throwaway por entrada es un quick-fix a escala (ya choqué con 3
  bugs; hp006 quedó malformado). Validación de esquema caza eso.
- **D11. Reranker ABIERTO, no asumido como próximo lever.** Por qué: s29 midió que
  ningún lever de retrieval (reranker, top-k, RRF, dense-only) convirtió en mejor
  calidad end-to-end; el cuello era generación. Re-decidir con el ruler fiable.

---

## 6. Gaps / riesgos asumidos (declarados de entrada)

1. **n pequeño** aun creciendo → el ruler es diagnóstico, no gate estadístico. Los
   hechos atómicos mitigan (más señal/pregunta) pero no lo eliminan.
2. **Sintético ≠ wow real** → aun perfecto, es un proxy; solo preguntas reales
   (#10 / técnicos) lo cierran. Sesgar los nuevos a coloquial + modos de fallo.
3. **Localización residual** → la búsqueda exhaustiva aún puede fallar (fraseo raro,
   respuesta solo-en-diagrama) → `needs_human` para lo irreducible.
4. **Coste/tiempo** → render + cross-model + localización exhaustiva por gold es
   multi-sesión y cuesta API → el ruler será un **muestreo diagnóstico**, no exhaustivo.
5. **Refactor del prompt (Fase 4) no es behavior-neutral** → eval-validado, riesgo
   residual de regresión sutil.
6. **Calidad de chunks_v2 = suelo** de todo el ruler → lo aborda el lever de
   extracción; condiciona el techo.

---

## 7. Genealogía del corpus (contexto)

**v2** empezó con la **extracción vía LlamaParse** de los manuales → de ahí salió
**chunks_v2** (chunking + embedding Voyage `voyage-4-large`@1024). Los errores que el
ruler destapa (displays 7-seg malinterpretados, tablas/matrices perdidas, chunks
truncados) trazan a esa capa de extracción/chunking → ver lever de extracción (tarea
#10).
