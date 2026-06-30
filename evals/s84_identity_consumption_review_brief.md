# s84 F1 — Consumo de identidad (índice inverso producto→docs): diseño + plan de medición

**Qué reviso:** el DISEÑO del consumo del activo de identidad limpio (DEC-067) en retrieval, y
el PLAN de medición factorial, ANTES de cablear (Protocolo 3, zona de dolor retrieval/identidad →
cross-model INNEGOCIABLE). El objetivo es que muerdas: (1) ¿es un NO-OP encubierto, como el
pre-filtro de DEC-066? (2) ¿el diseño respeta el canon (aditivo, no filtro duro; DEC-068)? (3)
¿el plan de medición aísla el lever sin confound (#49 = medir 2 flags juntos)?

## Contexto (estado verificado)
- El activo (`evals/s83_document_models_final.jsonl`, 1014 docs / 2761 productos) mapea doc→modelos
  LIMPIO, multi-label, dúo-validado + adjudicado por Alberto. Branch-local, NADA en DB.
- Retrieval HOY resuelve identidad SOLO vía el column `product_model` por-chunk (sucio, ~200/1170
  docs con identidad-sucia por audit 1a): `keyword_search` usa `imatch product_model`
  (retriever.py:385); `_filter_to_query_models` filtra por substring de product_model (1424);
  `_diversify_by_source_file` siembra su set de docs vía `_get_source_files_for_model` (1554), que
  consulta `imatch product_model`.
- `source_file` (el doc) es LIMPIO y estable. El activo mapea modelo→source_files limpiamente.
  **JOIN verificado: los 1014 docs del activo casan EXACTO con `source_file` en chunks_v2 (1014/1014).**

## Verify-first (el gate ANTES del gate; $0, read-only) — el resultado que motiva F1
Diagnóstico de divergencia por gold (`s84_divergence_diag.py`): para cada dev gold, comparé
`S_clean(m)` (source_files que el activo dice que cubren el modelo m) vs `S_db(m)` (source_files que
el path actual alcanza vía `imatch product_model`, FIEL a prod usando `model_to_imatch_pattern`).

- **Divergencia REAL en 17/39 dev golds** (el índice inverso alcanzaría ≥1 doc que el tag sucio
  pierde). 6 de la frontera de recall: hp006, hp008, hp009, hp018, cat007, cat022.
- Casos canónicos:
  - **hp009** (ZX2e/ZX5e, el K-INESTABLE de DEC-066): NEW=3 docs limpios (`MIE-MC-530`+2),
    **removes=0** → upside limpio sin pérdida.
  - **hp006** (AFP-400): NEW=4 incl. `MADT170`.
  - **cat008 MI-DMMI**: la DB tiene **0 chunks** taggeados; el activo sabe que 2 docs lo cubren
    (mis-atribución clásica — el caso `LEVER2_PM_RESCUE`, pero data-driven en vez de heurística
    string-en-filename).
- **CONTRASTE con DEC-066:** el pre-filtro vectorial era estructuralmente redundante (los léxicos ya
  pre-filtran) → inerte. El índice inverso NO es redundante: alcanza docs que el tag sucio EXCLUYE.
- **CAVEAT (constraint de diseño):** las columnas `removes` son grandes en varios casos (DXc 17,
  RP1R 14, FAAST LT 10). Usar el activo como FILTRO DURO reventaría recall → **el consumo DEBE ser
  ADITIVO** (canon DEC-068: identidad→boost/augment, nunca filtro duro; el EQ-filter es el error hp008).

## Diseño propuesto (F1, aditivo, flag-gated, branch-local)
1. **Build $0**: invertir `document_models_final.jsonl` → índice estático `model(norm canonical+aliases)
   → {source_files, role}` (versionado en `data/` o `evals/`). Re-ejecutable, sin DB, sin coste.
2. **Consumo quirúrgico**: en el seam de diversify, AUMENTAR el set de source_files por modelo con el
   del índice inverso (UNIÓN; clean-first en el orden). Flag `IDENTITY_INDEX` (default OFF). Concreto:
   `_get_source_files_for_model(m)` ∪ `inverse_index[norm(m)]` cuando el flag está ON.
3. **Reúso total del pipeline existente**: `_fetch_top_chunks_by_source_file` ya trae solo los chunks
   relevantes-a-la-query DENTRO de cada doc (FTS por keywords de CONTENIDO), y los filtros de idioma /
   lifecycle / fail-open siguen. → recall puro aditivo, sin churn de la frontera de ranking.
4. **NADA en DB.** El índice vive en el repo; el column `product_model` no se toca. (E = re-taggear la
   DB es OTRO bloque, gateado por que F mida ganancia; stop-line de Alberto.)

## Plan de medición (factorial, freeze completo)
- **Factorial 2×1**: base (MAIN congelado, `IDENTITY_INDEX=OFF`) vs treat (`IDENTITY_INDEX=ON`), sobre
  los dev golds. (LEVER2_IDENTITY se mantiene en su estado de MAIN en AMBOS brazos → aísla el índice
  inverso, NO lo confunde con la resolución de token — evita #49.)
- **Freeze completo**: corpus (chunks_v2 snapshot), índice, embeddings+cache, juez (GPT-5.5 K-mayoría),
  seeds, config, proconfig. Manifest congelado (estilo s63/s73).
- **2 ejes**: completitud↑ SIN invención↑ (no basta recall — reach≠PASS, lección DEC-066).
- **Held-out EMBARGADO** (no se toca; 12 golds).
- **Criterio**: mide Δ_net en eval, no proxies. El verify-first (divergencia) NO es la métrica — es solo
  el gate que dice "vale la pena pagar el factorial". Si el factorial sale NO-OP/GRIS → no se shippea
  (eval-driven), aunque la divergencia exista.

## Alternativas descartadas
- **Activo como filtro duro** (admitir SOLO clean source_files): reventaría recall (removes 14-17 en
  DXc/RP1R) + viola DEC-068 (identidad nunca filtro duro).
- **Re-taggear la DB primero (E)**: riesgo NO-OP sin medir el consumo (la trampa exacta de DEC-066);
  E va gateado por F. Además irreversible-costoso vs el índice branch-local.
- **Re-abrir L-i / quitar el filtro de categoría**: SETTLED-archivado ×3 (DEC-040/050/042); el
  bloqueante es el RANKING, el filtro ya está inerte. NO se re-litiga (DEC-068).
- **Reemplazar `_get_source_files_for_model` (no unión)**: perdería los docs que el tag SÍ acierta y el
  activo (como secundario/mention) podría no listar → unión es estrictamente ≥ recall.

## Gaps / riesgos declarados
1. **Divergencia ≠ PASS** (la disciplina #49): que el índice alcance un doc nuevo no prueba que el doc
   contenga el hecho del gold ni que flipee el veredicto. Solo el factorial lo decide. Riesgo de NO-OP/GRIS
   sigue VIVO (hp018 fue GRIS en DEC-066 por residual de generación, no de recall).
2. **Ruido aditivo**: unir docs limpios podría meter chunks que desplacen a uno mejor en el top-k antes
   del rerank → posible regresión en golds NO-identidad. El factorial sobre los 39 lo capta (no solo los 17).
3. **Normalización de claves**: `40-40`→`4040` no casó con el activo (cat021/cat022) — el activo usa
   estilo `40/40`. Hay que reconciliar normkey activo↔retriever o se pierden golds.
4. **985 no human-validados** (QA pendiente) → un error compartido OCR/es-en/OEM en el activo se
   propagaría como recall espurio; mitigado por ser aditivo + relevancia-por-contenido downstream.
5. **`source_file` 1:1 con doc**: asumo un doc por source_file; si un source mezcla docs legacy el
   lifecycle filter ya lo cubre (post-fetch).

## Por qué es BP + estructural + escalable
- **Estructural (raíz)**: ataca la causa (resolución modelo→doc sobre tag sucio) con el activo limpio,
  no un parche por-gold. Reúsa el pipeline de diversify ya probado.
- **Escalable 30+**: el índice cubre los 1764 modelos del corpus, no solo golds-touching; un fabricante
  nuevo entra al re-invertir el activo (que ya es multi-marca).
- **Reversible**: flag OFF por default, branch-local, DB intacta.
- **Eval-driven**: gateado por Δ_net medido; divergencia es el gate-0 barato, no el veredicto.
