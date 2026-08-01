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
