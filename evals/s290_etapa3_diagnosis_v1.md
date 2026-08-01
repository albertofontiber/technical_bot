# s290 — DIAGNÓSTICO CONSOLIDADO de etapa 3 (workflow 4 misiones + refutación adversarial + regla-C)

Estado: **DIAGNÓSTICO CERRADO, nada cableado.** Método: foto fresca post-etapa-2 (mapa 10
golds N=2, flags etapa-2 ON, recibos `s100_factlevel_smoke_v31_s290map_rep{1,2}.yaml`) →
workflow de 4 misiones judge-free en paralelo (recibos + código + DB read-only) + 1 refutador
adversarial POR misión (8 agentes, 0 errores) → verificación regla-C mía de las anclas de
carga → micro-medición $0 (rank-en-pool). Journal: `wf_010535cc-1a4`.

## Resultados por diana (los 4 miss frescos)

### 1. cat017#4 «CLSS» — **FN DEL INSTRUMENTO** (refutador: NO refutado; 2 correcciones no-materiales)
El fix A de s289 FUNCIONA end-to-end: `b7633e98` servido vía document_local en AMBAS reps y
las DOS answers transmiten el bloque CLSS citando [F14] (rep1.yaml:1853-1856,
rep2.yaml:1677-1681; F14 es la ÚNICA fila servida con los marcadores fire.eu/.bin/sitio —
verificado en DB). El instrumento lo clasifica rerank-miss porque:
- `support_over_served` (factlevel_assessment.py:622-642) es el ÚNICO eje **sin red
  dual-Opus** (el pool-side la tiene :737-744; el conveyed :834), con prompt «ante la duda,
  EXCLUYE» y sin persistir votos por-id → un near-threshold (G-3 midió GPT 2/5-0/5 en este
  hecho EXACTO, rescatado por dual 5/5) produce `n_support_served=0` indistinguible de un
  no-soporte real.
- El clasificador solo corre conveyed bajo `if reaches_gen:` (:825, ✓ verificado); `elif
  in_pool:` aterriza rerank-miss SIN mirar la answer (:857-860, ✓).
**Lever (instrumento, prioridad 1 — distorsiona el mapa):** (a) persistir votos por-id de
`v_served`; (b) rescate dual-Opus en `support_over_served` cuando el candidato servido pasa
el L1-guard (y en `support_over_append_content`, misma asimetría — corrección del refutador);
(c) guard anti-clase-falsa: antes de aterrizar rerank/retrieval-miss con fila servida
same-family que pasa L1-guard → conveyed-check; firme → OK. Medición que zanja: re-run de
cat017#4 (~10 llamadas juez) con votos logueados.

### 2. hp002#4 (SEGURIDAD, flip) — omisión discrecional + red determinista CIEGA a no-citados (refutación PARCIAL aceptada)
El serving cumple (5b6a3a19 servido F12 en ambas reps con el quote completo del aviso). El
mecanismo completo del flip (corregido por el refutador, anclas ✓):
- El generador omite discrecionalmente en el cuerpo (rep2: 0 menciones del gate; la
  instrucción de avisos es condicional, generator.py:370; el header del fragmento no marca la
  clase, :715-719).
- **La red de seguridad determinista YA EXISTE y habría transmitido el gate**: el anexo
  `must_preserve` (familia F-MANDATORY, prioridad 1) corrió sobre esa misma respuesta y SÍ
  transmitió OTRO aviso (51bc5368, citado) — pero `bind_atoms` exige fragmento CITADO
  (must_preserve.py:1685-1688, ✓ verificado) y F12 sin citar ⇒ átomo jamás exigible. La
  «evidencia de slot-competition» del diagnóstico original era output del anexo (código), no
  del modelo.
- Menor: el gate también está verbatim en un chunk del topk (6d5a807f §7.7) en ambas reps;
  `in_topk:false` del recibo = otra atribución del juez de soporte (refuerza el lever 1).
**Lever candidato (DETERMINISTA, no obediencia-a-prompt):** eximir a los fragmentos de
`obligation_warning_reserve_v1` de la compuerta de citación en `bind_atoms` (o apendizar
incondicionalmente la card del gate vía el anexo existente cuando el borrador no lo
transmite), consumiendo el `mandatory_warning`/`retrieval_lane` que la lane ya estampa.
Convierte la clase en no-omitible POR CONSTRUCCIÓN. Brazo alternativo (prompt/header de
clase-seguridad) = candidato paralelo, más débil. Verificación: reps `gen_answer_only` sobre
composición congelada, conveyed de hp002#4 pre/post, con centinela hp009.

### 3. cat017#2 «licencia CLIP por lazo» — **NO ES TECHO** (refutador cazó ancla falsa con hallazgo positivo)
- DOS carriers explícitos de la cardinalidad en el corpus (no uno): 5bb83899 (HOP-138-9ES
  p.5) y **4c186fb2 (4188-1125-ES p.17, tabla «Activar Características»: «una licencia de
  CLIP para cada lazo CLIP… dos licencias por módulo»)** — ✓ verificado en DB. Ninguno llega
  a la vista servida en ninguna rep.
- **Micro-medición s290 ($0, 1 embedding): `4c186fb2` está EN el pool a rank 18** (hermano
  b0273b01 rank 14; ventana pool_n=37). La clase real = **recuperado-pero-no-servido**: muere
  en la selección (rank>10; ninguna lane del perfil actual lo rescata).
- Segundo mecanismo (instrumento+identidad): los chunks del doc de licencias llevan
  `product_model="INSPIRE Panel"` y el crédito L1 los mata contra gold_families
  «INSPIRE E10/E15» (b0273b01 aparece en `support_l1_killed` de AMBAS reps) — el doc de
  licencias DEL panel E10/E15 no acredita por identidad de familia.
- Los NO-GOs previos NO cubren esto (corrección del refutador): S273 solo cerró el canal
  ENUNCIADOS para ese contenido (rank-99 era del brazo 4188-1125-ES, mis-atribuido); los
  trazados previos siguieron solo a 5bb83899.
**Levers a dúo:** (a) rescate serving-side de la clase (qué lane y con qué señal — DISEÑO
abierto, cuidado con re-litigar ancho/cuota settled); (b) identidad: normalización de familia
«INSPIRE Panel»↔«INSPIRE E10/E15» (workstream entity-linking #52.1, mecanismo concreto
nuevo); (c) instrumento: puente de familia panel-doc en el crédito L1. Micro-lever al
instrumento: estampar `pool_ids` en el recibo (hoy ausentes).

### 4. hp009#0 «Retorno» — CENTINELA APARCADO (refutador: NO refutado)
DEC-166: hp009 = nota-centinela de conducta para A3 (loop_eol). La conducta NO degradó
(ambas reps responden, 0 clarify). NO es objetivo de etapa 3 vía prompt; su rol = tripwire
(«hp009 sigue answer, 0 clarify») en CADA A/B de etapa 3 y en el gate de A3.

## Cola de etapa 3 re-derivada (bajo serving nuevo, subset 10 golds)
| diana | clase real | ruta |
|---|---|---|
| cat017#4 | instrumento-FN | fix instrumento (lever 1) — tras él, cat017#4 = OK |
| hp002#4 | generación+red-ciega | lever determinista bind_atoms (lever 2) |
| cat017#2 | recuperado-no-servido + identidad | levers 3a/3b/3c — diseño a dúo |
| hp009#0 | centinela | fuera de cola; tripwire |
| hp013#1 | techo seed-proximity (DEC-163d) | sin cambio |
Los synth fuera de los 10 golds quedan pendientes del full (diferido a decisión previa).

## Próximo paso
Dúo (sub-agente + cross-model Sol — instrumento y generación = zona-de-dolor) sobre los
levers 1 y 2 (build) y el fork de diseño de 3. Los micro-levers de instrumento (pool_ids,
votos por-id) van con el lever 1.

---

## Reconciliación dúo r1 (v1 → v1.1) — levers RE-SCOPEADOS

Dúo: Sol xhigh (6 hallazgos, 3 críticos) + sub-agente Fable fresco (7, convergente + propios).
Regla C: MP_SERVED_BINDING NO-GO (24/105, DEC-127×2) + citation_window + pool_n=53 verificados
por mí contra código/recibos. 4ª cazada de la sesión a la clase `feedback_my_bias` (proponer
lever sin grepear su settled: el brazo determinista de L2 era un flag ya construido y ya
NO-GO). Tallies ts=17:04:26.

### Declaración de OBJETIVO+MÉTRICA de etapa 3 (S6 — faltaba)
Objetivo: convertir los **synthesis-miss estables** bajo el serving nuevo. Métrica = per-fact
conveyed (instrumento, con la corrección L1 aplicada ANTES de los gates de L2/L3). Vara común
de no-regresión: sweep de composición + per-fact en todo gold cuya vista cambie (patrón s289)
+ tripwire hp009 (answer, 0 clarify) en CADA A/B. cat017#2 es clase rerank/serving (A7): entra
al arco pero FUERA de la métrica synth; su dimensión real espera el full.

### Levers v1.1 (adjudicados)
| lever | veredicto dúo | re-scope |
|---|---|---|
| **L1 instrumento** | GO-con-cambios | Solo (a) votos-por-id + (b) dual-rescue en `support_over_served` **y** `support_over_append_content` (asimetría verificada). **(c) guard conveyed EN HOLD** (cambia semántica de OK: L1-pass no es soporte adjudicado; crédito-por-memoria posible; redundante si (b) rescata). **= instrumento v3.2** — bump declarado, fila nueva no-comparable, **empaqueta 3c y pool_ids en el MISMO corte de serie**. Gate: re-run cat017#4 (~10 llamadas) + controles falsos (S3). |
| **L2 hp002#4** | GO-con-cambios | El brazo determinista NO es "por construcción": es **hipótesis nueva sobre población distinta del NO-GO medido** (MP_SERVED_BINDING 24/105 = binding genérico all-families; esto = 1 fila/respuesta, lane-estampada, solo F-MANDATORY; S274 exhausta era "para los 6 de entonces", hp002#4 no era uno). Diseño debe: citar DEC-127/134-C2 con métrica; ligar SOLO el span de la card `mandatory_warning` (jamás todos los átomos); equivalente de `atom_satisfied` sobre el span (dedup si el cuerpo ya lo transmite); render vía `render_appendix` existente; **gate FP pre-registrado tipo DEC-134-P3 (0 apéndices espurios, sweep-39)**; trampas medidas de ambos brazos (b2043 serving-view-sin-gatillo; irrelevancia del append) tratadas. Brazo prompt/header = paralelo débil. Construible flag-off en paralelo (SEGURIDAD); su gate GO corre bajo el instrumento v3.2. |
| **L3a serving cat017#2** | NO-GO-todavía | Antes de diseñar: **probe $0 de las 2 lanes existentes** (`RERANK_POOL_COVERAGE` — off por membresía del stack C1, no por NO-GO propio; hyq doc_scoped — DEC-166, outcome pendiente de A3) sobre pool congelado; incógnita real = barrera `MIN_ALIGNMENT_TERMS=6`. Encender RERANK_POOL_COVERAGE global re-abre el stack C1 (desproporcionado para 1 hecho). Dimensionar la clase con el full ANTES de diseñar lane nueva. |
| **L3b identidad** | RE-FRAME | NO es mecanismo nuevo: **doc_map.jsonl:90 YA mapea 4188-1125-ES → inspire-e10/e15** (umbrella s278). El gap = el crédito L1 usa `product_model` del chunk, no el doc_map. Normalización runtime nueva = doble verdad (bug canónico). Re-tag de corpus = clase en cuarentena (identity_quarantine_v1: regresión T3×replace) — ahí sí riesgo hp009/hp018. |
| **L3c puente L1** | GO-con-cambios | Legítimo consumiendo **doc_map** (fuente gobernada, role primary) — no ablanda el crédito. Va DENTRO del bump v3.2. |

### Secuencia adjudicada (A7)
**L1+3c+pool_ids (v3.2, un corte) → re-run mapa-10 → FULL de 39 (cola real bajo instrumento
corregido) → dimensionar recuperado-no-servido → L3a si paga. L2 en paralelo flag-off; gate GO
bajo v3.2.** Recibos pendientes exigidos antes del build (regla C del sub-agente): los votos
G-3 2/5→dual-5/5 y el rank-18 (se re-emiten con pool_ids del v3.2).
