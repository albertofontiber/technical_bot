# s332 · Correcciones y asunciones VISIBLES — v2 VINCULANTE (post-dúo, 21-ago-2026)

> Sustituye a la v1 (que queda como registro pre-dúo). Integra los 13 hallazgos de la ronda
> (Sol xhigh 7 · Fable 6, emparejados, ts=2026-08-21T08:26:35; adjudicación en §9).
> Mandato de Alberto intacto: tabla de confusiones ASR **con aviso al usuario**, aviso
> **generalizable**, y corrección de marca sin estado. Flags default-off = conducta servida
> byte-idéntica.

## 1 · Arquitectura en dos niveles (cambio central vs v1)

**El oráculo-de-plan de la v1 MUERE** (Sol-1 crítico + Fable-4, confirmados: `plan_turn` son
2 pasadas + resolución de hechos con DB en el llamador — ni puro ni barato; y despachar su
resultado reintroduce dos dueños de la decisión, contra s316e/s324h).

En su lugar, dos niveles con papeles distintos y honestos:

- **Nivel 1 — la TABLA (previene y gobierna)**: una confusión OBSERVADA y tabulada se corrige
  en T1, con aviso. La conversación nunca degenera: «¿Qué centrales Kidde tienes?» corregido
  entra por el pipeline NORMAL desde el principio (incluido el atajo de catálogo → el listado
  gobernado completo de `6ee97e80`). **El camino rápido es la tabla, no una re-entrada.**
- **Nivel 2 — la RED (recupera y observa)**: la rama F1 de corrección cubre las confusiones
  AÚN NO tabuladas («me refería a Kidde» tras un turno sin ancla). Recupera vía RAG con
  contexto (sin atajo — asumido y declarado: la red no re-invoca al planificador), deja la
  asunción VISIBLE, y produce la observación que alimenta la tabla. La siguiente vez, esa
  confusión ya es de nivel 1.

## 2 · Primitiva `Asuncion` (el requisito generalizable de Alberto)

```python
@dataclass(frozen=True, kw_only=True)
class Asuncion:
    kind: str        # 'marca_asr' | 'marca_corregida'  (enum cerrado, _guard_estricto)
    detectado: str   # lo que llegó (ASR crudo / token del usuario) — JAMÁS al trace
    asumido: str     # término gobernado asumido (token de catálogo)
    modo: str        # 'reescrito' | 'aviso'  (enum cerrado)
```

Vive en `src/orchestrator/contracts.py`. Render DETERMINISTA en la capa bot (cero LLM; la
conducta no se delega al prompt) con **contrato de propagación EXPLÍCITO por kind** (Sol-2:
la v1 sobre-afirmaba «todas las rutas»):

| kind | dónde nace | dónde se renderiza | cobertura |
|---|---|---|---|
| `marca_asr` | `normalize_voice_query` (tabla) | **Confirmación de voz** (`🎤 …` de `telegram_bot.py:1371-1378`), ANTES de la respuesta: `🏷 Entiendo que preguntas por *Kidde* (el audio se transcribió como «BQide»). Si no es eso, dímelo.` / modo aviso: `ℹ️ Nota: hay una confusión de voz observada «ID»↔Kidde. Si dictaste Kidde, dímelo.` | TODAS las rutas del turno de voz (el render es pre-ruta) |
| `marca_corregida` | rama F1 (red) | Sufijo `ℹ️ Respondo a tu pregunta anterior («{last_query}») entendiendo que la marca es *{Marca}*.` en el ensamblado de la respuesta RAG | Solo ruta RAG — la rama SIEMPRE resuelve STANDALONE→RAG, así que la cobertura es total para su kind |

El sufijo muestra QUÉ pregunta se reconstruyó: si el rebuild fuera sobre una `last_query`
equivocada (p.ej. rancia tras un turno de atajo — ver R8), el usuario lo VE y corrige. La
visibilidad ES el control.

Observabilidad: sección `asunciones` en `rag_trace` (patrón tri-estado `turn_identity`:
`not_wired`/`off`/`on`) con kinds+modos+counters+`asumido` (token gobernado). `detectado`
NUNCA (allowlist s331). **Cambio de esquema versionado y declarado** (Sol-6): el pin
`_CLAVES_HISTORICAS` se actualiza con comentario razonado (precedente `intent`/`turn_identity`);
el criterio byte-idéntico de GC0 es sobre la CONDUCTA SERVIDA (mensajes), no sobre el trace.

## 3 · Nivel 1: tabla con modo + caso por fila

Fila = `(patron, correcto, modo, case_sensitive, cita)`. La compilación respeta
`case_sensitive` **por fila** (Fable-2: el global `re.IGNORECASE` de hoy cazaría el «id»
español — imperativo de «ir», abreviaturas — en la fila nueva).

| fila | modo | case | evidencia (grado declarado) |
|---|---|---|---|
| `death knob → Detnov` | reescrito | insensible (hoy) | Observación piloto 17-ago (desplegada s324f) — sin cambios |
| **`bqide → Kidde`** | **reescrito** | insensible | `02055e5d` (transcript) — sin lectura legítima posible |
| **`ID → Kidde`** | **aviso** (texto INTACTO) | **SENSIBLE, solo «ID» aislado** (`\bID\b` sin IGNORECASE; `\b` no corta ID3000 — test explícito) + **solo `source=voice`** | `2b3febb6`+`838e71a6` (transcripts, MISMA conversación — cuenta como UNA confusión, Fable-5) + **testimonio directo de Alberto** («no está captando "kidde"» mientras el transcript escribía ID). Grado: transcript+testimonio, NO transcript puro (Sol-4). Se re-adjudica con tráfico (R4). |

Corrección del framing v1 (Sol-4): **DEC-233 no fijó umbral alguno** — la tabla se desplegó
con 1 fila. s332 AÑADE filas observadas y les pone VOZ (el aviso), que es lo que Alberto pidió.
Masa real: **3 confusiones distintas** en 4 días de piloto (Detnov→Death Knob ·
Kidde→BQide · Kidde→ID).

`corregir_transcripcion` conserva firma (compat);
`corregir_transcripcion_con_asunciones(texto, *, es_voz) -> (texto, tuple[Asuncion,...])` es
la vía nueva. **El docstring contradictorio del módulo se corrige EN este lote** (Fable-1,
confirmado): la verdad es «la forma corregida llega a la búsqueda Y a la columna `query`;
el ASR crudo queda VISIBLE en la confirmación 🎤 y en la columna `transcription`» — ambas
mitades explícitas, una sola autoridad.

## 4 · Nivel 2: rama F1 de corrección (la red)

Posición: dentro de `if matched_brands:` (impl:702), ANTES de `same_mfr`/`new_brand_no_state`.
Condiciones (todas): cue del léxico gobernado `config/correction_lexicon_v1.yaml` (ES/EN,
patrón `_confirmation_lists` exacto, fail-open a statu quo) por `_match_phrase` · turno
esencialmente-solo-corrección (≤2 tokens residuales tras cue+marca+funcionales del propio cue) ·
`real == ()` · **sin pending vivo** (la gramática s331 tiene precedencia) ·
`working_state.last_query is not None and within_window(now)` (ventana de `last_turn_at`,
SIN exigir modelos).

Resolución: `STANDALONE`, `rationale="brand_correction_rebuild"`,
`query_for_retrieval = f"{last_query} (el usuario corrige: la marca es {Marca})"`,
`target_models=()`, `asunciones=(Asuncion(marca_corregida, …, 'reescrito'),)`.

**Estado tras el turno** (Sol-3, confirmado): `TurnResolution` gana
`state_query_override: str | None = None`; `advance_working_state` lo usa como `last_query`
cuando está presente (espejado en MT-1b). La rama lo fija al REBUILD (no a «me refería a
Kidde») — el encadenado («no, era Notifier») reconstruye sobre la pregunta real. De paso
documenta el matiz s331 ya existente (tras `pending_confirmed_family`, `last_query`=«sí» —
inocuo allí porque el siguiente SET lo refresca, ahora declarado).

Interfaz congelada `conversation_policy.py`: extensión ADITIVA — `TurnResolution.asunciones:
tuple = ()` y `state_query_override` (mismo trato que `turn_identity` en s331; espejo MT +
fakes actualizados).

Huecos DECLARADOS de la red (ninguno la bloquea; todos al GC2 y a la R-lista):
- **R7 (Fable-6)**: con confusión no tabulada, el rebuild arrastra el token corrupto +
  meta-nota → retrieval con ruido. Aceptado vs plantilla vacía; el sufijo hace visible la
  base del rebuild; la observación alimenta la tabla (nivel 1 la cura para siempre).
- **R8 (Sol-3c)**: los turnos de atajo de catálogo NO refrescan el estado F1 (asimetría
  pre-existente, `_ejecutar_plan` retorna antes del seam) → tras un atajo, la corrección
  reconstruye una `last_query` anterior (visible en el sufijo) o no dispara (statu quo).
  Se declara como deuda aparte (candidata TECH_DEBT), NO se arregla en este lote.
- **R9 (Fable-3)**: si el turno corrupto salió por CLARIFY/DECLINE, no hay `last_query`
  fresco y la red no dispara (statu quo). Caso «previo=DECLINE» añadido al GC2.

## 5 · Flags: DOS, con atribución por mecanismo (Sol-7; ajuste vs v1)

| flag | gatea | riesgo que aísla |
|---|---|---|
| `ASR_AVISOS` | filas NUEVAS de la tabla (bqide, ID-aviso) + líneas 🏷/ℹ️ de confirmación + su parte del trace | El ruido del aviso-ID (R4) se apaga sin perder la red |
| `F1_MARCA_CORRECCION` | rama F1 + sufijo + `state_query_override` + su parte del trace | La conducta conversacional nueva se apaga sin perder la tabla |

Default **off** ambos = conducta servida byte-idéntica (la fila `death knob` existente NO se
toca). Clasificados en el inventario P1. Retirar solo la fila ID si R4 ruidosa = commit de una
línea (declarado). Graduación DEC-210/211 tras asentar. (La v1 proponía 1 flag; Sol-7 mostró
que acopla rollback de riesgos independientes y mata la atribución A/B. Dos es el mínimo con
atribución; la preocupación de Alberto por la inflación se honra graduando.)

## 6 · Alternativas descartadas (v1 §3 sigue vigente) + las nuevas de la ronda

1-6. Las de v1 (reescribir ID; disclosure vía prompt; corrección en plan/pre-plan; cirugía
   de token por heurística; cuatro flags; fuzzy fonético general) — sin cambios.
7. **Oráculo-de-plan / re-entrada al planificador** (v1 §2.C): muerto por Sol-1+Fable-4.
   El atajo se alcanza por la tabla (nivel 1), no re-planificando texto sintético.
8. **Un solo flag** (v1 §2.D): muerto por Sol-7 (acoplamiento de rollback + sin atribución).

## 7 · Riesgos vivos

R1 cue-léxico infra-cubre (fail = statu quo; crece por observación) · R2 falso positivo del
cue con marca igual (rebuild redundante correcto, visible) · R3 estado in-memory (limitación
F1 heredada) · R4 aviso-ID para usuarios legítimos de la familia ID (una línea; re-adjudicar
con tráfico) · R6 ES/EN en cues y plantillas (EN entra en léxico; confusiones observadas
ES-only) · **R7/R8/R9 (§4)**.

## 8 · Mini-gates PRE-REGISTRADOS (deltas vs v1 en negrita)

- **GC0 conducta-byte-idéntica con flags off**: replay de los 5 turnos de §0-v1 + kidde_t3
  (G3 s331): **mensajes servidos idénticos a HEAD; el trace añade la sección versionada
  `asunciones` (declarado, NO cuenta como desviación)** (Sol-6).
- **GC1 replay ON de la mañana**: `02055e5d` reescrito+aviso; `576a7ef9` → **respuesta SOLO
  Kidde (cero contenido cross-brand), no-vacía, con sufijo de asunción** (Sol-5; sin «ideal
  inventario» — el atajo llega vía nivel 1 en T1); `2b3febb6`/`838e71a6` → contenido ID
  INTACTO + aviso; `6ee97e80` intacto.
- **GC2 no-interferencia**: MT 52/52 con ambos flags on; suite completa; casos borde CON
  conducta esperada escrita ANTES: sustancia extra · modelo explícito · sin last_query ·
  fuera de ventana · tras restart · marca igual · «no era Kidde» (negación no-cue) · EN ·
  **previo=DECLINE (R9)** · **previo=atajo (R8)** · **«id» minúscula NO dispara aviso** ·
  **ID3000/ID3002/IDNet no disparan** (Fable-2).
- **GC3 conducta A/B** (patrón G3, N=4 por brazo): mañana-Kidde OFF (plantilla vacía) vs ON
  (contenido Kidde + asunción visible) — leído (DEC-092b).
- Ship: PR → merge → Railway (`ASR_AVISOS=on`, `F1_MARCA_CORRECCION=on`, Alberto) →
  verificación DEC-099 = re-lanzar la conversación de la mañana POR VOZ.

## 9 · Traza y adjudicación de la ronda (ts=2026-08-21T08:26:35, emparejada, agentes frescos)

| # | hallazgo | verificación | adjudicación en v2 |
|---|---|---|---|
| Sol-1 (crítico) | oráculo-de-plan: dos dueños + no-puro (turn_plan:496-550) | CONFIRMADO (leído) | §1: oráculo MUERTO; dos niveles |
| Sol-2 | propagación de Asuncion sin contrato; «todas las rutas» sobre-afirmado | CONFIRMADO (procedencia solo canal+raw) | §2: tabla de propagación por kind |
| Sol-3 | estado post-rebuild guarda la meta-frase; atajo sin transición; falta gate follow-up | CONFIRMADO (bot:2260-2267; impl:992-996) | §4: `state_query_override` + R8 + GC2 |
| Sol-4 | «ID observada» sobre-afirmada; «DEC-233 fijó umbral» falso | CONFIRMADO (DECISIONS 7573-7577) | §3: grado de evidencia + framing corregido |
| Sol-5 | GC1 optimizaba no-vacío, no precisión | CONFIRMADO | §8: criterio solo-Kidde/cero cross-brand |
| Sol-6 | sección de trace nueva rompe «ni UN byte» con flag off | CONFIRMADO (exact_keys) | §2/§8: esquema versionado; GC0 = conducta |
| Sol-7 (menor) | 1 flag acopla rollback y mata atribución | ADJUDICADO a favor | §5: dos flags |
| Fable-1 | docstring de `corregir_transcripcion` contradice el contrato declarado | CONFIRMADO (leído ambos textos) | §3: se corrige en el lote |
| Fable-2 | fila ID con IGNORECASE caza «id» español | CONFIRMADO (whisper_vocabulary:50) | §3: case por fila + tests GC2 |
| Fable-3 | «material YA en estado» condicional: DECLINE no refresca | CONFIRMADO (impl:969-987) | §4 R9 + GC2 |
| Fable-4 | oráculo sin contrato de transición ni pureza verificada | CONFIRMADO (converge Sol-1) | §1: muerto |
| Fable-5 (menor) | «≥4 observaciones» infla (2 transcripts = 1 confusión; «plausiblemente» endurecido) | CONFIRMADO | §3: 3 confusiones distintas, grados |
| Fable-6 (menor) | fallback de red con token corrupto = retrieval ruidoso, sin declarar | CONFIRMADO por construcción | §4 R7 |

**13/13 con sustancia, 0 falsos positivos.** Veredicto Fable «NO SÓLIDO tal cual» atendido:
los 3 bloqueantes (docstring, homógrafo «id», especificación del oráculo) quedan resueltos
(§3, §3, §1-muerto). La v2 es la spec VINCULANTE del build.

## 10 · Checklist de build (B1-B8)

- B1 `Asuncion` en contracts + enums cerrados + tests.
- B2 tabla con modo/case/cita + `corregir_transcripcion_con_asunciones` + docstring
  harmonizado + tests (ID3000/id-minúscula/BQide/death-knob-intacta).
- B3 `VoiceQueryNormalization.asunciones` + render 🏷/ℹ️ en confirmación de voz (flag
  `ASR_AVISOS`) + tests.
- B4 léxico de corrección + rama F1 + `state_query_override` + extensión `TurnResolution` +
  espejo MT + fakes + tests (12 casos GC2).
- B5 sufijo `marca_corregida` en ensamblado RAG (flag `F1_MARCA_CORRECCION`) + tests.
- B6 sección `asunciones` del trace (tri-estado) + pin actualizado con comentario + tests.
- B7 flags en `flags.py` + inventario P1 (los DOS clasificados) + censo.
- B8 runners GC0-GC3 + recibos + suite completa con exit real.
