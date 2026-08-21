# s332 · Correcciones y asunciones VISIBLES — propuesta v1 (21-ago-2026)

> **Mandato de Alberto (21-ago, GO doble con requisito nuevo):**
> 1. GO a la tabla de confusiones ASR (el fix diferido de DEC-233) — **con aviso al usuario**:
>    «avisar que estás incluyendo productos sobre marca/modelo X, que no corresponde con el que
>    ha detectado pero que crees que puede ser ese al que se refiera, y que si no es así lo
>    indique». Y que ese aviso sea **GENERALIZABLE** a otros puntos de la conversación.
> 2. GO a la corrección de marca sin estado («me refería a Kidde» → plantilla vacía).
>
> Estado: PROPUESTA (pre-dúo). Nada cableado. Flags default-off = byte-idéntico.

## 0 · La evidencia (query_logs, 21-ago 07:45-07:49Z — leída verbatim, no de memoria)

| id | turno | qué pasó |
|---|---|---|
| `02055e5d` 07:45 (voz) | «¿Qué centrales **BQide** tienes?» | Whisper destrozó «Kidde»→«BQide». Sin marca ni modelo → «No tengo documentación de "BQide"». Puerta 1 NO disparó (correcto: `_mention_intrinsic_ok` exige forma de modelo letra+dígito; «BQide» es alfabético puro). |
| `576a7ef9` 07:46 (texto) | «**me refería a Kidde**» | Cascada B → `new_brand_no_state` (impl:748-756) → STANDALONE con la **meta-frase literal** como query → retrieval sin señal → plantilla vacía «No he encontrado información relevante…». **EL GAP 2.** |
| `2b3febb6` 07:47 (voz) | «¿Qué centrales **ID** tienes?» | Whisper destrozó «Kidde»→«ID». El bot respondió **ID3000/ID3002 (Notifier) con confianza** — contenido de OTRA marca. **La clase peligrosa: la confusión cae sobre una familia REAL.** |
| `838e71a6` 07:48 (voz) | «¿Qué centrales de la marca ID tienes?» | Ídem: listado ID3000/ID3002 desde fragmentos. |
| `6ee97e80` 07:48 (texto) | «¿qué centrales de la marca Kidde tienes?» | **La conducta objetivo, ya probada por Alberto a mano**: ruta `catalog_shortcut` → listado gobernado completo (36 centrales). |

Más la observación fundacional: «Detnov»→«Death Knob» (17-ago, piloto día 1; ya corregida por la
tabla existente). Total clase DEC-233: **≥4 observaciones en 4 días de piloto.**

## 1 · Qué existe YA (verificado en código, no de memoria)

- **La tabla existe** con 1 fila: `_CONFUSIONES_OBSERVADAS` en `src/bot/whisper_vocabulary.py:44`
  (`death knob → Detnov`), aplicada por `corregir_transcripcion()` — **incondicional y MUDA**
  (nadie sabe qué fila disparó; no se avisa al usuario).
- **Dónde se aplica** (adjudicado por el dúo r40 de DEC-233, contrato del módulo): dentro de
  `normalize_voice_query` (`voice_query_normalization.py:241`) — `raw` intacto para el registro,
  la forma corregida es la de búsqueda.
- **La superficie natural del aviso YA existe**: la confirmación de voz del bot
  (`telegram_bot.py:1371-1378`) imprime «🎤 {raw}» y, si hubo reescritura de MODELO,
  «🔎 Modelo interpretado: …». Las correcciones de MARCA hoy NO aparecen ahí (la dataclass no
  las reporta).
- **El material del rebuild del gap 2 YA está en el estado**: `advance_working_state`
  (impl:992-1000) guarda `last_query` + `last_turn_at` **también en turnos sin modelos**; y
  `WorkingState.within_window()` depende SOLO de `last_turn_at`. El `in_window` de la cascada
  añade `last_target_models` — por eso la corrección cae hoy en `new_brand_no_state`. **No hace
  falta cambiar el esquema de estado: solo un predicado propio en la rama nueva.**
- Ruta del pipeline: `plan_turn` (atajos de catálogo) corre ANTES del seam F1 — un rebuild hecho
  en F1 no puede alcanzar el `catalog_shortcut` sin re-entrada.

## 2 · Recomendación

### 2.A Primitiva generalizable: `Asuncion` (la pieza que pide Alberto)

Una dataclass mínima y un renderizador ÚNICO y DETERMINISTA (cero LLM — la conducta no se
delega al prompt):

```python
@dataclass(frozen=True)
class Asuncion:
    kind: str        # 'marca_asr' | 'marca_corregida' | (futuros: 'alias', 'paraguas'…)
    detectado: str   # lo que llegó (ASR crudo / token del usuario)
    asumido: str     # el término gobernado que se asume (token de catálogo)
    modo: str        # 'reescrito' (se buscó con lo asumido) | 'aviso' (NO se reescribió)
```

Dos superficies de render, ambas en la capa BOT (determinista, byte-nivel):
- **Pre-turno (voz)**: línea extra en la confirmación existente —
  `🏷 Entiendo que preguntas por *Kidde* (el audio se transcribió como «BQide»). Si no es eso, dímelo.`
- **Post-respuesta (aviso / corrección)**: sufijo `ℹ️ …` añadido por el bot al mensaje saliente.

Observabilidad: sección `asunciones` en `rag_trace` (patrón tri-estado de `turn_identity`) con
**kinds + modos + counters + asumido (token de catálogo = controlado)**; `detectado` NUNCA va al
trace (es contenido de usuario/ASR — allowlist de privacidad de s331 intacta).

Por qué es la generalización correcta: cualquier punto futuro donde el sistema sirva algo
distinto de lo literalmente detectado (alias dudoso, paraguas con/sin variantes, fuzzy) produce
una `Asuncion` y ambas superficies la renderizan sin código nuevo.

### 2.B Tabla de confusiones: filas nuevas CON MODO (la lección del caso «ID»)

La fila deja de ser `(patrón, correcto)` y pasa a `(patrón, correcto, modo, cita)`:

| fila | modo | por qué |
|---|---|---|
| `death knob → Detnov` (existente) | `reescrito` | Sin lectura legítima; ya en producción. |
| **`bqide → Kidde`** (nueva) | `reescrito` | Sin lectura legítima («BQide» no existe en ningún catálogo). Cita: `02055e5d`. **+ Asuncion(marca_asr, reescrito) → aviso en la confirmación de voz.** |
| **`ID ↔ Kidde`** (nueva) | **`aviso`** | «ID» ES una familia real (ID3000/ID3002, Notifier): reescribir corrompería consultas legítimas. Solo en `source=voice` y token «ID» aislado (no `ID3000`): la respuesta sale INTACTA sobre ID + sufijo: `ℹ️ Respondo sobre «ID» tal como llegó. Si dictaste otra marca (hay confusión de voz observada ID↔Kidde), dímelo y te lo miro.` Citas: `2b3febb6`, `838e71a6`. |

Disciplina DEC-233 intacta: **solo lo observado, con cita**. El modo `aviso` es la vía para
observaciones cuya reescritura sería peligrosa — antes no había NINGUNA vía y la fila se quedaba
fuera (o peor, se reescribía).

Mecánica: `corregir_transcripcion` pasa a devolver también las filas que dispararon
(`(texto, tuple[Asuncion,...])`; wrapper de compat para la firma vieja — único caller:
`normalize_voice_query`). `VoiceQueryNormalization` gana `asunciones: tuple[Asuncion,...]`.

### 2.C Corrección de marca sin estado (gap 2)

**Rama nueva en la cascada F1** (en `resolve()`, al INICIO de la rama B — antes de
`new_brand_no_state` y de `brand_compatibility_in_window`):

Condiciones (todas):
1. Cue de corrección por léxico gobernado (`config/correction_lexicon_v1.yaml`: «me refería a»,
   «me refiero a», «quería decir», «quise decir», «no, es» …) — mismo patrón que
   `confirmation_lexicon_v1.yaml`.
2. Marca gobernada en el turno (la rama B ya la tiene: `matched_brands`).
3. El turno es ESENCIALMENTE la corrección (sin sustancia extra: presupuesto de tokens
   residuales ≤2 tras quitar cue+marca — «me refería a Kidde» pasa; «me refería a Kidde, ¿y el
   lazo?» NO pasa y sigue la cascada de hoy).
4. `working_state.last_query` existe y `within_window(now)` (ventana de `last_turn_at`, SIN
   exigir modelos — el predicado que hoy no existe en la cascada).
5. `real == ()` (un modelo explícito en el turno ya ganó en A — correcto).

Resolución: `STANDALONE` con `rationale="brand_correction_rebuild"`,
`query_for_retrieval = f"{last_query} (el usuario corrige: la marca es {marca})"` (fallback
SEGURO, mismo patrón probado de `pending_confirmed_family`), `target_models=()`,
`turn_identity` poblado + `Asuncion(marca_corregida, detectado=?, asumido=marca, reescrito)`.
Estado tras el turno: transición de RESPUESTA normal (el rebuild ES el nuevo `last_query`).

**Upgrade opcional en el seam del bot (flag on, mismo flag)**: si `rationale ==
"brand_correction_rebuild"`, el bot intenta el **oráculo-de-plan**: por cada token no-gobernado
de `last_query` (pre-filtro barato), sustituye la marca corregida y llama `plan_turn` sobre el
texto resultante; si EXACTAMENTE UNA sustitución produce ruta de atajo (`inventario`), despacha
ESE plan (→ el listado gobernado completo de `6ee97e80`, la conducta objetivo). Si ninguna o
varias: usa el fallback de F1 tal cual (RAG con contexto). El parser del plan es el oráculo —
**cero léxicos nuevos, cero segunda implementación del parseo** — y el intento es acotado
(≤ nº tokens de last_query llamadas a una función pura y barata).

MT-1b: la rama F1 se espeja en el harness (regla determinista); el upgrade-de-plan es capa bot
y lo cubre el gate e2e (mismo reparto que el atajo de catálogo hoy, que el MT tampoco ejercita).

### 2.D Flag y ship

**UN flag para el lote**: `CORRECCIONES_VISIBLES` (`on`/`off`, default **off** = byte-idéntico
probado). Gatea: línea de aviso en confirmación de voz, fila `bqide→Kidde`, aviso «ID», rama de
corrección F1 + upgrade de plan, y la sección `asunciones` del trace (off ⇒ `status=off`, patrón
tri-estado). Clasificado en el inventario P1 (`s277_c1_p1_release_config.py`).

Por qué UNO y no cuatro (la preocupación explícita de Alberto sobre la proliferación en
Railway): es una sola clase de conducta («lo asumido se declara»), se enciende y revierte como
unidad, y la graduación DEC-210/211 lo retira tras asentar. La fila `death knob` existente NO se
toca (ya es producción).

## 3 · Alternativas consideradas y descartadas

1. **Reescribir también «ID»→Kidde**: corrompe consultas legítimas de la familia ID (Notifier).
   Descartada por la evidencia misma que la motivó (2b3febb6 sería WRONG para un usuario de
   ID3000). El modo `aviso` captura la observación sin el daño.
2. **Disclosure vía prompt del generador** (como `GENERATOR_NO_REASK`): no determinista, coste
   en cada turno, y el aviso desaparecería en las rutas de plantilla/$0 (justo donde ocurrió el
   incidente). El render byte-nivel en el bot cubre TODAS las rutas.
3. **Corrección de marca en `plan_turn` / pre-plan del bot**: segundo punto de decisión
   conversacional fuera de F1 — la clase que s316e/s324h mataron (dos dueños del mismo juicio).
   F1 es el dueño del estado conversacional; el plan solo se re-consulta como ORÁCULO de formato
   con el rebuild ya decidido.
4. **Cirugía de token por heurística lingüística** (identificar «BQide» como el token malo con
   listas de function-words): léxico abierto no gobernado, frágil en 2 idiomas. El oráculo-de-plan
   da el mismo resultado en el caso que importa y degrada con seguridad al fallback.
5. **Cuatro flags** (uno por pieza): granularidad de rollback que nunca hemos necesitado, a costa
   de la queja real de Alberto (inflación de vars en Railway). Un lote = un flag + graduación.
6. **Fuzzy fonético general (Levenshtein/metaphone) para marcas**: la disciplina DEC-233 lo
   prohíbe («cada entrada inventada es una forma nueva de corromper una pregunta que estaba
   bien») y el veredicto sigue vigente; nada en la evidencia de hoy lo re-abre.

## 4 · Gaps y riesgos declarados

- **R1**: el cue-léxico de corrección puede infra-cubrir fraseos («era Kidde», «Kidde quise
  decir»). Mitigación: léxico gobernado ampliable con OBSERVACIONES (misma disciplina que la
  tabla ASR); el fallo es el statu quo (plantilla vacía), no una regresión.
- **R2**: falso positivo del cue («me refería a Kidde» tras un hilo YA sobre Kidde): el rebuild
  re-sirve la pregunta anterior con la misma marca — respuesta redundante pero correcta, con
  asunción visible. Aceptado (y el caso está en el mini-gate).
- **R3**: `mt_working_state` es IN-MEMORY: tras un restart no hay `last_query` y la corrección
  cae en la conducta de hoy. Limitación heredada de TODO F1 (declarada desde s281), no de este
  lever.
- **R4**: el aviso «ID» dispara también para usuarios legítimos de la familia ID (una línea
  extra, contenido intacto). Coste asumido y visible; se re-adjudica con tráfico.
- **R5**: el oráculo-de-plan depende de que el parser de inventario reconozca el rebuild; si el
  atajo evoluciona, el upgrade se degrada SOLO al fallback RAG (fail-open estructural, sin rama
  muerta).
- **R6**: dos idiomas (ES/EN) en cues y plantillas de aviso — EN entra al léxico desde el diseño
  (como `confirmation_lexicon`), pero las OBSERVACIONES de confusión ASR son ES-only hoy.

## 5 · Por qué BP + estructural + escalable

- **BP**: asunciones visibles + invitación a corregir es conducta estándar de asistentes con
  entrada ruidosa (ASR); determinista y auditable (trace); privacidad por allowlist intacta.
- **Estructural**: ataca la RAÍZ de las dos clases (representación ASR corrupta; corrección del
  usuario sin material de rebuild) en las seams que ya son dueñas (tabla en el módulo con el
  contrato raw-visible; rama en la cascada F1 dueña del estado). Cero parches en call-sites.
- **Escalable a 30+ fabricantes**: la tabla es data gobernada con cita (crece por observación,
  no por código); el cue-léxico es config; la primitiva `Asuncion` sirve para alias/paraguas/
  fuzzy futuros; el oráculo-de-plan reusa el parser único del atajo (una implementación).

## 6 · Métrica y relación con levers medidos (Protocolo 2.5)

- **Objetivo de HOY**: los 4 turnos reales de 07:45-48 (clase conversación-de-catálogo por voz)
  + el gap de corrección. NO es el lever «variantes-en-hilo» (ese quedó SHIPPED+VERIFICADO,
  DEC-257/258/263, métrica = hilo Kidde 2X; este lote NO toca su mecanismo) ni re-abre el
  NO-GO de síntesis (etapa 3, per-fact conveyed — sin relación).
- **DEC-233 (settled-en-diferir)**: su métrica era «1 observación» → hoy hay ≥4 con cita; el
  propio veredicto fijó el umbral de activación («tabla de confusiones observadas»). Coinciden.
- **Sonda de alcanzabilidad DEC-173**: N/A — no es un lever de serving/síntesis para un
  hecho-diana (no hay carrier que inyectar); es conducta de composición/UX determinista.

## 7 · Mini-gates PRE-REGISTRADOS (antes de encender nada)

- **GC0 byte-idéntico**: flag off ⇒ replay de los 5 turnos de §0 + kidde_t3 (G3 s331) sin UN
  byte de diferencia vs HEAD.
- **GC1 replay ON de la mañana**: `02055e5d` → reescrito a Kidde + aviso en confirmación;
  `576a7ef9` → rebuild (ideal: ruta inventario con 36 centrales; aceptable: RAG con contexto
  Kidde y asunción visible; NUNCA plantilla vacía); `2b3febb6`/`838e71a6` → contenido ID
  INTACTO + sufijo de aviso; `6ee97e80` → intacto (texto, sin cue).
- **GC2 no-interferencia**: MT 52/52 con el flag on; suite completa verde; los 8 casos borde del
  cue (con sustancia extra, con modelo explícito, sin last_query, fuera de ventana, tras
  restart, marca ya igual, negación «no era Kidde», EN) con conducta esperada escrita ANTES de
  correr.
- **GC3 conducta A/B** (patrón G3 s331, N=4): kidde-mañana OFF (plantilla vacía) vs ON (respuesta
  con contenido Kidde + asunción) — leído, no solo regex.
- Ship: PR → merge → `CORRECCIONES_VISIBLES=on` en Railway (Alberto) → verificación DEC-099 =
  re-lanzar la conversación de la mañana por VOZ.

## 8 · Traza del dúo

(pendiente — esta v1 va al dúo: Sol xhigh + Fable, emparejados, agentes frescos, cero git
durante la ronda)
