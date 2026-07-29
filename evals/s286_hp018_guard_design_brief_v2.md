# s286 — Guard hp018 v2 (post-dúo r1: Sol 7 hallazgos + sub-agente 9, convergentes)

## CAMBIOS v1→v2 (qué mató el dúo r1)
1. **C se modela sobre `apply_answer_conflict_guard`** (`src/rag/answer_planner.py:2745-2855`:
   sustitución de bloques + plantilla + re-validación + escalada fail-closed) — NO sobre el EC
   (append-only por contrato, `evidence_contract.py:26-36`; presentarlo ahí era capacidad nueva
   disfrazada de reutilización — hallazgo del sub-agente, sesgo del autor reconocido).
2. **Posición en pipeline ESPECIFICADA**: C corre inmediatamente post-writer, ANTES de
   must_preserve → conflict_guard → EC (`generator.py:806/825/839`), para que los appenders
   re-validen y re-rellenen sobre el texto ya guardado. Sin esto, un callout de seguridad puede
   perderse en silencio (Sol F-orden + sub-agente #5).
3. **Lexicón re-etiquetado «residual declarado», NO «cerrado»**, y EXTENDIDO: {en serie, en
   cadena, encadena(ndo), una tras otra, en cascada, daisy-chain} + patrón de cadena-de-polaridad
   AGNÓSTICO al conector (símbolos −/+ o palabras negativo/positivo … {siguiente|próxima|anterior}
   en la misma frase, con normalización tipográfica) + **regla ASCII-schematic** (BLOCKER del
   sub-agente: bloque code-fence/monoespaciado con stem "siren" + arte de línea
   (─/━/│/▶/◀/cajas) NO presente verbatim en ningún chunk servido → unsafe; 2/10 corridas de la
   traza ya reconstruyen la figura, una con atribución FABRICADA «Basado en Figura 15»).
4. **Entrada «sin ramales» ELIMINADA** del lexicón peligroso (semánticamente invertida: la fuente
   SÍ dice línea sin ramales; el hazard es la cadena de polaridad — sub-agente #7).
5. **Contexto especificado**: la detección aplica por BLOQUE (segmentación por líneas en blanco,
   como conflict_guard) y solo en bloques con stems {sirena(s), salida(s) de sirena, NAC}.
6. **Soporte sigue siendo léxico ⇒ RESIDUAL DECLARADO** (un «interface en serie» citado
   legitimaría — se acepta y documenta; la defensa principal contra eso es A', no C').
7. **A' endurecida**: además de no afirmar topología sin soporte textual, PROHIBIDO reconstruir
   diagramas (ASCII/esquemas/pseudo-figuras) y PROHIBIDO atribuir a figuras no presentes en el
   texto servido; si el conexionado solo existe como figura: describir lo textual + nombrar
   figura y página + remitir. (Anti-sinergia A↔C mitigada: A' ataca también el modo-escape
   ASCII que C' detecta; celdas factoriales miden ambos.)
8. **B FUERA del composite de seguridad** (pregunta cero del sub-agente #6): con
   `VISUAL_ASSETS_REGISTRY=on`, `append_cited_visual_assets` (`visual_assets.py:169-218`) YA
   adjunta assets wiring de páginas citadas. Verificación previa al A/B: ¿hp018 bajo perfil-prod
   adjunta hoy? Además la traza destapó **bug vivo confirmado**: el parseo de
   `DIAGRAMAS_RELEVANTES` (`generator.py:765-782`) falla ~50% cuando el modelo añade la coletilla
   «También puedo ayudarte…» tras la línea → assets no adjuntados. **Fix del parser = ítem
   independiente inmediato** (primera línea/regex prefijo + test); el gating fino = mejora 5.1.
9. **MEDICIÓN DES-CIRCULARIZADA** (BLOCKER común Sol F2 + sub-agente #3): el detector del guard
   NO puntúa el A/B. Métrica primaria = **adjudicación contra-fuente independiente** de cada
   respuesta (lectura completa incluyendo bloques de código, contra MIE-MI-310 §3.3.5 pp.18-19 y
   MIE-MI-530 equivalente): ¿contiene instrucción/esquema de topología NO soportado por el texto?
   Regex ampliado = solo tripwire secundario. Batería: pregunta hp018 + 3 paráfrasis × K
   (muestrea la distribución de formulaciones). Celdas factoriales: off/off (baseline traza) ·
   A'-only · C'-only · A'+C'. Config congelada declarada en el artefacto.
10. **Controles de sobre-supresión REALES** (sub-agente #9 + Sol F6): positivos con «en serie»
    LEGÍTIMO que NO debe suprimirse — hp003 (baterías 12V en serie, prosa textual), pregunta
    sintética sobre entrada monitorizada (2×6K8 en serie, MIE-MP-520rv04 p27), pregunta sintética
    de comunicación serie (SIB/RS-485). + controles de procedimiento textual legítimo.
11. **Producto 310 vs 530** (Sol F1, parcialmente refutado): el gold hp018 está AUTORADO sobre
    MIE-MI-310 (`pdfs_used`, verificado) — no está «descartado». Queda verificación añadida:
    consistencia del circuito entre MIE-MI-310 pp.18-19 y MIE-MI-530 (sección sirenas) antes del
    A/B; si divergieran, escalar a Alberto (ground-truth de dominio).

## SIN CAMBIOS v1→v2 (lo que el dúo sostuvo)
- Composite defensa-en-profundidad: A' (probabilística, generación) + C' (determinista,
  post-writer) con flags independientes reversibles. Alternativas descartadas se mantienen
  (self-check LLM por query; blacklist simple; solo-diagrama; bloquear conexionado).
- La clase es real y de seguridad: 10/10 sistemático, 0 chunks servidos con "serie".

## GAPS DECLARADOS v2
ES-céntrico (bot responde ES) · soporte léxico no semántico (residual, defendido por A') ·
lexicón residual-declarado (la adjudicación independiente del A/B mide el residual real) ·
pérdida acotada de contenido correcto en bloques mixtos (precedente conflict_guard aceptado;
peor-caso run 4 evaluado: perder 2 bullets de polaridad < servir serie).

## PLAN
1. Fix parser DIAGRAMAS_RELEVANTES (independiente, test unitario, hoy).
2. Verificar B-pregunta-cero + consistencia 310/530.
3. Construir A' + C' flag-off (C' junto a conflict_guard en answer_planner) + tests.
4. A/B factorial per §9-10 → adjudicación contra-fuente.
5. Flags on (clicks Alberto si env Railway) → re-baseline completo DESPUÉS (orden adjudicado).
