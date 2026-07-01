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

## Simetría de información — RESUELTA DE RAÍZ en s88 (pedido de Alberto; cierra TECH_DEBT #36)
**Desde s88 el cross-model LEE EL REPO él mismo:** `adversarial_review.py` corre un loop agéntico
(OpenAI function-calling) con tools **READ-ONLY** sandboxeadas al repo:
- `read_file(path, start_line, max_lines)` — con números de línea (anclas `fichero:línea`).
- `grep_repo(pattern, glob, max_hits)` — regex sobre el repo.
- `list_dir(path)`.
- **Deny-list:** `.env*` (secretos), `.git/` y dirs internos, y el **propio log de tally**
  (anti-contaminación). Sandbox: paths resueltos bajo la raíz (no traversal).
- **Cap 30 tool-calls** (disciplina de coste); al agotarlo se fuerza la review con lo leído.
  `--no-tools` restaura el modo legacy (pegado) como escape. `--diff` se mantiene.
- El tally registra `tool_calls` + `files_read` (auditable qué miró).
**Invariante preservado (el activo del cross-model):** ve el artefacto por lente no-Claude + su
salida se lee CRUDA — NO anidado en el sub-agente. **Smoke (s88):** con 2 claims falsas plantadas
(umbral 0.5; reranker voyage-en-prod) las cazó AMBAS leyendo el código (14 tool-calls; anclas
`generator.py:342-343`, `config.py:56-64`).

*Histórico (s52/DEC-028, superado):* antes el cross-model solo veía lo pegado → la regla era pasarle
las fuentes a mano (extractos, catálogo) y `--diff`; el síntoma s52b ("no puedo validar existencia
desde la propuesta") era la asimetría. Pasar ficheros como CONTEXTO sigue siendo útil como punto de
partida (ahorra tool-calls), pero ya no es el techo de lo que el revisor puede ver.

## Modelos del dúo (s88)
Sub-agente: pin `model: fable` (Fable 5; Alberto s88 — antes `opus` s73→s88) = MISMO árbol que el
autor → en ALTO/zona-de-dolor el cross-model GPT-5.5 es INNEGOCIABLE. Cross-model: `ADVERSARIAL_MODEL`
(default gpt-5.5), ahora con las mismas capacidades de lectura que el sub-agente.
