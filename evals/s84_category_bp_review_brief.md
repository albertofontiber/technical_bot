# Revisión adversarial — BP de los pre-filtros de metadato en el canal VECTORIAL (s84/F, zona de dolor retrieval)

## Contexto
El activo de identidad limpia (DEC-067) está construido. Al planear su CONSUMO en retrieval (fase F) surgió la pregunta de Alberto: **¿es BP filtrar la búsqueda VECTORIAL por metadato (categoría/modelo) cuando ya hay un canal léxico, o es un quick fix?** Claude (yo) afirmó un principio + recomendación + plan. **AVISO: en este MISMO hilo me equivoqué DOS veces sobre los hechos del código del retrieval** (afirmé "no hay filtro de categoría en el vectorial" y luego "es aditivo, no resta recall" desde un grep parcial; Alberto lo recordaba mejor y el código lo refutó). → **verificad mis claims de código AL PÍXEL, NO os fieis de mi resumen.**

## La CLAIM de Claude (a ATACAR, no a validar)
**Principio BP:** un pre-filtro DURO sobre el canal vectorial (ANN) es anti-patrón cuando (a) hay canal léxico que ya da precisión de identificadores, (b) el metadato es ruidoso/incompleto, (c) el query→filtro es frágil. El vectorial debe correr ANCHO (recall semántico); la precisión la dan el léxico (exact-match de códigos) + un POST-filtro/boost SOFT fail-open. Un pre-filtro duro en vectorial SOLO es BP para restricciones DURAS sobre metadato COMPLETO (tenant/permisos/idioma = seguridad), NO para facetas de relevancia (modelo/categoría).

**Recomendación:** la categoría como pre-filtro del vectorial = quick fix → retirarla/degradarla a señal SOFT (medido); el dato de categoría del activo de identidad → índice inverso / señal soft, NO resucitar el filtro duro poblándolo. Mismo trato que ya reciben los modelos (vectorial ancho + `_filter_to_query_models` post-filtro fail-open bajo estrategia no-stamps).

**Grounding (VERIFICAD cada punto contra el código):**
1. `vector_search` pasa `filter_category` al RPC `match_chunks` (`src/rag/retriever.py:882`); bajo `MERGE_STRATEGY="stamps"` (**default**, `src/config.py:75`) el vectorial principal corre CON `detected_category` (`:1108`); el comentario `:1096-1100` dice que con categoría detectada devuelve **~0 filas en ~85%** ("chunks_v2 tiene 0 chunks con categoría canónica", re-verif 12-jun-s68); broad-fallback capeado a **5** (flag `LEVER1_BROAD_FALLBACK` default OFF, `:1117`) → vectorial limitado a ~5 cuando dispara categoría.
2. **DEC-066**: el pre-filtro family-aware del canal vectorial fue **NO-OP MEDIDO** (el post-filtro + los canales léxicos ya dan la precisión). Claude transfiere esa lección a la categoría.
3. categoría del chunk = `_detect_category(source_path)` (heurística por path, `metadata.py:199`) ≠ taxonomía canónica de 54 términos del lado-query (`retriever.py:653` `_CATEGORY_PHRASES`/`CATEGORY_TERMS`) → mismatch de vocabulario.

**Plan de proceder:** Paso 0 = verificar `MERGE_STRATEGY` de prod (Railway); F = vectorial ANCHO + índice inverso producto→docs + post-filtro modelo/familia SOFT + categoría soft, MEDIDO; E (DB-apply de la identidad) gateado por que F mida ganancia.

## Lo que pido (bite concreto, anclado)
1. **VERIFICAD mis claims de CÓDIGO al píxel** (me equivoqué 2× ya este hilo): ¿el vectorial SÍ filtra por categoría bajo stamps y devuelve ~0? ¿el default es stamps? ¿el post-filtro de modelo `_filter_to_query_models` es fail-open? ¿el broad-fallback compensa o deja el canal limitado? ¿hay algo que MAL-LEÍ otra vez (p.ej. prod no corre stamps, o el filtro no es lo que digo)?
2. **ATACAD el PRINCIPIO BP**: ¿"pre-filtro duro en vectorial = anti-patrón con canal léxico" es correcto o SOBRE-GENERALIZO? ¿hay escenarios (recall-frontier, queries SIN modelo solo-categoría, multi-dominio PCI/CCTV/accesos) donde el pre-filtro de categoría SÍ ayudaría y los estoy descartando? ¿La analogía con DEC-066 (family pre-filter=NO-OP) TRANSFIERE a categoría, o categoría≠modelo la rompe (la categoría podría capturar una faceta que el léxico-por-modelo NO)?
3. **¿El plan es BP/estructural/escalable, o me dejo algo?** ¿Retirar el filtro de categoría puede ROMPER queries categoría-bound sin modelo ("¿qué centrales tenéis?")? ¿El índice inverso es la estructura de consumo correcta? ¿QUÉ medir exactamente para no shippear otro NO-OP NI una regresión?
4. ¿Es esto el siguiente paso correcto en F, o hay algo más prioritario (p.ej. la QA de los 985 primero)?

Distinguid ERROR-DE-HECHO (mi claim de código es falso) de DESACUERDO-DE-CRITERIO (el principio BP es debatible). Verificad contra código/DEC-066 antes de afirmar (regla C). El cross-model es INNEGOCIABLE aquí: autor y sub-agente son ambos Opus.
