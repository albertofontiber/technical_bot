# S118 — puente híbrido del benchmark congelado

## Veredicto que este diseño permite

S118 crea un **manifest diagnóstico híbrido**. No crea todavía un denominador
atómico final, no mejora el bot y no mueve facts a `OK`.

Su función es reconciliar sin overfit la población histórica S100 con:

1. las transformaciones atómicas M0 que afectan a esa población;
2. tres parents corregidos por S118 (`hp013#1`, `hp015#2` y `hp015#0`);
3. los blockers M1 ya conocidos entre los parents no transformados.

La revisión adversarial detectó que `hp015#0`, que heredaba `OK`, repetía la
misma imposibilidad no demostrada retirada en `hp015#2`. También encontró 33
carries con blockers M1 conocidos, 29 de los cuales heredaban `OK`. S118 los
separa y les retira crédito diagnóstico; no los borra ni los declara fallos del
RAG.

## Tres tracks que no deben mezclarse

- **Histórico comparable:** conserva la foto S100 de 127 parents puntuados y
  sirve únicamente para comparar con mediciones anteriores.
- **Híbrido diagnóstico:** proyecta 132 claims para organizar trabajo
  upstream/downstream. Su target de 126 es orientativo y no oficial.
- **Atómico oficial:** denominador, número de `OK` y target 95 % quedan `null`
  hasta cerrar requiredness/atomicidad con evidencia suficiente.

Un cambio de contrato de evaluación nunca cuenta como mejora del RAG.

## Por qué no se exige cerrar las 312 decisiones M1

Cerrar el ruler completo sigue siendo trabajo válido, pero no es una
precondición causal para medir y mejorar los 22 claims explícitos ya
transformados. S118 evita dos extremos:

- no bloquea todo el funnel hasta completar M1;
- no presenta como atómicos los carries que M1 todavía no ha verificado.

Los 33 blockers conocidos quedan en `known-m1-contract-hold`. Los otros 77
carries quedan como `provisional-legacy-carry-no-known-m1-blocker`: ausencia de
blocker conocido no equivale a aprobación atómica.

## Proyección portable de contratos S106

Los artefactos S106 completos estaban en otro checkout local. El runner ya no
depende de esas rutas para ejecutarse. Una operación separada y determinista:

1. valida por SHA el manifest M0 completo y el ledger M1 de 51 blockers;
2. reconstruye la población S100 por `(qid, SHA canónico completo del parent)`;
3. proyecta las 14 transformaciones M0 que intersectan la cohorte;
4. proyecta los 33 blockers M1 que coinciden con carries por
   `carry.<qid>.<parent_sha[:16]>`, pero almacena también el SHA completo;
5. congela ambos receipts y un `payload_sha256` en
   `s118_external_contract_projection_v1.json`.

La ejecución ordinaria consume solo esa proyección versionada. No selecciona
por stage, respuesta, fabricante, resultado del bot ni similitud textual.

## Binding de los hijos S118

`s118_child_claim_adjudication_v1.yaml` hace biyectiva la relación entre cada
hijo retenido y su subclaim aceptado. Para cada hijo congela:

- identidad completa del parent;
- hashes normalizados de subclaim, texto, valor y cita;
- chunk de evidencia, manual, página y hash del excerpt congelado;
- `basis=explicit`, track y requiredness;
- independencia del resultado runtime.

Cada retirada se liga 1:1 al hash de su subclaim no soportado. El runner falla
cerrado ante cambios de texto, tipo, página, cita, evidencia, cardinalidad o
requiredness.

## Correcciones S118

### hp013 / PWR-R

- Core explícito: batería de litio y módulo RTC.
- Supplementary explícito: PWR-R redundante de 9 a 30 V CC.
- Retirado: ausencia absoluta de batería tampón a bordo.

### hp015 / capacidad

- Supplementary explícito: máximo 32 detectores o pulsadores por zona.
- Retirados: imposibilidad absoluta de aislar un detector y causalidad no
  demostrada sobre todos los detectores.

### hp015 / arquitectura convencional

- Supplementary explícito: tres zonas convencionales y un riesgo.
- Retirado: inferir de esa arquitectura que es absolutamente imposible actuar
  sobre un detector concreto.

La respuesta técnica deberá ceñirse a lo positivo: el manual documenta la
desconexión por zona. No debe convertir falta de procedimiento documentado en
imposibilidad física absoluta.

## Conteos reconciliados

| Concepto | Conteo |
|---|---:|
| Parents históricos | 129 |
| Parents puntuados históricos | 127 |
| Meta-references excluidos | 2 |
| Parents M0 transformados | 14 |
| Parents S118 transformados | 3 |
| Carries sin transformar | 110 |
| Carries con blocker M1 conocido | 33 |
| Carries sin blocker M1 conocido | 77 |
| Claims transformados pendientes de replay | 22 |
| Denominador híbrido provisional | 132 |
| Target híbrido provisional al 95 % | 126 |
| Denominador/target atómico oficial | `null` |

Histograma híbrido provisional: 68 `OK`, 33 `known-m1-contract-hold`, 22
`pending-replay`, 2 `synthesis-miss`, 2 `retrieval-miss` y 5 `rest`.

## Política de stage

- Todo hijo transformado queda `pending-replay`; nunca hereda el stage del
  parent.
- Todo carry con blocker M1 queda en hold; conserva su stage histórico solo en
  un campo legacy sin crédito.
- Los otros carries conservan una foto provisional, no una aprobación atómica.
- Supplementary, derived, provenance, unresolved y withdrawn quedan fuera del
  denominador híbrido de contenido.
- M2.10 mantiene `facts_moved_to_ok=0` y autoridad exclusivamente upstream.

## Próxima ejecución barata

El siguiente paso permitido tras GO adversarial es diseñar un replay local de
los 22 claims transformados:

1. reutilizar receipts solo si coinciden pregunta, runtime, corpus, pool,
   top-k, contexto y respuesta;
2. acreditar retrieval/rerank determinísticamente cuando existan receipts
   exactos;
3. usar executor económico solo para residuos semánticos de synthesis;
4. reservar modelos caros para diseño, revisión de regresiones y survivors.

Ese replay podrá mejorar el diagnóstico de los 22 claims, pero no publicará un
95 % oficial hasta cerrar el contrato atómico pendiente.

## Seguridad y no autorizaciones

El runner restringe outputs al repositorio y prohíbe sobrescribir inputs
congelados. S118 no autoriza red, DB, modelos, extracción, carga de chunks,
serving, deploy, mutación de gold, relabel de facts ni replay completo.
