# s286 — Diseño del guard hp018: «instrucción afirmativa inventada desde diagrama» (SEGURIDAD)

## OBJETIVO + MÉTRICA
Eliminar la clase de fallo confirmada por la traza (f0baca6, 10/10 sistemático): el generador
INVENTA un procedimiento de conexionado paso-a-paso («+ a +, − de esa sirena al + de la
siguiente» = serie eléctrica, rompe supervisión y reparte 24V) cuando la fuente (MIE-MI-310
§3.3.5 pp.18-19) solo da texto descriptivo + DIAGRAMA (paralelo sobre el par, RFL 6K8, línea
sin ramales), citando [F3] — el EC valida existencia de cita, no soporte de la instrucción.
MÉTRICA del guard: re-traza hp018 K=10 → **0/10 con aserción de topología no soportada** +
no-regresión en controles de conexionado (K pequeño). El baseline completo se re-mide DESPUÉS
bajo vara v4 (orden adjudicado por Alberto). Clase nueva DEC-160c — no toca ningún lever settled.

## RECOMENDACIÓN (composite A+B+C, cada pieza con flag independiente default-off)

**A. Regla del generador (anti-invención, estructural).** Instrucción en el prompt del
generador: cuando el conexionado/topología solo existe como DIAGRAMA en los chunks servidos
(sin prosa paso-a-paso), NO sintetizar procedimiento paso-a-paso; describir lo que el texto
dice, remitir explícitamente a la figura, y NUNCA afirmar topología (serie/paralelo/cadena de
polaridad) sin soporte textual literal en el chunk citado.

**B. Servir el diagrama real.** Si la pregunta es de conexionado y las páginas citadas tienen
asset `visual_role='wiring'` en `document_visual_assets` (VERIFICADO: MIE-MI-310 pp.17-20 los
tienen, con URL) → adjuntarlo. El canal VISUAL_ASSETS_REGISTRY=on ya existe en prod; esto
afina su gating al caso conexionado. Sinergia con la mejora 5.1 (gating de assets).

**C. Check EC nuevo `wiring_topology_assertion` (determinista, fail-closed, léxico CERRADO).**
Post-writer: si la respuesta contiene aserción imperativa de topología en contexto de
sirenas/salidas supervisadas — lexicón cerrado ES: «en serie», «daisy-chain», patrón
«− … al + de la (siguiente|próxima)», «sin ramales»→«no … paralelo» — exigir que un chunk
CITADO en esa sección contenga el término de topología; si no → acción fail-closed: retirar la
aserción y sustituir la sección por descripción-del-texto + remisión a la figura. Es la
garantía que A (probabilístico) no puede dar. Inserción: `src/rag/evidence_contract.py`
(patrón existente de acciones fail-closed por sección).

## ALTERNATIVAS DESCARTADAS
- **Self-check LLM por respuesta**: coste por query + no determinista + no auditable — contra
  el patrón EC (que existe precisamente por esto).
- **Blacklist simple de «en serie»**: parche no estructural; rompería menciones legítimas
  («2x6.8kΩ en serie» de la entrada monitorizada MIE-MP-520rv04 p27; «interface en serie»
  SIB-2048) y no cubre reformulaciones («una tras otra, − con +»).
- **Solo-B (diagrama sin guard)**: el texto peligroso seguiría presente; mitiga, no elimina.
- **Bloquear preguntas de conexionado (clarify/admit)**: mata utilidad legítima del bot en su
  caso de uso central; el gold hp018 espera answer.

## GAPS DECLARADOS
1. Lexicón C es ES-céntrico — aceptable (el bot responde siempre en ES) pero queda declarado.
2. A es probabilístico — por eso C existe como red determinista; la combinación es el diseño.
3. B depende de que el asset exista — cubierto en hp018; no garantizado corpus-wide (fallback:
   remisión textual «ver Figura N, página M»).
4. Riesgo de sobre-supresión de A (procedimientos textuales legítimos suprimidos) — lo miden
   los controles del A/B (golds de conexionado con prosa real paso-a-paso).
5. El patrón «− al + de la siguiente» como regex tiene variantes tipográficas — el diseño debe
   normalizar (espacios/símbolos) antes de matchear.

## POR QUÉ BP + ESTRUCTURAL + ESCALABLE
Ataca la RAÍZ (invención de procedimiento sin soporte textual), no el síntoma («en serie»);
la clase generaliza a 30+ fabricantes (todo manual tiene diagramas de conexionado); reutiliza
los dos mecanismos vivos (EC fail-closed + registro visual etiquetado); cada pieza es flag
independiente reversible y medible por separado en el A/B.

## PLAN DE MEDICIÓN
1. Construir A+C flag-off (+ ajuste de gating B), tests unitarios del check C.
2. A/B dirigido: hp018 K=10 (target 0/10) + controles conexionado K=3 (hp009, cat019, hp004…
   golds con procedimiento textual real — no deben degradar).
3. Si pasa → flags on en Railway (clicks de Alberto si es env) + el baseline completo v4
   después (tasks #1/#2/#5/#6 primero, orden adjudicado).
