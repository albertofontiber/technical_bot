# s288c — DIAGNÓSTICO DE LAS PUERTAS CONTENT-KEYED EXISTENTES (pasos 2-3 de la ruta re-adjudicada por el dúo r2)

Estado: **DIAGNÓSTICO CERRADO, nada cableado.** Ejecuta los pasos 2 y 3 de la «RUTA
RE-ADJUDICADA» de `evals/s288c_composition_lever_respec_v1.md` (F3 + F7 del sub-agente).

- Probe: `scripts/s288c_gate_funnel_probe.py` · Recibo: `evals/s288c_gate_funnel_probe_v1.json`
- **Coste declarado: 2 llamadas de embedding** (`retrieve_chunks`, una por gold). **0 LLM · 0 juez ·
  0 escrituras en DB · 0 ediciones de código/config.**
- Perfil: `coverage_c1_v4`, flag-set DEMO idéntico al del instrumento v3.1
  (`factlevel_assessment.py:62-120`), re-afirmado tras `load_dotenv`.
- **Fidelidad de la reproducción (regla-C contra mí mismo):** el seam reproduce los artefactos
  HEAD **exactamente** — cat017 apendiza `5880b3b6 + 470a499b` (structural) `+ 1452c904`
  (obligation_warning), idéntico a `s100_factlevel_smoke_v31_cat017_head_rep1`; hp002 apendiza
  `1d1ca159 + 339f06e0`, idéntico a `p1map_rep{1,2}`. Se corrió en **dos ventanas de pool
  distintas** (cat017 `pool_n` 50 y 54, con el portador en rank de pool 15 y 44 — la
  inestabilidad §2.3 confirmada) **y el funnel dio el MISMO punto de muerte en ambas**: el pool
  de la puerta document-local sale de la RPC FTS document-scoped, no del rank vectorial, así que
  el diagnóstico es INMUNE a §2.3. Eso es un resultado, no una suposición.

---

## MISIÓN A — cat017: por qué `document_local` NO apendiza `b7633e98`

### A.0 La lane SÍ dispara y el plan SÍ lleva `commissioning_setup` (las 2 primeras hipótesis, muertas)

`expand_query_facets(v5, multi_match=True)` sobre la query de cat017 («¿Cómo se cablea y se da de
alta (configura) un lazo en la central Notifier INSPIRE (E10/E15)?») devuelve
`archetypes = [connect_install_wire, commissioning_setup]` — el patrón `\b(?:da|...|dar\w*)\s+de\s+alta\b`
matchea «se **da de alta**». El plan real (`_build_document_local_query_plan_v5`) produce **4
need-groups**, y el de commissioning **sobrevive el trim** como grupo índice 3:

| grupo | términos (post-trim) | origen |
|---|---|---|
| 0 | terminales · polaridad · conexion · cableado | connect_install_wire |
| 1 | pantalla · tierra · continuidad · resistencia | connect_install_wire |
| 2 | limites · seguridad · comprobacion | connect_install_wire |
| **3** | **sitio · edificio · licencia** | **commissioning_setup** |

El trim (`MAX_TSQUERY_CHARS=480`, tsquery pre-trim 709 chars) le quita `portal` y `bin`, pero el
suelo `NEED_GROUP_GATE_FLOOR=3` lo deja **exactamente en 3 = `N_FACET`** → sigue siendo
gate-elegible. **`alta` no aparece en el grupo porque es token de la query (anchor).**

Y la RPC FTS **sí trae el portador**: `fts_candidate_rows = 39`, y `b7633e98` está entre ellos
(`A3_funnel.fetch.carrier_in_candidates = true`). **El portador llega vivo hasta la puerta.**

### A.1 Muerte nº1 — la lane PRINCIPAL: `best_candidate_already_covered`

Traza real de la lane (`A2_seam.lanes[1]`):

```
lane: document_local_content_coverage_v1
status: best_candidate_already_covered
fts_candidate_rows: 39   eligible_rows: 3
satisfied_ids: [79faef35]   satisfaction_route: already_served
```

`select_document_local_coverage` rankea los 39 candidatos con `select_rerank_pool_coverage` y
obtiene **`ranked = [79faef35, 3a2fc401]`**. El ganador `79faef35` **ya está en el top-10 servido**
(rank 5 del prefijo) ⇒ la lane devuelve `[]`.

> **Punto de muerte 1: `src/rag/document_local_coverage.py:1434-1440`** — `winner_id in covered_ids
> ⇒ return [], "best_candidate_already_covered"`. La lane mira **sólo `ranked[0]`** y, si ya está
> servido, se apaga; **nunca avanza al siguiente candidato no servido**.

**Pero éste NO es el lever para el portador**: `b7633e98` **no aparece en `ranked` en absoluto**
(`A3_funnel.ranker.carrier_rank = null`, `eligible_rows=3`, sólo 2 filas rankeadas). Arreglar el
«avanzar al siguiente» **no serviría el portador**. Es un hallazgo de diseño real, pero de otra clase.

### A.2 Muerte nº2 — la vía POR-FACETA: el portador es elegible, gana el gate… y muere de rank-2

La vía complementaria (`FACET_COMPLEMENT_BUDGET=1`, flag `DOCUMENT_LOCAL_SELECTION_V2` **ON** bajo
`coverage_c1_v4`) sí corre. Traza real: `status = facet_attestation_failed`,
`need_group_grades = [2, 3, 1, 1]`.

Funnel exacto, medido con las funciones reales sobre el estado real:

1. **Gate A7 PASA.** Grupos no cubiertos con ≥3 términos: `[0, 2, 3]`. El grupo 3
   (`sitio·edificio·licencia`) tiene **grade 1 < N_FACET=3** ⇒ **la cobertura de commissioning en la
   selección es CERO-casi y el gate dispara.**
2. **Orden de grupos** = `(grade asc, index asc)` → `[2, 3, 0]`.
3. **El portador ES elegible y queda asignado al grupo 3**: ventana `[0:360]`, **`terms_hit = 3`**,
   hits `[edificio, licencia, sitio]`. El bucket del grupo 2 está **vacío**, así que el grupo 3 es
   el primero con candidatos.
4. **Bucket del grupo 3, en su orden pre-registrado** `(-terms_hit, density asc, chunk_index, …)`:

   | # | id | terms_hit | density | chunk_index | pág |
   |---|---|---|---|---|---|
   | 1 | `f2a64128` | 3 | **45** | 61 | 66 |
   | 2 | **`b7633e98`** | 3 | **148** | 4 | **5** |

   **El portador pierde el desempate por DENSIDAD** (45 < 148) — la ventana de `f2a64128` mete los
   3 términos en menos caracteres.
5. `_facet_gate_and_select` devuelve **sólo `bucket[0]`** = `f2a64128`.
6. `_facet_complement_row(f2a64128)` → **`_attest` devuelve None**: la fila no deriva **ni** la clase
   `markdown_pipe_row_v1` (`markdown_record_cards = false`) **ni** la clase de prosa
   (`prose_source_cards_built = 0`), con `has_exact_coverage_receipt = true` y la identidad de
   autoridad correcta. Es decir: candidato **inservible por CLASE**.
7. `_append_facet_complement` marca `facet_attestation_failed` y **aborta la vía entera** — sin
   probar `bucket[1]`, sin pasar al siguiente grupo.

> **PUNTO EXACTO DE MUERTE (el que domina la decisión):**
> **`src/rag/post_rerank_coverage.py:1118-1129`** (`candidate, window = bucket[0]` + `return` — se
> devuelve **un único** candidato, no una lista) **combinado con
> `src/rag/post_rerank_coverage.py:1377-1382`** (`if attested is None or not
> _attest_facet_complement(...): status = "facet_attestation_failed"; return served, trace` — **un
> solo intento, sin fallback**).
> La clase del fallo de `f2a64128` es `src/rag/post_rerank_coverage.py:787`
> (`if not pipe_class and not document_local_prose_class: return None`).

### A.3 CONTRAFACTUAL — ¿bastaría iterar el bucket? **SÍ** (medido, no inferido)

Probando cada candidato del bucket en su orden pre-registrado con las MISMAS funciones
(`A4_facet_complement.counterfactual_iterate_bucket`):

| # | id | grupo | `_facet_complement_row` | `_attest_facet_complement` |
|---|---|---|---|---|
| 1 | `f2a64128` (p.66) | 3 | **falla** (`_attest`, clase de servido) | — |
| 2 | **`b7633e98` (p.5)** | 3 | **OK** | **True** |
| 3 | `a01755a8` (p.50) | 0 | OK | True |

**`b7633e98` construye y atesta perfectamente.** Su clase servida sería
`exact_source_bounded_prose_sentence_span_v1` y **el texto que vería el generador es el hecho
verbatim**:

> «# Comprobaciones preliminares — Antes de ir a la instalación: 01 En el portal en la nube de CLSS
> Gestión de Clientes, cree un sitio/edificio y añada una central. Cargue la configuración de la
> central con el programa de configuración de CLSS. **Generar archivo .bin de licencia de la
> central.**»

⇒ **La muerte es de ORDEN + BUG de fallback, no de presupuesto, ni de attestation del portador, ni
de diseño del gate.** El presupuesto (`FACET_COMPLEMENT_BUDGET=1`) **nunca se consume**; el gate A7
**sí** dispara; el portador **sí** atesta. Un único candidato tóxico-por-clase en el puesto 1 apaga
la vía entera.

---

## MISIÓN B — hp002

### B.1 El chunk-soporte del hecho de SEGURIDAD (hp002#4)

Dump completo del documento `ASD535_TD_T131192es_h`: **242 chunks** (1 sola extracción) — **no
~89-100 como asumía el encargo; se declara la corrección**. Adjudicación léxica local contra el
texto del hecho, primero por términos-núcleo (`extincion·mantenimiento·bloquear·desconectar`, los
que separan el gate de seguridad de los demás avisos del manual):

| id | ci | pág | núcleo | sección |
|---|---|---|---|---|
| **`5b6a3a19-a924-4cf4-9513-bd50786ee3d9`** | 215 | **121** | **4/4** | **9.3 Comprobaciones de mantenimiento y funcionamiento** |
| `f31ecbc9` | 176 | 103 | 2/4 | 7.7.2 Disparos de prueba |
| `66bff43f` | 47 | 32 | 2/4 | 2.2.17 Tipos de reset |
| `6d5a807f` | 174 | 102 | 2/4 | 7.7 Pruebas, revisiones y comprobaciones |

**ID: `5b6a3a19-a924-4cf4-9513-bd50786ee3d9` · página 121 · chunk_index 215.** Cita:

> «**Indicación** — Para evitar que los controles de incendios, las alertas remotas y las zonas de
> extinción se disparen al llevar a cabo los trabajos de mantenimiento, es **imprescindible**
> bloquearlos o desconectarlos previamente.
> Para las comprobaciones de mantenimiento y funcionamiento deberán llevarse a cabo las siguientes
> acciones: **1. Bloquear o desconectar el control de incendios y la alerta remota en la CDI de
> orden superior.** […]»

Corresponde término a término con el hecho (incluido «Indicación que **ENCABEZA** el checklist de
mantenimiento»). **Corroboración independiente:** el docstring de `src/rag/post_rerank_coverage.py:33-38`
(s278 §3, escrito antes y por otra sesión) nombra el fallo hp002:r1 como «el warning ASD535 **p121**
quedó en el pool #28 sin servir» — misma página. Y su `best_pool_rank` medido aquí (23 en la ventana
`pool_n=34`) coincide con el 23/21 del artefacto.

### B.2 ¿Lo atestan los need-groups EXISTENTES de `evidence_coverage_facets_v5.yaml`? — **NO. 0 de 26.**

Vara real: `post_rerank_coverage._facet_best_window` (ventana 360 chars, misma función que usa el
gate) con `N_FACET = 3`. Tabla grupo × `terms_hit` sobre el contenido del singleton (los 9
arquetipos, 26 grupos; extracto ordenado):

| arquetipo/grupo | nº términos | `terms_hit` | hits |
|---|---|---|---|
| intrinsic_safety/entity_parameters | 13 | 2 | entrada, tension |
| intrinsic_safety/terminals_control | 7 | 2 | conexion, control |
| replace_without_loss/main_power | 10 | 2 | alimentacion, tension |
| replace_without_loss/redundant_power | 11 | 2 | alimentacion, tension |
| capacity_quantity/per_unit_capacity | 11 | 1 | detector |
| connect_install_wire/connection | 8 | 1 | conexion |
| intrinsic_safety/power_path | 12 | 1 | alimentacion |
| loop_eol_topology/loop_topology | 10 | 1 | salida |
| program_delay_cause_effect/logic_structure | 14 | 1 | entrada |
| program_delay_cause_effect/output_action | 21 | 1 | salida |
| compatibility/compatibility_scope | 8 | 1 | protocolo |
| **fault_reset_recovery/state_blockers** | 13 | **0** | — |
| **fault_reset_recovery/verification_recovery** | 11 | **0** | — |
| fault_reset_recovery/timing_state | 15 | 0 | — |
| connect_install_wire/continuity · limits_safety | 12 · 12 | 0 · 0 | — |
| loop_eol_topology/termination · wiring_continuity | 8 · 6 | 0 · 0 | — |
| battery_sizing/* · capacity_quantity/system_total · variant_reconciliation | — | 0 | — |
| compatibility/installation_requirements · program_delay/navigation | — | 0 | — |
| replace_without_loss/component_identity · persistence | — | 0 | — |

**`n_groups_attesting (≥N_FACET=3) = 0`.**

> **F7 del sub-agente queda REFUTADO por medición.** `state_blockers`
> [condicion, activa, enclavada, inhibicion, bloqueo, abort, …, manual, reset] y
> `verification_recovery` [diagnostico, comprobacion, recuperacion, normal, reposo, averia, …]
> **no son candidatos vivos: puntúan 0, no 3.**
> **Mecanismo:** `_facet_best_window` → `_tokens` hace match **EXACTO de token** (regex
> `[a-z0-9]+` sobre texto plegado; `_facet_min_span` usa `(?<![a-z0-9])term(?![a-z0-9])`),
> **sin stemming**. El config lleva los lemas (`bloqueo`, `comprobacion`, `diagnostico`) y el chunk
> lleva las formas flexionadas (**«bloquearlos»**, **«Comprobaciones»**, «desconectarlos») ⇒ cero
> intersección. El gap ES-flexión ≠ lema es el mecanismo, no el vocabulario.

Ni siquiera con la vara laxa del propio config (`min_distinct_terms: 2`) hay salida honesta: los
únicos grupos que llegan a 2 lo hacen con `[entrada, tension]` / `[alimentacion, tension]` /
`[conexion, control]` — hits del bloque de **medición de tensión** del checklist, **no del gate de
seguridad**. Servir por ahí sería atestar el contenido equivocado.

### B.3 Funnel de `obligation_warning_reserve_v1`: el singleton **era candidato** y **perdió por ORDEN**

La reserva **sí** aplica (`is_procedural_diagnostic_query = True`; la query lleva «se diagnostica» y
«causa más probable»). El singleton **pasa TODOS los gates de la lane**:

- scope: `source_file = ASD535_TD_T131192es_h`, **en los scopes servidos** ✔
- no servido ✔ · no TOC ✔ · **`_warning_span` presente**: `[76:290]`, trigger `imprescindible`,
  quote = *exactamente* la «Indicación» del hecho ✔
- `singleton_pool_entry`: `{pool_rank: 23, eligible: true, skip_reasons: []}` ✔

**Y aun así pierde**, porque el selector **no rankea nada**: es un **primer-match por orden de pool**
con presupuesto 1.

> **Punto de muerte: `src/rag/rerank_pool_coverage.py:535-585`** —
> `for pool_rank, source_row in enumerate(retrieval_pool[:POOL_LIMIT])` … el primer chunk que pase
> los filtros hace `return [enriched], trace`. **No hay puntuación, ni de faceta, ni de fuerza de
> obligación, ni de sección.**

Camino del pool medido (`reserve_pool_walk`, ventana `pool_n=33`): **11 filas elegibles** en los
ranks `[2, 5, 10, 11, 12, 14, 16, 17, 18, 19, 22]`. El singleton es **la ÚLTIMA (11ª) de las 11**.
La ganadora es la del rank 2:

| | id | pág | sección | «warning» que la hace elegible |
|---|---|---|---|---|
| ganadora | `339f06e0` | 7 | **Historia del documento** | `\| • 9.4.3 \| c \| **Advertencia** insertada antes del texto y adaptación del texto (daños en el elemento sensor) \| Rectificación \|` |
| singleton | `5b6a3a19` | 121 | 9.3 Comprobaciones de mantenimiento | «…es **imprescindible** bloquearlos o desconectarlos previamente.» |

**La ganadora es una fila de tabla del CHANGELOG del documento que sólo contiene la palabra
«Advertencia».** Es un falso positivo del léxico MANDATORY sobre la historia de revisiones — el
filtro `is_toc_page` no cubre esa clase. Consume el presupuesto de 1 y expulsa el aviso real.

⇒ **Ni gate, ni presupuesto conceptual, ni contenido: ORDEN puro.** No hace falta vocabulario nuevo
de ninguna clase para que el singleton gane.

---

## VEREDICTO DE RUTA

| # | pregunta | veredicto | anclaje |
|---|---|---|---|
| **(a)** | ¿existe lever barato en puerta EXISTENTE? | **SÍ — dos, independientes, ambos de ORDEN/BUG y sin vocabulario nuevo.** **A)** cat017: `_facet_gate_and_select` devuelve **sólo `bucket[0]`** y `_append_facet_complement` **aborta la vía en el primer fallo de attestation** ⇒ un candidato inservible-por-clase (`f2a64128`) apaga la puerta con el portador **atestable** en el puesto 2 del MISMO bucket. Fix: iterar bucket→grupos hasta que uno atestigüe, manteniendo q=1. **B)** hp002: la reserva es **primer-match por rank de pool sin ninguna puntuación**; 11 elegibles, se lleva el presupuesto una fila del **changelog** («Advertencia insertada…») y el aviso real queda 11º. Fix: un orden determinista (o excluir clase changelog/historia como ya se excluye TOC). | `post_rerank_coverage.py:1118-1129` + `:1377-1382` (+ clase: `:787`) · `rerank_pool_coverage.py:535-585` · `document_local_coverage.py:1434-1440` (3ª puerta, distinta clase, no sirve al portador) |
| **(b)** | ¿hp002 servible vía grupos EXISTENTES sin autoría? | **NO por grupos — SÍ por la reserva.** Los 26 need-groups de `evidence_coverage_facets_v5.yaml` dan **0/26** a `N_FACET=3` sobre la ventana del singleton (**F7 refutado**): el matcher es token-exacto sin stemming y el config lleva lemas (`bloqueo`/`comprobacion`) frente a las flexiones del chunk (`bloquearlos`/`Comprobaciones`). **Pero hp002 no necesita grupos**: ya es candidato pleno de `obligation_warning_reserve` y sólo pierde por orden ⇒ **servible sin autoría alguna**, por la puerta que ya lo alcanza. | B.2 tabla · B.3 `singleton_pool_entry = {rank 23, eligible: true, skip_reasons: []}` |
| **(c)** | ¿la cuota honesta queda forcluida o viva? | **MOOT para las dos dianas — y por tanto el re-spec content-keyed NO se justifica por ellas.** Ninguna de las dos necesita vocabulario nuevo. Matiz honesto en los dos sentidos: (1) **F2-Sol/dúo queda parcialmente refutado** — el doble-bind «la selección ya contiene sub-intención-2 ⇒ la cuota no dispara» es **empíricamente falso** con el vocabulario shippeado: `grade = 1 < 3` y el gate **sí** dispara; (2) **pero eso NO vindica la cuota honesta**, porque `commissioning_setup` está contaminado por construcción (sus términos `sitio/edificio/licencia/bin/portal` son la superficie literal del chunk-respuesta, A2 del brief v1). Un vocabulario ciego no tiene garantía de reproducir ese disparo — y B.2 muestra **la barrera real que se llevaría por delante**: sin stemming, cualquier vocabulario honesto en lemas falla contra corpus flexionado. ⇒ **la cuota queda VIVA pero DESPRIORIZADA y sin caso de negocio en estas 2 queries**; si alguna vez se retoma, su gate previo ya no es el vocabulario sino el **stemming del matcher**. | `A4.gate_A7.grades = [2,3,1,1]` · `retrieval_facets_v5_document_local.yaml:102-113` · B.2 mecanismo |

### Lo que este diagnóstico NO cierra (declarado de entrada)

1. **Radio no medido.** Ambos fixes tocan lanes que disparan fuera de la clase
   (`obligation_warning_reserve` toca **18/39** golds según el censo A6). El sweep-39 de composición
   (G3) sigue siendo **obligatorio** antes de cualquier cableado; nada de esto lo sustituye.
2. **Conversión ≠ servido.** Se ha medido que el portador **se serviría** con el texto del hecho
   verbatim; que eso **convierta** `conveyed` es cuestión de generación (gate G5 pareado), no de
   este probe. No se afirma conversión.
3. **`339f06e0` es una fila OK-portadora hoy** (apendizada en ambas reps HEAD). Desplazarla exige
   verificación **por-fila** de la cohorte protegida (riesgo 2 del re-spec, S273/DEC-132b) — no por
   conteo.
4. **La 3ª puerta (`best_candidate_already_covered`, `document_local_coverage.py:1434-1440`) queda
   diagnosticada pero SIN lever propuesto**: su fix no serviría al portador (no está en `ranked`).
   Se anota para la traza, no se propone.
5. **`f2a64128` (p.66) es inservible por ambas clases de servido** con receipt y autoridad válidos.
   Es una clase de fallo propia (chunk que ninguna clase puede servir) que hoy sólo se ve como
   `facet_attestation_failed`; merece traza propia si el fix se cablea.
