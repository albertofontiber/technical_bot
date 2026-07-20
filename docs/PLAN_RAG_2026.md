# Plan RAG 2026 — Technical Bot

> **Qué es este documento.** El doc CANÓNICO del roadmap + estado + qué sigue del Technical Bot.
> **Audiencia:** Alberto (decisión estratégica) y cualquier sesión futura — debe poder leerse en
> frío y saber qué hacer y por qué. **Fecha base:** 22 mayo 2026. **Última actualización:**
> 20 jul 2026 (S277 — C1 NO-GO vivo + gate P1 materializado offline).
>
> **El historial vive en [`docs/HISTORY.md`](HISTORY.md)** (movido en s56): log de sesiones
> s30→s55, rationale histórico de mayo 2026 (secciones originales ## 1-9, con su numeración —
> las citas antiguas tipo "PLAN §9.14" o "§660" resuelven allí) y changelog. Este fichero queda
> compacto a propósito: es el doc que se relee en cada arranque de sesión.
>
> **📍 Mapa canónico (un dueño por tema).** ESTE documento es el **único canónico** del
> **roadmap + estado + qué sigue**. Los demás lo referencian, NO lo duplican:
> `docs/RULER_DESIGN.md` = diseño del ruler (D1-D11 + §2 procedimiento + §8 taxonomía);
> `docs/DECISIONS.md` = el *por qué* de las decisiones med/alto; `TECH_DEBT.md` = deuda con
> triggers; `docs/ARCHITECTURE.md` = cómo funciona el sistema; `docs/HISTORY.md` = traza
> histórica (append-only). Si el rumbo aparece en dos sitios y discrepan, **manda éste**.
>
> **Principio rector.** Nada de quick fixes. Cada cambio debe ser (1) best practice con fuente
> identificable, (2) estructural — ataca la causa raíz, no el síntoma, (3) escalable a 30+
> fabricantes sin fricción por fabricante. Si una propuesta no cumple los tres, se declara como
> gap honesto.

<a id="estado-actual-s277--20-jul-2026"></a>
## Estado actual (S277 — 20 jul 2026)

**Marcador canónico sin movimiento desde S274: 154 facts = 146 OK · 6 synthesis-miss ·
2 retrieval-miss = 146/154 (94,81%); faltan +5 para 151 (≥98%).** Es la foto de trabajo
adjudicada; `official_atomic_kpi` sigue sin materializarse como KPI independiente. S277 no
banca facts, no cambia el denominador y no demuestra generalización.

**La observación viva cerró el recibo pendiente y mantuvo C1 en NO-GO.** La respuesta PEARL
aportada por Alberto fue una sola generación de 4.449 caracteres que Telegram dividió en dos
mensajes. No incluyó ninguno de los dos avisos F12 y afirmó un menú plano «8» sin revelar el
conflicto conocido 7-vs-8. `query_logs.response` se trunca a 4.096 caracteres, por lo que no es
autoridad sobre la respuesta completa. Resultado: el par legacy que convirtió el fact en el
probe S274 no equivale a un release C1 íntegro ni a síntesis fiable en vivo.

**Candidato de release C1 — PR #184, todavía no desplegado.** Se construyó un profile atómico
`coverage_c1_v1`, un seam único de serving, trazas privacy-safe y dos gates previos: A offline
prueba ensamblaje sin red; B GET-only prueba que, condicionado al prefijo congelado, el fetch
live alcanza el target PEARL en F12. A y B pasan, pero ninguno genera ni puntúa una respuesta;
por eso no autorizan release. El hash S113 se normalizó a LF para que el mismo pin valga en
Windows y Linux. `VISUAL_ASSETS_REGISTRY` es ortogonal y el contrato P1 conserva exactamente
su estado vivo; no lo apaga como efecto lateral.

**P1 end-to-end materializado offline, ejecución pagada todavía bloqueada.** El paquete sella
13 QIDs, 27 réplicas/27 generaciones y exactamente 81 llamadas a modelos; protege 43 filas
base de peso KPI 42, la guarda hp013 y el target compuesto hp017. Incluye scorer determinista,
preregistro, límite estático conservador de 6,777 USD bajo los tamaños preregistrados, techo duro
de 10 USD, WAL fsync/no-retry, identidad de release, proyección semántica de configuración,
fingerprint/fence y receipts internos ligados desde input preregistrado hasta respuesta/render.
El preflight se reconstruye al ejecutar; runtime, lease y request reservado se revalidan antes
de cada send; topología/claim/lease impiden doble runner y reinicialización de presupuesto. Estas
garantías son del orquestador offline. Toda reapertura reconstruye las 81 llamadas y sus respuestas,
revalida las 27 réplicas, exige 162 eventos WAL alternos y recompone el coste/presupuesto exacto.
La derivación productiva, los bytes SDK y el manifest live de RPC/ACL/índices/config siguen
pendientes del adapter, fence service y sus revisiones. Los CLI operativos están bloqueados por
máquina con `HOLD_FENCE_MANIFEST_CONTRACT_NOT_MATERIALIZED`; los hashes sintéticos actuales sólo
describen la superficie declarada. El control
almacenado de 0 USD confirma el conflicto hp017 en 3/3 y emite
`HOLD_PREPAID_KNOWN_CONFLICT_RISK`; nunca atribuye PASS/FAIL al candidato no medido.

**Stop-lines actuales:** release-config real no materializado; adapter productivo deliberadamente
ausente; manifest live RPC/index/config no materializado; identidad PostgREST read-only y fence
externo no provisionados; conflicto hp017 sin
resolver; gasto P1 no autorizado; lease filesystem sólo single-host y sin recuperación stale
automática. El dúo final Sol/Fable terminó y confirmó un blocker adicional para retirar la
stop-line: el manifest de implementation hashes aún no cubre transitivamente todo el código
ejecutado por scoring (al menos `src/rag/answer_planner.py`). También delega al adapter productivo
la validación terminal de rerank y la attestation externa de usage/coste. CI de la PR sigue
pendiente. No se han ejecutado las 27 réplicas, no existe `P1_PASS`, no se aplicó
la migración de trazas y no hubo escritura ni cambio de Railway/Supabase.

**Multi-turn/multi-hop permanece separado y `NOT_BUILT` (DEC-136).** El norte sigue siendo
orquestador transport-neutral, estado/event log durable, ingress idempotente, leases+fencing,
CAS propietario y outbox; single-hop barato por defecto, rewrite sólo para follow-ups
dependientes, 2 hops por defecto/3 hard cap y verifier fail-closed. No hay permiso de DDL/build
ni inferencia adicional para esta línea.

**Qué sigue, por orden:** (1) cerrar suite amplia + CI de la PR #184 —dúo final completo y suite
P1 focal 181/181—; (2) en una fase acotada del adapter/config, cerrar el manifest transitivo,
stop reason de rerank y receipts externos de usage/coste; (3) resolver o revelar de forma segura
el conflicto hp017 7-vs-8 antes de gastar; (4) materializar el contrato live de
RPC/ACL/índices/config, configuración, identidades, adapter y receipts externos, y pedir
autorización explícita para P1;
(5) sólo si P1 da PASS vigente, seguir el runbook de deploy y autorizar aparte el canary; (6)
para el +5, usar eval orgánico/fresco u otra familia causal —P1 es gate de release, no árbitro
del 98%—; (7) la Fase 0 conversacional requiere una decisión separada de Alberto.


<a id="estado-anterior-s205--18-jul-2026"></a>
## Estado anterior (S205 cerrado — 18 jul 2026)

**La foto diagnóstica comparable más reciente es 157 facts: 143 OK · 12 synthesis-miss ·
2 retrieval-miss = 91,08% OK, gap 11 facts hasta el objetivo ≥98% (154/157).** No es todavía un KPI atómico oficial ni
un resultado desplegado: parte del puente híbrido S133, conserva 77 legacy carries pendientes y
presupone dos candidatos locales/default-off. El bridge exacto es: S172 lleva la extracción
`10^5` de hold→OK y deja 141/157; S188 añade dos facts de compatibilidad/topología de
retrieval→OK, dejando 143/157. Estos movimientos sí son crédito diagnóstico de etapa, pero su
crédito productivo sigue siendo cero mientras los flags estén apagados y falte generalización
independiente.

**El orden de trabajo sigue en síntesis porque retrieval es residual (2 vs 12), y S192-S193 han
aislado el siguiente cuello sin tocar targets.** Sustituir Sonnet 4.6 directamente por Terra
`low` es **NO-GO**: 25/37 vs 26/37 puntos, −1 neto, 2 regresiones, +1 pregunta completa;
$0,259085. En cambio, separar planificación y redacción sí da señal causal: S193 conserva la
respuesta base y anexa determinísticamente spans ligados a IDs, por lo que un ID elegido no puede
omitirse. El candidato alcanza 31/37, **+5 puntos, +2 preguntas completas y 0 regresiones** por
$0,071248. No pasa el gate completo porque el selector solo cubre 27/34 puntos disponibles en el
store (79,4% < 90%), aunque la precisión de unidades sí pasa (78,3% ≥75%). Conclusión: el
renderizado con postcondición es candidato estructural; el selector de obligaciones es ahora el
cuello medido. S193 no mueve facts ni autoriza producción. No se ajustará el prompt sobre estas 14
preguntas; el siguiente paso exige descomposición de pregunta y validación fresca.

**S194 ejecutó esa validación fresca y se cerró antes del selector, sin mover facts.** Se congeló
por GET-only una cohorte nueva de `chunks_v2`: 25.090 filas leídas, 14 documentos/fabricantes
distintos, 7 tabla + 7 prosa, cero overlap documental/UUID/pares de desarrollo y manifest
pre-autor de cada unidad fuente. El autor económico Haiku produjo 13 preguntas elegibles,
7 tabla + 6 prosa y 50 puntos, pero **1/14 output fue inválido** porque asignó una cardinalidad de
soporte fuera del contrato. El gate exigía cero inválidos, así que el estado es
`NO_GO_COHORT_CONSTRUCTION`. Coste: **$0,078186**. No se llamó a Luna, no se abrió ninguno de los
cuatro targets, no se ejecutó el compilador sobre ellos y el crédito diagnóstico/productivo es
0. No se repite esta cohorte ni se relajan umbrales. La causalidad útil es upstream: el schema
estructurado del autor describía `support_unit_ids` como array, pero no imponía en JSON Schema el
`minItems=1`, `maxItems=3` y `uniqueItems=true` que el validador sí exigía. El siguiente intento,
si se prioriza, debe corregir ese contrato **antes** de congelar otra cohorte documental nueva;
no reutilizar outputs ni tocar el selector S193 sobre poblaciones ya observadas.

**S195 corrigió la clase de cardinalidad, pero destapó el siguiente límite upstream y también
se cerró sin mover facts.** Anthropic no admite `maxItems`/`uniqueItems` en el dialecto compilado,
por lo que se separó el contrato canónico exacto de un transporte sin arrays: cuatro slots de
puntos y tres slots de soporte por punto, con IDs ligados al documento, normalización determinista
y validación semántica externa Luna prevista para los 14 ítems. Sol 5.6 xhigh revisó el diseño;
la fila histórica llamó `omitted_unavailable` a lo que en realidad era ausencia de ejecutor
versionado en ese worktree, no indisponibilidad global de Fable 5. La cohorte fue
enteramente nueva y excluyó S194: 25.090 filas GET-only, 14 documentos/fabricantes, 7+7, cero
overlap previo/target y cero equivalencia exacta de contenido/extracción. Los 14 conteos de tokens
pasaron, pero la primera inferencia Haiku fue rechazada con 400
`Schema is too complex for compilation`; `max_retries=0`, checkpoint previo, **0 inferencias
completadas**, Luna 0 llamadas y targets/planner cerrados. Estado:
`NO_GO_EXECUTION_CONTRACT_REJECTED`; crédito de facts 0. No se reutiliza S195.

DEC-104 fijó que la reapertura legítima no era “añadir keywords” ni simplificar sobre la población
observada: primero un canary sintético separado con schema estático mínimo y solo después otra
cohorte nueva que excluya S194+S195. La simplificación debía conservar slots estructurales y mover
pertenencia/duplicados de IDs al validador determinista, evitando enums dinámicos y `$defs`.

**S196 completó ese canary y es GO del transporte, no del sistema.** El schema rectangular estático
(4 puntos × 3 soportes) contiene cero arrays, refs/defs, combinators, enums o consts; las restricciones
específicas viven en validación determinista. Sobre dos unidades 100% sintéticas, Haiku 4.5 compiló,
devolvió `end_turn` y produjo dos puntos válidos en una única inferencia. SDK 0.97.0, cero retries,
coste $0,002583. Sol 5.6 xhigh revisó tres iteraciones; Fable volvió a quedar mal rotulado por la
misma ausencia local de ejecutor versionado. Crédito de
facts 0 y ningún documento/target/Luna/planner se abrió. El resultado autoriza solamente un S197
separado: cohorte real nueva, disjunta de S194+S195, mismo schema genérico y validación externa Luna.

**El pre-S197 deja ese siguiente tramo listo sin ejecutar la cohorte.** Se versionó el runner
directo de `claude-fable-5` usado anteriormente desde Codex y el dúo byte-bound con Sol 5.6 xhigh,
eliminando la dependencia de un agente `.claude` local y el estado ambiguo
`omitted_unavailable`. También quedaron preparados el doble freeze GET-only de una cohorte nueva
disjunta de S194+S195 y el gate Haiku→Luna con schema S196, cero retries, locks, checkpoints,
presupuesto ≤$3 y STOP upstream. La verificación local pasa; dos intentos reales de Fable usaron
el pin exacto y tools pero terminaron con bloque de texto vacío, por lo que constan como fallo de
respuesta del proveedor, no como modelo ausente ni como revisión completada. Sol encontró cuatro
defectos medios del propio protocolo; se corrigieron sin abrir otra ronda. Facts movidos: 0.

**S197 ejecutó esa cohorte una sola vez y volvió a detener el funnel upstream.** El doble scan
GET-only fue idéntico sobre 25.090 filas y selló 14 documentos/fabricantes nuevos, 7 tabla + 7
prosa y cero overlap prohibido. El transporte estático S196 ya no es el cuello: Haiku completó
14/14, produjo 14 preguntas elegibles y 42 puntos con **0 outputs inválidos**. Luna revisó 14/14
sin outputs inválidos, pero 12 ítems fallaron al menos un gate: 8 tenían un point-set incompleto
para el alcance de su propia pregunta, 5 contenían un punto no plenamente soportado o irrelevante
para la pregunta y 6 asignaban mal el facet. Resultado `NO_GO_COHORT_CONSTRUCTION`, coste
$0,15476, facts 0; planner, targets, DB, runtime y producción no se abrieron. La clase dominante
ya no es compilación sino cierre pregunta↔obligaciones. El siguiente mecanismo debe seleccionar
primero 2–4 obligaciones support-bound, validar support+facet con definiciones genéricas y sólo
después redactar una pregunta exactamente acotada a ellas, sobre otra cohorte que excluya S197.

**S198 cerró el diseño point-first y el riesgo de transporte nuevo; aún no ha ejecutado la
cohorte real.** Sol 5.6 xhigh principal y Fable 5 independiente completaron la misma revisión;
11/11 observaciones se corrigieron en una sola adjudicación, sin bucle de convergencia. El paquete
seleccionará primero obligaciones support-bound, aplicará una elegibilidad y precedencia de facets
congeladas, y renderizará después la pregunta desde los claims aceptados. Antes de seleccionar
otra fuente, el canary 100% sintético del nuevo schema `{item_id, question}` compiló en Haiku:
1/1 salida válida, cero retry, $0,000686, estado `GO_QUESTION_SCHEMA_CANARY_COMPILED`. Esto mueve
0 facts y sólo autoriza construir desde `main` un packet GET-only nuevo, disjunto de
S194+S195+S197, reportando además el inventario y reserva que quedan. El planner continúa cerrado
hasta que una ejecución única obtenga cero fallos en ambos screens upstream.

**S198 ejecutó después el tramo real y se detuvo todavía más arriba de lo previsto.** La reserva
manufacturer-disjoint ya no podía producir 7+7: quedaban cinco fabricantes de prosa compatibles.
Se congeló por ello un packet exhaustion-aware de 12 fabricantes/documentos nuevos, 7 tabla + 5
prosa, con doble scan GET-only idéntico de 25.090 filas y cero overlap/escrituras. Haiku produjo
12/12 outputs válidos y 37 puntos, pero sólo 10 fuentes fueron elegibles (6 tabla + 4 prosa).
Como el mínimo seguía siendo 12 elegibles, el estado es `NO_GO_POINT_PLAN_STRUCTURAL_GATE` por
$0,070886. Luna, writer, scope-screen, planner y targets recibieron 0 llamadas; no se postseleccionan
los diez casos y la calidad semántica del mecanismo continúa `NOT_MEASURED`. El siguiente intento
legítimo debe restaurar 14→mínimo 12 sobre documentos/source-files/pares nuevos, permitiendo sólo
repetición histórica de fabricante y conservando 14 fabricantes distintos dentro de la cohorte.

**S199 restauró 14 fuentes, pero el cuello poblacional persiste.** El inventario permitió 14
documentos/source-files/pares nuevos, 7+7, pero un máximo de 13 fabricantes; se congeló una sola
repetición sin usar outputs. Haiku produjo 14/14 outputs válidos, 9 elegibles de 9 fabricantes,
4 tabla + 5 prosa y 34 puntos. El gate estructural volvió a parar antes de Luna/writer/planner por
$0,083863 y facts 0. La reserva posterior conserva 647 documentos pero sólo 10 fabricantes: ya no
puede cumplir el mínimo anterior de 12. Para evitar análisis indefinido queda un único intento
final, prelimitado a 24 fuentes balanceadas (12+12), máximo 10 fabricantes, motor S198 intacto y
mínimos 12 elegibles / 8 fabricantes / 5+5 / 24 puntos / cero fallos. Si no pasa, se cierra esta
línea y se cambia de mecanismo; no se reutilizan identidades o issues de S198/S199.

**S200 consumió ese último intento y cerró la línea.** El holdout final tenía 24 fuentes nuevas,
12+12, 24 documentos/source-files/pares y cobertura de los 10 fabricantes restantes. Haiku dio
24/24 outputs válidos, 11 elegibles de 7 fabricantes, 6 tabla + 5 prosa y 40 puntos. Pasaron
estratos/puntos/transporte, pero fallaron los mínimos predeclarados de 12 ítems y 8 fabricantes;
Luna/writer/planner quedaron en cero y el coste fue $0,144517. No habrá S201 poblacional ni otra
calibración point-first. El siguiente orden limpia primero el puente local/default-off mediante
generalización independiente S188→S172 —sin fingir aumento del 143 diagnóstico— y vuelve después
al residual de 12 synthesis-miss con preguntas reales, no con otra autoría source-first.

**La auditoría posterior evita repetir S127/S128 o fabricar población para S172.** S188 ya fue
generalizado sobre seis pares independientes en S127: 57.646 asignaciones produjeron cero
relaciones exactas válidas y la línea global quedó revocada; S128 solo puede reabrirse ante un
funnel nuevo materialmente relation-bound. S172 ya tiene holdout interno preregistrado, 11
documentos, 33 derivaciones propagadas y replay live default-off; el discovery exhaustivo no deja
otro positivo versionado no visto. Ninguno ofrece ahora un nuevo OK legítimo y no se repiten sus
modelos/revisores.

**Pre-S201 sustituyó la población artificial por preguntas reales preexistentes.** El packet
determinista selecciona 12 preguntas sin usar respuesta, clase, `reaches_gen` ni outputs: 8
fabricantes, 12 productos y 43 facts, incluyendo soporte parcial/nulo. Haiku mapea facts a unidades
y Luna valida independientemente soporte y hasta tres conjuntos equivalentes; cualquier desacuerdo
detiene antes de Terra. El planner conserva 90/80/75, máximo 70 unidades, compilación exacta y cero
retry. Solo un PASS abre un packet target autocontenido de los 12 residuals; PASS target requiere
cero regresiones/conflictos y al menos un residual nuevo. Sol 5.6 xhigh detectó seis defectos del
borrador y los seis se corrigieron; Fable 5 llegó al proveedor pero devolvió final vacío tras siete
tools, queda incompleto y no se reintenta.

**S201 se cerró antes de la primera inferencia y no se reintenta.** El primer `count_tokens` de
Anthropic rechazó el schema de autor con arrays y cardinalidad dinámica (`minItems`/`maxItems`), la
misma frontera de dialecto ya aislada en S195-S196. No existe receipt de inferencia completada, Luna,
Terra y targets quedaron en cero, coste de inferencia conocido $0 y facts movidos 0. La cohorte S201
queda consumida: reintentarla tras cambiar transporte contaminaría el holdout.

**Pre-S202 corrigió la causa como contrato reutilizable y separó de nuevo upstream de downstream.**
Una cohorte hash nueva excluye las 12 preguntas S201, los cuatro targets y los dos default-off:
12 preguntas, 5 fabricantes —toda la diversidad restante—, 12 productos y 43 facts. El transporte
Haiku es un rectángulo estático 6×6 sin arrays, enums dinámicos, refs ni combinators; identidad,
cardinalidad, pertenencia y duplicados se validan localmente en `src/rag/source_unit_gold.py`. El
schema exacto pasó el compilador `count_tokens` con 0 inferencias/retries y $0. S202 ejecutaría solo
Haiku→Luna: 0 outputs inválidos, 0 desacuerdos y ≥36 facts source-supported. Un GO únicamente
autorizaría congelar después el planner Terra; S202 no ejecutaría planner/targets ni movería facts.

**S202 resolvió el transporte pero cerró `NO_GO_DUAL_GOLD` antes del planner.** Haiku completó
12/12 mappings válidos para los 43 facts: la causa S201 no reapareció. Luna completó 12 llamadas,
pero sólo 5 outputs pasaron el contrato y 7 fueron inválidos. Seis declararon acuerdo con la
decisión supported/unsupported sin incluir el set exacto del autor: el prompt definía acuerdo sobre
la decisión mientras el validador local lo exigía sobre el mapping, una incompatibilidad real del
instrumento. El séptimo usó un ID fuera del manifest. Los 13 soportados reportados proceden sólo de
las cinco filas válidas y **no** permiten estimar support-rate. Coste $1,258906; facts 0; no hubo
postselección, retry, Terra ni target. Quedan sólo cuatro preguntas S100 no observadas, insuficientes
para otro holdout de 12. La siguiente población se construirá desde manuales Kidde hoy sin preguntas,
con gold visual página-a-página y autoría/cross-review Sol 5.6 `xhigh` + Fable 5 antes de usar modelos
económicos para el benchmark.

**S203 probó el transporte visual y ambos Frontier, pero cerró `NO_GO_VISUAL_GOLD`.** Tres
unidades Kidde nuevas quedaron ligadas a 11 renders pixel-only; Sol y Fable completaron 3/3
autorías cada uno y las dos revisiones cruzadas (8 llamadas, **$14,07876** conservadores). Sol
rechazó un candidato Fable por recomendar BR para una sala de calderas sin recomendación literal
en la fuente. Fable dio PASS a los tres Sol, pero dejó dos notas explícitamente no materiales en
`issues` para el relé y el gate congelado trataba cualquier `issues` como bloqueo. Solo 1/3 pares
fue limpio bajo la letra estricta; no se postseleccionó, no se añadieron golds y se movieron 0
facts. S204 usará páginas/predicados frescos y un contrato reusable que prohíba recomendaciones no
literales y separe `blocking_issues` de `nonblocking_notes`; no reintenta S203.

**Pre-S204 corrige el instrumento y congela una población visual no contaminada.** El contrato
reusable `src/rag/visual_gold.py` prohíbe inferir aplicaciones desde límites numéricos, restringe
facts a páginas focus y separa defectos bloqueantes de notas no materiales con consistencia local
PASS/FAIL. La primera selección local detectó a tiempo que sus predicados textuales ya aparecían
en las preguntas HyQ S99 embebidas del lado documento: no son golds, pero usarlas en evaluación
contaminaría retrieval. Se descartaron antes de autoría. El packet final incluye en el filtro de
duplicados las 51 preguntas gold y las 179 HyQ de los tres PDFs seleccionados, y congela cinco
renders de tres predicados visuales no presentes como preguntas exactas: topología Clase A entre
bases, posiciones DIP 008/112 y distinción de ranuras del KE-DBA-AUXW. La novedad semántica sigue
siendo un gate bloqueante de los revisores, no una afirmación local. Cero solape basename/SHA con fuentes
gold y cohorte S203 excluida. Sol 5.6 `xhigh` y Fable 5 alcanzaron sus pins en la revisión de diseño
monolítica, pero ambos agotaron el allowance sin JSON final; constan como incompletos, no
indisponibles, por **$3,25083**, sin retry. La auditoría determinista corrigió además el PASS vacío.
La preejecución pasa 4/4 tests y autoriza únicamente una PR con CI; tras merge, una ejecución
separada de máximo ocho llamadas y $40. Aún mueve 0 facts.

**S204 ejecutó las ocho llamadas y cerró `NO_GO_VISUAL_GOLD`, sin repetir los defectos S203.**
Sol y Fable produjeron 3/3 candidatos válidos; Fable dio PASS a los tres candidatos principales
Sol, incluidas notas no materiales que el nuevo contrato permitió correctamente. Sol dio PASS a
2/3 candidatos Fable y bloqueó sólo el cableado Clase A: sus seis facts eran visibles y correctos,
pero la respuesta final dejó una frase de polaridad ambigua y omitió la advertencia visible de
desenergizar/descargar antes del cableado. Es un fallo de contenido real, no del schema. Coste
conservador **$15,729345**; 2/3 pares simétricos limpios, pero no se postseleccionan, reparan o
salvan; golds 0, facts 0, bot cerrado. La causalidad nueva es de geometría: hacer publication-gate
del candidato independiente permite que un defecto exclusivo de un candidato no final vete un
candidato principal que sí pasó revisión independiente. Un sucesor fresco puede usar el candidato
independiente sólo como probe ciego de desacuerdo: debe seguir generándose antes de review, ambas
direcciones deben declarar cero desacuerdo material y Fable debe dar PASS a cada candidato Sol.
Debe congelarse antes de elegir páginas nuevas y nunca rescatar S204.

**S205 validó la geometría principal, pero la auditoría determinista cerró la cohorte por
contaminación.** La regla se congeló en un commit anterior a la selección: Sol 5.6 `xhigh` era el
único autor publicable, Fable 5 generaba a ciegas y debía aprobar todos los Sol, y el borrador
Fable sólo actuaba como probe de desacuerdo. Tras PR #142 y CI verde se completaron 8/8 llamadas
por **$11,81598**: seis candidatos válidos, Fable PASS 3/3 a Sol, Sol PASS 2/3 a Fable y cero
desacuerdos materiales; el runner produjo un GO mecánico. La revisión local obligatoria detectó
que `s205k03` pregunta por los modelos/funciones de barreras de la misma tabla y el mismo PDF ya
embebidos por `hyq:54c2275f…:2`. Sol sí marcó ese duplicado al revisar el counterpart; Fable lo
negó suponiendo erróneamente otro documento porque el packet no exponía identidad de source en
las filas de cobertura. Medirlo downstream premiaría leakage del retriever. El estado autoritativo
es por ello `CLOSED_NO_GO_VISUAL_GOLD`: no se salvan los otros dos candidatos, no se integra gold,
no se abre bot y se mueven 0 facts. La línea de canarios visuales se cierra aquí para evitar otra
convergencia; se vuelve directamente a las 12 synthesis-miss existentes.

**`chunks_v3` no se migra al completo.** S140 cerró el shadow representativo como
`FINAL_NO_GO_CHUNKS_V3_WHOLESALE`: empata recall funcional@10 (16/24 vs 16/24) pero empeora el
primer rango útil/MRR (0,4021→0,3694). `chunks_v2` sigue siendo el baseline activo. V3 preserva
más superficie upstream y su contrato de procedencia es valioso, pero esa propiedad no compensa
una regresión downstream. Solo se diseñará v4 si una causa estructural local mejora el ranking sin
pérdidas por fabricante/held-out; no se parchearán preguntas concretas.

**Frentes ortogonales:** (a) voz tiene selector versionado y default `whisper-1`; no se migra de
modelo sin 30 notas reales estratificadas, que hoy no existen; (b) el renderer de Telegram ya
preserva contenido, tablas y mensajes largos y pasa su gate local; (c) S190 demostró que el canal
de imágenes está implementado en bot/generador pero sin datos en `chunks_v2`: 0/25.090 URLs.
Existe un bridge exacto hacia 5.096 páginas legacy (7.685 chunks; 30/30 assets vivos), pero una
muestra visual contiene portadas/marketing. Por ello el backfill directo es NO-GO. S191 ejecutó
Luna sobre 60/60 activos válidos por **$0,04029**, pero el trigger 10–30 positivos quedó mal
calibrado frente a una cohorte con 48 estratos de intención técnica y produjo 44. No se cambió el
umbral post hoc ni se llamó a Sol/Fable. La calidad del clasificador queda sin medir; el diseño BP
sigue siendo un registro ligado a documento+revisión+página+hash, independiente del chunker.

**Producción no ha cambiado en este bloque.** No se ha hecho deploy, migración ni escritura
remota. Railway sigue siendo una demo y no es condición para merge con CI verde. Próximos pasos,
por orden: (1) merge CI-verde del resultado S205; (2) volver a las 12 synthesis-miss y reconstruir
su evidencia upstream con los artefactos ya versionados, sin otra autoría de preguntas; (3)
congelar un cambio estructural sobre el mayor sub-bucket y medirlo primero en población no usada
para diseñarlo; (4) reconciliar el bridge diagnóstico/productivo sin sumar de nuevo S172/S188;
(5) al alcanzar ≥98%, pasar a diagramas/formato/Wispr Flow; (6) recoger 30 audios reales antes de
comparar ASR. El funnel conserva sus etapas: S193 mantiene señal de renderer; S194, S195, S197,
S198, S199, S200, S202, S203, S204 y S205 son NO-GO upstream, S196 y los canarios de transporte
son GO instrumentales, S201 es HOLD cerrado y todos siguen con crédito de facts cero.

## Estado anterior (s129 — 15 jul 2026)

**No existe todavía un KPI atómico oficial vigente.** La última evaluación completa y
comparable (`s100_factlevel_full.yaml`, commit `9790673`, ya anterior al branch/worktree actual)
dio **93/127 OK (73%) · synthesis 11 · retrieval 7 · rerank 14 · corpus-gap 2→0 tras revisión
manual**. La fila del scoreboard tenía retrieval/rerank transpuestos y se corrigió en s129.

El **79** era un puente híbrido que aparcaba 33 parents y dejaba 11 claims sin respuesta; el
**111** aparece al sustituir esos 33 parents por 58 core claims y reutilizar respuestas congeladas.
No son tres puntos del mismo KPI ni 32 mejoras del bot. La foto provisional sin activar S126 es:
**157 claims · OK 111 · synthesis-not-measured 27 · synthesis-miss 14 · retrieval-miss 4 ·
source-contract-hold 1**. S126, local y default-off, movería 2 retrieval→not-measured y **0→OK**.
Además quedan **77 legacy carries** por migrar/adjudicar antes de poder publicar un KPI plenamente
atómico; hasta entonces, cualquier funnel completo será híbrido y debe conservar crosswalk.

**`chunks_v3`: GO estructural local, no GO de calidad/producción.** Se rematerializaron
determinísticamente 1.068 documentos / 31.226 filas; recupera 100 bloques antes perdidos, con 0
pérdidas detectadas, y cambia contenido en 27 documentos. Aún no hay DB apply/rollback real,
contexto, embeddings, shadow load ni A/B retrieval. Nueve qids antiguos estuvieron expuestos a
documentos cambiados, pero eso no prueba que el span nuevo soporte el fact. S127 queda
**NO-GO/revocado** y S128 (extractor relacional) **pausado antes de build**.

**Estado de ingeniería:** branch local S108-S111 = 4 commits sobre el `origin/main` local;
S112-S128 siguen mayoritariamente en worktree (**463 paths dirty, ~2,4 GB untracked**). La suite
actual pasa **1.285 tests, 5 skipped, 0 failed**. Nada de este bloque implica deploy o cambio de
producción verificado.

**Qué sigue, por orden:** (1) mapping exacto `claim→extraction→bloque ganado` sobre los 27 docs/100
bloques; si no encuentra oportunidad material, parar la rama KPI de v3; (2) en paralelo, M0b de
PostgreSQL+pgvector desechable (apply, permisos, activación y rollback); (3) solo con señal, generar
contexto/embeddings para el shadow mínimo y medir **retrieval→rerank→synthesis** en cascada contra
`chunks_v2`; (4) resolver los 27 not-measured reales con evidencia congelada y los 2 de S126 en
brazo separado; (5) cerrar los 77 legacy o publicar ambos denominadores con crosswalk. Solo entonces
elegir el mayor bucket fresco y reabrir mecanismos como el extractor relacional.

## Estado anterior (s104 — 10 jul 2026)

**s104 (DEC-102) — R2 corpus-wide ejecutado hasta su gate; DEC-101 MEDIDO en scoreboard (fila
v3: OK 93/73%, retrieval 12→7, lista diana completa convertida +9/−7).** R2: pipeline seguro
(generar→dump→loader-A3; el dúo cazó que el pase legacy insertaba al índice compartido del
NO-GO DEC-088) · G0 = Haiku GO medido (4x más barato, QA-pass superior; panel cazó meta-líneas
DE Sonnet) · T2 81/81 generado (45.889 enunciados QA-passed en dumps, ~$10) · **carga a 71K =
GATE T2 DISPARÓ** (0 ganancias de ancla, 2 OK perdidas, crowding del sort-mixto sin cuota —
la clase que hyq resolvió con fusión-por-cuota) → **rollback a T1 VERIFICADO 0/0; tail (~$95)
NO gastado**. Activo a salvo: 54.849 enunciados Haiku en dumps locales; re-carga post-fix ≈$1.
**Qué sigue (cabeza de cola): CUOTA del canal enunciados** (espejo hyq DEC-099; dúo obligatorio
+ gate de re-carga = probe pre/post committeado) → re-cargar T2 → si gate pasa, tail → gate
final (bvg + assessment fila v4). Después: synth/gold-review (DEC-094) + entity-linking #52.1.
Costes sesión: ~$135 envelope + R2 $14/$180. Prod = demo v3 (DEC-101) con tabla A3 en estado
T1 exacto.

## Estado anterior (s103b — 10 jul 2026)

**s103b (DEC-101) — landing RESUELTO por extensión acotada + selección code-gated: CANDIDATO DE
SHIP GATEADO, pendiente GO de Alberto (merge + Railway `GENERATOR_SELECTION_BLOCK=on`).** Tras el
NO-GO de la eviction (DEC-100, abajo), la re-apertura MEDIDA de su alternativa A2: el carve-out
deja de reservar slots (el doble cobro desaparece de raíz) y el aside viaja como extensión
(≤ top_k+cuota, patrón identity-fetch). Gates: diana 4/4 (incl. hp018·p21) · anclas +1/−0 ·
containment 0-missing · negcontrol 6≤7 · flips 2/2 · churn anclas-OK 0-loss · **bvg +cat022
FALLO→PASS**; la única regresión real (cat021, composición-sensible DEC-097) curada con el bloque
de selección con trigger EN CÓDIGO (el prompt-gated sobre-dispara hp009 — 2 mediciones; regex
determinista: sweep 39 = solo cat021, spec/avería byte-idénticas por construcción). cat024/hp009
= artefacto-juez/baseline (leídos). Family-aware landing MEDIDO NO-OP (0 cross-family con lista
resuelta) → queda como hygiene DEC-074. Top-100 MEDIDO no-paga (3/11 a ranks 55-91; 5 ni a 100 =
vocabulario). Desviaciones de proceso declaradas en DEC-101 (D1-v1 inválido→v2, métrica
refinada; fix `_stage_of` no-monotonía). Suite 473. Coste sesión ~$90/$150. **Qué sigue:** (1)
GO/NO-GO de Alberto al ship DEC-101; tras ship → assessment smoke→full (fila v3 del scoreboard,
caveat bucket in-pool +10). (2) **Entity-linking (DEC-074)**: primer consumo = sinónimos/series
del family-filter hyq (#52.1) — el family-aware landing quedó medido NO-OP; hygiene bajo REPLACE
sigue candidata. (3) Gateados: enunciados R2 ($160-270, presupuesto Alberto) · #52.2 al gatillo.

## Estado anterior (s103 — 9 jul 2026)

**s103 (DEC-100) — lever displacement-landing (eviction) MEDIDO → NO-GO por gate pre-declarado →
REVERTIDO.** El rediseño del carve-out hyq (diversify a top_k completo + eviction VECTOR por
posición + trim del aside; dúo 2 rondas × 2 lados, 14+ findings/0 FP) FUNCIONA para su diana
(cat022 recupera 3/3 chunks; anclaje corpus-amplio +1/−0) pero los CONTROLES amplios lo tumban:
rompe el flip shippeado hp018·6K8 (gate DEC-099), hp011 fuera del null, negcontrol EXCESS-HIGH
7→9. **Lección medida: canal/score/sim-pregunta/posición — los 4 ejes observables son ciegos al
valor.** Seam `evals/s103_displacement_seam.patch`; matriz v3→v2.2
`evals/s103_transition_matrix.json`. Synth residual mapeado (`evals/s103_synth_residual_map.md`):
6/8 stable-miss, cluster cat021 NO reaparece, 5×omitted → gold-review (DEC-094), no lever synth
nuevo. Prod NO tocado (revert por pre-registro).

## Estado anterior (s102 — 9 jul 2026)

**s102 (DEC-096..099) — canal hyq SHIPPEADO A PROD y VERIFICADO + demo completa medida (scoreboard
v2.2).** El canal question-side (tabla `chunks_v2_hyq` 70.134 preguntas + seam `HYQ_TABLE`, mecánica
v2: cuota 10 + barra 0.45 + family-parity nivel-fila patrón-012 + carve-out del diversify) pasó
flips 2/2 CON atribución + bvg 0-regresiones-reales, PR #115 mergeado, **flip cat016 verificado en
query_logs de prod** (d355867). **Scoreboard v2.2 (demo real: fidelity+hyq ON): OK 91 (72%) ·
synth 18→8 (¡cluster cat021×4 → OK vía composición-servida, sin tocar generador — confirma DEC-097!)
· retrieval 12 · rerank 13 · corpus-gap real 0.** Factura del canal VISIBLE y con mecanismo
verificado: cat022×3 + hp018×3 desplazados (el presupuesto reducido del diversify aprieta al canal
keyword — negcontrol rojo pool-level lo anticipó). **Qué sigue:** (1) lever candidato = aterrizar el
desplazamiento en la cola del canal VECTOR (no keyword) — medir antes de cablear, anti-overfit
flagged; (2) synth residual 8 (~reales); (3) el estructural grande = entity-linking/identidad
(DEC-074, F1 construido sin consumir). Levers cerrados: demote-TOC NO-GO (DEC-096) · selection-block
NO-GO+fork (DEC-097) · fidelity SHIPPED (DEC-098) · hyq SHIPPED (DEC-099). Límites declarados:
TECH_DEBT #52. Plan reanudable: `evals/s102_plan_autonomo.md`.

---

## Estado anterior (s101 — 8 jul 2026)

**s101 (DEC-095) — instrumento dual×2 + 4 levers upstream MEDIDOS + scoreboard v2 (autónomo nocturno,
mandato OK>95%).** El instrumento cazó y arregló 2 clases de FN de su propio juez (conveyed + soporte,
dual GPT→Opus con evidencia adversarial); gold-review pixel-vs-fuente (5 demotes + hp011 r.I — Alberto
corrigió su s30; el cross-model tenía razón contra el ground-truth humano). **Scoreboard v2 (juez v2):
OK 91 (71%) · synth 22 (14 stable/8 flip; cluster cat021×4 = variantes 40/40) · retrieval 8 · rerank 5 ·
corpus 2.** Levers: **hyq/HyPE piloto GO** (2/7 flips, cuota+barra; ship=D2 Alberto; residual-ancilar
declarado anti-overfit) · **tiebreak CERRADO** (2ª medición, con ancho-10: centinela hp001 regresa) ·
cat013=identidad (DEC-074). **Qué sigue: Fase 2 (synth 22→1-2)** — A/B fact-level del fidelity-block
en vuelo (métrica ≠ DEC-051-PASS); cluster cat021 (variantes) = candidato específico; luego D2-D5 de
`evals/s101_decisiones_alberto.md`. Plan reanudable: `evals/s101_plan_autonomo.md`.

---

## Estado anterior (s100 — 7 jul 2026)

**s100 (DEC-094) — assessment a nivel-hecho ESTANDARIZADO construido+corrido → foco RE-DERIVADO con datos frescos.**
Se construyó `scripts/factlevel_assessment.py` (unifica los 7 instrumentos ad-hoc) + doc canónico
`docs/FACTLEVEL_ASSESSMENT.md` con **scoreboard append-only** (source-of-truth de "qué tal funciona el bot" a
nivel-hecho, para trazar la aguja; medido en ruta HARNESS con flags-demo, NO el bot Telegram — caveat declarado).
**RESULTADO (39 golds, 133 facts):** OK 89 (67%) · **synth-miss 16 estructural** (+6 flip) · retrieval within-doc ~17
(gap vocabulario) · rerank 4 · **corpus-gap ~0** (5 raw TODOS FN, verificados a mano — `feedback_corpus_gap`) ·
**identidad 0**. **Titular: síntesis SIGUE siendo el cuello dominante post-ancho/A3/identidad → DEC-075 re-confirmado
en veredicto (su medición s87 sí era caduca); identidad+corpus descartados con datos frescos.** Refinado por sub-motivo
(~10 omitted/hedged=lever prompt + ~5 partial=lever retrieval + 2 contradicted) PERO **contaminado por scope/gold**
(hp007: el bot respondió lo preguntado) → qué-lever-DENTRO-de-síntesis = gold-review por-hecho, NO zanjado por este run.
Dúo-intensivo (spec ×3 + código ×2 + 3 smokes cazaron 4 bugs de diseño). Rama `eval/s100-factlevel-assessment`.
**Rumbo previo (s99b) VIGENTE en lo suyo:** blindar-demo→nota pivotó a NOTA; reescritor APARCADO (`evals/s99_rewriter_design.md`);
identidad B = QA ~363 candidatos (DEC-074); PCI-fuego puro (TECH_DEBT #75).

---

**Antecedente s87 (DEC-075) — diagnóstico de síntesis (⚠️ CADUCO, pre-ancho/A3/identidad):**
**s87 (DEC-075): diagnóstico autónomo de SÍNTESIS → el "cuello 103" era una COTA, no fallos.** El bucket
SÍNTESIS `by_target` (103/132, DEC-070/073) contaba hechos SINTETIZABLES (soportados por un chunk del top-5),
NO fallos de síntesis. Midiendo la RESPUESTA actual directamente (instrumento nuevo `synthesis_miss_judge.py`,
juez GPT-5.5 K=5 a nivel-proposición, dúo-hardened, 2 gen para varianza): el pipeline actual **sintetiza
~76-80% de los hechos en-contexto**; el cuello de síntesis ROBUSTO = **16 stable-MISS (~13-14 genuinos)**, cola
pequeña y HETEROGÉNEA — completeness ~10 (=lever de generación **settled NO-GO en PASS**, DEC-051) · contradicts
~4 (FIDELIDAD: bot afirma inconsistente, p.ej. hp001 '1111' access-level, hp013 'EEPROM' invertido) · hedge ~2 ·
judge-FN ~3-4 · identidad hp018 (DEC-074). **Sin lever barato de síntesis.** Atribución verificada: mejora vs
s67base con el MISMO modelo/temp/tabla → efecto de **VECTOR_NOCAT** (mejor retrieval → contexto más rico).
Certificado por dúo de agentes (adjudica-ciego + verifica-adversarial) que corrigió en AMBAS direcciones (cazó
over-credit hp018 + confirmó OMITTED reales). **NADA en prod, reach≠PASS, 354 tests. Refina (NO refuta) DEC-070/073.**

**PASS des-diferido MEDIDO (Alberto autorizó): PASS-control = 9 · K-INESTABLE 6 · residual 24 — PLANO vs s67base
(10+4), dentro del ruido ±2.** Mi predicción "subió mucho" FALSADA por la medición (VECTOR_NOCAT mejoró el
mecanismo pero no el PASS holístico; "80% hechos ≠ 80% PASS" confirmado). **Root-cause SEMÁNTICO de los 30
NO-PASS:** SÍNTESIS 11 (completeness=NO-GO+fidelidad) · **OTRO gold/juez 10 (sin miss de pipeline** → fidelity-errors
reales cat022/hp001/cat009, falso-NO-PASS juez cat019, conducta, supp) · RERANK 6 (settled) · RETRIEVAL 2 (ingesta) ·
IDENTIDAD 1. **Meta-hallazgo: ~10/30 fallan ⊥ el pipeline → arreglar retrieval+síntesis NO los pasaría. Plateau
noise-limited CONFIRMADO al nivel de gold (DEC-051e medido); NO hay lever de pipeline que mueva PASS.**

<details><summary>Antecedente s86 (DEC-074) — B2 por los 3 clusters: identidad ~4-palanca (no el cuello), BP=catálogo 2-etapas</summary>

**s86 (DEC-074): B2 por los 3 clusters de retrieval-miss.** **RECALL-INTRADOC (8)** = 5 hard-tail de INGESTA (coseno sub-suelo/"aguja en chunk grande"; neighbor-window NO-GO + ef_search marginal + más-contexto insuficiente, todo DESCARTADO midiendo → fix BP = capa-ingesta multi-granularidad/tablas, foundational futuro); 3 within-doc. **MODEL-FILTER (4, hp018) = identidad, ~4 de palanca REAL** (no el cuello): `LEVER2_IDENTITY` curado da 4/4 pero es quick-fix (per-familia, regresa hp009) → NO shipear; hp011 mis-diagnosticado (RP1r-Supra, within-doc). **BP identidad = catálogo canónico de 2 ETAPAS** (workstream A); mapa data-driven solo (`family_scope`) = net-negativo. Código `neighbor-window`+`IDENTITY_MAP` flag-gated OFF.
</details>

<details><summary>Antecedente s85 (DEC-073) — limpieza A mergeada + instrumento family-aware (=14) + B1</summary>

- **A — limpieza de raíz MERGEADA (PR #94, en demo):** `VECTOR_NOCAT` permanente (sin flag) — el filtro por la columna `category` MUERTA fuera de raíz (4 sitios + broad-fallback + 3c-i + detección inerte + param content_search). Verificado judge-free: 354 tests + equivalencia de pools 38/39 (net −63 líneas). Conserva MERGE_STRATEGY/LEVER2_IDENTITY/PM_RESCUE + detección para catálogo.
- **A — limpieza de raíz MERGEADA (PR #94, en demo):** `VECTOR_NOCAT` permanente (sin flag) — el filtro por la columna `category` MUERTA fuera de raíz (4 sitios + broad-fallback + 3c-i + detección inerte + param content_search). Verificado judge-free: 354 tests + equivalencia de pools 38/39 (net −63 líneas). Conserva MERGE_STRATEGY/LEVER2_IDENTITY/PM_RESCUE + detección para catálogo.
- **B0 — instrumento family-aware de retrieval-miss (`retrieval_miss_judge.py` + `_famtie.py`):** juez semántico GPT-5.5 K=5 (sustituye el matcher léxico que inflaba ~45%, DEC-070) + **tie por FAMILIA de `product_model`** (corrección de Alberto: by-target acreditaba hp018 vía manual de familia equivocada ZXAE/ZXEE por azar) + pin del pool. **retrieval-miss canónico = 14** (SÍNTESIS 103 = el cuello sigue siendo síntesis; CORPUS-GAP=1 residual FN). Dúos #17/#18 cazaron 8 bugs (2+2 CRÍTICO) → arreglados sin re-juzgar.
- **B0/B1 — instrumento family-aware (=14) + diagnóstico por (etapa×motivo):** juez GPT-5.5 K=5 + tie por FAMILIA de `product_model` + pin del pool. Mapa B2: RECALL-INTRADOC 8 · MODEL-FILTER 4 (hp018) · RECALL-GLOBAL 2. (Detalle: DEC-073.)
</details>

**Modelo operativo (DEC-071e) VIGENTE:** `main`=dev=demo, stop-line=tests-verdes, PASS diferido a síntesis, freeze per-eval. Disciplina de coste (`feedback_cost_discipline`).

**Qué sigue — s100 RE-CONFIRMÓ síntesis como cuello a nivel-hecho (16 estructural); PASS sigue plano (~9-10/39). Decisiones para Alberto:**
0. **(s100, fresco) El cuello a nivel-HECHO es síntesis (16 estruct.) + retrieval within-doc (~17, vocabulario).** Identidad/corpus
   descartados con datos frescos. El **lever dentro de síntesis** (prompt para omitted/hedged vs retrieval/chunking para partial) NO
   está zanjado: el sub-motivo está contaminado por scope/gold → requiere **gold-review por-hecho** de los 16 (eje gold/juez) ANTES
   de apostar. El retrieval within-doc = gap de vocabulario, lever caro (re-ingesta A3/tablas, DEC-085/86, gate presupuesto).
1. **NO perseguir levers de síntesis/rerank/retrieval CIEGAMENTE por PASS** — el PASS sigue plano (~10/30 NO-PASS ⊥ pipeline,
   DEC-051e). Pero el nivel-HECHO SÍ tiene señal accionable (síntesis 16) — separar "mejora el bot a nivel-hecho" de "mueve PASS".
2. **Highest-leverage PASS = dual-judge + gold-review del bucket OTRO (10 golds)** (s47 §D / s76): cat019 ya medido
   falso-NO-PASS (juez-bias); los 6 K-INESTABLE tienen votos PASS. Recuperaría varios PASS reales-pero-juzgados-PARCIAL
   **sin tocar el bot**. Es el ruler-hardening que DEC-051d gatea. Requiere held-out + cross-model.
3. **Fidelity-errors reales del bot (cat022 longitud-onda-IR, hp001 '1111', cat009 6K8)** = per-caso: ¿retrieval de
   sección equivocada o generación? Bugs de calidad genuinos, actionable (barato).
4. **Foundational (⊥ PASS a corto): (A) catálogo canónico de identidad** (BP entity-linking 2-etapas; escala-30+;
   4-7 ses, ~3.5-6.5h Alberto; Fase 0 = drafta contrato) + **capa-ingesta retrieval** (DEC-074) para RETRIEVAL/IDENTIDAD.
5. **El unlock de calidad REAL = eval orgánico (técnicos, ~sept)** — el ruler ±2 es el techo (DEC-051e/s69).

**DEC-056 SIGUE (ranking); DEC-068 SIGUE (L-i por PASS settled). Identidad ~4-palanca (DEC-074). SÍNTESIS ROBUSTA ~16 stable-MISS (DEC-075). PASS plano ~9/39 MEDIDO (DEC-075f) — plateau noise-limited.**

**s88 (DEC-076/077, nocturna autónoma):** per-caso al píxel de los "fidelity-errors" → **CERO invenciones del
generador** (se disuelven en within-doc + gold/juez-review; corrige un FN del rootcause en hp001); **dossier de
los 30 NO-PASS** (`evals/s88_nopass_dossier.md`) para decisión-en-lote de Alberto — la Clase A (gold/juez-review,
~6-7 candidatos con evidencia literal) es la palanca CANDIDATA más barata de PASS (delta no medido, gate Alberto).
**DÚO v2 (pedido Alberto):** sub-agente→`fable` + cross-model CON tools read-only sobre el repo (paridad de
información; cierra TECH_DEBT #36; smoke validado).

**s91 (DEC-080): F1 BULK — las 31 marcas en el catálogo canónico.** ~1.6k productos / 39 homónimos /
861 doc_map / 9 docrel ES/EN (los de DEC-066); BRAND_MAP 96→31; typo-merge #49 (30); x-brand jamás-merge-auto;
dúo 2 rondas (14 findings aplicados; la clase H5 reincidió en el gt FAAST → re-transcrito fiel). Golds-clave
resuelven; lo dudoso fail-open. PR #102.

**s91b (DEC-081): los 25 homónimos ADJUDICADOS por Alberto (G1✅ G2✅ G3✏️×3-verificados G4=APIC-clarify)
y APLICADOS** (`s91_apply_homonyms.py`: 30 winners / 33 redirects+rebrand-of / quedan 9 homónimos [2 gt +
APIC + 6 cola]; `systemsensor:6424` creado; umbrella B500; oem SOLO adjudicado: Esser/Xtralis/Carrier/SS×2).
Sub-agente adversarial cazó 3 H5 en MIS añadidos pre-commit (0 FP). **FIX D1: `data/catalog/` entra a git**
(`.gitignore data/*` lo dejaba SIN versionar y el test de integración skippeaba → repo-first real).
**Gate restante: merge PR #103 (Alberto) — CUMPLIDO.**

**s91c (DEC-082): plan F2 v2.2 dúo-hardened (×2 rondas, 15+13 hallazgos 0 FP)** — mecanismo = los 2
seams medidos (models-list LEVER2→catálogo + unión-protectora doc_map en `_filter_to_query_models`),
NO vía aditiva (DEC-069, fila nueva en LEVER_DIGEST con VENDIMIA de config); **contrato §5.1
ENMENDADO (✅ Alberto, PR #105): F2 expand-only, clarify conduct-level → fase posterior por-pregunta.**

**s91d (DEC-083): F2-S1 CONSTRUIDO (PR #106, dúo r3: 14 hallazgos aplicados pre-PR)** — resolver
query-side tras `IDENTITY_RESOLVE=off|shadow|on` (default off), detector regex-generada del catálogo,
brazos add/replace, fail-fast de flags en arranque, shadow a Supabase (`identity_resolve_shadow`
creada), stamp catálogo-commit; 28 tests nuevos (suite 411). **+ packet C2 COMPLETO adjudicado
(3 tandas Alberto): 19 marcas → 43 productos re-domiciliados; lecciones: hosting≠OEM,
string-grupo→contextual, familia≠marca (FAAST→paraguas familia+LT-200 divergent=true, expanden).**

**s92-s93 (DEC-084): F2 MEDIDO Y SHIPPEADO A DEMO; el lever identidad-en-retrieval queda EXHAUSTO.**
S2 con predicciones pre-registradas + pin-regen: **ADD gana** (retrieval-miss famtie 15-control→**12**;
hp018 4/4 contrato; hp009 intacto; REPLACE reproduce la regresión hp009 CON mecanismo visible) →
`IDENTITY_RESOLVE=on`+`add` **ON en Railway** (PRs #107-#109; verificado vivo vía shadow: ZXe→+3
variantes). S3-fetch acotado: **NO-OP 12→12** (el selector léxico no encuentra los chunk-ids juzgados)
→ NO-SHIP, código tras flag default-off. **−3 neto banked; el residual 12 ≠ identidad.**

**s93b (DEC-085): BAKE-OFF fine-grained EJECUTADO (8h autónomas; plan v3.2 dúo-hardened ×2 +
pushback de Alberto "no solo FTS")** — `evals/s93_bakeoff_resultados.md` = artefacto de decisión.
**PASO-0 trace: 30/31 soportes nunca entran a canal (fine-grained confirmado); hp012 '99+99' muere
en diversify → lever diversify, no ingesta. A-FTS: NO-GO 1/11 + desplazamiento 12-19/20 en controles.
B-multigranularidad cruda: 1/10 (aislar ALEJA: 5/8 sub<padre). C-extracción-tablas→ENUNCIADOS: 2/4 ✅
único mecanismo con hechos que nada más gana → ES el que financia la re-ingesta (~$150-300, gate
presupuesto Alberto; piloto natural = ~6 docs del testbed + famtie). HyDE solo: 0-1/10 (comprime
gaps, no cruza; re-evaluable post-ingesta). Cuello re-caracterizado: gap de VOCABULARIO query↔celda,
no tamaño del chunk per se.** Nada cablado (FTS_ALL_QUERIES no se construyó; flags intactos).

**s94 (DEC-086): PILOTO extracción→enunciados EJECUTADO — GO del mecanismo (criterio pre-registrado
cumplido en las 3 barras).** Spec v2 dúo-hardened + validación BP (multi-vector/verbalization =
canon). **R2 enunciado-LLM: famtie 12→6 (5/10 testbed + colateral '99+99'; GO-tabla 2/4 ✓ GO-prosa
3/6 ✓ 0 nuevas-miss; predicciones clavadas) · R1 plantilla DESCARTADO por medición (0/4) · R3
resumen/tabla complemento barato (12→8, gana ISO-X).** Triage: hp011+'99+99' mueren en DIVERSIFY
(mecanismo vivo → lever pipeline aparte); cat013/cat016 = vocabulario operativo puro (sin mecanismo
aún). Seam `PILOT_PARENT_SWAP` default-off (5 tests); inserciones REVERTIDAS ×3 (0 restantes);
nada shippeado. Artefactos: `evals/s94_pilot_{spec,run}.md` + `s94_f3_results.json`.

**s94b/T0 (DEC-087): la infraestructura PERMANENTE del pase construida y dúo-hardened (2 rondas
del dúo sobre plan + 2 sobre build; 30 hallazgos aplicados, 0 FP).** Migración **007 APLICADA**
(parent_id CASCADE + ingest_batch + RPC include_surrogates default-false; ef_search s59b preservado
vía set_config; rollback ejecutable `007_rollback.sql`) · **invariante de NO-SERVICIO** (9 GETs +
RPC: una fila con parent_id JAMÁS se sirve cruda — cierra la ventana demo-sirve-derivado F1) ·
swap `ENUNCIADOS_MULTIVECTOR` from-row (14 tests) · **QA generalizado calibrado ×3** (fix DECIMALES
reproducido: '13,9' alucinado pasaba; 86.6% final, 2/2 conocidas siempre) · panel de desplazamiento
(fix EMBARGO: los 12 held-out estaban dentro del pin v1; re-pineado dev+query_logs + suelo de ruido)
· pase idempotente por-doc (temperature=0, prompts v1 congelados; smoke MIDT180 427 QA-OK, cov 65%).
Umbral QA re-registrado a calibración-en-T1 (~78-86% real full-doc, no el 97% del piloto); coste
re-estimado: T1 ~$40-100 y su medición fija T2-T3 (banda $160-270 obsoleta). 435 tests; demo intacta
(flag off, 0 surrogates).

**s94c/T1 (DEC-088): pase corpus EJECUTADO → NO-GO del enfoque "surrogates en índice compartido".**
Gate G1 (reproducción) FALLA 2/6: los 21.995 enunciados en el MISMO HNSW que los 22.339 chunks
reales lo diluyen (índice ×2) → recall real cae 12→19, multivector 13 (neto peor que 12). El
piloto s94 (12→6) no escaló: usó 251 surrogates dirigidos/transitorios; a docs-enteros el mecanismo
se ahoga (dilución + enterramiento). **T1 (~$50-75) cazó el fallo ANTES del gasto de corpus ($150+)
= tramos funcionando.** Demo restaurada (dump+delete+revert+VACUUM); schema T0 conservado; bug
latente arreglado (FK duplicate_of → migración 009). Side-by-side: **Sonnet 5** es el vintage
(mejor calidad, ≤coste). 435 tests.

**s95 (DEC-089): redesign MEDIDO con 2 pilotos ($3.5).** Research verificado (BP unánime: surrogates
en índice propio; Dense X +2.2 con embedder fuerte; agentic-RAG-como-arquitectura descartado con
evidencia ACL-2026 + perfil de fallo propio) + dúo sobre el plan (15/15 confirmados, 0 FP, 4
críticos) + ejecución: **A3 (tabla `chunks_v2_enunciados` SEPARADA + paridad de filtros + colapso
Dense-X; migraciones 011/012) = famtie 12→7, 0 regresiones, control 12 INTACTO — arquitectura
VALIDADA, candidato a ship.** Piloto D (deep-lookup Haiku en seam IDENTITY_FETCH, parser
3-estados) = NO-GO (12→11, 0/6, 38% gatillado: el seam solo corre con doc AUSENTE y la clase
dominante es doc-presente-aguja-ausente). Residual 7 caracterizado por clase. Flag OFF en demo;
nada shippeado. 441 tests.

**s98 (DEC-092): matriz de rerank autónoma → el lever que paga es SERVIR-MÁS al generador
(top-8/10), NO tocar el reranker (6 métodos NO-GO: prompt×2, Opus 4.8, ventana 2500, Voyage-CE,
RRF). El dúo lo reencuadró de "estructural" a HIPERPARÁMETRO-DE-ANCHO (CUT15 confirma agujas en
rank 6-15 + el confound tamaño-petición). rerank-miss 1-2 ES alcanzable a nivel retrieval (top-10=2)
PERO el smoke e2e cazó truncado intermitente en un control (`LLM_MAX_TOKENS=2048` fijo, TECH_DEBT
#74) + rescate en respuesta parcial 3/9 → NO ship limpio.** Gate bvg prod-fiel (flag
`BVG_TARGET_MODELS`) + flag `RERANK_TOP_K` (getenv, default 5) + pre-registro
(`evals/s98_bvg_gate_prereg.md`) LISTOS para GO de Alberto; **recomendación = no-ship-10-as-is**
(subir LLM_MAX_TOKENS o quedarse en top_k=8). Residual reranker (hp005/hp006 >rank-15) =
document-side. **s97 (DEC-091/091b): tie-break diversify NO-GO** (hp001 regresión de contenido;
bloqueado en el reranker — s98 midió ese "afinar el reranker" = NO-GO como fix de calidad).

**s96 (DEC-090): gate bvg de A3 EJECUTADO y PASADO 4/4** (plan dúo-hardened: 11/11 confirmados,
0 FP, 2 fixes críticos de código aplicados — fail-open del canal enunciados + parser estricto del
flag): rescate→top-5 3/3 golds-flip · PASS-control 11→13 (+2 en banda; residual 23→19) ·
invención sin subida (matriz pareada 10/33=10/33; **eje factual del atomic a K=1 INUSABLE para
A/B — norma nueva DEC-090**) · latencia p50 +725ms. hp006 JP2→JP6 = mispairing de SÍNTESIS
expuesto por el rescate → dossier síntesis. Held-out no consumido. 443 tests.

**A3 SHIPPED A DEMO (5 jul):** PR #111 mergeada por Alberto + `ENUNCIADOS_MULTIVECTOR=on` en
Railway + **verificado en producción** (post-flip completo: smoke e2e local con flag efectivo;
RPC de enunciados llamado por 2 queries reales de Telegram — timestamps casan con query_logs;
AFP-400 responde con el hecho antes-inencontrable 'Fallo de Tierra'/MPS-400 citado; CAD-150
idéntica pre/post-deploy = 0 regresión; latencia 34-47s en banda histórica). Rollback = quitar
la env var.

**Qué sigue (decisiones de Alberto, sin dependencia entre sí):** (1) **packet doc_map**
(MIE-MI-310↔zxe [DB: ZXAE/ZXEE] · MIDT190↔sdx-751 [DB: ID3000] · 15092SP [DB: INA]); (2) **T2-T3
re-scopeado** (no gastar por famtie; si se retoma: Sonnet 5 + gates por-tramo, DEC-088); (3) '35'
→ regeneración dirigida (C) opcional. Luego: lever diversify (hp011 + '99+99'); conduct-level
clarify + calc-assist CON Alberto (el deep-lookup D queda aparcado flag-off como hipótesis de ese
modo); S4/F3 re-tag; workstream SÍNTESIS (dossier con la evidencia nueva JP2→JP6). Backlog:
BRAND_MAP→`catalog_gt.py`; re-homing FL*; 6 homónimos cola; ~630 candidates; dual-judge ~sept.

**s90 (DEC-079): F0 APROBADO (D1-D7) → contrato CANÓNICO; F1a slice vertical Morley CONSTRUIDO.**
`catalog_store.py` (la puerta: validate reglas-duras + resolve con contrato `expand`, check-homónimo
PRIMERO) + slice cargado (`data/catalog/`: gt nivel-1 + semilla s83, doc_map por document_id 114/114) +
Catalog gate en CI + 378 tests. **El slice cazó 3 clases de bug antes del bulk** (colisión
alias↔canonical, divergent-unknown expandiendo, CI sin gate). Smoke: hp011 `RP1r`→prefer Supra ✓,
hp018 `ZXe`→3 variantes ✓. **QA ADJUDICADO y APLICADO (s90b: P1-P8, correcciones de dominio HRZ2-8/EXP×3/BRH-BGL cross-brand) → F1a CERRADO. Gate: merge #101 → F1 bulk (31 marcas) → F2 query-side tras flag.**

**s89 (DEC-078): gold-review Clase A APLICADO (adjudicación de Alberto; #97/#98 mergeadas).** hp004 →
**PASS 5/5 unánime (+1, PASS-map ~10/39)**; cat024 → PARCIAL 5/5 (sin FALLOs; discrepancia 7-vs-17
verificada al píxel = MISMO modelo); cat009/cat020 sin movimiento (el juez completista encuentra la
siguiente arista) → **el plateau se confirma post-gold-edit; el lever restante del bucket OTRO = dual-judge**.
cat012 resuelto-solo (ya PASS 5/5). ES/EN → `docrel language-variant-of` añadido al contrato del catálogo.
**Pendiente de Alberto: contrato F0 (D1-D7, ~1h) → F1.**

**s88b (2ª tanda nocturna): (A) Fase 0 DRAFTEADA + paquete de adjudicación.** (1) **Contrato de gobernanza del
catálogo canónico** (`docs/IDENTITY_CATALOG_CONTRACT.md`, DRAFT dúo-hardened): modelo de datos (producto/alias/
paraguas/**homónimo**/relación/doc_map por `document_id`), gobernanza anti-Excel-opaco (jerarquía de fuentes,
blast-radius manda, QA por lote, tally con error-rate), consumo (cascada check-homónimo-primero + clarify-si-
divergent-adjudicado + fail-open), fases F1-F4 con gates y criterios medibles. Dúo COMPLETO: cross-model-con-tools
6/6 + sub-agente H1-H9 (críticos: la cascada exact-match reproducía el −2 hp011; convergente≠correcto demostrado
en la semilla). **GATE: tus D1-D7 (~1h)**. (2) **Paquete de adjudicación Clase A** (`evals/s88_goldreview_packet.md`):
5 casos con literal + edición propuesta + casilla ✅/✏️/❌ → tu gate baja a ~15-20 min.

### Antecedente s83·F2 (DEC-067)

**s83·F2: activo de IDENTIDAD MULTI-LABEL LIMPIO de los 1014 docs construido (1014 docs, 2761 productos) vía extracción dúo (Opus 4.8 + GPT-5.5, ~$145 Batches API) + adjudicación de Alberto de los 29 conflicts; regla de granularidad + fold-in base-unión dúo-validados ×3; branch-local en `main` (PR #90), NADA en DB.** Es el bloque F2 que DEC-066 señaló como el lever (`LEVER2_IDENTITY`). **s84 midió su CONSUMO = NO-OP en el eval (DEC-069)** → el activo vale para findability/catálogo/30+/corrección, NO para recall del eval. Detalle: DEC-067, `s83_identity_asset.md`.

### Antecedente s83·retrieval (DEC-066)

**s83 (DEC-066): el pre-filtro vectorial family-aware (headline construido) = NO-OP MEDIDO → revertido; el lever de los model-filter-excludes es LEVER2_IDENTITY (resolución de identidad). Dúo #11 (sub-agente Opus + cross-model GPT-5.5) cazó el confound. NADA en prod/mergeado.** Tras **5 rondas de pushback** de Alberto (plan-primero + máxima autonomía/ultracode), el headline quedó en su punto 1: el canal vectorial NO pre-filtra por modelo (los léxicos sí). Construí el pre-filtro FAMILY-AWARE del canal vectorial (over-fetch 200 + filtro recall-safe `passes_nivel2 ∪ unknown`, flag `MODEL_PREFILTER`, a nivel doc/familia reusando `series_registry`). **VEREDICTO (aislamiento 2×2 hp018): el pre-filtro SOLO = INERTE; `LEVER2_IDENTITY` SOLO recupera el primario** (MIE-MI-310 corroborador → MIE-MI-530 e-series) — porque al resolver ZXe→ZX2e/ZX5e los canales LÉXICOS (que YA pre-filtran por modelo) recuperan el manual; el vectorial no necesita pre-filtrar (el post-filtro ya limpia su ruido). **El cuello era la RESOLUCIÓN de identidad, no el canal vectorial → el lever real = `LEVER2_IDENTITY` (B4, ya candidato en DEC-065).** bvg K=5 (hp018+hp009): recupera el e-series correcto en ambos; **hp009 residual→K-INESTABLE** (mejora, gana votos PASS), **hp018 residual→residual** (recall arreglado pero **reach≠PASS**, residual=generación/diodo) = **GRIS** (movimiento + 0 regresión, 0 PASS-control limpio). Pre-filtro **REVERTIDO** (eval-driven; 353 tests verdes restaurados). **Pieza 3 (bilingüe, $0)**: lever PEQUEÑO — 9 pares ES/EN casi-idénticos (~205 ch duplicados, dedup) + EN-only real solo 2-3 golds + ho002/ho014=ModuLaser NO-ingestado → fork s84. **Qué sigue**: decisión de Alberto sobre ship de B4 (corrección de identidad REAL —arregla ZXe↔ZXAE/ZXEE + mejora hp009—, pero GRIS no-PASS); s84 = A1 (matcher es-en + histograma verdadero, foundational), limpieza broad de identidad (~78 pm-compuesto + 114 mis-atribución), B5 (hp006 AFP-400 series), categorías (TECH_DEBT #44), versiones. **DEC-056 SIGUE (ranking); el RECALL vía identidad es lever DISTINTO.**

### Antecedente s82 (DEC-065)

**s82 (DEC-065): investigación CORPUS-GAP (prioridad de Alberto) + plan PRIMARIO/RETRIEVAL. Workflow 29-agentes + cross-model (dúo #10), 0 FP. NADA en prod (diagnóstico).** **VEREDICTO (acotado): los 9 CORPUS-GAP del audit s81 son FN del matcher léxico — 0 reales** (el valor está VERBATIM en el corpus, casi siempre el manual objetivo; raíz = es-en [LlamaParse extrae la columna EN de manuales multilingües] + OCR/acento + literal-compacto + filename≠doc-nº). Es el residual es-en que s81 declaró diferido → PROBADO material (fabricó el bucket). Verificado: verificadores frescos (volcaron chunks DB) + regla-C propia al píxel (cat007/cat020/hp013). **Histograma corregido: CORPUS-GAP 9→0** (reubican a RETRIEVAL o downstream-gen). **PRIMARIO 2/4 reales:** cat019/hp001 = falso-positivo de source-naming del audit (token gold ≠ filename; primario es #1 del pool); cat011 reach≠PASS; hp018 real (model-filter). **Cuello real = RECALL** (DEC-056 SIGUE: ranking agotado, recall es lever DISTINTO): model-filter-excludes ×3 (hp018/hp002/hp006) + recall-frontier-vector ×6. **PLAN A/B/C:** **A** instrumento/gold no-eval (A1 matcher CORPUS-GAP es-en/OCR-aware [raíz; versionar/congelar]; A2 matcher PRIMARIO slug-laxo; A3 gold cat011); **B** PROD model-filter MEDIR (B4 hp018 CANDIDATO `LEVER2_IDENTITY=ON`; B5 hp006 series-registry; B6 hp002 broad-fallback); **C** PROD recall-frontier MEDIR (C7 within-doc diversify [contrato+métrica]; C9 cat016 synonym-aware). Orden A→B4→B5/B6→C7→C9. `scripts/corpus_grep.py` = herramienta reusable. El cross-model cortó mi over-claim de framing OTRA VEZ (#42-#47, 6ª sesión = control estructural). **Qué sigue:** ejecutar el plan (fork abierto a Alberto: A1 matcher es-en vs B4 hp018-flip primero). **DEC-056 SIGUE (ranking); el RECALL es lever DISTINTO.**

### Antecedente s81 (DEC-064)

**s81 (DEC-064): instrumento del audit ARREGLADO (DEC-061) + audit de los 30 NO-PASS CORRIDO → distribución de raíces. Contrato de autonomía nuevo (`feedback_autonomy`: actúo-y-reporto, el DÚO es el anti-bias, stop-line=el merge lo da Alberto).** Re-secuencié D1 detrás del audit (orden de DEC-061): verifiqué al píxel que NINGÚN gold canónico apunta a ZXSe → la findability-D1 es eval-inerte + dispara el blast-radius del catálogo (DEC-063). **Instrumento (5 defectos de DEC-061(e)):** retiré el matcher roto del funnel; predicado limpio `fact_match_score` **VALOR-EXIGIDO** (el datum debe estar [cov>0] + texto como contexto → mata el FP 'prosa sin el dato' + el FN token-corto); `measurable` segrega no-medibles (single-digit `1 A`/`4 circuitos` → juez semántico diferido); confianza por SCORE (borderline), no a priori; primario-vs-corroborador con flag PRIMARIO-NO-RECUPERADO; fuente k5; K=1 (reranker temp=0). **Dúo #9 (3 rondas, 3 cross-model + 3 sub-agente Opus, 0 FP)** cazó en cada ronda — incl. una REGRESIÓN que introduje en `bvg_kmajority` (cazada por grep regla-C, legacy restaurado); capé en r3 (anti-#45). **HISTOGRAMA de los 30** (~93 hechos medibles + 19 no-medibles): **RETRIEVAL 28-38 (recall, NO ranking) ≈ SINTESIS 34-39 (gen/gold/juez) >> RERANK 6-7 >> CORPUS-GAP 9; 16 borderline; 4 PRIMARIO-NO-RECUPERADO (cat011/cat019/hp001/hp018).** **Lectura: DEC-056 (RANKING agotado) CONFIRMADO (RERANK ~7%) pero MATIZADO — el RECALL (~38%) NO está cerrado y es en parte IDENTIDAD → RE-VALIDA D1/D3 VÍA el bucket RETRIEVAL** (el instrumento-primero pagó: localizó dónde importa la identidad, vs findability-por-sí-misma eval-inerte). Caveats: 83% cobertura (19 no-medibles=juez semántico diferido), corroborador=SINTESIS (flags marcan lo peor), CORPUS-GAP=riesgo FN. reach≠PASS, NADA en prod (instrumento+diagnóstico, branch-local); 353 tests; held-out intacto. **Qué sigue:** atacar los co-binding — (1) recall/identidad: los 4 PRIMARIO + el bucket RETRIEVAL (D1/D3, por qué el primario no se recupera) — AHORA con eval-leverage demostrado; (2) generación/gold de los SINTESIS (gold-review + dual-judge ~sept) vía el deep-dive por-SINTESIS (C5, diferido); juez semántico para los no-medibles. **DEC-056 SIGUE (ranking); el RECALL es lever DISTINTO.**

### Antecedente s80 (DEC-062/063)

**s80 (DEC-062/063): backfill de identidad de la SERIE FAAST LT-200 APLICADO en prod (DB-only, findability de serie VIVA) + criterio gold D6 (core/supp=IMPORTANCIA). Verificado AL PÍXEL que NO arregla cat007** (standalone 6574 vs addressable 6575/6577 difieren en prealarma/lazo, pero los hechos de cat007 son IDÉNTICOS en las 3 → alcanzable vía 6574 → cat007 es downstream: rerank/gen/es-en/gold). **Backfill** `s80_faast_backfill.py` (FX1 6575 `LT-200`→`FAAST LT-200` 78 + FX2 6575-ES mfr→Notifier 41 + FX3 6577 `ASD11`→`FAAST LT-200` 73; count-match→snapshot→apply lotes-10→from=0 ∀; reversible). **Decisiones (Alberto):** manufacturer=`Notifier` pragmático (el seam multi-marca NO existe → OEM System Sensor + Morley → D3); 6577 pm=`FAAST LT-200` serie (modelo NFXI-ASD11 → D3, recuperable como metadata pero path bare de usuario perdido-hasta-D3). **NO eval-inerte** (product_model visible al generador) → guardarraíl findability+ por handler real + no-regresión; riesgo cross-gold BAJO (solo cat007 en la familia; "LT-200" sigue substring). **Criterio D6 (cross-model, cita BP TREC/RAGAS/DeepEval/ARES):** core/supp=IMPORTANCIA no provenance; inferencia válida si predicado⊆documentado; no-invención en el OUTPUT; **el eval CANÓNICO (juez holístico sobre `gold_answer`) es INERTE a `tipo`** → core/supp gobierna el audit, NO el veredicto. cat007 failsafe=inferencia válida (sin editar). **HALLAZGO LATENTE (DEC-063): `model_catalog.json` congelado en s55 (`8876e56`); prod LEE el json (no reconstruye) → el detector dinámico no refleja s64/s77/s78. PERO el gate lee la DB LIVE (`lookup_model_manufacturer`/`manufacturer_in_db` = httpx Supabase) → s77/s78 SÍ vivos; catálogo-stale = LATENTE (solo afecta extract de modelos post-s55, fall-through seguro), no bug activo.** Dúo: 2 cross-model (6/6+7/7) + 1 workflow 3-fases, 0 FP; #42/#43 reincidió 3× sobre framing, cortado por cross-model = control estructural. Lección #45/#46: verificar dominio AL PÍXEL yo mismo (preguntar no escala). reach≠PASS; 353 tests; prod (DB) tocado+reversible, held-out intacto. **Qué sigue:** D1 (backfill ZXSe `MIE-MI-600 unknown→familia` + split ZXe `ZX2e/ZX5e`, con split de catálogo + regen — `extract("ZX5Se")=[]` verificado) → arreglar el instrumento del audit (predicado limpio + banda error + fuente k5) → correr el audit de los 30 → priorizar. Backlog baja prioridad: re-sync catálogo s55→hoy (full no-regresión) + CI anti-drift. dual-judge gated (~sept). **DEC-056 (levers de RANKING agotados) SIGUE — NO re-litigado.**

### Antecedente s79 (DEC-061)

**s79 (DEC-061): gate pre-D2 → el matcher de recall (`chunk_has_quote_strict`) está ROTO (FP `'24'∈'240'`/`'2222'`∈cualquier chunk; FN prosa OCR) y contaminó las conclusiones de retrieval de la sesión (rank-53/64/87, "within-doc muerto", "corpus-gap cat016/cat007" — cat016/cat007 SÍ están en el corpus, SQL).** El plan de revisión de los **30 NO-PASS por raíz VIVE** (cascada CORPUS-GAP/RETRIEVAL-MISS/RERANK-MISS/SINTESIS + predicado bimodal + ejes generación/gold-design/judge), pero el **dúo (workflow 7-lentes Opus + 4× cross-model GPT-5.5) = CON-CAMBIOS, NO escalar aún**: el quote-path del funnel (`audit_retrieval_funnel.py:132`) sigue usando el matcher roto para ~63% de hechos; el juez semántico no está implementado (bias #44); C6 invertido (`audit_locator` tiene 2 fixes que el funnel NO tiene → portarlos); C3/C4/C5 con fallos (reranker equivocado / sin banda de error / fuente k5 / eje gold-design circular). **Hallazgos accionables SQL-verificados:** identidad FAAST LT-200 mal-tagueada en 3 manuales (6574=`FAAST LT-200`/6575=`LT-200`·System Sensor/**6577=`ASD11`**, OEM Notifier-exclusivo → el tag excluye el chunk del failsafe = mejora de retrieval VÍA IDENTIDAD, candidato backfill s78-style); gold-flags cat007 "FAILSAFE"=inferencia-no-en-fuente (no fabricada), **hp009=answer family-genérico** (NO clarify en bruto), hp018=mixto. **Lección `feedback_my_bias #45`: SOBRE-INSTRUMENTACIÓN + sobre-corrección** (espiralé construyendo aparato; al frenar el dúo sobre-corregí a "abandonar"=bias #30; Alberto lo cortó). reach≠PASS, NADA en prod (toda la sesión = investigación + diseño). **Qué sigue:** gold-review D6 (cat007/hp009/hp018, $0, primero) → backfill identidad FAAST LT-200 → arreglar el instrumento del audit (predicado limpio en el funnel + coste acotado + banda de error + fuente k5) → correr el audit de los 30 → priorizar. dual-judge gated (organic-eval ~sept). **DEC-056 (levers de RANKING agotados) SIGUE — NO re-litigado.**

### Antecedente s78 (DEC-060)

**s78 (DEC-060): curación de identidad del corpus (ground-truth de Alberto, 4 familias) → BACKFILL A APLICADO en prod** (correcciones de marca/etiqueta **eval-inertes**, reversibles vía snapshot): RP1r-Supra Morley→Notifier 312 [arregla el mismatch-refuse del gate, **LIVE**], NFXI-ASD Securiton→Notifier 135 (+7 docs), NFXI-FLX 83, canonicalizaciones ZX50 126/ZXR50A-P 18/RP1r 65 = 447 mfr+292 pm. Dúo #8 0 FP; **eval-freeze 9/39** (vs ~10/39 base = ruido del juez, sin movimiento, cero PASS→FALLO). **Securiton = marca aparte (Detnov la vende), NO Honeywell.** Lección HNSW: UPDATE masivo→`statement timeout` → PATCH en lotes (reusable). **Backlog (no perder, spec `_s78_identity_backfill_spec.md` §DIFERIDO + memoria):** **D1** findability ZXSe/ZX1e (tag combinado + **split del catálogo** en `build_model_catalog.py`+regen — verificado que el tag SOLO no basta, `extract("ZX5Se")=[]`); **D2** levers de retrieval de los ~10 golds (preview-2400 aislado + within-doc; pre-checks cat022/cat007 hechos); **D3** Capa-2 multi-marca (grupo Honeywell + alias OEM↔vendedor, **TECH_DEBT #5 trigger cumplido**); **D4** contrato #4 revisión (v04/v07 HLSI-MN-103); **D5** sección↔variante; **D6** gold hp009/hp018→clarify. **reach≠PASS, ~0 eval — es corrección de prod + escala, no la métrica.** Rubric del juez sigue en cola (organic-eval ~sept).

### Antecedente s77 (DEC-059)

**s77 (DEC-059): gate-fix #49 CABLEADO = fall-through manufacturer-aware (Option D) — PR #85, NADA en prod aún (Alberto mergea → Railway despliega).** El gate del handler ya no da falso-refuse cuando la marca está en DB pero el modelo es un nombre de FAMILIA. **Audit (`s77_gate_audit.py`, DB real) corrige el framing de s76:** los 6 catalog-miss son **familia↔variante** (CAD-150→CAD-150-8/R, ZXe→ZX2e/ZX5e, 40/40→40-40L/M; los "103/157/486 chunks" eran SUMAS sobre variantes), no "modelo ausente". **Medido judge-free** (`s77_fallthrough_measure.py` + `s77_regression_probes.py` K=3 + smoke por el HANDLER REAL `s77_handler_smoke.py` 10/10 + 353 tests): 6/6 fall-through MEJOR que el falso-refuse (cat013 refuse-inference ✓, cat021 clarify ✓), no-regresión del fallo opuesto (el path fiel admite/rehúsa 3/3). **reach ≠ PASS y CERO delta de eval — ESTRUCTURAL** (el harness bypasea el gate): corrección de PROD, no sube la métrica. Dúo #7 (Opus+GPT-5.5) 0 FP; el cross-model rebajó mi sobre-afirmación (bias #42). Los 3 mismatch (RP1r/Securiton-OEM) NO los arregla esto → contrato de identidad #49.

### Antecedente s76 (DEC-058)

**s76 (DEC-058): revisión estructural EXHAUSTIVA de los 29 NO-PASS en ultracode = la fase de levers de
RETRIEVAL está agotada de verdad; la única clase NO-tocada por esa fase es de DATOS.** 1 workflow
ultracode (29 agentes, 7 clases × diagnóstico + 3 lentes adversariales) + 2 cortes cross-model GPT-5.5
(8/8 y 7/7, **0 FP**). Alberto eligió ejecutar 3 acciones MEDIBLES (no parar):
- **(1) PROD-REACH (medido, judge-free, `scripts/s76_prod_reach.py`):** el gate manufacturer-check del
  handler (telegram_bot.py:292-339) corta **9/29 antes del RAG; 7 son cortes ERRÓNEOS** (verificado en DB:
  corpus con 103-581 chunks del modelo, pero el catálogo de `lookup_model_manufacturer` está
  DESINCRONIZADO [CAD-150/ZXe/40-40 ausentes] + el regex mete RP1r/Morley bajo Notifier); 2 son frontera
  OEM-relabel. → para esos 7, ningún fix de retrieval ayuda en prod; el fix es el GATE (#49, deploy-prep).
  Confirma el mecanismo del NO-OP de LEVER2_IDENTITY (ZXe cortado antes del RAG). **reach ≠ PASS.**
- **(2) Contrato de revisión #4 = SPEC** (`evals/_s76_revision_contract_spec.md`, diseño no-build):
  árbitro de precedencia (revisión=latest-wins vs variante-regional vs OEM vs multi-parte vs datasheet;
  ante duda NO supersede) + validación judge-free; **vía = backfill s64-style (sin re-ingestión ni DDL — columnas
  ya existen en `documents`, `revision_date` 1/1170 = gap del parser) → candidato CERCANO, no gated a ingesta**. La
  única clase estructural que el lever-phase de retrieval no tocó (cat009/cat024; cat008 es OEM-relabel→identidad).
- **(3) Sonda dual-judge holística (medido, `scripts/s76_dualjudge_sonda.py`):** el dual-judge holístico
  NUNCA se midió-primero (s47 midió los ejes del scorer, no el ruler de veredicto). Medido = **30.8%
  desacuerdo cross-model, 11/12 Claude más laxo**; cat019/cat020 = sesgo sistemático del juez
  triple-confirmado (audit humano should_be=PASS + Claude=PASS vs GPT-PARCIAL) → **2 falsos NO-PASS**
  (+cat012 debatible). "2º-juez+voto"=NO (laxo global, no toca el ±2 sampling); recalibrar-rubric-por-principio = real pero gated.

**NADA shippeado (plan MEDIDO, no delta de prod; eval-driven).** Sin cambio de código de prod (solo
instrumentos de medición + specs). 353 tests. **Recomendación:** gate-fix #49 SUBE (defecto latente
medido en prod, deploy-prep) · contrato #4 (build a ingesta) · rubric del juez (organic-eval ~sept).

### Antecedente s75 (DEC-057)

**s75 (DEC-057): audit-first de la raíz de identidad (DEC-054) = el detector tiene ~0 palanca eval real → DIFERIDO
a su gatillo (ingesta-30+), NO se construye como lever.** Alberto eligió medir antes de decidir build/defer/pivote.
El audit ($0, read-only, `scripts/s75_identity_audit.py` → `evals/s75_identity_audit.yaml`): **(1) palanca eval ≈0** —
de los 17 NO-PASS de retrieval (s71 track2), el detector toca SOLO cat013, y cat013 es gold de **CONDUCTA**
(`refuse-inference` cross-marca, verificado en `gold_answers_v1.yaml`) que el detector no arregla y podría EMPEORAR;
hp009/hp018 son **CONFIG** (e-series en `morley.yaml`, Brazo A ya construido), no el detector → confirma DEC-054
(identidad ⊥ inanición del pool) y refina hacia abajo el sub-claim "eval-medible cat013/hp009/hp018" de DEC-056(f).
**(2) escala = real pero ACOTADA, en proxies ruidosos** (no pisos): 78 etiquetas separador-aparente (sobre-cuenta:
`20/20I`), ≤114 docs mis-atribución (crudo 368 contaminado por códigos de manual que el catálogo MISMO heredó =
la circularidad que DEC-054 predijo), 18 clusters inconsistencia; concentrado en 3-4 marcas legacy (Notifier/Morley/Detnov).
**Dúo (sub-agente Opus + cross-model GPT-5.5, ronda FRESCA, 0 FP, fuerte convergencia):** confirma DIFERIR, corrige mi
FRAMING (sesgo #38/#39/#40: "≈0 medido/completo/BP" → honesto: 17/29 examinados, cat013=conducta, escala=proxy ruidoso,
falta freeze-contract). DIFERIR = gate/audit-primero funcionando (no construir aparato de 0 palanca antes del gatillo).
1 dúo, 0 FP. Rama `eval/s75-identity-audit` → PR.

### Antecedente s74 (DEC-056)

**s74 (DEC-056): Lever 1 BATCH (cluster de inanición del pool) CONSTRUIDO tras flags inertes + gate-0
judge-free = lift de retrieval REAL pero MODESTO → BANCADO (no shipped), A/B con juez DIFERIDO; el cuello
de retrieval se FRAGMENTÓ → siguiente = la RAÍZ DE DATOS, no más levers de retrieval.** Corrección de
arranque: el "ship `LEVER2_IDENTITY`" de s73 era **NO-OP en prod** (el `manufacturer-check` del handler
bloquea fabricante+pm-compuesto ANTES del retrieval; el eval lo bypasea = bias #40) → flag de vuelta a OFF.
**Build (353 tests, paridad probada, default OFF = prod inerte):** 2a `LEVER1_BROAD_FALLBACK` (broad-fallback
`5→effective_top_k`) · 2b `LEVER1_KEYWORD_ORDER` (keyword_search `order` determinista + limit 5→15; el dúo mató
el `order` por content_type del diag = over-fit) · 2c `RERANK_PREVIEW_CHARS` (preview reranker 800→2400).
**Gate-0 (factcov-sobre-top5, modal n=3 + firm-up n=7, ~$15, esquiva el ±2):** target 48%→67% @2400 PERO afinado
= **solo 2 golds fuertes+estables (hp008/hp002)** + 5 marginales (+1, dado-ruidosos) + **~3-4 regresiones**
(cat016, hp009, hp011-dado, **PASS-control cat022**). **2400 elegido por dato** (4000 peor; el CE Voyage lee su
propio 4000 → 4000 no aporta). **Decisión Alberto:** bancar tras flags (NO shippear — modesto + colateral + sin
usuarios + PASS sin medir); el A/B saldría casi seguro GRIS (±2 + dado). **Mapa de NO-PASS (workflow adversarial):**
29 NO-PASS = ~16 retrieval + 5 generación + 4 corpus-gap + 2 borderline + 1 diseño + 1 gold-injusto (cat012, único;
bias #20 verificado — el bot falla de verdad en 28/29). El cuello de retrieval **FRAGMENTADO** → no hay siguiente
lever de retrieval que valga (re-entra en la fase que DEC-051e cerró); cuellos vinculantes = el ±2 del ruler
(dual-judge = prerrequisito) + las raíces de datos del SWAP. 3 dúos + 2 workflows, 0 FP. Rama `eval/s74-lever1-batch` → PR.

### Antecedente s73 (DEC-054/055)

**Brazo A (identidad e-series) MEDIDO = FALLO→PARCIAL ×2 (GRIS, 0 regresión) → se shippeó `LEVER2_IDENTITY`
como tapón, PERO resultó NO-OP en prod** (el manufacturer-check del handler lo bloquea antes del retrieval; el
eval/smoke lo bypasean = bias #40 → corregido en s74, flag a OFF). **Identidad ESTRUCTURAL (DEC-054):** la raíz
es el detector LLM-en-ingesta (#49 refinado) — diseñado/anotado, construido al gatillo (ingesta 30+); config a
mano = tapón, NO "la identidad escala". Harness endurecido (`ab_verdict.py`+`s73_ab.py`, dúo 0 FP). 347 tests. DEC-054/055; HISTORY.

### Antecedente s72 (DEC-053)

**s72 (DEC-053): primer build de los fixes de retrieval (DEC-052) — Lever 2 (IDENTIDAD) tras
flags; Brazo A VERIFICADO end-to-end, Brazo B NO-OP hasta Lever 1.** Orden decidido con Alberto:
Lever 2 (identidad) ANTES que Lever 1 (profundidad del pool) = más barato/escalable/bajo riesgo.
**Brazo A** (alias-paraguas `model_aliases` + serie e-series en `series_registry`, flag
`LEVER2_IDENTITY`): **VERIFICADO contra corpus real** — el pool de hp009/hp018 se da la vuelta
(0→23/26 chunks reales ZX2e/ZX5e, espurio 22/26→0, +25 docs de serie MI-530) = **candidato a
ship; falta medir PASS** (eval-driven incompleto). **Brazo B** (rescate de pm mal-atribuido en
`_filter_to_query_models`, flag `LEVER2_PM_RESCUE`): correcto+seguro+testeado, pero **verify-first
= NO-OP para cat013** (los chunks SDX-751 no entran al pool [broad-fallback capado a 5] → el
rescate no recupera lo ausente → **bloqueado en Lever 1**). **3 rondas de dúo (incl. cross-model
GPT-5.5), 0 FP** — corrigieron el rumbo 3× (C roto/B-gate; paraguas-no-en-members; B-NO-OP =
`feedback_my_bias` operando). C (keyword-strip hp006) / D (section_path, TECH_DEBT #48 nuevo) /
cat001 DIFERIDOS. 330 tests; flags default OFF = prod inerte (paridad probada). DEC-053; HISTORY.

### Antecedente s71 (DEC-052)

**El re-análisis del residual (pedido por Alberto, escéptico del pivote s69)
= el cuello es RETRIEVAL, atacable con fixes concretos.** Dos tracks ortogonales con dúo
adversarial (workflows batched; rate-limits y apagones gestionados con resume). **Track 1
(audit del ruler, doble-escéptico auditor+defensor):** de 13 candidatos a "gold-injusto",
solo **cat012** sobrevive como maybe-PASS (debatible) — el guard anti-"trampas al solitario"
tumbó 4 que el auditor marcó injustos (cat009/cat011/cat019/cat020 = gold JUSTO, bot falló);
**el bot NO está infra-puntuado, escepticismo de Alberto validado**; 6 golds reclasificados
a retrieval-miss; 10 dudas para Alberto (`s71_track1_audit.yaml`). **Clasificación v2 de los
29 no-PASS** (`s71_classification_v2.yaml`): **16 RETRIEVAL-miss + 2 retrieval-family ≈ 18
(≈60%)** · 4 generación · 3 corpus-gap? · 2 borderline (bot ~correcto, PARCIAL conservador)
· 1 diseño (cat011 catálogo) · 1 gold-injusto (cat012). **Track 2 (diagnóstico de retrieval,
17 golds, 6 mecanismos, 16/17 fixable** — `s71_track2_retrieval_diag.yaml`): raíz común =
**INANICIÓN DEL POOL aguas arriba** — `keyword_search` limit=5 sin order (orden físico
arbitrario), broad-fallback vectorial capado a 5, reranker LLM lee solo `content[:800]` (el
hecho cae fuera). Fixes CONCRETOS y baratos (subir límites, order, ventana del reranker),
varios MEDIDOS end-to-end (hp003: preview 800→2400 → el reranker ya sirve el chunk correcto).
NO es el canal-broad (NO-GO s68). **El pivote-a-producto de s69 queda CORREGIDO: el residual
SÍ es lever-addressable — la conclusión "agotado" fue prematura (le faltaba este diagnóstico
quirúrgico per-gold).** DEC-052; HISTORY.

### Antecedente s69 (corregido por s71):

**s69 (DEC-051): A/B del lever de GENERACIÓN (completitud + guarda de fidelidad tras flag)
= NO-GO — y con él CIERRA la fase de levers-baratos del eval.** Tras el NO-GO del canal
(s68), el ciclo de generación completo: audit de resolución ($0 — el eval SÍ tiene
resolución) → **4 audits para fijar la diana** (el bias #20 reapareció en 2 capas: diana
inflada 12→8→5; el re-audit por relato-del-juez ERA bias #20, cerrado solo a
nivel-de-CONTENIDO: 4 sólida [cat008/cat020/hp005/hp014] + 1 recuperada [cat019]) → diseño
v3.2 con dúo r1+r2 + 2 cortes cross-model (enmiendas: **verificación content-level de los
flips decisivos** [bias #20 aplicado a la DECISIÓN], flag estricto, available_models como
SHIP-gate) → build tras flag `GENERATOR_PROMPT_VARIANT` (default base = prod inerte;
paridad a nivel-de-construcción $0 — no output-LLM que es no-determinista; suite 317) →
A/B (~$20): brazo `fidelity` (195 gen, 0 err, `assembled_sha` distinto = corrió de verdad)
vs `s67base` **re-juzgado en la misma tanda** (mata el drift del juez). **Resultado:
Δ_net=0 — NINGÚN gold de la diana flipeó a PASS; la predicción §4 FALSADA · +1 regresión
de conducta (cat011 clarify→answer, content-verificada) · verbosidad en 3 PASS-control.**
La **verificación content-level (enmienda B) PAGÓ**: el Δ=0 del juez solo habría dicho
"inerte", pero el prompt SÍ añadió completitud (hp014 metió FET=20 y el límite 32) sin
flipear modal Y rompió clarify en cat011 → cuadro real = efecto modesto + colateral, no
inercia. **Hallazgo del re-judge: ±2 de varianza del juez** (re-juzgar las MISMAS
respuestas base dio F 5→7). **NO-GO: flag default base (inerte); NO se salta a Opus**
(anti-racionalización §4 — el prompt-completitud falló, no es prueba de que la capacidad
sea el cuello). DEC-051; HISTORY. (s68 DEC-050 canal NO-GO; s67 DEC-048 CE ROLLBACK.)

**Lectura estratégica (la que define el rumbo de abajo):** 3 ciclos de lever barato, 3
negativos. El residual está **mapeado y desmenuzado** (corpus-gap diferido · within-doc-miss
· generación que el prompt no mueve · K-INESTABLE = ruido del juez) y **el ruler tiene ±2
de ruido** justo donde SHIP exige +2. Conclusión honesta: **la fase de exprimir-el-residual-
con-levers-baratos está agotada**; cada NO-GO costó ~$20-30 y evitó shippear ruido, pero el
valor marginal del siguiente micro-lever es bajo. Los unlocks reales son corpus (diferido a
demanda) y **eval orgánico (técnicos, ~sept)** — gated. El pivote: dejar de pulir el eval y
**preparar producto/deploy para cuando lleguen los técnicos**.

**Sistema (prod, Railway auto-deploy desde `main`; SWAP de corpus por `CHUNKS_TABLE`):**
bot Telegram (polling) → pre-clasificación → retrieve híbrido wide (vector Voyage-4-large 1024
+ keyword + intent; `RETRIEVAL_TOP_K=50`; HyDE off) → filtro de modelos series-aware (3
niveles, DEC-044) → **lifecycle end-to-end (4b + suplementos de diversify, DEC-045)** →
rerank LLM Sonnet (top-5; dispatcher `RERANKER_BACKEND` default `llm` — el swap a CE
Voyage se midió en A/B s67 = **ROLLBACK**, lever archivado con evidencia; el dispatcher
queda como instrumento) → generador `claude-sonnet-4-6` (temp=0,
`max_tokens=2048`) sobre
**`chunks_v2` = 25.090 chunks (262 excluidos por lifecycle → ~24.8k servibles; 25 huérfanos
residuales) / 1.170 docs {active 998 · superseded 3 · needs_review 79 · retired 90} / 31
marcas / 587 modelos** (contextual-retrieval 100%; identidad data-driven, DEC-035; **catálogo
de fabricantes 30 marcas** tras el backfill s65 + fix de paginación). **⚠️ Contratos rotos por
el SWAP s44, medidos:** `category` (#44) y diagramas (#45). Ventana DB ABIERTA (ef_search=120,
default mantener); ventana de freeze del corpus: CERRADA (s64); fingerprint con dimensión
lifecycle (DEC-045e).

**Eval (el ruler):** **51 golds = 39 dev + 12 held-out** (embargo vivo, intacto en s69),
taxonomía CONGELADA (DEC-033), juez GPT-5.5 + K-mayoría. **Baseline VIGENTE = re-freeze
`s67base`** (12 jun 2026: 10/39 PASS-control · 5 unánimes · 4 K-INESTABLES; manifest
completo + `s67_embed_cache.json` como pin de embeddings); frozen-s58 = referencia
histórica muerta. Próximo freeze: correr SIEMPRE con `EMBED_CACHE_PATH` (DEC-048c).
**⚠️ Límite de resolución medido (s69): ±2 de varianza del juez** — re-juzgar las MISMAS
respuestas base dio F 5→7. SHIP exige Δ_net≥+2 = justo en el suelo de ruido → el ruler
actual NO distingue fiable un win de +1/+2. Endurecerlo (dual-judge, s47§D) sería
prerrequisito de MÁS lever-work; gated a "¿vale sin técnicos reales?" (lean: esperar al
eval orgánico).

## Qué sigue (s77 — builds estructurales GATED, priorizados por s76/DEC-058)

**s76 entregó el plan MEDIDO** (no delta de prod). Los 3 fixes estructurales, por orden, TODOS gated:

1. **Gate-fix #49 (deploy-prep) — ✅ CABLEADO s77 (DEC-059, PR #85).** Option D = fall-through
   manufacturer-aware (`telegram_bot.py:315`): si la marca está en DB → fall-through al RAG en vez de
   hard-refuse; refuse solo si la marca también está ausente. Raíz auditada = **familia↔variante** (no modelo
   ausente). Medido judge-free (reach≠PASS, CERO delta de eval — el harness bypasea el gate; corrección de
   PROD): 6/6 fall-through mejor que el falso-refuse, no-regresión del fallo opuesto, smoke por handler real
   10/10, 353 tests, dúo #7 0 FP. **PENDIENTE: que Alberto mergee el PR #85** (Railway despliega al merge).
   Los 3 mismatch (RP1r/Securiton-OEM) NO los arregla → contrato de identidad #49.
2. **Contrato de revisión/precedencia #4** — spec escrito (`evals/_s76_revision_contract_spec.md`); la única
   clase estructural que el lever-phase de retrieval NO tocó (cat009/cat024; cat008 es OEM-relabel→identidad).
   **Vía = backfill guardarraíl-eado s64-style** (sin re-ingestión ni DDL — verificado en DB: las columnas ya
   existen en `documents`, `revision_date` 1/1170 = gap del parser [el 70%], `document_family` filename-naive →
   re-derivar; el `_filter_by_document_status` de s64 ya consume `superseded`) → **candidato CERCANO, junto a #49**,
   NO gated a la ingesta lejana; la corrección de prod (no servir revisiones obsoletas) se valida judge-free; el
   win end-to-end en eval (2 golds < ±2) sí necesita el dual-judge.
3. **Rubric del juez (completitud-correcta ≠ contradicción)** — sesgo sistemático MEDIDO (cat019/cat020 =
   falsos NO-PASS, triple-confirmado). Recalibrar por-principio cuando haya algo que shippear que dependa de
   ello, o en el eval orgánico (~sept), con cross-model + held-out. NO "2º-juez-y-voto" (laxo global).

**Diferidos confirmados (sin cambio):** detector de identidad (DEC-054/057, a ingesta-30+); batch Lever 1
BANCADO tras flags (lift modesto + colateral cat022; el A/B espera al ruler que importe); categorías #44 (NO
backfill — filtro-EQ muerto DEC-040; si vuelve, BOOST en ingesta nunca filtro).

**Fases macro (rationale en HISTORY):** F1 calidad (levers de retrieval = rendimiento decreciente; el ±2 del
ruler es el techo) → **F2 escala (identidad de producto en ingesta = EL siguiente bloque)** → F3 routing/tool-use +
multi-dominio del scope M&A → F4 eval orgánico + CI → F5 técnicos reales (post 1-sept).

**Diferidos vivos:** gate-fix #49 del handler (deploy-prep pre-sept — prod-reachability; sin usuarios no urge,
el eval no lo ve); **dual-judge** (s47 §D — prerrequisito si se mide algún win pequeño, DEC-051d); buckets
residuales de bajo-leverage en el ruler ruidoso (generación 5 [s69 NO-GO], corpus-gap 4, frontera/stamps,
cat016/cat007 [reranker no sube el chunk-en-pool], cat021 [variant-aware diversify], cat008 [generación pura]);
es-us (sin manuales US); contrato de ausencia formal (admit/refuse); prompt caching (umbral ≥50 queries/día);
language/revision_date masivos (contrato de ingesta); TECH_DEBT #40 (recall-gate CI)/#47/#48 (section_path);
**dureza de la tabla de decisión** (SOLO pre-registrado y motivado por evidencia, NUNCA post-hoc).
