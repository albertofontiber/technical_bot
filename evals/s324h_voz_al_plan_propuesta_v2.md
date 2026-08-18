# s324h v2 — Paridad voz/texto: la procedencia viaja con la consulta

> **v2 tras el dúo r42 (Sol xhigh + Fable 5): los dos devolvieron NO SÓLIDO al contrato
> boceto de la v1, y por la MISMA razón.** La v1 proponía `_servir_plan(...) -> bool`.
> Ese booleano (a) mataba `plan.preambulo` —regresión del lever mismatch en el camino
> de TEXTO, introducida por mi propia refactorización— y (b) dejaba `Meta` construida
> en dos sitios, con la versión de voz omitiendo `mismatch_answer`: la divergencia de
> canal que la propuesta decía atacar, reintroducida por construcción. Y la v1 declaró
> a medias el hueco de auditoría: no era sólo «se pierde el ASR crudo», era que el
> turno quedaría **mal atribuido de canal**. Esta v2 no es un retoque: cambia la pieza.

**Corrección de la v1, visible**: escribí «las SIETE rutas de atajo» y enumeré NUEVE
(inventario, catálogo, fabricantes, 3 cortesías, mismatch, marca_no_servida, feedback).
Son **nueve**.

---

## 0. Objetivo y métrica de GO (faltaba en la v1 — Sol §5)

**Objetivo**: que la MISMA pregunta obtenga la MISMA respuesta por voz y por texto.

**Métrica**: tabla de paridad **9 rutas × 2 canales**. Para cada par (ruta, canal) se
compara: `plan.ruta`, `plan.transicion`, el texto de la respuesta, si hubo `log_query`
y con qué `source`/`transcription`, y el número de llamadas al RAG. **GO = las 9 filas
idénticas salvo en los campos que DEBEN diferir** (`source`, `transcription`).

La v1 decía «diagnosticado y medido» apoyándose en UN caso (inventario) y en la
clasificación de dos cadenas. Eso no es paridad: es un testigo. La tabla es el gate.

---

## 1. El diagnóstico (sin cambios respecto a la v1, verificado por los dos revisores)

`handle_voice` no llama a `plan_turn`: sólo a `_decidir_transicion`, y salta a
`_process_query` (RAG completo). Las **nueve** rutas de atajo son inalcanzables por voz.
Medido: las dos formas de la misma pregunta —la hablada y la tecleada— planifican ambas
`ruta='inventario'` con `datos={'marca':'Detnov','filtros':{'categoria':'central'}}`.

Lo que la v1 NO vio y el dúo sí: **`_ejecutar_plan` ya existe** (`telegram_bot.py:1555`),
ya es un despachador tonto separado y ya posee la caída a conversacional con
`preambulo`. Lo que falta compartir no es el despachador — es el **preludio**.

---

## 2. La pieza: la consulta deja de ser un `str` desnudo

El defecto de fondo no es «falta cablear una ruta». Es que **la procedencia es un
parámetro opcional con un default mentiroso**: `log_query` declara `source: str = "text"`
y `transcription: str | None = None`.

Los nueve atajos llaman `log_query(...)` sin `source`. Hoy da igual porque sólo los
alcanza el texto. En cuanto los alcance la voz, cada turno hablado se registra **como
texto y sin transcripción**, en silencio y para siempre. Olvidar es el comportamiento
por defecto, y ningún test lo nota.

Así que la corrección no es acordarse de pasar el origen: es **hacer irrepresentable el
estado incorrecto**.

```python
@dataclass(frozen=True)
class Entrada:
    """De dónde viene el turno. Lo ÚNICO que distingue voz de texto."""
    query: str                        # forma de búsqueda (normalizada en voz)
    source: str = "text"              # 'text' | 'voice' -> columna de query_logs
    transcription: str | None = None  # ASR crudo; None en texto
```

`_ejecutar_plan` recibe `Entrada` en vez de `query`. A partir de ahí no existe un string
suelto sin origen que se pueda loguear mal, y la ruta que nazca mañana hereda el
contrato de auditoría sin que nadie se acuerde de nada.

### 2.1 El preludio compartido

```python
async def _servir_turno(update, context, user_id, entrada: Entrada) -> None:
    if await _capture_reply_explanation(update, user_id, entrada.query):
        return
    meta = Meta(es_reply=update.message.reply_to_message is not None,
                mismatch_answer=mismatch_answer_activo(),
                fuente="voz" if entrada.source == "voice" else "texto")
    plan = _plan_o_conversacional(entrada.query, estado_modelos, meta)   # 2.2
    if plan.transicion == _turn_plan.INVALIDAR:
        _aplicar_estado(context.user_data, WorkingState())
    await _ejecutar_plan(update, context, user_id, entrada, plan)
```

**`Meta` se construye UNA vez** (hallazgo de Fable): la voz ya no puede olvidar
`mismatch_answer`. **No hay booleano**: `_ejecutar_plan` sigue siendo el dueño de la
caída a conversacional y sigue entregando `plan.preambulo` — el lever mismatch no se
toca, ni en texto ni en voz.

Los dos manejadores quedan reducidos a **obtener la `Entrada`**: texto la lee del
mensaje; voz la transcribe, la normaliza y adjunta el ASR crudo.

### 2.2 Una frontera de fail-open declarada (Sol §4)

`_resolver_hechos` hace llamadas SÍNCRONAS a Supabase (`lookup_model_manufacturer`,
`manufacturer_in_db`) **fuera** del `try` interno de `plan_turn`. Hoy, en voz, un blip
de red ahí escala al `except` exterior y convierte una pregunta contestable en una
incidencia; en texto sube al manejador de errores de PTB.

```python
def _plan_o_conversacional(query, estado_modelos, meta) -> TurnPlan:
    """Frontera ÚNICA: si resolver hechos o planificar falla, se degrada a
    conversacional (la conducta de HOY para la voz), nunca a incidencia."""
```

Queda **mejor que hoy para los dos canales**, no sólo para voz. Es la única parte de
esta propuesta que cambia conducta del camino de texto, y se declara aquí a propósito.

---

## 3. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `-> bool` + caída en el llamador (**la v1**) | Mata `plan.preambulo` ⇒ **regresión del lever mismatch en TEXTO**. Aplana dos continuaciones distintas en un valor que no las distingue. Cazado por los dos revisores |
| Cablear a la voz **sólo** la ruta de inventario | El parche que Alberto ya rechazó en la tabla de transcripción: arregla hoy, deja ocho rutas rotas, y obliga a cablear dos sitios para siempre |
| Fabricar un `Update` de texto y delegar en `handle_message` | Pierde `transcription=raw`, reevalúa consentimiento, reenvía `typing`. Acoplar por un objeto falsificado convierte cualquier campo nuevo en fallo silencioso |
| Pasar `source`/`transcription` como parámetros sueltos a `_ejecutar_plan` | Funciona hoy y falla el día que alguien añada una ruta: vuelve a ser «acuérdate». `Entrada` lo hace estructural |
| Extraer el despachador | Ya está extraído (`_ejecutar_plan`). La v1 no lo había mirado |

## 4. Gaps y riesgos declarados

1. **`_capture_reply_explanation` pasa a correr también en voz.** Es una GANANCIA (hoy
   una explicación hablada en reply se va al RAG — asimetría que señaló Fable), pero es
   cambio de conducta y entra en la tabla de paridad como fila propia.
2. **Cortesía hablada deja de loguearse** (`log_consulta=False`). Coherente con la
   promesa v7, pero es un cambio; un «hola» hablado hoy sí deja fila.
3. **Feedback hablado** pasa a capturarse como feedback en vez de ir al RAG.
4. **Esto NO compra paridad bilingüe** (Sol §6): el ASR fuerza `language="es"` y el test
   de catálogo en inglés sigue en `xfail(strict)`. La v1 lo vendió como «escalable» sin
   haberlo verificado. Se replica la limitación en los dos canales; ni más ni menos.
5. **Sin smoke real contra Telegram** hasta que Alberto mande un audio. Los tests prueban
   el enrutado, no el canal.
6. **La frontera de fail-open cambia conducta del camino de texto** (2.2). Declarado.

## 5. Las puertas que lo prueban

- **Test AST de mecanicidad**: ningún `log_query(` de `telegram_bot.py` puede omitir
  `source=`. Convierte «acuérdate» en «no pasa la suite». Hay precedente en casa — el
  test de mecanicidad por AST de `_resolver_hechos`.
- **Tabla de paridad 9×2** (0) como criterio de GO, no como comprobación de cortesía.
- **Equivalencia byte a byte del camino de TEXTO**: los tests s316e existentes no pueden
  moverse. Si se mueven, la refactorización rompió algo que funcionaba.

## 6. Por qué es BP, estructural y escalable

**BP**: la misma pregunta obtiene la misma respuesta por los dos canales, y la
trazabilidad no depende de la memoria de quien escriba la siguiente ruta.
**Estructural**: ataca que la procedencia fuera un parámetro opcional con default
mentiroso, no la ruta que faltaba. **Escalable**: `Entrada` es el sitio por donde entra
el tercer canal el día que exista, sin volver a tocar el despacho — y el test AST
obliga a cualquier ruta futura a declarar su origen.
