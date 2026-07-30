# s287 — ETAPA 2 (rerank 4→<2): diseño pre-dúo tras el diagnóstico read-only

## DIAGNÓSTICO (agente Opus, 0 llamadas de modelo, anclas verificables)
Son **2+2 por costura distinta a la esperada** — ningún «lexical-distractor» es colisión de valor:
- **Grupo A (orden within-doc)**: cat010#0 (soporte en pool_rank **0**, desplazado por 10/10 del
  MISMO manual repartido en DOS document_id gemelos con `duplicate_of=NULL` — pares casi
  byte-idénticos ocupando slots) · cat017#4 (rank 4; la pregunta tiene DOS verbos y 8/10 slots
  se van al primero — monopolio de sub-intención; la atribución TOC de DEC-096 está STALE:
  el TOC ya no está en el top-10).
- **Grupo B (identidad, el reranker acierta)**: hp018#1/#4 (mismo chunk-soporte, tabla specs
  ZXe p.43, pool_rank **49/50**; 8/10 slots son PRIMOS ZXSe/ZX50/DXc/ZXAE portando los MISMOS
  valores — DEC-091b literal). hyq Y enunciados cubren el soporte VERBATIM y aun así no entra.

## CAUSA RAÍZ del Grupo B (regresión por interacción de dos cambios correctos por separado)
1. T3/s285 re-tagueó el corpus a FAMILIA: `pm='ZXe'` — `pm ilike ZX1e/ZX2e/ZX5e` = **0 filas**.
2. El perfil C1 v3+ impone `IDENTITY_RESOLVE_POLICY=replace` fail-fast (DEC-149§1a/DEC-152):
   ZXE→{ZX1e,ZX2e,ZX5e} con drop del token 'zxe' → `_filter_to_query_models` = **0
   supervivientes** → fail-open (retriever.py:2152) → **el filtro de familia queda DESARMADO**
   y entran los primos.
3. El guard `all_members_consumable` no lo paró porque valida el CATÁLOGO (estado==activo),
   no las etiquetas del CORPUS (catalog_store.py:84-88) — consulta la tabla equivocada.
4. ADD fue el ganador MEDIDO (DEC-084: hp018 4/4; replace regresaba hp009) — pero DEC-091b lo
   declaró BAND-AID (gana por coincidencia de VALOR, inseguro si difieren) y el flip a replace
   entró con el perfil sin re-medir hp018. Verificado read-only: con ADD el filtro conserva
   ZXe+ZXAE/ZXEE y tira ZXSe/ZX50/DXc = 6/10 slots de hp018.

## RECOMENDACIÓN (por orden; cada pieza con su gate)
**0. Instrumento primero ($0, S5 de DEC-096c ya declarado)**: puente prefijo-kilo en
   `support_l1_guard_allows` (6K8↔6800Ω↔6,8kΩ) + re-adjudicación de `l1_killed` aunque `sup`
   no quede vacío. hp018#1 es probable MISS FALSO (la respuesta dice literalmente «RFL de
   6.800 Ω (6k8)») → puede dejar la etapa en 3 antes de diseñar nada. Gate: re-clasificación
   de los 4 hechos bajo guard arreglado, sin re-generar.
**1. Grupo B — `_consumable` CORPUS-AWARE (raíz, no flip de policy)**: el resolver degrada a
   token-familia cuando las variantes resueltas tienen 0 presencia en `pm` del corpus (la
   consulta que el guard ya hace, contra la tabla correcta; cache por catálogo-commit). NO se
   propone volver a ADD (DEC-091b: band-aid) NI tocar el perfil (replace fail-fast es release
   sellada): se hace que replace sea SEGURO con las etiquetas reales — que es exactamente «el
   primer consumo medible del workstream entity-linking» que DEC-100 dejó abierto. Gate:
   probe de pool hp018 (6/10 slots esperados) + famtie control ±0 + hp009 INTACTO (el
   centinela histórico de esta clase) + bvg K=3 de los golds tocados.
**2. Grupo A — dedup a nivel DOCUMENTO en el pool** (cat010: doc gemelo `duplicate_of=NULL`
   come 5/10 slots; el dedup s286 fue chunk-level). Lever NUNCA medido. Gate: probe de
   composición de pool en cat010 + sweep 39 de no-regresión de composición (barato, sin juez).
**3. Grupo A — cuota por FACETA de la query** (cat017: 2 verbos, monopolio del 1º). El eje
   canal está medido (DEC-099/101); el eje FACETA no. Más caro y especulativo → SOLO si 1+2
   no mueven cat017; pre-registrar antes.
**4. cat010 además conecta con etapa 3**: su soporte SÍ se sirve vía `obligation_warning_
   reserve_v1` pero esa lane solo sirve el span de advertencia → vecino de
   `append_view_truncated`. Si 2 no lo cura, el lever alternativo es EXCERPT de lane, no orden.

## GATES/GUARDARRAÍLES COMUNES
DEC-096b: el LLM-rerank NO es determinista → todo A/B con control OFF-vs-OFF o N-reps.
Los 93 OK protegidos del full v3 = regresión-cero obligatoria antes de declarar nada.
Sellos C1 (DEC-147): tocar retriever/resolver exige re-anclar recibos — inventariar ANTES.

## ALTERNATIVAS DESCARTADAS
- Volver a `IDENTITY_RESOLVE_POLICY=add`: band-aid medido (DEC-091b) + rompe el fail-fast del
  perfil sellado. La versión corpus-aware da lo mismo sin el riesgo de valor-coincidente.
- Afinar reranker / ancho / demote-TOC / tie-break: SETTLED (DEC-092/092b/096/s101) — y este
  diagnóstico lo CONFIRMA (en Grupo B el reranker elige BIEN dado su pool).
- Re-tag del corpus por variante (split D1): workstream de identidad completo, 4-7 sesiones —
  la degradación-a-familia del resolver da el 90% del valor a coste 1%.

## RIESGOS DECLARADOS
1. La degradación-a-familia puede sobre-filtrar en familias donde el tag fino SÍ existe
   (mixto): la regla debe ser por-token, no global (variante presente → úsala; ausente →
   familia). 2. hp009 es el centinela de TODA esta clase — va en el gate, no en la fe.
3. El dedup-documento puede quitar redundancia útil en docs multi-idioma (el gemelo EN a
   veces es el único con la aguja — cat010 mismo): dedup por CONTENIDO (extraction_sha o
   sim>umbral), no por nombre. 4. cat017 puede no moverse con 1+2 (su clase es facet) — se
   declara de entrada, no se persigue con el lever equivocado (anti-overfit).
