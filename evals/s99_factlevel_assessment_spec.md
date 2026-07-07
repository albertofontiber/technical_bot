# Assessment a nivel-hecho — SPEC ESTANDARIZADO v3 (dúo ×3 · para BUILD)

**Objetivo (Alberto):** lo hemos hecho ad-hoc 4× (s85/s87/s88/s99) y bit-rotea. Estandarizar en UN
procedimiento canónico reusable. **v3 (s100):** re-confirmación dúo corta sobre v2 (cross-model GPT-5.5 +
sub-agente Opus, ambos leen el repo) → **8 hallazgos confirmados regla-C, 0 FP**; 2 eran BLOQUEA-MEDICIÓN
(medirían un pipeline fantasma). v3 los incorpora. La idea se sostiene (absorción real, no-fusionar
RETRIEVAL/CORPUS-GAP, regenerar-siempre) — el diseño no cambia, se blinda la MEDICIÓN. Antes de escribir
`docs/FACTLEVEL_ASSESSMENT.md` canónico: build sobre v3.

## Δ v2→v3 (lo que cambió, con ancla)
| # | Sev (dúo) | Fix aplicado | Ancla verificada (regla-C) |
|---|---|---|---|
| A | **BLOQUEA-medición** | Freeze-contract lee `RERANK_TOP_K`/`LLM_MAX_TOKENS` del **ENTORNO** y estampa el valor REAL de la demo (10/3500), + check `manifest == demo`. Los instrumentos que hardcodean `RERANK_K=5` se unifican a env. | `config.py:47` (getenv, default 5); demo=10 (DEC-092); hardcode `audit_retrieval_funnel.py:75`, `retrieval_miss_judge.py:54` |
| B | **BLOQUEA-medición** | QUITADO `DIVERSIFY_TIEBREAK` del freeze-contract — flag MUERTO (0 en `src/`, DEC-091 NO-GO, contaminación de la rama `lever/s97`). | grep `src/` = 0; DEC-091/091b |
| C | crítico | Inventario COMPLETADO: absorber también `retrieval_miss_famtie.py`, `retrieval_miss_diagnose.py`, `synthesis_stability.py`. | los 3 existen en `scripts/` |
| D | medio | Eje gold/juez reconstruye el **blocker-primario por-gold** + **IDENTIDAD** como sub-bucket (lo que `s87_rootcause` aportaba, no solo "NO-PASS ⊥ pipeline"). | `s87_rootcause.py:22-71` une 4 YAMLs + max-blocker |
| E | medio | Clase `unmeasurable` (no-terminal → revisión manual): los hechos `measurable()==False` NO se dejan fuera del histograma (inflarían la precisión de las 5 clases). | `audit_retrieval_funnel.py:360` (`bucket=None`) |
| F | medio | Join hecho↔texto por **clave estable** (qid+valor), NO por posición (`zip`). Regenerar-siempre no lo arregla; el `assert len` no lo caza. | `synthesis_miss_judge.py:114,116` |
| G | medio | Freeze añade `MERGE_STRATEGY` + `GENERATOR_INCLUDE_CONTEXT`; `similarity` en el pin se declara **no-fiel** (stamp plano léxico ≠ coseno) salvo que se distinga stamp-vs-coseno. | `config.py:71-80`; `retriever.py:554` (stamp 0.80/0.70) |
| H | medio | `threshold-miss` NO es clase terminal propia → sub-motivo `threshold-drop` bajo **synthesis-miss** (raro: solo path vector-puro <0.4; fundirlo en rerank-miss es error de causa-raíz). | `generator.py:343,402`; stamps planos `retriever.py:442-605` |

**Decisión de Alberto (s100):** el juez de sub-motivo **VE los chunks servidos** (distingue `hedged` de
`partial` = qué lever accionar) → coste re-estimado (ver §Coste). **CORPUS_GAP:** default = **FN-MÍO**
(`feedback_corpus_gap`, cazado 3×), verificación anti-FN reforzada antes de aterrizar. **IDENTIDAD=ADD:**
el pipeline shippeado corre policy ADD (band-aid, DEC-091b) → el sub-motivo `model-filter` marca los
aciertos-hp018 como coincidencia-de-valor, no "identidad resuelta".

## Inventario COMPLETO de instrumentos a unificar/retirar (v3: +3 del dúo)
| Instrumento | Qué hace | Destino |
|---|---|---|
| `retrieval_miss_judge.py` | pool-50 vs hecho (juez GPT-5.5 K=5) | **absorber** (plomería + juez de soporte) |
| `synthesis_miss_judge.py` | ¿respuesta transmite el hecho servido? | **absorber** (juez de conveyed) |
| `audit_retrieval_funnel.py` | `classify()` 4 buckets posición-based (SINTESIS/RERANK-MISS/RETRIEVAL/CORPUS-GAP) + `measurable()` gate | **absorber** (clasificación + gate de medibilidad) |
| `retrieval_miss_famtie.py` | clase por FAMTIE (lee `pool_pin`, no re-recupera) | **absorber** (la clase-por-famtie que v3 exige; ojo: re-generar pin con flags ON) |
| `retrieval_miss_diagnose.py` | sub-motivos / etapa real del miss | **absorber** (insumo de sub-motivo retrieval) |
| `synthesis_stability.py` | varianza de generación (mismo input, K corridas) | **absorber** (separa synth-miss real de ruido de generación) |
| `s87_rootcause.py` | join de 4 YAMLs → blocker-primario por-gold + IDENTIDAD | **retirar**, pero el eje gold/juez RECONSTRUYE su join (fix D) |

## Taxonomía v3 — 5 clases terminales + `unmeasurable` + sub-motivo
Fix dúo: NO fusionar `RETRIEVAL` y `CORPUS-GAP` (distinción semántica real; `feedback_corpus_gap` = FN 3× si
se degrada). "Servido" = **post-`RELEVANCE_THRESHOLD`** (`fresh_ctx_ids` = lo que el generador VE,
`synthesis_miss_judge.py:135`, no el top-k crudo). **Ordenar el funnel por FAMTIE, no target-laxo** (DEC-075:
by_target contamina hp018 por identidad).

| Clase terminal (orden de funnel) | Definición precisa | Sub-motivo (juez corto CON contexto servido) |
|---|---|---|
| **corpus-gap** | el hecho NO existe servible en el corpus (ni en manual) | **default = FN-MÍO**; anti-FN reforzado (es-en / OCR / bare-value / tie) ANTES de aterrizar — `feedback_corpus_gap` |
| **retrieval-miss** | servible en corpus pero NO en el pool-50 | `within-doc`(aguja/coseno sub-suelo) / `es-en` / `model-filter`(marcar ADD-coincidencia, no "resuelto") |
| **rerank-miss** | en pool-50 pero NO sobrevive al top-k rerankeado (**k del entorno = demo, no default local**) | `lexical-distractor` / `diversity-lottery` / `pos-buried` |
| **synthesis-miss** | en el contexto servido (post-threshold), la respuesta NO lo transmite | `omitted` / `hedged`(vio-todo→lever prompt) / `partial`(chunk-incompleto→lever retrieval) / `contradicted` / `threshold-drop`(cayó por umbral, raro) — DEC-075 |
| **OK** | servido + transmitido | — |
| **unmeasurable** (NO terminal) | valor no verificable léxicamente (`measurable()==False`) | → revisión manual; NO entra al histograma de precisión de las 5 clases |

**`judge-FN` NO es sub-motivo de síntesis** (DEC-075): "el bot SÍ transmite, el juez falla" = CALIDAD-DEL-JUEZ
→ eje gold/juez, no contamina el funnel. **Borderline (2-3/5 votos):** default `partial` salvo evidencia de
error del juez → eje gold/juez. Resolver con muestreo, no asumir `judge-FN`.

## Eje SEPARADO gold/juez (per-gold, holístico) — v3: reconstruye el join de `s87_rootcause`
El funnel mide fallos de PIPELINE. Los NO-PASS ⊥ pipeline (bot acierta, gold/juez penaliza — DEC-075) van
aquí. **v3 (fix D):** NO basta absorber "los ~10/30"; reconstruye explícitamente **(1) blocker-primario
por-gold** (max de {SÍNTESIS, RETRIEVAL, IDENTIDAD, RERANK}) y **(2) IDENTIDAD como sub-bucket separado**
(ya está en la taxonomía como `model-filter`). **NO pre-cargar el conteo "~9-10/30 plateau" de DEC-075** — está
CADUCO (DEC-093, medido pre-ancho/A3/identidad); el estándar lo **re-deriva**. Etapa SEPARADA y opcional,
desacoplada del funnel barato; nunca se fusiona con el PASS caro. Necesita veredictos PASS o gold-review
(gate Alberto).

## Anti-bit-rot v3
- **DEFAULT = regenerar SIEMPRE** el `fact→chunk-support` contra golds+pipeline actuales. El cache
  "hash core_facts → re-juzgar solo cambiados" se DESCARTA (el soporte depende de corpus/índice/config/juez,
  no solo del texto → reusar = labels stale/circularidad). Si algún día se cachea: hash del **contenido
  serializado** (valor+texto+estado) Y match EXACTO del freeze-contract — nunca `len()`.
- **(fix F) Join hecho↔texto por CLAVE ESTABLE** (qid+valor o id-de-hecho), NO por posición. El `zip(cf,
  r["facts"])` (`synthesis_miss_judge.py:116`) es frágil: si `core_facts()` cambia orden/filtro entre la
  semilla y hoy, el hecho se pega al texto EQUIVOCADO y el `assert len` (`:114`) NO lo caza (solo longitud).
  Regenerar-siempre no arregla esto — el join posicional queda latente si el gold se re-ordena.

## Freeze-contract v3 (fix A/B/G — regenerado del pipeline SHIPPEADO, no de memoria)
**Regla:** el manifest se llena leyendo el **estado real del pipeline en runtime**, no una lista escrita a
mano (así no se cuela un flag muerto ni se omite uno vivo — la clase entera del bug). Estampar:
- git-commit + corpus-fingerprint (count+max_created_at) + **pool pineado con `content`/`has_diagram`**
  (patrón s98). **`similarity`: declararlo NO-FIEL** (stamp plano léxico 0.80/0.70, `retriever.py:554` ≠ coseno)
  salvo que se distinga stamp-vs-coseno; hoy el DEF ni lo guarda.
- **Flags load-bearing del pipeline shippeado** (leídos del entorno, valor de demo): `CHUNKS_TABLE`,
  `HYDE_ENABLED`, **`RERANK_TOP_K`(=10 demo)**, `RETRIEVAL_TOP_K`, `RELEVANCE_THRESHOLD`, **`LLM_MAX_TOKENS`(=3500 demo)**,
  `RERANKER_BACKEND`, `RERANK_PREVIEW_CHARS`, **`MERGE_STRATEGY`**, **`GENERATOR_INCLUDE_CONTEXT`**,
  `IDENTITY_RESOLVE(+POLICY=ADD)`, `ENUNCIADOS_MULTIVECTOR`(=on demo, A3 DEC-090), `VECTOR_NOCAT`(permanente) +
  judge-sys/user-sha + seeds. **QUITADO `DIVERSIFY_TIEBREAK`** (muerto).
- **Check `manifest.rerank_top_k == valor de demo`** (anti bug-s45: medir top-5 local cuando la demo sirve 10).
- **Clase terminal por FAMTIE**, no target-laxo.
- **Flag-set autoritativo de la demo (CONFIRMADO s100 con Alberto vía Railway Variables):** Railway define
  6 overrides — `CHUNKS_TABLE`(=chunks_v2), `ENUNCIADOS_MULTIVECTOR`(=on), `IDENTITY_RESOLVE`(=on),
  `IDENTITY_RESOLVE_POLICY`(=ADD), `LLM_MAX_TOKENS`(=3500), `RERANK_TOP_K`(=10); TODO lo demás usa el default
  de código (`RERANKER_BACKEND=llm`, `MERGE_STRATEGY=stamps`, `RERANK_PREVIEW_CHARS=800`, `HYDE_ENABLED=false`,
  `GENERATOR_INCLUDE_CONTEXT` sin-set — verificado ausentes de Railway). Los *valores* de los 6 están
  enmascarados en el dashboard → tomados de los DECs "verificado en producción" (aserción DEC-sourced, no
  eyeballed). El build los EXPORTA explícitamente al correr y los estampa en el manifest.

## Sub-motivo — juez nuevo CON contexto servido (decisión Alberto s100)
Los jueces actuales solo emiten `supported_ids`/booleano; el sub-motivo es una **rúbrica/juez NUEVO**.
**Recibe el contenido de `fresh_ctx_ids` (chunks servidos, top-10) + el gold** — sin eso NO distingue `hedged`
(el generador vio todo → lever de PROMPT) de `partial`-por-chunk-incompleto (lever de RETRIEVAL/chunking);
son causas-raíz distintas para accionar. **Coste declarado (fix b): inyectar top-10 servido sube el juez** —
ver §Coste. (Nota: el juez ACTUAL `synthesis_miss_judge.py:62-73` NO inyecta chunks, solo `answer`; v3 SÍ los
inyecta a propósito.)

## Coste v3 (fix b — re-estimado con inyección de contexto, disciplina `feedback_cost_discipline`)
- Soporte + conveyed = como hoy (~$10-15 el funnel, 39 golds, K=5).
- **Sub-motivo con chunks servidos**: juez K=5 SOLO sobre los MISS (universo acotado ~40-50), pero cada
  llamada carga top-10 servido (~7400 chars/chunk, `retrieval_miss_judge.py:55` CONTENT_CHARS=8000) ≈ 15-20k
  tokens/llamada × K=5 → orden **+$5-8** (NO +$2-4; la cifra v2 asumía juez chunk-free).
- `smoke`/`subset` SIEMPRE antes del full + `.partial.jsonl` resumible + estimación impresa. **Total estándar
  ≈ $18-25.** Confirmar en smoke antes del full (no declarar la cifra como cerrada pre-smoke).

## Canónico
Un entry-point `scripts/factlevel_assessment.py {smoke|full}` + `docs/FACTLEVEL_ASSESSMENT.md` + fila
Protocolo 4 (*gatillo: re-medir dónde caen los hechos tras cambio de pipeline/golds → acción: correr el
estándar*).

## Estado v3
Dúo ×3 cerrado (s100): 8 confirmados / 0 FP; los 2 BLOQUEA-medición (A, B) + los 6 medium incorporados.
**Sin gate abierto de diseño** — el fork del sub-motivo (ver-chunks) lo cerró Alberto. Dependencia de build:
flag-set autoritativo de Railway (§Freeze-contract). Listo para BUILD.
