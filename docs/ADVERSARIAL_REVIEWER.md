# Revisor adversarial — spec

Institucionaliza el "challenge" que hacía Alberto a mano (norma feedback_my_bias: el
sistema NO debe depender del humano como anti-bias). Se invoca **antes de decisiones de
build/commit/diseño de impacto MEDIO o ALTO**. Nació validándose dos veces: (1) en su 1er
uso cazó 5 fallos reales del localizador (2 verificados en código); (2) su propia spec, pasada
por GPT-5.5 cross-model, reveló 6 mejoras conceptuales que el autor (Claude) no vio — ya
incorporadas abajo.

## Disparador del dúo frontera = riesgo de sesgo conceptual, no solo impacto (fix GPT #2)
Una sola familia de modelos puede compartir el sesgo conceptual del autor. Las **zonas de dolor**
(corpus, idiomas ES/EN, legacy, retrieval, esquema del ruler) son justo donde ese sesgo
es peligroso. Por eso el dúo frontera NO se reserva solo a ALTO:

- **GPT-5.6 Sol xhigh como revisor principal (`scripts/adversarial_review.py`) + Fable 5
  como segundo revisor frontera ejecutado de forma independiente** cuando:
  impacto **ALTO** (arquitectura/esquema/contrato/irreversible/seguridad/core), **O**
  impacto **MEDIO en una zona de dolor conocida** (sesgo conceptual probable).
- **Fable 5** (lee el repo, ancla en código): MEDIO fuera de zona de dolor.
- **Juicio internalizado, sin spawn**: BAJO (local, reversible, mecánico).
- **En duda → tier superior.** Criterios de impacto AFILADOS (abajo) para que MEDIO no sea
  "todo" y no degenere en burocracia (tensión GPT #6 — la mitiga la métrica, ver final).

**Criterios de impacto (para que el tier no sea arbitrario):** ALTO = cambia
arquitectura/esquema/contrato, o es caro/imposible de deshacer, o toca seguridad o la
fiabilidad del ruler/RAG. MEDIO = decisión no trivial en componente establecido,
reversible pero con rework real. BAJO = local, trivialmente reversible, sin zona de dolor.

## Instrucciones del revisor (briefing / system prompt)
**El briefing operativo vive en `scripts/adversarial_briefing.md` (fuente ÚNICA).** Lo lee el
revisor principal Sol y lo cita Fable 5. Antes había una copia aquí y otra, más
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
`elapsed_s`), incluidas ejecuciones fallidas (`run_status=failed`); yo completo a mano los
campos de JUICIO tras verificar (`findings`, `confirmed`,
`false_pos`, `severity_max`, `verdict_notes`). La tasa de hallazgos sobre propuestas ordinarias
NO mide sola la calidad: una propuesta sólida puede y debe devolver `SÓLIDO`. Señales de matar/revisar:
- **recall bajo en una ventana de casos congelados con fallos conocidos** = ritual-SÍ.
- **falsos-positivos altos sobre controles limpios adjudicados** (fabrica trivialidades) = ritual-NO.
- precisión/recall aceptados y valor de hallazgos insuficientes frente a coste/fricción.
Se gana su sitio con datos, no por fe (eval-driven, como todo lo demás).

## Cross-model — dependencia (fix GPT #5)
Data-flow OpenAI ya **aceptado** en el proyecto (el mismo `OPENAI_API_KEY`).
`scripts/adversarial_review.py` lee el prompt de `adversarial_briefing.md`; modelo vía
`ADVERSARIAL_MODEL` (default `gpt-5.6-sol`) y esfuerzo vía
`ADVERSARIAL_REASONING_EFFORT` (default `xhigh`); ambos valores quedan registrados en el tally.
Una ejecución con override distinto debe declararse y no satisface por sí sola el rol de revisor
principal; el runner lo etiqueta como `override no-principal` y registra
`primary_contract_satisfied=false`. **`--diff`** auto-incluye `git diff HEAD` para no
depender de que yo elija bien el contexto (sesgo de selección). **Fallback**: si GPT no está
disponible, el suelo es Fable 5 + mi verificación, y se **marca explícitamente
"revisor principal Sol omitido"** (no se finge que se hizo).
Las llamadas usan Responses API con `store=False`; propuestas, diff y lecturas no se solicitan
como respuestas almacenadas por la API.
**Smoke Sol del contrato final (2026-07-17):** PASS versionado en
`evals/adversarial_sol56_xhigh_runner_smoke_v1.json`: `gpt-5.6-sol` + `xhigh` +
`store=False` completó una llamada `list_dir` y la continuación stateless con cap 1.
Cada entrada Sol nace con `duo_status=pending_fable` y un bloque `fable_review` pendiente. La
revisión ALTO/zona-de-dolor no está completa hasta rellenar ahí identificador, coste y adjudicación
de la ejecución Fable 5 separada; si no puede ejecutarse, se marca `omitted_unavailable`.

## Acceso autónomo al contexto versionado — resuelto en s88 (pedido de Alberto; cierra TECH_DEBT #36)
**Desde s88 el cross-model LEE EL REPO versionado él mismo:** `adversarial_review.py` corre un loop agéntico
(Responses API + function tools; necesario para mantener Sol en `xhigh`) con tools
**READ-ONLY** sandboxeadas al repo:
- `read_file(path, start_line, max_lines)` — con números de línea (anclas `fichero:línea`).
- `grep_repo(pattern, glob, max_hits)` — regex sobre el repo.
- `list_dir(path)`.
- **Deny-list:** `.env*` (secretos), `.git/` y dirs internos, y el **propio log de tally**
  (anti-contaminación). Sandbox: paths resueltos bajo la raíz (no traversal).
- **Cap 30 tool-calls** (disciplina de coste); al agotarlo se fuerza la review con lo leído.
  `--no-tools` restaura el modo legacy (pegado) como escape. `--diff` se mantiene.
- El tally registra `tool_calls`, `files_read` y `tool_trace` (tool, argumentos y estado;
  no persiste el contenido leído), de modo que se audita qué consultó sin duplicar código en el log.
**Invariante preservado (el activo del cross-model):** ve el artefacto por lente no-Claude + su
salida se lee CRUDA — NO anidado en el sub-agente. **Smoke (s88):** con 2 claims falsas plantadas
(umbral 0.5; reranker voyage-en-prod) las cazó AMBAS leyendo el código (14 tool-calls; anclas
`generator.py:342-343`, `config.py:56-64`).

*Histórico (s52/DEC-028, superado):* antes el cross-model solo veía lo pegado → la regla era pasarle
las fuentes a mano (extractos, catálogo) y `--diff`; el síntoma s52b ("no puedo validar existencia
desde la propuesta") era la asimetría. Pasar ficheros como CONTEXTO sigue siendo útil como punto de
partida (ahorra tool-calls), pero ya no es el techo de lo que el revisor puede ver.
El acceso comparable se limita al repo versionado: memoria externa u otras fuentes que vea Fable
se pasan a Sol como contexto/snapshot autorizado cuando sean materiales. No se amplía el sandbox
fuera de `ROOT` ni se promete simetría total de contexto implícito.

## Modelos del dúo (actualizado post-s194)
**Principal:** `gpt-5.6-sol` con `reasoning_effort=xhigh`, vía
`scripts/adversarial_review.py`, con tools read-only y salida cruda.
**Segundo revisor frontera, ejecución independiente:** pin `model: fable` (Fable 5; Alberto
s88 — antes `opus` s73→s88), con acceso autónomo al mismo repo versionado. “Independiente” describe la
ejecución y su salida cruda, no una familia distinta: Fable puede compartir árbol con el autor;
la diversidad cross-family la aporta Sol. En ALTO/zona-de-dolor se requieren las dos lentes;
Fable 5 no sustituye al principal Sol y Sol no sustituye la revisión separada de Fable 5.

**Objetivo de la migración GPT-5.5→Sol:** aplicar la decisión explícita de modelo principal sin
afirmar todavía una mejora de eficacia. El tally histórico y las entradas nuevas estratificadas por
`model`/`reasoning_effort` sirven para seguimiento operativo, no para atribución causal porque cambia
la dificultad de cada review. Validar una mejora de eficacia exige replays pareados de ambos modelos
sobre casos con fallos conocidos y controles limpios, congelando commit/corpus accesible, propuesta,
briefing, runner, tools/cap y configuración. Métricas: precisión y recall adjudicados, coste y latencia.
Hasta entonces la selección es una decisión de protocolo revisable, no un resultado demostrado.
