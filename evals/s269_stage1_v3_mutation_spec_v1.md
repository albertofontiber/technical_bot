# S269 — Etapa 1 v3: harness de MUTACIONES con gold mecánico (spec de build)

> Sucesor del NO_GO v1 (`s269_stage1_gate_v1.yaml`) tras la ronda de dúo del build
> (Sol 9/9 + Fable 7/7 confirmados, 0 FP — tally 2026-07-19T01:18:55). El pivote responde a
> los dos críticos de Fable: el gold de modelo barato NO es fiable (87% de negativos marcados
> positivos; F-COUNT incumplió su prompt) → **el gold pasa a ser MECÁNICO por construcción**
> (patrón S249, precedente in-repo validado con precisión 1.0/FP 0). Sin etiquetadores.

## A. Fixes de código previos (los críticos de Sol confirmados en código)

1. **C2 — binding claim-proximity**: `bind_atoms` debe ligar el átomo al TEXTO ADYACENTE a la
   cita [Fn] de SU fragmento (ventana: la(s) oración(es)/línea(s) que llevan la cita de ese
   fragment_id, no toda la respuesta). Sin cita localizable → no exigible (conservador).
2. **C3 — atom_satisfied completo**: F-RANGE exige extremos+paso+tolerancia Y unidad Y (si hay)
   tokens de scope presentes cerca del claim; F-COUNT con `conflict=True` NUNCA se satisface
   por presencia de números — solo por disclosure explícito (patrón "el manual también
   indica"); F-BUNDLE exige miembros + cabecera padre; F-MANDATORY sin cambio (ya exige
   trigger+anchors).
3. **C1 — gate a nivel átomo**: el gate v3 puntúa por MUTACIÓN individual (átomo), no por
   booleano de familia, con cobertura mínima declarada (≥90% de las filas de la cohorte
   puntuables; filas no puntuables listadas).
4. **C4 — freeze completo**: el prereg v3 pinea sha256 de `must_preserve.py`, del harness, de
   los templates de mutación y de la cohorte; el gate ABORTA si cualquier sha difiere.
5. **M7 — umbrales**: el gate LEE los umbrales del prereg (única fuente); constante espejo solo
   como cross-check anti-tamper (patrón del ejecutor visual v3).
6. **M9 — exclusión 7-seg**: whitelist de formas de display (`r.I`, `t.Fi`, `dr`, códigos
   1-3 chars con punto interior) SIN capturar numeración de sección tipo `A.1`
   (regla: la exclusión aplica solo si el token aparece en contexto de display/parámetro, no
   al inicio de línea/heading).

## B. Harness de mutaciones (gold mecánico)

- **Cohorte v2**: fragmentos frescos de la reserva (~700 docs post-exclusiones v1; MISMA
  mecánica de exclusión + excluir también los 60 docs de la cohorte v1). Seed nueva (=270).
  ~120 fragmentos con átomos DETECTABLES por el detector híbrido (pre-screen declarado; el
  sesgo de selección se controla porque el gold es mecánico y el gate mide sobre mutaciones,
  no sobre prevalencia).
- **Mutaciones por familia** (determinista, span-level, cada una con receipt de qué se quitó):
  - F-RANGE: quitar extremo superior · quitar paso · quitar unidad · quitar scope.
  - F-BUNDLE: quitar un miembro · quitar la cabecera padre.
  - F-MANDATORY: quitar la cláusula obligatoria completa.
  - F-COUNT: alterar el conteo declarado (crear inconsistencia) · quitar la enumeración.
- **Borrador sintético**: template determinista que redacta el claim del fragmento CON la
  mutación aplicada + cita [Fn] real (2 variantes de fraseo por mutación para no depender de
  un solo template; sin LLM en el path del gold).
- **Medidas**:
  - `mutation_recall` por familia: el mecanismo detecta el átomo y su appendix restaura
    EXACTAMENTE el span mutado (match verbatim contra el receipt).
  - `clean_noise` (precisión): sobre el borrador SIN mutar (átomo ya presente), el mecanismo
    NO anexa nada → FP=0 exigido.
  - `cross_binding` (control C2): borrador que cita el fragmento A pero habla del fragmento B
    → el mecanismo NO anexa átomos de A ligados a claims de B. FP=0 exigido.
  - `attestation_block`: fragmento de documento fuera del doc_map de la identidad → 0 anexos.
- **Gates pre-declarados** (leídos del prereg): mutation_recall ≥0.80 por familia ·
  clean_noise FP=0 · cross_binding FP=0 · attestation_block 0 · cobertura ≥90%.
- **Detector híbrido**: fast-path determinista actual + brazo Haiku con grounding verbatim
  obligatorio (span ∈ fragmento o descarte), `HYBRID_DETECTOR=on/off` como dimensión del
  harness (se reporta AMBOS brazos: determinista-solo vs híbrido) — coste Haiku ~$1-2.
- **Declaraciones honestas** (Fable M4-M6): el léxico/patrones se ajustaron con los misses de
  la cohorte v1 (tuning declarado; por eso v2 es población fresca); la prevalencia/ubicuidad
  de familias NO se mide aquí (harness condicionado a mutación); la salud de las familias s243
  queda como supuesto de diseño, no como hecho medido.

## C. Qué NO hace este paso

Sin exposición de los 4 targets (orden s261 intacto: Etapa 2 sigue gateada por Etapa-1-GO +
adjudicación formal de Alberto de la reapertura s222/s223). Sin tocar prod. Flag default-off.
Presupuesto: ≤$4 (Haiku del brazo híbrido + margen); todo lo demás $0.
