# s324d — Endurecimiento de la sonda de alcanzabilidad (TECH_DEBT #89): qué cambia, qué NO, y qué midió el smoke

**Estado: cableado en la rama `claude/s324d-autonoma`, NO mergeado; suite verde en los ficheros tocados; smoke real
2 reps ($0,60). Es INSTRUMENTO (scripts/), no serving: producción no cambia.** Ficheros:
`scripts/s293_reachability_probe.py` (probe), `scripts/reachability_verdict.py` (lógica pura nueva: `elegir_span`,
`span_cubre`, `carriers_ya_servidos`, `elegir_receipt`), `scripts/usage_meter.py` (nuevo, observación pura),
`tests/test_s324d_reachability_hardening.py` (15 tests tras el dúo) + los 10 previos de `test_s321_reachability_delivery_proof.py`.

## Los 5 defectos (agente de medición, 16-ago; `evals/s321_poblacion_etapa3_v1.md` §5) y el cambio

| # | Defecto | Cambio | Dónde |
|---|---|---|---|
| 1 | `RECEIPT` pineado al FULL del 1-ago (`s100_factlevel_full_v32_full_20260801.yaml`): pregunta/valor/texto/pool_ids salían de ahí aunque hubiera FULL nuevo | `--receipt <path>` explícito; por defecto el FULL v3* **más reciente por fecha del nombre** (`elegir_receipt`; excluye `INVALIDO`); el recibo estampa `receipt_usado` y el stdout lo imprime | probe `receipt_por_defecto`, verdict `elegir_receipt` |
| 2 | `appendix` tomaba la PRIMERA línea que casaba el regex (split en `.;:`, len>25) sin guard de cobertura: eligió spans que no cubrían el hecho (cat016#1, hp015#0), partía «etiqueta: definición» y descartaba etiquetas ≤25 chars (hp017#1 → «no construible» con el carrier servido) | `elegir_span`: parte SOLO por frase/línea (`.` `;` `\n`, no `:`); cada candidato se comprueba con `span_cubre` (tokens duros del `valor`: números/códigos/palabras≥3, normalizados sin acentos/caja); si no cubre se EXTIENDE hasta 2 líneas siguientes (cap 600 chars); si nada cubre → la rep queda **NO construible** (fila con `span=None`, `no_construible=motivo`, `eleccion_span` con el mejor candidato y sus tokens ausentes) y el veredicto es INCONCLUYENTE_SIN_PRUEBA_DE_ENTREGA (por la regla existente: span vacío = sin entrega). No se juzga NUNCA un apéndice que no cubre el valor | verdict `elegir_span`/`span_cubre`; probe rama appendix |
| 3 | Un `SystemExit` en una rep tardía tiraba las reps ya juzgadas sin recibo (hp009#0: ~20 llamadas al juez perdidas) | El loop de reps va en `try/except BaseException`: se escribe el recibo con `estado: PARCIAL` + `error` y las reps juzgadas, y se re-lanza. «Span no encontrado» ya no es `SystemExit`: es una rep no construible (el retrieval no es determinista; la siguiente rep puede construirse) | probe `recibo()`/`escribir()` |
| 4 | Ni imprimía ni guardaba coste | `scripts/usage_meter.py` (envuelve `Messages.create`/`Completions.create` solo para LEER `usage`; fases `turn_base`/`turn_oracle`/`judge`); el recibo lleva `coste` (usd por modelo con FUENTE del precio; modelo sin precio → `usd=None`, nunca inventado); stdout imprime `coste: $x (n llamadas)` | `usage_meter.py`; probe |
| 5 | `serve` sobre un chunk YA servido lo DUPLICABA con similarity máxima: el ALCANZABLE medía PROMINENCIA, no evidencia ausente; el recibo no guardaba la composición de la base | Si el carrier ya está en la vista, NO se duplica: se eleva su `similarity` in-place y se DECLARA (`carriers_ya_servidos_en_base`, `carriers_ya_servidos_en_oracle_sin_inyeccion`, `aviso_prominencia` en el veredicto y en stdout); el recibo guarda `base_served_ids` y `oracle_served_ids` | probe `run_turn`/rep |

## Qué NO cambia (a propósito)
- La vara: `judge_conveyed21` GPT-5.5 K=5, `THRESH_FIRM=4`, prompt/caps intactos.
- La lógica de veredicto (`veredicto_de`, `prueba_de_entrega`): fail-closed del negativo (s321) intacto; el nuevo
  caso «no construible» entra por la puerta que ya existía (span vacío ⇒ sin prueba de entrega ⇒ INCONCLUYENTE).
- El formato del nombre del recibo (`evals/s293_reachability_<qid>_<fact>.json`) — sigue SOBRESCRIBIENDO: quien
  re-mide un hecho pisa el recibo anterior (git conserva el histórico). Declarado, no arreglado aquí (ver riesgos).
- Los recibos ya escritos (8 sondas de etapa 3) NO se re-miden: DEC-175 sigue como está.

## Smoke real (2 reps, $0,60), sobre `hp017#1` (PEARL, «Instrucción de entrada»)
- **appendix** `--span-grep "Instrucci[oó]n de entrada"` 1 rep: recibo FULL 16-ago; span = «* Instrucción de entrada:
  esta parte de la regla…» (F12, sin extender, cobertura OK) → base 0/5 → **oracle 5/5, ALCANZABLE**, coste $0,29.
  Antes (defecto 2) este mismo caso salía «no construible» con el carrier servido.
  → `evals/s324d_reachability_smoke_hp017_1_appendix.json`.
- **serve** `--inject d27b1a1b-69cd-…` 1 rep: el prefijo `d27b1a1b` ya NO resuelve contra el pool del FULL 16-ago (el
  pool cambió; hubo que pasar el uuid completo — la cara B del defecto 1); el carrier estaba YA en la vista base →
  no se duplicó (12 filas en base y en oráculo), `aviso_prominencia` emitido; base 0/5 → oracle **0/5** (1 rep) →
  INCONCLUYENTE_SIN_COBERTURA_ATESTADA (correcto: no se atestó cobertura). Coste $0,31.
  → `evals/s324d_reachability_smoke_hp017_1_serve.json`.
  **Lectura honesta**: el ALCANZABLE de s324b para `hp017#1` en modo `serve` venía CON el carrier duplicado a
  similarity máxima (defecto 5). Sin duplicar, 1 rep da 0/5. Es coherente con la prueba offline D1 (el bullet
  está FUERA de todas las cards de cobertura: subir la similarity no mete el texto en la vista) — pero 1 rep no
  es una medida; no se cambia ningún veredicto con esto. Queda declarado en TECH_DEBT #89 y aquí.

## Riesgos y gaps declarados
1. `span_cubre` exige TODOS los tokens duros del valor: valores largos/parafraseados («menú ZONA + ELEMENTO» ok;
   pero un valor con sinónimos del manual fallará) → falsos «no construible» (INCONCLUYENTE, nunca NO): más
   seguro que antes, pero puede exigir un `--span-grep` más preciso o un valor con la grafía del manual.
2. La extensión a 2 líneas es heurística; hechos que viven a >2 líneas del ancla siguen sin cubrir (declarado en
   el recibo con los tokens ausentes).
3. `elegir_receipt` ordena por la fecha del NOMBRE (`20\d{6}`); un FULL sin fecha en el nombre queda último.
4. El recibo se sigue sobrescribiendo por (qid, fact): re-medir pisa el anterior (git lo conserva). Un sufijo por
   sello/fecha sería lo limpio; no se hizo para no romper los consumidores del nombre.
5. `usage_meter` mide solo Anthropic Messages + OpenAI chat.completions: embeddings/rerank REST no (centavos).

## Qué pido al revisor
Atacar: (a) que el guard de cobertura no pueda producir un NEGATIVO falso ni ocultar un ALCANZABLE legítimo;
(b) que la deduplicación in-place en `serve` no cambie la semántica del oráculo más de lo declarado (¿debería
seguir duplicando para medir «prominencia» a propósito? — declaro que NO: medir prominencia por duplicado era el
defecto); (c) que el recibo parcial no pueda pasar por completo; (d) el default del receipt (¿fecha del nombre es
un criterio robusto?); (e) cualquier claim de este doc que el código no sostenga.

---

## ADENDA — dúo r34 (17-ago): Sol GPT-5.6 xhigh 7 hallazgos + Fable 5 emparejado (11 `tool_use` reales) 1 hallazgo — TODOS verificados y APLICADOS antes de mergear
| # | Hallazgo (Sol) | Verificación | Cambio |
|---|---|---|---|
| 1 | crítico — `judge_conveyed21` devuelve `n_fail` y la sonda lo descartaba: 5 votos caídos = `oracle_yes=0` ⇒ podía emitir `NO_ALCANZABLE` | cierto (código pre-existente) | cada rep guarda `base_n_fail`/`oracle_n_fail`; una rep NO firme con votos caídos no sostiene un negativo → `INCONCLUYENTE_JUEZ_INCOMPLETO`. **El propio smoke lo validó**: mi primer oráculo pareado pasaba el dict del generador al juez (5 fallos) y el veredicto salió `JUEZ_INCOMPLETO`, no un NO falso; el bug (`generation["answer"]`) se arregló |
| 2 | crítico — un recibo PARCIAL conservaba `ALCANZABLE`/`NO_ALCANZABLE` literal (Fable: el mismo, medio) | cierto | `veredicto_recibo()` (puro, testeado): en PARCIAL el veredicto es `PARCIAL_<…>` y un negativo NO es emitible (`PARCIAL_INCONCLUYENTE_SIN_REPS_COMPLETAS`); `veredicto_reps_juzgadas` conserva el literal informativo |
| 3 | crítico — `span_cubre` acreditaba subcadenas (`32` dentro de `132`) y solo el valor, no el predicado | cierto | frontera de palabra + `texto` (enunciado del hecho): ≥2 tokens de contenido del predicado deben estar en el span (o todos si hay menos); detalle en `span_cobertura` del recibo |
| 4 | medio — base y oráculo eran turnos independientes: «prominencia» mezclada con churn de retrieval/rerank | cierto (el smoke lo mostraba) | oráculo **PAREADO por defecto** en `serve` (misma vista que recibió el generador en la base + inyección, `gen_answer_only` de s289); `--oracle-fresco` restaura el comportamiento anterior; el recibo estampa `oracle_pareado` |
| 5 | medio — `usage_meter.install()` silenciaba fallos y podía reportar $0 como coste | cierto | `proveedores_instalados`/`errores_instalacion`/`disponible()`; el recibo lleva `medicion_disponible` y `n_llamadas_medidas`; stdout dice «coste NO MEDIDO» cuando no hay medida |
| 6 | medio — «freeze-contract completo» en la etiqueta del recibo contradecía el sello PARCIAL | cierto | etiqueta «sello de freeze PARCIAL» |
| 7 | menor — recuento de tests (11+12) no cuadraba; el recibo parcial no se probaba | cierto | 15 + 10 (arriba); `veredicto_recibo` es puro y tiene test |

Re-smoke tras la adenda ($0,56): `appendix` hp017#1 → 0/5 → **5/5 ALCANZABLE** (cobertura con predicado: regla/condición/alarma/equipo); `serve` pareado sobre carrier ya servido → 0/5 → 0/5, misma vista en base y oráculo, prominencia declarada, `INCONCLUYENTE_SIN_COBERTURA_ATESTADA` (no se atestó cobertura: correcto). Recibos `evals/s324d_reachability_smoke_hp017_1_{appendix,serve}.json`. Tally: `evals/adversarial_review_log.jsonl` ts=2026-08-17T10:39:29 (Sol 7/7 confirmados, 0 FP; Fable 1/1).

