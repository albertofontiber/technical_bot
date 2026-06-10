# s40 — Consolidación del árbitro (atomic_scorer): propuesta a refutar

Sesión "consolidar el árbitro" (no crecer golds). Dos piezas. Ataca la CONCLUSIÓN y mi framing.

## Pieza 1 — Validar `--prose-llm` (#35, firmado en B1 con un cabo suelto)
- B1 dejó UN cabo: el rescate prose-llm de `hp007 valor='cada 2 años'` era sospechoso de over-credit.
- VERIFICADO leyendo la respuesta real del bot (`bot_vs_gold_results_k5.yaml`, hp007 VESDA-E VEP):
  el bot dice literalmente "sustitución del filtro (mantenimiento **bienal**)" y "comprobación
  **trimestral** de fuente". bienal=cada 2 años; trimestral=cada 3 meses. → **NO es over-credit**;
  el rescate es paráfrasis legítima. El prompt de prosa **NO necesita endurecerse**.
- Prueba de no-over-credit en el piloto: `cat007 'no enclavado'` → prose-llm dio "no cubierto"
  (correcto: el bot ADMITIÓ no conocer el comportamiento failsafe). El overlay solo RESCATA y es
  conservador (asimetría False→True; nunca baja).

## Pieza 2 — Fix del matcher de rangos (lo que SÍ había que endurecer)
- Bug: `distinctive("110-230")` → {'110','-230'} (guion de rango leído como signo). El '-230'
  fallaba la frontera de dígito de `_anchor_present` (atomic_scorer) y `_value_on_page` (locate_fact)
  → falso-miss. Era la causa REAL del "cat005 PARCIAL=suelo", NO fragilidad de prosa.
- Fix raíz: `_NUM = re.compile(r"(?<!\d)[+\-]?\d[\d.,]*")`. Verificado: rangos→positivos, negativos
  reales preservados, sin partir enteros.
- Resultado: cat005 5/6→**6/6 PASS** (completitud real; el bot dice "110-230 Vac" literal). Los 19
  golds hp/cm/nd: core x/n IDÉNTICO antes/después (A/B mecánico sobre el cache k5). 249 tests verdes
  (6 nuevos en tests/test_strict_match.py). Añadido test que fija el contrato rango-vs-signo.
- Efecto colateral DECLARADO (sub-agente, hallazgo B): soltar el signo de una suma SIN espacios
  ('159+159/99+99') relaja `all(anchor in chunk)` en los instrumentos de retrieval → inflación de
  recall acotada a **1 hecho de 134 (solo cat001)**; hp012 ('99 + 99', con espacios) es INMUNE; los
  3 rangos no inflan. NO toca prod ni el scoring de golds. Decisión: aceptar (no endurecer más = 1/134
  en un instrumento-proxy ya caveateado; endurecer sería sobre-ingeniería).

## Diagnóstico autoritativo del piloto post-fix (HyDE-off, chunks_v2, --llm --prose-llm)
- cat005 (Fidegas CS4, gas): **PASS 6/6**, 0 contradicciones.
- cat007 (FAAST LT-200, ES/EN): PARCIAL 4/5 — el único miss ('no enclavado') es REAL (el bot admitió).
- cat001 (PEARL multi-doc): PARCIAL 2/7 — los 5 misses son anchors duros que el bot OMITIÓ (0,75 A,
  40 CLIP, 99, 255/8192, 25), NO artefactos; 0 contradicciones → omisión, no error.

## CONCLUSIÓN (atácala)
El árbitro queda CONSOLIDADO para lectura categórica + delta razonable: (1) `--prose-llm` validado
como conservador y correcto; el cabo de B1 cerrado (no over-credit). (2) El "PARCIAL=suelo" de DEC-010
era, para el piloto, (a) un bug del matcher de rangos [ARREGLADO → cat005 PASS] + (b) misses REALES
[cat001/cat007, no un suelo], NO fragilidad de prosa. El overlay prose-llm funciona (validado en los
19: rescates hp003/005/007 legítimos) pero NO era el lever de los suelos del piloto. El cuello
multi-doc de cat001 (síntesis incompleta) se confirma y NO es ruido de medición.

## Gaps declarados (de entrada, sin esperar pushback)
- El A/B de los 19 usó respuestas CACHEADAS pre-AC220 (era s37): válido SOLO como check de regresión
  del matcher (mismas respuestas, solo cambió el matcher), NO como baseline fresco. NO se regeneró un
  baseline post-AC220 de los 19 esta sesión (fuera del scope = piloto).
- prose-llm validado con n pequeño (4 rescates + 3 no-rescates del piloto), no calibración amplia.
- "cat001 incompletitud real" se apoya en anchors genuinamente ausentes + lectura manual (s39) +
  factual=0 contradicciones; no en un humano técnico.
- Efecto de sumas en recall: aceptado sin endurecer (1/134, instrumento-proxy).
