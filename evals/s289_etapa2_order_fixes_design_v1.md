# s289 — DISEÑO de los 2 fixes quirúrgicos de etapa 2 (orden/fallback en lanes existentes)

**v1.1 — reconciliado tras dúo r3** (Sol 5 hallazgos [1 crítico] + sub-agente Fable 8; ambos
GO-con-cambios; 0 FP; tally en `evals/adversarial_review_log.jsonl` ts=2026-08-01T00:06:06;
resoluciones en §Reconciliación al final).

Estado: **DISEÑO, nada cableado.** Ejecuta la parte (b) del «Al retomar» de s288c (DEC-167):
los 2 head de etapa 2 = {cat017#4, hp002#4} mueren por ORDEN/FALLBACK en lanes existentes, no
por vocabulario ni por presupuesto. La parte (c) de DEC-167 (observabilidad salud/fail-open por
canal) es pieza SEPARADA del mismo arco — este diseño no la cubre (la traza nueva de ambos
fixes es insumo, no sustituto). Base = `evals/s288c_gate_diagnosis_v1.md` (funnel byte-exacto,
$0) + audit s289 fresco sobre los competidores reales de hp002 (§B.1) + **censo corpus
`evals/s289_warning_census_v1.json`** (población = unión de `pool_by_source_file` de los 39
pools del sweep s287 = 284 documentos).

## Declaración de métrica (Protocolo 2.5 — lever YA medido en zona)

- **Objetivo de HOY**: convertir el servido de {cat017#4, hp002#4} — métrica = **per-fact
  conveyed** bajo el instrumento v3.1 (mapa re-anclado, N=2), gateado por **sweep-39 de
  composición** (no-regresión) + **verificación por-fila** de la cohorte protegida.
- **Settled citados y su métrica** (no colisionan):
  - **DEC-167 (cuota-por-faceta CERRADA como familia)** — métrica: diseño de cuota
    content-keyed; cerrada por contaminación de autoría + probe serve-rate 0/6. **Esto NO es
    una cuota**: no hay vocabulario nuevo, no hay presupuesto nuevo, no hay gate nuevo. Son
    fixes de orden/fallback DENTRO de puertas ya shippeadas, con presupuestos intactos.
  - **DEC-158 «techo» VACATED en su letra (DEC-164)** — no aplica como bloqueo.
  - **DEC-132b / S273 riesgo-2 (cohorte protegida)** — misma métrica que usamos: por-fila, no
    por conteo. Se cumple en G-2.

---

## FIX A — cat017#4: fallback de attestation en la vía por-faceta (`post_rerank_coverage.py`)

### Mecanismo del fallo (medido, s288c §A.2-A.3)
`_facet_gate_and_select` (:1065-1130) devuelve **solo `bucket[0]`** del primer grupo no vacío;
`_append_facet_complement` (:1370-1382) hace **un único intento** de attestation y aborta la vía
entera en fallo. Un candidato inservible-por-clase (`f2a64128`, p.66: ni pipe-row ni prosa
derivable, `:787`) apaga la puerta con el portador **atestable** (`b7633e98`, p.5) en el puesto
2 del MISMO bucket. Contrafactual A.3 **medido**: iterando el bucket, `b7633e98` construye y
atesta True; `a01755a8` (grupo 0) también.

### Diseño
1. **Función NUEVA `_facet_gate_and_select_all`** con la lógica actual pero devolviendo la
   **lista ordenada completa de selecciones** en el orden pre-registrado TOTAL ya existente
   (grupos por `(grade asc, index asc)`; dentro del grupo `(-terms_hit, density asc,
   chunk_index, source_file, id)`; candidato multi-grupo asignado al primer grupo elegible —
   TODO idéntico, cero libertad nueva). **`_facet_gate_and_select` PRESERVA SU FIRMA** y
   delega (devuelve la primera selección) — la firma actual está pineada por call-sites en
   `tests/test_s279_facet_complement.py`, `scripts/s288c_gate_funnel_probe.py` (el REPRODUCTOR
   del recibo de DEC-167) y `scripts/s279_selection_census.py`; romperla rompe la cadena de
   evidencia re-ejecutable (dúo r3, A4).
2. `_append_facet_complement` bajo flag ON itera la lista de `_all`: por cada selección intenta
   `_facet_complement_row` + `_attest_facet_complement`; **la primera que atesta se sirve** y
   se corta. Con flag OFF itera solo el primer elemento = byte-idéntico a hoy. Presupuesto
   **intacto** (`FACET_COMPLEMENT_BUDGET=1`: a lo sumo UNA fila anexada; lo que cambia es
   cuántos CANDIDATOS se prueban antes de rendirse, acotado por el pool FTS ya fetcheado,
   ≤ ~40 filas, todo CPU local, 0 RPC extra). Invariantes de attestation verificados para
   bucket[1..n] por el dúo (served no muta durante la iteración; `served_view_sha256` se
   estampa y re-verifica contra el MISMO served pre-append; bounds re-derivados deterministas).
3. **Traza nueva** `facet_attempts: [{id, group_index, outcome}]` — da visibilidad propia a la
   clase «chunk inservible por ambas clases de servido» (punto 5 del diagnóstico: hoy solo se
   ve como `facet_attestation_failed` agregado).
4. Status final si nadie atesta: `facet_attestation_failed` se mantiene (compat con
   consumidores de traza); los intentos quedan en `facet_attempts`.

### Flag
`FACET_COMPLEMENT_FALLBACK` (`_strict_on_off`, default **off**). Off = byte-idéntico al
comportamiento actual (se intenta solo la primera selección). Clasificación release_config por
el patrón s286 (allowlist, NO ampliar la tupla sellada de `PROFILE_OWNED_FLAGS` — rompe 89 pins).

### Alternativas descartadas
- **Arreglar solo `best_candidate_already_covered`** (`document_local_coverage.py:1434-1440`,
  la 3ª puerta): NO sirve al portador — `b7633e98` no está en `ranked` de esa lane (A.1). Queda
  anotada, sin lever (igual que en el diagnóstico).
- **Filtrar candidatos inservibles-por-clase ANTES del sort** (pre-attest en el gate): attesta
  2 veces cada candidato (una en el filtro, otra en la fila real) o exige refactor del attest a
  dry-run; el fallback post-fallo da el mismo resultado con menos superficie.
- **Cap de intentos** (`MAX_ATTEMPTS=k`): número mágico sin caso medido; el pool ya acota. Si
  la observabilidad (tarea 5) muestra colas largas, se añade con dato.

---

## FIX B — hp002#4: orden determinista + filtros de clase en la reserva
(`rerank_pool_coverage.py::select_obligation_warning_reserve`, :535-585)

### Mecanismo del fallo (medido, s288c §B.3 + audit s289 §B.1)
La reserva es **primer-match por rank de pool** con presupuesto 1, sin puntuación alguna.
Audit fresco s289 (funciones reales `_warning_span` sobre los 7 elegibles de la ventana del
recibo, DB live):

| rank | pág | sección | span ganador | clase |
|---|---|---|---|---|
| 2 | 7 | Historia del documento | fila de tabla «Advertencia insertada…» (192 ch) | **FP-tabla/changelog** |
| 5 | 17 | 1.1 Función | «…información imprescindible para garantizar el correcto funcionamiento» (119 ch) | **FP-prosa incidental** |
| 10 | 5 | Indicaciones de seguridad | «## Peligro — Si no se observan las advertencias…» (271 ch) | aviso genérico meta |
| 11 | 20 | Aspectos generales | `> **Peligro**` (**13 ch**) | **FP-marcador huérfano** |
| 12 | 21 | 1.6 Hardware/Firmware | `> **Peligro**` (13 ch) | FP-marcador huérfano |
| 19 | 27 | 2.2.8 Entradas | `> **Advertencia**` (17 ch) | FP-marcador huérfano |
| 22 | 121 | 9.3 Comprobaciones de mantenimiento | `> Para evitar que… es **imprescindible** bloquearlos…` (214 ch) | **EL AVISO REAL** |

Hallazgo NUEVO del audit: la clase dominante de FP no es solo el changelog — son los
**spans huérfanos** (el marcador del callout separado de su cuerpo porque el cuerpo no lleva
término-gatillo: la agrupación solo mergea oraciones CON gatillo). Servir `> **Peligro**` al
generador = quote de 13 chars con CERO información.

### Diseño (2 filtros de clase + 1 orden, todos content-derived, cero vocabulario nuevo)

1. **Filtros POR-GRUPO dentro de `_warning_span`** (dúo r3, A3 — NO per-chunk tras el return):
   `_warning_span` gana un parámetro `filtered=False` (el caller lo pasa True solo bajo flag →
   off-path byte-idéntico). En el bucle de grupos ya existente (que ya hace `continue` en
   grupos sobredimensionados, :487-489), un grupo filtrado hace `continue` al SIGUIENTE grupo
   del mismo chunk — el primer-grupo-FP ya no entierra un callout real más abajo del chunk.
   (`_mandatory_callout_card` es implementación SEPARADA en `post_rerank_coverage.py:590` —
   cero acoplamiento, verificado.)
   - **Filtro grupo-en-tabla**: descarta el grupo si TODAS sus líneas no vacías, tras plegar
     prefijos blockquote (`>` iniciales — tablas dentro de blockquote), empiezan por `|`. Un
     callout de seguridad no es fila de tabla en el censo (0 contraejemplos en 284 docs); mata
     la clase changelog/historial corpus-wide **sin lista de secciones**.
   - **Filtro grupo-sin-contenido-residual**: pliega el grupo (`_fold`), retira los gatillos
     presentes — **frases multi-palabra como substring; términos-token con boundary
     `(?<![a-z0-9])term(?![a-z0-9])`; compuestos (`debe(n)+antes de`, `must+before`) por sus
     componentes (`\bdebe(n)?\b`, `antes de`, `\bmust\b`, `\bbefore\b`)** — y todo
     no-alfanumérico; si no queda nada ⇒ descarta (marcador huérfano). **Sin número mágico.**
2. **Orden determinista** sobre los supervivientes (en vez de first-match): el selector
   recolecta TODOS los elegibles del pool — **coste nuevo declarado: escanea el pool entero
   siempre que la lane aplica (hoy corta en el primer match); CPU local puro, cota
   `POOL_LIMIT=64`** — y ordena por `(callout_blockquote desc, pool_rank asc)` donde
   `callout_blockquote` = todas las líneas no vacías del span son blockquote (`>`). Si ningún
   elegible es blockquote ⇒ degrada a pool-rank = comportamiento actual (fail-open preservado).
3. **Traza simétrica de descartes** (dúo r3, A8): `reserve_discards: [{pool_rank, id, filtro}]`
   + `reserve_ranked_ids` en la traza de la lane — G-1 necesita atribuir cada cambio de fila en
   los 18/39 golds que la reserva toca.

**ESCALADA v2 EJECUTADA (post G-1, trigger preservado en
`evals/s289_g1_sweep39_result_orderv1_trigger.json`):** el arms orden-v1 mostró la
materialización EXACTA del riesgo 4: en la ventana capturada de hp002 (`pool_n=34`), el callout
`fa55311c` (p.78, sección «Instalación» — aviso real pero AJENO al procedimiento preguntado)
ganaba por pool-rank (20<23) al aviso de la sección procedimental (`5b6a3a19`, p.121). Orden v2
= la escalada pre-declarada abajo: clave `(sección-con-intención-procedimental desc,
blockquote desc, pool_rank asc)` donde el match de sección usa el MISMO léxico
`_OBLIGATION_INTENT` que dispara la lane (cero vocabulario nuevo) sobre `section_title`
foldeado. Es además la letra de DEC-167(b)(ii) («selección PUNTUADA»). Fail-open intacto: sin
señal alguna → pool-rank = first-match actual. Medido en la ventana: solo `5b6a3a19` matchea
sección → v2 lo sirve.

**Estatus epistémico del criterio blockquote-first (dúo r3, S4/A5 + lección #56):** es
heurística anticipatoria no-eval-driven, elegida CON el ganador de hp002 a la vista — misma
clase que la alternativa section-intent descartada; la simetría se declara. Lo que la separa:
el **CENSO** (`s289_warning_census_v1.json`, 284 docs, 2.216 spans): la clase blockquote (200)
es avisos reales de seguridad en el eyeball (Caution/ATENCIÓN/PRECAUCIÓN/NUNCA/imprescindible…;
1 caso-borde anotación-de-imagen declarado); las clases que los filtros matan (tabla 217 +
huérfano 220) son ~20% de la masa total de spans y FP por construcción; en 64/284 docs
conviven blockquote y prosa (la prioridad DECIDE); avisos reales en formato heading
(`## Peligro`, p.5 ASD535) EXISTEN y pierden contra blockquote solo cuando ambos compiten —
limitación declarada, gateada por G-1+G-3 (el fallo iría a per-fact, no silencioso).

Con filtros+orden sobre los datos medidos de hp002: elegibles post-filtros = {p.5
prosa-genérica, p.17 prosa, **p.121 callout**} → gana **p.121, el aviso real**. (Nota honesta:
el audit §B.1 se computó con la semántica primer-grupo; con filtros por-grupo un chunk hoy
clasificado tabla/huérfano puede aportar un grupo limpio posterior — el sweep G-1 mide el
estado real, no esta tabla.) Presupuesto (1), scope (source_file servido), trigger de
intención y léxico MANDATORY: **intactos**.

### Flag
`OBLIGATION_RESERVE_ORDERED` (`_strict_on_off`, default **off**). Off = first-match actual
byte-idéntico. Misma clasificación release_config que Fix A. Flags SEPARADOS (rollback y
atribución independientes en los gates).

### Contrato de flags con el instrumento (dúo r3, S3+A2 — clase de bug s286e reincidente)
Ambos flags son flags-hoja del MISMO seam que el bloque s286e de
`scripts/factlevel_assessment.py:104-120` pinea precisamente porque «un .env sucio mediría OTRA
stack bajo la etiqueta demo». Obligatorio en el build:
1. Añadir `FACET_COMPLEMENT_FALLBACK: "off"` y `OBLIGATION_RESERVE_ORDERED: "off"` a
   `DEMO_FLAGS` (pineado off = ship actual).
2. El runner de gates pone ON **vía override DECLARADO post-`_assert_demo_flags`** y el
   manifest/freeze-hash de cada brazo **estampa el flag-set efectivo** — OFF y ON no pueden
   compartir freeze-hash (el tratamiento es parte del contrato del recibo).
3. `validate_release_contract`: verificar que admite ambos flags off junto a `coverage_c1_v4`
   (los flags NO entran en `PROFILE_OWNED_FLAGS` — la tupla sellada no se toca; verificado por
   el dúo: el validador solo rechaza overrides de flags profile-owned).

### Alternativas descartadas
- **Solo excluir changelog/historial** (la opción (o) del veredicto (a) del diagnóstico):
  INSUFICIENTE — medido: quedan 5 FPs por delante del singleton (prosa incidental + huérfanos
  + genérico p.5). El diagnóstico no había mirado los competidores; el audit s289 sí.
- **Puntuación por alineación query↔faceta**: anti-diseño — la lane EXISTE porque esa
  alineación es el punto ciego medido de hp002:r1 (comentario :563-566 del propio código).
- **Alineación section_title↔intención procedimental** (preferir el aviso cuya sección matchea
  `_OBLIGATION_INTENT`): discrimina p.121 únicamente, PERO es la opción con sabor a autoría
  dirigida (la lección #56 de DEC-167: diseñar el criterio mirando al ganador conocido).
  Se declara como **v2 de escalada** si el gate dirigido N=2 muestra inestabilidad
  entre-ventanas, no como v1.
- **Extender `_warning_span` para MERGEAR el cuerpo sin-gatillo del callout** (arreglar el
  huérfano «hacia dentro»): cambiar la regla de MERGE sí es radio mayor (otra semántica de
  agrupación) y sigue descartado. El dúo r3 (A3) separó correctamente ese descarte del
  SALTO de grupos filtrados, que es local y va en el diseño (punto 1). Un chunk cuyo único
  grupo es el marcador huérfano queda inelegible (mejor saltar que servir quote degenerado);
  limitación anotada.

---

## Gaps / riesgos declarados (de entrada)

1. **Radio no medido**: la reserva toca **18/39** golds (censo A6); la vía por-faceta corre
   bajo `coverage_c1_v4` en composición. → **G-1 sweep-39 obligatorio** (ambos flags on vs
   HEAD, no-regresión de composición por gold).
2. **`339f06e0` (changelog) es fila OK-portadora HOY en hp002 HEAD (ambas reps)**. Fix B la
   desplaza. → **G-2 verificación POR-FILA de la cohorte protegida** (qué facts pierden su
   soporte y si re-aparece por otra vía), riesgo-2 del re-spec S273/DEC-132b. No por conteo.
3. **Conversión ≠ servido**: que el portador servido convierta `conveyed` es de generación. →
   **G-3 gate dirigido pareado** (~$2-4, N=2) sobre {cat017, hp002}.
4. **Ventana-dependencia residual (Fix B)**: el pool es VENTANA-DEPENDIENTE (bandas medidas
   s288c); en otra ventana puede haber OTRO callout-con-contenido por delante de p.121 en
   pool-rank (los ranks 14/16/17/18 de la ventana de 11 elegibles no están caracterizados).
   El orden v1 no lo pina; G-3 con N=2 lo mide; escalada declarada = section-intent v2.
5. **Fix A no re-ordena**: si `bucket[0]` atesta, sirve exactamente lo de hoy — el fix solo
   añade fallback. Ninguna fila hoy-servida cambia con A on (la vía hoy o sirve bucket[0] o
   nada). El riesgo de A es AÑADIR filas donde hoy no había — G-1 lo hace **VISIBLE** (lista
   de golds que ganan fila) y **G-3 lo MIDE per-fact en cada uno de esos golds** (dúo r3,
   S2+A1: una fila extra puede degradar conveyed por distracción del generador; el diff de
   composición NO es no-regresión en la métrica declarada).
6. **Coste CPU extra acotado, no medido**: Fix A attesta hasta ~40 candidatos en el peor caso
   (hoy 1); Fix B corre `_warning_span` sobre el pool entero SIEMPRE que la lane aplica (hoy
   corta en el primer match). Ambos CPU-local sin RPC/LLM; se estampa en traza para la pieza
   de observabilidad (tarea 5).

## Por qué BP + estructural + escalable
- **Raíz, no parche**: ambos fixes eliminan la clase del fallo (abort-on-first-failure;
  first-match-sin-orden), no el síntoma del gold. Cero vocabulario nuevo, cero números mágicos
  (el único umbral nuevo es «contenido residual > 0»).
- **Señales content-derived** (tabla, blockquote, contenido residual) = invariantes del
  extractor, no del fabricante → escalan a 30+ marcas sin curación.
- **Presupuestos y contratos intactos**: q=1 en ambas lanes; attestation fail-closed intacta;
  fail-open de la reserva intacto.
- **Flags default-off byte-invariantes** + gates pre-registrados antes de cualquier ON.

## Plan de verificación (pre-registrado; re-diseñado por el crítico S1 del dúo r3)

**Principio (S1, CRÍTICO):** con la ventana-dependencia del pool documentada (bandas s288c),
comparar flags-on vs HEAD end-to-end NO atribuye el delta. Todos los brazos corren sobre los
**MISMOS pools serializados**: el harness captura el pool de retrieval UNA vez por gold
(chunks completos, no resúmenes — los pools del recibo s287 son conteos, no sirven de replay),
lo congela en el recibo, y ejecuta la composición determinista por brazo sobre esa captura.
Patrón s287/DEC-096b: brazo OFF + brazo ON + **réplica OFF-vs-OFF como control de ruido** (debe
dar diff vacío — si no, el harness está roto, no el fix).

- **G-0** suite completa verde con flags off + tests de byte-invariancia (off-path idéntico:
  firma preservada de `_facet_gate_and_select`, `_warning_span(filtered=False)` default).
- **G-1** sweep-39 de composición determinista ($0 LLM) sobre pools capturados: 3 brazos
  (OFF / ON / réplica-OFF). Salida = **LISTA de golds cuya vista servida cambia** (diff por
  fila con atribución por lane vía `reserve_discards`/`facet_attempts`). Esperado: {hp002:
  339f06e0→5b6a3a19} + cat017: +b7633e98 + N adiciones facet-complement. Réplica-OFF con
  diff no-vacío = STOP (harness). Pérdida de fila NO-prevista = STOP (diseño).
- **G-2** por-fila 339f06e0 (cohorte protegida, S273/DEC-132b): pre-audit s289 YA medido —
  en ambas reps HEAD ningún fact de hp002 la cita como soporte y la respuesta no extrae nada
  de ella (menciones changelog en answer: 0/4 probes). Verificación formal = sus facts en G-3.
- **G-3** dirigido pareado per-fact sobre **TODOS los golds de la lista de G-1** (no solo
  {cat017, hp002} — S2/A1), N=2 por brazo, generación temp=0 sobre la composición de cada
  brazo del MISMO pool capturado: cat017#4 y hp002#4 conveyed = éxito; TODO fact hoy-OK de
  CUALQUIER gold listado sin degradar = no-regresión. Coste escala con |lista G-1| (~$2-4 si
  la lista es {cat017, hp002} + pocas adiciones; se re-estima al ver G-1 y se declara antes
  de correr).

---

## Reconciliación dúo r3 (v1 → v1.1)

Dúo: cross-model GPT-5.6 Sol (xhigh, 60 tool-calls, repo-read) + sub-agente Fable 5 fresco.
Veredicto AMBOS: **GO-con-cambios**. Convergencia independiente en 2 hallazgos (S3=A2 flags;
S2=A1 per-fact). Regla C aplicada: claims de código verificadas contra fuente antes de actuar.

| # | hallazgo | sev | resolución en v1.1 |
|---|---|---|---|
| S1 | A/B sin congelar pools no atribuye (ventana-dependencia) | CRÍTICO | Plan de gates re-diseñado: pools capturados + 3 brazos + réplica-OFF (patrón DEC-096b) |
| S2=A1 | adiciones fuera de {cat017,hp002} solo VISIBLES, no medidas («cubierto» sobre-afirmaba) | MEDIO | G-3 se extiende a TODOS los golds de la lista G-1; gap 5 re-redactado |
| S3=A2 | flags nuevos fuera de DEMO_FLAGS/freeze del instrumento (clase s286e reincidente) | MEDIO | Sección nueva «Contrato de flags con el instrumento»: pin off + override declarado + freeze-hash estampa tratamiento |
| S4 | prioridad-formato generalizada desde 1 manual, sin censo | MEDIO | CENSO ejecutado (`s289_warning_census_v1.json`, 284 docs/2.216 spans): blockquote=avisos reales (eyeball), filtros matan ~20% masa FP; heading-warnings declarados como limitación gateada |
| S5 | «ejecuta el Al retomar» sobre-afirmaba alcance vs DEC-167(c) | MENOR | Cabecera re-redactada: parte (b); observabilidad = pieza separada |
| A3 | filtros per-chunk pierden callouts reales tras un primer-grupo-FP | MEDIO | Filtros movidos POR-GRUPO dentro de `_warning_span` (param `filtered`, off-path idéntico); nota de honestidad sobre el audit §B.1 |
| A4 | cambiar la firma de `_facet_gate_and_select` rompe 4 ficheros pineados (incl. probe reproductor DEC-167) | MEDIO | `_facet_gate_and_select_all` nueva; la existente delega y PRESERVA firma |
| A5 | universales no medidos + asimetría lección #56 (blockquote-first también se eligió mirando al ganador) | MEDIO | Bloque «Estatus epistémico» explícito: heurística anticipatoria censada, simetría declarada |
| A6 | retirada de gatillos infra-especificada (frases multi-palabra, compuestos) + tabla dentro de blockquote | BAJA-MEDIA | Especificado: fold → frases substring → tokens boundary → compuestos por componentes; fold de `>` antes del check `\|` |
| A7 | prosa contradictoria sobre el coste del scan | BAJA | Punto 2 del diseño declara el coste nuevo (el gap 6 era el honesto) |
| A8 | asimetría de traza (reserva sin descartes) | BAJA | `reserve_discards` + `reserve_ranked_ids` añadidos |

**Sostiene el dúo (verificado, sin cambio):** invariantes de attestation bajo iteración;
no-colisión con revalidación downstream de la reserva (`_attest` + content-exacto, no re-deriva
`_warning_span`); flags fuera de `PROFILE_OWNED_FLAGS` correcto (89 pins intactos);
no-colisión con DEC-167 (esto no es cuota: cero vocabulario/presupuesto/gate nuevo);
alternativas descartadas de Fix A honestas.
