# s324d — Censo de COBERTURA DE PÁGINAS del corpus activo

2026-08-17T09:42:01Z · `chunks_v2` · **solo lectura, cero escrituras, $0 de LLM** · **1054/1054** documentos activos medidos (censo COMPLETO) · 1.336 GB de PDF descargados, leídos con PyMuPDF y borrados.

Mide lo que el censo de densidad no ve: páginas ENTERAS que no entraron. Contra la verdad del PDF (`page_count` de PyMuPDF), no contra `pmax`.

## Los 25 peores por texto nativo perdido (nativos − corpus)

|documento|pág|ausentes†|idioma|nativos|corpus|perdido|clase|gold|
|---|---:|---|---|---:|---:|---:|---|---|
|I56-3836-006_FAAST_XM_8100E_ML|110|11-22,24-28,30,3|de,it,fr,nl,|553.091|253.509|299.582|pp_otro_idioma||
|997-671-007-3_Configuration_PT|75|2-19,21-37,39-74|pt,?,otro|128.699|5.230|123.469|pp_otro_idioma||
|HLSI-MN-103I_V04 FR|73|2-9,11-17,19-72|fr,?|120.137|994|119.143|pp_otro_idioma||
|HOP-138-9PT-issue 6_01-2026_In|92|2-16,18-25,27-28|pt,?,otro|115.626|7.417|108.209|pp_otro_idioma||
|HOP-138-8PT-issue 5_01-2026_Co-|91|2-18,21-30,32,36|pt,otro,?,cs|108.429|4.769|103.660|pp_otro_idioma||
|HLSI-MN-025-I_NFS Supra Series FR 25|50|2-19,22-23,25-49|fr|95.327|1.726|93.601|pp_otro_idioma||
|HLSI-MI-130F.pdf|42|3-42|fr,otro,?|89.902|1.085|88.817|pp_otro_idioma+cola||
|NF30-50_Manuel_d'utilisation_lr.pdf|56|2-3,6-7,9-52,54|fr,?|82.497|1.288|81.209|pp_otro_idioma||
|VSN4-PLUS_ITA.pdf|42|2-20,22-41|it,?,otro|83.181|3.507|79.674|pp_otro_idioma||
|MI_KIDDE_KE_IO3144_631e.pdf|37|6-8,14-23,25,27,|sv,it,fr,nl,|130.476|56.415|74.061|pp_otro_idioma||
|CCD-103_Manual_ES_FR_GB_IT|170|89,91-97,99,102-|fr,it,?|223.803|150.184|73.619|pp_otro_idioma|sí|
|3103063-ml_r003_excellence_series_ad|41|6-9,15-27,30,37-|nl,it,de,fr,|128.618|57.062|71.556|pp_otro_idioma||
|MNDT102I_D FR VSN-RP1r_hlsi.pdf|35|1-6,8-10,13-33|fr,?|66.691|1.578|65.113|pp_otro_idioma||
|MNDT102I_D FR.pdf|35|1-5,8-10,12-33,3|fr,otro|66.048|1.419|64.629|pp_otro_idioma||
|1998M0901_FS24X_PT-BR54-10_PT-BR_Rev|36|1-16,18-28,31,34|pt,?,otro|68.978|4.432|64.546|pp_otro_idioma||
|997-670-007-3_Operating_PT|45|2-5,7-20,22-45|pt,?,otro|72.617|8.936|63.681|pp_otro_idioma||
|3103198-ml_r002_excellence_series_in|44|7-10,18,20-28,30|it,nl,de,fr,|143.689|80.835|62.854|pp_otro_idioma||
|MI_KE_IU3111_ZME_202407_ES_fde1.pdf|36|5-8,13-23,32,34-|de,it,fr,nl,|125.154|62.910|62.244|pp_otro_idioma||
|55310021-Manual-Centrales-Convencion|138|73,76-100,102-10|it,fr,?|167.333|107.617|59.716|pp_otro_idioma||
|MI_KE_IU3110_202407_ES_5e36.pdf|31|5-7,12-21,26,28-|nl,it,fr,de,|105.054|47.099|57.955|pp_otro_idioma||
|996-130-000-3 Manuel d'utilisation Z|28|2-23,25|fr|57.981|748|57.233|pp_otro_idioma||
|MNDT102P|32|1-7,9-29,31-32|pt,?,otro|57.609|1.737|55.872|pp_otro_idioma||
|NFS4_NFS8-2PLUS_MANU_ITA.PDF|26|2-6,9,11-25|it|57.810|4.030|53.780|pp_otro_idioma||
|MNDT040P|32|3,6-22,26,28-30,|pt,?|64.431|10.670|53.761|pp_otro_idioma||
|HOP-338-9PT-issue 4_01-2026_Op|64|2-26,28-38,40-55|pt,?,en,otro|59.630|5.957|53.673|pp_otro_idioma||

† páginas cuyo texto nativo NO aparece en NINGÚN chunk del documento (por palabras de ≥6 letras; <35 % de aciertos). `pp_` = `paginas_perdidas_`.

## Recuento por clase

|clase|n|gold|significado|
|---|---:|---:|---|
|sano|842|64|texto verificado en corpus; ratio normal|
|paginas_perdidas_otro_idioma|156|12|solo faltan páginas EN/FR/IT/DE/NL/PL/SV… (hojas multilingües)|
|escaneado_ocr_ok|43|1|sin capa de texto; el OCR de LlamaParse sí entró|
|texto_perdido|5|0|todas las páginas, pero <50 % del texto nativo|
|paginas_perdidas_sin_idioma|3|0|ausentes sin idioma adjudicable — exige ojo|
|sin_url|3|0|`source_url` vacío: NO medible|
|escaneado_sin_texto|1|0|sin capa de texto y corpus pobre: nada que recuperar|
|paginas_perdidas_es|1|0|**defecto real**: páginas ESPAÑOLAS ausentes|

**Afectados** por defecto accionable o no medible: **13** de 1054. De ellos **0** sustentan un gold (`pdfs_used` de `gold_answers_v1.yaml`) y **10** están en `doc_map.jsonl`. Los 12 documentos-gold tocados lo son solo por páginas en OTRO idioma.

## Verificado a ojo (no inferido)

- `Installation manual_conduct detector` (Uniguard, Detnov): manual DE/ES intercalado; las págs. 5 y 8 ausentes SÍ llevan castellano («Fije el soporte al conducto», «Taladre un orificio de Ø 51 mm»). **Pérdida real.**
- `TMP2_QRefnotiES` (OGGIONI): la pág. 1 ausente es la portada ESPAÑOLA («DETECTORES TÉRMICOS TERMOVELOCIMÉTRICOS TMP2 Manual de Usuario»). **Pérdida real**, clasificada `?` por ser portada con pocas palabras vacías.
- `085501987j PY X-M` (D-GB-F-RU-IT) y `15088SP`: las ausentes son alemanas/francesas la primera, y de una página con fuente rota la segunda (corpus 899k > nativo 528k). Benignas.
- Calibración: `HLSI-TI-007_VSN-4REL` — el `md` degenerado ya conocido (47 chars en corpus vs 2.252 nativos) cae en `texto_perdido`, como debía.

## Lo que este censo NO cubre (declarado)

1. **No mide impacto en respuestas**: ni retrieval, ni eval, ni si un gold cambia.
2. **`cobertura_page_number` no es pérdida**: es cota inferior (ver †); la clase se decide por TEXTO.
3. **Falsos «presente»**: una página que repite contenido de otra (tablas idénticas en dos idiomas) se da por presente → la pérdida medida es cota INFERIOR, nunca exagerada.
4. **Idioma**: 19 idiomas por palabras vacías; cs, hu, lt, sr… caen en `otro`/`?`. Una página española jamás cae en `otro` (sería el argmax), pero sí en `?`.
5. **PDFs sin capa de texto o con fuente rota**: no hay verdad contra la que comparar; `ratio_texto` > 1 es normal (LlamaParse añade markdown de tablas y descripciones de imagen).
6. **No medidos**: los 3 sin `source_url` y los 26 `document_id` con chunks que NO están activos (fuera de alcance).
7. **No mide calidad del chunk** (orden, tablas rotas, secciones), solo presencia de texto.
