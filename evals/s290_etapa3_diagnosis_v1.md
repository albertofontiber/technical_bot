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
