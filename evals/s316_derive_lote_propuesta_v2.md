# s316 v2 — Fixes al pipeline de derivados (#68) tras el dúo: para revisión adversarial

> ## ⚠ RESULTADO DEL DÚO: **NO-SÓLIDO**. Este documento queda como REGISTRO, no como diseño vigente.
>
> Sol (4 críticos) y el sub-agente Opus (3 críticos + 8 más) convergieron en que la pieza
> central —la semántica nueva de dedup— **es un no-op**: `parse_questions`
> (`s101_hyq_embed.py:44`) ya deduplica global por texto dentro del jsonl, así que
> `dup_intra_doc ≡ 0` y `UMBRAL_DEDUP` era código muerto.
>
> **La afirmación de la sección «decisión de semántica» de que «entre documentos NO se
> deduplica» era FALSA**: `tests/test_s315_derive_lote.py:41-53` fija como contrato lo
> contrario. Y el atenuante que declaré (family-parity del RPC) era over-claim: el RPC
> global trunca a `LIMIT 200` **antes** de filtrar por familia (TECH_DEBT #52).
>
> **Alberto adjudicó revertir** (10 ago). El dedup vuelve a la semántica original; se
> conservan los fixes que sí son fixes. Ver **DEC-196** para el estado vigente y
> `tests/test_s316_derive_lote_fixes.py` para los contratos que ahora sí están fijados.

**Qué revisar.** NO es un diseño nuevo: son los fixes aplicados a
`scripts/derive_channels_lote.py` y `scripts/hyq_lote_pipeline.py` en respuesta a los 8
hallazgos de Sol sobre la v1 (`evals/s316_derive_lote_propuesta_v1.md`), más una decisión
de semántica adjudicada por Alberto. El código está **sin commitear** en el working tree.
El run contra producción (~$10-16, escribe en `chunks_v2_enunciados` y `chunks_v2_hyq`)
**no se ha ejecutado** y depende de esta revisión.

**Pregunta central para ti:** ¿queda alguna ruta por la que este pipeline pueda escribir
en producción y declarar cobertura completa sin tenerla? Y: ¿la semántica nueva de dedup
es correcta y escalable, o rompe algo que la vieja protegía?

## Estado verificado (DB de producción, hoy)

74 docs · 1.091 chunks del lote con **0 enunciados / 0 hyq**. `chunks_v2_hyq`: 70.126
filas, 70.126 textos **globalmente únicos**, 1 vintage. Dry-run post-fix: 74 docs / 1.091
chunks, firma `77e3ae58900afdc7`, comprobación de fuga **sin hallazgos** en este lote.
Suite: 3657 passed / 1 failed antes de los fixes → el fallo (`test_clis_exponen_contrato`)
era `UnicodeEncodeError` en Windows; ahora 139/139 en los ficheros tocados.

## Los fixes (uno por hallazgo)

| # | Hallazgo de Sol | Fix aplicado |
|---|---|---|
| C1 | V imprimía ❌ y devolvía **0**; manifiesto ausente/vacío no fallaba | V es **fail-closed**: acumula `fallos[]` (manifiesto ausente, manifiesto vacío, ids incompletos en DB, docs sin enunciados, hyq sin recibo, hyq incompleto), el recibo estampa `veredicto: COMPLETO\|INCOMPLETO` + `fallos`, y `main` devuelve **1** |
| C2 | lote por `document_id` pero materializado con **un** `source_file` (`limit:1` sin `order`) | `_source_files_de_doc` pagina TODOS los chunks y devuelve el conjunto de source_files; `_verificar_biyeccion` compara, por cada source_file, el recuento **corpus-wide** contra el recuento **dentro del lote** y ABORTA si hay chunks de documentos ajenos (la fuga que s288 F2 prohíbe en runtime) |
| C3 | errores de API intermitentes se saltaban y la fase devolvía éxito; `poison` restado del universo | `errores_totales` cuenta los saltados y `fase_generar` devuelve **1** si hay alguno; `ok_count = (n_batch == len(universo)) and not poison` |
| M4 | el dry-run no congelaba la selección | firma sha256-16 sobre `{docs, document_ids, chunks}` persistida en `derive_lote_<tag>_seleccion.json`; `--aplicar` **aborta** si la firma cambió, salvo `--refrescar-seleccion`; nuevo `--hasta` como cota superior de `ingested_at` |
| M5 | dedup global por texto (ver abajo) | dedup **por documento** + puerta de tasa |
| M6 | `_existing_pairs_tagged` leía cualquier no-200/206 como fin de paginación | `raise_for_status()` |
| M7 | «no toca ningún lever» minimiza: añadir filas a dos índices vivos cambia pools | **Aceptado, no cerrado en código**: se declara canario obligatorio pre/post (`scripts/factlevel_assessment.py smoke`) como condición del `--aplicar`. Ver «gap abierto» |
| m8 | `"el equipo del manual"` persistido como `product_model` | la fila guarda el `product_model` REAL (NULL si no hay); el centinela solo entra al prompt |

También: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (convención de 143
scripts del repo) en los 4 del camino que la omitían — sin ella, en Windows con salida
capturada un `print` con `→ ≈ ─ ✅ ❌ ⚠` **aborta el run a media carga**.

## La decisión de semántica (dedup) — adjudicada por Alberto: «lo que sea BP/escalable»

**Antes**: se descartaba toda pregunta del lote cuyo texto normalizado ya existiera para
**cualquier** chunk del corpus, y los descartes se excluían del denominador **antes** de
verificar (V podía dar ✅ con el lote vaciado).

**Argumento de escala que decide**: con 70.126 textos globalmente únicos, el primer
fabricante ingestado se queda **para siempre** con toda pregunta genérica; cada marca
nueva entra sin cobertura question-side. A 30+ fabricantes eso no es un detalle, es el
«corpus de segunda clase» de #68 convertido en invariante. Y **no es inocuo**: corregí un
error propio aquí — el canal hyq no es solo document-scoped, `retriever.py:1256`
(`_hyq_table_hits`) llama al **RPC global `match_hyq`**, así que la pregunta de la marca
nueva solo podría aterrizar en el chunk de la marca vieja (atenuado, no eliminado, por
`_hyq_family_filter`).

**Ahora**: keep-FIRST por `(document_id, texto normalizado)` — la redundancia se juzga
dentro del documento, que es lo que «pregunta repetida» significa para un consumidor con
family-parity. Entre documentos no se deduplica; el único invariante duro sigue siendo
`UNIQUE(chunk_id, question)` del esquema. `document_id` se persiste ahora en el jsonl (se
selecciona en `_chunks_del_lote`), con aviso si falta. Puerta: `UMBRAL_DEDUP = 0.35`,
aborta ANTES de escribir si se supera. Observabilidad: se cuenta y estampa
`obs_dup_global_v1` — cuántas habría tirado la regla vieja — para poder medir el efecto
de este cambio sin volver a razonarlo de memoria.

## Alternativas descartadas

- **Mantener el dedup global y solo hacerlo visible/bloqueante**: conserva paridad exacta
  con el keep-FIRST corpus-wide, pero es la opción que NO escala — deja el problema de
  #68 intacto para toda marca futura.
- **Quitar todo dedup y confiar en `UNIQUE(chunk_id,question)`**: permite 4 preguntas
  casi idénticas de chunks distintos del MISMO documento compitiendo por slots del pool,
  que es lo que el dedup del parse corpus-wide sí evitaba con razón.
- **Migrar el manifiesto entero a `document_id`** (en vez de verificar biyección): es el
  fix más limpio, pero cambia el contrato de entrada de `enunciados_pass` y `s104_a3_load`
  (ambos consumen `--only-source-files`) ⇒ toca dos scripts congelados del canal por un
  caso que en este lote no se da. Se verifica y se aborta; queda anotado como deuda.
- **Gate de desplazamiento por lote** (instrumento `enunciados_panel`): a 1.091 chunks el
  precedente NO-GO de DEC-102 queda 2 órdenes de magnitud lejos; el canario del
  assessment es la medida proporcionada.

## Gaps / riesgos declarados

1. **M7 sigue abierto en código**: no hay canario automático pre/post. Es un paso manual
   declarado, no una guarda. Si se olvida, una regresión de pools entraría sin señal.
2. **`_verificar_biyeccion` cuesta ~2 queries por source_file** (148 en este lote) y es
   O(docs) en cada arranque, también en dry-run.
3. **El aviso `<sin-doc>`** no aborta: un jsonl generado por la v1 (sin `document_id`)
   agruparía todos los chunks bajo una sola clave y el dedup sería más agresivo de lo
   pretendido. Hoy no hay ninguno, pero es una trampa para un resume futuro.
4. **`UMBRAL_DEDUP = 0.35` es un número elegido, no medido** — no hay base empírica para
   0.35 frente a 0.25 o 0.5. Su función es que una sorpresa sea ruidosa, no ser exacto.
5. **`fase_generar` devuelve 1 con errores de API**, así que un lote con 1 chunk fallido
   por rate-limit exige re-lanzar. Es deliberado (fail-closed) pero puede ser molesto en
   lotes grandes.
6. **La firma de selección no cubre el CONTENIDO** de los chunks: si un chunk se re-escribe
   entre dry-run y `--aplicar`, la firma no cambia.
7. **Nada de esto mide calidad**: el run aumenta cobertura. No se declarará ningún delta.
