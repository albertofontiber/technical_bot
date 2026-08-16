# s324c · Lever B de etapa 3 — propuesta de DISEÑO para el dúo (nada construido)

> **Qué es.** Diseño escrito (Protocolo 2) del lever de etapa 3 sobre la población medida en s324b
> (`evals/s321_poblacion_etapa3_v1.md`, banner DEC-175). Va al dúo (Sol xhigh + Fable) ANTES de
> tocar código. Todo lo afirmado sobre conducta del sistema está leído en código o en recibo (cita
> `fichero:línea`); lo medido hoy son **replays $0** (lecturas REST + selectores deterministas, sin
> generación ni juez): reproducen los `appended_ids` estructurales del FULL 16-ago **15/15 golds**
> (misma disciplina de fidelidad que s293). Corpus/vara: FULL `evals/s100_factlevel_full_v3_20260816.yaml`
> (26.215 chunks, `coverage_c1_v4`, `RERANK_TOP_K=10`, juez GPT-5.5 K=5, `THRESH_FIRM=4`).

## 1 · Decisión a la que sirve

**Población medida:** ≥4 golds (lectura conservadora: solo donde el oráculo levanta la base) / ≥7
(vara literal, contando 3 «flips»). **Adjudicación pendiente de Alberto: ¿cuenta un flip como
población?** Consecuencias, con lo medido aquí:

- **Sí cuentan** → la población sube, pero la clase de los flips es *estabilidad de síntesis* (la
  base ya transmite ≥1/3 sin oráculo): **ningún lever de serving la toca**, y los levers de esa
  clase están medidos (prompt DEC-051→098 SHIP; selection-block DEC-097; ledger DEC-119;
  descomposición DEC-120). Consecuencia: nada que diseñar en serving; van a N-reps/gold-review.
- **No cuentan** → ≥4 golds nominales, pero **el diagnóstico por hecho (§2) muestra que NO son una
  clase**: un solo lever de serving paga con evidencia **1 hecho** (`hp017#1`), quizá 2 con dos
  cambios más (`hp017#2`); el resto son packet de datos, NO-GO de retrieval ya medido, o ya OK.

Corrección aritmética que el hub debe adjudicar: la base «≥2 (`hp001#2`, `hp012#3`)» viene del
censo sobre el FULL **1-ago**; en el FULL 16-ago `hp012#3` es **OK** (`in_topk`, conveyed 5/5;
sus carriers `b162a7eb`/`f03d3ae4` en topk ranks 1 y 5) y `cat017#2` también (5/5). El encargo
lista 7 hechos / 5 golds; por gold, la población de HOY es {hp017, hp005, hp015, hp001} = **4**, no
«≥2+2».

## 2 · Diagnóstico por hecho (dato del recibo/replay, no de memoria)

Vista servida = prefijo rerank (10, byte-protegido `serving_pipeline.py:95,126`) + ≤4 filas de
coverage (`serving_pipeline.py:20`; `post_rerank_coverage.py:130-131`: cap global 4, **cap 2 por
lane**; reserva y vía por-faceta con presupuesto propio `:134,:141`). Las filas de lane se sirven
**solo como excerpts** = cards de 360 chars (`coverage_context_content`, `post_rerank_coverage.py:311-351`;
`config/evidence_coverage_facets_v*.yaml: window_chars 360`), no el chunk completo. La sonda `serve`
inyecta el chunk **completo**, **al final** de la lista y con la `similarity` máxima
(`s293_reachability_probe.py:121-132`); el generador respeta el orden de la lista y estampa esa
relevancia en la cabecera (`generator.py:778-805`).

| hecho | por qué el carrier no se sirve HOY (medido) | qué lo levantaría |
|---|---|---|
| **hp017#1** «instrucción de entrada» | `raw=0/in_pool=False`; el carrier `d27b1a1b` (p41) SÍ se sirve como fila estructural F12, **pero sus 3 cards son [419:673],[675:1032],[1694:2052] y el bullet «* Instrucción de entrada:» está en [1427:1690]** → el generador nunca vio el literal (el FULL lo contó «servido» con votos de soporte 5/5 sobre los excerpts — plausiblemente por la card de salida, que habla de «condiciones de entrada»; el submotivo `append_view_truncated` solo se alcanza con soporte servido = 0, `factlevel_assessment.py:997-1010`). Oráculo con el chunk completo: 0/5→**5/5 ×3**. | **Cerrar el bloque de lista intersecado** en la vista de la fila apendizada (D1). Censo $0: **6/30 filas estructurales del FULL (6/15 golds) tienen un bloque de bullets cortado por las cards** (cat008, cat019, cat022, hp003, hp012, hp017). |
| **hp017#2** «Editar Configuración» | Carrier `94cbb0ce` (p43 «A5.2 Crear una regla», ruta SIN número + «borrar la regla 1») **no está en el pool (19 tras filtro de familia)**; SÍ está en la ventana estructural (gap 2 de la semilla idx76), puntúa positivo (19,4) y casa 2 facetas, pero **queda 4.º de 47** (`rank_key` prima nº de facetas: `structural_neighbor_coverage.py:351-365`; `max_anchors: 2`, cap por lane 2). Además, **aunque se sirviera, su única card sería [1500:1828]** (no lleva la ruta, en 592, ni «Regla 1», 230/400). El chunk que sí se sirve (`a95f8659`, F11) lleva la ruta con «7:» y el guard la borra (DEC-172). Oráculo (chunk completo al final): 0/5→5/5 ×3. | Dos cambios (selección + vista completa) para **1 hecho** ⇒ NO por población (regla DEC-175). Selección por-necesidad **medida y descartada**: `94cbb0ce` es 11.º/3.º/26.º en las 3 needs; +1 anchor tampoco (3.º = `a7a78a13`). |
| **hp005#3** «CIRCUITO SIRENA» | Un carrier (`66946fcc`, votos 5/5) SÍ se sirve vía lane; **base 5/5·0/5·5/5** hoy; los otros (`29270029` idx94, `b92ecc4a` idx96) están en ventana con 2 facetas y rango bajo. | Ninguno de serving: omisión **inestable**. N-reps + gold-review (¿exige la pantalla literal?). |
| **hp015#0** «convencional» | Carriers = portada/intro (`717223e7` idx0, `da5d4101` idx1): **ni en pool (16) ni en ventana** (semilla más cercana idx10 → gap 9-10 > `max_gap 8`), `archetype None` ⇒ lane inerte. Y **CCD-103 es `candidate: true` en el catálogo** (`unresolved:ccd-103`) ⇒ el detector lo excluye (`catalog_resolver.py:142-144`), `resolve_query` no detecta nada, `_query_resolved_ids=[]` ⇒ anexo must-preserve fail-closed (`must_preserve.py:2375-2380`), `attest_identity=False`. Oráculo 0/5→5/5 ×2. | **Dato, no lever**: packet «confirmar CCD-103 (Detnov)» + atributo tipado #76 (`tecnologia=convencional`, cita portada) como evidencia gobernada (D5, futuro). |
| **hp015#2** «32 por zona» | Carrier `fdb14497` **en topk F4, contenido completo**; síntesis pura (base 0/5·0/5·5/5); apéndice-oráculo 5/5 ×3. El anexo existente no dispara: identidad no resuelta (arriba) **y** `detect_atoms(fdb14497)=0` (ninguna familia F-* cubre «máximo… por zona son 32»). | Packet CCD-103 primero; luego haría falta una familia nueva (F-LIMIT) = vocabulario nuevo (clase FP DEC-127) → no ahora. |
| **hp001#2** «1111» | Carrier `edeb58a7` (MU-376 p10 «4. Nivel usuario») **no en pool (45)**; el doc MU-376 sí (ranks 3 y 7, fuera del top-10 ⇒ sin semilla estructural); `IDENTITY_FETCH` solo actúa con doc **ausente** (`catalog_resolver.py:782-785`); la aguja «1111» no está en la pregunta (DEC-085). Colateral visto: el corpus tiene **dos revisiones** de MC-380 (119+136 chunks) y de MS-416 (99+88). | Retrieval within-doc: **NO-GO ya medido** (DEC-084/085/089). Sin lever de serving. |
| **hp012#3** «4 lazos / 792» | **OK en el FULL 16-ago** (carriers en topk 1 y 5; conveyed 5/5). Within-doc solo en el FULL 1-ago (pool sin «792»). | Fuera de la población de hoy. |
| *(cat017#2)* | OK 16-ago (`4c186fb2` ni en pool; el hecho llega por otra vía). El lever B «referencia gobernada» original tenía población 1 (DEC-175a, pata golds intacta): **no es el lever de esta población**. | — |

## 3 · Diseños candidatos

**D1 (recomendado) — `COVERAGE_LIST_BLOCK_CLOSURE`: cierre de bloque de lista en la vista servida
de la fila apendizada.** *Mecanismo:* en `_build_served_coverage_cards` (`post_rerank_coverage.py:644-676`),
tras `_expand_logical_table_boundaries` (`:354-390`, el precedente EXACTO para filas de tabla),
un `_expand_logical_list_boundaries`: si el rango de una card interseca un **bloque de lista**
(línea introductoria opcional que termina en «:» + ≥2 líneas contiguas `^\s*(?:[-*•·◦]|\d{1,2}[.)])\s+`,
blancos permitidos), el span servido se extiende a los límites del bloque; si el excerpt superaría
`MAX_EXPANDED_EXCERPT_CHARS` (1800, `:150`) → sin cambio. El span extendido viaja como
`served_coverage_cards` con su receipt (`selector_start/end`, `logical_record_expanded`,
`has_exact_served_coverage_receipt` `:232-243` re-deriva con el MISMO flag), y `coverage_context_content`
(`:324-337`) lo usa para la lane estructural cuando el flag está on. *Señal:* estructural pura
(card ∩ bloque); cero vocabulario de producto/gold. *Sirve:* el bloque completo de una fila **ya
validada y ya servida**; no añade filas, no toca prefijo, `appended_ids` ni selección; 0 HTTP, 0
llamadas de modelo. *Flag:* modificador de coverage (añadir a `COVERAGE_MODIFIER_FLAGS`,
`release_profiles.py:79`; exige master+lane como LOGICAL_RECORD `:229-247`), default off,
`DEMO_FLAGS`/`SAFE_DEFAULTS` off, byte-inerte con off. *Coste:* $0/consulta; +277-682 chars por fila
afectada (censo). *Radio:* solo filas cuya card interseca una lista: **6/30 filas estructurales,
6/15 golds** en el FULL; las 18 filas de reserva y 3 document-local **no censadas** (§7). *Por qué
BP/estructural/escalable:* la vista de 360 chars parte listas por la mitad — defecto de acotación,
no de prompt; misma clase y mismo seam que el cierre de fila de tabla ya existente; independiente
del fabricante. *No re-litiga:* ni cuota (DEC-167), ni prompt (DEC-051), ni composición/lanes
(DEC-169), ni selección de la lane viva (DEC-171). Hermano de `LOGICAL_RECORD_COVERAGE` (off en
prod; **su veredicto no lo he localizado** en DECISIONS/LEVER_DIGEST — declarado).

**D2 (medido y APARCADO) — cierre posicional del hueco entre anchor estructural y semilla**
(conducta con presupuesto propio 1, patrón reserva). Trigger censado: **20 filas / 14 golds, 62
chunks-hueco (31 pasan faceta)** → radio grande; retorno con evidencia **1 hecho** (`hp017#2`) y
solo si además se sirviera contenido completo (su card no lleva el hecho) ⇒ **NO por población y
por doble cambio en lane viva**. Queda documentado para que nadie lo re-proponga sin este censo.

**D3 (declarado, NO diseñado) — relleno del pool acotado a la familia tras el filtro** (2.ª pasada
vectorial sobre `allowed_sources` cuando el filtro deja el pool en 16-19; extensión post-corte,
decide el reranker). Cae bajo la fila **«Consumo ADITIVO del pool — bajo CUALQUIER nombre»** del
LEVER_DIGEST (NO-OP-con-regresión; brazo legítimo = medición NUEVA gateada + permiso de Alberto).
Retorno incierto (`94cbb0ce` debería además ganar el top-10; portada/intro de hp015 y «Nivel
usuario» de hp001 son distractores léxicos para el reranker); coste +1 RPC y más tokens de rerank.
No se recomienda ahora; si Alberto lo autoriza, es OTRA propuesta con su prereg.

**D5 (dato, no lever)** — packet CCD-103 (confirmar candidate → detector/anexo/clarify) y, después,
servir atributos tipados #76 con cita como evidencia gobernada para la clase «negar la premisa»
(hp015#0). Su población es la de la fase 2 de #76.

## 4 · Gate pre-registrado (D1)

Métrica: per-fact `conveyed` juez canónico GPT-5.5 K=5, `THRESH_FIRM=4`, instrumento v3.2 (que
ya juzga sobre `coverage_context_content`, `factlevel_assessment.py:415-420` — ve D1 sin cambios).

- **G0 ($0)** — censo extendido del trigger a las 21 filas de reserva/document-local (replay con pool)
  + fidelidad 15/15 re-verificada el día del gate. Población del defecto y radio exacto.
- **G1 ($0)** — tests: flag off ⇒ `coverage_context_content` byte-idéntico (suite verde); flag on ⇒
  solo cambian filas con card∩lista, span ≤1800, receipts válidos, prefijo/`appended_ids`/selección
  intactos; contrato de release acepta el flag.
- **G2 (~$1-2, opcional)** — oráculo *exacto*: variante `serve` que inyecta la **vista cerrada** de
  `d27b1a1b` en su posición de lane (no el chunk completo ni duplicado); 3 reps. Exige la fase 2 de
  la sonda (TECH_DEBT #89); si no está, se salta a G3.
- **G3 (~$8-15)** — pareado OFF/ON sobre **captura congelada** de retrieval+rerank (patrón s289 G-1/G-3,
  DEC-096b): generación N=3 por brazo. **Diana** `hp017#1`. **Cohorte «vista cambiada»** = los golds
  de G0 (hoy 6): todos sus hechos. **Controles negativos** = los ~33 golds restantes: hash de la
  vista servida OFF==ON (byte) — no se regeneran. **No-invención**: eje invención pareado K=3 en la
  cohorte (K=1 inusable, DEC-090) + lectura de respuestas (regla-C DEC-092b). **Latencia**: p50 OFF/ON
  (esperado ≈0). **Coste sweep**: tokens añadidos por consulta afectada (esperado +100-200).
- **Veredicto pre-declarado:** **GO** ⇔ `hp017#1` firme (≥4/5) en ≥2/3 reps ON con OFF ≤1/3 **∧** 0
  regresiones a nivel-hecho en la cohorte (ningún hecho firme-OFF cae a miss en ≥2/3 ON) **∧**
  invención sin subida **∧** byte-identidad fuera de la cohorte. **NO-GO** ⇔ `hp017#1` 0/3 ON o
  cualquier regresión estable. **INCONCLUYENTE** ⇔ flip 1/3 → residual de síntesis declarado; sin
  re-corridas (anti gate-shopping DEC-126). Un GO deja **ON pendiente de Alberto** (rollback = quitar
  la variable).

## 5 · Alternativas descartadas · gaps · métricas de los settled citados

Descartadas: lever B «referencia gobernada» (DEC-175: población 1; hoy cat017#2 OK) · span-repair
del guard para hp017#2 (DEC-172 NO-GO economía+seguridad; y hoy: el carrier limpio ni se sirve) ·
`RERANK_POOL_COVERAGE` global (DEC-169; medido no trae carriers, s293) · cuota/selección por-faceta
en la lane (DEC-167 cerrada; además **medida aquí sin efecto** sobre `94cbb0ce`) · +1 anchor
estructural (medido: 3.º no es el carrier; consumiría el cap 4) · levers de prompt/ledger/descomposición
para los flips (DEC-051/098·119·120) · deep-lookup/fetch within-doc para hp001#2 (DEC-084/089) ·
familia F-LIMIT del anexo para hp015#2 (vocabulario nuevo; y ciego mientras CCD-103 sea candidate).

Métricas (Protocolo 2.5): objetivo de HOY = conveyed per-fact K=5 sobre hechos servidos-y-omitidos.
DEC-175 = POBLACIÓN (no coincide → no lo toco: lo aplico); DEC-167/168 = conveyed pareado sobre
cat017#4/hp002#4 (misma métrica, otra población y otro mecanismo → D1 no lo re-litiga); DEC-051 =
PASS pre-NOCAT, re-medido conveyed en DEC-098 (misma métrica: por eso los flips NO son diana de
serving); DEC-084/085/089 = retrieval-miss/famtie (métrica distinta pero mecanismo idéntico al que
hp001#2 necesita → no lo re-abro); DEC-186 EN REVISIÓN: no cito su cifra.

Gaps/riesgos declarados: (i) D1 paga **1 hecho** con evidencia — la población del **defecto** (6/30
filas) es el argumento estructural, no el conteo de golds; DEC-175 puede volver a morder y es
legítimo que Alberto diga no. (ii) El oráculo de hp017#1 no es D1: chunk completo, al final, con
relevancia máxima y duplicado (s321 §5.5); D1 sirve un excerpt en su posición de lane → G2/G3 son
la prueba, no la sonda. (iii) Cambia el contrato de la vista servida «solo spans receipted» de
s110/s111 — igual que la fila de tabla: el bloque es el registro lógico y va receipted; el dúo debe
decidir si lo acepta. (iv) Riesgo de deriva: `has_exact_served_coverage_receipt` re-deriva las cards
con el flag → un toggle entre attest y render invalida el receipt (fail-closed a cards). (v) El
instrumento cuenta como «servido» excerpts que no llevan el literal (soporte por paráfrasis) ⇒
`append_view_truncated` infracontado (0 en todos los FULL) → deuda para el hub. (vi) Corpus con
revisiones duplicadas de CAD-250 (MC-380 ×2, MS-416 ×2) → memoria «un sha distinto no es un
documento nuevo»; no medí su efecto en hp001.

## 6 · Recomendación y orden

**UN diseño: D1.** Orden: (1) dúo Sol xhigh + Fable sobre este documento (tier MEDIO en zona de
dolor: vista servida de una lane viva C1); (2) construir flag-off + línea de contrato de release +
tests G1; (3) G0 → (G2) → G3 con veredicto pre-declarado; (4) adjudicación de Alberto (ON en
Railway) + DEC + fila LEVER_DIGEST. **En paralelo, sin lever:** packet CCD-103 (desbloquea anexo/
clarify/attest para hp015 antes de medir nada más), cerrar `hp001#2` (NO-GO de retrieval medido) y
`hp012#3` (OK) con evidencia, `hp005#3` a N-reps/gold-review, y la corrección aritmética de §1 en el
banner DEC-175. Alternativa igualmente defendible para Alberto: **no construir** (población 1 hecho)
y cerrar etapa 3 con este diagnóstico — la elección es suya (riesgo declarado, rollback barato).

## 7 · Lo que NO sé

Veredicto histórico de `LOGICAL_RECORD_COVERAGE` (off en prod, sin fila en el digest) · si el
cierre de bloque paga hp017#1 en la posición/relevancia de lane (solo lo prueba G2/G3) · población
del trigger en filas de reserva/document-local (no replayadas) · qué facetas exactas hicieron perder
a `94cbb0ce` frente a `a7a78a13` (no leí `evidence_coverage_facets`) · si la duplicación de
revisiones CAD-250 mueve el pool de hp001 · por qué el hub sumó «≥2+2=4» (yo cuento 4 golds sin
hp012) · efecto de D1 fuera de los 39 golds (tráfico real).
