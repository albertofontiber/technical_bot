# s324d — La ingesta perdía documentos enteros por un `or`: guarda de MARKDOWN DEGENERADO (TECH_DEBT #87)

**Estado: cableado en `claude/s324d-autonoma` (commit d7ec670), NO mergeado. Suite verde. NADA re-ingestado
todavía** — la re-ingesta de `HLSI-TI-007_VSN-4REL` espera a esta revisión. Producción (serving) no cambia:
esto es etapa B de ingesta.

## El hallazgo (verificado hoy, no inferido)

TECH_DEBT #87 decía «ingestas VACÍAS → hace falta OCR». **Era un diagnóstico equivocado y lo probé en tres pasos:**

1. El PDF de `HLSI-TI-007_VSN-4REL` (bucket, 1 página) tiene **2.246 chars de texto NATIVO** (PyMuPDF
   `page.get_text()`), con procedimiento técnico real: configuración por puente PROG + tecla Z1, combinaciones
   Z1/Z2/Z3 = nº de placas VSN-4REL, cables de 40 cm (central→módulo) y 6 cm (entre módulos). No es un escaneado.
2. Re-parse con la **config real del corpus** (`parse_page_with_agent` + `anthropic-sonnet-4.5`, job
   `1b73eb2d-34c3-4f32-9e9b-8323a47287c0`, 25 s, ~$0,06): LlamaParse devuelve para esa página
   **`md` = 34 chars** (`"\n\n**Honeywell Life Safety Iberia**"`) y **`text` = 3.708 chars**. El contenido está
   en el JSON, en el campo de al lado.
3. Los tres consumidores del JSON hacen `p.get("md") or p.get("text") or ""`
   (`chunk.py:270`, `contextualize.py:66`, `language.py:112`). Ese `or` sólo cae a `text` cuando `md` es
   **vacío**; con 34 chars es *truthy* y gana. El corpus se quedó con **47 chars**.

⇒ La respuesta a «¿hace falta OCR / es compatible con LlamaParse agentic?» es: **LlamaParse agentic YA es la capa
de OCR** (LVM multimodal lee la página como imagen) y aquí ni siquiera hizo falta —el PDF tenía texto—; lo que
faltaba era una **guarda contra su propio markdown degenerado**.

## El cambio

`src/reingest/page_content.py` (nuevo, leaf, sin dependencias):
- `page_content(page)` — devuelve `text` en vez de `md` **sólo** si `len(md) < 0.25·len(text)` **y** la pérdida
  absoluta es `≥ 500` chars. Los dos umbrales juntos hacen improbable el falso positivo (un markdown legítimamente
  más corto —el agente limpia cabeceras/pies— pierde decenas de chars, no miles).
- `sanear_record(record)` — copia dirigida del registro con las páginas degeneradas saneadas + auditoría. No muta
  el original ni el store en disco.
- `auditar_paginas(pages)` — censo (páginas afectadas, chars rescatados) para declararlo.

`src/reingest/pipeline.py` (`process_file`):
- **Sanea UNA vez, en el orquestador**, antes de B2 (idioma) / B3-B4 (chunking) / B7 (contextualización), con
  `logger.warning` si dispara. El registro de estado devuelve `md_degenerado`, `chars` y `texto_escaso`.
- **Aviso de texto escaso** (#87): si el documento sale de la ingesta con `< 300` chars, se declara en el estado y
  en el log. **No bloquea** (hay hojas de un párrafo legítimas): declara, que es justo lo que faltó con TI-007.

**Por qué en el orquestador y no en los tres consumidores** (mi primer intento, revertido): `src/reingest/chunk.py`
está **pineado por sha en un freeze-contract ACTIVO de CI** (`evals/s132_ci_evidence_contract_v1.yaml` →
`s130_chunker_utf8_lf`, del pre-registro s130 que congela el chunker como instrumento). Al tocarlo, el test
`test_s130_prereg_has_portable_active_source_receipts` se puso rojo y me paró. Además, normalizar la ENTRADA es
responsabilidad del orquestador: un solo punto, y los tres consumidores ven la misma página.

Tests: `tests/test_s324d_page_content_guard.py` (13 tras el dúo): caso real de TI-007; no-disparo con md legítimamente más
corto (ratio 0,87 y 0,30); no-disparo en páginas cortas; comportamiento previo intacto; auditoría; `sanear_record`
no muta el original y es inerte sin degeneración; y el contrato de que el pipeline sanea ANTES de leer y de que
`chunk.py` sigue con su `or` (freeze respetado).

## Dimensionamiento (medido hoy, censo completo del corpus activo)

26.215 chunks / 1.054 documentos activos. Densidad **mediana: 2.632 chars/página**; **19 documentos** por debajo de
250 chars/página, y la mayoría son **fragmentos PT/FR/IT** ya conocidos (política de idiomas s65/DEC-066:
HOP-138-9PT, 997-671-007-3_Configuration_PT, VSN4-PLUS_ITA, HLSI-MN-103I FR…). Los casos ES reales son
**TI-007** (47 c/p) y **«Docs Morley-IAS Max - QR»** (142 c/p, es un QR: baja o sustitución). ⇒ **La patología no
es masiva**; no vendo que esto suba muchos OKs. El censo que **no** se ha hecho todavía —páginas ENTERAS ausentes,
que la densidad no ve— está corriendo aparte (`s324d_censo_cobertura_paginas`).

## Riesgos y gaps declarados

1. **Umbrales no calibrados contra la distribución real**: el store de extracción del corpus (966 JSON de mayo) NO
   está en este checkout, así que `0,25`/`500` se eligieron conservadores, no medidos. La guarda falla hacia el
   comportamiento ACTUAL (usar `md`). Declarado en el módulo.
2. `text` de LlamaParse puede traer ruido que `md` limpia (pies/cabeceras repetidos, orden de columnas): en las
   páginas saneadas el chunking estructural pierde los headers markdown → chunks menos estructurados. Es un
   trade-off consciente: prefiero contenido con menos estructura que ausencia de contenido.
3. El corpus **ya ingestado** no se re-procesa con esta guarda: sólo aplica a futuras ingestas y a lo que se
   re-ingeste a mano (TI-007). No hay re-ingesta masiva planificada ni presupuestada.
4. El aviso de texto escaso usa un umbral absoluto (300); un manual de 100 páginas que pierda el 90% lo pasa. Ese
   agujero lo cubre el censo de cobertura de páginas, no esta guarda.

## Qué pido al revisor

(a) ¿Puede la guarda producir un contenido PEOR que el actual en algún caso realista (md limpio vs text ruidoso)?
(b) ¿El punto de saneamiento (orquestador, antes de B2) deja algún consumidor fuera —`full_document_text`,
`profile_document`, dedup, provenance— que siga leyendo el `md` original?
(c) ¿Los umbrales 0,25/500 son defendibles sin la distribución, o el diseño debería exigir medirla primero?
(d) ¿El aviso de texto escaso debería BLOQUEAR la indexación en vez de declarar?
(e) Cualquier claim de este documento que el código o los datos no sostengan.

---

## ADENDA — dúo r35 (17-ago): Sol GPT-5.6 xhigh 5 hallazgos + Fable 5 (11 `tool_use` reales) — TODOS verificados y APLICADOS

**El emparejamiento se rompió y la causa está identificada:** lancé Fable con `--sol-ts` correcto, pero entre
ambos runs **un agente de medición en background escribió ficheros nuevos** (`evals/s324d_censo_cobertura_paginas_*`),
el snapshot del repo cambió y el runner rechazó unir los recibos («Sol y Fable no revisaron exactamente los mismos
bytes ordenados»). La review de Fable se guardó como **standalone válida** (11 `tool_use` reales, auditoría #86
activa) y sus hallazgos se aplican igual. **Lección para TECH_DEBT #86**: la regla no es sólo «no muevas HEAD
durante un dúo emparejado» — es «que nadie escriba en el árbol», agentes incluidos.

| # | Hallazgo | Quién | Verificación | Qué cambió |
|---|---|---|---|---|
| 1 | **CRÍTICO — `md` de sólo whitespace se perdía igual**: `page_content()` caía a `text`, pero `page_content_degradada()`/`sanear_record()` usaban OTRO criterio y no sustituían; `"\n\n"` es *truthy* para los consumidores ⇒ la página se perdía. Mi test probaba el helper, no la ruta cableada | Sol | cierto (dos criterios divergentes en el mismo módulo) | criterio **ÚNICO** `_degenerado()` que comparten `page_content`, `page_content_degradada`, `motivo_degeneracion`, `auditar_paginas` y `sanear_record`; test sobre la RUTA CABLEADA |
| 2 | **Falso positivo realista**: una página de tabla/diagrama puede tener `md` compacto legítimo y `text` largo y disperso ⇒ sustituir EMPEORA | Fable | plausible y no acotado | tercera condición: un `md` **con estructura** (heading, lista, tabla, cita, bloque de código) NO se sustituye, mida lo que mida. El `md` de TI-007 (cabecera suelta) no la tiene |
| 3 | **La auditoría no viajaba en todos los caminos**: `register_only`, `empty`, `empty_after_language`, `sin_indexar` la perdían, y `run()` no la persistía ni en `done` — justo donde acaba un documento roto | Sol + Fable (coincidentes) | cierto | `**audit` en los cuatro caminos + `_traza_extraccion()` persistida en el estado de los cinco estados; test que lo ancla |
| 4 | **Un CUARTO consumidor, y en SERVING**: `rag/deep_lookup._item_text` (brazo `fetch_mode()=="llm"`) leía el store crudo con el mismo `or` ⇒ el outline del selector LLM seguía ciego justo en los docs rescatados | Fable | cierto (`deep_lookup.py:56-69`) | usa la misma guarda; declarado en el módulo |
| 5 | **`chunk_provenance.materialize_raw_record` no está saneado** | Sol | cierto | **NO se sanea a propósito**: su contrato es reproducir el artefacto CRUDO con el chunker congelado y sólo lo usan scripts de auditoría s117/s135 (verificado); declarado en el módulo |
| 6 | «Caso real» con `"X"*3708` y recuento de tests inflado (9 vs 8) | Sol + Fable | cierto | fixture con el JSON **real** del job (`tests/fixtures/s324d_ti007_llamaparse_page1.json`); el test comprueba que lo rescatado contiene `PROG`, `Z1`, `VSN-4REL`, `40 cm`; **13 tests** |
| 7 | `texto_escaso` se mide tras el filtro de idioma (un `register_only` nunca se evalúa) | Fable | cierto | declarado en el código |

**Condición del dúo que NO se pudo cumplir (declarada, no tapada):** Fable exigió correr `auditar_paginas` sobre el
**store real de 966 JSON antes de mergear**. Ese store no está en este checkout **ni en el OneDrive de esta máquina**
(busqué; sólo hay 2 JSON locales). Queda como condición pendiente en TECH_DEBT #87: con el store delante son minutos
y $0. Mientras tanto, la guarda es conservadora (tres condiciones AND) y falla hacia el comportamiento actual.
