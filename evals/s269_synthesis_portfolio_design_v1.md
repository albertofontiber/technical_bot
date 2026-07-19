# S269 — Cartera para los 12 synthesis-miss: triage de golds + contrato de átomos must-preserve (v2, dúo-adjudicado)

> **v2 (19 jul):** revisión del dúo aplicada — Sol xhigh ts=2026-07-19T00:08:29 (10 hallazgos:
> 4 críticos + 5 medios + 1 menor) + Fable 5 emparejado (8 hallazgos: 1 crítico + 4 medios +
> 3 menores). Adjudicación: **18/18 confirmados o confirmados-con-matiz, 0 falsos positivos
> claros**. Cambios v1→v2 listados en §6. Ronda única — sin bucle de convergencia (DEC-106).

> **Objetivo de HOY (métrica visible, Protocolo 2 §5):** convertir synthesis-miss → OK en la foto
> diagnóstica 157 (143 OK / 12 synth / 2 retr; 98% = 154). Métrica: anchors por-obligación
> (matcher determinista s163/answer_planner, auditado JUSTO — 0 FN hallados) sobre respuestas
> frescas a las 4 preguntas target, gate tipo DEC-112 (≥1 conversión + 0 regresiones protegidas +
> 0 conflictos nuevos), K≥3 réplicas por brazo (inestabilidad de réplica medida en S242).
> **El gate de SHIP (≥1 conversión limpia) y el objetivo 98% (+8 conversiones tras demotes) son
> DISTINTOS y se reportan por separado** [dúo-Sol M8]: un GO de ship con <8 conversiones NO
> declara el objetivo cumplido; itera por-familia o declara el gap.

## 0. Contexto congelado (autoridades)

- Taxonomía causal de los 12: `evals/s243_synthesis_miss_causal_taxonomy_v1.yaml` —
  11/12 `within_cited_fragment_detail_loss`, 1/12 `source_fragment_selection_loss`
  (hp011/obl_2f5d79e354b9, F13 servido no citado). Familias: qualifier_loss 5 ·
  bundle_member_loss 3 · mandatory_safety_omission 3 · enumeration_cardinality 1.
  **Los `forbidden_reopens` viven en s243:173-184** (no en s261 — corrección dúo-Fable).
- Checkpoint canónico: `evals/s261_synthesis_checkpoint_v1.yaml` + cláusula operativa exacta de
  `evals/s260_evidence_claim_ir_closeout_v1.yaml`: *"A new synthesis architecture may reach the
  twelve targets only after a small independent positive/negative structural cohort and a
  contemporaneous same-model control establish generalization and attribution. Reusing S260 on
  the targets or relabeling the same package is forbidden."* → el probe a los 12 está
  SANCIONADO tras la Etapa 1; lo prohibido es reutilizar el package S260 [resuelve dúo-Fable F5].
- Techo frontier medido: `evals/s156_frontier_synthesis_ceiling_v1.json` — sobre **13
  relaciones** target con contexto completo one-shot, Fable cubre 4/13 y Sol 2/13 (una llamada
  Sol quedó incompleta) [métrica corregida por dúo-Fable F3]. Lectura honesta: la sustitución
  one-shot de writer NO resuelve los misses (S156 NO-GO, forbidden_reopen); NO es prueba de que
  ningún writer pueda — es evidencia de que el contrato implícito de completitud no lo aplica
  ningún writer QA-genérico por defecto [reformulado por dúo-Sol M9].
- Señal positiva más fuerte: S193 (`evals/s193_terra_id_planner_deterministic_append_v1.json`)
  — selector de IDs + anexado determinista: **+5/37 puntos, +2 completas, `regressed_points: 0`
  MEDIDO** (no "garantizado"; corrección dúo ×2), $0.07; cerrado solo por recall del selector
  0.794 < 0.90. LEVER_DIGEST l.26: reapertura sancionada vía cohorte fresca.
- Precisión determinista alcanzable: S249 — precisión 1.0 / FP 0; **cerró por DOS gates:
  `mutation_recall_min_0_90` (0.778) Y `represented_questions_min_8` (6)** [precisión de cita
  corregida por dúo-Fable F6]. Lección que S269 CONSERVA como gate (no la invierte — dúo-Sol
  C2): la Etapa 1 lleva gates de recall POR FAMILIA, no solo precisión.
- Modos de fallo a no repetir: S164 (selección de fuente equivocada), S221 (rewrite: gains con
  regresiones), S242 (clause-bound: 0 gains / 3 regresiones / 1 conflicto), S223 (addendum:
  cerrado con review semántica INCOMPLETA — el prefijo preservado no impidió contradicciones
  materiales según su review parcial).

## 1. Recomendación

### Track 1 — Adjudicación de requiredness de los 12 (gold-review, DEC-094 pendiente)

Triage EJECUTADO y VERSIONADO en **`evals/s269_triage_12misses_v1.yaml`** [artefacto añadido
por crítico dúo-Fable F1: sin primarios versionados no hay triage]. Propuesta: 8 CORE + 3
SUPPLEMENTARY + 1 SOURCE-CONFLICT (detalle §4). **Paso previo obligatorio a editar golds**
[dúo-Sol M7]: packet de adjudicación para Alberto con verificación al píxel (render de página
vía `scripts/render_pdf_page.py`, páginas vecinas, ES+EN, cita literal por fila — checklist
canónico RULER_DESIGN §2); el triage de sesión NO basta para tocar gold/denominador. Nada se
edita sin ✅ de Alberto + puerta `gold_store`.

### Track 2 — Contrato de átomos must-preserve con render por postcondición (mecanismo)

Capa flag-gated `MUST_PRESERVE_CONTRACT` (default-off) en el path de generación:

1. **Detector por familia** — feasibilidad declarada POR FAMILIA [dúo-Sol M6: la infraestructura
   `evidence_units_v2` solo empareja cabecera+fila de tablas; NO cubre pestañas/listas/schemas]:
   - F-RANGE (determinista): valor+unidad+extremos+paso+scope detectados juntos por estructura
     numérica. NO cubre el qualifier semántico tipo "valores nominales" → ese sub-caso es
     LLM-assist declarado (Haiku, barato, solo si el determinista no dispara).
   - F-BUNDLE (determinista nuevo): headings markdown (`##`/`###`) + estructura lista/tabla del
     fragmento extraído → miembro↔cabecera-padre. Parser propio, NO `evidence_units_v2`.
   - F-MANDATORY (determinista): léxico cerrado bilingüe de lenguaje obligatorio/peligro
     (imprescindible, obligatorio, vital, nunca, advertencia, peligro, evite; mandatory, must,
     warning, never...). **"antes de"/"before" NO son gatillo por sí solos** [dúo-Fable F8:
     frecuencia altísima → FP masivo]; solo colocados con un término obligatorio en la misma
     cláusula.
   - F-COUNT (determinista): conteo declarado vs miembros enumerados en el fragmento; fuente
     inconsistente → conducta DISCLOSE (guard s243), nunca resolver en silencio.
2. **Binding claim↔átomo + attestation de identidad** [endurecido por dúo-Sol C4]: un átomo
   solo es exigible si (a) la respuesta borrador toca su claim ancla (mismo valor/entidad/
   procedimiento) en un fragmento citado, **y (b) el `document_id` del fragmento pertenece al
   doc_map de la identidad resuelta de la query (catálogo DEC-074/090)**; si la identidad no
   resuelve → el anexo NO actúa (fail-closed del anexo, fail-open de la respuesta). Restringirse
   al fragmento citado NO basta contra S164 (el writer puede citar el manual equivocado y el
   contrato lo amplificaría) — la attestation es la barrera.
3. **Render por postcondición** (S193): átomo exigible ausente → anexa el span fuente EXACTO
   con cita, sección "Información adicional del manual" (SIN la palabra "verificada" — el span
   verbatim hereda la extracción, no el píxel; riesgo OCR/7-seg declarado [dúo-Sol M5,
   `feedback_7segment`]). Garantía real [dúo ×2, C3/F4]: **la monotonía garantiza no-borrado
   bajo el matcher; NO garantiza ausencia de contradicción** — si el span contradice
   numéricamente un claim del borrador sobre el mismo predicado → formato disclosure explícito
   ("el manual también indica...") y el gate de Etapa 2 cuenta conflictos nuevos (0 requerido).
   Cap: 4 átomos/respuesta.

**Validación (orden s243/s260, sin saltarse fases):**
- **Etapa 1 — cohorte estructural pos/neg independiente** (docs jamás empaquetados de la
  reserva ~623; DEC-111 cerró la autoría de PREGUNTAS desde chunks, no el etiquetado de
  unidades — distinción declarada): positivos con átomos por familia + negativos sin ellos.
  **Etiquetado = gold independiente del detector** [dúo-Sol C2]: doble etiquetador modelo
  (Luna + Haiku, prompts distintos), desacuerdo → adjudicación (Sonnet árbitro o descarte del
  ítem); el detector JAMÁS etiqueta su propio gold. Gates pre-declarados POR FAMILIA:
  **recall ≥0.80 · precisión ≥0.95 · FP=0 en negativos** — recall como GATE, no como reporting
  (conserva la lección S249). Coste ~$3-6.
- **Etapa 2 — probe único a los 4 targets**, SOLO tras: (a) Etapa 1 GO, **y (b) adjudicación
  formal de Alberto de la reapertura de la familia s222/s223** [dúo ×2, C1/F2 — la adyacencia
  no se delega al dúo ni se decide sola: Track 2 anexa post-generación y la prohibición s243 es
  de FAMILIA. Evidencia para esa decisión: el cierre S223 fue con review semántica INCOMPLETA
  (Fable max_tokens, Sol 520) + directiva de Alberto de esta sesión de no descartar líneas por
  condiciones de ejecución distintas + las 4 diferencias de diseño (detector determinista,
  attestation identidad, spans verbatim+disclosure, gates S249-preservados)]. Gate tipo DEC-112,
  K=3 réplicas, control same-model contemporáneo. Coste ~$3-6.
- **Etapa 3 — regresión amplia** (fact-level smoke ~$3 → full ~$22 si limpio) antes de
  cualquier default-on. Total track ≤ ~$40.

**Alcance declarado sobre los 9 core post-triage** [aritmética corregida, dúo-Sol menor]:
**8 directos** = F-BUNDLE ×3 (obl_7bba, obl_b2043, obl_7aa7) + F-MANDATORY ×3 (obl_b6f6,
obl_16637, obl_0d6a) + F-RANGE/qualifier ×1 (obl_a5d9 — sub-caso LLM-assist) + F-COUNT/disclose
×1 (obl_872c re-specced) · **+1 stretch** = obl_2f5d (selection-loss: binding por entidad `r.i`
sobre fragmento SERVIDO no citado — extensión declarada del binding, con la MISMA attestation
de identidad; brazo de gate propio, no prometido). Los 2 retrieval-miss (cat017#2, hp010#1) =
margen por lever retrieval aparte.

## 2. Alternativas consideradas y por qué se descartan (métrica del veredicto citada)

| Alternativa | Veredicto previo · métrica | Por qué no |
|---|---|---|
| Sustitución writer (frontier/Terra) | S156: Fable 4/13, Sol 2/13 (una llamada incompleta); S192: −1 punto, 2 regresiones | forbidden_reopen (s243); one-shot no aplica el contrato |
| Checklist/facetas en prompt | S206/DEC-119: 0 estables, 1 regresión, $1.73 | cerrado como mecanismo; guardrails de prompt no auto-ejecutan (2× medido) |
| Writer clause-bound descompuesto | S242: 0 gains, 3 regresiones, 1 conflicto (n=2 réplicas, baseline inestable — matiz) | rompe más de lo que gana |
| Rewrite post-answer | S221: 7/7 gains, 3 regresiones protegidas | capacidad sí, seguridad no |
| Addendum semántico s222/s223 | forbidden_reopen s243; S223 cerrado con review INCOMPLETA | **familia adyacente a Track 2 — adjudicación formal de Alberto ANTES de Etapa 2 (§1); no se presume** |
| Agentic RAG / multi-hop | DEC-089 piloto D 0/6; S106-era; ACL-2026 | 11/12 misses son within-cited-fragment: la evidencia ya está delante del writer |
| Capa clarify | conduct-level DEC-074/082 (diferida por-pregunta) | las 4 targets no son ambiguas; otra clase de fallo |
| Re-chunking v3/v4 | S140 FINAL_NO_GO (MRR 0.402→0.369) | ortogonal al miss within-fragment |
| Extender S122 per-target | S248: 0/12; s141 forbidden | anti-escalable; S269 es por-familia genérica |

## 3. Gaps y riesgos declarados

1. **Overfit-por-taxonomía** (familias derivadas de los 12) → mitigación: formulación genérica
   + Etapa 1 en población fresca con gates de recall/precisión ANTES de mirar targets.
2. **Adyacencia forbidden s222/s223** → adjudicación formal de Alberto pre-Etapa-2 (§1).
3. **Contradicción por anexo** (el span verbatim puede contradecir la paráfrasis del borrador)
   → formato disclosure + gate 0-conflictos-nuevos + K=3.
4. **OCR/extracción en spans verbatim** → caption sin "verificada"; displays 7-seg fuera del
   anexo automático (léxico F-RANGE excluye patrones de display).
5. **F-MANDATORY FP** → léxico sin gatillos de alta frecuencia solos; gate FP=0 en negativos.
6. **hp011/obl_2f5d fuera de garantía** (selection-loss) — brazo stretch propio. Si tras
   Track 1+2 quedan >1 core sin convertir de los 9, **el 98% NO se alcanza por esta vía sola**
   → se declara el gap con opciones (retrieval-lever para los 2 retr-miss; iteración
   por-familia; nueva adjudicación).
7. **La foto 157 es diagnóstica** (8 OK dependen de lanes default-off + 23 medidos con planner
   guided): el crédito de S269 se mide con el MISMO instrumento (anchors s163) para
   comparabilidad; el crédito PRODUCTIVO (flags en serving) queda como decisión de release
   separada y explícita.

## 4. Triage (Track 1) — artefacto versionado

**`evals/s269_triage_12misses_v1.yaml`** (12 veredictos + verificación adversarial 12/12 +
auditoría del instrumento + los 2 retrieval-miss). Resumen: **8 CORE** (obl_7bba pestaña-padre ·
obl_b6f6 aislamiento-seguridad · obl_a5d9 rol-nominal [borderline] · obl_2f5d r.i-rearme
[el más core; selection-loss] · obl_b2043/obl_7aa7 schema-regla · obl_16637/obl_0d6a warnings
[merge-note: mismo bloque F12]) · **3 SUPPLEMENTARY** (obl_015f TONE [demote más débil] ·
obl_07ee 120%-A11-C32 [pregunta es flujo BAJO] · obl_1615 paso-5s [demote limpio]) ·
**1 SOURCE-CONFLICT** (obl_872c "seis" vs 7 columnas pairwise-distintas verificadas → re-spec a
disclosure). Instrumento auditado JUSTO (matcher determinista, 0 model calls, 0 INSTRUMENT-FN).
Retrieval-miss: ambos CORE, hecho verbatim en corpus.

**Proyección si Alberto acepta:** denominador 154 · 98% = 151 · hacen falta **+8** de los
9 core + 2 retr. Estado: PROPUESTA — pendiente packet-al-píxel + adjudicación Alberto.

## 5. Por qué es BP + estructural + escalable

- **BP:** completitud por contrato verificable (postcondición render) — patrón de sistemas
  verificados, medido en S193 (+5, `regressed_points: 0`); detectores deterministas con
  precisión Y recall gateados (lección S249 conservada); disclose-conflictos = conducta
  canónica del dominio seguridad; identidad attestada por catálogo gobernado (DEC-074).
- **Estructural:** ataca la causa raíz medida (poda de qualifiers/miembros/callouts al
  redactar — s243), sin reglas por fabricante/producto/target (cumple prohibición s141).
- **Escalable a 30+:** familias = propiedades del género "manual técnico"; detectores = código
  + léxico cerrado bilingüe; coste marginal ≈1 call Haiku condicional por query.

## 6. Registro de adjudicación del dúo (ronda única, 19 jul)

- Sol xhigh ts=2026-07-19T00:08:29 (60 tool-calls, budget agotado — dependencias no
  inspeccionadas declaradas): C1 reapertura-formal ✔ aplicado (§1 Etapa 2) · C2 gate-recall ✔
  aplicado (Etapa 1) · C3 sobre-claim regresiones ✔ aplicado (§1.3) · C4 attestation ✔ aplicado
  (§1.2) · M5 OCR/caption ✔ · M6 feasibilidad detectores ✔ (verificado en código por el autor) ·
  M7 packet-al-píxel ✔ · M8 gate-vs-objetivo ✔ (encabezado) · M9 framing S156 ✔ · menor
  aritmética ✔.
- Fable (12 tool-calls): F1 triage-sin-artefacto ✔ **crítico aplicado**
  (`s269_triage_12misses_v1.yaml`) · F2 reapertura-default ✔ (=C1) · F3 denominador S156 13 no
  11 ✔ · F4 =C3 ✔ · F5 reuse_s260_targets ✔ resuelto con cita literal (§0) · F6 S249 dos gates ✔ ·
  F7 atribución forbidden_reopens s243 ✔ · F8 léxico "antes de" ✔.
- Falsos positivos: 0. Tally: 18/18 confirmados o confirmados-con-matiz.
