# Plan s42 — a batir adversarialmente (Protocolo 3) ANTES de comprometer el rumbo

> Impacto ALTO (decide el rumbo + zona de dolor: autoría de golds, localización, conductas).
> El backlog heredado de s41 dice "modo-ausencia en locate_fact + autorar #16/#18/#19 + re-formular
> hp006". Antes de ejecutarlo lo someto a la **Pregunta cero**: ¿es esto lo de mayor leverage, o es
> seguir un backlog por inercia? Atacad sobre todo §1 (la tensión), no deis por bueno el backlog.

## 0. Dónde estamos (post-s41, verificado)
- Árbitro endurecido: eje NO-FABRICACIÓN + C1 (DEC-012). Re-baseline fresco post-AC220 (HyDE-off,
  `--llm --prose-llm`): **7 FALLO / 10 PARCIAL / 2 REVISAR / 0 PASS** (19). El bot NO tiene problema
  de PASS, tiene fabricación en matrices/parámetros (hp005/11/13 contradicen) + síntesis multi-doc
  incompleta (cat001) + 2 conductas cruzadas (hp004/18 clarify↔answer).
- **El eje NO-FABRICACIÓN NO está validado sobre golds de conducta reales (n=0)**; el spot-check de
  hp006 reveló 1 FP (hecho ausente-probado mal formulado). Gap (c) de DEC-012.
- DEC-005: tras 4 intentos, **NO hay lever de RETRIEVAL recomendado** (ninguno movió calidad
  end-to-end). El lever de GENERACIÓN/prompt (Fase 4 / D9: bloque BEHAVIOR_POLICY anti-fabricación)
  NO se ha probado contra el árbitro.
- INTERLEAVE (RULER_DESIGN §4): "construir el ruler fiable-lo-suficiente → TIRAR DEL LEVER que señale
  → demostrar mejora de producto → y ENTONCES seguir creciendo el ruler". Llevamos s34–s41 puliendo
  el árbitro sin tirar de ningún lever de producto.

## 1. PREGUNTA CERO — ¿qué es s42? (la decisión de mayor impacto)
Tres encuadres posibles, NO excluyentes:
- **(A) Backlog literal**: autorar conductas #16/#18/#19 por cobertura de taxonomía (DEC-003).
  *Riesgo*: cobertura-por-cobertura; el árbitro se sigue puliendo sin demostrar mejora de PRODUCTO
  (viola INTERLEAVE); fast-convergence por inercia del backlog.
- **(B) Tirar de un lever YA** (el árbitro está endurecido): lever de generación anti-fabricación,
  medido con el eje no-fabricación recién construido — el diagnóstico (hp005/11/13 + cat001) lo
  señala. *Riesgo*: el eje no-fabricación AÚN NO está validado (n=0) → medir un lever con un
  instrumento sin validar repite el error "medir contra gold roto" (s30).
- **(C) Síntesis (mi recomendación tentativa)**: s42 = **autorar las conductas MÍNIMAS para VALIDAR
  el eje no-fabricación (cerrar n=0 + el spot-check), como PRERREQUISITO del lever** anti-fabricación
  que el diagnóstico ya señala. La autoría deja de ser un fin (cobertura) y pasa a ser el paso que
  desbloquea el lever. Orden: validar el eje (pocas celdas) → tirar del lever de generación → medir
  delta contra el baseline fresco de s41.
**Pregunta al dúo**: ¿(C) es el encuadre correcto, o estoy racionalizando el backlog? ¿Bastan 2–3
golds de conducta para "validar" el eje, o es autoengaño con n pequeño? ¿El lever anti-fabricación
es el de mayor señal, o lo es la síntesis multi-doc / la conducta clarify (hp004/18)?

## 2. Modo-ausencia en `locate_fact` (greenfield — el dúo de s41 lo confirmó NO-reutilización)
Diseño propuesto: input = producto + términos del tema (sin valor) + manuales (autor). Pipeline negativo:
1. grep términos ES+EN en todos los manuales; clasificar digital/scan (`_scan_ratio`/`is_scan` ya existen).
2. **digital-native**: grep=0 → ausencia FIABLE en ese manual; grep>0 → render-verificar si el predicado del tema está.
3. **scan**: grep no fiable (regla de scans) → render-verificar páginas relevantes; si no se puede localizar → `needs_human`.
4. Veredicto: `absence_supported` SOLO si todos los digital-native no cubren el tema Y los scans se
   render-verificaron; si algún scan no verificable → `needs_human`. Naming honesto (NO `absence_proven`).
**Talón de Aquiles (lo declaro)**: probar ausencia en un SCAN es casi irresoluble robustamente (¿qué
páginas renderizar si grep=0 en 100pp?). → el modo-ausencia FIABLE solo afirma ausencia sobre
productos con manuales relevantes TODOS digital-native; con un scan en el set, la celda cae a
`needs_human`. Es una restricción de SELECCIÓN, no un fix. **Pregunta al dúo**: ¿esto deja autorables
suficientes celdas, o casi todo #16/#18 caerá a needs_human (haciendo s42 inviable)?

## 3. Selección de celdas + orden propuesto
- **#19 clarify PRIMERO** (no necesita modo-ausencia; el gate clarify ya existe): familia ambigua
  (p.ej. CAD-150-4/8/X) → valida el pipeline de autoría + el flujo end-to-end barato.
- **Construir el modo-ausencia** (§2).
- **#16 admit**: producto DIGITAL-NATIVE + tema genuinamente ausente (un detalle plausible que el
  manual no cubre). Reto: "buscar lo que no está" — se parte de una pregunta de técnico realista.
- **#18 refuse-inference**: par de ecosistemas DISJUNTOS verificado contra `_ECOSYSTEM_OF`
  (Notifier↔Morley = ambas Honeywell distintas, caso `cm001`; o Notifier↔Detnov). NO Detnov↔Securiton.
- **Validación del eje** (la pre-condición del dúo): correr el árbitro sobre las celdas autoradas +
  spot-check del eje no-fabricación (recall/especificidad sobre golds reales) → cierra gap (c) DEC-012.

## 4. Re-formular hp006 (menor)
El hecho `ausente-probado` debe ser quirúrgico: SOLO "no hay procedimiento de localización paso a
paso", sin la nota parentética sobre MFDT170 (que induce el FP, porque MIDT170 sí cubre el aviso).
Vía `gold_store.upsert`. Cuidado: toca un gold verificado → re-verificar que no rompe el baseline.

## 5. Riesgos/gaps declarados
- (a) Si la autoría de #16/#18 cae mayoritariamente a `needs_human` (scans / universo cross-brand
  amplio), s42 no produce golds → el eje sigue sin validar (el objetivo principal falla). Plan B: ¿basta #19 + 1 admit digital-native?
- (b) Validar un eje LLM con n=2–3 es señal débil (mismo caveat que todo el ruler: diagnóstico, no gate).
- (c) Re-formular hp006 cambia el ruler → re-baseline para confirmar no-regresión.
- (d) El lever de generación (si se tira en s42) NO es behavior-neutral (D9) → eval-validado, riesgo de regresión sutil; y toca PRODUCCIÓN (a diferencia de s40/s41 eval-only).

## 6. Qué quiero del dúo
1. **§1 (lo crítico)**: ¿(C) es BP o racionalización del backlog? ¿El leverage real está en autoría
   de conductas, o en tirar ya de un lever (cuál: generación anti-fabricación / síntesis / clarify)?
2. ¿El modo-ausencia es viable o su talón de Aquiles (scans) lo hace producir solo needs_human?
3. ¿La selección de celdas/pares es correcta (disjuntos, digital-native)? ¿Algún fallo de dominio?
4. ¿Re-formular hp006 es seguro, o hay un riesgo que no veo?
