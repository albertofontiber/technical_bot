# s287 — PACKET DE ADJUDICACIÓN cat008 (auditoría píxel completa; NADA aplicado)

## Veredicto de la auditoría: (b) gold anclado con PRECISIÓN a una fuente ERRÓNEA
**13 variantes de módulo · 5 manuales oficiales · 4 idiomas (EN/ES/IT/DE) coinciden**:
T1/T2 = SALIDA del lazo · T3/T4 = ENTRADA del lazo · T5 = salida+ alternativa (unida
internamente a T4). **La ÚNICA fuente que dice lo contrario es la guía KB
`Conexionado-del-modulo-M710-MI-DMMI.pdf`** — y sus dos guías HERMANAS de la misma serie KB
(CZ, CZR) usan la convención oficial ⇒ los rótulos de esa guía están invertidos por error de
edición, no por convención ni por variante. La hipótesis nocturna de conflicto-de-variante
(DEC-163e) queda REFUTADA por píxel. Renders: `evals/s287_renders/` (18 PNG, tabla completa
en el informe del agente auditor).

## Lo que decides tú (gold — no se toca sin tu OK):
**A. Corregir cat008#4 (core)**: «1=−Salida del lazo, 2=+Salida, 3=−Entrada, 4=+Entrada,
   5=+Salida alternativa (unida internamente al 4); Entrada A (circuito supervisado) = 6-7»
   · cita: I56-2006-004 FIG.3 (ES p3) + I56-4406-001 §Wiring + I56-2005-002 FIG.3.
**B. Re-alcance cat008#2**: la RFL 47 kΩ (M200-EOL-R) es del CIRCUITO DE ENTRADA supervisado
   (Entrada A, 6-7) — el lazo direccionable NO lleva RFL. El gold_answer propaga la frase.
**C. cat008#7 fuera de alcance** (M200E-EOL-RD/VdS 2489 = opción del M701/salida, no del
   M710/MI-DMMI) → eliminar o re-etiquetar; y el puntero «figs 5/6» de #1 → FIGURE 3 nota 3.
**D. Documentar en notes del gold**: CONFLICTO-FUENTE con autoridad-manda (manual de
   instalación certificado EN54-17/18 > artículo KB de soporte) — patrón cat009.

## Lo que es CORPUS (ticket independiente, también tuyo por ser serving-data):
**E. `I56-2006-004` no tiene capa de texto (escaneado) y 3/17 chunks INVIERTEN una
   instrucción de cableado** («terminal 5 conectado internamente con el terminal 2» — la
   fuente dice TERMINAL 4, verificado en ES y DE) + otras degradaciones en los mismos chunks.
   Clase de fallo NUEVA y safety-adjacent: corrupción OCR semántica que invierte cableado —
   ninguna heurística de longitud la caza. Propuesta: re-extracción/QA de los 17 chunks +
   **check de fidelidad sobre TODOS los docs con textlen==0 antes del próximo lote** (el
   agente ya olió un caso análogo en I56-2128-003 p3, no auditado a fondo).
**F. Nota de calibración**: incluso los oficiales tienen UN desliz in/out en una línea
   (T5 del MI-D2ICMOE en EN/IT vs ES) — el desliz in/out es modo de fallo RECURRENTE de esta
   familia documental; nunca en el bloque T1-T4.

## Implicación para el OBJETIVO
El FALLO de cat008 en el baseline es (probablemente) el bot dando el mapping OFICIAL y el juez
puntuando contra el gold-KB-erróneo. Con A-D aplicados, cat008 debería convertir sin tocar el
pipeline. El fact cat008#3 sale del residual de la etapa 1 (era clase gold/fuente, no
mecanismo) → **residual mecanismo-abierto de la ETAPA 1 = 1 (hp013#1)** = <2 CUMPLIDO.
