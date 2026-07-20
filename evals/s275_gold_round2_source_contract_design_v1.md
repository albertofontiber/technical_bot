# S275 — Gold round 2 con lente source-contract

## Decisión que esta ronda puede informar

Auditar los seis `synthesis-miss` que permanecen en el funnel banked S274 sin
volver a probar la familia de anexo ya agotada. La pregunta es estricta:

> ¿Cada obligación exige del bot exactamente un predicado material para la
> pregunta que, además, está contratado por un span completo de la evidencia
> servida? ¿O el ledger está contando granularidad, ejemplos o anchors que el
> contrato fuente↔pregunta no justifica?

La ronda **no mejora el bot**, no mueve hechos automáticamente y no autoriza
ediciones de gold. Produce un packet de decisión para Alberto, dueño del gold
(DEC-025). Cualquier efecto en el denominador o en `OK` requiere su marca,
edición posterior vía `gold_store` y una proyección determinista separada.

## Objetivo y métrica visibles

- Foto congelada: 146 OK / 6 synthesis-miss / 2 retrieval-miss / 154 = 94,81 %.
- Objetivo externo: 151/154 para superar el 98 %; faltan +5 bajo el ledger
  vigente.
- Métrica **de esta ronda**: acuerdo por caso sobre tres ejes independientes,
  más calibración en cuatro controles. El porcentaje final queda oculto a los
  revisores durante la adjudicación y se calcula después.
- Éxito metodológico: los seis casos reciben un veredicto trazable y los
  revisores pasan los controles. Un resultado `KEEP_CORE ×6` es válido; no hay
  cuota de demotes ni de créditos.

## Autoridades congeladas

Los hashes son SHA-256 con CRLF normalizado a LF:

| Artefacto | SHA-256 LF |
|---|---|
| `evals/s274_banked_funnel_v1.json` | `656e6f0be525bbeedb5871d90af20eaaaad9a3aa7c2df1902a38028ba7744a30` |
| `evals/s274_bloquesCD_closeout_v1.yaml` | `faa1db3207096ad22cb5b0782db68b652408548971ada34d8f4034b78ead9b6a` |
| `evals/s270_gold_adjudication_v1.yaml` | `51a64a10172557ffb8d06c9c89887d1ac6f9fb312f0b1387f6a36db6fb1ca436` |
| `evals/s269_goldreview_packet_v1_ADJUDICADO.md` | `b28255a64fe91ea76c727f1a6c8e942e1e0a7aed01a835b3a740ec40ad7f6dd9` |
| `evals/s235_direct_clause_bound_score_packet_v1.json` | `b9d7d4036c9aa00aeb521628da7e876cbc04ccb7ea6fa48a130960c43f2c8f48` |
| `evals/gold_answers_v1.yaml` | `c16a20ad8d6a5c2f3dc6cdd53080207d8072d43e48910da5aacd63f9edb8cff2` |

La fuente al píxel ya fue renderizada y adjudicada en S269. Esta ronda la
relee, pero no reabre su transcripción salvo que encuentre un defecto nuevo:

- hp011: `s269_goldreview_renders/hp011_obl_2f5d79e3_p63.jpg` y zoom 500 dpi;
- cat018: `.../cat018_obl_7bba8d03_p21.jpg` y `.../cat018_obl_015f9b9a_p70.jpg`;
- hp002: `.../hp002_obl_a5d9fa1f_p28.jpg`;
- hp017: `.../hp017_obl_b2043cd4_p42.jpg`.

## Población congelada

Casos target, exactamente los seis del cierre S274:

1. `obl_2f5d79e354b9` · hp011 · estado especial `r.i = --`.
2. `obl_7bba8d03d496` · cat018 · pestaña Programa + Zona/CBE.
3. `obl_a5d9fa1f9253` · hp002 · reset inicial → nominal 100 %.
4. `obl_015f9b9aaa3a` · cat018 · TONE/volumen/sirenas SND.
5. `obl_b2043cd4379b` · hp017 · instrucción de entrada.
6. `obl_7aa723717412` · hp017 · instrucción de salida.

Controles que no pueden mover el funnel S274:

- `obl_b6f6211be439` · hp002 · aislamiento previo de controles/alertas/extinción
  — control `CORE` material.
- `obl_0d6a30948dfd` · hp017 · probar todas las reglas en puesta en marcha —
  control `CORE` material ya convertido.
- `obl_161564ff41bf` · hp011 · intervalos de 5 s — control
  `SUPPLEMENTARY` adjudicado.
- `obl_07eee3300535` · hp002 · anchors 120 % / A11-C32 en pregunta de flujo
  bajo — control `SUPPLEMENTARY` adjudicado.

No se añaden casos tras ver resultados. Los controles se mezclan en el packet
con IDs `R2-01..R2-10`; la tabla target/control se revela solo al scorer local.

## Unidad de decisión y rúbrica pre-registrada

Cada revisor devuelve, sin proyección de KPI, estos ejes:

### E1 · Contrato de evidencia

- `EXACT_SERVED`: el predicado completo (valor/entidad/condición/acción y
  qualifiers) está en uno o más spans acotados realmente servidos, con identidad
  del producto atestada y sin contradicción no declarada.
- `SOURCE_CONTRACT_GAP`: falta en la vista servida una parte necesaria del
  predicado, la identidad no está atestada o el soporte es contradictorio.
- `UNCERTAIN`: no puede demostrarse con el packet; no autoriza cambios.

Un fragmento servido pero no citado sigue siendo `EXACT_SERVED`; eso distingue
contrato de evidencia de selección/citación. La mera coincidencia de tokens no
cuenta como predicado completo.

### E2 · Requiredness y atomicidad para la pregunta

- `KEEP_CORE`: omitir el predicado cambia materialmente el diagnóstico, la
  acción, la seguridad o la ejecutabilidad de lo pedido.
- `SUPPLEMENTARY`: correcto y útil, pero ejemplo, precisión periférica o detalle
  no necesario para responder la pregunta concreta.
- `MERGE_REATOMIZE:<otro-id>`: dos obligaciones son partes inseparables de un
  único hecho atómico del gold; conservar ambas como unidades independientes
  doble-cuenta.
- `RESPEC`: el contrato debe cambiar (p. ej. disclosure), con texto exacto
  propuesto.
- `UNCERTAIN`: mantiene el estado actual y se eleva a Alberto.

Requiredness codifica importancia para **esta pregunta**, no provenance. Que el
span esté servido no convierte automáticamente todo su contenido en `CORE`.
La adjudicación S270 es el prior: solo se recomienda cambiarla con un defecto de
contrato nuevo y explícito, no porque el mecanismo haya fallado cuatro veces.

### E3 · Cobertura semántica de la respuesta congelada

- `CONVEYED`: la respuesta transmite el predicado completo aunque no use los
  anchors literales.
- `PARTIAL`: transmite el kernel pero pierde un qualifier material.
- `MISSING`: no transmite el predicado.
- `CONTRADICTED`: transmite un valor/relación incompatible.
- `UNCERTAIN`.

Este eje audita posibles falsos `synthesis-miss` del matcher. No se concede
`CONVEYED` por palabras sueltas ni por una conclusión operativa compatible si
la relación requerida no está expresada.

### Efectos permitidos tras adjudicación humana

- `KEEP_CORE + MISSING/PARTIAL`: sigue como miss; cero movimiento contable.
- `KEEP_CORE + CONVEYED`: puede mover miss→OK, sin cambiar denominador, solo si
  la regla semántica es generalizable y el mismo criterio pasa los controles.
- `SUPPLEMENTARY`: reduce denominador en uno; nunca suma simultáneamente un OK.
- `MERGE_REATOMIZE`: reduce denominador por la cardinalidad fusionada; el carrier
  conserva el estado que corresponda.
- `SOURCE_CONTRACT_GAP`: no da OK de síntesis; se re-bucketiza o excluye solo con
  especificación aprobada.

## Protocolo de revisión

1. Construir un packet determinista con pregunta, hecho atómico vigente,
   obligación, span servido exacto, respuesta congelada y cita/renders.
2. Dos revisores frontera independientes: GPT-5.6 Sol xhigh y Fable 5. No ven la
   proyección final ni una recomendación por target. Temperatura/configuración
   del runner canónico; outputs versionados.
3. Cada revisor clasifica los 10 casos antes de una síntesis. No puede omitir
   casos ni usar `mecanismo agotado`, `necesitamos +5` o coste hundido como razón.
4. Gate de calibración: ambos controles `CORE` deben salir `KEEP_CORE` y ambos
   controles supplementary deben salir `SUPPLEMENTARY`, salvo finding de fuente
   nuevo verificado al píxel. Si un revisor falla >1/4 controles, sus veredictos
   target quedan informativos y no pueden sostener una edición.
5. Desacuerdos target quedan visibles. No se resuelven por mayoría automática:
   se presentan a Alberto con evidencia y recomendación del coordinador.
6. Solo después se revela y calcula la proyección aritmética, por escenarios
   exactos, sin redondear `>=98 %`.

## Gates, stop rules y presupuesto

- Techo de modelos: USD 6; objetivo aproximado USD 5. Cero retries automáticos.
- STOP si falla un hash, falta un render/span, un revisor no devuelve 10/10 o
  falla la calibración indicada.
- STOP si aparece un cambio de fuente/gold no registrado: se abre una ronda
  nueva, no se corrige en caliente.
- Cero llamadas al bot, DB o targets; held-out embargado.
- Cero edición de `gold_answers_v1.yaml`, cero `gold_store.upsert`, cero banking
  y cero ship en esta fase.

## Alternativas consideradas

- **Serving-view generalizada:** familia técnica plausible (~USD 10), pero
  reabre el contrato de lanes S110/S111 y debería construirse solo después de
  saber qué obligaciones siguen siendo legítimas.
- **Eval orgánico:** mejor árbitro de utilidad real, pero no está disponible
  hasta que haya técnicos; no corrige hoy posibles defectos del ruler.
- **Probe #5 del anexo:** descartado por el cierre pre-registrado S274 y por
  exposición repetida a los mismos targets.
- **Demotar todo lo que el mecanismo no convierte:** metric gaming explícito;
  prohibido por la rúbrica y los controles.

## Por qué es BP, estructural y escalable

- **BP:** separa soporte, requiredness y cobertura, evitando que un matcher
  léxico o el resultado de un mecanismo decidan el gold.
- **Estructural:** audita el contrato que gobierna todos los obligations, no
  introduce reglas por fabricante ni por target en runtime.
- **Escalable:** la rúbrica se aplica a cualquier manual/pregunta; los casos
  concretos solo son la población congelada de esta auditoría.
