# S274 — Diseño consolidado Bloques C/D (síntesis): serving-view + binding + composites

**Estado:** DISEÑO + PREREG, nada construido (contrato de sesión: diagnóstico $0 + diseño;
el dúo revisa ANTES del build — Protocolo 3, zona de dolor retrieval/síntesis ⇒ dúo
INNEGOCIABLE). Prereg ejecutable: `evals/s274_bloquesCD_prereg_v1.yaml`.

**Objetivo declarado (DEC-125/131):** foto oficial 145/154 → 151/154 (98%) = **+6**.
Candidatos (los 7 synth restantes, mapa causal DEC-127/131): `obl_0d6a` (serving-view) ·
`obl_2f5d` (uncited) · `obl_7bba` (binding 1-token) · `obl_a5d9`/`obl_015f`/`obl_b2043`/
`obl_7aa7` (composites). No hacen falta los 7: +6 de 7.

---

## 0. Diagnósticos de esta sesión (insumo medido, artefactos committeados)

### 0.1 C1 — obl_0d6a (hp017 F12): la vista servida trunca el bloque-warning — CONFIRMADO

Artefacto: `evals/s274_serving_view_diag_v1.json` ($0, `scripts/s274_serving_view_diag.py`);
verdict `all_pass: true`.

- **Dónde trunca (código):** `src/rag/post_rerank_coverage.py::coverage_context_content`
  (l.161-192). Para un chunk de lane validada sirve SOLO los spans de sus
  `coverage_cards` mergeados. F12 (chunk `d27b1a1b`, lane
  `same_blob_structural_neighbor_coverage_v1`, p41) tiene cards `[419,673]+[675,1032]+
  [1694,2052]` → vista servida 1.037 chars de 2.864 crudos. **NO existe cap de chars que
  "subir": es SELECCIÓN DE SPANS.** (`MAX_EXPANDED_EXCERPT_CHARS=1800` solo acota la
  expansión de filas de tabla, no la vista.)
- **Defecto o diseño:** DISEÑO, no bug. Introducido en s110 (commit `75720fc`) y
  reconciliado en s111 (`23cfa27`, "reconcile served evidence boundaries"); rationale en
  el docstring: acotar coste de tokens + impedir que "la cola no relacionada del mismo
  chunk" influya en la respuesta. El punto ciego ESTRUCTURAL: las cards del selector se
  alinean a facetas de la QUERY — un callout de seguridad adyacente al procedimiento
  jamás es faceta de query ⇒ la clase `mandatory_safety_omission` (s243) queda
  sistemáticamente fuera de la vista en chunks de coverage.
- **La vista completa SÍ contendría el bloque** (verificado freeze s113): warnings en
  offsets 2479-2555 («evite las lógicas contradictorias») y 2558-2724 («Es de vital
  importancia probar rigurosamente…»), fuera de toda card. `detect_atoms` sobre el crudo
  produce los 2 átomos F-MANDATORY (triggers `evite` / `de vital importancia`); el átomo
  carrier (2558) pasa `atom_good_form`; sobre la vista servida: **0 átomos MANDATORY**.
- **El binding aguantaría** (borradores OFF almacenados del probe v3, r1-r3): F12 CITADO
  en 3/3; ambos átomos exigibles en la ventana de cita (overlap procedimental 4 ≥ 2) en
  3/3. El detector must-preserve usa la MISMA vista (`_chunk_text` → paridad de vista)
  ⇒ hoy es estructuralmente ciego a obl_0d6a; abierta la vista, la conversión vía anexo
  es determinista módulo cap (MANDATORY = prioridad 0 del cap).
- **Hallazgo adicional que refina DEC-131:** el span fuente de **obl_b2043**
  («Instrucción de entrada», offset 1427 de F12) TAMBIÉN queda fuera de las cards →
  b2043 comparte causa serving-view además de su causa composite. («Instrucción de
  salida»/obl_7aa7 SÍ está servida, card `[1694,2052]`.)

### 0.2 D1 — composites: funnel POR-PROPUESTA del brazo híbrido — MEDIDO ($0.0815)

Artefacto: `evals/s274_hybrid_funnel_diag_v1.json` (`scripts/s274_hybrid_funnel_diag.py`,
1 réplica sobre borradores OFF ALMACENADOS r1, 16 llamadas Haiku, 0 generaciones, 0 DB).

- **Por qué el probe v3 no pudo diagnosticar esto (gap DEC-127):** los contadores SÍ se
  persistieron pero AGREGADOS por réplica (`hybrid_grounding` en el jsonl:
  proposals/rejected_shape/…), sin registro por-propuesta (familia, span, causa) ni
  funnel downstream (accepted→bound→missing→selected) — `must_preserve_trace` solo lleva
  totales. Con agregados no se distingue si el span del TARGET murió o ni se propuso.
  Este diagnóstico cierra el gap con instrumentación por-propuesta (sin tocar el módulo).
- **Funnel real (80 propuestas):** 62 `rejected_shape` (77,5%) · 10 overlap · 2
  grounding · 6 accepted. Por target:
  - **obl_015f (cat018/TONE):** Haiku SÍ propone el contenido diana 2 veces —
    `**Donde:** Tono = tipo de sonido en el rango 1–33 / Volumen = …` como F-BUNDLE y
    «Es el operador el que permite introducir tono y volumen…» como F-MANDATORY — y
    AMBAS mueren en `rejected_shape`: el separador `=` no es separador de definición
    para `_DEFLINE` (solo `:` y guion espaciado) y la frase no tiene trigger del léxico
    MANDATORY. **Causa: gap de shape/familia, no grounding ni crowding.**
  - **obl_a5d9 (hp002/F2):** la vista es completa (fragmento sin lane) y Haiku propone 6
    spans de F2 — NINGUNO el qualifier «valores nominales»: el prompt solo define las 4
    familias y el qualifier semántico no encaja en ninguna. Es EXACTAMENTE el sub-caso
    declarado no-detectable en el diseño §1.1 (TODO LLM-assist en `must_preserve.py`,
    comentario F-RANGE). **Causa: hueco de familia en el contrato (ni det ni híbrido).**
  - **obl_b2043 (hp017/F12):** Haiku solo ve la vista servida (1.037 chars) — el span
    diana NO está en ella. **Causa: serving-view (= C1), aguas arriba del híbrido.**
  - **obl_7aa7 (hp017/F12):** el contenido («esta parte de la regla solo puede
    procesarse…») SÍ se propone → `rejected_shape` como F-MANDATORY (sin trigger).
    **Causa: gap de familia (cláusula definicional, no obligación).**
  - Crowding del cap NO es causa dominante: solo 2 exclusiones `cap_or_dedup` en toda la
    réplica, ninguna de target.
- **Y aunque el shape los admitiera, HOY el binding también los mataría** (probes $0
  sobre ventanas de cita de los borradores r1):
  - cat018 `[F8]`: ventana sin NINGÚN token propio del bundle TONE (la respuesta cubre
    los ejemplos OPCIONES del mismo F8, otros miembros) → bind ≥2 falla.
  - hp017 `[F12]`: ventana = «El menú de la central solo debe usarse para modificaciones
    menores [F12].» — 0 tokens de la anatomía de regla → bind falla para b2043/7aa7
    (los MANDATORY del warning SÍ bindean: su contrato es contexto procedimental, overlap 4).
  - hp002 `[F2]`: ventana contiene `nominal` y `flujo`; el átomo diría `nominales`
    (plural) → con match EXACTO 1 token; con tolerancia de plural (que ya existe como
    `_noun_stem` en F-COUNT) serían 2 → bindearía.
- **Cadena causal completa de los composites:** (1º) familia/shape — el validador
  colapsa el brazo híbrido sobre los 4 shapes deterministas y las cláusulas
  relacionales/definicionales no tienen familia; (2º) binding exacto sin tolerancia
  morfológica; (3º) b2043 además serving-view. Grounding NO es el cuello (2/80).

---

## 1. Recomendación (por bloque), alternativas y descartes

> Protocolo 2 §5 — levers YA medidos que esto toca, con MÉTRICA visible:
> - **Relajación del binding:** DEC-127 la rechazó 2× — «relajar el binding ≥2 compra
>   conversiones con ruido» — con métrica de las validaciones frescas seed-270 (36
>   clean-FP por anchors genéricos) y seed-271 (14 FP single-token). Ese "settled" es
>   sobre relajación INCONDICIONAL decidida en caliente durante probes. D2 NO lo
>   re-litiga: propone una variante RESTRINGIDA (1-token-DISTINTIVO) con gate de
>   clean-noise en población fresca ANTES del probe — resuelve la tensión DECLARADA en
>   DEC-122/DEC-127 (obl_7bba: 1 solo token «cbe») con datos. Si el gate fresco de ruido
>   falla, D2 muere sin tocar el probe (el veredicto DEC-127 queda reforzado).
> - **Bounded serving (s110/s111):** decisión de diseño, no lever medido con gate; C1 no
>   la revierte — añade una CLASE de card recibida manteniendo su contrato íntegro
>   (spans exactos receipted, vista acotada, prefijo protegido intacto).
> - **Cuota-enunciados (Bloque B):** CERRADO PERMANENTE (DEC-132b, métrica v3b: daño a
>   nivel respuesta hp005#2 3/3→0/3). Familia mecánica DISTINTA (retrieval-fusión); nada
>   de este diseño la toca. Los 2 retrieval-miss (cat017#2, hp010#1) NO están en scope.
> - **Contrato must-preserve:** Etapa-1 v8 GO (recall 0.976/0.923/1.0/0.905, DEC-130);
>   los cambios D pasan por re-validación fresca v9 con los gates v8 ÍNTEGROS (un fix no
>   se compra con recall).

### C1 — Fix de la vista servida (obl_0d6a; co-beneficia b2043)

**Recomendación:** card de CALLOUT-MANDATORY en la lane, flag estricto default-off
`COVERAGE_MANDATORY_CALLOUT` (patrón `_strict_on_off`):

- En `_build_served_coverage_cards` (attest-time): escanear el `content` COMPLETO del
  chunk con el léxico CERRADO F-MANDATORY (mismas `_mandatory_triggers` de
  `must_preserve`, import lazy — léxico ya validado en Etapa-1); las oraciones con
  trigger FUERA de los spans ya servidos forman **UNA card extra** por chunk:
  contiguas mergeadas, acotada ≤600 chars, `mandatory_callout: true`,
  `exact_source_span_validated: true`, receipted EXACTAMENTE igual que las demás
  (`has_exact_served_coverage_receipt` la re-deriva y compara — la revalidación existente
  cubre la card nueva sin código extra).
- Con flag off: `_build_served_coverage_cards` byte-idéntico (cero drift de receipts).
- Efecto: la vista servida (generador Y detector, paridad intacta) incluye el callout;
  el anexo must-preserve puede anexarlo (MANDATORY = prioridad 0 del cap); el matcher
  `merged_warning_block` del probe lo acredita en respuesta O anexo.

**Por qué es BP + estructural + escalable:** ataca la raíz (punto ciego sistemático de la
alineación query-faceta para la clase seguridad), reutiliza léxico y receipts ya
validados, y escala a 30+ fabricantes (cualquier warning adyacente a procedimiento en
chunk de coverage, sin lista por-fabricante). Mantiene TODOS los invariantes de la lane.

**Alternativas descartadas:**
1. *Servir el chunk completo en lanes de coverage* — revienta el contrato de vista
   acotada (coste de tokens + cola-no-relacionada, el rationale s110/s111 sigue válido).
2. *Fix solo en el detector* (`_chunk_text` lee `content` crudo) — rompe la paridad de
   vista deliberada (docstring: «el MISMO contenido que el generador sirve»), deja al
   generador ciego igual, y reabre por el anexo la cola-no-relacionada completa (no solo
   la clase seguridad). Queda como fallback declarado si el negcontrol de C1 muestra
   ruido de la card en sanos.
3. *«Subir el cap»* — no existe tal cap (hallazgo del diagnóstico); no-op.
4. *Re-tunear el selector de cards de la lane* — tocaría la selección validada de
   evidencia por faceta para TODAS las queries (blast radius máximo) por un caso de
   clase acotada.

**Medición (fase P2 del prereg):** pareado CONTEMPORÁNEO OFF/ON (lección v3 Bloque B:
JAMÁS referencia congelada), mismo día/misma DB/K=3, generación fresca hp017 en ambos
brazos (el fix cambia la GENERACIÓN, no solo el apply; `MUST_PRESERVE_CONTRACT=on` en
ambos brazos = estado prod DEC-131), matcher determinista NFKD (el de s163/v3b, 0 juez):
- Gate de conversión: `merged_warning_block` estable (≥2/3) en ON.
- Gates de daño heredados: 3 obligaciones protegidas estables-en-OFF no caen en ON;
  0 conflictos nuevos; anclas pareadas +0/−0 con STOP duro en la unión s104+s105;
  containment pareado contemporáneo de pool no aplica (0 cambios de retrieval: la card
  cambia la VISTA, no el pool) — se verifica `appended_ids` idénticos OFF/ON.
- Negcontrol: los 5 golds sanos del smoke Etapa-3 con flag ON — 0 apéndices espurios
  nuevos, 0 anclas perdidas (matcher pareado).

### C2 — Extensión del binding a fragmentos SERVIDOS-no-citados (obl_2f5d)

**Recomendación:** elegibilidad de átomos de fragmentos servidos+ATTESTADOS sin cita
`[Fn]` en el borrador, con contrato MÁS estricto que el de citados (conservador):

- Attestation de identidad INTACTA (catálogo DEC-074/090, fail-closed) — sin cambio.
- Binding: sin ventana de cita disponible, el contrato por-familia de
  `atom_exigible_in` se evalúa sobre la RESPUESTA COMPLETA con umbral REFORZADO
  (≥3 tokens propios, o número propio + ≥1 token propio; F-MANDATORY: contexto
  procedimental ≥3) — el listón sube porque la superficie de match crece.
- Render: cita `[Fn]` del fragmento fuente en el anexo (el dato es verificable aunque el
  writer no lo citara — es exactamente el selection-loss de s243: F13 servido, no usado).
- Caso diana: obl_2f5d — F13 (r.i «- -» + rango 01-30) attestado; el borrador §1 cubre
  rI 00/01-30 → números/tokens propios presentes en la respuesta.

**Alternativas descartadas:** (a) exigir cita siempre (estado actual — deja el único
selection-loss del set estructuralmente fuera del mecanismo); (b) forzar la CITA en el
writer vía prompt (re-litiga la familia generación-guiada, clase s121-s123 sin delta); (c)
umbral igual al de citados (compra riesgo de ruido sin necesidad — el guard de Etapa-1
fresco decide si incluso ≥3 es ruidoso).

**Guard de no-ruido ANTES del probe (fase P1):** cohorte de mutaciones FRESCA (seed
NUEVA, exclusiones acumuladas v1+s270-274) con tipos `served_not_cited_*`: átomos
plantados en fragmentos no citados de poblaciones limpias → FP=0 exigido en clean;
recall medido en mutados. Sin GO de P1, C2 no entra al probe.

### D1 — Composites: cerrar el gap de familia + tolerancia morfológica del binding

Del funnel (§0.2), fixes GENÉRICOS en cadena causal, cada uno gateado en fresco:

- **D1a — separador `=` en `_DEFLINE`** (det + híbrido): «Tono = tipo de sonido…» es
  patrón genérico de definición en manuales/OCR (clase del fix v2 ya adjudicado para el
  guion espaciado, DEC-126-era). Coste: riesgo FP en líneas de asignación de config —
  gate: mutaciones BUNDLE con `=`-schemas + clean FP=0.
- **D1b — familia híbrida F-RELATION (cláusula relacional/definicional):** el brazo
  LLM-assist DECLARADO en el diseño §1.1 (TODO en `must_preserve.py`) para
  `compound_relation_qualifier_loss`. Slot nuevo en el prompt híbrido + shape-check en
  CÓDIGO (cláusula completa con verbo conjugado ≥40 chars — reusa `span_good_form` — y
  ≥1 número-con-unidad O ≥2 tokens distintivos propios); binding con el contrato de
  presencia parcial (≥2 tokens propios / número propio); render vía whitelist v5 sin
  cambios. Cubre a5d9 (qualifier), 7aa7 (definicional) y el lado-relación de 015f.
- **D1c — tolerancia morfológica del binding** (plural es/en): el match token-propio ↔
  token-ventana acepta stem plural (`nominales`≈`nominal`) reutilizando `_noun_stem`
  (ya vivo en F-COUNT desde v4). Convierte el bind de a5d9 (1→2 tokens); genérico
  (es/-s/-es), no por-target. Gate: clean-noise fresco (el stem NO puede reactivar la
  clase seed-271 de 14 FP single-token — se mide exactamente esa clase).

**Declaración honesta de alcance (gaps):**
- **obl_015f probablemente NO convertible sin comprar ruido:** su ventana `[F8]` no
  comparte NINGÚN token con el bundle TONE (la respuesta cubre miembros hermanos). El
  binding a nivel fragmento fue rechazado con métrica (seed-270: 36 FP) y NO se propone.
  015f se MIDE en el probe pero no se gatea; si no convierte, su vía es edición de gold
  NO (Alberto ya la confirmó CORE) → queda como residual declarado del mecanismo.
- **b2043/7aa7 dependen de C1 (vista) + D1b (familia) + ventana:** su ventana `[F12]`
  hoy no comparte tokens; la conversión llegaría por (i) generación con vista abierta
  (incierto: s156 muestra que los frontier también lo omiten con contexto completo) o
  (ii) anexo si el binding cambia de ventana — se miden, confianza MEDIA-BAJA.
- Confianza por candidato: 0d6a ALTA (C1, binding verificado 3/3) · 7bba MEDIA (D2) ·
  2f5d MEDIA (C2) · a5d9 MEDIA (D1b+D1c) · b2043/7aa7 MEDIA-BAJA · 015f BAJA.
  **El +6 NO está garantizado por diseño; la aritmética honesta es 1 alta + 3 medias +
  2 medias-bajas + 1 baja.** Si el probe rinde <+6, el gap restante vuelve por-clase (no
  se itera en caliente — herencia anti-overfit DEC-127).

### D2 — Binding 1-token-DISTINTIVO (obl_7bba), la tensión DEC-122 resuelta con datos

**Recomendación:** el bind por-familia acepta TAMBIÉN «1 token propio si es
DISTINTIVO», con definición CERRADA y determinista (sin DB en runtime):

- token distintivo := no-stopword, longitud ≥2, y (patrón identificador técnico:
  acrónimo `[A-Z]{2,6}` en la superficie original, o alfanumérico con dígito
  `C1L1M2`/`W01`; o pertenencia a la lista cerrada de identificadores del catálogo
  gobernado ya cargado en memoria) — «cbe» califica (acrónimo CBE); «sistema»/«ajuste»
  (la clase seed-271) NO califican.
- idf-alto sobre corpus se DESCARTA como criterio de runtime (exige stats de corpus
  vivas = dependencia DB + drift); si el patrón cerrado resultara insuficiente en P1, el
  fallback declarado es lista estática versionada derivada UNA vez del corpus (decisión
  nueva, no este prereg).

**Gate de clean-noise ANTES del probe (P1):** población fresca seed nueva, mutación
`single_distinctive_token_window`: ventanas de 1 token distintivo en poblaciones limpias
→ FP=0 exigido; + re-medición de la clase seed-271 (single-token genérico) → debe seguir
0. Si falla → D2 muere, DEC-127 reforzado, obl_7bba residual.

---

## 2. Cuenta de probes y riesgo anti-overfit — DECLARADO

Este sería el **probe #4** sobre los mismos 4 targets (v1 $0.75 / v2 $1.09 / v3 $1.14,
DEC-127; + certificaciones det-only $0). El riesgo de overfit a los 4 textos gold CRECE
con cada probe. Mitigaciones (heredadas y ampliadas):

1. **Cambios exclusivamente GENÉRICOS** justificados por funnel/diagnóstico medido (este
   doc §0), jamás por los textos gold; los casos pineados en tests son de los
   diagnósticos, no de los golds.
2. **Validación fresca SIEMPRE previa** (P1, seed nueva, exclusiones acumuladas): ningún
   cambio entra al probe sin GO en población que no ha visto ningún probe.
3. **UN solo probe consolidado para C+D** (no uno por fix): P2 es la única exposición
   nueva a los targets; sin re-runs "para confirmar"; no-retry.
4. **Gates de daño heredados intactos** (protegidas, conflictos, anclas unión s104+s105,
   negcontrol en sanos) — un fix no puede comprarse con daño; TODOS pareados
   contemporáneos (lección v3 Bloque B: la referencia congelada v2.2 dio falso-daño).
5. **Compromiso de cierre:** si P2 no alcanza su gate, NO hay probe #5 con esta
   mecánica; lo no convertido queda residual por-clase y cualquier reapertura exige
   evidencia nueva + permiso explícito (patrón DEC-126/132b).

## 3. Fases, gates y presupuesto (techo total ≤$15)

| Fase | Qué | Coste techo | Gate para avanzar |
|---|---|---|---|
| P0 | Diagnósticos $0.08 (HECHOS: §0) + build flag-off C1/C2/D1/D2 + tests unitarios (sin red) + **dúo Protocolo 3 del build** | $0.30 (dúo Sol) | tests verdes + dúo sin críticos abiertos |
| P1 | Etapa-1 **v9** fresca (seed nueva): recall v8 ÍNTEGRO + clases nuevas (`=`-defline, F-RELATION recall, served-not-cited FP=0, 1-token-distintivo FP=0, stem-binding FP=0, re-clase seed-271=0) — det $0 + brazo híbrido | $2.50 | GO = gates v8 verdes + clases nuevas en umbral; cualquier NO-GO mata SOLO su fix (los demás siguen) |
| P2 | **Probe consolidado C+D** (el #4, único): hp017 generación fresca pareada OFF/ON de C1 (K=3, ambos brazos MPC=on) + apply-side D/C2 sobre borradores OFF (almacenados v3 para cat018/hp002; los frescos de este mismo probe para hp017) con Haiku híbrido; matcher determinista; gates §1 | $6.00 | conversiones estables (≥2/3) por candidato + 0 daño en gates heredados |
| P3 | Negcontrol vivo (5 sanos Etapa-3 con flags ON) + smoke monotonía | $1.50 | 0 espurios / 0 anclas perdidas |
| P4 | Cierre: banking SOLO de conversiones con certificación det-only o det+híbrido según flag de prod (patrón DEC-131), DECs, closeout | $0 | — |

Total techos: **$10.30 ≤ $15** (margen para 1 re-run de fase P1 si un gate de
instrumento — no de resultado — lo exige, declarándolo; jamás re-run de P2).

**Forks Protocolo 4 verificados:** levers medidos citados con métrica (§1 cabecera);
held-out embargado NO se toca; juez NO se usa (matcher determinista s163); freeze
s113 + réplicas v3 pineados por SHA en el prereg; DB GET-only en todas las fases (0
escrituras); los 77 legacy carries siguen fuera del KPI (S205).

**Decisión de ship (fuera de este prereg):** flags default-off; merge tras dúo; la
activación en demo/prod de `COVERAGE_MANDATORY_CALLOUT` sigue el patrón DEC-127b/130
(re-smoke limpio); el banking sigue el patrón DEC-131 (certificación + recibo vivo).
