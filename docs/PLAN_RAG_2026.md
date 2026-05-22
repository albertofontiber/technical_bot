# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El plan de acción único para llevar el Technical Bot
> desde su estado actual (3 fabricantes, en producción) hasta una solución
> alineada con best practices de Mayo 2026, escalable a 30+ fabricantes de PCI y
> usable por técnicos reales. Funde tres fuentes: la auditoría inicial, las
> recomendaciones de la calibración con Cowork (Opus 4.7), y los hallazgos
> empíricos de la Fase 0.
>
> **Audiencia.** Alberto (decisión estratégica) y cualquier sesión de desarrollo
> futura — debe poder leerse en frío y saber qué hacer y por qué.
>
> **Fecha:** 22 mayo 2026. **Estado:** Fase 1 — pipeline de re-ingesta en construcción.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best
> practice de Mayo 2026 con fuente identificable, (2) estructural — ataca la
> causa raíz, no el síntoma, (3) escalable a 30+ fabricantes sin fricción por
> fabricante. Si una propuesta no cumple los tres, se declara como gap honesto.

---

## 1. Resumen ejecutivo

**El estado real no es el que dice la métrica.** El eval reporta 51/52 PASS (98%),
pero esa cifra está sobreestimada y mide algo más estrecho de lo que parece. La
Fase 0 (calibración del eval) lo ha confirmado con evidencia.

**Lo que hemos aprendido, con datos:**

1. **El bot NO tiene un problema de invención de datos.** Verificación determinista
   de los 52 casos: de 49 datos duros citados (números, normas, switches,
   secciones), **49 están soportados por los chunks (100%), 0 miscitados, 0
   inventados**. La narrativa de "alucinaciones" que arrastrábamos no se sostiene
   para datos verificables.

2. **El problema real es el RETRIEVAL**, no la generación. Hay casos donde la
   respuesta correcta existe literalmente en el corpus pero el retrieval no se la
   entrega al bot (hp009: resistencia fin de línea 6,8 kΩ; hp001: contraseña de
   instalador). El bot responde con honestidad "no aparece" — no alucina, pero la
   respuesta es inservible para el técnico porque le faltó información.

3. **El eval mismo está parcialmente "amañado" sin querer.** Varias preguntas se
   recalibraron de `answer` a `admit_no_info` asumiendo que el corpus no tenía la
   respuesta. Verificado: en hp006, cm001, cm005 la respuesta SÍ está en el
   corpus. El eval bajó el listón en vez de arreglar el retrieval.

4. **El judge actual está mal de ALCANCE, no de calibración.** Evalúa "¿el bot fue
   fiel a los 5 chunks que recibió?" — y casi siempre sí. No evalúa "¿el bot dio
   la mejor respuesta que el corpus permite?". Esa segunda pregunta es la que
   importa.

5. **Un evaluador es tan fiable como la integridad de su input.** Durante la Fase 0,
   un bug propio (truncado de chunks a 1.800 caracteres) hizo que el 78% de los
   chunks llegaran mutilados al calibrador. Lección estructural, no anecdótica.

**El plan en una frase por fase:**

- **Fase 0** — Reanclar la métrica: judge v2 + verificación determinista. *(en curso)*
- **Fase 1** — Calidad estructural: arreglar el retrieval y la extracción de PDFs.
- **Fase 2** — Escalabilidad: quitar el hardcoding por fabricante antes del fabricante ~5.
- **Fase 3** — Routing + tool use: el "agentic RAG" bien entendido.
- **Fase 4** — Eval orgánico (queries reales de DGs) + CI.
- **Fase 5** — Técnicos reales (post 1-sept): field-grade eval y multi-turno.

---

## 2. El estado real del sistema — auditoría honesta

### 2.1 Por qué la métrica "98%" es engañosa

El judge automático (Claude Sonnet 4.6) reporta 51/52 PASS. Tres razones por las
que esa cifra no significa "el bot funciona al 98%":

- **Alcance estrecho.** El judge solo compara la respuesta del bot contra los
  chunks que el retrieval le pasó. Si el retrieval falló y el bot dijo "no tengo
  info", el judge lo da por bueno — sin saber que la info sí existía en el corpus.
- **El eval persiguió al bot.** Las preguntas que el bot fallaba se reclasificaron
  a `admit_no_info`. La categoría `cross_manual` tiene hoy 7 de 8 preguntas
  esperando "el bot admite que no sabe". El 98% mide "acierta el comportamiento
  que le pedimos", no "responde bien".
- **Sin gold standard humano.** Las 52 preguntas tienen `verified: false`. No hay
  ancla externa que diga si el judge acierta.

### 2.2 Lo que SÍ funciona (no tocar)

- **Faithfulness citacional.** Verificado: el bot no inventa datos duros (§3.4).
- **Retrieval híbrido base** — vector + keyword + content search en paralelo, con
  filtros cross-product y diversificación multi-doc. La estructura es correcta.
- **HyDE** — la expansión de query con hipótesis de manual funciona y está en
  producción (resolvió el vocabulary mismatch de hp001).
- **Observability** — `query_logs` captura cada interacción con consent RGPD.
- **Document lifecycle** — gestión de revisiones (supersede chains) Phase 1.
- **Arquitectura agnóstica al fabricante** en schema, retriever y generator.

### 2.3 Lo que NO funciona — los gaps reales

| Gap | Evidencia | Capa | Severidad |
|---|---|---|---|
| Retrieval miss: info en corpus que no llega al bot | hp009 (6,8 kΩ), hp001 (contraseña), hp005, hp014 | retrieval | **Alta** |
| Extracción de tablas: `[TABLA EXTRAÍDA]` mal aplicado (falsos + y −) | hp002, hp003, ≥12 casos | ingesta | **Alta** |
| Tablas con marcas visuales (X/✓) perdidas en extracción | hp007 (VESDA Tabla 7-1) | ingesta | **Alta** |
| Recalibraciones de YAML que enmascaran fallos de retrieval | hp006, cm001, cm005 (verificado: la info existe) | eval | Media |
| Reranker = LLM genérico (Sonnet pide a Sonnet) | reranker.py | retrieval | Media |
| `MODEL_PATTERN` regex hardcoded por fabricante | retriever.py (~50 líneas para 3 fabricantes) | escalabilidad | **Alta** (a 30+) |
| Atribución de fabricante incorrecta | ASD = Securiton, no Detnov | metadata | Media |
| Prompt del generator monolítico y saturado | TECH_DEBT #28 (regresión al añadir un bloque) | generación | Media |
| `section_title` de chunks no coincide con el contenido | hp003 (dice 2.4, trae 2.3) | ingesta | Media |
| Sin separación retrieve_top_k / generate_top_k | config.py (ambos = 5) | retrieval | Media |
| Judge de alcance estrecho, sin gold, mismo modelo que el bot | §2.1 | eval | **Alta** |

### 2.4 Escalabilidad a 30+ fabricantes

El **core** escala (schema, retriever, generator, eval son agnósticos). El
**boilerplate por fabricante NO escala**:

- `MODEL_PATTERN` regex hardcoded — 50 líneas para 3 fabricantes → ~500 para 30.
- Overrides de metadata hardcoded en `chunker.py`.
- Scraping con un script ad-hoc por fabricante.

**Regla:** el sprint de externalización a YAML (Fase 2) debe hacerse **antes del
fabricante ~5**, y siempre antes de la ingesta masiva post-M&A. Hacerlo después
duplica trabajo.

---

## 3. Hallazgos de la Fase 0 — calibración del eval

### 3.1 El proceso seguido

1. Se generaron 5 archivos de calibración (52 casos) para revisión humana.
2. Alberto calibró a mano hp001-hp004 (gold humano real).
3. Cowork (Opus 4.7, con acceso al corpus) calibró los 52 y produjo un documento
   de recomendaciones + una auto-auditoría adversarial de sus propios golds.
4. Claude verificó de forma **determinista** los claims objetivos contra los PDFs
   y los chunks completos.

### 3.2 El bug de truncado y su lección

`build_calibration_v2.py` truncaba el contenido de cada chunk a 1.800 caracteres.
**El 78% de los chunks (203 de 260) superaban ese límite**; las 52 preguntas
tenían al menos un chunk truncado. Cowork calibró sobre información mutilada — en
hp010 y hp011 declaró "fabricación citacional" porque el dato estaba en la
posición 1.870 y 2.148 del chunk, después del corte.

**Lección estructural:** un evaluador (LLM o humano) es exactamente tan fiable
como la integridad del input que recibe, y no tiene forma de saber que su input
está incompleto. → La verificación de hechos debe operar **siempre sobre la
fuente canónica completa**, nunca sobre una representación intermedia.

### 3.3 Verificación documental — resultados

Verificación con PyMuPDF sobre los PDF reales (inmune al truncado):

| Claim de Cowork | Verificación |
|---|---|
| hp006: "Earth Fault" está en AFP-300/400 como "Falla de Tierra" | ✅ Confirmado (50253SP págs. 80/160/215) |
| hp009: la resistencia fin de línea 6,8 kΩ existe | ✅ Confirmado (MIE-MI-530 pág. 21, sec. 3.4.4) |
| hp013: el ADW535 sí tiene batería de litio | ✅ Confirmado (pág. 29) |
| cm003: ASD531 es −10/+55 °C y 70%/95% humedad | ✅ Confirmado (pág. 91) — corrige el gold |
| cm001/cm005: doc Honeywell con respuesta cerrada existe | ✅ Confirmado (1 pág., literal) |
| cm004: dato "EN54-2 13.7 = 512" es real | ✅ Confirmado (MIDT190 pág. 24) |
| hp019: gold "−20/+60 °C" | ❌ Erróneo — el manual real es −10/+55 |

### 3.4 Verificación de citación — el bot no inventa datos duros

`scripts/verify_citations.py` extrae cada dato duro citado con `[F<n>]` y verifica
deterministamente si está en el chunk citado. Sobre los 52 casos:

> **49 datos duros citados → 49 soportados (100%), 0 miscitados, 0 inventados.**

(Los 4 que la primera pasada marcó como dudosos eran falsos positivos de formato
de unidad: `²` vs `2`, `Ω` vs `R`/`ohm`. Resueltos con normalización.)

**Límite honesto:** esta capa solo cubre datos duros. Las afirmaciones
cualitativas (rutas de menú, procedimientos) necesitan la capa 2 del judge v2
(§5). Pero la conclusión sobre datos verificables es sólida.

### 3.5 Conclusión de la Fase 0

El problema del bot **no es la alucinación citacional**. Es:

1. **Retrieval** — no entrega al bot información que sí está en el corpus.
2. **Extracción** — tablas y metadata mal extraídas del PDF.
3. **El eval mismo** — judge de alcance estrecho + recalibraciones que bajan el listón.

Esto **reordena las prioridades**: la Fase 1 (retrieval + extracción) es la de
mayor impacto en calidad real. El esfuerzo en "anti-alucinación" (validadores
post-generación) es un camino equivocado — ya falló una vez (TECH_DEBT #11i) y la
evidencia dice que la alucinación no es el cuello de botella.

---

## 4. El plan de acción — 5 fases

### Fase 0 — Reanclar la métrica *(en curso)*

**Objetivo:** una métrica que mida calidad real, no "comportamiento que pedimos".

| Tarea | Estado |
|---|---|
| Verificación de citación determinista (capa 1 del judge v2) | ✅ Prototipo funcionando |
| Arreglar el bug de truncado en `build_calibration_v2.py` | Pendiente |
| Corregir premisas falsas en `rag_improvements_recommendations.md` | Pendiente |
| Judge v2 — capa 2 (claims cualitativos) + arquitectura completa | Pendiente (§5) |
| Gold answers regeneradas con extracción de PDF + validación humana en muestra | Pendiente |
| Holdout split: `calibration_set` (~10) / `eval_set` (~42) | Pendiente |
| Validación humana de Alberto en muestra pequeña (criterio, no hechos) | Pendiente |

### Fase 1 — Calidad estructural (retrieval + extracción)

**Objetivo:** cerrar los retrieval misses. Es la fase de mayor impacto en calidad.

1. **Contextual retrieval** (Anthropic, sept 2024) — añadir a cada chunk un
   párrafo de contexto generado antes de embeber. Reduce el fallo de retrieval
   ~49% según Anthropic. Requiere re-embed del corpus. *Estructural, escalable.*
2. **Extracción visual de PDFs** — sustituir el extractor actual por LlamaParse
   en **modo multimodal** (VLM), no estándar (ver Resultado del PoC abajo).
   Elimina el `[TABLA EXTRAÍDA]` con sus falsos positivos y el texto sin
   espacios. Visión por defecto, no como fallback condicional.
3. **Reranker dedicado** — sustituir el reranker LLM-genérico por Cohere Rerank
   3.5 o Voyage Rerank-2 (cross-encoder entrenado). Más preciso, más barato, más
   rápido.
4. **BM25 + RRF** — fusión híbrida vector + BM25 con Reciprocal Rank Fusion.
   Captura términos exactos del dominio que los embeddings pierden.
5. **Separar retrieve_top_k (15-20) de generate_top_k (5-8)** — recall amplio para
   el reranker, contexto acotado para el generador.
6. **Auditar y revertir las recalibraciones de YAML ilegítimas** — hp006, cm001,
   cm005: verificado que la info existe; revertir a `answer`.

#### Diagnóstico del corpus (22 mayo 2026)

Inventario de los 1.208 PDFs (24.696 páginas) — `logs/corpus_diagnosis.json`:

- **Carga visual:** 567 documentos (47%) tienen contenido visual denso (≥0,5
  imágenes grandes por página). El contenido visual no es un caso aislado — es
  casi medio corpus.
- **Idiomas:** ~66% ES, ~17% EN, ~9% PT/FR/IT, ~8% sin detectar.
- **Duplicación:** 241 PDFs son copias byte-idénticas (verificado por SHA-256 en
  la Etapa A1: 1.208 PDFs → 967 únicos). 139 de los duplicados cruzan carpeta de
  fabricante — flag en el manifiesto para resolver la atribución en B5.
- **Escala del re-proceso:** 20.486 páginas únicas a extraer (de 24.696 totales,
  verificado en A1). Coste de extracción agéntica ≈$1.150 (≈45 créd/pág ×
  20.486 págs) — verificado tras el probe; pago único.

#### Decisiones de diseño del pipeline de re-ingesta

1. **Multimodal de primera clase, no fallback condicional.** Con el 47% del corpus
   con contenido visual denso, la visión se aplica por defecto. La arquitectura
   actual (visión solo si poco texto + imágenes grandes) está mal calibrada.
2. **De-duplicación a dos niveles.** Nivel 1: hash SHA-256 del archivo (caza los
   ~188 duplicados). Nivel 2: dedup **semántica a nivel de chunk** (embedding,
   intra-producto) — caza los chunks ES/EN equivalentes (descarta el redundante,
   conserva el contenido único, prefiere ES) y la duplicación del chunker
   (TECH_DEBT #7).
3. **Política de idiomas.** Se indexa: todo lo que contenga español (monolingüe o
   multilingüe) + lo solo-EN. NO se indexan los monolingües PT/FR/IT — pero se
   *registran* (no se borran): si un producto solo está documentado en otro
   idioma, hay que saber que la fuente existe para traducir/indexar bajo demanda.
4. **Detección de idioma por bloque/página** con librería robusta (`lingua`), no
   por heurística — un manual "ES FR GB IT" tiene páginas de cada idioma y el
   filtro de idioma del retrieval las necesita bien etiquetadas.
5. **El pipeline es el mismo para re-procesar el corpus y para añadir un manual
   nuevo** — automatizable desde el día uno. "Añadir un fabricante" debe ser un
   comando, no un script ad-hoc.
6. **`page_number` fiable por chunk** — prerrequisito del deep-link a la fuente
   (enlace `manual.pdf#page=N` para que el técnico vaya directo a la página).

#### Resultado del PoC de extracción (22 mayo 2026)

PoC sobre 6 manuales representativos, 3 stacks — `logs/poc_extraction/`:

- **El extractor actual (baseline) hay que sustituirlo — demostrado.** Pierde los
  espacios entre palabras dentro de los bloques que marca como tabla (`pdfplumber`
  produce texto pegado, ilegible), falsea tablas masivamente (`[TABLA EXTRAÍDA]`
  en títulos de figura y párrafos normales), no genera estructura (0 headers),
  25-28% de duplicación interna, y 0 caracteres en escaneados.
- **LlamaParse gana en texto y tablas** — texto legible, headers, tablas markdown
  excelentes (cabeceras + valores), OCR de escaneados, 6-13% duplicación.
- **Docling**: texto narrativo limpio pero pierde el contenido visual (marca
  `<!-- image -->` sin leerlo) y es lento en CPU.
- **Hallazgo clave (MPDT190 / hp005):** las capturas de pantalla de UI con texto
  extraíble — donde vive mucho procedimiento — se **pierden** con LlamaParse y
  Docling en modo estándar (las tratan como imagen). El baseline las capturaba por
  fuerza bruta. → **El modo multimodal de LlamaParse es obligatorio**, no opcional;
  el modo estándar sería una regresión en el contenido visual.
- **Diagramas de flujo decisionales** (MPDT190 pág. 60 — diagrama de la Matriz de
  Control, relevante para hp005): ningún extractor reconstruye la estructura —
  extraen las cajas como texto suelto y pierden las flechas y la jerarquía de
  decisión. Inservible como texto. Requieren **doble vía**: el VLM describe la
  lógica del flujo (para que el bot razone) **+** se adjunta la imagen del
  diagrama en la respuesta al técnico (para que lo vea). Es el test más exigente
  de la tarea #12.

**Decisión (confirmada — tarea #12, 22 mayo 2026):** stack de extracción =
**LlamaParse en modo multimodal** (`parse_mode=parse_page_with_lvm`). El modo
estándar queda descartado. Salvedad estructural: los diagramas de flujo
decisionales exigen "doble vía" obligatoria — ver el resultado abajo.

#### Resultado de la tarea #12 — confirmación del modo multimodal (22 mayo 2026)

`scripts/poc_multimodal.py` ejecutó LlamaParse multimodal
(`parse_page_with_lvm`, VLM = `anthropic-sonnet-4.5`) sobre un excerpt de 9
páginas de MPDT190 (printed 53-61): teclado de edición, los dos diagramas de
flujo decisionales (7.2 Categorías de entrada, 7.3 Categorías de salida) y
capturas UI. Salida en `logs/poc_extraction/visual_MPDT190__llamaparse_lvm_anthropic-sonnet-45.md`.

**Se confirma el modo multimodal como stack.** Frente al estándar es una mejora
cualitativa, no incremental:

- **Texto, tablas, teclados, capturas UI:** limpios y fieles. Donde el estándar
  daba texto sin espacios o tablas falsas, el multimodal produce markdown
  estructurado y legible.
- **Diagramas de flujo:** el estándar los convertía en una tabla de 38-47 filas
  de palabras sueltas — 0% usable. El multimodal los reconstruye como grafos
  `mermaid` con nodos y aristas dirigidas — la lógica de decisión pasa de
  invisible a navegable.

**Salvedad — verificada contra las páginas reales 58 y 60 (`_MPDT190_verify_p65/67.png`).**
En los diagramas de flujo el VLM produce salida *estructurada pero parcialmente
inventada*, lo que es **más peligroso que la ensalada de palabras**: es una
alucinación con apariencia de orden, y ni el bot ni el judge pueden detectarla.

- **Notas al pie inventadas.** Las notas (a)-(h), de letra minúscula en el
  original, salen como una misma frase plausible repetida 7-8 veces verbatim.
  El VLM no pudo leerlas y rellenó.
- **Etiquetas mal leídas.** "REARME" → "REPLICA ARMA"; "ACTIVACIÓN TÉCNICA" →
  "ACTIVACIÓN ESCENA"; cajas con palabras pegadas ("CONTROLLa").
- **Grafo parcialmente incoherente.** Nodos conectores (C1-C13) referenciados
  pero sin definir; subgrafo "ALARMA" colgando suelto.

**Segunda verificación — el otro lado del límite (rango de hp005, PDF 71-78).**
Una segunda pasada multimodal sobre el procedimiento de "coincidencia de dos
detectores" — la respuesta de la pregunta hp005 del eval, en capturas de menú y
texto procedimental — confirma que sobre ese tipo de contenido el multimodal es
**fiel y legible**: las pantallas salen como bloques de código limpios, los
pasos numerados son coherentes, las cajas IMPORTANTE/EN54 se conservan.
Verificado contra las páginas reales 65-66: los únicos errores son misreads
puntuales de etiqueta ("TRANSFERIR FLAG"→"FIJO", "n"→"3 COINCIDENCIA ZONAS"),
sin invención estructural ni notas fabricadas. **La fiabilidad del multimodal es
dependiente del tipo de contenido:** alta en narrativa, tablas, capturas de UI y
teclados; baja en los diagramas — crítica en los flowcharts decisionales densos.

(Matiz de método: hp005 está documentado como un fallo de *retrieval*, no de
extracción — el judge constató que el retrieval trajo chunks de fecha/hora en
vez del procedimiento de coincidencia. El multimodal no moverá hp005; lo moverá
la Fase 1 de retrieval. El test sirve para mapear la extracción, no para
diagnosticar hp005.)

**Tercera verificación — capítulo §7 completo (PDF 68-90, 23 págs).** El test
más representativo: un capítulo real continuo, no páginas sueltas. Narrativa,
decenas de capturas de menú, tablas y cajas de aviso salen fieles y usables, y
la respuesta completa de hp005 (coincidencia de entrada + salida de sirena, con
ejemplo trabajado incluido) queda bien cubierta. Afina el límite de los
diagramas — verificado contra las páginas reales 79-80: el render `mermaid` es
*siempre* una linealización con pérdida. En flujos lineales por naturaleza
(navegación de menús) es adecuada; en diagramas cuyo sentido está en la
estructura no lineal (los tiempos del pulsador ESPERA de 7.8.4, los árboles de
decisión de 7.2/7.3) pierde lo esencial — en los simples de forma silenciosa
(AHJ y NYC salen como grafos idénticos), en los densos con incoherencia e
invención. Donde el manual acompaña el diagrama con prosa explicativa, la prosa
sí se extrae bien y carga la información real (caso 7.8.4).

**Conclusión.** Stack confirmado, pero la "doble vía" que la Fase 1 anticipó
para los diagramas de flujo **deja de ser recomendación y pasa a ser obligatoria**:

1. La re-ingesta debe **detectar las páginas de diagrama de flujo** y marcar sus
   chunks de texto como *baja confianza / orientativos* — nunca fuente citable única.
2. La **imagen del diagrama se adjunta siempre** a la respuesta del técnico.
3. El texto del VLM sirve de andamiaje de navegación ("este diagrama trata de X,
   ramifica en Y"), no de cita textual.

Esto refina el plan, no lo contradice: la tarea #12 demuestra *por qué* la doble
vía es imprescindible y descarta confiar en el texto del VLM para flowcharts.

**Follow-up no bloqueante:** medir el coste real por página de
`parse_page_with_lvm` y compararlo con `parse_page_with_agent` — el presupuesto
de re-proceso (~$250-500) depende del modo final. No afecta a la decisión
arquitectónica: la doble vía es necesaria con cualquier modelo (la alucinación
en flowcharts es un problema de legibilidad del original, no de capacidad del VLM).

#### Arquitectura del pipeline de re-ingesta (decidida sesión 22, 22 mayo 2026)

**Principio — dos etapas con una frontera duradera.** El paso caro, externo e
irreversible es la extracción LlamaParse. Se aísla en una Etapa A cuyo output es
un artefacto duradero; el resto es una Etapa B local, barata y re-ejecutable.
Cualquier fallo de chunking, contexto, embedding o dedup se corrige re-corriendo
la Etapa B — nunca se re-paga LlamaParse. Es la respuesta estructural a "no
repetir el proceso".

```
ETAPA A — Extracción   (cara · externa · se paga UNA vez · artefacto duradero)
  A1  Inventario+dedup   walk del corpus, SHA-256 → manifiesto de archivos
                         únicos (descarta las ~188 copias byte-idénticas)
  A2  Extracción         LlamaParse parse_page_with_agent → JSON por archivo
                         (markdown + imágenes + nº de pág); modelo VLM
                         pendiente del probe representativo
  A3  Store duradero     Supabase Storage, clave = hash + config de extracción
  ───────────────────── frontera duradera ─────────────────────
ETAPA B — Indexación   (barata · local · re-ejecutable infinitas veces)
  B1  Idioma             lingua por bloque markdown (+ regex de marcadores)
  B2  Política idiomas   indexa ES / multilingüe-con-ES / EN-only;
                         registra-sin-indexar PT/FR/IT-only
  B3  Chunking           headers markdown + split por tamaño (techo <8000
                         chars con el blurb); sin partir tablas/procedimientos;
                         section_path (parent-child); page_number del JSON
  B4  Diagramas flujo    el VLM los clasifica en A2 → chunk confidence baja
                         + imagen adjunta (doble vía, tarea #12)
  B5  Metadata           detect_metadata() — interfaz; YAML en Fase 2
  B6  Dedup semántico    NO DESTRUCTIVO — marca duplicate_of, no borra
  B7  Contextual retr.   blurb por chunk (Haiku + prompt caching), cacheado
  B8  Embed + index      Voyage voyage-4-large @1024 · HNSW · tabla chunks_v2
  GATE  recall sobre las 52 preguntas del eval + checks automáticos
  SWAP  RENAME TABLE chunks→chunks_old, chunks_v2→chunks
```

**Decisiones fijadas:**
- **Extracción: LlamaParse `parse_page_with_agent`** — el modo agéntico domina
  a `lvm` (mejor calidad verificada y más barato: 45 vs 60 créd/pág). Modelo VLM
  pendiente del probe representativo. Coste realista del corpus ≈$1.150.
- **Embedding: Voyage `voyage-4-large` @1024 dims** — líder de retrieval
  multilingüe (mayo 2026); 1024 respeta el límite ~2000 del índice HNSW.
- **Dimensión 1024 como contrato** — todos los modelos serios soportan
  Matryoshka; almacenar siempre `vector(1024)` evita migración de schema ante
  un cambio futuro de modelo.
- **Abstracción de proveedor** en el módulo de embedding (`embed(texts,
  input_type)` con adaptadores Voyage/Cohere/OpenAI) — cambiar de modelo es
  config, no reescritura.
- **Store de Etapa A:** Supabase Storage.
- **Reemplazo del corpus:** `chunks_v2` + swap por `RENAME TABLE` — las RPC del
  retriever referencian `chunks` por nombre y siguen válidas sin tocarse.
- **`documents` NO se reconstruye** — `document_registry` es idempotente (hash).
- **`translator.py` se retira** — la política de idiomas indexa EN-only sin traducir.

**Robustez (anti "fallo grave que exija reprocesar"):**
- **Resumable** — estado por archivo; el run multi-día se reanuda.
- **Probe de coste** — antes del run completo, extraer ~150 páginas, medir
  créditos LlamaParse reales y extrapolar. No comprometer 23k páginas a ciegas.
- **Puerta de aceptación** — checks automáticos + recall de las 52 preguntas del
  eval + muestreo humano. Go-live solo pasada la puerta.

**Schema** (`chunks_v2`, migración versionada): añade `language`,
`is_flow_diagram`/`confidence`, `section_path`, `context` (separado de
`content`), `embedding vector(1024)` con índice HNSW.

**Módulos** — `src/reingest/`: `inventory` (A1), `extract` (A2/A3), `language`
(B1/B2), `chunk` (B3), `metadata` (B5), `dedup` (B6), `contextualize` (B7),
`embed`+`index` (B8), `pipeline` (orquestador). `src/ingestion/` se conserva
como referencia hasta que el pipeline nuevo lo sustituya.

**Orden de construcción:** A1 → A2/A3 + probe de coste → [run de extracción tras
visto bueno] → módulos B sobre el store → GATE → SWAP.

### Fase 2 — Escalabilidad pre-M&A

**Objetivo:** que añadir un fabricante cueste 2-3h, no 8-15h. Antes del fabricante ~5.

1. **Externalizar `MODEL_PATTERN` y overrides a YAML** — `config/manufacturers/{nombre}.yaml`. Un no-desarrollador puede editar.
2. **Template de scraping** — framework común; cada fabricante define solo selectores y login.
3. **Migrations versionadas** — `supabase migration`, no SQL ad-hoc.
4. **Corregir atribución de fabricante** — campo separado fabricante real vs distribuidor (ASD = Securiton).

### Fase 3 — Routing + tool use ("agentic RAG" bien entendido)

**Objetivo:** que el pipeline se adapte a la query, sin caer en el loop de agente libre.

1. **Intent classifier / query routing** — rutas catálogo / saludo / técnica /
   cross-brand. Cada ruta su pipeline. Evita que un saludo pague HyDE + 5 búsquedas.
2. **Tool use nativo** — el generador decide cuándo pedir más chunks
   (`search_more`), cuándo clarificar, cuándo cerrar. Límite 3 iteraciones.
3. **Memoria conversacional** — resumen del historial reciente del técnico.
   Resuelve "varias preguntas sobre un manual / saltar de manual a manual".

### Fase 4 — Eval orgánico + CI

1. **Tier 2 DG-grade** — curar 20-30 queries reales de los DGs desde `query_logs`,
   marcadas `verified: true`.
2. **Calibración inversa con los DGs** — que validen una muestra de veredictos del judge.
3. **CI con eval automático** — cada PR ejecuta el eval; bloquea merge si regresión.

### Fase 5 — Técnicos reales (post 1-septiembre)

1. **Tier 3 field-grade** — queries reales de técnicos en obra (jerga, voz, typos).
2. **Eval multi-turno** — diálogos de 2-3 turnos.
3. **Validación técnica de golds pendientes** — los que necesitan un técnico PCI
   (p. ej. hp004: ¿el DGD-600 a 220V es AC o DC?).

### Orden y dependencias

```
Fase 0 ──> Fase 1 ──> Fase 2 ──> Fase 3 ──> Fase 4 ──> Fase 5
(métrica)  (calidad)  (escala)   (routing)  (CI)       (campo)
   │                                                     ▲
   └── sin métrica fiable, el resto se mide a ciegas ─────┘
```

Fase 0 es prerrequisito de todo. Fase 1 antes que Fase 2 (calidad antes que
escala). Fase 3 nunca antes que Fase 1 (no tiene sentido un agente sofisticado
sobre un retrieval roto). Fases 4-5 dependen de deploy a DGs y de 1-sept.

**Refinamiento del orden Fase 0 ↔ Fase 1 (22 mayo 2026, tras la tarea #12).**
La frontera Fase 0 / Fase 1 se ordena por *dependencia de datos*, no por número
de fase. Las gold answers de la Fase 0 se generan a partir de la extracción del
corpus: generarlas sobre la extracción actual — rota, demostrado en el PoC y la
tarea #12 — las haría heredar sus puntos ciegos (contenido de diagramas y
capturas perdido). Sería repetir la lección central de la Fase 0: *un evaluador
es tan fiable como la integridad de su input*. Secuencia real:

1. **Paralelo, ya** — judge v2 *código* (cross-model, verificación de citación,
   secciones F/V) + fix del truncado. Es código: no depende del corpus.
2. **Re-ingesta** — extracción multimodal + contextual retrieval en una pasada.
   Se valida por inspección directa; no necesita el eval.
3. **Gold answers + holdout + calibración humana** — sobre el corpus ya
   re-ingestado. Se generan una sola vez, sobre datos correctos.
4. **Tuning de retrieval** (BM25+RRF, reranker dedicado, top_k split) — medido
   contra la métrica ya fiable del paso 3.

El espíritu se respeta: el *tuning de retrieval* no se toca sin métrica fiable.
Se corrige solo la imprecisión de "Fase 0 entera antes que Fase 1 entera".

---

## 5. El judge v2 — arquitectura

El judge actual evalúa "bot vs chunks F" — alcance demasiado estrecho. El judge v2
tiene **tres capas**:

**Capa A — Gold answers versionadas.** Una respuesta canónica por pregunta,
generada por un LLM fuerte **con extracción programática del PDF** (no de memoria
— el sesgo de "citar de memoria" produjo 6 errores de gold en la Fase 0),
validada por humano en muestra, almacenada con cita exacta (manual + página). Se
regeneran cuando cambia el corpus.

**Capa B — Judge operativo cross-model.** Un LLM distinto del generador y del
generador del gold. Evalúa en **dos ejes separados**:
- *Faithfulness vs chunks F* — ¿el bot fue fiel a lo que recibió?
  - Sub-capa determinista: datos duros (verify_citations.py — ya prototipado).
  - Sub-capa LLM atómica: claims cualitativos, un claim contra un chunk, temp=0.
- *Correctness + completitud vs gold* — ¿el bot dio la mejor respuesta posible?
- Y reporta **retrieval recall** por separado: ¿los chunks que el gold necesita
  estaban en F? — distingue fallo de retrieval de fallo de generación.

**Capa C — Calibración humana periódica.** Holdout split (~10 calibration / ~42
eval). Mide agreement judge↔humano. Se rehace cuando el judge cambia.

**Principio:** la fiabilidad viene del **determinismo y de la independencia**, no
del modelo más potente. La Fase 0 demostró que un LLM más capaz (Opus) con input
incompleto falla; una búsqueda de texto determinista sobre el input completo no.

---

## 6. Recomendaciones de Cowork — qué se acepta y qué se corrige

El documento `rag_improvements_recommendations.md` es sólido en diagnóstico
general. Evaluado punto por punto:

**Se acepta (converge con la auditoría):**
- Extracción de tablas mala (falsos `[TABLA EXTRAÍDA]`). → Fase 1.
- Híbrida BM25 + embeddings + reranker. → Fase 1.
- Headers semánticos + parent-child retrieval. → Fase 1.
- Recalibraciones de YAML sospechosas. → Fase 1, verificado.
- Separar evaluación de retrieval vs generación. → judge v2, Capa B.
- Cambiar la métrica primaria a agreement con humano. → Fase 0.

**Se corrige (premisa falsa):**
- ❌ Patrón "G7 — fabricación citacional", basado en hp010/hp011. La verificación
  determinista demostró 0 invención citacional. hp010/hp011 eran artefacto del
  truncado. **El patrón G7 se elimina.**
- ⚠️ Recomendación "groundedness check post-generación con Haiku" — es una variante
  del validador post-generación que **ya se probó y se revirtió** (TECH_DEBT #11i,
  net-negativo). La variante barata estructural (verificación de citación
  determinista) sí — ya está en el judge v2. La variante LLM, no.
- ⚠️ "Revertir recalibraciones de YAML" — correcto en intención, pero verificar
  SIEMPRE contra el corpus antes de revertir. hp006/cm001/cm005 verificados; el
  resto no asumir.

**Falta en el documento de Cowork (lo añade este plan):**
- Contextual retrieval (Anthropic sept 2024).
- Escalabilidad a 30+ fabricantes (todo el documento es calidad, nada de estructura).
- El prompt monolítico del generator.
- El historial del proyecto (qué ya se probó y falló).

---

## 7. Lo que NO hay que hacer (anti-patrones)

- **Validador post-generación con LLM** — ya falló (TECH_DEBT #11i). La evidencia
  dice que la alucinación no es el cuello de botella; el retrieval sí.
- **Recalibrar el YAML para "tapar" un fallo de retrieval** — sube el PASS y baja
  la calidad real. Antes de cambiar `answer → admit_no_info`, verificar el corpus.
- **Confiar en una métrica sin calibrar** contra una referencia externa al menos
  una vez.
- **Evaluar sobre representaciones intermedias** (un `.md` que puede truncarse) en
  vez de la fuente canónica completa.
- **Reescribir desde cero** — la estructura del retriever híbrido es buena; los
  cambios son ortogonales a lo que funciona.
- **Quick fixes por fabricante** — cada parche hardcoded multiplica por 30.

## 8. Principios de trabajo para las próximas sesiones

1. **Contrato BP + estructural + escalable** — toda propuesta se valida contra los
   tres criterios *antes* de proponerla, y se declara el resultado.
2. **Eval-driven** — ningún cambio se da por bueno sin medir delta. Pero la
   métrica tiene que ser fiable primero (Fase 0).
3. **Verificar la cadena entera antes de concluir** — la Fase 0 enseñó que una
   conclusión ("X falló") sin verificar el input puede ser falsa. Verificar primero.
4. **Determinismo donde se pueda, LLM solo donde haga falta** — los hechos se
   verifican con código; el lenguaje, con LLM en tareas acotadas.
5. **No legacy** — si un desarrollo no cumple el contrato, se rehace. No se
   acumula deuda para "ya lo arreglaremos".

---

## Changelog

- **22 mayo 2026** — Documento creado. Consolida auditoría inicial + calibración
  Cowork + hallazgos de Fase 0 (bug de truncado, verificación documental,
  verificación de citación 100% en datos duros).
- **22 mayo 2026** — Añadido a la Fase 1: diagnóstico del corpus (1.208 PDFs, 47%
  con carga visual densa, ~188 duplicados) y las 6 decisiones de diseño del
  pipeline de re-ingesta, incluida la política de idiomas.
- **22 mayo 2026** — Añadido el resultado del PoC de extracción: baseline a
  sustituir (pierde espacios, falsea tablas), LlamaParse en modo multimodal como
  stack elegido (pendiente confirmar modo multimodal — tarea #12).
- **22 mayo 2026** — Tarea #12 cerrada: confirmado el modo multimodal de
  LlamaParse (`parse_page_with_lvm`) como stack de extracción. Salvedad: en
  diagramas de flujo el VLM alucina (notas inventadas, etiquetas mal leídas),
  verificado contra las páginas reales — la "doble vía" texto+imagen pasa de
  recomendada a obligatoria.
- **22 mayo 2026** — §4: refinado el orden Fase 0 ↔ Fase 1 — secuenciar por
  dependencia de datos. La re-ingesta precede a las gold answers (que heredarían
  los puntos ciegos de la extracción si se generan antes). El judge v2 *código*
  va en paralelo; el tuning de retrieval sigue esperando a la métrica fiable.
- **22 mayo 2026** — Fase 1: fijada la arquitectura del pipeline de re-ingesta
  (dos etapas con frontera duradera) y el modelo de embedding (Voyage
  `voyage-4-large` @1024, con dimensión-contrato y abstracción de proveedor).
  Arranca la construcción por la Etapa A1 (inventario + dedup nivel 1).
- **22 mayo 2026** — Fase 1: coste de extracción medido (dashboard LlamaParse):
  estándar 3 créd/pág, agéntico 45, `lvm` 60. **`lvm` descartado** — dominado
  por el modo agéntico (mejor calidad verificada *y* más barato). Modo de
  extracción fijado = `parse_page_with_agent`; presupuesto realista ≈$1.150
  (no $250-500). El modelo VLM se decidirá con un probe representativo (~150
  págs) — los single-runs de 9 págs no son base fiable. Construido el módulo
  A2/A3 (`src/reingest/extract.py`).
- **22 mayo 2026** — Probe cerrado, decisión de extracción fijada: **agéntico en
  todo el corpus** (`parse_page_with_agent`), ≈$1.150 pago único. Se exploró y
  descartó el enfoque por niveles (estándar barato + agéntico solo en lo
  difícil): verificado que el modo estándar **corrompe silenciosamente** las
  tablas de marcas ✓ — la VESDA Tabla 7-1 salió con 0/7 marcas y confianza 0,96
  (parece correcta, es falsa); el agéntico, 7/7. Los fallos silenciosos no los
  caza ningún router barato (confianza, word-salad, agregación por documento —
  los tres fallan en pruebas). Para un corpus de seguridad, agéntico-en-todo es
  la única opción sin errores silenciosos. El run completo requiere plan de pago
  de LlamaParse (supera el free tier de 10k créd/mes).
- **22 mayo 2026** — Cierre de sesión 22. Alberto contrató el Plan Pro de
  LlamaParse → run de extracción completo desbloqueado. Próxima sesión: lanzar
  el run agéntico completo (background, resumable) + construir la Etapa B
  (idioma, chunking, contextual retrieval, embed Voyage + HNSW `chunks_v2`).
