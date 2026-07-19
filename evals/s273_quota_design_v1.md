# s273 — Diseño + prereg: CUOTA del canal enunciados (Bloque B) — v1, para ronda de dúo

**Estado v1: DISEÑO + PRE-REGISTRO. Nada construido, nada medido, 0 escrituras DB, 0 pagos en esa
fase.** El dúo (sub-agente Fable + cross-model Sol xhigh — retrieval = zona de dolor, dúo
INNEGOCIABLE) revisó ESTE doc + `evals/s273_quota_prereg_v1.yaml` ANTES de cablear una línea.
Insumo canónico: `evals/s273_retrieval2_diagnosis_v1.md` (diagnóstico s272, ranks/sims medidos
en vivo contra `origin/main@5774a6c`).

> **v2 (misma sesión, post-dúo):** dúo adjudicado por Alberto — Sol 7/7 (3 críticos + 4 medios)
> + Fable 5/5 «SÓLIDO-con-condiciones» (3 medios + 2 menores), 0 FP. Contrato VIGENTE =
> **`evals/s273_quota_prereg_v2.yaml`**; los 11 fixes y los resultados de las fases sin-DB ya
> ejecutadas (F0 NO-GO → cat017#2 residual formal; F1/vía-A GO con servido; F2 dry-run
> verificado sin escritura) están en **§8**. Las secciones 1-6 se conservan como registro v1;
> donde difieran, manda §8 + el prereg v2.

---

## 0. Cabecera — fork de Protocolo 4, DECLARADO VISIBLE

**El settled y su autoridad (adjudicado por Alberto en s273; verificado verbatim en esta
sesión):** la cuota del canal enunciados **SÍ fue medida** — s105 (DEC-103 pre-Codex). La traza
canónica vive en `docs/PLAN_RAG_2026.md` §«Estado anterior (s105 — 10 jul 2026)», preservado en
la rama `codex/s107-wip-backup` (commit `33977c15f64705670ce377a9bfeee4cba47a9de2`; las
sesiones Codex renumeraron DEC-103+ para S194+ y pisaron los números s105–s107 — ver nota de
integridad documental al final). Verbatim del veredicto:

> «**s105 (DEC-103) — cuota del canal enunciados construida, revisada y MEDIDA → NO-GO a
> escala; tail parado y T1 restaurado.** F1 dedup-at-fusion + F2 cuota N=10 pasaron el gate
> barato a T1 (109 facts +0/−0; diana 4/4; suite 481), pero tras recargar T2+G0H (49.207
> filas; tabla A3 = 71.202) el gate definitivo dio **0 ganancias (<2 → STOP) y 2 anclas
> perdidas** (`hp006` Fallo de Tierra + ISO-X), además de served-containment nuevo en
> cat021/hp005/hp006. […] **R2 queda cerrado bajo esta mecánica; no subir N ni tunear contra
> hp006.**»

(Complemento del episodio previo: **DEC-102 (s104)**, `docs/DECISIONS.md:1682` — la carga 71K
SIN cuota, anclas perdidas hp005#2 + hp006#2/ISO-X, `evals/s104_t2_gate_anchors.json`.)

**MÉTRICA DE HOY ≠ MÉTRICA DE AQUEL NO-GO (por qué la reapertura es legítima, no re-litigio):**

1. **Escala:** el NO-GO fue a **71.202 filas** (recarga corpus-wide T2+G0H buscando gains); hoy
   se opera a **T1 actual (21.995 vivas)** — donde la cuota s105 midió +0/−0, es decir INOCUA —
   más una recarga **acotada a ≤2 documentos** desde dumps QA-passed (HOP-138-9ES + el doc de
   cat017 si difiere), ~23.9K « 71K.
2. **Diana:** aquel gate buscaba ganancias corpus-wide sin diana pre-identificada (0 gains →
   STOP); hoy hay **2 ganancias CONOCIDAS pre-identificadas por diagnóstico independiente**
   (s272): hp010#1 con su enunciado VIVO en tabla a sim 0.4268 muriendo en el floor 0.4556 del
   sort-mixto, y cat017#2 con doble carrier verbatim + gate offline F0 que decide ANTES de
   recargar.
3. **Mecánica:** el cierre es explícitamente «bajo ESTA mecánica» — y la mecánica s105 era
   **cuota-de-entrada-al-sort-mixto** (verificado en el código del backup, `retriever.py`
   @33977c1: `fused += quota; fused.sort(); results = fused[:top_k]` — los top-N padres nuevos
   ENTRAN al sort pero deben ganarse el floor real). Bajo esa mecánica **hp010#1 NO se
   rescataría** (0.4268 < floor 0.4556 muere igual, con cualquier N). La mecánica de HOY es
   **carve-out con slots reservados** (el patrón hyq DEC-099 literal, shippeado y vivo:
   `results[:top_k−Q] + quota`) — precisamente lo que el cierre s105 dejó fuera de su alcance.
4. **Guardas:** las de AMBOS gates (s104 Y s105) se **HEREDAN** como gates de F3: anclas hp006
   «Fallo de Tierra» + ISO-X (s105) y hp005#2 + hp006#2/ISO-X (s104) intactas, containment
   0-nuevo (con vigilancia explícita de cat021/hp005/hp006 — los del containment s105),
   negcontrol pool-level, diana famtie.

**Restricciones heredadas del cierre s105 (duras, vigentes en este prereg):** «no subir N» —
Q=6 **< N=10 de s105**, congelado antes de F1, NO se sube si falla; «no tunear contra hp006» —
hp006 es GUARDA (F3), jamás objetivo de tuning; Q se deriva del diagnóstico (rank-6-de-nuevos
de hp010), no de barrido contra golds; el NO-GO de cualquier fase se declara y para (no-retry).

---

## 1. Recomendación

**Fusión POR CUOTA del canal enunciados (espejo literal del patrón hyq DEC-099, shippeado y
vivo en `src/rag/retriever.py:1002-1010`), sustituyendo el sort-mixto de
`src/rag/retriever.py:944-946`, tras un flag nuevo default-off; + recarga ACOTADA a ≤2
documentos desde dumps h1 QA-passed, gateada por un gate offline PRE-carga (~$0.01).**

### 1.1 Mecánica exacta (lo que el dúo revisa; pseudocódigo contra el código real)

Hoy (`vector_search`, retriever.py:944-946 — el punto de muerte medido de hp010#1):

```python
merged = results + list(by_parent.values())   # reales top-50 + parents keep-max del RPC enunciados
merged.sort(key=sim, reverse=True)
results = merged[:top_k]                      # floor real 0.4556 > 0.4268 → parent p37 FUERA
```

Propuesto (bajo `ENUNCIADOS_QUOTA_FUSION=on`, default `off` = sort-mixto actual, prod inerte;
parser estricto a nivel de módulo, lección s96-H3/s102):

```python
# (a) keep-max boost de padres YA en pool (espejo exacto de hyq retriever.py:996-1001):
#     si el chunk real c está en results y by_parent[c.id].sim > c.sim → c.sim sube,
#     c["_enun_boosted"]=True (conserva la semántica de boost que hoy da el swap keep-max).
# (b) cuota de padres NUEVOS (espejo de hyq retriever.py:1008-1010):
new = [s for pid, s in by_parent.items()
       if pid not in {c["id"] for c in results} and s["sim"] >= ENUNCIADOS_MIN_SIM]  # barra 0.40
new.sort(key=sim, reverse=True)
quota = new[:ENUNCIADOS_QUOTA]                # Q = 6, marcadas _enun_quota=True
results = results[:max(0, top_k - len(quota))] + quota   # carve-out de la cola del canal real
# (c) INTERACCIÓN con el carve-out hyq posterior (retriever.py:1010): el recorte hyq debe
#     respetar las filas _enun_quota — composición final explícita:
#     reales[:top_k − |E| − |H|] + E + H   (E ≤ 6, H ≤ 10 ⇒ reales ≥ 34 slots garantizados).
#     Sin esta protección, el trim hyq evicta la cuota enunciados recién insertada (bug
#     conocido-por-diseño; test unitario específico en el build).
```

Aguas abajo NADA cambia: `_enunciados_swap` (retriever.py:1288) sigue haciendo el
surrogate→padre 1:1 con la sim del surrogate; `_merge_channels` (stamps), model-filter,
**diversify/interleave s59 INTACTOS** (las filas cuota-swapped compiten como chunks normales;
en los 2 targets medidos no hay presión de cap: hp010 pool 28<50, cat017 post_diversify 42<50).

**Prior art a HEREDAR en el build (código s105, backup `33977c1:src/rag/retriever.py:938-978`
— no se resucita a ciegas, se heredan sus fixes de dúo ya pagados):** (i) el **dedup-at-fusion**
(padre ya en `results` → boost keep-max SIN comprar slot; telemetría s105: a T1 el 43% de los
slots del canal eran esa pérdida pura) — es el paso (a) de arriba; (ii) la **atomicidad S4**
(dúo s105 r1+r2): boosts sobre COPIAS y reasignación de `results` como ÚLTIMA operación — un
body bien formado con tipos rotos cae al `except` con `results` INTACTO (fail-open real, sin
boosts parciales); (iii) tags de traceability `_enunciado_boosted` (espejo `_hyq_boosted`).
**Lo ÚNICO que cambia respecto a s105 es la línea de fusión:** `fused += quota; sort; [:top_k]`
(entrada-al-sort, la mecánica CERRADA) → `results[:top_k−|quota|] + quota` (slots reservados,
patrón hyq).

### 1.2 Hiperparámetros — fijados AHORA, congelados antes de F1, con su justificación

| knob | valor | por qué ESTE valor (no tuneado contra el gold) |
|---|---|---|
| `ENUNCIADOS_QUOTA` (Q) | **6** | El diagnóstico s272 midió el puente de hp010#1 en **rank-6 entre parents nuevos** — Q=6 es el MÍNIMO que lo admite, minimizando el desplazamiento de cola real (la guarda hp006). Además **6 < N=10 de s105** = cumple literalmente el «no subir N» del cierre. Derivado del diagnóstico, no barrido: si F1 con Q=6 no mete el parent al pool → **NO-GO, Q no se sube** (herencia del cierre «no subir N ni tunear contra hp006»). |
| `ENUNCIADOS_MIN_SIM` (barra) | **0.40** | = `RELEVANCE_THRESHOLD` (`src/rag/generator.py:375`), constante YA existente del sistema: un parent bajo 0.40 no puede ser servido nunca → slot de cuota desperdiciado. No es un knob nuevo ni elegido mirando el gold (hp010 0.4268 la cruza por mérito; cat017 lo decide F0). Distinta de la barra hyq 0.45 (aquella corrige el espacio-pregunta deflactado; aquí la escala es comensurable). |
| fetch-K, threshold canal, filtros | sin cambio | `ENUNCIADOS_FETCH_K=200`, threshold 0.3, paridad `filter_product` (012) — no se tocan. |

### 1.3 Recarga acotada (solo si F0 da GO)

≤2 documentos, desde dumps h1 QA-passed (activo YA pagado, mandato no-gastar-dos-veces):
- `HOP-138-9ES issue 5_11-2025_In` (doc `79a3471a`, carrier adjudicado p5): ledger
  `evals/enunciados_ledger.json` → sha `2964cab7…`, tranche T2, vintage h1, **925 insertables**;
  dump local `evals/enunciados_dump_T2.jsonl` (gitignored); si OneDrive lo desmaterializó →
  regenerar SOLO este doc con el prompt h1 congelado (≈$0.26, coste ledger 0.2572).
- `4188-1125-ES issue 5_11-2025_Li` (doc `484dd402`, 2º carrier verbatim p17): **NO está en el
  ledger** (nunca generado) → solo se genera (≈$0.26 + QA) si F0 con HOP-138-9ES sale NO-GO.

Batch nuevo `enunciados-v1:T2Q1:h1` (loader A3 `scripts/enunciados_pass.py`; DELETE selectivo
por batch = rollback documentado y barato). Escala resultante ≈ 21.995 + ≤1.9K ≈ **23.9K « 71K**
— dentro del régimen donde el canal está medido sano (DEC-089: «bien a 22K»).

---

## 2. Por qué es BP + estructural + escalable

- **BP:** Dense-X/HyPE canónico — un índice auxiliar tiene su PROPIO presupuesto de fusión
  («the question index has its own top-k»), exactamente el argumento con el que la fusión-por-
  cuota hyq se diseñó, gateó y shippeó (DEC-099, en producción desde s102). El sort-mixto entre
  un canal de 22K filas dirigidas y un canal real de 25K chunks es estructuralmente injusto con
  el canal chico cuando su valor está bajo el floor del grande — medido dos veces (hyq s101;
  enunciados s272/hp010).
- **Estructural (raíz, no parche):** arregla la FUSIÓN — el mecanismo exacto donde DEC-102
  diagnosticó el NO-GO de escala y donde s272 midió morir un CORE. No toca golds, no toca el
  reranker, no re-litiga diversify. Y es la ÚNICA vía que desbloquea el activo pagado: 54.849
  enunciados Haiku QA-passed en dumps + tail ~$95 no gastado quedan inertes mientras la fusión
  sea sort-mixto.
- **Escalable — HIPÓTESIS NO MEDIDA (re-encuadre v2, Sol-M7 + Fable-M3):** la cuota con barra
  *debería* ser invariante a la escala del canal (cap + floor a la vez), y el patrón mostró esa
  propiedad en hyq (70.134 filas con cuota 10 sin crowding) — pero para ENUNCIADOS no está
  medido y tiene un límite declarado: `FETCH_K=200` con `ef_search=120` = techo de recall del
  canal (a 71K el top-120 del scan puede no contener la fila puente aunque exista viva; además
  el NO-GO s105 a 71K perdió anclas CON cuota). El tail 71K es un GATE FUTURO propio, fuera del
  alcance de este prereg — aquí solo se acredita el régimen T1 + recarga acotada.

---

## 3. Alternativas consideradas y por qué se descartan

| alternativa | por qué NO (con su DEC/medición) |
|---|---|
| Subir knobs hyq (fetch-K 200→500, cuota 10→N, barra) | El diagnóstico s272 lo midió NO-lever para AMBOS: cat017 parent rank-36-de-43 post-family vs cuota-10 (ni con fetch-500 entra), hp010 cos hyq 0.156-0.276 « barra 0.45. Subirlos re-litiga DEC-099 sin diana. |
| Re-scope s174 per-facet (`access_prerequisite` pasó umbrales; lane s114 recupera p37 en local) | Riesgo **gate-shopping declarado** (packet s269): reabrir un gate conjunto por-facet tras verlo fallar en agregado es la definición del sesgo. La cuota lo subsume por mecanismo GENERAL (no per-fact). Queda declarada como SEGUNDA vía si la cuota falla su gate — decisión explícita de Alberto, no default. |
| Consumo aditivo del pool (pool 50+Q sin desplazar) | DEC-069/084: el pool aditivo está descartado; la cuota NO es aditiva — desplaza cola del canal real con competencia explícita de slots, el mecanismo ya shippeado en hyq (DEC-099). |
| FTS/BM25-sobre-pregunta | DEC-085 NO-GO; y los tokens aguja no están en la query («licencia» no aparece en cat017; «nivel 3» no aparece en hp010). |
| Tie-break coseno del diversify | DEC-091/s101 NO-GO definitivo (centinela hp001 regresa con ambos anchos). |
| Afinar reranker / ancho | DEC-092 (6 métodos NO-GO) / DEC-092b (top-10 ya shippeado): irrelevantes — ambos misses son PRE-reranker (not-in-pool). |
| neighbor-window / ef_search / más contexto | s86 medidos NO-GO; p37↔p48 no son vecinos. |
| Re-carga corpus-wide sin cuota (repetir s104) | DEC-102 NO-GO con STOP disparado — precisamente lo que NO se repite; la recarga aquí es acotada a ≤2 docs y gateada por F0. |
| Reintentar la mecánica s105 (cuota-de-entrada-al-sort, N=10) | Es la mecánica CERRADA por el veredicto s105 («R2 queda cerrado bajo esta mecánica») Y, medido en s272, **no rescataría a hp010** (el parent debe ganarse el floor real: 0.4268 < 0.4556 muere con cualquier N). Se heredan sus fixes de código (dedup-at-fusion, atomicidad S4), no su línea de fusión. |
| Re-carga corpus-wide CON el carve-out (tail ~$95 de una vez) | El NO-GO s105 a 71K fue con cuota (0 gains + anclas hp006 perdidas + containment): la escala 71K está medida hostil incluso acotando el desplazamiento. Primero el mecanismo debe pagar en acotado (F0-F4); el tail es decisión futura de Alberto con SUS gates, fuera de este prereg. |
| Variante «top-up» (cuota-garantía SIN cap: sort-mixto actual + relleno hasta Q parents) | Preserva anclas por construcción PERO no resuelve el crowding a escala (el modo de fallo DEC-102) → dos mecánicas conviviendo y el activo de 54.849 seguiría bloqueado. El espejo hyq completo (boost keep-max + carve-out) es el que ya está validado en producción para el canal chico; la preservación de anclas se MIDE (F3), no se asume. |
| Redactar enunciados nuevos mirando los golds | Prohibido (overfit al eval): SOLO se usan enunciados h1 chunk-side YA generados y QA-passed, no query-aware. |

---

## 4. Gaps / riesgos conocidos (declarados de entrada)

1. **Dilución hp006 (LA guarda):** la cuota desplaza hasta 6 filas de la cola del canal real en
   TODAS las queries — y el carve-out desplaza MÁS agresivamente que la mecánica s105 a igual Q
   (slots garantizados aunque el parent no gane el floor, vs ganarse el floor): es el precio
   declarado de rescatar lo-bajo-el-floor. Mitigación estructural = barra 0.40 (solo parents
   servibles compran slot) + Q=6<10. Los DOS modos de fallo medidos perdieron anclas por
   desplazamiento de cola: s104 hp005#2 + hp006#2/ISO-X; s105 hp006 «Fallo de Tierra» + ISO-X
   (+ containment cat021/hp005/hp006). Guarda = matriz de transición de anclas completa (109
   facts, 39 pools, K=3) con STOP en cualquier pérdida de la UNIÓN de ambos sets
   {hp005#2, hp006#2/ISO-X, hp006 Fallo de Tierra} y en lost>gained (F3).
2. **Cambio de comportamiento corpus-wide:** bajo cuota, los parents que HOY entran por
   sort-mixto ganándose el floor quedan capados a 6 por query (además del boost keep-max, que
   se conserva). En golds famtie ganados por el canal (A3 12→7) podría regresar → diana famtie
   39 en F3 si el gate de anclas dispara raro.
3. **Q fijo puede no bastar:** si F1 con Q=6 no mete el parent p37 al pool → NO-GO declarado;
   Q NO se sube (restricción heredada §0). hp010#1 pasaría a residual con el diagnóstico como
   traza.
4. **cat017 puede no cruzar NI con cuota:** el rank de sus enunciados de dump contra la query
   es DESCONOCIDO (el doc tiene 0 filas vivas del chunk). Por eso F0 (offline, ~$0.01, sin
   tocar DB) decide ANTES de recargar; F0 NO-GO en ambos carriers ⇒ **cat017#2 residual
   formal** (lo que s188 release_boundary.next y PLAN ya prescriben) y F2 no se ejecuta para
   ese doc.
5. **Interacción de los DOS carve-outs (enun + hyq):** sin la protección §1.1(c), el trim hyq
   evicta la cuota enunciados. Es el punto más delicado del build → test unitario específico +
   revisión del dúo sobre esa línea.
6. **Rerank no determinista (DEC-096):** «servido» en F1/F4 es 1 muestra, no-retry; el criterio
   PRIMARIO de F1 es entrada-al-pool (determinista). La conversión a nivel respuesta (F4) se
   reporta como medida, no como promesa.
7. **Dumps locales no versionados (OneDrive):** si el dump T2 no está → regen del doc ($0.26,
   prompt h1 congelado del ledger). Declarado en presupuesto.
8. **Artefactos s272 del replay** viven en scratchpad (no versionados): el prereg los pinea por
   sha256 (§YAML `inputs.frozen_artifacts`) y el build los copia a la rama antes de F1.
9. **Embeddings de query re-computados** (no persistidos en s272): drift Voyage ±ε — tolerancia
   declarada ±0.005 sobre las sims citadas; los floors/ranks del diagnóstico son la referencia,
   el replay F1 los re-verifica con el embedding fresco antes de aplicar la cuota.
10. **Ruta harness ≠ ruta Telegram** (nota §e del diagnóstico): el gate del handler puede pedir
    aclaración antes del retrieval en vivo; la conversión F4 es de la ruta harness (la misma del
    funnel 143/157). No se reclama nada sobre la ruta viva.

---

## 5. Fases gateadas (contrato completo y ejecutable en `evals/s273_quota_prereg_v1.yaml`)

| fase | qué | gate → NO-GO significa | coste techo |
|---|---|---|---|
| **F0** | Gate offline PRE-carga cat017: embedir enunciados h1 del dump HOP-138-9ES (y 4188-1125-ES solo si HOP NO-GO, generándolo), simular la unión con las filas vivas del RPC → ¿algún enunciado de los carriers entra al top-6 de parents nuevos con sim ≥0.40 para la query cat017? | NO-GO ⇒ cat017#2 **residual formal**; F2 no corre para ese doc; el lever sigue para hp010 solo | $0.01 (+$0.26+QA si hay que generar 4188) |
| **F1** | Cuota-only sobre T1 VIVO, sin recarga: (i) replay determinista de la fusión §1.1 con probe RPC read-only + pools s272 pineados → ¿parent p37 entra al pool-50 de hp010? (ii) 1 rerank e2e → ¿se sirve? (informativo, 1 muestra) | NO-GO (no entra al pool con Q=6) ⇒ STOP del lever; Q no se sube; hp010#1 residual con traza | ~$0.06 |
| **F2** | Recarga acotada ≤2 docs (batch `enunciados-v1:T2Q1:h1`, reversible), SOLO si F0 GO **y** F1 GO **y** dúo GO **y** GO de Alberto (única fase con escritura DB) | — | ~$0.10 (+regen condicional) |
| **F3** | Gates heredados de AMBOS episodios (s104/DEC-102 + s105/DEC-103-pre-Codex): probe 39 pools × K=3 × 2 brazos (`s103_displacement_probe` reutilizado) → anclas (STOP: pérdida de cualquiera de {hp005#2, hp006#2/ISO-X, hp006 Fallo de Tierra}, o lost>gained), containment served-ids 0-nuevo-perdido con vigilancia explícita cat021/hp005/hp006 (el containment del NO-GO s105), negcontrol pool-level (patrón s102), diana famtie 39 SOLO si algo dispara raro | NO-GO ⇒ rollback F2 por batch + lever NO-GO documentado | ~$0.10 |
| **F4** | Conversión a nivel respuesta: `factlevel_assessment.py smoke --qids cat017,hp010` (2 generaciones + matcher juez GPT-5.5 K-mayoría congelado DEC-023/095) → ¿cat017#2 y hp010#1 convierten? | Se REPORTA (no gatea el ship del flag: eso es decisión de Alberto con todo el paquete) | ~$0.30 |

**Techo total $3** (incluye el brazo condicional de regen). SHAs pineados, no-retry, seeds y
tolerancias en el YAML. Todo NO-GO se estampa; nada se re-corre para «mejorar» el resultado.

## 6. Qué NO hace esta sesión / qué queda para después del dúo

- NO se construye el flag ni la fusión (ni una línea en `src/`); NO se escribe en DB; NO se
  paga nada. Este doc + el YAML + sus tests de esquema son el único output.
- Tras el dúo: build del seam flag-off + tests unitarios (incl. §1.1(c)) + ejecución F0→F4 por
  fases con sus STOPs + decisión de ship/residual de Alberto con las cifras en la mano.

---

## 7. Nota de integridad documental — colisión de numeración DEC-103..105

Detectada en esta sesión y adjudicada por Alberto: **las sesiones Codex renumeraron DEC-103+
para S194+** (`docs/DECISIONS.md:1719` → DEC-103 = s194/planner), pisando los números de las
decisiones pre-Codex s105–s107, cuya traza canónica vive SOLO en el PLAN/HISTORY de la rama
`codex/s107-wip-backup` (commit `33977c15f64705670ce377a9bfeee4cba47a9de2`) — p.ej. el veredicto
de la cuota (s105, «DEC-103» pre-Codex) citado en §0. La nota de
`evals/s269_triage_12misses_v1.yaml:679-681` («s105–s193 solo tienen traza en artefactos») era
correcta pero incompleta: la traza s105–s107 está en ese backup, no en `evals/s1xx_*` de main.
**Propuesta (no ejecutada aquí — este prereg no renumera nada):** hasta una re-numeración
formal, toda referencia futura a las DEC pre-Codex del rango 103–105 cita
«PLAN §estado-sXXX» (con el pin del backup) en lugar del número DEC, para que el gatillo de
Protocolo 4 («grep DECISIONS antes de opinar») no vuelva a resolver al DEC equivocado.
(v2/Fable-M1: la sección s105 queda además VERSIONADA verbatim con pins en
`evals/s273_s105_authority_excerpt_v1.md` — la autoridad ya no depende de la rama de backup.)

---

## 8. Enmiendas v2 (dúo adjudicado: Sol 7/7 + Fable 5/5, 0 FP) + build + fases sin-DB ejecutadas

**Los 11 fixes aplicados** (contrato ejecutable completo en `evals/s273_quota_prereg_v2.yaml`):

1. **Sol-C2b (crítico, prod-neutral):** con la cuota OFF, las filas del batch F2 se excluyen
   post-fetch por id contra un manifest VERSIONADO (`--ids-out` del loader; ids deterministas
   del dump). El RPC 012 NO acepta filtro de batch ni devuelve `ingest_batch` (verificado) →
   exclusión cliente. **Over-fetch compensatorio declarado NO-OP** (techo real del scan =
   `ef_search=120` < FETCH_K=200, medido s272) → la byte-igualdad del scan NO se promete; la
   neutralidad se verifica con el brazo OFF-pre/OFF-post del A/B (residual DEC-088 declarado).
2. **Sol-C1 (crítico, loader real):** `scripts/s104_a3_load.py` extendido con
   `--only-source-files` + `--rewrite-batch-tag` + `--ledger-check` (sha exacto contra el
   ledger) + `--ids-out`. Dry-run ejecutado y VERIFICADO: 2 docs sha-OK, 1326 filas al batch
   `enunciados-v1:T2Q1:h1`, delete-scope exacto impreso, 0 de los 1326 ids vivos en DB (GET).
   Caveat declarado: `_existing_ids` pagina a 1000 (cap PostgREST) → la carga real va con
   `--replace`.
3. **Sol-C2a (crítico, A/B completo):** F3 = dos brazos — (i) OFF-pre vs OFF-post (efecto de
   la recarga sola, el modo s104; solo aplica si F2 corre) y (ii) OFF vs ON (efecto de la
   cuota); ambos con la unión de anclas heredadas s104+s105.
4. **Sol-C3 (grafo):** hp010 = **vía A** (quota-only sobre filas VIVAS; F1→F3→F4, sin F0/F2);
   cat017 = **vía B** (F0→F2→F3→F4). El NO-GO de F0 NO bloquea la vía A — así ocurrió.
5. **Sol-M4 (outcome):** F4 pasa de informativa a **GATE de ship**: ≥1 conversión ESTABLE a
   nivel respuesta (K=3 generaciones, convertido en ≥2/3, juez congelado).
6. **Sol-M5 (instrumento ejecutable):** `scripts/s273_quota_gates.py` implementa DE VERDAD
   probe K=3 / compare / negcontrol con umbrales numéricos heredados: anclas **+0/−0** (STOP
   duro en `hp005#2:misma zona o subzona` · `hp006#2:ISO-X` · `hp006#0:Fallo de Tierra`),
   containment **0-missing** (vigilancia cat021/hp005/hp006), negcontrol **≤7 EXCESS-HIGH**
   (clon del patrón s102), K-mayoría 2/3 pre-declarada.
7. **Sol-M6 + Fable-menor (framing honesto):** Q=6 es **TARGET-DERIVADO** del rank de hp010,
   congelado sin retry; la generalidad la acreditan F3/negcontrol, no la derivación.
8. **Sol-M7 + Fable-M3:** «escalable» re-encuadrado como HIPÓTESIS no medida (§2 enmendada);
   FETCH_K/ef_search declarados como límite de recall a escala; tail 71K = gate futuro.
9. **Fable-M1:** autoridad s105 VERSIONADA (`evals/s273_s105_authority_excerpt_v1.md`).
10. **Fable-M2:** F1 re-etiquetada «verificación de consistencia» (solo falla por drift); el
    gate load-bearing del lever es F3.
11. **Fable-menor-2:** test explícito de los DOS carve-outs simultáneos (E+H) con pool<50 —
    `tests/test_s273_quota_fusion.py`.

**Build ejecutado (esta sesión):** flag `ENUNCIADOS_QUOTA_FUSION` default-off (parser estricto
import-time) + `_fuse_enunciados_quota` (carve-out slots reservados + dedup-at-fusion +
atomicidad S4 del prior art s105) + protección del trim hyq + exclusión T2Q1 flag-off +
propagación del tag `_enun_quota` en el swap. 12 tests unitarios verdes.

**Fases sin-DB ejecutadas (~$0.22 de $3):**

| fase | resultado | evidencia |
|---|---|---|
| **F0 (vía B, cat017)** | **NO-GO** → **cat017#2 RESIDUAL FORMAL**; F2 deshabilitada | Run 1: el dump h1 de HOP-138-9ES NO cubre el chunk carrier (0 filas parent `5bb83899`; 61/100 parents; pp. 5-7 ausentes; 0 filas «licencia» en 925) — gap del ACTIVO de generación, no del instrumento. Brazo condicional pre-registrado ejecutado: 4188-1125-ES generado h1 acotado ($0.10; 408 filas; 29 «licencia»; 2 filas del carrier `4c186fb2` — resumen-tabla sin el cuantificador): best_sim 0.4782 → **rank-99-de-108** nuevos vs floor de cuota 0.614. Ni con cuota. `evals/s273_f0_offline_gate.json` |
| **F1 (vía A, hp010)** | **GO** | Consistencia s272 OK (drift ≤0.005); replay con la mecánica REAL: rank-6-de-nuevos exacto → entra por cuota Q=6; e2e: p37 en pool (16/28) → **rerank top-2 → SERVIDO** (1 muestra, informativo, no-retry). `evals/s273_f1_viaA_replay.json` |
| **F2** | NO ejecutada (contrato) | Dry-run VERIFICADO (fix 2). Deshabilitada por F0 NO-GO; la vía A no la necesita. |
| **F3/F4** | pendientes — las corre Alberto | Comandos exactos en el prereg v2 §F3/§F4. Con F0 NO-GO, el A/B queda OFF vs ON sobre T1 vivo (sin recarga). |

**Lectura del resultado:** el Bloque B queda en su forma final de decisión — hp010#1 tiene
mecanismo construido + rescate medido end-to-end (pool → top-2 → servido, 1 muestra); cat017#2
es residual formal CON evidencia fina (el hecho-licencia no existe en el espacio-enunciados
generable barato: ni el activo T2 lo cubre ni el h1 fresco lo produce con señal — su vía viva
seguiría siendo re-scope s174 per-facet, decisión explícita aparte por riesgo gate-shopping).
Ship del flag = decisión de Alberto tras F3+F4.

**Lección de coste anotada (feedback_cost_discipline):** `enunciados_pass.py --dry` GENERA
(paga el modelo; solo omite dump/ledger) — el «dry» costó $0.05 no previstos. Los techos
absorbieron el desvío (F0 cerró en ~$0.12 de $0.30), pero el flag merece renombrarse en una
sesión futura (no aquí — fuera de scope).
