# s97 · Lever diversify → TIE-BREAK SEMÁNTICO de stamps planos (pre-registro **v2 POST-dúo**)

> v1 → v2: dúo completo (sub-agente 9 + cross-model 6, solapan 3 → **12 únicos confirmados,
> 0 FP**). Cambios marcados [H#/C#]. Tally: `evals/adversarial_review_log.jsonl` 2026-07-04.

## Diagnóstico (medido, config demo = multivector on; control famtie = 7)
- Trace de los 7 misses: hp012·'99+99' entra por CONTENT y muere EXACTO en diversify (1→0,
  determinista). hp018·'1 A' entra con 4, diversify corta 4→2 (borderline conocido,
  K-INESTABLE en s96). **hp011 fuera del lever** (0 en todas las etapas — premisa s93 STALE
  post-A3). cat013/cat016/hp013/hp014: nunca entran (otra clase).
- **Causa raíz (espiada):** `content_search` estampa `similarity` PLANA (`base_score` 0.80/
  0.70, retriever.py:554) → grupos grandes EMPATADOS → sort estable = orden-de-inserción
  arbitrario → el round-robin (lógica intocable, s59×2) selecciona a ciegas entre iguales.
  La aguja de '99+99' es el mejor chunk de su doc y quedó fuera por sorteo. **Ya documentado
  en DEC-050:** "10 hechos que el canal vectorial SANO rankea ≤50 expulsados del pool-50 por
  los keyword-stamps planos"; y DEC-050(d) dejó DECLARADA la candidata legítima "stamps
  intactos + cosenos acotados" — este lever ES esa candidata, en famtie.

## Fix: tie-break por coseno real, WITHIN-SOURCE only, clave-tupla
En `_diversify_by_source_file`: tras agrupar `by_source`, cada lista de fuente se ordena
por **clave-tupla `(-similarity, -coseno_real)`** — coseno calculado SOLO para chunks cuyo
`similarity` se repite dentro de su grupo (empates).
- **[H2 CRÍTICO-si-mal] `similarity` JAMÁS se muta** (el helper existente
  `_rescore_to_cosine` MUTA en :1002 — NO reutilizar ese patrón; el cosine-merge mutante es
  DEC-050 entero). Test que lo pinea: similarity intacta post-diversify.
- **[H6/C1] Scope WITHIN-SOURCE only:** el sort GLOBAL y `source_order` (por
  `by_source[s][0].similarity`, :2204-2208) quedan con la semántica actual — el desempate
  entre FUENTES sigue siendo el orden de inserción de hoy (declarado: es otro accidente,
  pero fuera de alcance para acotar el blast radius).
- **[H5/C4-C5] Implementación:** firma gana `query_embedding=None` (threadeado desde el
  call-site :1410 donde YA está en scope — NUNCA re-embeber dentro: con HyDE el embedding
  del pipeline es sobre `embedding_text`, no `query`); embeddings de empatados vía el
  helper EXISTENTE `_fetch_embeddings_by_id` (:961, batch 80, tabla activa, fail-open).
  Colateral declarado: `diversify_fn_sha` del manifest bvg cambia (control same-day cubre).
- **Flag `DIVERSIFY_TIEBREAK`** = `off` (default) | `cosine`; parser estricto fail-fast
  (lección s96-H3). Fail-open total (GET falla → orden actual).
- **[H7] Suplementos 0.72:** son grupo empatado → el tie-break los ordena también (en
  alcance, benigno — mismos ≤8). Combo con `MERGE_STRATEGY=cosine` (rescore_fn muta a
  coseno real → los empates desaparecen antes) = coherente por construcción; combo
  declarado no-primario (la demo corre MERGE default).
- **[H8] `_diversify_by_manufacturer`:** MISMA patología (empates 0.70, :1470/1553) —
  fuera de alcance CONSCIENTE (solo corre sin modelo; los 7 misses llevan modelo). Queda
  anotado como candidato futuro si la famtie de queries-sin-modelo lo pide.

## Encuadre vs settled [H1 — el juicio que el dúo marcó para el cross-model, y corrió]
Este lever **re-pisa un SUBSET del terreno DEC-050 bajo su caveat de vigencia** ("re-medir,
no recordar" — settled en PASS·pre-NOCAT; hoy se mide en famtie). NO es "no-overlap": los
PASS-golds cuyo top-5 vive DENTRO de un empate (p.ej. cat022, 4×0.85) pueden re-barajarse.
**El gate bvg del ship-path ES el test del colateral DEC-050: re-barajado profundo de
PASS-control = el mismo modo de fallo = NO-GO sin racionalizar.**

## Gate-0 [H4/C2 — la afirmación "rescata las dos" era extrapolación]
El probe inline (rank de la aguja por coseno DENTRO de su grupo empatado: hp012 2/16 ·
hp018 2/19) se re-ejecuta como **artefacto commiteado** (`scripts/s97_gate0.py` + json):
replay OFFLINE del `_diversify_by_source_file` REAL con el tie-break aplicado sobre pools
capturados → ¿la aguja ENTRA en el top-50 resultante? (rank-en-grupo ≠ selección: depende
de los 0.82/0.85 por encima, del cap por-fuente y del orden de fuentes). Si el replay no
la mete → NO construir el brazo (ahorra la medición).

## Medición pre-registrada [H3: norma DEC-090 aplicada]
- **famtie K=3 runs por brazo** (control off / tratamiento cosine, mismo día, freeze
  declarado [C3]: corpus/tabla-enunciados/flag-set/config env estampados en el yaml de
  salida). Banda del control declarada: 7±1 (hp018 inestable conocido).
- **G1:** flip PERSISTENTE (3/3 runs) de **'99+99'** (el determinista) y famtie mediana ≤6.
  hp018 = informativo (estabilización), NO decide el gate.
- **G2 [C6]:** LISTADO PAREADO de nuevas-miss por hecho (no solo agregado): cualquier
  nueva-miss persistente (3/3) = diagnóstico antes de nada (el tie-break desplaza a otros
  empatados — es el punto — pero no puede costar hechos juzgados).
- **G3:** latencia añadida medida (p50 del retrieve, patrón s96) — presupuesto ACUMULADO
  declarado: A3 ya añadió +725ms; este lever estima +200-500ms más ([H9]: payload real
  ~11-13KB/chunk → 60 empatados ≈ 660-780KB; frecuencia ≈ toda query-con-modelo).
- **Pasa G1+G2 → ship-path:** gate bvg 2 brazos (patrón DEC-090, con la lectura H1 arriba)
  → decisión Alberto flag-on. Falla G1 → trace por-hecho + archivar con veredicto (sin
  iterar-on-eval).

## Fuera de alcance (declarado)
hp011 (no entra a canales; residual fine-grained) · VALORES de los stamps (jerarquía
0.65-0.85 intocada) · lógica del interleave (s59×2) · `_diversify_by_manufacturer` [H8] ·
desempate ENTRE fuentes [H6].
