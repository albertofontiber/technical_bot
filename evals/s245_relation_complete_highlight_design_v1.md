# S245 — resaltado pre-respuesta de relaciones completas

## Objetivo causal

Reducir los 11 `synthesis-miss` atribuidos por S243 a pérdida de detalle dentro
de un fragmento ya citado. El residual de selección `hp011/F13` queda fuera.
Ninguna métrica intermedia mueve hechos oficiales: 143/157 permanece canónico
hasta un A/B end-to-end y la regresión completa.

## Antecedentes que limitan el diseño

- **S176, misma cohorte no-target y métrica de cobertura:** una tarjeta literal
  seleccionada por BM25 y añadida después de la respuesta pasó de 26 a 27/37
  puntos (+1), mantuvo 6/14 preguntas completas (+0) y añadió 18 unidades. Esa
  vía post-respuesta está cerrada.
- **S170/S171, relation store:** la extracción LLM por chunk cerró por transporte
  antes de medir semántica y prohibió una tercera iteración del store. S245 no
  persiste ni genera relaciones y no reabre ese store.
- **S242, planner + writers:** 0 ganancias estables. Su conflicto hp017 era
  preexistente también en canónico y baseline; no se atribuye al tratamiento.

S245 solo merece target si demuestra utilidad pre-respuesta que S176 no mostró.

## Intervención mínima

### Representación efímera

Un atomizador local detecta spans técnicamente densos dentro de cada fragmento
servido. Un átomo es una **relación completa en una sola unidad**: su contenido
debe mantener juntos, según aplique, condición + acción + target; valor + unidad
+ límites + paso; cabecera + fila; padre + miembro; o warning/requisito + acción.

El runtime no crea un store ni duplica el manual. Inserta delimitadores internos
alrededor de los spans exactos antes de llamar al writer, por ejemplo dos partes
con el mismo ID para una cabecera y su fila. El texto fuente y los números de
fragmento permanecen idénticos. La única instrucción nueva indica que, si un
resaltado responde a la pregunta, se conserve la relación completa al redactar.

Los reconocedores son de forma fuente ES/EN: números/unidades/rangos/tolerancias,
condicionales y dependencias, tablas/listas/definiciones, lenguaje obligatorio o
de seguridad/verificación y enumeraciones. No contienen QIDs, fabricantes,
productos, valores esperados ni tipos de relación del residual.

`reason_labels` son explicativos y pueden ser múltiples; el gate no finge medir
una taxonomía semántica que el gold existente no etiqueta. La propiedad medida
es que una cita relacional completa cabe en **un** átomo source-bound.

### Contrato exacto de identidad

- offsets: índices de code points del `str` Python original, `[start,end)`;
- contenido: concatenación exacta de spans en orden, con joiner fijo `\n\n`;
- hash: SHA-256 de UTF-8 del contenido exacto;
- ID: hash de `fragment_number`, `candidate_id`, spans, hash de contenido y
  versión de contrato;
- Unicode no se normaliza para identidad/reconstrucción; NFKD/casefold solo se
  permite en detección y scoring;
- máximo 900 caracteres de contenido por átomo, 48 átomos por fragmento y 96 por
  request; el exceso falla cerrado y deja el brazo inelegible, nunca trunca.

El atomizador **no detecta conflictos cross-fragment**. El conflicto hp017 se
mantiene como guardarraíl end-to-end separado: el tratamiento no puede empeorar
su disclosure frente al control contemporáneo.

## Gate A — representación local, cero llamadas

Cohorte: los mismos 14 items/37 puntos de S171/S147. Es independiente de los
cuatro targets pero ya fue expuesta en mecanismos anteriores; es desarrollo
reutilizado, no held-out virgen.

El implementador solo usa fixtures sintéticos para unit tests. Después se abre
el gate real una vez; no se retoca v1 con sus errores.

Pasa solo si:

- 34/37 citas exactas (≥91,89 %) están contenidas cada una en un único átomo;
- recall ≥80 % por tabla, prosa, fuente ES real y fuente EN real;
- source-bound, reconstrucción, determinismo, hashes y límites: 100 %;
- densidad global de caracteres no-blancos resaltados ≤35 % y mediana por item
  ≤40 %;
- fixture negativo sin ninguna forma técnica reconocida: cero átomos.

Las fuentes EN congeladas son `s147_src_01/04/06/08/09/11/14`; las fuentes ES
son `s147_src_02/03/05/07/10/12/13`.

Un PASS de A solo autoriza B. No demuestra que el writer use el resaltado.

## Gate B — A/B contemporáneo no-target, antes de cualquier target

Población: las 14 preguntas S173 y sus 37 answer-points S171. Antes de llamar se
congelan por path+SHA: source packet, orden, runner, atomizador, renderer,
prompts exactos, modelo, parámetros, max tokens, scorer, SDK/runtime y manifest
de contexto. El gold de puntos no entra en generación.

- Writer: el mismo modelo de producción de la foto canónica, mismo system prompt,
  contexto, orden de fragmentos, `temperature=0` y presupuesto de salida en ambos
  brazos.
- Control: contexto original. Tratamiento: solo delimitadores + instrucción S245.
- Dos repeticiones por brazo e item; orden AB/BA alternado por hash del item.
- Sin retries. Respuestas y receipts se guardan antes de abrir el gold.
- Ganancia estricta: tratamiento 2/2 y control 0/2 para el mismo answer-point.
- Regresión estricta: control 2/2 y tratamiento 0/2. Mixtos son advisory.

Pasa solo con ≥4 ganancias estrictas de punto, ≥2 preguntas que sean completas
2/2 en tratamiento y 0/2 en control, cero regresiones estrictas, cero citas
inválidas y cero fallos source-bound. Es deliberadamente al menos tan exigente
como el gate que S176 no superó. Si falla, S245 se cierra sin target ni tuning.

## Gate C — target causal, solo si A+B pasan

Se congela otro A/B contemporáneo de los cuatro qids, con contextos, writer,
prompts, scorer, orden y parámetros ligados por SHA. Dos repeticiones por brazo;
las definiciones de gain/regression 2/2 vs 0/2 son las mismas que en B.

Continuar exige ≥3/12 ganancias estrictas, cero regresiones estrictas sobre
obligaciones ya cubiertas por el control, cero citas inválidas y disclosure de
hp017 no peor que el control. La respuesta canónica histórica es referencia de
producto, no brazo causal. Antes de default-on siguen siendo obligatorios los
143 hechos protegidos completos.

## Por qué es una hipótesis distinta y acotada

- S176 añadió evidencia después de una respuesta inmutable; S245 modifica solo
  la representación que ve el writer antes de sintetizar.
- S242 dejó que un LLM inventara obligaciones; S245 marca spans exactos por forma
  fuente, sin planner, selector global ni retry.
- S206 dio facetas abstractas; S245 liga cada señal a bytes concretos.
- No hay append post-respuesta, relation store, template por producto ni cambio
  de retrieval.

## Alternativas descartadas y riesgos

- Otra selección/rerank: 11/12 son downstream del fragmento citado.
- Cubrir una cita con varios átomos: no preserva el vínculo y queda prohibido.
- Densidad 70 %: casi trivial; se reduce a 35/40 %.
- Detector local de conflictos: promesa imposible; fuera del mecanismo.
- Golds nuevos: innecesarios para este primer gate.

Riesgos: el parser ES/EN puede fallar ante OCR; el cohort de desarrollo no es
virgen; el inline markup puede distraer al writer; un PASS local puede no dar
ganancias. Gates B y C existen precisamente para matar esas posibilidades sin
racionalización.

`chunks_v2=ACTIVE_READ_ONLY`; `chunks_v3=FINAL_NO_GO_CHUNKS_V3_WHOLESALE` como
línea explícita de evaluación; Railway demo no bloquea PR/merge con CI verde.

