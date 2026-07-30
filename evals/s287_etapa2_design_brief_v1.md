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

# ══════════ v2 (SPEC CONSOLIDADO post-dúo r1: Sol 6 + sub-agente 11, convergencia) ══════════

## RÉPLICA N=2 (hallazgo entre-medias: Alberto relanzó el full → 2 runs, mismo código)
r1 (0729): OK 101·synth 13·rerank 4·retr 10 / r2 (0730): OK 98·synth 15·rerank 6·retr 8.
15 flips = suelo de ruido del instrumento (estocástica de generación + churn de composición;
incl. hp014#2 OK→corpus-gap = 10ª instancia FN). **Los 4 objetivos de etapa 2 son ESTABLES
4/4 en ambos runs** → dianas estructurales. CONSECUENCIAS NORMATIVAS: (a) la campaña cuenta
misses ESTABLES-entre-runs, no fotos single-run; (b) cohorte protegida del gate = **93
OK-estables-N2** (DERIVADA: 101 menos 8 flippy — responde Sol-1 con datos); (c) el delta de
cualquier lever se declara sobre estables.

## PIEZAS (orden final; cada una con su gate)
**0. Instrumento S5**: puente prefijo-kilo con canonicalización DENTRO de `_unit_quantities`
   (F9: si no, `quantities_complete` queda vacuo) + re-adjudicación de `l1_killed` con sup≠∅ +
   bump `INSTRUMENT_VERSION` v3.0→v3.1 + estampa (norma F4/DEC-096) + re-baseline declarado.
**0.5 HOTFIX $0 (F11, NUEVA)**: `config/identity_quarantine_v1.yaml` → `tokens: [zxe]` —
   suprime el drop DENTRO del diseño sellado (semántica «fail-open-a-add por unidad; nunca
   peor que add», consumida en catalog_resolver.py:310-313). Es TAMBIÉN el probe más barato de
   la predicción 6/10 (pool de hp018 antes/después, $0). Estiramiento semántico declarado
   (la quarantine nació «pendiente de adjudicación») → nota para Alberto, reversible una línea.
**1. `_consumable` corpus-aware — REGLA MONÓTONA-SEGURA (F4, BLOCKER resuelto)**: NUNCA
   dropear un token cuyo PROPIO core tenga presencia en `pm` (presencia del tag-FAMILIA, no
   ausencia de variantes) → estado mixto post-split-D1 seguro; coexistencia → conservar.
   Declaraciones honestas: (i) es CRITERIO NUEVO con dependencia DB nueva en módulo file-only
   (F1/Sol-3) — fail-open a conservar-token en error DB; (ii) cache por FINGERPRINT DE CORPUS
   o TTL, jamás catálogo-commit (F6/Sol-2); (iii) CONFINA el comportamiento-ADD a las familias
   sin tags finos — el riesgo DEC-091b (valor-coincidente, `zxe`⊂`zxee`) PERSISTE ahí y se
   declara, no se niega (F2/Sol-4) + control negativo catalog-wide de familias con valores
   divergentes ANTES del ship; (iv) F3: esto repara una REGRESIÓN DE CORRECCIÓN VIVA
   corpus-wide (toda query con token-paraguas re-tagueado en T3), no solo hp018 — nota de
   release para Alberto. GATE AMPLIADO (F5): sweep-39 de composición de pool (determinista,
   sin juez) + centinelas hp009/hp012/cat022/cat012/hp001 + famtie ±0 + bvg K=3 tocados.
**2. Dedup — RAÍZ corpus-side (F7/Sol-6)**: adjudicación near-dup (shingle/Jaccard, maquinaria
   del audit s62) → `duplicate_of` vía census→staging→PASTE DE ALBERTO, con política de
   representante language/revision-aware (el gemelo EN se protege por adjudicación, no por
   umbral — cat010 mismo: la aguja está en el EN). El dedup-en-pool queda como DEFENSA
   fallback y respeta las marcas de carve-out `_hyq_boosted`/`_enun_quota`/`_swapped_*`
   (F8/DEC-099 §1.1c). Sol-6: primero materializar la relación canónica; hecho.
**3. Cuota-faceta**: sin cambios (condicionada + pre-registro).

## CORRECCIONES DE FRAMING (para el registro)
- Sol-5: retirada mi frase «el soporte de cat010 se sirve vía obligation_warning_reserve» —
  el artefacto dice n_support_served=0; la conexión con etapa 3 queda como hipótesis no medida.
- F1: «la consulta que el guard ya hace» era falso-adyacente; F10: los sellos NO byte-pinean
  retriever/resolver — el coste real es la serie nueva del pipe_sha del assessment (declarada).
- «93 OK protegidos» de v1 era eco stale; ahora es la cohorte DERIVADA estable-N2 (§réplica).

## PLAN v2
1. ~~Dúo r1~~ HECHO (Sol 6 + Fable 11, tally). 2. Confirmación FRESCA focused (F4-regla +
F11-semántica + este consolidado). 3. Build por piezas CON SUS GATES en orden 0→0.5→1→2;
la 0.5 da el probe de la predicción antes de construir la 1. 4. Re-medición estable (2 runs o
K-reps de los golds tocados). 5. Tally/scoreboard/DEC + nota release + paquete Alberto.
