# Contrato de gobernanza — Catálogo canónico de identidad de producto (workstream A, Fase 0)

> **Estado: DRAFT para revisión de Alberto (~1h).** Deliverable de la Fase 0 de (A) (DEC-074e).
> Al aprobarse (con tus decisiones D1-D6 de §9), pasa a CANÓNICO y gobierna las fases F1-F4.
> Nace de: DEC-074(c) (BP = entity-linking 2 etapas, dúo + literatura arXiv 2502.01555 /
> EVPI-CLAM 2212.07769), el activo s83 (DEC-067: 1014 docs / 2761 productos dúo-extraídos +
> tus 29 adjudicaciones), TECH_DEBT #49/#50, y los ground-truths tuyos (Morley ZX/RP1r,
> FAAST, CAD-150 — `memory/reference_*.md`).

## 1. Qué es (y qué NO es)

**ES:** la fuente única y GOBERNADA de identidad de producto del sistema — qué productos existen,
cómo se llaman canónicamente, qué alias/paraguas/familias tienen, qué marca los vende y quién los
fabrica (OEM), y qué documentos hablan de cada uno. Consumida por: resolución query-side (retriever),
gate del handler, re-tag de `chunks_v2.product_model`, e ingesta futura (30+).

**NO ES:** (a) un lever de PASS del eval — la palanca medida es ~4 retrieval-miss (hp018, DEC-074);
su valor es **escala-30+ / findability / corrección** (cimiento). (b) Un filtro que "adivina" en
ambigüedad — la política es resolver determinista, y ante ambigüedad REAL con divergencia,
**clarify** (s79/s80). (c) Otro Excel opaco — el riesgo declarado en DEC-074: si la gobernanza de
§4 degenera, el catálogo muere; por eso cada regla de este doc tiene enforcement, no intención.
(d) **El superseding de REVISIONES de manuales** (frontera declarada, pregunta de Alberto s89):
qué edición de un manual prevalece (latest-wins vs variante-regional vs OEM vs datasheet — la clase
cat009 4K7→6K8 / cat024 V1→V2) es el **contrato de revisión/precedencia #4**, workstream HERMANO ya
especificado (spec s76 `evals/_s76_revision_contract_spec.md`, DEC-058) que vive en el ciclo de vida
de DOCUMENTOS (`documents.status`, que el retrieval consume desde s64). **Punto de contacto único:**
`docrel revision-of` puede REPRESENTAR la relación entre docs; la POLÍTICA de precedencia se decide
en #4, no aquí. Identidad de PRODUCTO ≠ ciclo de vida de DOCUMENTO — fusionarlos sería scope-creep.

## 2. Modelo de datos (entidades canónicas)

```
producto  { id_canonico, canonical_model, vendido_bajo[marcas], oem_manufacturer_marca,
            oem_entidad_legal?, familia?, protocolo?, categoria?, cert[], estado: activo|retirado }
            # vendido_bajo = LISTA (I56-6574 aplica a Morley Y Notifier, s80) — no singular
alias     { alias_texto → id_canonico, tipo: variante-tipografica | codigo-comercial |
            nombre-largo | numero-de-parte }          # ID200/ID-200, Pearl-997-670-005-3
paraguas  { termino → [id_canonico...], tipo: familia | serie | rango,
            divergent: true|false|unknown }           # "ZXe" → ZX2e, ZX5e; divergent ADJUDICADO
homonimo  { termino → [id_canonico...] SIN relación de familia, politica: clarify | prefer(id) |
            fail-open }   # "RP1r" a secas = 4 productos DISTINTOS (Supra/extinción/VSN/OPC) — NO familia
relacion  { origen, destino, tipo: variant-of | rebrand-of(OEM↔vendedor) | shared-doc |
            supersedes }                               # RP1r-Supra rebrand-of Notifier-RP1r
doc_map   { document_id → [{id_canonico, role: primary|secondary, scope: doc|paginas[], provenance}] }
docrel    { document_id ↔ document_id, tipo: language-variant-of | revision-of }   # pares ES/EN (s89)
```

- **`docrel language-variant-of`** (añadido s89, pregunta de Alberto en el gold-review): los ~9 pares
  ES/EN casi-idénticos (~205 chunks duplicados, DEC-066) se marcan como variantes de idioma del mismo
  doc lógico → habilita **prefer-ES/dedup en el pool** en el consumo (BP: NO excluir EN en ingesta —
  hay contenido EN-only y el EN a veces lleva la revisión más nueva, p.ej. cat009 HLSI-MN-025-I v05).
  El activo s83 trae `languages[]` por doc → detección casi gratis en F1.

- **Clave de `doc_map` = `document_id`** (la tabla `documents` ya tiene ids estables), NO
  `source_file` — filename-keys rompen ante renames (TECH_DEBT: migrar a document-identity);
  `source_file` queda como selector humano/provenance. *(Corrección del dúo.)*
- **`scope` doc-vs-páginas** anticipa la atribución fina: el ground-truth CAD-150 (Alberto) es
  aplicabilidad POR-PÁGINA de los manuales 55315013/55315008 — el modelo debe poder expresarlo
  aunque F3 empiece doc-level (ver §6-F3).

- **Granularidad canónica = la regla s83 dúo-validada** (DEC-067): el producto es la unidad
  COMERCIAL-operativa (CAD-150-2 ≠ CAD-150-8; ZX2e ≠ ZX5e), NO el SKU tipográfico ni el rango.
  Los rangos/series son `paraguas`, nunca productos.
- **Anti-sobre-ingeniería v0 (ajuste s89b):** los campos descriptivos (`cert[]`, `protocolo`,
  `categoria`) se cargan SOLO-si-gratis desde el activo s83 y NUNCA se curan en v0 — ningún
  consumidor los lee aún; curarlos sería aparato sin demanda.
- **Semilla = el activo s83** (`s83_document_identity_final.jsonl` + `s83_document_models_final.jsonl`,
  1014 docs / 2761 productos, con `aliases`, `role`, `found_by`, `provenance` ya poblados) + el índice
  s84 (5274 keys model-keyed) + las 3 series declaradas en config (`series_registry`). Los paraguas
  (que el índice s84 NO tiene — DEC-074c) se derivan del `family_scope` de s83 + tus ground-truths.
- **La metadata-inconsistency (TECH_DEBT #49) se resuelve AQUÍ**: N formas del mismo producto
  (Pearl/PEARL/Pearl-997-…) = 1 `producto` + N `alias`. El config-seam no podía; el catálogo sí.

## 3. Dónde vive (D1 — decisión tuya, con recomendación)

**Recomendación: REPO-FIRST.** El catálogo fuente = ficheros versionados en el repo
(`data/catalog/*.jsonl` o YAML por marca), y la DB consume una CARGA DERIVADA (tabla
`product_catalog` regenerable). Por qué es BP y anti-Excel-opaco:
- Cada cambio = un diff revisable (PR) con autor y motivo — la traza ES el formato.
- Rollback trivial (git revert), sin migraciones de pánico.
- El eval puede pinear el catálogo por commit (freeze-contract).
- Alternativa descartada: DB-first (Supabase como fuente) — edición sin traza obligatoria,
  el "quién cambió qué y por qué" hay que construirlo aparte; ya nos quemó el
  `model_catalog.json` congelado-stale (DEC-063).
- **Guard anti-dos-copias (corrección del dúo):** la topología repo→tabla-derivada reproduce el
  MISMO patrón que el `model_catalog.json` stale-desde-s55 (DEC-063) si la regeneración es "cuando
  me acuerde". Contrato: la tabla derivada lleva **el commit-hash del catálogo-fuente** como
  columna/metadata + **check de frescura** en el arranque del bot y en CI (hash de la tabla ≠ hash
  del repo → warning visible / falla el check). La regeneración es parte del pipeline de merge,
  no un paso manual.

## 4. Gobernanza (la parte que evita el Excel opaco)

**Jerarquía de fuentes de verdad (de mayor a menor):**
1. **Ground-truth de Alberto** (adjudicación explícita; como los 29 conflicts s83) — gana siempre.
2. **Dúo-validado** (extracción CROSS-ÁRBOL convergente: Claude + no-Claude, `found_by: both`) —
   entra sin adjudicación SOLO si no-conflictivo Y es entrada de BAJO blast-radius (producto/alias).
   *Precisión de modelos (Alberto, s89): la SEMILLA s83 se extrajo con Opus 4.8 + GPT-5.5 (histórico,
   su provenance no cambia); las extracciones FUTURAS (F4/ingesta-30+) las hace el Claude vigente
   (hoy Fable 5) + el cross-model — la propiedad que valida es el cross-árbol, no la versión.*
   **⚠ Convergente ≠ correcto** (*el dúo lo falseó con dato*: la semilla trae `CAD150R →
   family_scope 'CAD-150'` dúo-convergente y MAL — el ground-truth dice producto DISTINTO).
3. **Extractor single / heurística** — entra como `candidate: true` (visible, NO consumido por
   la resolución query-side hasta promoción).

**Blast-radius manda (corrección del dúo):** los **`paraguas` y `homonimo` nacen SIEMPRE
`candidate`** hasta QA humano, sea cual sea su fuente — son los objetos que MUEVEN pools (la
expansión de un paraguas cambia el retrieval); un producto/alias erróneo es inerte hasta que algo
lo referencia. Además: (a) el **QA-sample pre-filtrado se repite POR LOTE de ingesta** (no solo en
F1 — "no-conflictivo" es vacuamente cierto cuando no hay nada con qué colisionar); (b) el **tally
incluye error-rate por spot-check** (N entradas re-verificadas por lote), no solo throughput.

**Reglas de cambio (enforcement, no intención):**
- Todo cambio al catálogo = PR (aunque sea auto-generada); NUNCA edición directa en main.
- Conflicto (dos fuentes discrepan sobre el mismo producto/alias) → cola de adjudicación
  para Alberto, EN LOTE (no a goteo) — el formato de los 29 de s83 funcionó.
- Cada entrada lleva `provenance` (de qué doc/decisión sale) y `added_by` (s83-extraction /
  alberto-groundtruth / detector-s72 / ingesta-X).
- **Tally de salud** (como el del revisor adversarial): nº entradas por fuente, % candidate
  sin promover, conflictos pendientes. Si `candidate` crece sin promoción → el proceso degeneró.

## 5. Consumo (los 3 lectores y su contrato)

1. **Resolución query-side (retriever)** — F2: `texto de query → id(s) canónico(s)` en cascada
   DETERMINISTA-primero: **check-homónimo → exact-match → alias → paraguas** (expande a variantes).
   **El check-homónimo va PRIMERO** (*corrección crítica del dúo*): un token registrado como
   `homonimo` NUNCA se resuelve por exact-match aunque coincida con un `canonical_model` —
   "RP1r" a secas coincide con el producto extinción, pero resolver ahí dropea el Supra =
   **el fallo MEDIDO −2 hp011 (DEC-074c)**; aplica su `politica` adjudicada (D7). **hp011 = test-case
   obligatorio de F2** (debe resolver a Supra/answer, el gold Alberto-adjudicado). **LLM solo al
   margen** (token no resuelto que PARECE producto), nunca en el camino caliente (DEC-074c, literatura).
   **Clarify-on-ambiguity**: si un `paraguas` tiene `divergent: true` (ADJUDICADO, no inferido —
   DEC-074 declara que "diverge" NO es decidible query-side sin atributos normalizados/EVPI) →
   clarify; `divergent: false` (family-genérico, hp009 EOL) → answer; **`unknown` → fail-open**
   (comportamiento actual del pipeline). Política s79/s80 como principio de diseño (D4).
   **Fail-open general**: si el catálogo no resuelve, el pipeline actual sigue tal cual.
2. **Gate del handler** — ya lee DB live (DEC-063); pasa a leer la tabla derivada (mismo contrato).
3. **Re-tag DOC (chunks_v2)** — F3: `product_model` → **valor canónico** vía `doc_map`. GATED (§6).
   **Semántica del valor (corrección del dúo, armoniza con §2):** un doc MONO-producto → el
   `id_canonico`; un doc multi-variante de familia → **el TAG del paraguas como etiqueta de doc**
   (p.ej. `CAD-150` para 55315013) — usar el término-paraguas como VALOR de `product_model` NO lo
   convierte en entidad-producto (§2 sigue mandando: el paraguas no es un producto); un doc
   multi-producto sin familia → multi-valor o sin re-tag (F3a lo salta). La atribución POR-PÁGINA
   (`scope: paginas`, el ground-truth CAD-150) = **F3b, GATED aparte y OUT-OF-SCOPE de v0**.

## 6. Fases del workstream con gates (de DEC-074e: 4-7 sesiones, ~3.5-6.5h tuyas en lotes)

| Fase | Qué | Gate de Alberto | Medición |
|---|---|---|---|
| **F0** | Este contrato | **Aprobar D1-D6 (~1h)** | — |
| **F1** | Esquema + **normalización/merge de la semilla** (*etapa REAL declarada — corrección del dúo*: `family_scope` = 844/1014 no-vacío pero **592 valores únicos free-text** con dups ES/EN a fundir; merge doc-scoped→producto con regla ante atributos en conflicto [brand ES vs EN]; `oem` de la semilla = entidades LEGALES [Pittway S.r.l.] ≠ OEM-marca [System Sensor] → mapear) + carga → catálogo v0 (branch) + QA | **QA-sample pre-filtrado** (~30-60 entradas de riesgo, en lote) + re-adjudicar hp018/hp011/hp009 **+ los homónimos/paraguas `candidate` de mayor blast-radius** | integridad (0 huérfanos, 0 colisiones id); **cobertura vs el CORPUS** — incl. declarar los **~156 docs SIN entrada** (semilla=1014, corpus=1170; en F3 → fail-open sin re-tag) — la DB de 587 modelos es SOLO cross-check informativo (desincronizada: CAD-150/ZXe/40-40 ausentes, TECH_DEBT #49 — usarla de vara = certificar contra el legacy contaminado; *corrección del dúo*) |
| **F2** | Resolución query-side tras flag (OFF) + clarify | revisar la medición | **hp018 4/4 SIN regresar hp009** (el criterio DEC-074b), medido con el instrumento famtie bajo **freeze-contract COMPLETO** (corpus+índice+embeddings+juez+seeds+config+**catálogo-commit**; *corrección del dúo*) + retrieval-miss=14 no empeora + 354 tests |
| **F2.5** | **SHADOW-MODE (ajuste s89b):** la resolución corre en modo sombra (log-only) sobre TODAS las queries del harness/demo — qué resolvería el catálogo por query, sin afectar nada. Amplía la cobertura de F2 (39 golds = estrecha) a la cola larga, GRATIS, antes del paso caro | revisar el log de discrepancias (en lote) | % queries donde catálogo ≠ comportamiento actual, clasificado (mejora/regresión/neutro) |
| **F3** | Re-tag DOC en chunks_v2 (snapshot reversible, lotes, s78-style). **El switch del GATE del handler a la tabla derivada = flag PROPIO + smoke del handler real (s77-style)** — toca el path de prod que hoy corta 7/9 mal (s76); no va implícito (ajuste s89b) | **aprobar DB-apply + la política multi-producto** | no-regresión eval (freeze-contract completo) + findability probes. **Política multi-producto explícita** (*corrección del dúo, TECH_DEBT #49: doc-level ≠ chunk-level — taguear un doc multi-producto entero a un id contamina el pool de cada modelo*): los docs multi-producto se re-taguean **multi-valor o al paraguas** (NUNCA colapsados a un solo id); la atribución por-página (`scope: paginas`, p.ej. CAD-150) es F3b GATED aparte — F3a solo toca docs mono-producto/inconsistencia-tipográfica (el caso seguro) |
| **F4** | Retirar LEVER2+YAML (#50) + detector proactivo s72 productizado para ingesta-30+ (#49.2) | — (limpieza gated a F2/F3 verdes) | tests + tally |

Orden estricto F2 (query-side, read-only, reversible-por-flag) ANTES de F3 (DB) — D6.

**Beneficiario downstream declarado (pregunta de Alberto, s89): la atribución de modelos POR CHUNK.**
El catálogo la convierte de problema ABIERTO (¿de qué producto habla este chunk? — contra 587+ modelos
ruidosos) en clasificación CERRADA (¿cuál de los N candidatos del `doc_map` de este doc aplica a esta
página? — con alias normalizados para el match). La cadena: `doc_map.scope: paginas[]` +
`chunks_v2.page_number` (ya existe) → F3b aplica el mapa mecánicamente; y el **escritor-en-ingesta**
(TECH_DEBT #49.1, la raíz que escala) atribuye por-chunk EN ESCRITURA consultando el catálogo — sin
catálogo no tiene contra qué resolver. Afina el **model-filter** (menos contaminación de pool, clase
hp018); NO arregla el hard-tail del coseno (RECALL-INTRADOC = multi-granularidad de la capa-ingesta,
DEC-074) — dos ejes que convergen en el mismo escritor futuro.

## 7. Criterios de aceptación del workstream (medibles, declarados ANTES de construir)

1. **Corrección**: hp018 resuelve 4/4 SIN regresión hp009/aisladores — criterio MÁS estricto que lo
   que LEVER2 logró (4/4 PERO regresando hp009 −1, net +3, DEC-074b) — medido en retrieval-miss con
   famtie, NO en PASS (métrica declarada). + **hp011 resuelve a RP1r-Supra/answer** (test-case homónimo).
2. **Escala**: añadir un fabricante nuevo = correr extracción dúo + adjudicar SOLO conflictos
   (horas-Alberto por fabricante ≤ ~15 min). **Medible SIN esperar ingesta nueva (ajuste s89b):
   DRY-RUN en F4** — re-procesar un fabricante YA ingestado como si fuera nuevo → mide el pipeline
   completo (extracción→conflictos→carga) contra un ground-truth que ya existe.
3. **Cero regresión**: eval PASS sin movimiento fuera de ±2 (freeze per-eval) + 354 tests verdes
   en cada fase.
4. **Anti-Excel-opaco**: 100% de entradas con provenance; tally de salud publicado en cada cierre.

## 8. Riesgos declarados (de entrada)

- **El matching texto-libre es frágil** — MEDIDO net-negativo tal-cual (DEC-074: −2 hp011 al
  adivinar). Por eso la cascada es determinista-primero y ante ambigüedad-que-diverge → clarify,
  nunca adivinar. El LLM-al-margen es el ÚLTIMO eslabón, no el primero.
- **OEM multi-marca (D3)**: FAAST (System Sensor/Xtralis/Notifier/Morley), 2X-A→Aritech, RP1r
  (4 productos distintos). El modelo `rebrand-of` lo representa, pero la política de qué
  `manufacturer_visible` gana es decisión de producto (s80 eligió pragmático=vendedor) — D3.
- **QA de los 985 no adjudicados** (s83 validó 29 conflicts; el resto es dúo-convergente pero no
  humano-verificado) → el QA-sample de F1 es la mitigación; el residual se declara, no se esconde.
- **Palanca de eval pequeña (~4)** — este workstream NO es para PASS; si el criterio 2 (escala)
  no se cumple, el workstream falla AUNQUE hp018 resuelva.
- **Coste de gobernanza recurrente**: si cada ingesta genera cientos de conflictos, la
  adjudicación en lote no escala → el detector proactivo (F4) + la extracción dúo lo amortiguan;
  el tally lo hace visible.
- **El "diverge" NO es decidible query-side** sin atributos normalizados/EVPI (gap declarado de
  DEC-074, ratificado aquí): por eso `divergent` es un campo ADJUDICADO del paraguas (humano/dúo-QA),
  nunca inferido en runtime; `unknown` → fail-open. La mecanización completa queda fuera de v0.
- **La semilla s83 NO es limpia lista-para-cargar**: 592 `family_scope` free-text únicos (dups
  ES/EN), atributos en conflicto entre docs del mismo producto, OEM legal≠marca, ~156 docs del
  corpus sin entrada, y errores dúo-convergentes demostrados (CAD150R) → F1 tiene una etapa real
  de normalización + QA; la estimación de horas-Alberto (~3.5-6.5h total) asume adjudicación EN
  LOTE de lo pre-filtrado, no revisión item-a-item.

## 9. Decisiones para Alberto (la ~1h de F0 = marcar estas 6)

| # | Decisión | Recomendación |
|---|---|---|
| **D1** | ¿Repo-first (ficheros versionados, DB derivada) o DB-first? | **Repo-first** (§3) |
| **D2** | ¿Ratificar la regla de granularidad s83 como canónica? | **Sí** (dúo-validada 3 rondas) |
| **D3** | Política OEM/multi-marca: ¿`manufacturer_visible` = vendedor con `rebrand-of` como metadata, o entidad-OEM plena? **Decisión NUEVA de producto** — s80 aplicó vendedor como workaround para 3 QIGs FAAST y difirió explícitamente la política general a D3 (*corrección del dúo: no es "ratificar", es decidir*) | **Vendedor + rebrand-of** (coherente con s80; reversible) |
| **D4** | ¿Adoptar clarify-solo-si-diverge como política de catálogo? Es un **principio de diseño establecido** (s79/s80, con casos hp009-answer/hp018-mixto) pero **SIN caso end-to-end de clarify real en el eval** (DEC-074: hp011 era answerable) — política de diseño, no resultado medido (*corrección del dúo*) | **Sí, como principio** (el eval lo pondrá a prueba cuando haya caso real) |
| **D5** | ¿Quién escribe? PR-only + adjudicación-en-lote de conflictos + auto-entrada de dúo-convergente no-conflictivo | **Sí** (§4; el auto-entrada es lo que hace escalar) |
| **D6** | ¿F2 (query-side, flag) estrictamente antes de F3 (DB re-tag)? | **Sí** (reversibilidad primero) |
| **D7** | **Política del token HOMÓNIMO** ("RP1r" a secas → 4 productos sin relación de familia): ¿`clarify` por defecto, `prefer(id)` cuando tu ground-truth designe el dominante (RP1r→Supra, tu adjudicación s86), o fail-open? *(añadida por el dúo — es la clase del fallo medido −2 hp011)* | **prefer(id) donde HAY ground-truth tuyo; clarify donde no** |

— Cualquier "no" o matiz tuyo se incorpora y este doc pasa a CANÓNICO con tu OK.
— **Traza del dúo (Protocolo 3, ALTO/zona-de-dolor):** cross-model GPT-5.5 **con tools** (23
tool-calls; 6/6 confirmados: chunk-level F3, cobertura-circular, D3/D4 sobre-afirmados,
freeze-contract, document_id) + sub-agente Fable fresco (H1-H9; críticos: homónimo/cascada
[reproduce el −2 hp011], convergente≠correcto [CAD150R en la semilla]). TODAS las correcciones
aplicadas in-place. `adversarial_review_log` s88.
