# Framing de s45 — propuesta a atacar (Protocolo 3, dúo). Autor = Claude.

> **⚠️ CORREGIDO POST-DÚO (5 jun, NO-SÓLIDO → la versión CANÓNICA vive en `PLAN_RAG_2026.md` bloque "PRÓXIMO s45").** El dúo cazó 2 conflaciones load-bearing en la propuesta de abajo: **(1)** la (2) pre-suponía un "lever de completitud-SÍNTESIS" que s44 deprioritizó POR MEDICIÓN (DEC-018d), citando diagnosis pre-s44 → corregido: **gate puro, el lever sale del triage, definido estructuralmente, NO pre-nombrado**; **(2)** hp006 (recall-miss) iba bundleado con completitud → es item propio (corpus/term-exacto). Además: (0) HyDE-off + cap-rerank = MEDICIÓN real (re-medir en el path retrieve-wide; A/B cap-rerank vs ganancias s44), no "fleco"; el `--prose-llm` debe anclarse EN FUENTE (anti-circularidad). El esqueleto (F1→F2, triage-first, Track-B interleave, A/B 2-ejes) = SÓLIDO. **El texto de abajo es la versión PRE-corrección (referencia histórica del input del dúo).**

> Te llega la propuesta RECONCILIADA con el PLAN canónico, no su defensa. Ataca contrato / fallo-conocido / sobre-ingeniería / desalineamiento con el PLAN.

## Contexto (estado tras s44, verificado)
- Estamos en **Fase 1 (calidad estructural: retrieval+extracción)** del PLAN de 5 fases. Orden canónico: F1 (calidad) ANTES que F2 (escala).
- **s44 shipped retrieve-wide** (`RETRIEVAL_TOP_K` 15→50, DEC-018): **FALLO ~6→1 medido K=3**. Cerró los FALLO del bulto (los peligrosos). Descartó por medición: borrar-cruft (#32) y "síntesis Track D" (los casos eran retrieval-contexto).
- **Residual de F1 = los 14 PARCIAL** (incompletas, no incorrectas) + hp006 (recall-miss de corpus) + flecos (HyDE-off, latencia 15-39s).
- **Diagnóstico canónico previo (s39-40, DEC-010/011):** `cat001 2/7 = "síntesis incompleta real"` (omite hechos cross-doc) → "el cuello multi-doc = completitud de SÍNTESIS, no retrieval ni alucinación". Consistente con DEC-005/006.
- **Caveat (#35/DEC-006):** los PARCIAL son un SUELO — el matcher-prosa frágil (sin `--prose-llm`) under-cuenta completitud → algún "PARCIAL" podría ser PASS.
- Contexto negocio: bot SIN usuarios reales (meses), M&A due-diligence. Fase 2 = "antes del fabricante ~5".

## Propuesta s45 (reconciliada con el PLAN)
- **(0) Consolidar F1 (barato, flecos):** confirmar HyDE-off (latencia+determinismo; #32:1250 lo midió no-ayuda en s29) + cap-rerank-~30 (latencia + mitiga la regresión hp013).
- **(1) Triage de los 14 PARCIAL** en el path de producción (= s35-orden-paso-1, ahora maduro tras cerrar FALLO): clasificar retrieval-residual / síntesis-omisión / gold-demasiado-estricto. **CON `--prose-llm`** (por el caveat #35-suelo). Es el GATE — no asumir la causa (lección s44: mis asunciones retrieval-vs-síntesis estaban mal).
- **(2) Lever de COMPLETITUD-SÍNTESIS si el triage lo confirma** (el cuello de cat001/DEC-005/006). Riesgo declarado: generación tiene mal historial (DEC-001 change-1 direccional pero change-2 revertido) → A/B K-mayoría DOS EJES (completitud ↑ SIN invención ↑).
- **Track B (breadth-baseline del eval: Spectrex/conductas) = INTERLEAVE** (Capa 1, anti-regresión), no pivote.
- **F2 (escala-prep) NO se adelanta** — sigue después de F1.

## La pregunta estrecha (el fork real, de Alberto)
¿El residual PARCIAL/completitud merece un lever de CIERRE de F1, o se declara F1 "suficiente para la fase sin-usuarios" (FALLO cerrado) y se pasa a F2 (escala-prep, "antes del fabricante ~5")?

## Claims LOAD-BEARING (atácalos)
- **C1:** ¿es PARCIAL el residual correcto a perseguir, o es en parte SUELO-de-medición (#35 prosa-frágil) → el triage con `--prose-llm` podría disolver varios PARCIAL en PASS (como pasó con cat005 6/6 en DEC-011)? Si así, el "lever" podría ser innecesario.
- **C2:** ¿un lever de completitud-síntesis repetirá change-1/change-2 (DEC-001, generación net-negativa)? ¿El A/B de dos ejes basta para no subir invención?
- **C3:** ¿"F1 antes que F2" sigue válido, o retrieve-wide cerró F1 lo bastante (FALLO=0 funcional) para justificar pasar a F2 (escala-prep) ya — dado due-diligence + sin usuarios?
- **C4:** ¿el triage-first es measure-first legítimo, o es otra vuelta de "afinar el instrumento" (la queja de fondo de Alberto s35-42)? ¿Dónde está la línea?
- **C5:** ¿hp006 (recall-miss) + Track B (breadth eval) deberían adelantarse/agruparse, o son ruido para s45?

## Contrato
BP + estructural (raíz) + escalable (30+ fab, ES/EN) + precisión>velocidad + sin sobre-ingeniería + alineado con el PLAN canónico + todos los gaps declarados.
