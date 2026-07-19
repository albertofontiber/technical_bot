# S269 — Diagnóstico del NO_GO de Etapa 1 (detector determinista) — $0, programático

Gate: `evals/s269_stage1_gate_v1.yaml` (NO_GO 4/4 familias + 1 FP-negativos).
Cruce detector-vs-gold por fila (108) con clasificación de causa por span:

| Familia | HIT | MISS es/en | MISS idioma | FP-vs-gold | Lectura |
|---|---|---|---|---|---|
| F-RANGE | 28 | 27 | 0 | 3 | Detector corto: notaciones reales fuera del patrón — `–10˚C ≤ Ta ≤ +55˚C` (cadenas de desigualdad), `470Ω a 1K máx` (compacto con sufijo de unidad), `0.129 ilâ 3.31 mm²` (conector no-ES/EN dentro de doc mixto). Gold correcto. |
| F-BUNDLE | 30 | 40 | 0 | 19 | El gold marca TABLAS (markdown y **HTML `<tr><td>`**) como bundles — y el guard s243 las INCLUYE ("headers, tables, lists and rule schemas"); mi parser solo cubría headings+listas-definición. Gap genuino de modalidad. Los 19 FP = headings sin miembros reales (parser demasiado laxo en la otra dirección). |
| F-MANDATORY | 28 | 45 | 1 | 2 | Mixto: (a) huecos de léxico genuinos — `deberá`, `hay que tener en cuenta`, `asegúrese`; (b) sobre-inclusión del gold — pasos procedimentales (`Guardar programación: Retirar puente...`) etiquetados como mandatory sin lenguaje de peligro/obligación (la familia s243 es "prerequisite/warning/verification callouts", no todo imperativo). |
| F-COUNT | 1 | 6 | 0 | 9 | **Mismatch de SPEC en ambas direcciones**: el gold marca todo conteo+enumeración (`There are 2 options...`, `uno de los tres niveles`) mientras el detector solo emitía INCONSISTENCIAS; y el conteo de miembros del detector falla (9 FP). La familia necesita re-spec: detección = par conteo↔enumeración; `conflict` = sub-caso para DISCLOSE. |

**Conclusión:** las FAMILIAS s243 siguen siendo sanas; lo que no generaliza es el **detector
determinista-puro** (≈60% del gap = modalidades/notaciones no cubiertas — tablas HTML, cadenas
de desigualdad, formas verbales; ≈30% = definición del gold a apretar en el prompt del
etiquetador; ≈10% = idioma no-ES/EN, real pero minoritario). Coste del aprendizaje: $1.63,
cero exposición de targets (orden s261 respetado).

## Propuesta v3 (para ronda de dúo — NO construida)

1. **Detector híbrido**: fast-path determinista (se conserva) + **detección modelo (Haiku,
   structured output por familia) con grounding determinista obligatorio** — cada átomo debe
   citar un span VERBATIM del fragmento (validador código: span ∈ fragmento + shape-check por
   familia); sin span verbatim → átomo descartado. El render/binding/attestation NO cambian
   (la postcondición sigue siendo código).
2. **Independencia del gold**: detector usa Haiku ⇒ el gold pasa a **Luna + Terra-low**
   (model-disjoint), árbitro Sonnet o descarte. Prompts del etiquetador APRETADOS con las
   exclusiones de este diagnóstico (paso procedimental ≠ mandatory; conteo consistente =
   átomo con `consistent=true`, no ausencia).
3. **Re-spec F-COUNT**: detección del par conteo↔enumeración; `conflict` como sub-caso.
4. **Cohorte v2 fresca** (reserva restante ~700 docs; misma mecánica de exclusiones), mismos
   gates (recall ≥0.80 · precisión ≥0.95 · FP=0), coste ~$3-4. La cohorte v1 y sus labels NO
   se re-usan para tunear (anti-overfit del prereg v1); sirven solo como diagnóstico.
5. Coste runtime declarado del híbrido: +1 call Haiku por respuesta (solo fragmentos
   citados/servidos, cap de tokens) — dentro del presupuesto de latencia del diseño v2.
