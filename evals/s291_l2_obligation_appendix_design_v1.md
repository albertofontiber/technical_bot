# s291 — DISEÑO L2: apéndice determinista del aviso obligatorio servido (clase hp002#4)

Estado: **DISEÑO, nada cableado.** Ejecuta el lever L2 adjudicado por el dúo r1 de etapa 3
(`evals/s290_etapa3_diagnosis_v1.md` §Reconciliación; DEC-169). Mecanismo diagnosticado:
la reserva sirve el aviso (etapa 2 ✓), el generador lo omite a discreción en ~50% de
generaciones, y la red determinista existente (`must_preserve`, familia F-MANDATORY prioridad
1) NO puede exigirlo porque `bind_atoms` requiere fragmento CITADO (must_preserve.py:1685-1688)
y un aviso omitido nunca se cita.

## Declaración de métrica + settled que gobierna (Protocolo 2.5 — VISIBLE)

- **Objetivo HOY**: hp002#4 (SEGURIDAD) conveyed-stable; clase «aviso obligatorio servido»
  no-omitible. Métrica = per-fact conveyed pareado sobre composición congelada
  (`gen_answer_only`, N=2 por brazo, juez del instrumento **v3.2**).
- **Settled que esta clase YA midió — citado con métrica (mandato dúo r1, hallazgo 1):**
  - **`MP_SERVED_BINDING` NO-GO (DEC-127, reforzado ×2; métrica `served_uncited_clean_fp =
    24/105`)**: binding GENÉRICO de fragmentos servidos-no-citados, TODAS las familias de
    átomos, cohorte 105 filas → 26 anexos de hermanos genuinos / 1 target. DEC-134: «relajar
    el gate de C2 re-litiga DEC-127 sin evidencia nueva».
  - **Por qué esto NO es ese lever (población distinta, declarado, NO probado — el gate FP
    lo prueba o lo mata):** aquí se liga (i) SOLO la lane `obligation_warning_reserve_v1`
    (≤1 fila/respuesta, presupuesto propio, filtros de clase + orden sección-intención de
    s289), (ii) SOLO el span de la card `mandatory_warning` (jamás todos los átomos del
    fragmento), (iii) SOLO la familia F-MANDATORY. El mecanismo de FP medido (hermanos
    genuinos multi-familia sobre 105 filas) no tiene población equivalente aquí — pero la
    afirmación se GATEA, no se asume (S274 declaró la familia de anexos exhausta «para los
    6 residuales de entonces»; hp002#4 no era uno — reconfirmado en DECISIONS:2723-2724).
- **Techo de radio**: la reserva dispara en 18/39 golds (censo A6) — el gate FP cubre los 39.

## Diseño (brazo A — determinista, el principal)

Flag **`OBLIGATION_WARNING_APPENDIX`** (`_strict_on_off`, default off; DEMO_FLAGS pin off +
SAFE_DEFAULTS off, patrón s289). En `apply_must_preserve_contract`, tras el pase normal:

1. **Selección de candidatos**: fragmentos servidos con `retrieval_lane ==
   "obligation_warning_reserve_v1"` y `coverage_cards[0].mandatory_warning == True` (los
   stamps que la lane YA estampa, rerank_pool_coverage.py:727-731). Cardinalidad ≤1 por
   construcción (presupuesto de la reserva).
2. **Detección SOLO sobre el quote de la card** (`coverage_cards[0].quote` = el span del
   aviso, ≤600 chars, trigger garantizado por `_warning_span`): `detect_atoms(quote)` →
   átomos F-MANDATORY. NO sobre la vista completa del fragmento (evita la clase b2043
   «serving-view sin gatillo», hallazgo 2 del dúo). Léxico COMPARTIDO (mp_lexicon) entre la
   lane y el detector — ítem de verificación V1: `detect_atoms` encuentra ≥1 átomo sobre el
   quote real de hp002 (test unitario con el chunk 5b6a3a19).
3. **Dedup por el predicado EXISTENTE**: `atom_satisfied(atom, draft_answer)`
   (must_preserve.py:1721, F-MANDATORY = trigger presente + overlap de anchors ≥ min(2,n))
   — si el cuerpo YA transmite el aviso (con otras palabras) ⇒ NADA (hallazgo 2: anti-dup).
4. **Si no satisfecho** ⇒ el átomo entra a `missing` con `meta.obligation_appendix=True` y
   se renderiza vía **`render_appendix` EXISTENTE** (prioridad F-MANDATORY=1, paridad
   display/v6-s272) — ningún append-path nuevo. La exención de citación es SOLO para esta
   lane-estampada; `bind_atoms` y `MP_SERVED_BINDING` quedan INTACTOS para todo lo demás.
5. **Traza**: `obligation_appendix: {fragment_id, satisfied|appended, atom_span}` — G-1 del
   gate atribuye cada apéndice.

## Brazo B (paralelo débil — prompt/header)

Marcar en el header del fragmento las filas de la reserva (`[AVISO OBLIGATORIO DE SEGURIDAD]`
en vez del genérico; generator.py:715-719) + regla de prompt no-condicional para esa marca.
Depende de obediencia del modelo (la clase que DEC-051 mide como débil) — se construye como
brazo del MISMO gate pareado; si A pasa FP-limpio y convierte, B queda de respaldo comparado.

## Gates pre-registrados (bajo instrumento v3.2; tripwire hp009 en TODOS)

- **G-0**: suite + byte-invariancia flag-off + V1 (detect sobre quote real).
- **G-FP (el que decide, patrón DEC-134-P3)**: sweep-39 sobre capturas congeladas, brazos
  OFF/ON: lista de golds con apéndice; **por cada apéndice, verificación POR-FILA a mano**
  (¿es EL aviso de la sección procedimental de la query? el orden v2 de s289 lo favorece
  pero no lo garantiza) — vara: **0 apéndices espurios** en 39; esperado: apéndice solo
  donde (reserva sirvió) ∧ (cuerpo no transmite) ≈ 1-3 golds.
- **G-directed**: hp002#4 pareado OFF/ON (`gen_answer_only` sobre composición congelada,
  N=2/brazo): miss/flip → conveyed-stable = éxito; hp002#0-#3 sin degradar.
- **G-conducta**: hp009 (answer, 0 clarify) + longitud/estructura de respuesta en los golds
  con apéndice (el apéndice no debe desplazar contenido del cuerpo — es post-generación).

## Riesgos declarados

1. El quote de la card podría no derivar átomo si `detect_atoms` fragmenta distinto que
   `_warning_span` (léxico compartido pero mecánica de oraciones propia) → V1 lo mide antes
   de nada; si falla, el diseño se re-trabaja (no se fuerza).
2. Apéndice sobre aviso genérico-pero-real (la reserva sin sección-intención en el pool):
   el gate FP lo caza por-fila; si aparece, la mitigación natural es condicionar el apéndice
   a `section_intent` del candidato (dato que la lane ya computa) — NO se pre-cablea sin verlo.
3. Doble aviso si el generador lo transmite parcialmente (satisfied borderline): el predicado
   es el MISMO que gobierna F-MANDATORY hoy en producción — no se inventa vara nueva; los
   bordes que el gate muestre se adjudican con recibo.
4. Radio 18/39: el apéndice solo puede DISPARAR donde la reserva sirvió Y el cuerpo omite —
   el sweep mide la frecuencia real; si dispara >5/39, STOP y re-diseño (sobre-apendizar es
   la clase 24/105).

---

## Reconciliación dúo r2 (v1 → v2) — 14 hallazgos, 0 FP; build GATEADO por V1

Sol 8 (3 críticos) + sub-agente Fable 8 (H1 crítico). Convergencias en léxico, cap/prioridad,
dedup (AMBAS direcciones cazadas: doble-aviso por paráfrasis [Sol] y no-op por satisfied
genérico [H2]) e identidad. Regla C: el matiz «ordered sin ship» de H1 está STALE (ON en
Railway desde hoy) — la exigencia de codificar la dependencia sigue en pie.

### Cambios de diseño (v2)
1. **Gate pareado del brazo A re-diseñado (Sol-1, mejora)**: A es post-generación pura → el
   pareado congela LOS DRAFTS (capturas OFF reales) y aplica el apéndice determinísticamente
   OFF/ON sobre el MISMO draft — $0 de generación, cero varianza. B (prompt) = gate separado
   con generación.
2. **Vector de flags pineado + dependencia codificada (H1)**: `OBLIGATION_WARNING_APPENDIX`
   exige `OBLIGATION_RESERVE_ORDERED=on` (y RESERVE+MP_CONTRACT) en `validate_release_contract`
   (patrón reserve⇒post_rerank_coverage, release_profiles.py:268). Todos los gates corren con
   el vector de ship (hoy: ambos ON en Railway y en DEMO_FLAGS).
3. **Span anexado = QUOTE ENTERO de la card como átomo sintético (H6)** si ≥1 átomo F-MANDATORY
   detectado en él ∧ el quote pasa `_mandatory_clause_form` — evita fragmentación por-oración y
   el rechazo de good-form sobre cabeceras.
4. **Slot garantizado sin desplazar banked (Sol-3 + H4)**: el átomo de la reserva NO compite en
   `_select_for_appendix` — entra como slot PROPIO (adicional al cap de familia y al cap global),
   espejo del presupuesto-propio que la lane ya tiene en serving. Aserción de sweep: entradas de
   apéndice existentes SIN CAMBIO (solo adiciones) — protege obl_0d6a/hp017 banked (DEC-134).
5. **Cita [Fn] garantizada (Sol-4)**: `meta.fragment_number` del fragmento fuente estampado.
6. **Revalidación fail-closed del receipt (Sol-5)**: antes de anexar, re-verificar id/bounds/
   quote/contenido-padre con el mismo contrato del serving (post_rerank_coverage.py:196-220).
7. **Gates de identidad HEREDADOS (H3, recomendación aceptada)**: el apéndice corre tras el gate
   de identidad y attestation como el pase normal; el coste de radio se MIDE en el sweep
   (columna identity_resolved por gold), no se asume.
8. **Dedup con vara medida (Sol-6 + H2)**: V1b obligatorio — `atom_satisfied(átomo-sintético,
   answer)` sobre las capturas OFF reales donde #4 fue no-conveyed DEBE dar False (dirección
   no-op) y sobre las conveyed DEBE dar True (dirección doble-aviso). Si falla cualquiera, la
   vara del dedup se re-trabaja ANTES de cablear.
9. **Léxico (Sol-2 + H5)**: V1a sobre LOS 18 QUOTES REALES del censo de la reserva (átomos por
   quote); decisión declarada tras el dato: extender triggers del detector SOLO en este path
   (extensión = `_WARNING_EXTRA_TERMS`) o aceptar pérdida de clase con cifra.
10. **G-FP con recibo por-fila pre-registrado (H7)**: yaml {gold, fragment_id, quote,
    section_title, veredicto, ancla-en-fuente}; expectativa honesta hasta ~9 disparos
    (18 golds × ~50% omisión); el control real = tripwire STOP>5 + 0-espurios por-fila.
11. **Atribución de inflación cruzada (H8)**: en el pareado, cada delta per-fact se etiqueta
    cuerpo-vs-solo-apéndice; G-0 invariancia con `MUST_PRESERVE_CONTRACT=on` + appendix off.
12. **Cita DEC-051 corregida (Sol-8)**: B es hipótesis débil por diseño (obediencia), no clase
    zanjada — DEC-098 (fact-level +3/0 SHIP) superseded el veredicto PASS de DEC-051.

### Secuencia de build (gateada)
**V1a+V1b ($0, medidos ANTES de tocar código de producción)** → build v2 flag-off → G-0 →
G-FP (sweep con recibo por-fila + aserción banked) → G-directed pareado-de-drafts → B si A
no convierte. Tallies ts=18:11:38.

### V1 MEDIDO (pre-build, $0 — `s291_l2_v1_probe_result_v1.json`)
- **V1a**: reserva sirve en 20/39 (vector ship); **0-átomos = 3/20** (hp006 cabecera-only ·
  cat001 línea-TOC · cat017 precaución-batería) — TODOS clase precaución/cabecera predicha
  (H5) y TODOS fallan también `_mandatory_clause_form` ⇒ bajo la regla v2 son NO-OP silencioso
  (jamás apéndice basura). Pérdida de radio aceptada con cifra (17/20); léxico del detector NO
  se extiende (la estrictez protege: 2/3 quotes son sirvientes de bajo valor).
- **V1b**: dirección no-op (H2, la letal) = **0/4** ✓; dirección doble (Sol-6) = 1/4
  (paráfrasis conveyed que la vara léxica no ve → apéndice redundante). Para clase SEGURIDAD
  duplicar >> omitir; al recibo G-FP como columna «redundante» separada de «espurio».
- **Adjudicación: BUILD GO** (flag-off, gates v2).
