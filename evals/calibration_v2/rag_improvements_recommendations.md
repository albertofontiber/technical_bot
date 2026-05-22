# Recomendaciones para mejorar el Technical Bot — Auditoría sobre 52 casos

**Fecha:** 21 de mayo de 2026
**Base:** calibración manual + Claude de las 52 preguntas del eval `eval_20260502T152857Z.json`
**Estructura:** patrones detectados → remedios por capa → priorización por ROI

---

## Resumen ejecutivo

El bot reporta **51/52 PASS (98%)** con el judge actual, pero la calibración revela que **al menos 7-10 casos son falsos PASS** o problemas estructurales no detectados por el judge. La métrica `% PASS` está **sobreestimada por entre 15-20 puntos** porque el judge solo evalúa "bot vs F" sin verificar:

1. **Completitud objetiva** vs el manual completo (no solo los chunks F que vio el bot).
2. **Calidad del retrieval** (qué chunks faltaron y por qué).
3. **Calidad de la extracción de chunks** (errores en `[TABLA EXTRAÍDA]`, headers fragmentarios, mismatch metadata-contenido).
4. **Recalibraciones del YAML** legítimas vs enmascaramiento de fallos.

El ROI más alto está en **(a) arreglar la extracción de chunks** (PDFs → tablas y headers), **(b) ampliar el retrieval con BM25 y rerank**, y **(c) auditar las recalibraciones del YAML** anteriores.

---

## 1. Patrones sistémicos detectados (con frecuencia)

Recopilados a partir de la calibración cruzada de los 5 archivos del eval (hp001-020, am001-008, mc001-008, nd001-008, cm001-008).

### 1.1. Extracción de PDFs

| # | Patrón | Frecuencia | Casos donde aparece |
|---|---|---|---|
| E1 | **`[TABLA EXTRAÍDA]` aplicado a texto plano (falso positivo)** | ≥12 casos | hp002, hp003, hp005, hp006, hp008, mc001, mc005, nd001, nd008, am006… |
| E2 | **Tabla real sin marcador `[TABLA EXTRAÍDA]` (falso negativo)** | ≥8 casos | hp002 (F4), hp007 (Tabla 7-1), hp005 (tabla "Indique tipo de coincidencia")… |
| E3 | **Headers de chunks que son fragmentos arbitrarios** (no epígrafes) | endémico | hp001 (F2/F3), hp008 (F3/F4/F5), nd casos, am casos |
| E4 | **Mismatch metadata sección vs contenido**: chunk dice "sec 2.4" pero contiene sec 2.3 | ≥5 casos | hp003 (F1 dice "2.4" trae "2.5"; F4 dice "2.4" trae 2.3.10-12), cm007 (metadata "B501" pero contenido CPX-751E) |
| E5 | **Chunking que parte una sección por la mitad** y deja fuera la pieza clave | ≥8 casos | hp001 (OTROS/REINICIAR cortados), hp005 (pantalla "COINCIDENCIA 2 EQUIPOS" justo fuera de F1), hp006 (Falla de Tierra + JP2) |
| E6 | **Marcadores de continuación rotos**: "(continuación)" en headers sin contexto del original | ≥6 casos | F1/F2 de hp004, F3 de hp006 |

### 1.2. Retrieval

| # | Patrón | Frecuencia | Casos |
|---|---|---|---|
| R1 | **Duplicación masiva** (mismo contenido en F1+F2+...+F5) | ≥10 casos | hp004 (5/5 chunks de p.1), hp007 (4/5 de pág. 87), nd005/007/008 (3-4× repetidos) |
| R2 | **Asimetría cross-brand** (4-5 chunks de un fabricante, 0-1 del otro cuando la pregunta requiere combinar) | ≥4 casos | cm004, cm006, cm007 |
| R3 | **Cross-product contamination**: la query "ASD" trae chunks de productos no-ASD que comparten términos genéricos | hp012, hp019, am004, am007 |
| R4 | **Cross-language sin filtro**: chunks en EN/IT/PT/NL cuando la query es ES | hp011 (4 idiomas), hp020 (PT), am005 (NL FAAST XM) |
| R5 | **Inestabilidad entre queries casi idénticas**: hp009 y hp018 mismo manual sec. 3.4.4; uno lo recupera sim 0.83, el otro no entra en top-5 | hp009/hp018 |
| R6 | **Inestabilidad entre interfaces**: la misma query en Telegram vs eval devuelve chunks completamente distintos y a veces respuestas opuestas ("no tengo info" vs respuesta completa) | hp003, hp005, hp002 |
| R7 | **Retrieval miss aún con info en corpus**: la info SÍ existe pero no entra en top-k | hp001 (sec 5.3 contraseña), hp005 (sec 7.6.1.1 pantalla coincidencia), hp006 ("Falla de Tierra" en 50253SP) |
| R8 | **Apéndices sistemáticamente fuera del top-k** (aparecen al final del manual) | hp007 (Apéndice A formularios), hp008 (Apéndice C compatibles) |

### 1.3. Metadatos y catalogación

| # | Patrón | Frecuencia | Casos |
|---|---|---|---|
| M1 | **Atribución de fabricante incorrecta**: producto del fabricante X marcado como del distribuidor Y | hp002 (ASD535 = Securiton, no Detnov), hp019 (ASD Detnov→Securiton) |
| M2 | **Familia de modelo ambigua sin estructura**: CAD-150 vs CAD-150-2/4/8; bot no clarifica variante | hp003 (1/2/4/8 lazos no diferenciados) |
| M3 | **Metadata `unknown` en `brand`/`product_model`** debilita capacidad de filtrar/sugerir candidatos | am003, am004, am006 (Morley Dimension marcado `unknown`) |
| M4 | **Documentos clave del corpus no indexados o no priorizados**: guía Honeywell de compatibilidad Notifier↔Morley no se usa para preguntas cross-brand | cm001, cm005, cm006 |
| M5 | **Cobertura visual perdida** (diagramas, esquemas, capturas de pantalla): páginas 11-33 de CAD-150-8 con diagramas no capturados | hp003, hp005 (capturas de UI de central) |

### 1.4. Generación y citación

| # | Patrón | Frecuencia | Casos |
|---|---|---|---|
| G1 | **Numeración de citas para usuario**: bot cita "F3" sin "F1, F2" — confunde al técnico que solo ve la respuesta | hp004, hp005 (mencionado por Alberto) |
| G2 | **Corchetes desaparecen en Telegram**: "F1" en vez de "[F1]" por interpretación Markdown | hp002, hp003, hp004 |
| G3 | **Premisa errónea no desafiada**: bot acepta presupuestos arquitectónicamente imposibles | hp013 (ADW535 "batería tampón"), hp015 (CCD-103 "desactivar detector"), hp016 (B501RF "detector"→base), hp019 |
| G4 | **Inversión de polaridad / restricción invertida**: el manual dice "X solo disponible para Y" y el bot lo genera como "X no disponible para Y" | hp005 (Optiplex/SMART) |
| G5 | **Reordenación de pasos vs manual**: bot reordena pasos (a veces justificadamente, a veces no) sin avisar | hp002 (orden de medición vs inspección) |
| G6 | **Padding con chunks tangenciales**: para parecer completo, el bot mete información de un chunk relacionado pero no específico | hp005 (Pulsante SÍ/NO en pregunta de coincidencia) |
| G7 | **Citación múltiple errónea**: una afirmación se atribuye a F5 cuando viene de F1 | hp002 (Telegram) |
| G8 | **Híbrido "answer-then-clarify"** confunde al clasificador de behavior | mc006 |

### 1.5. Eval y YAML

| # | Patrón | Frecuencia | Casos |
|---|---|---|---|
| Y1 | **Recalibrado YAML que enmascara fallos de retrieval**: cambiaron `answer → admit_no_info` sin verificar si la info existe en el corpus | hp006 ("Falla de Tierra" SÍ existe en 50253SP), cm001, cm006 (guía Honeywell SÍ existe) |
| Y2 | **Keywords frágiles**: el bot usa sinónimos legítimos no anticipados ("V CC" vs "vdc"; "videovigilancia" vs "cctv"; "grupos de presión contra incendios" vs regex `grupo presión`) | hp004, nd006, nd007 |
| Y3 | **Clasificador de `observed_behavior` mal calibrado**: etiqueta por presencia de "?" final ignorando contenido afirmativo previo | mc006 (BUG real) |
| Y4 | **Categoría `not_in_db` es la única limpia**: 8/8 legítimos. Útil como benchmark de "judge funcionando bien" | nd001-008 |

---

## 2. Recomendaciones por capa

Estructura de prioridad (ROI): **alta → media → baja**. Cada recomendación incluye qué patrones aborda.

### 2.1. Capa de extracción (PDFs → chunks)

**Prioridad ALTA**

1. **Sustituir el extractor de tablas actual por uno layout-aware**: el patrón E1/E2 indica que el detector de tablas tiene falsos positivos Y falsos negativos. Considerar:
   - **Unstructured.io** con `strategy="hi_res"` (usa visión)
   - **Marker** (PDFs → Markdown con detección de tablas integrada)
   - **Azure Document Intelligence** o **AWS Textract** (servicios pagos pero robustos para PDFs técnicos)
   - **ColPali / ColQwen** para indexar páginas visuales completas (especialmente útil para capturas de pantalla de UI de centrales)
   - *Aborda: E1, E2, M5*

2. **Headers semánticos en lugar de "primera línea no vacía"**: el patrón E3 indica que el extractor toma cualquier fragmento como header. Reemplazar por detección de jerarquía:
   - Reconocer numeración `\d+(\.\d+)+` como header
   - Reconocer estilos tipográficos del PDF (font size, bold)
   - Conservar **breadcrumb** completo: `Capítulo 5 > 5.4 AVANZADO > Pestaña OTROS`
   - *Aborda: E3, E4*

3. **Chunking por sección semántica, no por longitud fija**:
   - Cada sección con su numeración como unidad atómica
   - Si excede tamaño máximo, partir por subsección, no por caracteres
   - **Sticky warnings**: cualquier chunk con `EN54`, `PRECAUCIÓN`, `IMPORTANTE`, `Nota` se adhiere al chunk de procedimiento más cercano de la misma sección
   - *Aborda: E5*

4. **Parent-child retrieval (auto-merging)**:
   - Indexar chunks pequeños para precisión de búsqueda
   - Devolver el chunk padre (sección completa) al LLM
   - Resuelve el problema de "chunk parte sección por la mitad"
   - *Aborda: E5, E6*

**Prioridad MEDIA**

5. **De-duplicación post-extracción**: el patrón R1 indica que el extractor produce el mismo chunk N veces con micro-variaciones. Aplicar un de-dup por similitud (cosine > 0.95) o por hash de contenido normalizado.

6. **Auditoría manual de PDFs problemáticos**:
   - MIDT170/MFDT170/MPDT170/MADT170/50253SP (AFP-300/400) — chunks fragmentados, tablas mal extraídas
   - MPDT190 (ID3000) — pantallas de UI partidas
   - VESDA-E VEP-A10/A00 — Tabla 7-1 sin marcas
   - CAD-150-8 (3 manuales) — diagramas no capturados
   - MIE-MI-600 / MIE-MI-530 (Morley ZXSe/ZXe)

### 2.2. Capa de retrieval

**Prioridad ALTA**

7. **Híbrida BM25 + embeddings con reranker**:
   - BM25 captura términos exactos del dominio que los embeddings pierden: `COINCIDENCIA 2 EQUIPOS`, `Falla de Tierra`, `JP2`, números de sección
   - Embeddings capturan semántica para queries parafraseadas
   - Reranker (Cohere Rerank multilingüe, BGE-reranker-v2-m3) sobre los top-50 hits para devolver top-5 limpios
   - *Aborda: R7, R8, hp001 contraseña, hp005 coincidencia, hp006 falla de tierra*

8. **Adaptive retrieval por tipo de query**:
   - Query clasificada en `lookup_simple` (un dato puntual), `procedure` (paso a paso), `compatibility` (cross-product/brand), `troubleshooting` (síntoma → causa)
   - Cada tipo activa parámetros de retrieval distintos (top-k, expansión de query, fuentes priorizadas)
   - *Aborda: R3, R7*

9. **Query expansion sistemática con sinónimos del dominio PCI**:
   - Tabla de sinónimos: `coincidencia ⇔ double knock ⇔ doble detección ⇔ 2 equipos ⇔ confirmación cruzada`
   - `tierra ⇔ Falla de Tierra ⇔ Fallo de Tierra ⇔ Earth Fault ⇔ derivación a tierra`
   - `prueba de humo ⇔ smoke test ⇔ commissioning test ⇔ aerosol test`
   - Generada y mantenida por el equipo, no auto-aprendida (riesgo de drift)
   - *Aborda: R7, Y2*

**Prioridad MEDIA**

10. **Filtro/boost por idioma de la query**:
    - Si query es ES → priorizar chunks `lang=es`, penalizar `lang∈{en, it, pt, nl, fr}` salvo que la query mencione un manual específico en otro idioma
    - *Aborda: R4*

11. **Filtro/boost por marca/modelo detectado en la query**:
    - Si el usuario menciona "ID3000" → priorizar chunks con `product_model=ID3000`
    - Manejar familias: query "CAD-150" debe traer todos los CAD-150-X con flag de "modelo no especificado, sugerir clarificación"
    - *Aborda: R3, M2*

12. **Detección automática de queries multi-manual y boost cross-doc**:
    - Si la query menciona dos marcas/modelos → activar retrieval con un mínimo por cada uno (p.ej., 2 chunks de cada)
    - Boost específico al documento `Compatibilidad-entre-equipos-Notifier-y-Morley.pdf` cuando la query es cross-brand intra-Honeywell
    - *Aborda: R2, M4, cm001, cm006*

**Prioridad BAJA**

13. **Cross-reference graph**:
    - Parsear referencias "Sección X.Y" y "Apéndice Z" como aristas
    - En retrieval, si un chunk top-5 referencia "Sección 11.21", añadir el chunk de esa sección al contexto
    - *Aborda: R7 multi-hop*

14. **Determinismo / reproducibilidad**:
    - Si el retrieval depende de embeddings con temperature, fijar seed o usar embeddings deterministas
    - Si la base vectorial tiene HNSW, fijar `ef_search`
    - El patrón R6 sugiere que distintas llamadas devuelven distintos top-k
    - *Aborda: R5, R6*

### 2.3. Capa de generación

**Prioridad ALTA**

15. **Groundedness check post-generación** (paso de verificación):
    - Para cada afirmación factual de la respuesta, un modelo barato (Haiku) etiqueta "soportado / no soportado" contra los F
    - Si % no-soportado > umbral → revisar/reescribir
    - Habría cazado G4 (inversión Optiplex) y G3 (premisas erróneas)
    - *Aborda: G3, G4, G6, G7*

16. **Reglas explícitas en el prompt del generador**:
    - "Una afirmación = un único F que la soporte de forma exacta; no atribuir a múltiples F sin que cada uno la soporte"
    - "Si recibes chunks con marcador `EN54`, `PRECAUCIÓN`, `IMPORTANTE` → son **obligatorios** en la respuesta"
    - "Si una premisa de la pregunta es arquitectónicamente cuestionable, **señálalo antes de responder** (ej. 'el ADW no usa batería tampón porque...')"
    - "**No reordenes pasos** del manual a menos que el cambio sea necesario por dependencia explícita"
    - *Aborda: G3, G4, G5, G7*

17. **No-handoff rule**: si la respuesta sugiere "consulta otro manual", verificar primero (con un retrieval de 2ª vuelta) que el contenido no está en otros chunks del corpus actual.
    - *Aborda: hp005, hp006, R7*

**Prioridad MEDIA**

18. **Numeración de citas normalizada para el usuario**:
    - Renumerar los F citados en la respuesta como F1..Fn según el orden de uso, no el rank original
    - Ejemplo: si el bot solo usa lo que internamente es F3, debe presentárselo al usuario como [F1]
    - *Aborda: G1*

19. **Escapado/sustitución de corchetes para Telegram**:
    - Bug del render: `[F1]` se interpreta como link incompleto y desaparece
    - Solución: usar `(F1)`, `«F1»`, `<F1>`, o asegurar que el cliente Markdown renderiza bien
    - Probar en cada cliente (Telegram, web, etc.)
    - *Aborda: G2*

20. **Política multi-manual intra-grupo más permisiva**:
    - Hoy: política "no inferir cross-brand" bloquea respuestas que SÍ están soportadas por documentos oficiales (caso cm001, cm006 con guía Honeywell)
    - Cambio: permitir inferencia cross-brand cuando hay documento oficial del grupo que zanja la pregunta
    - *Aborda: M4, recalibrados ilegítimos en cm/hp006*

### 2.4. Capa de eval y judge

**Prioridad ALTA**

21. **Auditar y revertir recalibraciones ilegítimas del YAML**:
    - hp006: `answer → admit_no_info` se hizo asumiendo que "Earth Fault" no está en AFP-300/400. **Está como "Falla de Tierra"**. Revertir a `answer`.
    - cm001 (SDX-751 + Morley ZXe): existe guía Honeywell oficial. Recalibración ilegítima. Revertir.
    - cm006 (aislador Detnov + ID3000): mismo caso. Revertir.
    - cm005 (red ID3000 + DXc): mismo caso. Revisar.
    - *Aborda: Y1*

22. **Bug del clasificador `observed_behavior`** (no es bug del judge):
    - Reemplazar la heurística actual (probablemente "termina en `?`") por una llamada LLM que clasifica observada(answer/clarify/admit_no_info) leyendo el cuerpo de la respuesta
    - *Aborda: Y3, mc006*

23. **Métrica primaria pasa a ser `judge_agreement_con_humano`**, no `% PASS`:
    - El `% PASS = 98%` actual está inflado.
    - Con la calibración de los 52 casos, calcular `agreement_rate` por categoría: si la calibración Alberto+Claude difiere del judge en X casos, agreement = (52-X)/52.
    - Reportar agreement por dimensión: faithful, helpful, behavior_match…
    - *Aborda: Y4 y el sesgo general del eval*

**Prioridad MEDIA**

24. **Holdout split**:
    - Mover ~10 casos calibrados a `calibration_set.yaml` (para tunear el prompt del judge)
    - Mantener ~42 en `eval_set.yaml` (nunca se toca su `expected_behavior`)
    - Reportar métricas siempre en el `eval_set`, no en el `calibration_set`
    - Esto está alineado con el plan del README

25. **Keyword YAML como lista OR-extensible**:
    - Hoy: `expected_keywords: ['vdc']` falla cuando el manual dice `V CC`
    - Mejor: `expected_keywords: [{'or': ['vdc', 'V CC', 'V cc', 'voltios CC']}]`
    - O bien aceptar sinónimos semánticos vía embedding sobre las keywords
    - *Aborda: Y2*

26. **Tests adversarios específicos en el eval**:
    - **Inversión de polaridad** (G4): preguntas donde el manual dice "X solo para Y"; el bot debe inferir el sentido positivo, no invertirlo
    - **Premisa errónea** (G3): preguntas con presupuestos imposibles ("¿cómo cambio la batería del ADW535?" — el ADW no tiene batería); el bot debe educar al técnico
    - **Cobertura de pasos**: para procedimentales, ¿menciona los 4-5 pasos clave?
    - **Cobertura de advertencias**: ¿menciona el aviso normativo EN54?
    - *Aborda: G3, G4*

**Prioridad BAJA**

27. **Visualización de patrones por categoría** en un dashboard:
    - % faithful, % helpful, % behavior_match por categoría (happy_path / ambiguous_model / missing_context / not_in_db / cross_manual)
    - Permite ver dónde el bot funciona y dónde falla

---

## 3. Priorización combinada (top 10 acciones)

Ordenadas por impacto estimado en `judge_agreement_con_humano` (medible) × esfuerzo de implementación:

| # | Acción | Capa | Esfuerzo | Impacto | Patrones |
|---|---|---|---|---|---|
| 1 | Sustituir extractor de tablas (Unstructured hi_res, Marker, Azure DI, o ColPali) | Extracción | M-A | A | E1, E2, M5 |
| 2 | Híbrida BM25 + embeddings + reranker | Retrieval | M | A | R1, R3, R7, R8 |
| 3 | Headers semánticos + parent-child retrieval | Extracción | M | A | E3, E4, E5 |
| 4 | Auditar y revertir recalibraciones ilegítimas (hp006, cm001, cm006…) | Eval/YAML | B | A | Y1 |
| 5 | Groundedness check post-generación con Haiku | Generación | B | M-A | G3, G4 |
| 6 | Query expansion con tabla de sinónimos del dominio PCI | Retrieval | B | M | R7, Y2 |
| 7 | Fix del clasificador de `observed_behavior` (LLM en vez de heurística) | Eval | B | M | Y3 |
| 8 | Política multi-manual: priorizar guía Honeywell de compatibilidad | Retrieval/Política | B | M | M4 |
| 9 | Reglas de generación: una afirmación = un F; no reordenar pasos | Generación | B | M | G5, G7 |
| 10 | Cambiar métrica primaria a `judge_agreement_con_humano` | Eval | B | A (estratégico) | Y4 |

**Esfuerzo:** B=bajo (<1 sprint), M=medio (1-2 sprints), A=alto (>2 sprints).
**Impacto:** B=mejora <5 pp en agreement; M=5-15 pp; A=>15 pp.

---

## 4. Casos paradigmáticos para reusar como test stress

Estos 5 casos cubren la mayoría de los patrones; conviene usarlos como sanity test después de cada cambio:

1. **hp001 (CAD-250 menú AVANZADO)** — test de retrieval que recupera media sección y deja la otra fuera. Métrica: ¿menciona la pestaña OTROS desarrollada (no solo el nombre)?
2. **hp005 (ID3000 coincidencia 2 detectores)** — test de retrieval que pierde el chunk crítico ("Indique tipo de coincidencia"). Métrica: ¿menciona la opción literal "2: COINCIDENCIA 2 EQUIPOS"?
3. **hp006 (AFP-400 Earth Fault)** — test de recalibración YAML ilegítima. Métrica: tras revertir el YAML a `answer`, ¿el bot responde con LED Falla de Tierra + JP2?
4. **hp007 (VESDA-E test anual)** — test de extracción de tabla (Tabla 7-1 con marcas). Métrica: ¿enumera las 4 tareas anuales (no solo las 7 totales)?
5. **cm006 (aislador Detnov + ID3000)** — test de política cross-brand intra-Honeywell. Métrica: tras priorizar la guía Honeywell, ¿el bot responde con "no compatible" cerrado?

---

## 5. Lo que NO se debe hacer

Lecciones aprendidas durante la calibración para evitar regresiones:

- ❌ **No recalibrar el YAML para "tapar" un fallo de retrieval**. Antes de cambiar `answer → admit_no_info`, grepea el corpus completo para verificar que la info de verdad no está.
- ❌ **No confiar en `% PASS` como indicador de salud del bot**. El judge tiene blind spots compartidos con el generator (ambos Sonnet 4.6).
- ❌ **No descartar `keyword=FAIL ∧ judge=PASS` automáticamente como "judge lenient"**. En muchos casos es keyword frágil (sinónimo legítimo) o retrieval miss (info no llegó al bot).
- ❌ **No usar `observed_behavior` heurístico** (clasificación por presencia de `?` u otros marcadores superficiales). Usar el propio LLM.
- ❌ **No tratar los chunks como verdad absoluta**: muchos chunks tienen contenido pero metadata corrupta (sección X dice "Y", contenido es "Z"). Validar antes de citar.

---

## 6. Siguiente paso operativo

1. **Revisar y validar** este documento con el equipo.
2. **Priorizar las 10 acciones** de la sección 3 según capacidad del equipo en el próximo sprint.
3. **Re-procesar el eval** después de cada cambio significativo y medir `judge_agreement_con_humano` contra la calibración guardada en `evals/calibration_v2/`.
4. **Crear el holdout split** (`calibration_set.yaml` ~10 casos + `eval_set.yaml` ~42 casos) para no contaminar la métrica.
5. **Iterar**: cada release del bot debe ir acompañada del agreement rate medido sobre el `eval_set`, no del `% PASS`.

---

## Fuentes

- Calibración manual de Alberto sobre `01_happy_path.md` (hp001-hp007).
- Calibración Claude sobre los 52 casos (hp001-hp020, am001-am008, mc001-mc008, nd001-nd008, cm001-cm008).
- Gold answers de referencia:
  - `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Projects\PCI\gold_answer_earth_fault_AFP400.md`
  - `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Projects\PCI\gold_answer_VESDA_VEP_annual_test.md`
- Log del eval del 2 de mayo de 2026: `logs/eval_20260502T152857Z.json`.
- Guía oficial Honeywell de compatibilidad: `Manuales_Morley_Guias/Compatibilidad-entre-equipos-Notifier-y-Morley.pdf` (referenciada por subagente de cm).
