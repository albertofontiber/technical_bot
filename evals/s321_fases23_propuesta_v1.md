# s321 fases 2 y 3 — sonda endurecida (prueba de entrega) + el censo de población que NO concluye

> **Encargo.** Dos cosas distintas y quiero ataque distinto en cada una. En la **fase 2** he
> cableado un guard: atacadlo como código (¿falsos positivos? ¿se traga el resultado legítimo?).
> En la **fase 3** he producido un **negativo** —el censo no puede medir— y ahí atacad si el
> negativo es real o si me falta mirar donde no miré. Mi sesgo de hoy, declarado: llevo 24 h
> corrigiéndome, y un negativo cómodo («no se puede medir, no es culpa mía») es exactamente el
> tipo de conclusión que debería desconfiar de mí mismo.

Rama `claude/s321-packet-b2-correcciones`, worktree propio, **sin commitear**.

---

## FASE 2 — la sonda ya no puede emitir un negativo sin prueba de entrega

`scripts/s293_reachability_probe.py`, tres piezas nuevas:

**`prueba_de_entrega(cfg, rep)`** — distinta POR MODO, porque exigir ids en `appendix` bloquearía
todo NO legítimo de esa rama (lo cazasteis en mi primera redacción):
- `serve` → **TODOS** los carriers del `--inject` admitidos. «No vacío» no basta: con 2
  requeridos y 1 admitido, el hecho puede vivir en el que faltó.
- `appendix` → span no vacío **y** presente literal en la respuesta aumentada.

**`veredicto_de(reps, firm)`** — fail-closed **del negativo**: `NO_ALCANZABLE` solo es emitible si
TODAS las reps prueban entrega; si no, `INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA`. **Asimetría
deliberada**: un `ALCANZABLE` sí se emite aunque alguna rep no pruebe entrega, porque una rep
firme demuestra la capacidad por sí sola. El fail-closed protege el negativo, que es el que cierra
líneas de trabajo (`hp017#2` cerró la etapa 3 durante meses).

**`sello_freeze()`** — freeze-contract completo (corpus, top-k, reranker, merge, modelo, juez,
instrumento), no solo `git_sha`.

Anclado con **8 tests** (`tests/test_s321_reachability_delivery_proof.py`), incluido el
anti-falso-positivo: *un negativo legítimo (entrega probada, nada transmitido) SIGUE siendo
emitible*.

## FASE 3 — el censo de población: NEGATIVO, y el negativo es el entregable

Plan original: censar barato sobre el recibo FULL congelado (patrón del censo de punteros de
DEC-175). **No se puede, y está demostrado** (`scripts/s321_censo_poblacion_carrier.py` →
`evals/s321_censo_poblacion_carrier_v1.json`):

- por etiquetas, hechos con «carrier conocido y cero servido» = **0**;
- los **12** `synthesis-miss` tienen **todos** `n_support_served ≥ 1`;
- **testigo verificado**: `hp017#2` figura `clase=synthesis-miss`, `n_support_raw=0`,
  **`n_support_served=1`** — y su carrier real (p43, `94cbb0ce`) **nunca se sirvió**; lo servido
  era la p45. La sonda de s321 prueba 3/3 a 5/5 con el correcto.

**Raíz (TECH_DEBT #79)**: el soporte se acredita **POR HECHO, no por mitad**. En un compuesto, un
chunk que sostiene una mitad ya marca «servido», y el fallo se etiqueta `synthesis-miss` —«lo
tenía y no lo escribió»— cuando la verdad es «no se lo dimos». Diagnósticos opuestos.

⇒ **La puerta de población de DEC-175 queda ABIERTA**, ni a favor ni en contra. Cerrarla exige
sondar los 12 `synthesis-miss` con el carrier COMPLETO (~$1 c/u). Declarado, no ejecutado.

## Lo que quiero que ataquéis

1. **Fase 2 · ¿el guard se traga algún resultado legítimo?** Buscad el falso positivo que no vi.
   ¿Es correcta la asimetría (fail-closed solo en el negativo), o es una excusa para no aplicarlo
   donde molesta?
2. **Fase 2 · ¿la prueba de entrega es suficiente?** En `serve` exijo todos los carriers
   admitidos — ¿basta «admitido» o habría que probar que el contenido del carrier cubre el hecho?
3. **Fase 3 · ¿el negativo es real?** ¿Hay OTRO campo del recibo (`in_topk`, `in_pool`,
   `reaches_gen`, `n_support_fam`, los `served_ids` por gold) con el que sí se pueda estimar la
   población, y no lo he mirado? **Este es el punto donde más me desconfío.**
4. **Fase 3 · ¿es correcta la raíz de #79**, o el `n_support_served=1` de `hp017#2` tiene otra
   explicación (p.ej. que el juez de soporte acreditara el chunk correcto y el conteo sea de otra
   cosa)?
5. **¿Qué NO he verificado y debería antes de commitear?**

## Declarado de entrada

- El censo es sobre un recibo del **01-ago** con `sonnet-4-6`; el corpus se ha movido varias veces.
  Aunque el instrumento no fuera ciego, sería orden de magnitud, no cifra viva.
- **No he ejecutado** el sondeo de los 12 — es coste real y quería vuestro veredicto antes.
- La sonda endurecida **no se ha re-corrido** end-to-end: los 8 tests son unitarios sobre las
  funciones nuevas, no una corrida completa con API.

`SÓLIDO` es respuesta válida.
