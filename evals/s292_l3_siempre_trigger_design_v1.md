# s292 — DISEÑO L3: gatillo compuesto «siempre» en el léxico MANDATORY (clase hp003#4)

Estado: **DISEÑO, nada cableado. Las 4 mediciones que lo gobiernan están HECHAS ($0) — este
brief se presenta al dúo con números, no con hipótesis.**

## Mecanismo (verificado, no inferido)
El hecho hp003#4 («desconectar el magnetotérmico antes de manipular la central») vive verbatim
en `eaa39792` (55315013 p.8): «**Desconecte siempre** la magneto térmico bipolar exterior antes
de manipular la central.» Ese chunk está **SERVIDO (pos 3/10) y CITADO [F3]** en la respuesta.
El generador lo omite y **el contrato must-preserve no puede exigirlo** porque el detector no
ve la cláusula: `detect_atoms` encuentra 2 átomos F-MANDATORY en ese chunk y **ninguno es este**
(«Es imprescindible que se usen los orificios…», «No usar nunca el fusible…»). El léxico cerrado
no tiene forma para el imperativo español con «siempre».
⇒ La clase NO es de serving ni de retrieval: es **un hueco del léxico** que deja fuera del
contrato una obligación servida y citada. El resto de la maquinaria (bind → satisfied →
apéndice) ya está viva en producción y funcionaría sin cambios.

## Medición 1 — el gatillo NAIVE está MUERTO (69% FP)
Censo sobre la **vista SERVIDA real de los 39 golds** (398 chunks; recibo
`evals/s292_hp003_trigger_census_v1.json`). Candidato v1 = «verbo terminado en -a/-e adyacente
a *siempre*»: **13 capturas, 9 falsos positivos** («presenta siempre», «permanecerá fija
**siempre y cuando**» ×3, «siempre recibe», «siempre existe»…). El sufijo `-a/-e` no distingue
imperativo de 3ª persona del presente. **Descartado por medición.**

## Medición 2 — el gatillo APRETADO: 6/398, 0 FP (adjudicación mía, a challenge del dúo)
Dos formas CERRADAS, ambas exigiendo «siempre», con exclusión explícita del condicional
(`siempre y cuando` / `siempre que`):
- **A · imperativo**: el verbo ABRE la cláusula y «siempre» le sigue inmediatamente
  (`Desconecte siempre …`).
- **B · deóntico reforzado**: «siempre» en la misma cláusula que `debe(n)` / `tiene(n) que` /
  `hay que`.

Capturas (las 6, íntegras — que el dúo las adjudique):
1. «**Desconecte siempre** la magneto térmico bipolar exterior antes de manipular la central.» ← DIANA
2. «**Debe instalarse siempre** una resistencia RFL entre + y − de la última sirena…»
3. «**Siempre deben respetarse** las recomendaciones de mantenimiento de la norma EN54 parte 14.»
4. «**Siempre debe comprobarse** que la sección del cable usado mantiene la tensión…»
5. «…deben colocarse **siempre** [caja de filtro/trampa de polvo/separadores]…»
6. «El orden de conexión **para su seguridad**, siempre tiene que ser primero la red…»
Mi lectura: 6/6 son obligaciones reales de instalación/seguridad. **Es adjudicación MÍA y es
justo lo que el dúo debe atacar** (el precedente de la sesión: mi «0 espurios» de L2 r1 resultó
1-2 espurios cuando se miró por-fila).

## Medición 3 — el cap de familia (hallazgo de Sol en L2) sale JUSTO
`FAMILY_CAP = 2` para F-MANDATORY. En el chunk diana los 2 átomos existentes están: 1
**satisfecho** por el cuerpo, 1 **no satisfecho**. ⇒ `missing` tendría 1 + el nuevo = **2 = el
cap exacto**. Cabe, pero sin holgura: en un chunk con 2 obligaciones no satisfechas, el nuevo
átomo perdería el slot. **Riesgo declarado, no resuelto: el lever puede ser no-op en chunks
densos en obligaciones.** Opción a debatir con el dúo (NO pre-cablear): priorizar dentro de
F-MANDATORY por proximidad al procedimiento citado, o dejar el cap intacto y aceptar la
limitación con cifra.

## Medición 4 — la dirección no-op del dedup: NEGATIVA (el lever dispararía)
`atom_satisfied(átomo-de-la-cláusula, answer_real) = **False**`, pese a que la respuesta SÍ
menciona «magnetotérmico» — pero en el contexto INVERSO («conectar la alimentación
**activando** el magnetotérmico»). Coincide con el juez del instrumento (`conveyed = 0`).
⇒ La vara del dedup y la del juez concuerdan en este hecho; el apéndice se emitiría.

## Diseño
Flag **`MP_SIEMPRE_TRIGGER`** (`_strict_on_off`, default off; pin off en DEMO_FLAGS y
SAFE_DEFAULTS, patrón s289/s291). Bajo flag, `_detect_mandatory` reconoce las 2 formas A/B
como gatillo compuesto — **exactamente el patrón ya existente** `debe(n)+antes de` /
`must+before` (`mp_lexicon.trigger_present`), sin abrir el léxico a términos sueltos. Todo lo
demás (bind por cita, `atom_satisfied`, `atom_good_form`, caps, `render_appendix`) INTACTO.
El fragmento diana está CITADO ⇒ **no** necesita la exención de citación de L2: es el camino
estándar del contrato.

## Settled citados con su métrica (Protocolo 2.5)
- **DEC-051** (métrica PASS): prompt-completeness genérico NO-GO → esto NO es prompt: es léxico
  determinista del contrato. Además **DEC-098 superseded** su veredicto en fact-level (+3/0).
- **MP_SERVED_BINDING 24/105** (binding servido-NO-citado): no aplica — aquí el fragmento SÍ
  está citado.
- **S274/DEC-134** («familia anexos exhausta para los 6 residuales de entonces»): hp003#4 **no
  era uno de los 6** — verificar en el dúo.
- **DEC-122/130** (léxico MANDATORY cerrado): esta es una EXTENSIÓN del léxico ⇒ el settled que
  más pesa; el gatillo es compuesto y censado, no un término suelto.

## Gates pre-registrados
- **G-0**: suite + byte-invariancia con flag off (medida con `MUST_PRESERVE_CONTRACT=on`).
- **G-FP (decide)**: sweep-39 sobre drafts congelados, brazos OFF/ON, **recibo por-fila** de
  cada apéndice nuevo {gold, fragmento, cláusula, adjudicación} — vara **0 espurios**;
  tripwire **STOP si >4/39** (censo: máx. 6 cláusulas en toda la vista servida, y solo
  disparan las citadas-y-no-satisfechas).
- **G-directed**: hp003#4 pareado-de-drafts OFF/ON (patrón s291b, $0 de generación) + el resto
  de facts de hp003 sin degradar.
- **G-conducta**: centinela hp009 (answer, 0 clarify) + no-desplazamiento de apéndices banked
  (aserción «entradas existentes sin cambio, solo adiciones»).

## Riesgos declarados
1. **Cap de familia** (medición 3): el lever puede ser no-op donde más obligaciones hay.
2. **Mi adjudicación 6/6** puede ser optimista — el gate por-fila la somete a prueba.
3. **Cobertura EN**: el censo es sobre corpus ES mayoritario; la forma inglesa («always +
   imperative») no está medida — se declara fuera de alcance de esta v1 o se censa antes.
4. El apéndice añade texto a respuestas ya largas (clase truncado s98) — G-conducta lo vigila.

---

## Reconciliación dúo (v1 → v2): **NO-GO como estaba diseñado** — 13/13 confirmados, 0 FP

Sol (GPT-5.6, xhigh) 4 + sub-agente **en Opus 5** 9. **Desviación de pin declarada**: el
sub-agente adversarial está pineado a Fable 5 (s88, Alberto) y el crédito de Fable se agotó
mid-sesión; se corrió en Opus 5 (el pin previo s73 era `opus`), con el cross-model —el lado
innegociable— intacto. **Decisión de política pendiente de Alberto.**

### El hallazgo que decide (F1, CRÍTICO — verificado por mí en 1 línea)
`atom_good_form(átomo-de-la-cláusula) = **False**` con el léxico intacto, porque
`_mandatory_clause_form` (must_preserve.py:1973-1997) **re-deriva el gatillo** con el
`_mandatory_triggers` COMPARTIDO. ⇒ Aunque el detector lo viera, el átomo **muere en la
whitelist fail-closed**: el lever era **no-op silencioso**. Mi afirmación «el resto de la
maquinaria funcionaría sin cambios» era FALSA.

**Y el seam obvio es peor que el problema**: parchear `mp_lexicon.mandatory_triggers` tiene
radio de explosión a **SERVING** — `rerank_pool_coverage.py:463` lo consume vía
`_warning_sentence_triggers` para `select_obligation_warning_reserve`, **la lane L2 que
Alberto acaba de encender en producción** (verificado). Cambiaría qué avisos se reservan,
invalidaría los drafts congelados de los gates y G-0 (medido en flag-OFF) NO podría cazarlo.
⇒ **Seam correcto (v2)**: pasar el set de gatillos extendido **por parámetro** a
`_detect_mandatory` **y** `_mandatory_clause_form`, dejando `mp_lexicon` byte-idéntico, +
gate de invariancia de `served_ids` OFF vs ON.

### Los otros hallazgos materiales
- **F3 (medio-alto)**: mis regex sobre población ampliada (1187 chunks) dan **16 capturas con
  ≥4 SPANS ROTOS** — citas decapitadas («…según el cap. », termina en «:»), fusión de 2
  oraciones, y una nota-de-diseño que es **exactamente la clase espuria que L2 r1 dejó
  registrada en código**. El apéndice cita VERBATIM: una cita decapitada en un aviso de
  SEGURIDAD rompe el contrato de fuente ⇒ **guard de integridad de span obligatorio**.
- **F4**: mi censo era **in-sample** (los 39 golds donde correrá el gate) ≈1,6% del corpus ⇒
  censo out-of-sample N≈300-500 antes del GO ($0, la sonda ya hace GET por id).
- **F5**: el léxico se declara **CERRADO BILINGÜE**; mis dos formas son ES-only y hay 16% de
  chunks EN en la propia población ⇒ gemela EN en la misma v1, o DEC explícita de que el
  léxico deja de ser bilingüe. **No es scoping de v1: es contrato.**
- **F7**: mi vara era auto-calificada y **mi tripwire STOP>4/39 cae EXACTAMENTE sobre el valor
  observado** (4 filas en 3 golds) ⇒ ni discrimina ni acota daño. Sustituir por **regla de
  daño** («cualquier fila adjudicada espuria → STOP») + taxonomía de «espurio» pre-registrada
  ANTES de ver filas + adjudicación ciega (Alberto o cross-model), no mía.
- **F8**: FP-por-relevancia medido en el brazo ON: hp009 (pregunta por resistencia EOL de
  **lazos**) recibiría «…resistencia RFL entre + y − de la última **sirena**» = **otro
  circuito**, en la familia donde la confusión de topología es clase SEGURIDAD (DEC-162a).
- **F6**: la forma A es un detector morfológico de **clase abierta** dentro de un léxico
  cerrado; la alternativa que NO re-abre DEC-122/130 —**lista cerrada de imperativos**
  (desconecte/utilice/apague/corte/compruebe…) + adyacencia de «siempre»— no se consideró
  (gap del Protocolo 2 punto 2). **Es la vía preferente de la v2.**
- **F2/F9**: mi Medición 3 estaba mal en 3 términos (cap por-respuesta, 2 capturas en el chunk
  no 1, el átomo existente ni siquiera pasa good_form) aunque acertara por casualidad; y el
  censo se commiteó sin generador (cerrado a posteriori por `scripts/s292_l3_probe.py`).

### Lo que SÍ se sostiene (verificado ejecutando por el revisor)
El **mecanismo** es correcto (F3 citado · ventana 439 chars · `atom_exigible_in=True` ·
`atom_satisfied=False`): la clase ES un hueco de léxico, no serving ni retrieval. DEC-134 no
la zanja (hp003#4 no está entre los 6 exhaustos). MP_SERVED_BINDING bien descartado. La v1
naive bien matada. Y su simulación OFF/ON ($0, 39 golds) da **+4 filas en 3 golds, 0
desplazadas, con la diana entrando** ⇒ **el lever convierte SI se cablea en el seam correcto**.
El propio revisor declaró el caveat de su medición y se auto-corrigió (regla C sobre sí mismo).

### Estado
**Build NO autorizado.** v2 exige, en orden: (F1) seam por-parámetro + gate de invariancia de
serving · (F6) lista cerrada de imperativos en vez del patrón morfológico · (F3) guard de
integridad de span · (F7) taxonomía + adjudicación ciega + regla de daño · (F4) censo
out-of-sample · (F5) resolver ES/EN. Siguiente ronda del dúo sobre la v2 **con Sol
obligatorio** (y el pin del sub-agente a decidir por Alberto).
