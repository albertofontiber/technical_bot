# s324h v5 — El default que miente está CUATRO veces (y la cuarta es la base)

> **Quinta versión.** La r47 fue la primera **sin ningún crítico**, y Fable verificó uno a
> uno los anclajes de la v4 contra el repo: *«El trabajo de medición es real, no
> retórico»*, veredicto **«casi sólido»**. Esta v5 cierra los diez hallazgos de esa ronda.
> Dos de ellos desmontaban afirmaciones de la propia v4, incluida —otra vez— una medición
> que presenté como completa y era parcial.

---

## 0. Lo que la r47 corrigió de la v4

| Hallazgo | Quién | Qué era falso |
|---|---|---|
| `Procedencia` no impone su invariante | **Sol + Fable** (convergente) | `Procedencia(source="voice", transcription=None)` es construible: los classmethods no hacen privado el constructor. «Irrepresentable» era la misma sobre-afirmación que la v2 |
| El default existe una **CUARTA** vez | Sol | `query_logs.source TEXT DEFAULT 'text'`, nullable y sin CHECK (`supabase_schema.sql:97`). La autoridad final conservaba la mentira |
| El «radio medido» era **parcial** | Sol | Sólo censé `src/` y los dobles `lambda **k`. Faltaban 15 construcciones de `TurnRequest`, 8 de `build_turn_request` y **14 llamadas directas a `log_query` en tests**, algunas posicionales |
| El gate omite `mismatch` | Sol | La ruta de seguridad cross-brand no estaba en la tabla (`turn_plan.py:595-603` la produce) |
| `Meta.fuente` colapsa canales | Sol | `"voz" if source == "voice" else "texto"` — **el mismo default mentiroso que denuncio, en mi propio código** |
| B1 sobre-declaraba el coste | Fable | El tragado exige un **voto previo**: `set_feedback_comment` es PATCH, no upsert. Sin voto devuelve False y el mensaje sigue su curso. Repetí el hallazgo de Opus 5 sin verificar su alcance |
| «Puertas ya verificadas» | Sol + Fable | El test AST estaba declarado «pendiente» en el mismo documento |

---

## 1. El diagnóstico, ahora completo

```
src/logging_db.py:135                      log_query(source: str = "text", ...)
src/orchestrator/contracts.py              TurnRequest.source: str = "text"
src/orchestrator/telegram_adapter.py:37    build_turn_request(source: str = "text", ...)
supabase_schema.sql:97                     source TEXT DEFAULT 'text'   ← la autoridad final
```

**Cuatro capas, el mismo default optimista.** Un default sólo debe existir cuando el valor
omitido es verdad; `"text"` es la mitad de los casos. Por eso el bug reaparece en sitios
sin relación aparente, y por eso la r44 vio que mi propio arreglo creaba otra instancia.

**Síntoma que lo destapó** (Alberto, con la transcripción ya correcta): «¿Qué centrales de
Detnov tienes?» por voz → «no he encontrado información relevante»; tecleada → el listado.
Las dos formas planifican `ruta='inventario'` idéntica; `handle_voice` nunca llama a
`plan_turn` (`telegram_bot.py:1391-1404`).

---

## 2. El diseño

### 2.1 `Procedencia` — la invariante en el TIPO, no en los constructores

```python
_CANALES = {"text", "voice"}

@dataclass(frozen=True)
class Procedencia:
    """De dónde viene el turno. Se construye UNA vez, en el manejador."""
    source: str
    transcription: str | None = None

    def __post_init__(self):
        # La invariante vive AQUÍ, no en los classmethods: `Procedencia(...)` es
        # público y saltárselos es trivial (Sol y Fable, r47, convergente).
        if self.source not in _CANALES:
            raise ValueError(f"canal desconocido: {self.source!r}")
        if (self.source == "voice") != (self.transcription is not None):
            raise ValueError(
                "voz exige ASR crudo, y texto no puede llevarlo: "
                f"source={self.source!r} transcription={self.transcription!r}")

    @classmethod
    def de_texto(cls): return cls(source="text")

    @classmethod
    def de_voz(cls, asr_crudo: str): return cls(source="voice", transcription=asr_crudo)
```

Ahora sí es cierto: **no existe una `Procedencia` de voz sin ASR crudo, ni de texto con
él, ni de un canal inventado.** Y hay test que lo prueba, en vez de una afirmación.

**No es un tercer vocabulario** (Sol, r44 M5): `build_turn_request` pasa a derivar de ella
sus dos campos en vez de tener su propio default. Un origen, varios consumidores.

### 2.2 `Meta.fuente` — mapa explícito, sin colapso

La v4 escribía `"voz" if source == "voice" else "texto"`, que manda cualquier canal futuro
a «texto» en silencio: **el defecto que el lote arregla, reintroducido por mí** (Sol, r47).

```python
_FUENTE_META = {"text": "texto", "voice": "voz"}
...
meta = Meta(..., fuente=_FUENTE_META[procedencia.source])   # KeyError, no colapso
```

Un canal nuevo revienta ruidosamente en el test en vez de clasificarse mal en producción.

### 2.3 Frontera: obligatoria en la firma

```python
async def _ejecutar_plan(update, context, user_id, query, plan, *, procedencia): ...
async def _responder_atajo(update, respuesta, *, user_id, query, registrar, procedencia): ...
```

Y la caída conversacional —el crítico convergente de r44— la reenvía:

```python
await _process_query(update, context, query, preambulo=plan.preambulo,
                     source=procedencia.source, transcription=procedencia.transcription)
```

---

## 3. Alcance en DOS fases, y por qué se parte

El radio real, **re-medido tras el hallazgo de Sol** y esta vez completo:

| | Censo real |
|---|---|
| `log_query` en producción | 8, todos en `telegram_bot.py`; 4 ya pasan `source` |
| `log_query` **directo en tests** | **14** (algunos posicionales: `log_query(1, "q", ...)`) |
| `TurnRequest(` en todo el repo | **15** |
| `build_turn_request(` en todo el repo | **8** |
| Escritores de `query_logs` | **1** — `src/logging_db.py` (dos `POST`); el resto son lecturas |
| Valores de `source` en producción | 102 filas: `text`×98, `voice`×4, **0 nulos** |

**FASE 1 — este lote. Cierra lo que está ROTO.**
`Procedencia` + preludio compartido + frontera obligatoria + reenvío en la caída
conversacional + `log_query` exige `source`. Toca 8 call sites de producción y ~14 de
tests.

**FASE 2 — lote aparte. Endurecimiento del mismo patrón, que HOY NO está roto.**
`TurnRequest` / `build_turn_request` sin default, y la migración de la base. **Distinción
declarada:** el orquestador recibe hoy `source` correctamente desde `_process_query`; su
default es una trampa esperando, no un fallo activo. Meterlo aquí sería el cuarto
ensanchamiento del lote, y las tres rondas anteriores dicen cómo acaba eso.

### 3.1 La migración de la Fase 2, escrita y NO aplicada

```sql
ALTER TABLE query_logs ALTER COLUMN source DROP DEFAULT;
ALTER TABLE query_logs ALTER COLUMN source SET NOT NULL;
ALTER TABLE query_logs ADD CONSTRAINT query_logs_source_valido
    CHECK (source IN ('text', 'voice', 'error'));
```

**Viabilidad medida:** 0 nulos, un solo escritor, y el CHECK **incluye `'error'`** porque
el código lo escribe (`telegram_bot.py:2398`) y una vista filtra por él
(`supabase_schema.sql:674`). Omitirlo repetiría el fallo que la migración 017 evitó: un
INSERT que revienta en producción justo cuando hay un error que registrar.

Por eso `source` **no** se tipa `Literal["text","voice"]`: el dominio real es ternario.

---

## 4. Fallo de identidad: RESUELTO, no pendiente

Medido con sonda sobre `error_taxonomy`:

| Excepción de la consulta de identidad | Clase | Conducta |
|---|---|---|
| `ConnectTimeout` / `ReadTimeout` / `ConnectError` / 5xx | `red_datos`, reintentable | «No he podido consultar la base de manuales ahora mismo… vuelve a enviarme la pregunta en unos segundos» |
| 401 | `bug`, grave, **no** reintentable | «…es un defecto» |

Ya distingue «reintenta» de «esto es un bug» — más fino que el mensaje único que la v3
proponía. **No se añade ninguna frontera de fail-open**: la de la v2 fue matada por Sol
(regresión de SEGURIDAD: saltarse `mismatch`/`marca_no_servida` puede dar respuesta
cross-brand) y por Fable (regresión de OBSERVABILIDAD: desmonta la telemetría de
`bot_errors`). La conducta de hoy se conserva y es la correcta.

---

## 5. Cambios de conducta declarados

| # | Cambio | Alcance EXACTO |
|---|---|---|
| B1 | `_capture_reply_explanation` corre también en voz | **Estrechado tras Fable r47**: el tragado sólo ocurre si existe un **voto previo** en `answer_feedback` — `set_feedback_comment` es PATCH, no upsert (`logging_db.py:497`). Sin voto devuelve False y el mensaje sigue su curso. Y **ya pasa hoy en texto**: no nace aquí |
| B2 | `es_reply` en voz pasa a `True` en replies ⇒ deja de invalidar | Es la conducta del texto. Fila propia en el gate, **afirmando estado** (`mt_working_state`), no mensajes |
| B3 | Cortesía hablada deja de registrar fila | Coherente con la promesa v7 |
| B4 | Feedback hablado se captura como feedback | Ver L1 |

## 6. Límites — lo que NO arregla

- **L1** — Feedback hablado sin ASR crudo en ningún almacén: `log_feedback` no acepta
  `source`/`transcription` (`logging_db.py:326-332`). Hueco de esquema.
- **L2** — `_capture_reply_explanation` traga preguntas cuando hay voto previo.
  Preexistente en texto.
- **L3** — Clarify por voz ya pierde `transcription` hoy (`telegram_bot.py:1913, 2027`).
- **L4** — No compra paridad bilingüe (`language="es"` + catálogo EN en `xfail(strict)`).
- **L5** — No aborda «no te he entendido». Fable (r46): su causa raíz ya se atacó con el
  cambio de modelo ASR (s324g); y Sol (r45): «cero marcas reconocidas» **no** demuestra
  «el ASR no entendió» — el reconocedor es un regex curado más el léxico de servidas.
  **Nota de Alberto (18-ago)**: la asimetría es correcta —el corrector se aplica sólo a
  voz, porque un texto tecleado dice lo que quiso decir—; lo que falta es **generar** las
  variantes de las 30 marcas como ya se generan las de los modelos, en vez de coleccionar
  confusiones observadas. Lote propio.
- **L6** — Sin smoke real contra Telegram hasta que Alberto mande un audio.

## 7. Las puertas

`tests/test_s324h_paridad_voz_texto.py` está en el repo y **verificado que discrimina**:
hoy falla en lo roto y pasa en lo que funciona.

1. **Paridad — se AÑADE la fila `mismatch`** (Sol, r47): faltaba justo la ruta de seguridad
   cross-brand. Compara la secuencia completa de mensajes, no sólo la respuesta.
2. **Procedencia con aserción ANTI-VACUIDAD.**
3. **No-regresión ×3** — PASAN hoy y protegen la ruta conversacional.
4. **B2 afirma estado**, con frase discriminante verificada por sonda.
5. **Invariante de `Procedencia`** — test nuevo: los tres estados inválidos deben lanzar.
6. **Test AST** exigiendo `source=` **y** `transcription=`. **Pendiente de escribir, y así
   se dice**: la v4 decía «puertas ya verificadas» en el mismo documento que lo declaraba
   pendiente (Sol y Fable, r47).
7. **Equivalencia s316e**: sus *asserts de conducta* son intocables; la *fixture* se adapta
   mecánicamente para pasar `procedencia`. Distinción explícita.

**Mecanismo del marcador** (Fable, r47): es `pytest.mark.xfail(strict=True)` gobernado por
la constante `VOZ_CABLEADA_AL_PLAN`, que se pone a `True` **en el mismo commit** que
cablea. Al ser estricto, si el cableado llega y la constante no se toca, la suite lo canta
por XPASS en vez de dejar la puerta abierta en silencio. La razón del marcador se corrige:
decía «pendiente de adjudicación» y la adjudicación de Alberto ya existe.

## 8. Por qué es BP, estructural y escalable

**BP**: ningún default afirma algo que puede ser falso, y un turno de voz no puede quedar
registrado como texto sin que la suite lo cante.

**Estructural**: ataca la causa —el default replicado— y no el síntoma. Tras la Fase 1 el
bug no se puede reintroducir en el camino roto; tras la Fase 2, tampoco en la base.

**Escalable**: un canal nuevo construye su `Procedencia`, y si alguien olvida mapearlo a
`Meta.fuente` **falla en el test** en vez de clasificarse mal en producción.

**Lo que NO se afirma**: no mejora el fail-open, no arregla el hueco de esquema del
feedback hablado, no aborda «no te he entendido», no da paridad bilingüe, y la Fase 2 no
está incluida.
