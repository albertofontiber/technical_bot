# s321 — Conducta (a) ante marca↔producto errónea · PROPUESTA v2 (nada cableado)

**v1 → v2.** Sol (ts=2026-08-16T13:08:52) devolvió 6 medios, **0 críticos, 0 falsos positivos** tras
regla C — y tres de ellos tumban el diseño de v1 de raíz: (1) `query_logs.route` tiene un **CHECK
cerrado** y `logging_db.py:80-81` dice que violarlo «es un bug del emisor y debe fallar» ⇒ mi ruta
nueva perdía el recibo; (2) `turn_plan.py` es el **punto de decisión único** por contrato (DEC-200):
«el transporte EJECUTA el plan sin re-examinar el texto» ⇒ «un flag en el handler» repetía el drift
que DEC-200 eliminó; (3) **voz no pasa por `plan_turn`** (`telegram_bot.py:965-998` llama a
`_process_query(source="voice")` directo) ⇒ la conducta (a) es de TEXTO y hay que declararlo. Los otros
tres (log RAG con `route="rag"` por defecto; multi-modelo; el test que solo prueba cableado) van
resueltos abajo.

**Impacto**: MEDIO en zona de dolor ⇒ dúo completo sobre ESTA v2 antes de tocar código. Flag default OFF
byte-idéntico; el ON es acción de Alberto en Railway.

---

## 1 · Diseño v2 — la reacción NACE EN EL PLAN

### 1a · El flag entra por `Meta`, no por `os.getenv` dentro del plan (pureza)

```python
@dataclass(frozen=True)
class Meta:
    es_reply: bool = False
    fuente: str = "texto"
    mismatch_answer: bool = False      # [v2] leído por el shell de MISMATCH_ANSWER, inyectado aquí
```
`plan_turn` sigue siendo pura. El shell (`telegram_bot._resolver_meta` o donde hoy construya `Meta`) lee
`os.getenv("MISMATCH_ANSWER","").strip().lower() in {"1","on","true"}` — el mismo patrón que
`INTENT_LLM` (l.667). `src/flags.py` da de alta `MISMATCH_ANSWER` (`default_fuente: '""'`, `via: getenv`,
`lectores: src/bot/telegram_bot.py`) — lo exige `test_s311_flags_registry`.

### 1b · El plan expresa la conducta con lo que YA tiene: `ruta` + `fallback_ruta`

En `turn_plan.py:455-460`, donde hoy devuelve `_plan(ruta="mismatch", …)`:

```python
if str(real).lower() != resolve_manufacturer_alias(mencionada).lower():
    return _plan(
        ruta="mismatch",
        fallback_ruta=("conversacional" if meta.mismatch_answer else None),   # [v2]
        log_consulta=True,
        datos={"modelo": modelo, "marca_real": str(real), "marca_mencionada": mencionada},
    )
```
Semántica: `fallback_ruta=None` = conducta (b) actual (el mismatch ES la respuesta); `fallback_ruta=
"conversacional"` = conducta (a): el mismatch es un PREÁMBULO y el turno continúa por la ruta
conversacional (RAG). Es **exactamente el patrón de `inventario`** (`telegram_bot.py:1140-1142`: «la
degradación es fallback_ruta, no una segunda decisión del despachador»). No hay ruta nueva ⇒ no hay
CHECK que violar; no hay `getenv` en el plan ⇒ pureza intacta; `test_s316e_fase_a_equivalencia` sigue
byte-equivalente con `mismatch_answer=False`.

### 1c · El handler EJECUTA: si hay `fallback_ruta`, corrige y sigue

En `telegram_bot.py:1178`:
```python
if ruta == "mismatch":
    d = plan.datos
    if plan.fallback_ruta:                                        # conducta (a)
        preambulo = (f"El *{d['modelo']}* es un producto de *{d['marca_real']}*, "
                     f"no de _{d['marca_mencionada']}_. Te respondo sobre el "
                     f"*{d['modelo']}* de *{d['marca_real']}*:")
        await update.message.reply_text(preambulo, parse_mode="Markdown")
        ruta = plan.fallback_ruta          # → cae al bloque conversacional de abajo
        # NO log aquí: lo hace _process_query (una sola fila) — ver 1d
    else:                                                          # conducta (b) = HOY, byte-idéntico
        respuesta = (…texto actual sin cambiar…)
        await update.message.reply_text(respuesta, parse_mode="Markdown")
        if plan.log_consulta:
            log_query(…, route="manufacturer_mismatch", …)
            asegurar_seudonimo(user_id)
        return
```
El bloque `conversacional` del final (`await _process_query(update, context, query)`) recoge la ruta.

### 1d · Log: UNA fila, ruta existente, con la marca de que hubo corrección

`_process_query` loguea con `route="rag"` (default de `log_query`). Para no violar el CHECK y no
duplicar filas: la corrección **no** loguea; `_process_query` loguea su fila `rag` como siempre, y la
señal de «hubo mismatch corregido» va en **`rag_trace`** (jsonb libre, ya existe:
`logging_db.py:97` lo trata como telemetría opcional): `rag_trace["mismatch_corrected"] = {"modelo",
"marca_real", "marca_mencionada"}`. **Cómo llega a `_process_query`**: parámetro nuevo opcional
`extra_trace: dict | None = None` que se fusiona en el `rag_trace` que ya construye. Sin migración SQL,
sin ruta nueva, una fila. **Se pierde**: poder filtrar por `route` las corregidas ⇒ se filtra por
`rag_trace->>'mismatch_corrected'`. Declarado como coste; si Alberto quiere ruta propia, es una
migración versionada aparte (Sol crítico 1) — no en este PR.

### 1e · El modelo resuelto viaja como DATO, la query original se conserva

Sol (medio 4): `_process_query` re-extrae **todos** los modelos de la query y conserva la marca errónea
en la entrada del generador; con «el ASD535 de Detnov y el ADW535…» el scope se ampliaría. Diseño:
`_process_query(update, context, query, target_models_override=[d["modelo"]], extra_trace=…)` —
si viene override, se usa en vez de `extract_product_models(query)`; la **query original** se
conserva para retrieval/log/contexto (no se inventa texto del usuario). Es un parámetro opcional
más; con `None` (default) conducta idéntica.

### 1f · Voz: FUERA de v2, declarado

`handle_voice` no pasa por `plan_turn` ⇒ hoy un audio «el ASD535 de Detnov» **ni siquiera dispara
mismatch** — va al RAG directo con la query transcrita. La conducta (a) para voz sería en realidad
«empezar a detectar mismatch en voz», que es OTRA decisión (v3 §2 del rediseño la dejó para fase B).
Se declara: **MISMATCH_ANSWER afecta solo a texto**; voz sigue como hoy. Se anota en DEC.

## 2 · Alternativas descartadas

- **v1 (flag en el handler, ruta nueva `manufacturer_mismatch_answered`)** — viola DEC-200 y el CHECK.
- **Ruta nueva en el plan (`mismatch_answer`) + migración SQL** — correcto pero más grande: exige
  migración versionada + test SQL + tocar la lista del CHECK. `fallback_ruta` expresa lo mismo con
  vocabulario que ya existe. Si en el futuro se quiere filtrar por `route`, se migra entonces.
- **Reescribir la query con la marca correcta** — inventa texto del usuario; el override de
  `target_models` resuelve el scope sin tocar el texto.
- **Detectar mismatch también en voz** — es fase B del rediseño; fuera de alcance, declarado.

## 3 · Riesgos declarados

1. El técnico se equivocó de **aparato**, no de marca — riesgo aceptado por Alberto; mitigado por el
   preámbulo explícito.
2. `_process_query` gana **dos parámetros opcionales** (`target_models_override`, `extra_trace`).
   Superficie pequeña, default `None` = idéntico. Pero es la función central: sus tests actuales tienen
   que seguir verdes sin tocarlos.
3. Contexto conversacional: el preámbulo va como mensaje aparte y NO se guarda en la sesión; la
   respuesta RAG sí. Turno siguiente «¿y el grande?» resuelve sobre `[modelo]` — correcto.
4. Sin smoke real posible en este PR (no toco prod). Checklist de encendido para Alberto: flip en
   Railway → 3 preguntas (marca errónea texto / marca correcta / audio con marca errónea → debe seguir
   como hoy) → recibo en `query_logs` (`rag_trace->>'mismatch_corrected'`).

## 4 · Qué prueba (Sol medio 6: integración, no solo cableado)

- **Plan** (`test_s316*`/nuevo): `plan_turn` con `Meta(mismatch_answer=False)` ⇒ `fallback_ruta is
  None` (byte-equivalencia con hoy); con `True` ⇒ `fallback_ruta=="conversacional"`, `ruta`, `datos` y
  `log_consulta` idénticos.
- **Handler OFF**: fixture del texto actual; `_process_query` NO invocada; `log_query` con
  `route="manufacturer_mismatch"` exactamente una vez.
- **Handler ON, integración con adapters congelados**: `_process_query` invocada **una vez** con
  `target_models_override==[modelo]` y la query original; **dos** mensajes al usuario (preámbulo +
  respuesta); **una** fila de log con `route="rag"` y `rag_trace.mismatch_corrected` presente; el
  modelo servido en la respuesta = el resuelto (se asserta sobre los chunks del adapter congelado).
- **Marca correcta ON**: no pasa por mismatch; RAG directo sin preámbulo (control `hp019`).
- **Marca no servida ON**: ruta `marca_no_servida` intacta.
- **Voz ON**: audio con marca errónea ⇒ conducta idéntica a hoy (sin preámbulo).
- **Registro**: `MISMATCH_ANSWER` en `REGISTRO`.

## 5 · Lo que el dúo tiene que atacar en v2

1. ¿`fallback_ruta="conversacional"` es semánticamente honesto para «preámbulo + continuar», o abusa de
   un campo pensado para «degradación si falla»? ¿Debería ser un campo nuevo tipado (`preambulo`) en
   `TurnPlan`?
2. `rag_trace` como portador de «mismatch corregido»: ¿es telemetría legítima o esconde una ruta que
   debería ser de primera clase con su CHECK?
3. `target_models_override` en `_process_query`: ¿rompe algún invariante del orquestador/F1 que hoy
   asume que `target_models` sale del texto?
4. ¿Falta algún camino por el que el mismatch se alcance sin pasar por `handle_message` (callbacks,
   replies, grupos)?
