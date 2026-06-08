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
**El briefing operativo vive en `scripts/adversarial_briefing.md` (fuente ÚNICA).** Lo lee el
script cross-model y lo cita el sub-agente Claude. Antes había una copia aquí y otra, más
pobre, en el script: divergieron — el cross-model (el que MENOS conoce el dominio) recibía el
prompt más flaco, sin el catálogo de fallos. Re-anclarlo a un fichero único es la corrección
de raíz; este doc ya NO lo duplica, solo explica el porqué.

Cubre: calibración anti-ritual · **sesgo conocido del autor** (over-claim de FRAMING, no de
valores → atacar ahí primero) · evidencia calibrada al estadio (código→`fichero:línea`;
diseño→`[CONCEPTUAL]`) · catálogo de fallos del dominio · fuentes canónicas · el contrato ·
**formato de salida anclado** (cada hallazgo cita `fichero:línea` | cita | `CONCEPTUAL`, para
que aplicar la regla C —verificación humana, que sigo haciendo yo— sea directo y uniforme, no
"mecánico": el script NO valida el formato ni auto-rellena el veredicto).

## Normas de uso (mías — van a CLAUDE.md)
- **C. Verificar al revisor**: spot-checkear sus claims FUERTES contra código/fuente antes
  de actuar (Protocolo 1 aplica a su output; no mover el punto único de confianza de mí al
  agente). Las objeciones conceptuales se calibran (¿válida o fabricada?), no se verifican
  contra código.
- **F. Aumenta, no reemplaza**: yo decido y soy responsable. No rubber-stamp.

## Métrica operativa del guardarraíl anti-ritual (fix GPT #4)
El guardarraíl no puede ser declarativo. Log real: **`evals/adversarial_review_log.jsonl`** —
el script escribe una entrada parcial por revisión con el coste AUTO-capturado (`tokens`,
`elapsed_s`); yo completo a mano los campos de JUICIO tras verificar (`findings`, `confirmed`,
`false_pos`, `severity_max`, `verdict_notes`). Señales de matar/revisar:
- **confirmed-rate → ~0** (siempre "alineado, sin issues") = ritual-SÍ.
- **falsos-positivos altos** (fabrica trivialidades) = ritual-NO.
- coste/fricción > valor de los hallazgos confirmados.
Se gana su sitio con datos, no por fe (eval-driven, como todo lo demás).

## Cross-model — dependencia (fix GPT #5)
Data-flow ya **aceptado** en el proyecto (GPT-5.5 es el juez del eval; el mismo OPENAI_API_KEY).
`scripts/adversarial_review.py` lee el prompt de `adversarial_briefing.md`; modelo vía
`ADVERSARIAL_MODEL` (default gpt-5.5); **`--diff`** auto-incluye `git diff HEAD` para no
depender de que yo elija bien el contexto (sesgo de selección). **Fallback**: si GPT no está
disponible, el suelo es sub-agente Claude + mi verificación, y se **marca explícitamente
"cross-model omitido"** (no se finge que se hizo).

## Simetría de información: pasarle las FUENTES al cross-model (s52/DEC-028)
El sub-agente Claude **lee el repo**; el cross-model **solo ve lo que se le pasa** (no navega). Para
que no quede en desventaja conceptual NI factual frente al sub-agente, en gates de **selección/diseño**
hay que **pasarle explícitamente las fuentes que debe VERIFICAR** —no solo la propuesta—:

```
python scripts/adversarial_review.py propuesta.md data/model_catalog.json <extractos>
```

(p.ej. `data/model_catalog.json` para existencia de productos; extractos del gold YAML para no-duplicado.)
`--diff` cubre los ficheros **tracked-cambiados** pero NO las fuentes no-cambiadas (el catálogo) → en un
gate de **selección** (donde aún nada ha cambiado) hay que pasarlas a mano. **Síntoma de que faltó
(s52b):** el cross-model dijo *"no puedo validar existencia desde la propuesta"* mientras el sub-agente
(con repo) sí → asimetría re-introducida por infra-alimentar al cross-model. Límite práctico: el gold
YAML entero es grande (~77k tokens) → pasar **extractos relevantes**, no el fichero completo. Es la
realización s47 ("cross-model-con-fuentes") hecha REGLA, no discrecional.
