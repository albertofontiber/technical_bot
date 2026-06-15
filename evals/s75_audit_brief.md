# s75 — Brief para revisión adversarial: audit de identidad (DEC-054) + recomendación DIFERIR

**Contexto.** s74 cerró el ciclo de levers de retrieval (Lever 1 batch bancado, lift modesto).
El "Qué sigue §1" del PLAN apuntaba al **detector de identidad LLM-en-ingesta + backfill
`product_model`** (la raíz de datos, DEC-054 / TECH_DEBT #49) como siguiente bloque, justificado
como "eval-medible: cat013/hp009/hp018 (~3 golds)" + prep de escala 30+. Alberto eligió
**audit-first**: medir antes de decidir build/defer/pivote. Este brief es el resultado del audit
+ mi recomendación. **Atácalo.**

## Lo que hizo el audit (read-only, `scripts/s75_identity_audit.py` → `evals/s75_identity_audit.yaml`)

**Parte 1 — escala del problema de datos en chunks_v2 (1170 docs / 25090 chunks):**
- **1A pm-compuesto** (etiqueta multi-modelo literal `AM2020/AFP1010`, `ID50/60`): 78 docs / 2371 chunks / 6 fabricantes (Notifier 67).
- **1B mis-atribución** (filename nombra un modelo del catálogo ausente del `product_model` — firma cat013 SDX-751→LOCAL-360): proxy crudo dio **368 docs** pero estaba CONTAMINADO (el regex genérico parsea códigos de manual `MNDT-430` como modelos; el catálogo `data/model_catalog.json` MISMO los heredó como pseudo-modelos = la circularidad que DEC-054 predijo). Tras (i) usar el extractor de catálogo y (ii) filtrar doc-codes `^[mt][a-z]{0,2}dt\d` → **piso ≈ 114 docs / 1218 chunks** (Morley 54, Notifier 25, Detnov 15), gran parte con `pm='unknown'`.
- **1C metadata-inconsistency** (mismo core normalizado, ≥2 labels): 18 clusters (`NFS Supra`/`NFS-SUPRA`, `ID200`/`ID-200`, `SMART 3`/`SMART-3`/`SMART3`).

**Parte 2 — palanca eval del detector (clasificación per-gold de los 18 NO-PASS de retrieval, fuente `evals/s71_track2_retrieval_diag.yaml` + correcciones verificadas):**
- Lever 1 (inanición del pool): 9 — cat016, hp013, hp008, hp002, cat001, cat007, hp001, hp011, cat017.
- config-seam identidad (e-series en `config/manufacturers/morley.yaml`, Brazo A YA construido — NO el detector): 2 — hp009, hp018.
- **detector mis-atribución (la raíz de datos): 1 — cat013, y Lever-1-gated** (sus chunks SDX-751 no entran al pool; pm-rescue NO-OP hasta Lever 1, verify s72/DEC-052/053).
- otros (keyword/rerank/gen/corpus/diversify): 5.

## CLAIMS que afirmo (atácalos uno a uno, con código/artefacto)

1. **El detector de datos tiene ≈0 palanca eval neta.** Solo cat013 lo necesita, y está bloqueado en Lever 1; hp009/hp018 son config (no el detector). → confirma DEC-054 ("~0 de los retrieval-miss; ortogonal a la inanición del pool") y corrige el §1 del PLAN como inflado.
2. **La clasificación per-gold es correcta.** Verifica: ¿hp009/hp018 son de verdad config-fixable y NO dependen del detector? ¿cat013 está de verdad Lever-1-gated (no resoluble solo por el filtro)? ¿algún gold que mal-clasifiqué y SÍ sería detector-net? ¿algún NO-PASS con `pm='unknown'` que el detector arreglaría y no está en el track2?
3. **El sizing 1B (368→114) es defendible como PISO.** ¿El filtro doc-code `^[mt][a-z]{0,2}dt\d` sobre/infra-excluye? ¿114 sigue contaminado (ej. `GUIDE-0044-047`, `55310011` en los ejemplos)? ¿la circularidad catálogo-índice invalida la cifra?
4. **Recomendación: DIFERIR el build** a su gatillo real (ingesta-30+), NO construirlo ahora como lever (no lo es). Es BP + estructural + escalable: gate/audit-primero funcionando, no se construye aparato de 0 palanca antes del gatillo (anti bias #38/#40). Alternativas: (b) build-ahora como prep-de-escala pura; (c) productizar solo el flag-tool (detector proactivo capa-2, sin backfill).

## Lo que quiero del revisor
- ¿Hay un fallo en la clasificación de Parte 2 que cambie el "≈0"? (el claim decisivo)
- ¿La recomendación DIFERIR es la BP, o hay un caso fuerte para build/flag-tool que no vi?
- ¿Sobre-afirmo algo (infra/alcance) como ya-validado sin sustento? (bias #38/#39/#40)
- ¿El audit tiene un sesgo de selección o un agujero metodológico que invalide alguna cifra?
