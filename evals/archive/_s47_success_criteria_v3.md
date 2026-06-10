# Propuesta s47 v3 — Rumbo estructural: criterios de EXCELENCIA + base escalable

## Qué es esto
Output de una revisión estructural (Alberto + Claude). Consolida y **corrige** la v1 de
criterios tras dos rondas de dúo + el pushback de Alberto. Define: (A) qué es "suficiente",
(B) cuándo se shipea un lever, (C) cómo crece el eval, (D) cómo se cierra el ruido del juez,
(E) el contrato de identidad para escala, (F) la secuencia, (G) el dúo, (H) consolidación de
docs. Impacto **ALTO en zona de dolor** (método del ruler + corpus + escala) → dúo dual.

## Restricciones decididas por MEDICIÓN (un criterio que las contradiga es un error)
- Ruler diagnóstico, no gate estadístico de CI (DEC-003 / `RULER_DESIGN §0`) — PERO ver §C: el
  "no-N" se reabre por metas nuevas (held-out + señal), sin convertirlo en gate de CI.
- "Recall no convierte" (`TECH_DEBT:1246`, DEC-018/020 — NO DEC-005, que es s36/funnel).
- Síntesis-genuina ≈ 0 (DEC-020): con el chunk en top-5 el bot lo usa.
- retrieve-wide cerró los FALLO peligrosos (DEC-018, FALLO ~6→1).
- Juez ruidoso (#37) + prosa-frágil (#35) → §D lo CIERRA, no solo lo tolera.
- Eje no-fabricación / asimetría de seguridad (DEC-012): afirmar hecho ausente-probado = FALLO.
- **chunks_v2 ya es LlamaParse-multimodal EJECUTADO** (`PLAN:174`, `TECH_DEBT:1241`) → la
  extracción NO es un lever fácil; lo que el multimodal pierde (7-seg) es cola dura (tarea #10).
- Sin usuarios (M&A due-diligence) → no CI estadístico; pero SÍ base escalable (la tesis = 30+).

## §A — DoD F1: EXCELENCIA + seguridad (NO solo "no-daño")
Corrige el error de la v1 (un DoD de solo-no-fallo produce un bot mediocre-pero-seguro). F1 es
suficiente cuando, sobre el held-out:
1. **POSITIVO (excelencia)**: completitud de hechos `core` — el bot surfacea los hechos atómicos
   core que el corpus soporta, bien citados. Es "la mejor respuesta que el corpus permite", no
   "no inventó". Medible con `atomic_scorer` (ya separa completitud).
2. **SEGURIDAD**: 0 FALLO-peligroso **MEDIDO** (eje factual + no-fabricación). Criterio NUEVO a
   correr (no medido aún post-retrieve-wide con los dos ejes), no "consolidado".
3. Cada FALLO no-peligroso restante: causa clasificada + decisión (atacar / diferir-con-razón).
Validación = §D (determinista + dual-judge). El humano (no-experto, supervisa el proceso)
spot-chequea SOLO los flags — excepción, no gate (estado `needs_human`). Sin %PASS de CI.

## §B — Ship-criterion de un lever (incluida la zona gris)
Shipea SÓLO si: mueve **veredictos** O **mejora por severidad/eje** (peligroso→benigno cuenta) ·
2 ejes (completitud↑ SIN invención↑, DEC-001) · delta > ruido (regla numérica: neto fuera del
conjunto inestable conocido hp001/02/10/20; dual-judge) · no-regresión (diagramas/wiring + PASS) ·
coste/latencia declarados.
**Zona gris** (no-daño pero mecanismo claramente mejor): shipea sin delta medido SÓLO si
(estructural/relevante-a-escala O cierra riesgo conocido) Y (sin complejidad material) Y
(no-regresión). Si añade complejidad sin ganancia ni relevancia de escala → no (default a lo simple).

## §C — Expandir el eval (señal-por-lever + held-out)
Reabre DEC-003 "no-N": correcto a n=19/diagnóstico; las metas nuevas (held-out + distinguir un
lever del ruido) lo justifican. NO es gate de CI.
- **Target DERIVADO, no decretado**: matriz de taxonomía (fabricante × tipo-doc × idioma ES/EN ×
  modalidad × conducta) × **3-5 por celda activa** → ~**60-100 total ahora** (dev ~45-70 /
  held-out ~20-30; held-out <20 no es fiable, de ahí el suelo). Crece con fabricantes (~150). **NO
  miles** (escala de training/potencia estadística; overkill sin usuarios; cada gold cuesta C4).
- **Split dev/held-out**: levers se tunean SÓLO en dev; el held-out NUNCA se tunea ni se inspecciona
  durante el desarrollo del lever (embargo) → única medida honesta de generalización.
- **Aislamiento (fix infra de la v1)**: golds nuevos en estado no-verificado (`cuarentena`/
  `pendiente`) → el gate `test_bot_vs_gold.py:138` los excluye del A/B con infra que YA existe. NO
  se inventa campo `slice`.
- **Freeze-contract**: el A/B de un lever congela corpus + índice + embeddings + juez + config, no
  solo los golds.
- **Industrializar la autoría** (requisito de "sustancial"): pipeline sintético source-verified
  (`CATALOG_PLAN`: co-gen Claude+GPT-5.5 + doble-lectura + dúo C3 + regla C). Front-load que hace
  BARATO añadir golds por fabricante = enabler de escala. NO relaja el source-anchoring.

## §D — Cerrar el ruido del juez (BP junio-2026, estructural)
No "juez perfecto"; **encoger la superficie ruidosa** + mandar al humano solo la ambigüedad genuina:
1. **Determinista** para hechos duros (números/códigos/IDs): matcher `anchor_present` (ya existe,
   F0) — cero ruido LLM. El gold ya tiene `valor` por hecho.
2. **Dual-judge** para el residual cualitativo (Claude + GPT-5.5): acuerdo = fiable; solo los
   DESACUERDOS → spot-check humano. El ruido #37 se manifiesta como desacuerdo → se caza.
3. Decomposed (`atomic_scorer`) + `response_format` (ya, DEC-015) matan el ruido de formato.
Baja la carga manual de Alberto a lo genuinamente ambiguo. Límite honesto: no hace omnisciente al
juez en matiz de prosa; acota el ruido.

## §E — Contrato de identidad de producto (escala) — APUESTA ANTICIPATORIA declarada
hp002 es el canario (un chunk Notifier se coló en una respuesta Detnov; `TECH_DEBT #11f`
parcialmente resuelto). Lever = derivar identidad por chunk (fabricante + product_model +
ecosistema) **EN INGESTA, desde datos/catálogo**, reemplazando el `MODEL_PATTERN` hardcodeado
(`PLAN §2.4`: 50 líneas/3 fabricantes → 500/30) + conducta **admit-on-empty** (no inventar al
quedarse sin material del fabricante correcto). DEBE ser industrializable (añadir fabricante = un
comando, no un script).
**Banderas honestas**: (1) es trabajo de **F3/escala traído adelante** — pivote CONSCIENTE (tesis
M&A = el valor son los 30+), no deriva accidental; (2) **NO es eval-driven** (no hay corpus de 30
marcas → el eval actual no puede surfacear la contaminación de escala) → apuesta estructural sobre
**principio + canario**; disciplina: timeboxear, no gold-platear, validar cuando lleguen fabricantes.

## §F — Secuencia (respeta el freeze-contract)
Expandir golds sobre corpus existente NO toca el índice → **paralelo-seguro**.
contextual-retrieval / identidad / extracción SÍ tocan el índice → **serializar**.
1. Industrializar autoría + expandir el eval (paralelo-seguro) →
2. Medir **contextual-retrieval** sobre el eval grande (medir sobre 22 desperdicia la medición) →
3. **Identidad-contrato** (serializado; escala) →
   Extracción hp011 **deprioritizada** (nicho/duro; multimodal ya ejecutado).

## §G — Dúo (mejorado)
Lentes diversas + **acceso compartido a verificar** (no inputs idénticos: la diversidad viene del
modelo+lente, no de inanizar inputs). Cross-model con ficheros fuente (piloto en ESTA review;
Codex si no basta). Briefing ya editado: check de "consolidación/ya-existe" + freeze-contract +
apuesta-anticipatoria al catálogo.

## §H — Consolidar PLAN/DECISIONS (acotado)
Condensar el bloque de estado (~180 líneas de log sesión-a-sesión → current-state nítido + mover el
log a un fichero de historia), reconciliar la numeración dual (Fase 0-5 macro vs F0-F3 micro). Para
que el doc se lea en frío (su audiencia declarada).

## Encargo al revisor (REFUTA, no confirmes)
1. ¿**~60-100** es el número correcto, o sobra/falta? ¿La derivación (ruido ~18% + held-out ≥20)
   aguanta, o es un número anclado?
2. ¿El bar de excelencia §A es medible con `atomic_scorer.py` TAL CUAL, o requiere instrumentación
   nueva no declarada? **Verifícalo en código.**
3. ¿El **dual-judge** §D cierra ruido de verdad, o solo añade coste y otra capa de ruido? ¿"Acuerdo
   de dos modelos" es señal o consenso-falso (ambos pueden equivocarse igual)?
4. ¿Traer **F3/identidad** adelante (§E) es el pivote correcto o scope-creep? ¿La apuesta
   anticipatoria está bien declarada, o es "construir sin medir" que lamentaremos?
5. ¿La **secuencia** §F respeta de verdad el freeze-contract? ¿Hay una vía de contaminación que se
   escapa (p.ej. el dual-judge cambia el juez a mitad de A/B)?
6. ¿Over-claims de framing del autor? ¿Esto es estructural + escalable, o perfeccionismo / ritual?
