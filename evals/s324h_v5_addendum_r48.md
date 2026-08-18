# s324h — Addendum a la v5 tras la r48 (Fable: **SÓLIDO**)

**Veredicto dividido, y la división importa menos de lo que parece.** Fable dio **SÓLIDO**
tras verificar trece anclajes contra el repo: *«Los diez cierres de r47 son reales y
verificables en el artefacto… Los tres hallazgos son de precisión declarativa, no de
diseño.»* Sol dio seis medios — y al revisarlos uno a uno, **también son de precisión
declarativa**: ninguno toca el diseño. Este addendum los cierra sin reescribir la v5.

---

## 1. Son SEIS defaults, no cuatro — y el censo que lo dice estaba roto

Sol encontró dos más. Los verifiqué, y **el intento de refutarle destapó un fallo mío**:

| # | Dónde | Estado en la v5 |
|---|---|---|
| 1 | `src/logging_db.py:135` — `log_query(source="text")` | Ya declarado |
| 2 | `src/orchestrator/contracts.py:45` — `TurnRequest.source = "text"` | Ya declarado |
| 3 | `src/orchestrator/telegram_adapter.py:37` — `build_turn_request(source="text")` | Ya declarado |
| 4 | `supabase_schema.sql:97` — `source TEXT DEFAULT 'text'` | Ya declarado |
| **5** | **`src/bot/telegram_bot.py:1842` — `_process_query(source="text")`** | **NUEVO (Sol)** |
| **6** | **`src/orchestrator/turn_plan.py:373` — `Meta.fuente = "texto"`** | **NUEVO (Sol)** |

*(Adyacente, mismo patrón en otro eje: `contracts.py:41` — `channel: str = "telegram"`.)*

**El episodio que hay que registrar.** Para cerrar de una vez el goteo (3 → 4 → 6), corrí
un censo «exhaustivo» por grep. No devolvió el #6, y estuve a punto de anotar el primer
falso positivo del dúo en toda la sesión. Antes de acusar, verifiqué la línea: **`Meta.fuente:
str = "texto"` está exactamente donde Sol dijo.** Mi grep no lo vio porque llevaba un
`grep -v '#'` para descartar comentarios, y esa línea termina en `# "texto" | "voz"` —
**el filtro se comía justo las líneas documentadas.**

El instrumento con el que iba a corregir al revisor tenía el defecto. Queda escrito porque
es la misma clase de fallo que las seis rondas vienen señalando, esta vez en la herramienta
de medir y no en la afirmación.

**Consecuencia para el alcance:** el #5 (`_process_query`) entra en **Fase 1** — está en el
camino roto y la Fase 1 sólo exigía el reenvío desde `_ejecutar_plan`, dejando viva esa
segunda vía de reetiquetar voz como texto. El #6 se resuelve con `_FUENTE_META` (§2).

## 2. `_FUENTE_META`: sobre-ingeniería declarada, y por qué se queda

Sol: `Meta.fuente` **no gobierna ninguna rama** hoy (`turn_plan.py:562` lo dice: *«meta.fuente
=="voz" NO tiene rama propia en fase A»*), así que traducir entre dos vocabularios y probarlo
es sobre-ingeniería sobre dato muerto.

**Es cierto, y se mantiene igual** — con la razón declarada: son dos entradas y un
`KeyError`. El coste de mantenimiento es *una entrada por canal nuevo*, que es exactamente
lo que debe pasar al añadir un canal. La alternativa —`else "texto"`— es el default mentiroso
que este lote existe para matar, y dejarlo vivo «porque el campo está muerto» es apostar a que
siga muerto. **Se añade el test de completitud** que Sol pedía: el mapa debe cubrir
`_CANALES` entero.

## 3. «Fallo de identidad RESUELTO» era evidencia PROXY — ahora es end-to-end

Sol: la sonda probaba el **clasificador**, no que las consultas **propaguen** el fallo hasta
él. Podrían tragarlo y devolver «marca no servida», que sería mucho peor que una incidencia:
una mentira sobre el catálogo.

**Verificado end-to-end:** `manufacturer_in_db` (`retriever.py:906-918`) no tiene `try/except`
— hace `raise_for_status()` y devuelve. **Propaga.** Y un test nuevo lo ejercita inyectando
`ConnectTimeout` y `HTTPStatusError(500)` en la consulta real: `_resolver_hechos` levanta la
excepción en vez de convertirla en ausencia.

**Límite declarado:** el test de *qué mensaje lee el técnico por voz* sólo puede pasar
**después** del cableado — hoy la voz ni llega a la consulta de identidad. Va al gate como
`xfail(strict)`, igual que los de paridad.

## 4. La migración: atomicidad, idempotencia y postcondición

Sol: tres `ALTER` sueltos repiten el fallo que la 017 evitó — si el `ADD CONSTRAINT` falla,
quedan aplicados `DROP DEFAULT`/`SET NOT NULL` sin vocabulario cerrado.

```sql
BEGIN;
ALTER TABLE query_logs ALTER COLUMN source DROP DEFAULT;
UPDATE query_logs SET source = 'text' WHERE source IS NULL;   -- idempotente; hoy 0 filas
ALTER TABLE query_logs ALTER COLUMN source SET NOT NULL;
ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS query_logs_source_valido;
ALTER TABLE query_logs ADD CONSTRAINT query_logs_source_valido
    CHECK (source IN ('text', 'voice', 'error'));
COMMIT;
```

**Postcondición** (se corre después, y si falla se revierte):
```sql
SELECT count(*) FROM query_logs WHERE source IS NULL;                    -- debe ser 0
SELECT DISTINCT source FROM query_logs;                                  -- ⊆ {text,voice,error}
```

## 5. «Un solo escritor» era falso — otra vez un censo parcial

Sol: hay `INSERT INTO query_logs` **directos** en `tests/test_s295_rgpd_integracion_pg.py:185`
y `:420`, sin `source`, dependiendo del DEFAULT. **Verificado: existen.**

Mi censo miró `src/`, `dashboard/`, `scripts/` y `api/` — **no tests**. Es la tercera vez en
esta sesión que mido un subconjunto y lo presento como completo. Corrección: *el único
escritor de **producción** es `src/logging_db.py`; en tests hay dos INSERT SQL directos que
entran en el radio de la **Fase 2***.

## 6. `Procedencia.de_voz("")` pasaba

Sol: comprobar `is not None` no sostiene «voz exige ASR crudo» — la cadena vacía cuela.

```python
if self.source == "voice" and not (self.transcription or "").strip():
    raise ValueError("una procedencia de voz sin ASR crudo no es auditable")
if self.source == "text" and self.transcription is not None:
    raise ValueError("una procedencia de texto no lleva transcripción")
```

## 7. Cierres de Fable

- **Regla de conteo declarada** (su hallazgo 1): «`TurnRequest(` en todo el repo» = **16**
  ocurrencias sintácticas; **15** excluyendo el constructor interno de `build_turn_request`
  (`telegram_adapter.py:46`), que también es Fase 2. Ambas cifras, y el criterio, explícitos.
- **La asimetría binario/ternario, declarada** (su hallazgo 2): `Procedencia` es el canal de
  un **turno** y por eso es binaria; `'error'` es una pseudo-fuente de **logging** que nunca
  construye una `Procedencia` — la escribe el manejador de errores directamente
  (`telegram_bot.py:2398`). Por eso el tipo es binario y el CHECK ternario, y **no es una
  incoherencia que haya que «arreglar» en ninguna de las dos direcciones**.
- **Las dos mediciones contra producción son puntuales** (su hallazgo 3): las 102 filas y la
  sonda de taxonomía no son verificables desde el repo. La viabilidad de la migración no
  depende de que sigan siendo ciertas — depende del escritor único y de que la fila siempre
  incluya `source`, que sí son propiedades del código.

---

## Estado

**Diseño validado.** Fable: SÓLIDO. Sol: seis hallazgos, todos de precisión declarativa,
todos cerrados arriba. **Se procede al cableado de la Fase 1**, y la ronda siguiente se hace
sobre el **código**, no sobre la propuesta: el diseño ya está revisado; lo que queda por
mirar es la implementación.
