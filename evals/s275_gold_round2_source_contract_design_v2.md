# S275 — Gold round 2 source-contract (diseño v2)

## Estado y alcance

Este diseño **sustituye** a `s275_gold_round2_source_contract_design_v1.md`,
declarado NO-GO por el dúo adversarial. Conserva el objetivo diagnóstico, pero
cierra cinco grados de libertad: cegado, respeto de S270, taxonomía E1,
calibración exacta y crédito E3.

La ronda estudia únicamente los seis `synthesis-miss` del cierre S274. No
pretende validar una política general para otros golds, manuales ni preguntas.
No mejora el bot, no edita gold, no banca conversiones y no puede convertir por
sí sola ningún caso a `OK`.

Foto congelada: **146 OK / 6 synthesis-miss / 2 retrieval-miss / 154 =
94,81 %**. El objetivo externo de 98 % no se muestra a los adjudicadores y no
forma parte de su rúbrica.

## Autoridad y evidencia congeladas

SHA-256 de texto con CRLF normalizado a LF:

| Artefacto | SHA-256 LF |
|---|---|
| `evals/s274_banked_funnel_v1.json` | `656e6f0be525bbeedb5871d90af20eaaaad9a3aa7c2df1902a38028ba7744a30` |
| `evals/s274_bloquesCD_closeout_v1.yaml` | `faa1db3207096ad22cb5b0782db68b652408548971ada34d8f4034b78ead9b6a` |
| `evals/s270_gold_adjudication_v1.yaml` | `51a64a10172557ffb8d06c9c89887d1ac6f9fb312f0b1387f6a36db6fb1ca436` |
| `evals/s269_goldreview_packet_v1_ADJUDICADO.md` | `b28255a64fe91ea76c727f1a6c8e942e1e0a7aed01a835b3a740ec40ad7f6dd9` |
| `evals/s235_direct_clause_bound_score_packet_v1.json` | `b9d7d4036c9aa00aeb521628da7e876cbc04ccb7ea6fa48a130960c43f2c8f48` |
| `evals/s113_full_contexts_freeze_v1.json` | `556490dd74056603b6b8f8c8d885c55820957761bbd6407bb1dcf8f533434498` |
| `evals/s126_upstream_residual_audit_v1.json` | `1bf5f8e5323239d3a83ef1d69fde6109d773edbbe3cfe1f367b4636a682895ac` |
| `evals/gold_answers_v1.yaml` | `c16a20ad8d6a5c2f3dc6cdd53080207d8072d43e48910da5aacd63f9edb8cff2` |

SHA-256 de bytes de los renders target:

| Render | SHA-256 |
|---|---|
| `hp011_obl_2f5d79e3_p63.jpg` | `536cb96797bc7e0dd348dd313edbc0afdd79e06ff85ff35d8598ac4a374c9635` |
| `hp011_obl_2f5d79e3_p63_zoom_ri_500dpi.jpg` | `7d7479592f5834b183e4f6bcf981c3c2feccff699111f132733a559b99398d80` |
| `cat018_obl_7bba8d03_p21.jpg` | `6acc21cbefb0bd8a2d756255220297735d86d022978f1ef6d2a2151911393d1f` |
| `cat018_obl_015f9b9a_p70.jpg` | `05934e2280796adaca12782fcdd48f8dfe6333bae3808b8ad2913bbc7eb8f572` |
| `hp002_obl_a5d9fa1f_p28.jpg` | `efc0cc2c6aa7a01921b1dca0349ac1c0393ce85a550f53555bbb0fd83dc54be1` |
| `hp017_obl_b2043cd4_p42.jpg` | `73e1107bf0e45db183a1561825535fd5230890ee158634b00fc34727f78141fc` |
| `hp017_obl_7aa72371_p42.jpg` | `73e1107bf0e45db183a1561825535fd5230890ee158634b00fc34727f78141fc` |

El builder falla cerrado ante cualquier hash distinto o falta de span/render.

## Población y unidad de análisis

Targets, exactamente los seis residuales S274:

1. `obl_2f5d79e354b9` · hp011.
2. `obl_7bba8d03d496` · cat018.
3. `obl_a5d9fa1f9253` · hp002.
4. `obl_015f9b9aaa3a` · cat018.
5. `obl_b2043cd4379b` · hp017.
6. `obl_7aa723717412` · hp017.

La unidad no es «todo lo útil que aparece en una página». Es la comparación
entre: pregunta, átomo canónico vigente, unidad contada en el ledger, evidencia
realmente servida y respuesta congelada.

Se añaden controles inertes, fijados en la preregistración, para calibrar cada
eje. No cuentan en el funnel y no se añaden ni sustituyen después de observar
outputs.

## E1 — Contrato de evidencia, con buckets no colapsados

Cada caso recibe una sola etiqueta:

- `EXACT_SERVED`: el predicado completo está en spans realmente servidos, con
  identidad atestada y sin contradicción material no declarada.
- `NOT_SERVED`: existe soporte decisivo en el corpus, pero no estaba en la vista
  congelada; corresponde a upstream/retrieval, no a síntesis.
- `IDENTITY_UNATTESTED`: el texto existe, pero el binding producto/documento no
  está acreditado.
- `SOURCE_CONFLICT`: dos fuentes aplicables servidas sostienen predicados
  incompatibles y la respuesta no puede resolverlos sin disclosure.
- `CORPUS_ABSENT`: no existe soporte decisivo en la población de fuente
  congelada.
- `UNCERTAIN`: el packet no permite demostrar una de las anteriores.

La presencia de palabras sueltas no basta; deben estar entidad, relación,
valor, condición y qualifiers materiales. Un span servido pero no citado sigue
siendo `EXACT_SERVED` para E1.

Controles E1: un `EXACT_SERVED`, un `NOT_SERVED` y un `SOURCE_CONFLICT`. El gate
es **3/3 exacto por revisor**. Los buckets sin control (`IDENTITY_UNATTESTED` y
`CORPUS_ABSENT`) pueden describirse, pero no sostener una mutación en esta ronda.

E1 es diagnóstico: aun con acuerdo, solo puede proponer un re-bucket o una
especificación de disclosure para una ronda posterior. No cambia el KPI S275.

## E2 — Protección de la adjudicación S270

S270 es el prior vinculante. Esta ronda **no vuelve a preguntar si un hecho es
CORE o supplementary** y prohíbe usar como razón que el mecanismo no lo haya
convertido, que parezca demasiado detallado o que falten cinco puntos.

Solo se puede reabrir un caso si el packet demuestra uno de estos defectos
estructurales nuevos:

- `REOPEN_NO_GOLD_BIJECTION`: la unidad contada no corresponde a ningún átomo
  vigente de `gold_answers_v1.yaml`.
- `REOPEN_SPLIT_CARDINALITY:<alias>`: un único átomo vigente se cuenta como dos
  o más obligaciones independientes.
- `REOPEN_DERIVED_SUBCLAUSE`: una subcláusula separable fue promovida desde el
  contexto servido aunque el contrato canónico no la exige como unidad propia.
- `REOPEN_PIXEL_OR_SOURCE_CORRECTION`: el píxel o la fuente verificable invalida
  el predicado adjudicado y la corrección no estaba ya registrada en S270.
- `REOPEN_GOLD_OR_QUESTION_CHANGED`: cambió el gold o la pregunta después de la
  adjudicación congelada.
- `LOCK_PRIOR_S270`: ninguno de los defectos anteriores está demostrado.
- `UNCERTAIN`: evidencia insuficiente; tiene el mismo efecto operativo que
  `LOCK_PRIOR_S270`.

La elegibilidad se congela antes de ejecutar: cuatro targets solo permiten
`LOCK_PRIOR_S270`; uno puede probar `REOPEN_NO_GOLD_BIJECTION`; y el par hp017
puede probar `REOPEN_SPLIT_CARDINALITY`. La tabla de mapping permanece fuera del
packet ciego.

Controles E2: dos locks de signo distinto ya adjudicados, el merge histórico
`obl_16637b935bd4` + `obl_0d6a30948dfd` como split positivo y el micro-predicado
«120 % + A11–C32» como derived-subclause positivo. El gate es **4/4 exacto por
revisor**. Un error invalida todo E2 de ese revisor; no hay retry.

Incluso con acuerdo del dúo, E2 solo produce una recomendación para Alberto. La
edición del gold, la reatomización y cualquier efecto de denominador necesitan
marca humana y una proyección determinista posterior.

## E3 — Cobertura semántica sin crédito post hoc

Etiquetas:

- `CONVEYED`: la respuesta expresa el predicado completo semánticamente.
- `PARTIAL`: expresa el kernel, pero pierde un qualifier material.
- `MISSING`: no expresa el predicado.
- `CONTRADICTED`: expresa una relación o valor incompatible.
- `UNCERTAIN`.

Controles: dos `CONVEYED` (`obl_0db2b9f2842a`,
`obl_e265a4c97a31`) y dos `MISSING` (`obl_b6f6211be439`,
`obl_161564ff41bf`) en la respuesta congelada. Gate: **4/4 exacto por revisor**.

E3 no puede mover target→OK en S275. Un `CONVEYED` target solo abre un finding de
posible falso negativo del matcher. Para conceder crédito haría falta otra
preregistración que congele la regla antes del score, la aplique a la población
completa definida allí y pase controles/regresiones disjuntos. Así se elimina la
regla semántica elegida después de ver el caso.

## Cegado ejecutable

El builder produce dos artefactos distintos:

1. `review_packet`: casos mezclados con semilla fija y aliases opacos; contiene
   únicamente la información necesaria para E1/E2/E3.
2. `private_mapping`: qid, obligation id, target/control, etiquetas esperadas de
   controles y elegibilidad E2. Nunca se pasa a los modelos.

Los adjudicadores reciben solo la rúbrica y `review_packet`, en llamadas nuevas
con `--no-tools`: sin shell, repo, web, DB, memoria de sesión, nombres S269/S270,
veredictos previos, estados target/control ni proyección KPI. Los aliases no
codifican qid ni clase. El coordinador verifica el hash exacto del packet enviado.

Cada revisor devuelve JSON estricto para todos los aliases, con una etiqueta por
eje, evidencia localizada y una razón breve. No puede pedir más contexto. Cero
retries automáticos.

## Regla de decisión

- Se puntúa primero la calibración, sin targets visibles al scorer humano.
- Un eje de un revisor solo es válido si pasa todos sus controles exactos.
- Una recomendación target requiere que **ambos** revisores tengan el eje válido
  y coincidan en la misma etiqueta. No hay mayoría, desempate ni síntesis que
  sustituya el desacuerdo.
- Un desacuerdo, `UNCERTAIN` o gate fallido se presenta tal cual y conserva el
  estado vigente.
- La tabla target/control y cualquier escenario aritmético se revelan únicamente
  después de sellar los dos outputs.

## Stop rules, presupuesto y efectos prohibidos

- STOP ante hash distinto, fuente/render ausente, packet no determinista, salida
  incompleta, JSON inválido o cualquier fallo de calibración.
- STOP ante contaminación: acceso del adjudicador al repo/mapping, aparición de
  qid/obligation ids, estado target/control, veredicto S270 o KPI en su contexto.
- Cero retries, cero nuevos casos y cero cambio de rúbrica tras el primer output.
- Techo adicional de ejecución de modelos de esta v2: USD 6; registrar tokens,
  configuración y recibos. Cero llamadas al bot, Railway, Supabase o held-out.
- Prohibido editar `gold_answers_v1.yaml`, llamar `gold_store`, bankar, desplegar
  o contabilizar E3 como OK dentro de S275.

## Salidas previstas

1. Builder, tests de determinismo y hashes.
2. Packet ciego y mapping privado versionados por separado.
3. Dos outputs raw, calibración automática y join por alias.
4. Packet de decisión para Alberto con evidencia, desacuerdos y escenarios
   aritméticos, pero sin ejecutar cambios.
5. Closeout que declare explícitamente que las conclusiones solo cubren estos
   seis residuales y estos controles.
