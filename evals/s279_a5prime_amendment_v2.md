# s279 — Enmienda A5' al trim del plan v5 (v2 · POST-census · dúo focal adjudicado)

**Reemplaza el framing de `s279_a5prime_amendment_v1.md`** con las 7 correcciones adjudicadas
por el dúo. El instrumento y las cifras vienen del census re-corrido con el código enmendado
(`s279_selection_census_report_v2.md` / `_result_v2.json`, freeze-contract A1 = v1; commit dirty;
fingerprint estable en los 18 pares).

## 0. Naturaleza del cambio — CAMBIO DE DISEÑO POST-PROBE (no "corrección independiente del gold")

La v1 se presentó como "corrección de coherencia, NO calibración al gold" y afirmó que la regla
"se deriva de la CONSISTENCIA A5↔A7… no del resultado del probe". **Eso sobre-reclamaba
independencia.** La verdad honesta: **es un cambio de diseño hecho DESPUÉS de ver el probe** del
census fase IV (cat017 NOT_SELECTED). Lo que lo separa del gold-tuning NO es que no hayamos visto
el probe — lo vimos —, sino un **discriminador ex-ante** (§2) que existía antes del resultado y que
distingue la variante elegida de las alternativas. **`cat017` seleccionado bajo la vista real es un
RESULTADO A ADJUDICAR (E2E), no la prueba de que el cambio sea legítimo** (§5, §6).

## 1. Qué pasó — interacción adversa A5×A7 (NO "contradicción lógica")

La v1 dijo que A5 y A7 "se contradicen". **Corrección:** no hay contradicción lógica; hay una
**interacción adversa** entre dos reglas cada una correcta por separado:

- **A7** (gate): solo entran al gate los need-groups con ≥`N_FACET=3` términos.
- **A5** (trim): round-robin desde el ÚLTIMO grupo, retirando el último término, con suelo mínimo
  de 1 término/grupo.

El arquetipo nuevo del multi-match cae SIEMPRE en el último grupo (§3 del diseño lo fija para no
mover la faceta primaria). En una query larga que dispara el trim, A5 recorta ese último grupo
primero y —bajo el suelo-1 previo— lo deja por debajo del umbral de A7, que entonces lo excluye del
gate. Medido en cat017 (v1): el grupo commissioning `[sitio, edificio, licencia, bin, portal]`
(5 términos; `alta` es token de la query, NO del grupo — la v1 lo listó mal como de 6) llegó al gate
como `[sitio, edificio]` (2 < 3) → excluido por A7. La interacción es real; el marco "contradicción"
no lo era.

## 2. Enmienda A5' [SUELO] + la alternativa nombrada + el discriminador ex-ante

**Regla (implementada):** el trim no puede reducir un need-group por debajo de su **suelo**:
- suelo = `N_FACET=3` si el grupo tenía ≥3 términos ANTES del trim (era gate-elegible);
- suelo = 1 para los grupos de 1-2 términos (que A7 ya excluye).
Fase 1 (round-robin desde el último) salta los grupos que ya están en su suelo. Fases 2 (eliminar
GRUPOS enteros desde el último) y 3 (base > 480 ⇒ `plan None` con receipt) SIN cambios. El suelo es
posicional y se computa UNA vez sobre los grupos sin recortar; los índices de grupo quedan estables.

**Alternativa considerada y descartada (VISIBLE):** «si el trim bajaría un grupo gate-elegible por
debajo de `N_FACET` ⇒ **eliminar el grupo ENTERO**». Esta alternativa **tampoco hace pasar cat017**
(elimina el grupo commissioning, quitando el span-diana del alcance del gate).

**Discriminador ex-ante que justifica el suelo (no el resultado del probe):** la alternativa del
grupo-entero reproduce la clase de fallo **lever-muerto-por-construcción** que C3 (el arquetipo
nuevo) existe precisamente para EVITAR — deja **cero grupos-zombi sub-umbral, pero también cero
lever** (el arquetipo que se añadió para recuperar el gap CLSS nunca puede disparar). El
**suelo-preserve es la ÚNICA variante compatible con el propósito de C3**: mantiene el grupo
gate-elegible vivo cuando es factible, y solo lo mata (fase 2) cuando el presupuesto de 480 lo hace
inevitable. Este discriminador es previo al resultado; es lo que hace del suelo un fix estructural y
no una calibración al gold.

## 3. El régimen suelo-INFACTIBLE existe y se declara (no es un bloqueante)

Corrigiendo otra sobre-simplificación de la v1: el suelo **no siempre es factible**. Cuando flooring
TODOS los grupos gate-elegibles a `N_FACET=3` sigue superando 480, la **fase 2 elimina el grupo
entero de la cola** — mata la posición del arquetipo, pero **jamás deja un zombi sub-`N_FACET`**.

**Testigo IN-SET medido: `cat001`.** Su plan v5 necesita 18 remociones de término para caber; el
suelo solo permite **13** (flooring 4 grupos gate-elegibles a 3). `slack 13 < 18` ⇒ la fase 2 mata
el 5º grupo (`groups_removed=[4]`, `final_sizes=[3,3,3,3]`, tsquery 480→410). Es un **residual
medible, no bloqueante**: cat001 está `LANE_BLOCKED` aguas arriba por identidad
(`unverified_document_lineage`), así que nunca alcanza el gate — el kill de la posición del
arquetipo es observable en el plan, sin efecto en su veredicto.

## 4. Resultado MEDIDO (census v2 · 18 queries · freeze-contract A1 = v1)

**Solo 3 planes cambian v1→v2 (todos por el suelo); el resto byte-idénticos** (sus tsqueries no
superaban 480, el trim no se alcanza):

| qid | plan v1 (sizes / tslen / groups_removed) | plan v2 | régimen |
|---|---|---|---|
| cat017 | (4,4,4,2) / 477 / [] | **(4,4,3,3) / 468 / []** | suelo sostenido en FASE 1 (g3=`[sitio,edificio,licencia]`) |
| cat001 | (3,1,2,2,2) / 480 / [] | **(3,3,3,3) / 410 / [4]** | suelo INFACTIBLE ⇒ FASE 2 |
| ctrl_…_verbose (NUEVO) | — | (3,3,3,3) / 445 / [4] | suelo INFACTIBLE ⇒ FASE 2 |

Clases delta: `LANE_BLOCKED 13 · GAIN 4` (IDÉNTICO a v1) `+ SAME 1` (el control nuevo). El suelo
cambia el trim INTERNO de cat017/cat001 y el control nuevo, no la topología de alcance del set.

### 4.1 cat017 — probe adjudicado TAL CUAL (INCIERTO)

El suelo hizo lo esperado (§6): el grupo commissioning llega al gate como
`[sitio, edificio, licencia]` (3 términos, gate-elegible) y el diana `b7633e98` tiene una **ventana
de 360 con los 3 términos** (`terms_hit=3`: edificio+licencia+sitio). El diana pasó de
NO-elegible a **ELEGIBLE**.

- **Vista VACÍA (cota superior D2, el HEADLINE del instrumento): `NOT_SELECTED`.** Con todos los
  grupos en grado 0, el gate procesa el grupo 0 primero y sirve `a01755a8` (grupo 0, 3 términos,
  is_target=False). El diana, elegible solo por el grupo 3, pierde por PRIORIDAD DE GRUPO (no por
  inelegibilidad — el motivo cambió respecto a v1).
- **Vista = ganador-del-lane (subconjunto REAL de la vista servida de producción): SIRVE EL DIANA.**
  El ganador semántico servido cubre el grupo 1 (grado 3 = cubierto ⇒ excluido) y parcialmente el 0
  (grado 1); el gate reordena por cobertura y elige `b7633e98` = **el diana** (grupo 3, terms_hit=3,
  **is_target=True**, grades `[1,3,0,0]`). En v1 esta misma vista servía `a01755a8` (no-diana); el
  suelo **flipeó el resultado de la vista real de no-diana → diana**.

**Caveat honesto sobre el corolario D2.** La v1 (y el diseño) afirman «no-seleccionado con vista
vacía ⇒ definitivamente no-seleccionado». cat017 lo **refuta**: el diana NO se sirve bajo vista
vacía pero SÍ bajo la vista real. La razón: la vista vacía es la cota superior de ELEGIBILIDAD, no
de SELECCIÓN — la cobertura de grupos de menor índice bajo la vista servida REORDENA la prioridad
hacia el grupo del diana. El corolario D2 vale para alcance/elegibilidad, NO para el orden de
selección cuando la cobertura ayuda a un grupo de índice alto. Es un hallazgo, no un ajuste.

### 4.2 cat019 — NOT_SELECTED (esperado; el suelo NO lo toca)

Su plan v5 (arquetipo único `program_delay_cause_effect`, tsquery 415 < 480) **no dispara el trim**
(`trimmed=False`): byte-idéntico v1↔v2. El diana `f68f2d40` sigue no-elegible (máx `terms_hit=1`
por grupo; techo del pool `max_terms_hit_in_pool=2`). No se afloja `N_FACET` tras ver el resultado.
**Veredicto: NOT_SELECTED**, tal como se esperaba.

### 4.3 Controles negativos (§4.2) — los 3

- `ctrl_offtopic_mc380` (CCTV off-topic): 0 candidatos ambos brazos. NO sirve (empty=False,
  lane=False). Sanidad OK.
- `ctrl_ontopic_adjacent_mc380` (adyacente): sirve bajo vista vacía (artefacto D2/H3), **rechaza bajo
  vista real** (`no_eligible_candidate`). La salvaguarda depende de la cobertura de la vista servida.
- **`ctrl_ontopic_adjacent_verbose_mc380` (NUEVO · pre-registrado):** query verbosa MC-380 con
  tsquery PRE-trim ≈1229 chars ⇒ **ejercita el trim enmendado** (suelo + fase 2: `(3,3,3,3)`,
  tslen 445, `groups_removed=[4]`). Alcanza el pool (v5 cands=40) pero **NO sirve NADA bajo NINGUNA
  vista** (empty=False, lane=False; `no_eligible_candidate`; ningún candidato con ventana ≥3 de un
  grupo, `max_hit`∈{1,1,1,2}). **Pre-registro cumplido:** no sirve bajo la vista real (si sirviera,
  fallo del diseño). Es más limpio que el requisito (no sirve ni bajo la cota superior).

## 5. Criterio GO/NO-GO E2E (declarado)

**La adjudicación FINAL no es el proxy `SELECTED` del census, sino el smoke/pasada E2E: hecho
SERVIDO en la respuesta Y CITADO a la fuente.** El census adjudica alcance/elegibilidad/selección
sobre snapshots RPC ($0), con dos deviaciones declaradas (D1 anchor-route proxy, D2 vista servida
como cota). La vista=lane es un subconjunto REAL de la vista de producción, así que
«diana servido bajo lane» es señal POSITIVA fuerte — pero producción sirve MÁS (prefijo reranked +
coverage completos) y podría cubrir también el grupo 3, excluyéndolo. Por eso el resultado de
cat017 se **adjudica como INCIERTO** y el GO/NO-GO lo da la pasada real, no este proxy.

## 6. Expectativa honesta y qué queda

- **cat017 (expectativa declarada, cumplida en forma):** con el suelo, g3 llega como
  `[sitio, edificio, licencia]` y el pase depende de la ventana de 360 — la ventana SÍ captura los 3
  términos, pero el pase E2E depende además del orden de grupos bajo la vista servida REAL de
  producción. **INCIERTO — se adjudica tal cual** (vista real del census: diana servido; headline
  vista vacía: no-seleccionado por prioridad de grupo). Zanja la pasada, no el proxy.
- **Números corregidos:** post-trim canónico de cat017 = **477** (v1; la v1 dijo "445", erróneo);
  con el suelo el v2 es 468. El grupo commissioning es de **5** términos pre-trim
  (`[sitio,edificio,licencia,bin,portal]`), no 6 (la v1 incluyó `alta`, que es anchor de la query).
  **Residual cat019 = 2 FAILs (r1/r2)** de los 29 (la v1 lo atribuyó a "1 ítem hp017-clase";
  corrección adjudicada: el residual medible es cat019, 2 FAILs).
- **No tocado (residual declarado):** `N_FACET=3` y todos los órdenes quedan sin calibrar; cat019
  NOT_SELECTED se mantiene sin aflojar el umbral. **H0 (identidad aguas arriba):** 13/18 queries
  `LANE_BLOCKED` por `unverified_document_lineage`/`backfill:*` — workstream post-release de backfill
  de identidad, ajeno a C1/C2/C3, fuera de esta ronda.

## 7. Verificación de la enmienda

- Tests del trim (`tests/test_document_local_coverage.py`): suelo pineado (cat017-clase, fase 1),
  asimetría del suelo (grupo pequeño → 1), suelo-infactible → fase 2 (cat001-clase, sin zombi),
  sincronía `NEED_GROUP_GATE_FLOOR == N_FACET`, los 3 bordes A5 originales intactos, byte-igualdad
  flag-off intacta. **86 passed.**
- Census re-corrido completo ($0, read-only): 18 queries, freeze-contract A1 = v1, fingerprint
  estable en los 18 pares. Reportes: `s279_selection_census_report_v2.md` / `_result_v2.json`.
- **Pendiente (fuera de esta ronda):** oráculo baseline byte-inerte + smoke dirigido + pasada final
  E2E (§5) → lectura de Alberto → merge/flip.
