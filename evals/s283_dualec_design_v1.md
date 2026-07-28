# s283 — DISEÑO dual-EC (pre-dúo, Protocolo 3): dos reglas deterministas EC-side de la cola de calidad

**Lane:** diseño-dual-EC (s283). **Rama:** claude/s282-h0t2-qa @ 5f27a2e. **Sin commits. $0** (diseño puro; SELECTs RO y tests locales permitidos para anclar).
**Entregable único:** este doc. **Estado:** PRE-BUILD, PRE-DÚO. Es el paquete que el dúo (Protocolo 3, MEDIO-en-zona-de-dolor: corpus/idiomas/EC-schema/OCR) ataca como unidad; el build posterior es mecánico.
**Anclas de código leídas:** `src/rag/evidence_contract.py` (kinds answer-gated, léxico, render, `apply_evidence_contract`), `src/rag/struck_ocr.py`, `src/rag/generator.py` (seam STRUCK_OCR_CONTEXT líneas 600-645), `src/rag/answer_planner.py` (`build_answer_conflicts`, `KNOWN_ANSWER_CONFLICTS`, `document_revision`), `src/rag/retriever.py` (`_DOC_STATUS_AUTHORITY`, campos del chunk), golds hp012/cat009/cat024/hp002, `evals/s283_hp011_p1_result_v1.md`, `evals/s283_hp012_diag_v1.md`, patrón de gate DEC-149.

## TL;DR

- **Regla 1 — `attribution_conflict` de PROSA cross-source, answer-gated (diana hp012-framing).** Nuevo builder determinista en el EC: mismo sujeto gobernado + cardinal DISTINTO + `source_file` DISTINTO **Y NO-par-de-revisión** → DISCLOSE con atribución de fuente. **Riesgo DECISIVO declarado de entrada:** la separación hp012 (disclose-both) ↔ cat009/cat024 (latest-wins) descansa por completo en normalizar `source_file`, porque **el corpus carece de metadata de revisión/fecha** (declarado en AMBOS golds). El **oráculo offline $0 sobre los 39 es el GATE**: si no separa (dispara hp012, silencio total en cat009/cat024 + colateral 0), **NO-GO**. Aun con separación perfecta, hp012 **sigue PARCIAL** (techo de retrieval-miss del 792, DEC-085/158) — Regla 1 tapa el framing (b)+(d), no alcanza PASS sola.
- **Regla 2 — span-strip struck-OCR SOLO en el contexto servido (diana hp011).** Variante de la política de tachados que elimina SOLO el span `~~…~~` con letras y CONSERVA el resto de la línea; el EC mantiene intacta su política cortar-hasta-fin-de-línea para display-values. Es exactamente la «variante-que-preserva-post-tachado» que el P1 (`s283_hp011_p1_result_v1.md §3 Alternativa 2`) recomendó adjudicar tras medir el colateral de la política cut-to-end en hp002/hp014. Bajo riesgo, medición barata reusando la escalera del P1.

**Alineación de MÉTRICA (Protocolo 2/4).** R1 objetivo = hp012 **PARCIAL** (c1_v4, juez GPT-5.5 single-pass, baseline v2 s283); ningún settled lo zanja (DEC-097 NO-GO se midió en *sobre-disparo-en-spec de un PROMPT*, R1 es código fail-closed; DEC-149 shipeó kinds del EC en *10-réplicas*). R2 objetivo = hp011 **FALLO** (bvg, generación single-turn); el P1 ya NO-GO'eó la política cut-to-end en *conveyed-fact (t.Fi) + no-regresión de superficie* — R2 es la variante que mueve esa misma métrica sin el colateral.

---

# REGLA 1 — `attribution_conflict` de prosa cross-source (kind `market_attribution`)

## §1.1 Mecánica (pseudocódigo anclado a funciones reales)

Nuevo builder en `evidence_contract.py`, clase existente `CLASS_ATTRIBUTION`, kind nuevo `market_attribution`, answer-gated (patrón `meta["answer_gated"]` + `_answer_gate`, idéntico a `enum_alternative`/`ui_path`). La evidencia de hp012 es **prosa** («máximo de dos LIB-200» vs «máximo de cuatro lazos»), no líneas `Etiqueta: valor` → `_param_conflict_obligations`/`parameter_two_values` **no matchea** (diag §3, verificado). Se reutiliza el extractor de cardinales de prosa YA existente `_distinct_counts_of_noun` (regex `(\d|palabra-conteo) … <noun-stem>`).

```
def _market_attribution_obligations(question_tokens, views):
    # 1. Extraer claims (cardinal, noun_stem, span) de la PROSA de cada view,
    #    reusando la maquinaria de _distinct_counts_of_noun / _LIMIT_MAX_RX.
    claims = []                         # {frag, card, source_file, noun_stem, value, span, start}
    for idx, card, text in views:
        for noun_stem, value, span, start in _prose_cardinal_claims(text):  # nuevo helper leaf
            claims.append({...})
    # 2. Emparejar: MISMO noun_stem (distintivo, plural-colapsado con _stem),
    #    cardinal DISTINTO, source_file DISTINTO.
    for a, b in _pairs_by_noun_stem(claims):
        if a.value == b.value:                      continue
        if a.source_file == b.source_file:          continue
        # 3. GUARDA anti-latest-wins (§1.3): los dos docs NO son un par de revisión.
        if not _independent_documents(a.card, b.card):  continue
        # 4. Gate de aplicabilidad a la PREGUNTA (stems distintivos, ya existente).
        matched = _matched_tokens(question_tokens, (a.span, b.span))
        applicable = _question_gate(CLASS_ATTRIBUTION, matched)
        # 5. Gates de plausibilidad de clase (reusa _count_conflict_ok):
        #    condicional/display-noun/ejemplo/comparativa-2-productos → descartar.
        applicable = applicable and _count_conflict_ok(a.span, b.span, noun, tie="cross_source")
        yield _obligation(CLASS_ATTRIBUTION, "market_attribution", a.frag, a.card,
                          a.span, a.start, applicable, matched,
                          {"answer_gated": True, "noun": noun,
                           "value_a": a.value, "b_fragment_number": b.frag,
                           "b_span_text": b.span, "b_source_file": b.source_file})
```

**Answer-gate** (`_answer_gate`, rama nueva para `market_attribution`): dispara SOLO si la respuesta ya afirmó UN cardinal (p.ej. «4 lazos») y **omitió la contraparte con su fuente** — completar la atribución que la prosa dejó a medias (idéntico patrón a `ui_path`: parte presente, parte ausente).

**Render** (`_render_action`, rama nueva): reusa `_base_action("disclose")` + `counterpart` (idéntico a `parameter_two_values`), atribuyendo **por fuente** (no por mercado — ver §1.3):
```
- Nota: las fuentes difieren en «lazos del AFP1010»: «…máximo de dos LIB-200…»
  (MPDT280, p.3) [F1] frente a «…máximo de cuatro lazos…» (15088SP, p.30) [F5];
  confirme según la documentación del panel instalado.
```
La coletilla «confirme según la doc del panel instalado» = **exactamente** lo que el gold hp012 acepta («atribuye cada valor a su fuente y remite a la doc del panel instalado, sin adjudicar»). Fail-closed heredado de `_render_action`: sin cita, sin anclaje exacto del span en su view, o span no-informativo → None.

## §1.2 Por qué NO repite DEC-097

DEC-097 (bloque de selección en PROMPT) fue NO-GO porque (a) una instrucción textual **no auto-ejecuta** (el writer YA la tiene y funde 3/3, diag §3) y (b) **sobre-dispara en spec de forma no-testeable** (exige runs pagados para caracterizarlo). Regla 1 es la clase OPUESTA y la que YA shipeó (DEC-149): **código determinista, fail-closed, $0-testeable** contra el contexto servido. Su disparo se mide offline sobre las cards de los 39 (precisión/recall exactos); añade un DISCLOSE (append), **jamás** reescribe prosa; el sobre-disparo se acota por construcción (fuente-distinta + cardinal-distinto + no-par-revisión + answer-gate + léxico de precisión existente). No es un prompt: no puede «sobre-disparar en spec» de forma opaca.

## §1.3 Guarda anti-falso-positivo latest-wins — **el estudio del discriminador (RIESGO DECISIVO)**

**Ground-truth de los golds (leído, no de memoria):**

| | source_files | producto | idioma | relación | conducta gold |
|---|---|---|---|---|---|
| **hp012** (disclose-both) | `MFDT280`/`MPDT280` (ES) **vs** `15088SP` (US) | AFP1010 (ambos) | ES vs US | **documentos DISTINTOS**, no revisiones (gold L1467-72) | surfacear ambos, atribuir por fuente, **sin adjudicar** |
| **cat009** (latest-wins) | mismo manual, `v04` **vs** `v05` (EN) | — | EN=EN | **misma familia de docs**, revisión posterior | 6K8 (v05) GANA; NO disclose-both |
| **cat024** (latest-wins) | `…GB FR GB IT` **vs** `…_V2` (mismo doc 55347200) | MAD-472 (ambos) | mismo | **mismo doc, dos ediciones** (gold L4390-92) | 17mA (V2) GANA; NO disclose-both |

**El problema, declarado sin adorno:** `source_file DISTINTO + mismo sujeto + cardinal distinto` **NO separa** hp012 de cat024. Ambos tienen source_file distinto, mismo `product_model`, y —crítico— **el corpus NO trae `document_revision`/`document_revision_date` fiables** (hp012 gold L1469-70: *«sin metadata de revisión/fecha … no se puede establecer supersesión»*; cat024 gold L4391: *«ambas revisiones coexisten sin metadata de revisión»*). El `documents.status` (`superseded`→filtrado en retrieval, `_filter_by_document_status`; `_DOC_STATUS_AUTHORITY`) **no llega a la card servida** (se consulta transitoriamente para rankear, no se adjunta) y con ambas ediciones `active` tampoco separaría.

**Único discriminador determinista disponible en `served_cards` sin red:** la **normalización del stem de `source_file`**. Hipótesis anclada en los datos: cat009/cat024 comparten el **número/base de documento** (MAD-472 / 55347200) y difieren solo en un token de edición/idioma (`_V2`, `GB FR IT`, `v05`); hp012 tiene **números de manual disjuntos** (MFDT280/15088SP). Guarda:
```
def _independent_documents(a, b):        # True ⇒ market-variant (dispara); False ⇒ revisión (silencio)
    if a.document_id and a.document_id == b.document_id:      return False
    if _doc_number_stem(a.source_file) == _doc_number_stem(b.source_file): return False
    if a.document_revision and b.document_revision \
       and _same_doc_lineage(a, b):                           return False  # si algún día hay metadata
    return True
# _doc_number_stem: baja + quita tokens de edición/idioma/rev (_V2, vNN, GB/FR/IT/EN/ES,
#   guías-rápidas), extrae el nº de doc → «MAD-472», «55347200», «MFDT280», «15088SP».
```

**Consecuencia para el rumbo (honesta):** la regla es **tan buena como `_doc_number_stem`**, y ese normalizador es frágil sin la metadata que el corpus no tiene. Por eso **el gate NO es el diseño, es la MEDICIÓN**: el oráculo $0 (§1.6) debe demostrar separación PERFECTA sobre los served-sets de los 39. Si `_doc_number_stem` no logra {dispara hp012} ∧ {silencio en cat009+cat024} ∧ {colateral 0}, la regla es **NO-GO** — no se cablea un separador que confunde supersesión con variante-de-mercado (re-afirmaría un valor obsoleto como si fuera conflicto vivo = daño en cat009/cat024). Esto es consistente con el diag hp012 (Rank 2 A, condicionado a «guarda dura por fuente-distinta-sin-supersesión»).

## §1.4 Sobre-disparo en specs multi-doc legítimas + mitigación

**Riesgo:** el mismo dato citado distinto en datasheet vs manual (p.ej. «396» en datasheet y «≈400» redondeado en manual del MISMO producto) → falso «fuente inconsistente». **Mitigaciones (todas deterministas, $0-medibles):**
1. **No-par-de-revisión** (§1.3) también captura datasheet+manual del **mismo doc lineage** → silencio.
2. **Answer-gate:** solo dispara si la respuesta ya se comprometió con UN lado y omitió el otro con su fuente — una spec bien contada (un solo valor, o ambos ya atribuidos) no gatilla.
3. **Gates `_count_conflict_ok` reusados:** condicional, sustantivo-de-display (7-seg), comparativa-de-dos-productos-en-una-oración, ejemplo → descartan el disparo.
4. **Cardinal genuino:** exige DOS enteros distintos del MISMO noun-stem gobernado (no redondeos de la misma magnitud si difieren <1 unidad → gate opcional `|a-b|≥2` a calibrar en el census).
5. **Cap propio del EC** (`APPEND_CAP=3`) + orden estable: acota blast-radius aunque dispare de más.

## §1.5 Tests que la definen (`tests/test_s283_market_attribution.py`)

- **Positivo hp012 (served-set real):** con las cards `MPDT280 p3` (5730afb3, «dos LIB-200/396») + `15088SP p30` (d8892f08, «cuatro lazos») y una respuesta que cita «4 lazos» sin atribuir → emite 1 disclose `market_attribution` con ambas fuentes; span anclado exacto; fail-closed si falta una cita.
- **Negativo cat024 (served-set real):** cards MAD-472 V1 («<15 mA») + V2 («17 mA»), mismo doc lineage → `_independent_documents=False` → **0 obligaciones**. Idéntico para cat009 (4K7 v04 / 6K8 v05).
- **Negativo answer-gate:** respuesta que YA atribuye ambos valores a su fuente → satisfecha, 0 acción.
- **`_doc_number_stem` unit:** {MAD-472…GB FR IT, MAD-472…_V2}→mismo stem; {MFDT280, 15088SP}→distinto; guías-rápidas y sufijos `_lr`/idioma normalizados.
- **Byte-inercia:** flag `EVIDENCE_CONTRACT` off ⇒ módulo no importado (contrato de seam ya existente); on-sin-conflicto ⇒ respuesta byte-idéntica.

## §1.6 Plan de medición (GATE)

1. **Oráculo offline $0** (`scripts/s277_c1_p1_offline_counterfactual.py`, brazo `--with-evidence-contract`, o sonda `build_obligation_ledger` sobre las 27 réplicas): precisión/recall del kind sobre los served-sets de los **39 golds + 27 réplicas**. **Criterio de GO:** dispara en hp012, **silencio en cat009/cat024/hp002 y en los 37 restantes**, `candidate_fails=0`. Preserva 62/62 + 93/93.
2. **bvg dirigido `ONLY_QIDS=hp012`** (~$0.4, env de paridad DEC-157) + juez canónico GPT-5.5: mide si el framing (b)+(d) del diag se corrige. **Predicción declarada:** mejora framing, **sigue PARCIAL** (falta el 792, retrieval-miss — techo honesto).
3. **Controles no-regresión** cat009 + cat024 + hp002 (bvg dirigido o judge-free $0 sobre served-set fijo): **cero** disclose nuevo.
4. **No-regresión suite** completa (byte-inercia flag off) + los 62/62 semánticos del oráculo.

**Coste total R1:** **$0** el gate decisivo (oráculo) + ~$0.4 bvg hp012 + ~$0.4 controles pagados si el $0 no basta. **El $0 manda: sin separación perfecta offline, no se gasta ni se cablea.**

## §1.7 Qué NO hace (límites declarados)
- **NO** resuelve el retrieval-miss del 792/1980 (hp012 sigue PARCIAL; eso es el path B del diag, DEC-085/158 — otra lane).
- **NO** adjudica ganador (eso es latest-wins, explícitamente fuera; la guarda §1.3 lo evita).
- **NO** reescribe prosa (append/disclose solo).
- **NO** dispara si el corpus adquiere metadata de revisión (la guarda `_same_doc_lineage` lo silenciará) — se degrada con seguridad.
- **NO** toca `parameter_two_values` ni `declared_vs_enumerated` (kinds ortogonales; las 2 notas figura-vs-conteo de hp012 son un ruido aparte, fuera de alcance — diag §4 secundaria).

---

# REGLA 2 — span-strip struck-OCR SOLO en el contexto servido (STRUCK_OCR_CONTEXT)

## §2.1 Mecánica (pseudocódigo anclado)

Nueva función leaf en `struck_ocr.py`, **sin tocar `apply_struck_ocr`** (política EC, cortar-hasta-fin-de-línea, adjudicada s722/1222). El seam `generator.py:606-609` re-apunta de `apply_struck_ocr_context` (cut-to-end por-línea, NO-GO en P1) a la variante span-strip:

```
def _strip_struck_span(line):            # por LÍNEA física
    if "~~" not in line: return line     # early-out byte-preservador (idéntico a la actual)
    parts, pos = [], 0
    for m in _STRUCK_RX.finditer(line):
        if _LETTER_RX.search(m.group(1)):        # tachado CON letras (transliteración dudosa)
            parts.append(line[pos:m.start()])    #   → ELIMINA el span, CONSERVA lo demás
            pos = m.end()                         #   (contraste con apply_struck_ocr: allí pos=None,break)
        else:                                     # tachado de SÓLO símbolos/dígitos (7-seg)
            parts.append(line[pos:m.start()] + m.group(1))  # → conserva contenido (marcador=formato)
            pos = m.end()
    parts.append(line[pos:])
    return _collapse_ws("".join(parts))          # colapsa dobles espacios que deja el hueco

def apply_struck_ocr_context_span(text):
    if "~~" not in text: return text
    return "\n".join(_strip_struck_span(l) for l in text.split("\n"))
```

La única diferencia con `apply_struck_ocr` es la rama letter-bearing: **eliminar-el-span** (`pos=m.end()`, seguir) en vez de **cortar-a-fin-de-línea** (`pos=None; break`). El test de la letra, la conservación de símbolo/dígito-solo, y la aplicación por-línea física son IDÉNTICOS.

## §2.2 Por qué DOS políticas para DOS capas es correcto (no drift)

**Un solo invariante de seguridad, blast-radius por-capa:**
- **EC (`_display_span`, cut-to-end):** opera sobre un **span de valor-display corto que ES el payload** de la obligación (el bot lo AFIRMA como dato). Un tachado-con-letras ahí ⇒ el valor entero es OCR-no-fiable ⇒ negarse a re-afirmar CUALQUIER parte de esa línea es la postura conservadora correcta (adjudicada).
- **Contexto (span-strip):** opera sobre **prosa arbitraria de referencia** que solo pasa al writer para ubicar/citar. El P1 midió que cut-to-end aquí trunca prosa VÁLIDA post-tachado (hp002 pierde la cláusula de medición de flujo; hp014 pierde un encabezado). Suprimir más que el artefacto = pérdida de información **sin beneficio de seguridad**.

Ambas políticas **eliminan el token tachado-con-letras** — el invariante («jamás re-afirmar una transliteración 7-seg dudosa», feedback_7segment) es EL MISMO. Difieren solo en cuánto material CIRCUNDANTE arrastran, y esa diferencia está **justificada por qué es el material** (un valor afirmable vs prosa de contexto). No son dos reglas de seguridad en conflicto: es UNA regla con radio adecuado a cada capa. Por eso no es drift — y por eso el EC queda **intacto** (su política adjudicada no se re-litiga).

## §2.3 Casos borde
- **Tachado que abarca la línea entera** `~~todo~~` → span-strip deja línea vacía (igual que cut-to-end; sin info extra perdida).
- **Múltiples spans** `a ~~b~~ c ~~d~~ e` → elimina b y d, conserva a/c/e (decisión POR-SPAN, no por-línea).
- **Tachado SIN letras** `~~- -~~`, `~~00~~`, `~~De 01 a 30~~` → **conserva contenido** (paridad 7-seg, marcador=formato) — recupera exactamente las alternativas `00`/`De 01 a 30` que el P1 midió CAYENDO con cut-to-end (P1 §2c).
- **Mixto en una línea** (símbolo-solo + letra) → conserva el símbolo-solo, elimina la letra (por-span).
- **Adyacente a markdown** `**~~Hardware~~**` (hp014) → deja `****` colgante. **Mitigación declarada:** `_collapse_ws` + opcional colapso de pares de marcadores vacíos (`**  **`→``); bajo impacto, se mide en el control hp014.
- **Espacios dobles** por el hueco → `_collapse_ws` dentro de la línea modificada; líneas sin `~~` byte-idénticas (early-out).

## §2.4 Tests que la definen (extienden `tests/test_s283_struck_ocr_context.py`)
- **Chunk real 475a8f18 (F13):** ON ⇒ `~~`/`t.Fi`/`t.A` ausentes, `r.i`/`4.12.2` presentes, **y AHORA** `- -`/`00`/`De 01 a 30` **PRESENTES** (el colateral del P1, corregido) — este es el assert que distingue span-strip de cut-to-end.
- **hp002 (chunk real):** el tachado `~~y con el conducto de aspiración intacto~~` a mitad de línea → **conserva** «se registrarán los valores de la medición del flujo de aire…» (la regresión del P1, eliminada).
- **Casos borde §2.3:** whole-line, múltiples spans, símbolo-solo, mixto, markdown colgante.
- **Paridad EC intacta:** `evidence_contract._apply_struck_ocr is struck_ocr.apply_struck_ocr` (la política EC NO cambia; los tests del EC siguen verdes).
- **Byte-inercia + clausura sellada:** import perezoso, flag off ⇒ módulo no importado (evita `HOLD_IMPLEMENTATION_DRIFT` del runner P1, hallazgo del P1 §1); suite completa 0 fail flag off.

## §2.5 Plan de medición (reusa la escalera de `s283_hp011_p1_result_v1.md`)
1. **Unit** con el chunk real 475a8f18 + hp002 (a): superficie ON vs OFF, $0.
2. **Suite completa** byte-invariante flag off (b): 3228/0 (o el conteo vivo).
3. **A/B judge-free hp011 Y hp002** (c): reusa los dumps del served-set del P1 (generación FAKE $0 para no-regresión) + 3 gen ON hp011 (~$0.3). **Criterio:** t.Fi 1/3→0/3 (diana preservada del P1) **Y** cláusula de flujo de hp002 **conservada** (colateral del P1 eliminado) — el delta que justifica la variante.
4. **bvg dirigido** `ONLY_QIDS=hp011` + hp002 + controles cat001/hp014 (~$0.25 juez): confirma FALLO→PARCIAL en hp011 sin regresión en hp002/hp014.

**Coste total R2:** ~$0.55 (idéntico orden al P1; el no-regresión hp002 es $0 reusando served-sets). **Predicción/techo honesto:** R2 elimina la mitad ESTOCÁSTICA de hp011 (t.Fi, F.1) sin dañar contexto; **NO** toca la mitad ESTABLE (`ri/Resumen/4.1.2`, duplicado corrupto de corpus = P2/Alberto) → hp011 **no llega a PASS con R2 sola** (P1 §3 gap iii, reconfirmado).

## §2.6 Qué NO hace (límites declarados)
- **NO** cambia la política del EC para display-values (cut-to-end, adjudicada — intacta).
- **NO** toca tachados de símbolo/dígito solo (paridad 7-seg preservada).
- **NO** re-afirma ningún token tachado-con-letras (invariante de seguridad idéntico al EC).
- **NO** resuelve el duplicado corrupto `ri` de hp011 (corpus, P2/Alberto).
- **NO** opera en ingesta ni en el EC: SOLO en el seam `STRUCK_OCR_CONTEXT` del generador (reversible, flag off).

---

# GATE TRANSVERSAL Y COSTE

- **Dúo Protocolo 3 OBLIGATORIO antes de build** (MEDIO-en-zona-de-dolor: corpus/idiomas ES-EN/OCR/EC-schema): sub-agente Fable 5 + cross-model **GPT-5.6 Sol xhigh** (`scripts/adversarial_review.py`, lee el repo). Las dos reglas se atacan **como unidad**. Bite esperado: R1 §1.3 (¿`_doc_number_stem` separa de verdad? ¿casos donde supersesión y market-variant colisionan?), R2 §2.2 (¿el argumento «dos políticas, un invariante» aguanta, o es drift encubierto?).
- **Orden de build sugerido:** R2 primero (bajo riesgo, gate barato, cierra un colateral ya medido) → R1 (gateada por el oráculo $0; puede resultar NO-GO en el propio gate, y eso está bien).
- **Coste agregado:** R1 = $0 (gate) [+~$0.8 si pasa a pagado] · R2 = ~$0.55. Nada activo en prod (ambas flag-off, byte-inertes). El flip/merge lo decide Alberto.
- **Baseline inmutable:** ni R1 ni R2 editan la P1 `b92ff51` ni la clausura sellada s277 (import perezoso en ambos seams, hallazgo del P1 §1 respetado).
