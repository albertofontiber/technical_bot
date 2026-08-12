# s318/#71 — Frame `legal_disclaimer` en el evidence_contract (flag-gated, adjudicación DEC-148)

## El defecto (TECH_DEBT #71, observado en producción)

El apéndice «Obligaciones de evidencia del manual» citó el párrafo de
responsabilidad legal de KGS Fire & Security (bcn-3100017 p.4, «no se hará
responsable en ningún caso…») como si fuera una obligación técnica. Mecanismo
confirmado: el boilerplate legal lleva **cuantificador universal** («en ningún
caso») y vocabulario de obligación — exactamente lo que la ruta de obligaciones
universales busca.

## Población (censo s318, recibo `s318_disclaimer_census_v1.json`)

**108 documentos / 119 chunks** del corpus activo llevan boilerplate de la clase
RESPONSABILIDAD (~10% de 1.069) — es clase, no anécdota. Casi todos 1 chunk (la
página legal).

## El fix

Frame nuevo `legal_disclaimer` en la familia `_universal_frame_skip` (la que ya
salta capability/conditional/definition/example — encaje estructural, no aparato
nuevo): `_LEGAL_DISCLAIMER_RX` sobre texto folded, clase RESPONSABILIDAD
bilingüe ES/EN/PT. **Flag `EC_LEGAL_DISCLAIMER_SKIP` default OFF byte-idéntico**
(aparato PROTEGIDO — DEC-148: la exclusión solo se enciende con adjudicación de
Alberto). Versión de léxico EFECTIVA en el recibo (`v2` off / `v3_legal_disclaimer`
on — un recibo v3 con el frame apagado mentiría).

## Precisión (el daño de un falso skip es PERDER una obligación real)

- «in no event» SOLO con contexto de responsabilidad (≤80 chars de liab/responsib):
  «in no event should the loop current exceed 500 mA» NO matchea (test).
- «el técnico responsable de la instalación debe…» NO matchea (sin negación de
  exención; test).
- **Clase GARANTÍA FUERA a conciencia**: «la garantía se anula si se abre la
  carcasa» carga contenido operativo útil — límite declarado, no olvido.
- Tests: 13 (KGS on/off, 8 variantes de la clase, 5 negativos de precisión,
  frames v2 invariantes bajo el flag).

## Sonda dirigida (recibo `s318_disclaimer_probe_v1.json`)

Las **129 frases EXACTAS** (98/108 docs; 10 residuales del censo sin frase
segmentada, declarados) que el frame saltaría con el flag ON, por documento —
la adjudicación se hace VIENDO lo que desaparece. Muestra: Spectrex «no asume
ninguna responsabilidad a causa de omisiones…», Notifier «no será responsable
ante usted ni cualquier otra persona…».

## Qué NO hace

- No toca la detección de callouts `safety_mandatory` (ruta determinista de
  advertencias): el defecto observado entró por la ruta de obligaciones
  universales; si la clase reapareciera por otra ruta, es evidencia nueva.
- No re-litiga el léxico v2 (tests de invariancia).
- No se enciende: el ON viaja en la sentada de adjudicación de Alberto
  (B2 + DP312x + esto).

## Gaps declarados

- EN «in no event shall…» con la parte liable a >80 chars no matchearía
  (precisión-primero: preferimos un disclaimer colado a una obligación perdida).
- Rama PT: 0 documentos en el censo — cobertura DEFENSIVA declarada (Fable r16
  F3), no validada por población.
- La pregunta-oráculo de la sonda v2 es cota de MÁXIMA aplicabilidad: en
  producción una pregunta real admite menos — 83 es techo, no tasa.

## Estado tras el dúo r16 (Sol 5 · Fable 4, 0 FP) — TODO APLICADO

- **Sol C1 (crítico): la sonda v1 medía el REGEX, no el contrato** — «129
  frases EXACTAS que desaparecerían» era falso (el camino real exige
  cuantificador+compuesto+forma+aplicabilidad ANTES del frame; y la sonda
  truncaba a 400 chars). → **Sonda v2** (`s318_disclaimer_probe_v2.json`):
  ejecuta `_universal_obligations` (la función gateada real) con
  pregunta-oráculo de máxima aplicabilidad (patrón DEC-173), sin truncar:
  **83 obligaciones legales removidas en 70 docs ACTIVOS (de 105)** —
  la cifra de adjudicación es esta, no las 129 del RX.
- **Sol C2 (crítico): «mixta no observada» se contradecía con mi propia
  sonda** → sección MIXTAS del recibo v2: **28 removidas llevan deber
  operativo embebido** (instalar/usar/mantener «conforme al manual») —
  listadas verbatim para la adjudicación; su contenido operativo es genérico
  (remiten al manual, sin payload numérico), pero lo decide Alberto viendo.
- **Sol M3: «los 10 residuales los cubriría el runtime» era FALSO** — el RX v1
  no incluía «en ningún caso será responsable» ni «no liability» → añadidos
  con guarda, con tests de las variantes del censo.
- **Sol M4: los tests no conducían el camino protegido** →
  `test_camino_real_universal_obligations_kgs_off_on`: la cláusula Notifier
  REAL entra como obligación con OFF (defecto vivo), desaparece con ON, y la
  obligación técnica de control es INVARIANTE. **Invariante poblacional
  (sonda v2): 0 obligaciones no-legales cambiadas en los 105 docs.**
- **Sol M5 ≡ Fable F4: denominador sin filtro de activos** → sonda v2 solo
  activos: 105/108 (3 del censo v1 no están activos); la prevalencia honesta
  es 105 docs activos con boilerplate, la tasa sobre el total la estampará
  el censo v2 si se necesita — el «~10%» de la v1 queda RETIRADO.
- **Fable F1 (medio, la reserva del SÓLIDO): guarda ES ausente** — «el módulo
  no es responsable de generar la alarma» es arquitectura real que el v1 se
  comía → guarda de contexto de exención SIMÉTRICA en ES (≤90 chars de
  daños/pérdidas/uso indebido/…), con 2 tests negativos nuevos; las formas
  fuertes («declina toda responsabilidad») quedan sin guarda a conciencia.
- **Fable F2: «Tests: 13» era 16** → recuento retirado de la prosa; la cifra
  la da la suite (24 tras r16).
- **Fable F3: rama PT especulativa** → declarada defensiva (0 en censo).
