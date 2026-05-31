# Revisor adversarial — spec

Institucionaliza el "challenge" que hacía Alberto a mano (norma feedback_my_bias: el
sistema NO debe depender del humano como anti-bias). Se invoca **antes de decisiones de
build/commit/diseño de impacto MEDIO o ALTO**. Nació validándose dos veces: (1) en su 1er
uso cazó 5 fallos reales del localizador (2 verificados en código); (2) su propia spec, pasada
por GPT-5.5 cross-model, reveló 6 mejoras conceptuales que el autor (Claude) no vio — ya
incorporadas abajo.

## Disparador del CROSS-MODEL = riesgo de sesgo conceptual, no solo impacto (fix GPT #2)
El sub-agente Claude comparte el sesgo conceptual del autor. Las **zonas de dolor**
(corpus, idiomas ES/EN, legacy, retrieval, esquema del ruler) son justo donde ese sesgo
es peligroso. Por eso el cross-model (GPT-5.5) NO se reserva solo a ALTO:

- **Cross-model GPT-5.5 (`scripts/adversarial_review.py`) + sub-agente Claude** cuando:
  impacto **ALTO** (arquitectura/esquema/contrato/irreversible/seguridad/core), **O**
  impacto **MEDIO en una zona de dolor conocida** (sesgo conceptual probable).
- **Solo sub-agente Claude** (lee el repo, ancla en código): MEDIO fuera de zona de dolor.
- **Juicio internalizado, sin spawn**: BAJO (local, reversible, mecánico).
- **En duda → tier superior.** Criterios de impacto AFILADOS (abajo) para que MEDIO no sea
  "todo" y no degenere en burocracia (tensión GPT #6 — la mitiga la métrica, ver final).

**Criterios de impacto (para que el tier no sea arbitrario):** ALTO = cambia
arquitectura/esquema/contrato, o es caro/imposible de deshacer, o toca seguridad o la
fiabilidad del ruler/RAG. MEDIO = decisión no trivial en componente establecido,
reversible pero con rework real. BAJO = local, trivialmente reversible, sin zona de dolor.

## Instrucciones del revisor (briefing / system prompt)
> Eres un REVISOR ADVERSARIAL. Ataca la propuesta y encuentra dónde (a) viola el contrato,
> (b) repite un fallo documentado, (c) se sobre-ingenieriza.
> - **CALIBRACIÓN (anti-ritual)**: reporta SOLO lo que GENUINAMENTE encuentres, cada
>   hallazgo con **confianza** (alto/medio/especulativo). Concluir "es sólido" es valioso
>   cuando lo es — **NO fabriques preocupaciones** para parecer útil.
> - **EVIDENCIA, calibrada al estadio (fix GPT #1)**: para lo que YA existe, ancla en
>   **código/fichero/línea/doc** y verifica tus claims fuertes contra el código. Para
>   decisiones de **DISEÑO aún sin código**, vale **razonamiento arquitectónico explícito y
>   concreto** (acoplamiento futuro, escalabilidad 30+/ES-EN, contrato mal definido,
>   circularidad) marcado como tal. **NUNCA descartes una objeción conceptual válida por no
>   tener una línea de código** — ese sesgo es en sí un fallo.
> - **ÁRMATE con las fuentes CANÓNICAS (fix GPT #3 — rutas exactas, no "memoria")**:
>   `TECH_DEBT.md`, `docs/RULER_DESIGN.md`, `docs/ADVERSARIAL_REVIEWER.md`, y la memoria del
>   proyecto en `C:\Users\Admin\.claude\projects\C--Users-Admin-OneDrive---fontiber-com-Documents-Claude-Technical-Bot\memory\`
>   (`project_techbot.md`, `feedback_*.md`). Catálogo de fallos: vocabulary mismatch, OCR/
>   7-seg, OEM relabeling, multi-doc, idiomas ES/EN, conflictos, diagram-only, agujeros tipo
>   cobertura-parcial, circularidad, perfeccionismo-de-instrumento, contaminación legacy.
> - **CONTRATO**: BP + estructural (raíz) + escalable + precisión > velocidad + sin
>   quick-fixes + sin sobre-ingeniería + gaps declarados.
> - **NO te ancles** a la justificación del autor (pásate la propuesta, no su defensa).
> - **SALIDA**: hallazgos por severidad, cada uno con confianza + evidencia; o "sólido".

## Normas de uso (mías — van a CLAUDE.md)
- **C. Verificar al revisor**: spot-checkear sus claims FUERTES contra código/fuente antes
  de actuar (Protocolo 1 aplica a su output; no mover el punto único de confianza de mí al
  agente). Las objeciones conceptuales se calibran (¿válida o fabricada?), no se verifican
  contra código.
- **F. Aumenta, no reemplaza**: yo decido y soy responsable. No rubber-stamp.

## Métrica operativa del guardarraíl anti-ritual (fix GPT #4)
El guardarraíl no puede ser declarativo. Tally ligero por revisión (en un log simple):
`#hallazgos`, `#confirmados` (los que verifiqué ciertos), `#falsos-positivos`, severidad
media, coste (tokens/tiempo). Señales de matar/revisar:
- **confirmed-rate → ~0** (siempre "alineado, sin issues") = ritual-SÍ.
- **falsos-positivos altos** (fabrica trivialidades) = ritual-NO.
- coste/fricción > valor de los hallazgos confirmados.
Se gana su sitio con datos, no por fe (eval-driven, como todo lo demás).

## Cross-model — dependencia (fix GPT #5)
Data-flow ya **aceptado** en el proyecto (GPT-5.5 es el juez del eval; el mismo OPENAI_API_KEY).
`scripts/adversarial_review.py` fija el prompt; modelo vía `ADVERSARIAL_MODEL` (default
gpt-5.5). **Fallback**: si GPT no está disponible, el suelo es sub-agente Claude + mi
verificación, y se **marca explícitamente "cross-model omitido"** (no se finge que se hizo).
