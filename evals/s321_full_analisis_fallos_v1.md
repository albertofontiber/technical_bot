# s321 — Dónde fallan los 19 hechos del FULL (16-ago) y cuáles son atacables

Fuente: `evals/s100_factlevel_full_v3_20260816.yaml` (PR #273) · recibos de sonda en `evals/s293_reachability_*.json`.

## 1 · No se concentran por PREGUNTA — se concentran por MECANISMO

16 golds distintos tienen algún fallo; **14 de ellos tienen exactamente uno**. No hay preguntas rotas.

| mecanismo | n | qué significa |
|---|---|---|
| `synthesis-miss · omitted` | **10** | el carrier **se sirve y llega al generador**, y el LLM no lo dice |
| `synthesis-miss · contradicted` | 1 | `cat020#1` — el bot afirma algo que lo contradice |
| `synthesis-miss · hedged` | 1 | `hp017#2` — lo matiza sin afirmarlo |
| `rerank-miss` | 2 | `cat010#0` lexical-distractor · `hp002#5` pos-buried |
| `retrieval-miss` | 3 | `cat011#1` model-filter · `hp001#2` y `hp013#1` within-doc (`raw=0`: ni llegan al pool) |
| `corpus-gap` | 2 | `cat013×2` — **verificados a mano 10 veces**: clase FN family-scoped (DEC-074), NO son gaps |

⇒ **12 de 19 son de síntesis, y 10 de esos son «servido y OMITIDO»**. Es UN mecanismo repartido en 10 preguntas, no 10 problemas.

## 2 · Tabla completa

| gold | hecho | clase | submotivo | raw | srv | pool | →gen | sonda |
|---|---|---|---|---|---|---|---|---|
| `cat013` | `cat013#0:bucle cerrado` | corpus-gap | None | 0 | 0 | False | False | — |
| `cat013` | `cat013#1:CLIP` | corpus-gap | None | 0 | 0 | False | False | — |
| `cat010` | `cat010#0:24V dc` | rerank-miss | lexical-distractor | 2 | 0 | True | False | — |
| `hp002` | `hp002#5:Securiton AG` | rerank-miss | pos-buried | 1 | 0 | True | False | — |
| `cat011` | `cat011#1:seguridad intrínseca` | retrieval-miss | model-filter | 1 | 0 | False | False | — |
| `hp001` | `hp001#2:1111` | retrieval-miss | within-doc | 0 | 0 | False | False | — |
| `hp013` | `hp013#1:PWR-R` | retrieval-miss | within-doc | 0 | 0 | False | False | serve · 0/5→0/5 ×3 · **NO alcanzable** (s321) |
| `cat001` | `cat001#3:32 / 25 / 20` | synthesis-miss | omitted | 2 | 1 | True | True | — |
| `cat008` | `cat008#3:1/2/3/4 lazo; 6-7 entrada` | synthesis-miss | omitted | 1 | 1 | True | True | — |
| `cat016` | `cat016#1:menu ZONA + ELEMENTO` | synthesis-miss | omitted | 1 | 1 | True | True | — |
| `cat020` | `cat020#1:0-100 % normalizado` | synthesis-miss | contradicted | 1 | 1 | True | True | — |
| `hp003` | `hp003#4:magnetotermico` | synthesis-miss | omitted | 1 | 1 | True | True | appendix · 0→5/5 (2 de 3; 1 base ya 5/5) · **ALCANZABLE** |
| `hp005` | `hp005#3:CIRCUITO SIRENA` | synthesis-miss | omitted | 5 | 1 | True | True | — |
| `hp009` | `hp009#0:Retorno` | synthesis-miss | omitted | 1 | 1 | True | True | — |
| `hp011` | `hp011#2:05 a 295 seg` | synthesis-miss | omitted | 1 | 1 | True | True | serve · 0/5→0/5 ×3 · **NO alcanzable** |
| `hp015` | `hp015#0:convencional` | synthesis-miss | omitted | 3 | 1 | True | True | — |
| `hp015` | `hp015#2:32` | synthesis-miss | omitted | 3 | 2 | True | True | — |
| `hp017` | `hp017#1:instruccion de entrada` | synthesis-miss | omitted | 0 | 1 | False | True | — |
| `hp017` | `hp017#2:Editar Configuracion` | synthesis-miss | hedged | 0 | 1 | False | True | serve · 0/5→5/5 ×3 · **ALCANZABLE** |

## 3 · ¿Son atacables? Solo se sabe de 4 de los 12 de síntesis

El proyecto **ya tiene la puerta**: ningún lever de serving/síntesis se diseña sin la sonda de alcanzabilidad antes (Protocolo 4 · DEC-173). Estado:

| hecho | sonda | veredicto |
|---|---|---|
| `hp017#2` | serve (carrier p43 `94cbb0ce`) | **ATACABLE** — 0/5 → 5/5 en 3/3 |
| `hp003#4` | appendix (span «Desconecte siempre…») | **ATACABLE** — 0→5/5 en 2 de 3 (caveat: 1 base ya daba 5/5) |
| `hp011#2` | serve (ambas mitades admitidas) | **NO** — 0/5 → 0/5 ×3 |
| `hp013#1` | serve (2 carriers, entrega probada) | **NO** — 0/5 → 0/5 ×3 (s321; además hoy es retrieval-miss) |
| `cat017#2` | serve | ATACABLE — pero **ya flipeó a OK** sin lever |

**Los otros 8 `omitted` NUNCA se han sondado**: `cat001#3`, `cat008#3`, `cat016#1`, `hp005#3`, `hp009#0`, `hp015#0`, `hp015#2`, `hp017#1`. A **~$1 y minutos cada uno**.

## 4 · Recomendación

**Sondar esos 8 antes de diseñar nada** (~$8, una hora). No es rigor por rigor: es exactamente la pregunta abierta de **DEC-175** — si la población de hechos que un lever de serving podría pagar es 1 (murió el lever B) o es varias. Hoy la cota inferior es **≥2** (`hp001#2`, `hp012#3`, más `hp017#2` probado); si de los 8 salen 3-4 alcanzables, la población deja de ser el bloqueador y el lever vuelve a ser diseñable. Si salen 0-1, la etapa 3 se cierra **con evidencia** en vez de por cansancio.

**Lo que NO hay que hacer**: diseñar un lever contra «los 12 synthesis-miss» como si fueran una población. Cuatro de ellos ya tienen veredicto y dos son NO.

## 5 · Dos cosas que este análisis descarta

- **#84 no explica ningún miss** (ver la corrección en `TECH_DEBT #84`): los golds con más material excluido están todos OK, y `cat011#1` (`model-filter`) es el control C1 del censo, no #84.

- **Los 2 `corpus-gap` no son gaps**: `cat013` es la clase FN family-scoped verificada 10 veces (DEC-074). No hay manual que comprar.

