# s293 · Lever A (reparación por span del conflict-guard) — **NO-GO**, nada cableado

Veredicto tras dúo completo (cross-model GPT-5.6 Sol xhigh + sub-agente Opus 5, pin DEC-171d):
**15 hallazgos, 15 confirmados, 0 falsos positivos, severidad máxima crítico.** Sub-agente:
«NO-SÓLIDA». Tally: `evals/adversarial_review_log.jsonl` (ts 2026-08-02T09:30:03,
`duo_status=complete`). Salida íntegra del cross-model en `evals/adversarial_reviews/`.

El lever cae por **dos motivos independientes**. Cualquiera de los dos basta.

---

## Motivo 1 — ECONOMÍA: ni con el guard perfecto el hecho llega al umbral

Los dos revisores convergieron en la misma medición barata que yo no había ejecutado (y que
mi propia sonda había pre-declarado en su docstring): juzgar *conveyed* sobre el borrador
**PRE-guard** ya persistido. Juez canónico `judge_conveyed21`, K=5, `THRESH_FIRM=4`
(recibo `s293_hp017_conveyed_preguard_v1.json`):

| | PRE-guard | POST-guard |
|---|---|---|
| rep0 | **3/5** | 0/5 |
| rep1 | **1/5** | 0/5 |
| rep2 | **2/5** | 0/5 |
| control: `answer` del recibo del FULL | — | 0/5 *(el instrumento v3.2 dio 0/5 ✓)* |

**El hecho `hp017#2` tiene dos mitades** — «acceder a la pantalla Causa y Efecto desde el
menú Editar Configuración» **y** «borrar la Regla 1 por defecto (CUALQUIER entrada de alarma
activa TODOS los equipos de salida)». El modelo escribe la primera (y el guard se la come:
3/5 → 0/5, efecto causal real) y **no escribe la segunda**: 0/3 reps, verificado con cinco
marcadores incluyendo paráfrasis (`regla 1`, `reglas por defecto`, `borrar|eliminar|suprimir`,
`cualquier entrada`, `todos los equipos`). Ni PRE-guard alcanza el umbral firme.

⇒ El guard NO es causa suficiente. La mitad residual es **omisión de síntesis** = otra clase.
Esto **corrige la ficha de DEC-171**, que atribuía `hp017#2` íntegro a «supresión por
conflict-guard».

## Motivo 2 — SEGURIDAD: el peldaño de redacción ABRE el agujero que el guard cierra

Hallazgo H1 del sub-agente, **reproducido por mí ejecutando el validador** (regla C):

```
Desde Editar Configuración, seleccione Causa y Efecto [F2].          <- línea redactada
Los fragmentos discrepan para el número de menú de Causa y Efecto:
[F1] indica 7: Causa y Efecto; [F2] indica 8: Causa y Efecto. …      <- aviso de dos lados
```
`validate_answer_conflicts` → **safe = True**. Pero el aviso mapea **fragmento → valor**
(`answer_planner.py:2718`), así que el técnico sigue la cita que sobrevive y **reconstruye el
número**: elección unilateral de facto, justo lo que el guard promete impedir
(`answer_planner.py:2758-2759`). Hoy esa línea **muere entera** (`:2829`) — el lever crea el
canal. En `hp017` la rama one-sided no expone números y por eso la medición no lo vio: es un
caso **no medido**, no inexistente — y aparecería en cuanto retrieval sirviera ambas
revisiones del manual, que están en el mismo documento.

Corolario incómodo y declarado: **mejorar retrieval empeoraría este lever.**

---

## Los otros hallazgos confirmados (por qué el gate tampoco valía)

- **Vara ciega** (Sol crítico · H2): G2 medía `ROUTE_PAT` (regex de la ruta), no *conveyed*;
  medía la mitad del hecho que me convenía. Mi propio `resumen` de la sonda calculaba los
  contadores de ruta y **omitía** los de Regla-1, que sí recogía.
- **Criterio sin contraste** (Sol crítico): el NO-GO solo restringía `on ≥5/6`; podía aprobar
  con 5/6 en AMBOS brazos, es decir sin efecto causal.
- **Circularidad** (Sol crítico · H3): el mismo `validate_answer_conflicts` es filtro de la
  reparación y árbitro del gate ⇒ «salida limpia» es un teorema del algoritmo, no conducta.
  Y G1 (flag off) da cobertura **cero** al camino nuevo; G4 es **tautológico** (flag-on solo
  diverge tras `initial unsafe`, y la huella es 1/39 = el mismo gold de G2).
- **A/B no pareado** (Sol medio): siendo el lever determinista post-generación, lo correcto es
  congelar N borradores y aplicar off/on sobre CADA uno; con generaciones independientes la
  varianza del writer contamina la medida (y sale más caro).
- **Anáfora colgante** (H4, reproducido): «Selecciona esa misma opción y borra la Regla 1» →
  safe (`esa misma opción` no casa `relative_choice_pattern`; `positive_directive_pattern` no
  incluye asigna/borra/accede/pulsa).
- **Peldaño 2 mal definido** (H8, reproducido): «El número correcto es el 7.» es safe aislada
  e **insegura** en bloque — validar-línea-aislada ≠ leave-one-out, porque
  `_bounded_relation_windows` colapsa el bloque a UNA ventana.
- **Integridad de span** (H5): con `MUST_PRESERVE_CONTRACT=on` los anexos son spans VERBATIM
  con cita y el guard corre DESPUÉS (`generator.py:912→931`) ⇒ la escalera podría editar
  in-place un span contractualmente verbatim. **DEC-171 ya exigía «guard de integridad de
  span» para esta misma clase** y el diseño no lo incorporaba.
- **Aviso una vez** (H6): con supervivencia del texto, la segunda ocurrencia se sirve sin
  aviso adyacente; I4 consagraba el bug en vez de corregirlo.
- **Gate más débil que su precedente** (H7): DEC-162a shippeó el otro guard determinista con
  A/B **ciego** pre-registrado, 24 generaciones, peligro 10/10→0/20 y supresiones 0/48.
- **Tier mal asignado** (Sol menor): `docs/ADVERSARIAL_REVIEWER.md:24-27` — «ALTO = … o toca
  seguridad» ⇒ esto era ALTO, no MEDIO.
- **Spec por ejemplo** (H9): la regla de redacción no definía si `« »` es literal; la forma
  frecuente en fuente y tests es SIN comillas ⇒ o no-op, o radio mayor que el declarado.

## Lo que SÍ queda en pie (no se re-litiga)

- El **diagnóstico** de s293: reparación por bloque (`:2811`), rama one-sided (`:2719-2724`),
  conflicto REAL intra-documento (7×1 chunk p.45 vs 8×7 chunks pp.15/26/41 del MISMO manual),
  huella 1/39, y el efecto causal medido del guard (3/5 → 0/5).
- **El daño cualitativo es real**: el guard borra un procedimiento de 3 pasos por un número
  dudoso. No mueve la métrica, pero es coste de usuario y está documentado.
- **El criterio del guard es correcto**; el defecto es de granularidad.

## Si alguien retoma esto (v2), tendría que traer

1. Cierre del canal de **reconstrucción por cita** (H1): o el aviso deja de mapear
   fragmento→valor, o la redacción se lleva también la cita del span redactado — con su
   propia medición.
2. **Juez semántico independiente** del validador (el validador no puede ser filtro y árbitro).
3. **A/B pareado sobre borradores congelados** + vara = *conveyed* con taxonomía
   pre-registrada, no regex de una mitad.
4. **Invariante de integridad de span** compatible con `MUST_PRESERVE_CONTRACT` (DEC-171).
5. Un solo peldaño (redacción) + conducta actual: el peldaño de línea no tiene evidencia
   medida y es el que trae H4/H8.
6. Y, antes de todo lo anterior: un hecho-diana cuya **otra mitad** sí se escriba, o el lever
   seguirá sin poder pagar la métrica.
