# s316 — Propuesta: ejecutar la fase DERIVADOS sobre el lote Casmar (#68) — para el dúo

**Contexto de gobernanza.** El código que aquí se somete a revisión YA está mergeado
(`main` @ `f947fac`, DEC-194) y su dúo se declaró **con gap**: la sesión s315b corrió en
cloud sin `OPENAI_API_KEY`, así que el revisor principal cross-family (Sol) **no se
ejecutó**; solo el sub-agente Opus (13 hallazgos, aplicados). Esta sesión corre en local
con la clave disponible ⇒ el gap es cerrable y el Protocolo 3 lo exige: DEC-194 es
zona-de-dolor (corpus / ingesta / esquema). **Lo que falta no es cablear código: es
EJECUTAR el run contra producción**, que es la acción irreversible. Ataca el diseño y el
código con esa lente: *¿qué escribe mal, de más, o de menos, en la DB viva?*

**OBJETIVO + MÉTRICA de HOY**: cerrar TECH_DEBT #68 para el lote Casmar/Kidde s314 — 74
docs · 1.091 chunks que hoy tienen **0 enunciados y 0 hyq** (verificado contra producción
en esta sesión, no de memoria). Métrica de éxito: cobertura >0 en AMBAS tablas para los
docs del lote, con recibo y asa de rollback por `ingest_batch`. **NO toca ningún lever
medido de retrieval** — es cobertura de canales derivados ya VIVOS (`ENUNCIADOS_MULTIVECTOR`
DEC-090, `HYQ_TABLE` DEC-099), no un mecanismo nuevo. El corpus derivado cambia ⇒ freeze
per-eval (DEC-071e).

**Estado real medido hoy (fuente: DB de producción, no docs):**

| Magnitud | Valor |
|---|---|
| Lote (docs `ingested_at >= 2026-08-08`) | 74 docs · 1.091 chunks |
| Enunciados / hyq del lote | **0 / 0** |
| `chunks_v2_hyq` global | 70.126 filas · **70.126 textos distintos** · 1 vintage · 23.205 chunks cubiertos |
| `chunks_v2_enunciados` global | 22.842 filas |
| Corpus | 26.215 chunks · 1.243 documents |

## Recomendación

Ejecutar `scripts/derive_channels_lote.py --since 2026-08-08 --tag casmar314 --data-root
"<OneDrive>/Documents/Claude/Technical Bot"`, primero en dry-run (0 API) y luego
`--aplicar`, que orquesta E1→E2→H→V:

1. **E1 enunciados** — `enunciados_pass.py --to-dump` con Haiku vintage `h1` (el GO de
   DEC-102), QA in-run, ledger+resume, y `--budget-usd` calculado como
   `gastado_en_ledger + max(10, 3·coste_alto_del_lote)` (fix #7 del dúo Opus: el
   `--budget-usd` del generador compara contra el ledger acumulado **de por vida**, así
   que un techo absoluto pararía el lote N-ésimo en el doc 1 devolviendo éxito).
2. **E2 carga** — `s104_a3_load.py` por el camino acotado s273 (`--only-source-files`
   limitado a los docs **con filas en el dump**, `--rewrite-batch-tag
   enunciados-v1:casmar314:h1`, `--ledger-check`, `--ids-out` como manifiesto).
3. **H hyq** — `hyq_lote_pipeline.py`: vintage **por lote** append-seguro con
   `ingest_batch=hyq-lote-<tag>-<sha16 npz>`, reusando piezas pineadas del canal (PROMPT +
   few-shot con pin sha12, `parse_questions`, `embed_questions` voyage-4-large,
   `_insert_rows`). Generación pineada a `claude-sonnet-4-6` (NO hereda el `LLM_MODEL`
   vivo, hoy Opus 5).
4. **V** — verificación contra el **manifiesto de ids** que E2 declaró (no presence-check
   por doc) + conteo por `ingest_batch` + smoke self-hit vía `match_hyq`, y recibo JSON
   con el `DELETE ... WHERE ingest_batch = ...` de rollback.

**Contrato de convivencia de vintages (fix #1, el CRÍTICO — verificado en código hoy):**
`s102_hyq_load.py` borra en `--wipe` solo `like.hyq-v1-*` (línea 156) y su predicado de
aborto excluye `ingest_batch.not.like.hyq-lote-*` (líneas 165-166). Sin ese fix, un
`--wipe` global posterior habría borrado el lote sin camino de re-carga.

## Alternativas consideradas y descartadas

- **Re-correr el camino corpus-wide (s102) con el lote dentro**: exige re-embeber y
  recargar las 70.126 filas del vintage global para añadir ~4k — coste y ventana de
  riesgo desproporcionados, y rompería el pin del npz global vigente.
- **Dar el dúo por cerrado con el gap declarado** (lo que dejó s315b): el Protocolo 3 no
  admite gap auto-declarado en zona-de-dolor **cuando el lado que falta sí es ejecutable
  ahora**. Con autor y sub-agente ambos en Opus 5 (pin s292), el cross-family es el único
  lado que rompe la cámara de eco.
- **Cablear la fase dentro de `ingest_new.py`** en vez de driver hermano: acopla el alta
  de corpus (barata, sin LLM) con la derivación (cara, con presupuesto y resume propios);
  un fallo de la segunda dejaría la primera a medias. El driver separado permite re-lanzar
  la fase cara sin re-tocar la ingesta.
- **Ejecutar sin dry-run previo**: el dry-run es 0 API y estampa `evals/derive_lote_*_docs.txt`,
  que es la selección auditable que consumen E1/E2/H. Saltárselo pierde el artefacto.
- **`--solo hyq` para abaratar**: dejaría el lote a medias en el otro canal vivo, que es
  justo la definición del gap #68.

## Gaps / riesgos declarados (de entrada, sin esperar pushback)

1. **Dedup cross-vintage por TEXTO GLOBAL — el riesgo nº1 y el que más quiero que ataques.**
   `hyq_lote_pipeline.fase_cargar` descarta toda pregunta del lote cuyo texto normalizado
   ya exista en la tabla **para cualquier otro chunk del corpus** (`textos_ajenos`). Como
   el vintage global tiene 70.126 textos **globalmente únicos** (medido hoy), toda
   pregunta genérica que un manual nuevo comparta con el corpus viejo se cae, y **el doc
   nuevo pierde siempre** (keep-FIRST asimétrico). Atenuante verificado: el lane hyq es
   `doc_scoped_hyq_coverage` (document-scoped), así que esto NO desvía a otra marca — pero
   sí deja al lote con menos cobertura, que es literalmente el «corpus de segunda clase»
   que #68 viene a cerrar. **Peor aún, es invisible en la verificación**: `universo`
   excluye los `dup_cross` ANTES de contar, de modo que V puede dar ✅ con el 90% de las
   preguntas del lote descartadas. Preguntas para ti: ¿es correcta la paridad con el
   corpus-wide, o el dedup debería ser **por (chunk_id, texto)** o por documento? ¿Debería
   V fallar, o al menos avisar, si `dup_cross / total` supera un umbral?
2. **`_docs_del_lote` toma `source_file` del PRIMER chunk** (`limit: 1` **sin `order`**):
   un documento cuyos chunks tengan `source_file` heterogéneo entraría parcialmente, y la
   fila elegida no es determinista entre runs.
3. **Selección por `documents.ingested_at` pero derivación por `source_file`**: si un
   documento viejo compartiera `source_file` con uno del lote, `_chunks_del_lote` arrastraría
   sus chunks al lote. No verificado que no ocurra en este lote.
4. **V mezcla estados cuando se usa `--solo hyq`**: la verificación de enunciados se
   dispara con `ids_out.exists()`, así que un `derive_lote_<tag>_enun_ids.json` de un run
   anterior produce un veredicto stale en el recibo nuevo.
5. **`product_model` centinela**: en `fase_generar`, un chunk con `product_model` NULL
   escribe la cadena literal `"el equipo del manual"` en `chunks_v2_hyq.product_model`. Se
   declara como paridad deliberada con el corpus-wide, pero contamina una columna de
   identidad con una frase.
6. **`_existing_pairs_tagged` descarga la tabla entera** (70.126 filas con texto) en cada
   carga: hoy es tolerable, pero crece lineal con el corpus y es el patrón que habrá que
   pagar en cada lote futuro.
7. **Coste estimado y su banda**: enunciados $4-11 (banda T2 observada, DEC-102) + hyq
   ≈$4,4 (1.091 chunks × $0,004) + Voyage <$1. La banda de enunciados viene de un lote de
   perfil distinto; puede desviarse.
8. **VACUUM post-carga** (fantasmas HNSW, DEC-088) queda como recordatorio en el recibo,
   no como paso ejecutado.
9. **No hay medición de efecto**: este run aumenta cobertura, no demuestra mejora de
   respuesta. No se declarará ningún delta de calidad a partir de él.

## Por qué BP + estructural + escalable

- **BP**: dry-run por defecto y 0 API; presupuesto duro dimensionado contra el ledger real;
  todo resumible (ledger, done-set del jsonl, idempotencia por `UNIQUE(chunk_id,question)`);
  piezas del canal **importadas**, no reimplementadas (mismo PROMPT, mismo parser, misma
  receta de embedding), con pin sha12 del few-shot para que una edición del gold no cambie
  el prompt en silencio; recibo con asa de rollback selectivo por `ingest_batch`.
- **Estructural**: ataca la raíz de #68 —que la ingesta no alimenta los canales derivados
  vivos— en el seam correcto, y establece el **contrato de convivencia de vintages**
  (`hyq-v1-*` global vs `hyq-lote-*` aditivo) que antes no existía y sin el cual el
  incremental era imposible sin recargar el corpus entero.
- **Escalable**: cualquier lote futuro (Aritech/Edwards, Tyco, Hikvision…) usa el mismo
  driver con otro `--tag`; el coste crece con el lote, no con el corpus, salvo el punto 6
  de los gaps.
