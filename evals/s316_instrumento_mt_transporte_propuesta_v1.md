# s316 — Instrumento: harness conversacional de TRANSPORTE (el prerrequisito de #70)

**Adjudicado por Alberto (10 ago)**: atacar el INSTRUMENTO, no el fix, y que sea
BP/robusto/escalable. Este documento es el diseño; nada cableado.

## Por qué existe (la evidencia, no la intuición)

Dos rediseños de #70 fueron NO-SÓLIDO en la misma tarde, y **las dos veces por la misma
causa: un cambio que habría pasado sus pruebas sin arreglar nada.**

- El v1 limpiaba `last_detected_models` — clave MUERTA en producción (F1 activo lee
  `mt_working_state`). Su test habría quedado verde.
- El v2 se proponía medir con `scripts/test_multiturn_vs_gold.py`, que llama a
  `policy.resolve` **directamente**: `grep -c "handle_message\|user_data\|catalog_shortcut"`
  sobre ese fichero da **0**. Habría pasado con la guarda sin cablear.

El agujero no es de diseño: **es que no existe forma de VER el fallo**. El fallo orgánico
de Alberto (9-ago 21:58-21:59Z) vive en la costura entre el enrutado de `handle_message` y
el estado conversacional de `_process_query`, y hoy ningún test recorre esa costura.

**OBJETIVO + MÉTRICA de HOY**: un instrumento que **reproduzca el fallo orgánico**.
Criterio de aceptación, y es el que importa: **debe salir ROJO sobre el código de hoy**
en el caso A→B→C, y VERDE en el control de compatibilidad. Un instrumento que pasa sobre
un sistema que sabemos roto no vale nada — es exactamente la trampa de las dos rondas
anteriores.

**LEVER**: ninguno. No toca retrieval, ni generación, ni la política. Es test
infrastructure; el eval single-turn no se mueve por construcción.

## Qué cubre, y qué NO (complementariedad declarada)

| Capa | Instrumento | Qué prueba |
|---|---|---|
| Política conversacional | `scripts/test_multiturn_vs_gold.py` (EXISTE) | `policy.resolve` aislado: clasificación, rewrite, ventana |
| **Transporte + estado** | **este, NUEVO** | `handle_message` real: enrutado, retornos tempranos, `context.user_data`, transición de `mt_working_state` entre turnos |

No sustituye al primero. El fallo de #70 es invisible para el primero **por diseño**: la
política nunca ve el turno que rompe el estado.

## Diseño

1. **Conduce el punto de entrada REAL.** Un `Update` y un `Context` falsos con un `dict`
   de verdad como `user_data`, persistido entre turnos de la misma conversación. Se
   invoca `handle_message` — no la política, no el orquestador.
2. **$0 por defecto.** Se stubean las piezas caras (retrieval, generación, red Telegram),
   **nunca** el enrutado ni el estado: eso es justo lo que se mide. Un fallo de plomería
   determinista no necesita LLM. Modo `--vivo` opcional para el end-to-end.
3. **Golds en YAML, no en código** (mismo patrón que `evals/multiturn_golds_v1.yaml`):
   una conversación = lista de turnos; por turno se afirma **ruta**, **estado resultante**
   (`mt_working_state.last_target_models`) y, opcionalmente, un substring de la respuesta.
   Casos nuevos = datos, no código.
4. **Puerta de cobertura por RUTA (la parte estructural).** Las rutas son un contrato
   observable: el código las declara en `log_query(route="…")`. El instrumento las
   **enumera del fuente por AST** y **falla si una ruta declarada no tiene ningún gold que
   la ejerza**. Hoy son 8: `catalog_shortcut`, `manufacturer_no_model`,
   `manufacturer_mismatch`, `clarify`, `coverage_append`, `already_served`, `rag` (default)
   y el implícito de las ramas sin log. **Añadir la ruta nº9 sin caso rompe CI.**
   Esto responde a la objeción de Sol al v2: un instrumento no puede depender de que
   alguien se acuerde de cubrir su ruta.
5. **Primer contenido**: (a) el fallo orgánico A→B→C reconstruido de `query_logs`, que
   debe salir ROJO; (b) el control de compatibilidad («¿es compatible con X?»), VERDE;
   (c) un caso por cada ruta declarada, para arrancar la puerta con cobertura completa.

## Alternativas consideradas y descartadas

- **Extender `test_multiturn_vs_gold.py`**: mezcla dos capas con contratos distintos en un
  script que ya tiene su gate y sus golds; y su bucle está construido alrededor de
  `policy.resolve`, no de un handler async con `Update`. Se declara la complementariedad
  en ambos docs en vez de fusionarlos.
- **Test unitario del handler, sin golds**: es lo que proponía mi v1. No escala (cada caso
  es código), no tiene puerta de cobertura y no habría detectado ninguno de los dos
  no-ops de hoy.
- **Test end-to-end contra Telegram real**: no determinista, no $0, no ejecutable en CI.
- **Medir en producción con `query_logs`**: es diagnóstico *a posteriori* — el fallo ya
  le llegó al técnico. Sirve para descubrir, no para gatear un cambio.
- **Esperar a la Fase 2 y su métrica MT**: deja #70 sin poder arreglarse mientras tanto, y
  el fallo es de uso real, no hipotético.

## Gaps / riesgos declarados

1. **Fidelidad del doble.** Un `Update`/`Context` falso puede divergir del real
   (`python-telegram-bot`). Si diverge en lo que importa —el diccionario `user_data` y el
   orden de llamada—, el instrumento mentiría. Mitigación: stubear lo MÍNIMO y afirmar
   sobre el estado, que es un `dict` de verdad; no sobre mocks.
2. **La puerta de cobertura mide RUTAS, no comportamientos.** Una ruta cubierta por un
   gold trivial cuenta como cubierta. Es un suelo, no una garantía — hay que decirlo en el
   doc para que nadie lo lea como «todo probado».
3. **La enumeración por AST es frágil ante refactor**: si alguien pasa la ruta como
   variable en vez de literal, la enumeración la pierde. Se declarará y el parser fallará
   ruidosamente ante un `route=` no literal, en vez de ignorarlo.
4. **No mide CALIDAD de respuesta**, solo enrutado y estado. La utilidad conversacional
   sigue siendo del eje MT de Fase 2. Este instrumento no la sustituye ni la anticipa.
5. **`handle_voice` es un entrypoint aparte** que no pasa por `handle_message`: debe
   entrar en el censo de la puerta o quedará fuera, y es justo el tipo de agujero que
   este instrumento existe para impedir.
6. **Coste de mantenimiento**: un harness más que mantener alineado con el handler. Si el
   handler se refactoriza a fondo (Fase 2), habrá que rehacerlo.
7. **No arregla #70.** Es explícitamente el paso previo. Al terminar, #70 seguirá abierto
   — pero por primera vez será demostrable.

## Por qué BP + estructural + escalable

- **BP**: el criterio de aceptación es que el instrumento FALLE sobre el bug conocido
  antes de que exista fix alguno — la única forma de saber que mide algo. $0 y
  determinista, así que se puede correr en cada cambio. Golds como datos.
- **Estructural**: ataca la causa de las dos rondas fallidas (no hay forma de ver el
  fallo), no el síntoma (#70). Y la puerta de cobertura convierte «acuérdate de cubrir tu
  ruta» en un fallo de CI.
- **Escalable**: cada transporte o ruta nueva entra por la puerta; los casos crecen como
  datos; y cuando la Fase 2 unifique el estado conversacional, este harness es el que dirá
  si la unificación rompió algo.
