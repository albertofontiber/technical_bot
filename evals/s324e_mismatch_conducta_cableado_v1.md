# s324e — Cableado de la conducta (a) ante marca↔producto errónea · v1 (BUILD)

**Qué cierra**: DEC-224 §B (Alberto: «corrige Y responde») con el alcance que Alberto adjudicó
hoy en DEC-226: **opción (a)** — la corrección se aplica **solo si hay UNA marca y UN modelo**
que no casan. Con varios modelos o varias marcas el bot responde **como hoy**. La opción (b)
(emparejar por proximidad) queda **anotada como mejora futura**, no implementada.

**Base**: `evals/s321_mismatch_conducta_a_propuesta_v3.md` (11 hallazgos verificados de dos rondas
de Sol, 0 falsos positivos). Sus cinco restricciones se respetan una a una — ver §4.

---

## 1 · Recomendación (lo construido)

Cuatro piezas, todas con el lever `MISMATCH_ANSWER` **OFF por defecto**:

1. **`TurnPlan.preambulo: Preambulo | None`** (`src/orchestrator/turn_plan.py`) — campo NUEVO y
   TIPADO, no un `fallback_ruta` genérico: `fallback_ruta` significa *degradación* (el inventario
   que falla cae a RAG) y esto es lo contrario, una *continuación* deliberada. Para el caso:
   `ruta="conversacional"` + `Preambulo(tipo="mismatch_corrected", modelo, marca_real,
   marca_mencionada)`. Los tres campos son TOKENS validados (charset + ≤40 chars + ≤3 palabras +
   espaciado normalizado), con la disciplina de `Hecho` — este dato viaja al trace persistido.
2. **`runtime_trace.mismatch_corrected`** (`src/rag/runtime_trace.py`) — sección **opcional**
   acotada en el builder (`mismatch_obs=`), con validador propio en el sink. Sin ruta nueva:
   `route="rag"`, se filtra por `rag_trace ? 'mismatch_corrected'`.
3. **F1** (`src/orchestrator/conversation_policy_impl.py`) —
   `resolve_conversational_turn(..., resolved_model: str | None)`: con él, el detector **ni se
   llama** y el modelo servido ES el del preámbulo por construcción.
4. **`MISMATCH_ANSWER`** (`src/flags.py`) — registro + accessor `mismatch_answer_activo()` con
   parser estricto `on|off` (precedente r19/Sol M1). El flag entra al plan **como dato**
   (`Meta.mismatch_answer`): `plan_turn` sigue PURA.

**El texto que lee el técnico** (pineado en test):
`El ASD535 es de Securiton, no de Detnov. Sobre el ASD535 de Securiton:` + línea en blanco +
respuesta RAG. Texto **plano** (sin `*`/`_`): se antepone a una respuesta que se renderiza como
HTML de Telegram y que puede caer al transporte plano; un asterisco suelto sobreviviría a una ruta
y no a la otra.

**Pendiente, descrito y NO aplicado**: `_process_query`/`log_query` en `telegram_bot.py` (fichero
ocupado por otro agente). El diff va en el informe; el test de integración con adapters congelados
compone las cuatro piezas **en el mismo orden** en que lo hará el transporte: es su especificación
ejecutable.

## 2 · Alternativas descartadas

- **(b) emparejar marca↔modelo por proximidad textual** — la descarta Alberto en DEC-226 y la
  comparto: contrato nuevo, superficie de error mayor, y corregir mal es peor que no corregir.
- **Ruta de log propia (`route="mismatch_answered"`)** — la descartó Sol sobre la v1: `query_logs.route`
  tiene CHECK cerrado y `logging_db:80-81` declara bug del emisor un 400 por columna. Se filtra por
  la sección del trace.
- **Sección de trace REQUERIDA con tri-estado** (como `intent`/`timings`/`retrieval`) — descartada:
  aquéllas miden un LEVER y su silencio era ambiguo («sin fallos» vs «sin medir»); ésta registra un
  EVENTO, y la ausencia significa «no hubo corrección», que es cierto con el lever encendido y con
  el apagado. Ser opcional es además lo que hace que con OFF el trace salga **byte-idéntico**.
- **Renderizar el preámbulo en el transporte** (donde viven los textos de las otras rutas) —
  descartado: la voz entra por su propia puerta (`_process_query` directo, sin `plan_turn`) y dos
  copias de la frase son la clase de deriva que produjo #70. `texto_preambulo()` es función pura y
  el transporte decide *si* y *dónde* anteponerla.
- **Leer el flag dentro de `plan_turn`** — rompería la pureza y el punto de decisión único.

## 3 · Gaps y riesgos declarados

1. **Voz FUERA**: el audio no pasa por `plan_turn` (llama a `_process_query` directo), así que un
   mismatch dictado se sirve como hoy. Declarado, no cableado: expandir el plan a voz es decisión de
   producto de fase B.
2. **El conteo de marcas usa el regex CURADO** (`_MANUFACTURER_NAMES`), no la DB: una marca que solo
   existe en la base no suma. El error va al lado seguro — sub-contar **no** enciende la corrección
   (el gate exige exactamente una).
3. **Marcas hermanas cuentan como dos** («Honeywell Notifier») ⇒ no se corrige, se sirve la ruta de
   hoy. Conservador a propósito.
4. **`marca_real` viene de la DB y no está acotada**: si no valida como token, `preambulo_mismatch()`
   devuelve None y se sirve la ruta `mismatch` de siempre. Fail-closed del lever, nunca del turno.
5. **El lever está INERTE hasta que aterrice el diff del transporte**: hoy nadie construye
   `Meta(mismatch_answer=...)`. `MISMATCH_ANSWER=on` no cambia nada todavía. Honesto y verificable.
6. **La conducta (a) no tiene testigo en el harness**: `test_bot_vs_gold` no atraviesa `mismatch`
   (DEC-224). Su verificación end-to-end es **smoke del bot real** tras el flip, no `hp002`.
7. **Un mismatch que además dispara `_FEEDBACK_PATTERNS`** va a RAG con preámbulo en vez de a la ruta
   feedback. Hoy tampoco iba a feedback (la rama `mismatch` retorna antes): se preserva la precedencia.

## 4 · Por qué es BP · estructural · escalable

- **Estructural, no parche**: la decisión vive donde ya vive toda la cascada (`plan_turn`, punto de
  decisión único de DEC-200); el transporte sigue siendo un despachador tonto que ejecuta un plan.
  La alternativa v1 (un `if` en el handler) fue justamente lo que Sol tumbó.
- **Las cinco restricciones del v3, respetadas**: `plan_turn` pura (flag por `Meta`) · trace con
  validador y longitudes acotadas, sin claves libres · `route="rag"` sin tocar el CHECK · F1 con
  modelo explícito (el override de la v2 era inerte) · voz declarada fuera.
- **Escalable a 30+ fabricantes**: el preámbulo es un TIPO (`_TIPOS_PREAMBULO`), no un texto
  hardcoded en una rama; una conducta nueva («producto descatalogado», «marca no servida pero
  respondo lo genérico») añade un tipo y su texto, sin tocar transporte ni trace. Nada depende de
  qué marcas existan: el dato sale del catálogo gobernado.
- **Reversible en un flip**: `MISMATCH_ANSWER=off` (default) devuelve la conducta de hoy sin deploy,
  y la byte-equivalencia con OFF está **probada**, no argumentada (plan idéntico en toda la cascada +
  trace sin una clave nueva).
