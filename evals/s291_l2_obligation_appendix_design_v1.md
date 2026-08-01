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
