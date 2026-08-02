# s293 — MEDICIÓN de los 2 levers vivos de etapa 3 (hp017#2 · cat017#2)

Estado: **medición cerrada, NADA cableado.** Todo el trabajo de esta fase es diagnóstico
determinista salvo 3 generaciones declaradas. Baseline de la sesión: suite **3427 passed,
5 skipped** en `610f137`; los módulos de coverage/serving/generación son **byte-idénticos**
entre `bf2bf8e` (commit del FULL v3.2) y HEAD → las sondas miden el mismo código que el recibo.

Recibos: `s293_hp017_guard_probe_v1.json` · `s293_guard_censo_v1.json` ·
`s293_lane_replay_cat017_{baseline,pool,hyq}.json` · `s293_hp017_preguard_probe_v1.json`.

---

## A. hp017#2 «Editar Configuración» — supresión por el conflict-guard: CONFIRMADO

**Mecanismo (verificado, no inferido).** La fuente pone el dato del gold y el valor en
conflicto en la MISMA frase, a 12 caracteres:

> «En el menú **«Editar Configuración»**, seleccione **«7: Causa y Efecto»** para abrir la
> función de edición.» — `997-671-005-3_Configuration_ES` p.45, chunk `a95f8659` (F11, 5/5
> votos de soporte servido).

`apply_answer_conflict_guard` repara por **BLOQUE** (`re.split(r"(\n[ \t]*\n)")`): cualquier
párrafo que asevere el valor se sustituye ENTERO por el aviso.

**Evidencia $0** (`s293_hp017_guard_probe_v1.json`, contexto servido real del FULL):
- 13 fragmentos servidos; valores de menú presentes: **solo `7`** ⇒ rama **one-sided** de
  `_render_conflict_notice` (el `8` lo aporta el registro, no la evidencia servida).
- Contra-prueba sobre el guard real: párrafo fiel al carrier **con** el número →
  `surgical_repair` (sustituido); **sin** el número → `pass` (intacto). El guard no puede
  salvar el número sin llevarse la ruta: su unidad de reparación es el bloque.

**Evidencia con generación (3 turnos reales por el seam del harness,
`s293_hp017_preguard_probe_v1.json`):** guard alcanzado 3/3 · `surgical_repair` 3/3 ·
**ruta presente en el borrador PRE-guard 3/3** · **ausente POST-guard 3/3**. Bloque borrado
(rep0):

```
1. En el menú «Editar Configuración», selecciona **«7: Causa y Efecto»** [F11].
2. Crea o edita la regla de causa-efecto correspondiente a la salida de alarma (sirena, relé…).
3. Asigna a esa regla uno de los seis tipos de retardo disponibles [F2][F3]:
```

⇒ El colateral NO es solo el hecho del gold: se pierden los pasos 2 y 3 del procedimiento.
Reproducido pese a composición servida distinta de la del recibo (11/13 comunes) ⇒ el
mecanismo es robusto a la composición.

**El conflicto es REAL e intra-documento** (`s293_guard_censo_v1.json`): el mismo manual dice
`7: Causa y Efecto` en la prosa de p.45 (1 chunk) y `8:Causa y Efecto` en el árbol de menú de
pp.15/26/41 (**7 chunks**). El registro `pearl_cause_effect_menu_7_vs_8_v1` NO es fantasma y
el guard hace bien en no elegir. *(Regla-C: el censo v1 filtraba `ilike '%: Causa y Efecto%'`
—español y con espacio tras los dos puntos— y devolvía solo el `7`, un null falsamente
tranquilizador que habría declarado fantasma el registro. v2 filtra laxo en ambos idiomas.)*

**Blast radius medido:** el guard deja huella en **1/39 golds** del FULL (solo hp017);
de los 12 hechos servidos-y-no-transmitidos, **1** es colateral del guard (hp017#2).

**Lever candidato (NO construido):** reparación **por span** antes de la reparación por
bloque — (1) redacción del valor en conflicto conservando la frase; (2) si tras re-validar
sigue unsafe, sustitución de la línea/frase; (3) si sigue unsafe, conducta ACTUAL (bloque);
(4) validación whole-answer y fail-closed ACTUALES, sin tocar. La garantía se mantiene por
construcción: el criterio de aceptación (el validador) no cambia; solo sobrevive más texto
que ese mismo validador considera seguro.

**Riesgos declarados.** (i) El validador define la seguridad: si es incompleto, sobrevive
texto que él no sabe leer — no se debilita, pero tampoco se refuerza. (ii) La redacción
determinista toca prosa del modelo (riesgo de artefactos gramaticales/markdown). (iii) La
población medida es 1 gold: el retorno en eval es ≤1 hecho; el argumento fuerte es el
procedimiento borrado, no el conteo. (iv) Zona sensible (guard de seguridad numérica) ⇒
dúo obligatorio + flag default-off + A/B ciego, patrón DEC-162a.

**Alternativas descartadas.** Servir el otro lado del conflicto (brazo serving-side: roza
fila settled, y no quita el colateral: el bloque se sustituye igual) · relajar el registro o
el umbral del validador (debilita la garantía) · granularidad de línea/frase COMO ÚNICA
etapa (recupera los pasos 2-3 pero NO el hecho del gold, que vive en la línea infractora).

---

## B. cat017#2 «licencia CLIP por lazo» — probe $0 de lanes: NINGUNA lo cubre

Cierra el paso que **DEC-169** dejó pre-declarado: «probe $0 de las 2 lanes existentes
(`RERANK_POOL_COVERAGE` off-por-stack-C1; hyq doc_scoped pendiente A3) … ANTES de diseñar
lane nueva», sin encender nada (encender `RERANK_POOL_COVERAGE` global está descartado en
DEC-169: re-abre la stack C1).

**Método.** Replay de la ETAPA DE COVERAGE con el pool (50) y el prefijo protegido (top-k 10)
GRABADOS en el recibo del FULL: 0 llamadas a retrieval, rerank o generación.
**Auto-verificación de fidelidad:** el brazo `baseline` reproduce los **4 `appended_ids` del
recibo, en el mismo orden y con las mismas lanes**. *(Regla-C: la v1 copiaba el flag-set a
mano, se dejó fuera `FACET_COMPLEMENT_FALLBACK` y `OBLIGATION_RESERVE_ORDERED`, y el baseline
NO reprodujo el recibo. v2 lee `DEMO_FLAGS` del propio instrumento por AST = fuente única.)*

| brazo | lane añadida | apéndices | ¿trae el carrier `4c186fb2`? |
|---|---|---|---|
| `baseline` (fidelidad ✓) | — | 4 (los del recibo) | **no** |
| `RERANK_POOL_COVERAGE=on` | `retrieval_pool_coverage_v1` | 6 (`c0b2dce8`, `b06ad597`) | **no** |
| `CANONICAL_HYQ_COVERAGE=on` | `canonical_document_hyq_coverage_v1` | 4 (ninguno nuevo) | **no** |

**Diagnóstico más fino que «ninguna lane lo cubre».** La conduct `facet_complement` de
`document_local_content_coverage_v1` **YA detecta la necesidad**
(`need_group_terms: ["sitio", "edificio", "licencia"]`) y la satisface con `b7633e98` —
el chunk **PUNTERO**, el que dice «Consulte la guía del usuario Concesión de licencias para
la central INSPIRE con CLSS (**4188-1125-ES**)» — marcándolo `attested`. La necesidad queda
**dada por cubierta por el puntero, no por el dato**. El payload vive en el documento
REFERENCIADO, fuera del scope document-local de esa lane:

> «**Necesitará una licencia de CLIP para cada lazo CLIP**, por lo que se necesitarán dos
> licencias por módulo si ambos lazos son lazos CLIP.» — `4188-1125-ES` p.17, chunk
> `4c186fb2`, **pool rank 18**, no servido.

El documento referenciado tiene **3 chunks en el pool** (ranks 9, 14, 18) y **ninguno
servido**. Los otros dos brazos fallan por causas distintas y declaradas: la lane de pool
razona por **arquetipo** (`connect_install_wire`: terminales, pantalla/tierra, límites — la
licencia no está en su lista de necesidades); la lane hyq **sí** mete `4188-1125-ES` en scope
(`484dd402`) pero rechaza sus parents por `no_query_aligned_card` / `no_matching_card`.

**Corrección al diagnóstico previo:** el segundo carrier `5bb83899` que citaba DEC-169 **no
está en el pool** de este run (`in_pool: false`); el carrier vivo es `4c186fb2`.

**Lever candidato (NO construido, NO es lane nueva de retrieval):** que un chunk cuya única
coincidencia con la faceta sea una **referencia gobernada a otro documento acreditado por
doc_map** no cuente como necesidad satisfecha, y que la selección siga la referencia hacia
**candidatos del POOL** de ese documento. Sin fetch nuevo, sin llamadas de modelo, acotado
por doc_map.

**Riesgos declarados.** (i) Dimensión medida = **1 hecho** en el eval; DEC-169 exigía
dimensionar antes de diseñar y esta es la dimensión. (ii) Tocar la satisfacción de
necesidades de `document_local_content_coverage_v1` toca la lane **viva en la release C1**
(radio a serving — la clase de fallo que el dúo cazó en L3 s292). (iii) El puntero servido
tiene valor propio (dice DÓNDE está el documento): la regla debe AÑADIR el dato, no
sustituir el puntero. (iv) Requiere dúo + flag default-off + gate de no-desplazamiento
(el prefijo protegido y la capacidad de append son finitos: en el brazo `pool` una lane
extra ya provocó `skipped_no_append_capacity` en otra).

---

## Qué NO se ha hecho (y por qué)

- **Nada cableado**: Protocolo 3 exige dúo (sub-agente + cross-model) ANTES de construir, y
  ambos levers son MEDIO-en-zona-sensible (guard de seguridad / lane viva en release).
- **Ningún eval de PASS**: el trabajo intermedio se mide en su propia métrica
  (`feedback_autonomy` / DEC-071e); el gate de cada lever se pre-registra en su diseño.
