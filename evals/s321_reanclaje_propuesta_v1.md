# s321 — ¿Re-anclar las guardas congeladas tras una adjudicación de gold? · propuesta para el dúo

> **Encargo.** No es «revisa mi código». Es una pregunta de **gobernanza del aparato de
> integridad**: acabo de editar un gold por adjudicación de Alberto y eso ha puesto en rojo 4
> tests de contrato congelado. Propongo «re-anclar». Quiero que ataquéis si eso es correcto, o si
> estoy a punto de neutralizar una guarda por comodidad — que es exactamente la clase de fallo que
> esta misma sesión ha destapado dos veces.

Rama `claude/s321-packet-b2-correcciones`, en worktree propio. El árbol que leéis ya tiene el
cambio del gold aplicado.

---

## 1. Qué ha pasado (hechos, verificados)

Alberto adjudicó el ítem 7 del packet B2: «configuración avanzada» = el submenú **AVANZADO**.
Apliqué la edición **por la puerta** (`gold_store.upsert`, validación 0 errores):

- `hp001` atomic_fact idx 2 (`valor: '1111'`, intacto): `texto` pierde «completa» y gana el ancla
  del submenú; `cita` pasa de `MU-376 p10` a `MU-376 p10 + MC-380 5.4 (p29) y 3.1`.
- Cláusula gemela del `gold_answer` actualizada en el mismo upsert.
- Diff: 14 líneas, todas dentro de `hp001`.

**Suite: 3.828 passed, 4 failed.** Los 4 fallos:

| test | qué dice |
|---|---|
| `test_s205_kidde_visual_canary::test_s205_prereg_is_frozen` | `ValueError: S205 frozen input drift: existing_gold_ledger` |
| `test_s203_kidde_visual_canary::...contract_is_bounded_and_non_merging` | (misma familia) |
| `test_s204_kidde_visual_canary::...contract_and_prereg_are_frozen` | (misma familia) |
| `test_s277_c1_p1_contract::test_contract_rebuilds_byte_semantically_from_frozen_authorities` | `payload_sha256` reconstruido ≠ almacenado |

Mecánica verificada: `s205_run_kidde_visual_canary.py:59-67` carga
`evals/s205_kidde_visual_canary_prereg_v1.yaml` (`status: FROZEN_BEFORE_FRONTIER_EXECUTION`),
recorre `frozen_inputs` y compara `normalized_text_sha(path)` contra el `sha256` grabado. Uno de
esos inputs es **`existing_gold_ledger → evals/gold_answers_v1.yaml`**.

## 2. El precedente que invoco (y que quiero que verifiquéis, no que aceptéis)

El commit **`de0032c` (s286)** dice en su mensaje: «re-anclajes del freeze **exigidos por el
cambio**: … fact-contract regenerado por su builder + prereg_v1 regenerado + pins LF/payload en
prereg v2/v3 y scorer (**manifest histórico b92ff51 INTACTO**), **canarios s203/s204/s205
re-anclados al gold ledger adjudicado**…». Y `972e96b` (s287) aplicó otra tanda de adjudicaciones.

⚠️ **Estoy citando un MENSAJE DE COMMIT como autoridad.** Hoy me he equivocado dos veces
exactamente así (citar una fuente que no decía lo que yo afirmaba). **Verificad contra el diff
real de `de0032c` qué se re-ancló y cómo**, no contra su prosa.

## 3. Lo que propongo

1. Regenerar por su builder lo que sea derivado (contrato `s277`).
2. Actualizar el `sha256` de `existing_gold_ledger` en los preregs de s203/s204/s205.
3. **NO tocar** ningún registro histórico de lo que un experimento pasado ejecutó realmente
   (la línea «manifest histórico INTACTO» de s286).
4. Declarar en el commit qué anclas se movieron y a cuenta de qué adjudicación.
5. Añadir el paso al packet como **coste declarado de cualquier marca** (hoy no aparece en
   ninguno de los 7 ítems), y hacerlo **UNA vez al final** de aplicar todas, no por marca.

## 4. Lo que quiero que ataquéis

1. **¿Es re-anclar lo correcto, o es el arreglo cómodo?** Un prereg `FROZEN_BEFORE_FRONTIER_
   EXECUTION` que fija un fichero **vivo y deliberadamente mutable** (el ruler que Alberto
   adjudica) ¿no es un defecto de diseño? Si cada adjudicación legítima obliga a re-anclar, la
   guarda no distingue «cambio legítimo» de «manipulación»: solo detecta *que* cambió. ¿No debería
   pinnear un SNAPSHOT del gold en vez del fichero vivo?
2. **¿Dónde está exactamente la frontera** entre «guarda viva re-anclable» y «registro histórico
   intocable»? Mi criterio (¿qué corrió un experimento pasado? → intocable) ¿es el correcto, y lo
   aplico bien a estos 4?
3. **El riesgo que más me preocupa:** al re-anclar el sha del ledger, ¿estoy bendiciendo de paso
   cualquier OTRA deriva del mismo fichero que no haya inspeccionado? ¿Cómo se acota a «solo el
   cambio adjudicado»?
4. **¿Una vez al final o por marca?** Con 7 marcas pendientes, ¿tiene efectos distintos?
5. **¿Es esto medio o alto impacto?** Si es alto, ¿qué falta antes de cablearlo?
6. **¿Debería la suite haber fallado?** ¿O el hecho de que 4 tests se pongan rojos ante una
   adjudicación normal indica que el acoplamiento canario↔ruler está mal puesto?

## 5. Declarado de entrada

- **No he verificado** cuál de los 4 se regenera por builder y cuál pide editar un sha a mano. Lo
  propongo sin ese detalle resuelto, a propósito, para no pre-cocinar vuestra lectura.
- El cambio del gold **no altera el denominador** (`valor` intacto ⇒ join key `qid#idx:valor`
  conservada), pero el packet **no advertía** de este coste en ninguna de sus 7 fichas.
- Contexto de la sesión: hoy se destapó que un recibo (s305) nunca leyó al juez, y que dos de mis
  lecturas de fuente eran de modelos equivocados. El sesgo a vigilar en mí ahora mismo es el
  contrario: sobre-corregir y tratar como sospechoso algo que es rutina documentada.

Si la propuesta es correcta, decidlo — `SÓLIDO` es respuesta válida y la prefiero a un hallazgo
fabricado.
