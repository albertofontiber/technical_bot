# s278 — Census catalog-wide de identidad (add vs replace) — OFFLINE

Worktree: `C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot-s277` (READ-ONLY) · catalog_commit: `4883aed` · 845 unidades · 1707 queries de sondeo · 6.2s · 0 red (guard socket activo, 0 intentos bloqueados)

## 1. Conteos por clase

| Clase | Unidades |
|---|---:|
| REPLACE_EMPTIES | 0 |
| REPLACE_DROPS_DOC | 0 |
| ADD_BROADENS | 7 |
| REPLACE_NARROWS | 40 |
| SAME | 740 |
| NO_DETECTION | 58 |

Por tipo de unidad:

| kind | REPLACE_EMPTIES | REPLACE_DROPS_DOC | ADD_BROADENS | REPLACE_NARROWS | SAME | NO_DETECTION |
|---|---:|---:|---:|---:|---:|---:|
| alias | 0 | 0 | 1 | 36 | 682 | 57 |
| homonym | 0 | 0 | 1 | 0 | 8 | 0 |
| product_member | 0 | 0 | 0 | 0 | 43 | 0 |
| umbrella | 0 | 0 | 5 | 4 | 7 | 1 |

## 2. REPLACE_EMPTIES — 0 unidades (lista COMPLETA)

(ninguna)

## 3. REPLACE_DROPS_DOC (docs de familia perdidos) — 0 unidades (lista COMPLETA)

(ninguna)

## 4. ADD_BROADENS (la clase del bug hp018) — 7 unidades (lista COMPLETA)

### `umbrella:ZXe`
- ref catalogo: `{"tipo": "familia", "divergent": true, "candidate": false, "ids": ["morley:zx1e", "morley:zx2e", "morley:zx5e"]}`
- flags: docs_solo_bajo_add:5
- query: `ZXe`
  - models add → replace: `['ZXE', 'ZX1e', 'ZX2e', 'ZX5e']` → `['ZX1e', 'ZX2e', 'ZX5e']`
  - docs add/replace (con union seam-2): 12 / 7
  - docs perdidos bajo replace: `['MIE-MI-310', 'MIE-MP-310', 'MIE-MP-315', 'MIE-MU-310', 'MIE-MU-315']`
- query: `manual de ZXe`
  - models add → replace: `['ZXE', 'ZX1e', 'ZX2e', 'ZX5e']` → `['ZX1e', 'ZX2e', 'ZX5e']`
  - docs add/replace (con union seam-2): 12 / 7
  - docs perdidos bajo replace: `['MIE-MI-310', 'MIE-MP-310', 'MIE-MP-315', 'MIE-MU-310', 'MIE-MU-315']`
- query: `averia en la central ZXe`
  - models add → replace: `['ZXE', 'ZX1e', 'ZX2e', 'ZX5e']` → `['ZX1e', 'ZX2e', 'ZX5e']`
  - docs add/replace (con union seam-2): 12 / 7
  - docs perdidos bajo replace: `['MIE-MI-310', 'MIE-MP-310', 'MIE-MP-315', 'MIE-MU-310', 'MIE-MU-315']`

### `umbrella:ZXR`
- ref catalogo: `{"tipo": "rango", "divergent": true, "candidate": false, "ids": ["morley:zxr50a", "morley:zxr50p"]}`
- flags: docs_solo_bajo_add:1
- query: `ZXR`
  - models add → replace: `['ZXR', 'ZXR50A', 'ZXR50P']` → `['ZXR50A', 'ZXR50P']`
  - docs add/replace (con union seam-2): 4 / 3
  - docs perdidos bajo replace: `['MIE-MI-430']`
- query: `manual de ZXR`
  - models add → replace: `['ZXR', 'ZXR50A', 'ZXR50P']` → `['ZXR50A', 'ZXR50P']`
  - docs add/replace (con union seam-2): 4 / 3
  - docs perdidos bajo replace: `['MIE-MI-430']`
- query: `averia en la central ZXR`
  - models add → replace: `['ZXR', 'ZXR50A', 'ZXR50P']` → `['ZXR50A', 'ZXR50P']`
  - docs add/replace (con union seam-2): 4 / 3
  - docs perdidos bajo replace: `['MIE-MI-430']`

### `umbrella:CAD-150`
- ref catalogo: `{"tipo": "familia", "divergent": true, "candidate": false, "ids": ["detnov:cad-150-1", "detnov:cad-150-2", "detnov:cad-150-2-mb", "detnov:cad-150-4", "detnov:cad-150-8", "detnov:cad-150-8-plus"]}`
- flags: docs_solo_bajo_add:1
- query: `CAD-150`
  - models add → replace: `['CAD-150', 'CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']` → `['CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']`
  - docs add/replace (con union seam-2): 3 / 2
  - docs perdidos bajo replace: `['55315501 CAD150R Instalacion ES GB 191018']`
- query: `manual de CAD-150`
  - models add → replace: `['CAD-150', 'CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']` → `['CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']`
  - docs add/replace (con union seam-2): 3 / 2
  - docs perdidos bajo replace: `['55315501 CAD150R Instalacion ES GB 191018']`
- query: `averia en la central CAD-150`
  - models add → replace: `['CAD-150', 'CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']` → `['CAD-150-1', 'CAD-150-2', 'CAD-150-2-MB', 'CAD-150-4', 'CAD-150-8', 'CAD-150-8-PLUS']`
  - docs add/replace (con union seam-2): 3 / 2
  - docs perdidos bajo replace: `['55315501 CAD150R Instalacion ES GB 191018']`

### `umbrella:B500`
- ref catalogo: `{"tipo": "serie", "divergent": true, "candidate": false, "ids": ["systemsensor:b501", "systemsensor:b501dg", "systemsensor:b524htr", "systemsensor:b524ieft-1"]}`
- flags: docs_solo_bajo_add:1
- query: `B500`
  - models add → replace: `['B500', 'B501', 'B501DG', 'B524HTR', 'B524IEFT-1']` → `['B501', 'B501DG', 'B524HTR', 'B524IEFT-1']`
  - docs add/replace (con union seam-2): 16 / 15
  - docs perdidos bajo replace: `['I56-1267-000 SMB500']`
- query: `manual de B500`
  - models add → replace: `['B500', 'B501', 'B501DG', 'B524HTR', 'B524IEFT-1']` → `['B501', 'B501DG', 'B524HTR', 'B524IEFT-1']`
  - docs add/replace (con union seam-2): 16 / 15
  - docs perdidos bajo replace: `['I56-1267-000 SMB500']`
- query: `averia en la central B500`
  - models add → replace: `['B500', 'B501', 'B501DG', 'B524HTR', 'B524IEFT-1']` → `['B501', 'B501DG', 'B524HTR', 'B524IEFT-1']`
  - docs add/replace (con union seam-2): 16 / 15
  - docs perdidos bajo replace: `['I56-1267-000 SMB500']`

### `umbrella:FAAST`
- ref catalogo: `{"tipo": "familia", "divergent": true, "candidate": false, "ids": ["notifier:fl0111e-hs", "notifier:fl0112e-hs", "notifier:fl0122e-hs", "notifier:fl2011ei-hs", "notifier:fl2012ei-hs", "notifier:fl2022ei-hs", "notifier:nfxi-asd11-hs", "notifier:nfxi-asd12-hs", "notifier:nfxi-asd22-hs", "morley:mi-fl2011ei", "morley:mi-fl2012ei", "morley:mi-fl2022ei", "notifier:faast-8100e"]}`
- flags: docs_solo_bajo_add:3
- query: `FAAST`
  - models add → replace: `['FAAST', 'FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']` → `['FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']`
  - docs add/replace (con union seam-2): 14 / 11
  - docs perdidos bajo replace: `['FAAST Area Coverage Planner_SP', 'FAAST Understanding EN54-20_SP', 'I56-3836-006_FAAST_XM_8100E_ML']`
- query: `manual de FAAST`
  - models add → replace: `['FAAST', 'FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']` → `['FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']`
  - docs add/replace (con union seam-2): 14 / 11
  - docs perdidos bajo replace: `['FAAST Area Coverage Planner_SP', 'FAAST Understanding EN54-20_SP', 'I56-3836-006_FAAST_XM_8100E_ML']`
- query: `averia en la central FAAST`
  - models add → replace: `['FAAST', 'FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']` → `['FL0111E-HS', 'FL0112E-HS', 'FL0122E-HS', 'FL2011EI-HS', 'FL2012EI-HS', 'FL2022EI-HS', 'NFXI-ASD11-HS', 'NFXI-ASD12-HS', 'NFXI-ASD22-HS', 'MI-FL2011EI', 'MI-FL2012EI', 'MI-FL2022EI']`
  - docs add/replace (con union seam-2): 14 / 11
  - docs perdidos bajo replace: `['FAAST Area Coverage Planner_SP', 'FAAST Understanding EN54-20_SP', 'I56-3836-006_FAAST_XM_8100E_ML']`

### `homonym:RP1r`
- ref catalogo: `{"politica": "prefer:notifier:rp1r-supra", "candidate": false, "ids": ["notifier:rp1r-supra", "notifier:rp1r", "morley:vsn-rp1r", "notifier:opc-rp1r"]}`
- flags: docs_solo_bajo_add:12
- query: `RP1r`
  - models add → replace: `['RP1r', 'RP1r-Supra']` → `['RP1r-Supra']`
  - docs add/replace (con union seam-2): 28 / 16
  - docs perdidos bajo replace: `['HLSI-BT-001', 'HLSI-TI-001I', 'MIEMN570', 'MIEMN570I', 'MN-DT-102I', 'MN-DT-959_OPC-RP1r', 'MNDT102', 'MNDT102I_D FR', 'MNDT102I_D FR VSN-RP1r_hlsi', 'MNDT102P', 'RP1R - MAN ITA r.A2', 'Tg-Honeywell_Tecnico']`
- query: `manual de RP1r`
  - models add → replace: `['RP1r', 'RP1r-Supra']` → `['RP1r-Supra']`
  - docs add/replace (con union seam-2): 28 / 16
  - docs perdidos bajo replace: `['HLSI-BT-001', 'HLSI-TI-001I', 'MIEMN570', 'MIEMN570I', 'MN-DT-102I', 'MN-DT-959_OPC-RP1r', 'MNDT102', 'MNDT102I_D FR', 'MNDT102I_D FR VSN-RP1r_hlsi', 'MNDT102P', 'RP1R - MAN ITA r.A2', 'Tg-Honeywell_Tecnico']`

### `alias:G-100-R`
- ref catalogo: `{"tipo": "nombre-largo", "id": "notifier:g-100-r-12", "target": "notifier:g-100-r-12"}`
- flags: docs_solo_bajo_add:2
- query: `G-100-R`
  - models add → replace: `['G-100-R', 'G-100-R-12']` → `['G-100-R-12']`
  - docs add/replace (con union seam-2): 3 / 1
  - docs perdidos bajo replace: `['MNDT500', 'MNDT503']`
- query: `manual de G-100-R`
  - models add → replace: `['G-100-R', 'G-100-R-12']` → `['G-100-R-12']`
  - docs add/replace (con union seam-2): 3 / 1
  - docs perdidos bajo replace: `['MNDT500', 'MNDT503']`

## 5. Controles obligatorios

### hp018 — **PASS**
```json
{
 "verdict": "PASS",
 "synthetic_pinned_test_replica": true,
 "probes": [
  {
   "query": "conectar una sirena convencional en Morley ZXe",
   "replace_excluye_legacy_310": true,
   "replace_conserva_530_combinados": true,
   "add_arrastra_legacy (clase del bug)": true,
   "docs_replace_familia": [
    "MIE-MI-530rv001",
    "MIE-MP-530rv001",
    "MIE-MP-535rv001",
    "MIE-MU-530rv001",
    "MIE-MU-535rv001",
    "No-puedo-conectarme-con-el-ordenador-a-la-central-ZX",
    "Tg-Honeywell_Tecnico"
   ],
   "docs_add_familia": [
    "MIE-MI-310",
    "MIE-MI-530rv001",
    "MIE-MP-310",
    "MIE-MP-315",
    "MIE-MP-530rv001",
    "MIE-MP-535rv001",
    "MIE-MU-310",
    "MIE-MU-315",
    "MIE-MU-530rv001",
    "MIE-MU-535rv001",
    "No-puedo-conectarme-con-el-ordenador-a-la-central-ZX",
    "Tg-Honeywell_Tecnico"
   ],
   "census_class": "ADD_BROADENS"
  },
  {
   "query": "manual de la central ZX2e/ZX5e",
   "replace_excluye_legacy_310": true,
   "replace_conserva_530_combinados": true,
   "add_arrastra_legacy (clase del bug)": false,
   "docs_replace_familia": [
    "MIE-MI-530rv001",
    "MIE-MP-530rv001",
    "MIE-MP-535rv001",
    "MIE-MU-530rv001",
    "MIE-MU-535rv001",
    "No-puedo-conectarme-con-el-ordenador-a-la-central-ZX",
    "Tg-Honeywell_Tecnico"
   ],
   "docs_add_familia": [
    "MIE-MI-530rv001",
    "MIE-MP-530rv001",
    "MIE-MP-535rv001",
    "MIE-MU-530rv001",
    "MIE-MU-535rv001",
    "No-puedo-conectarme-con-el-ordenador-a-la-central-ZX",
    "Tg-Honeywell_Tecnico"
   ],
   "census_class": "SAME"
  }
 ]
}
```
### hp009 — **PASS**
```json
{
 "verdict": "PASS",
 "models_replace": [
  "ZX1e",
  "ZX2e",
  "ZX5e"
 ],
 "docs_replace_n": 7,
 "no_se_vacia_bajo_replace": true,
 "family_level_chunks_sobreviven_add": true,
 "family_level_chunks_sobreviven_replace": true
}
```
### cat017_inspire — **DOCUMENTED_UNGOVERNED**
```json
{
 "verdict": "DOCUMENTED_UNGOVERNED",
 "nota": "detect()==[] en todas las formas => el catalogo gobernado NO resuelve INSPIRE/E10/E15 (handoff §8.2: 7 identidades candidate sin gobernar). El seed MODEL_PATTERN del retriever si detecta formas 'INSPIRE E10' (retriever.py:56) — la deteccion legacy existe pero SIN resolucion/doc_map gobernados."
}
```
Sondeos (detect gobernado vs seed legacy):

| query | detect() | seed extract |
|---|---|---|
| `INSPIRE` | `[]` | `['INSPIRE']` |
| `E10` | `[]` | `[]` |
| `E15` | `[]` | `[]` |
| `INSPIRE E10` | `[]` | `['INSPIRE E10']` |
| `INSPIRE E15` | `[]` | `['INSPIRE', 'INSPIRE E15']` |
| `Notifier INSPIRE E10` | `[]` | `['INSPIRE E10']` |
| `Notifier INSPIRE E15` | `[]` | `['INSPIRE', 'INSPIRE E15']` |
| `manual de INSPIRE E10` | `[]` | `['INSPIRE E10']` |
| `Como genero el fichero de licencia .bin en CLSS para una cen` | `[]` | `['INSPIRE E10']` |

### Aislamiento por proceso — PASS
Los controles se re-ejecutaron en subprocesos con `IDENTITY_RESOLVE_POLICY` fijada en el env del proceso completo; resultados identicos al toggling in-process (`apply_to_models` lee el env en cada llamada, catalog_resolver.py:289; `detect()` no consulta la policy y se verifico 2x por query con assert de igualdad).

## 6. Fuera de census (sin truncado silencioso)

| Grupo | Motivo | N |
|---|---|---:|
| aliases | destino no consumible (candidate/retirado) | 617 |
| aliases | nombre-largo sin digito (excluido del detector) | 319 |
| aliases | normkey digit-only (pre-exclusion del detector) | 29 |
| products | activos no-candidate sin umbrella (exact-only ⇒ replace==add por construccion, catalog_resolver.py:260-263) | 897 |
| miembros de umbrella | no consumibles (candidate/retirado) — no probeables | 4 |
| otros | relations.jsonl (42 filas) y docrel.jsonl (9): relacionales, no resolubles por query — sin unidad de census | — |
| otros | doc_map.jsonl: consumido como sustrato de alcanzabilidad, no unidad | — |
| otros | products activos no-candidate sin umbrella: 897 — exact-only, replace==add por construccion (drop_tokens solo en paraguas/alias/homonimo, catalog_resolver.py:260-263) | — |

Miembros no consumibles: `morley:dx1e` (activo, candidate), `morley:dx2e` (activo, candidate), `morley:dx4e` (activo, candidate), `notifier:faast-8100e` (activo, candidate)

## 7. Honestidad del instrumento — lo que este census NO juzga

- **Wrong-family SEMANTICO** mas alla de los drop_tokens estructurales: el census compara conjuntos de documentos via doc_map; decidir si un doc extra es contenido incorrecto para la pregunta requiere lectura humana/duo. Aqui solo se marca la clase estructural.
- **Nondeterminismo del `LIMIT` de content_search**: requiere DB (plan fisico de Postgres); prohibido en este census offline. Queda pendiente del candidate-context gate (handoff §8.1).
- **Alcanzabilidad = proxy catalogo-side**: pseudo-entradas de doc_map (canonical_model de cada entry tras redirects) con la regla nivel-1 REAL (substring sobre `series_registry.normalize_model`, retriever.py:2024-2028) + union protectora seam-2 (retriever.py:1993-1998). NO son los tags `product_model` reales de la DB (combinados tipo 'ZX2e/ZX5e' o 'unknown' difieren; la union seam-2 es exactamente lo que protege esa clase).
- **No emulado por ser pool-dependiente**: fail-open `<3` (retriever.py:2067-2069), nivel-2 series (vetos de hermanos), brazos rescue (flags OFF), vector search, reranker. Las unidades donde el nivel-2 aplicaria van marcadas `series_registry_applicable`.
  - unidades con series-registry aplicable: 10
- **La conducta answer/clarify NO se toca**: expand=False (clarify/unknown/candidate) es no-op de policy por contrato (drop solo bajo expand=True) — esas unidades son SAME aqui, no evidencia de que clarify sea correcto para la pregunta.
- El census usa la ruta harness offline (`resolve_query`/`apply_to_models`); `resolve_for_retrieval` (shadow-log a Supabase) NO se llama nunca.

## 8. Adjudicación cualitativa de las 7 ADD_BROADENS (verificada contra el catálogo, fila a fila)

El census marca la clase ESTRUCTURAL; esta tabla añade la lectura contra products/doc_map (qué producto posee cada doc perdido bajo replace). "Drop BUENO" = el doc es de un producto DISTINTO (la clase del bug hp018, replace lo arregla); "ADJUDICAR" = el drop pierde cobertura posiblemente legítima.

| Unidad | Docs solo-bajo-add | Dueño real del doc (doc_map) | Lectura |
|---|---|---|---|
| `umbrella:ZXe` | MIE-MI/MP/MU-310/315 (5) | `morley:zxae`/`morley:zxee` (familia legacy distinta) | **Drop BUENO** — es exactamente hp018; pineado en `tests/test_catalog_resolver.py:123-139` |
| `umbrella:CAD-150` | 55315501 CAD150R Instalacion (1) | `detnov:cad-150r` (producto DISTINTO, repetidor — gt `memory/reference_detnov_cad150.md`) | **Drop BUENO** — substring `cad150` ⊂ `cad150r` |
| `umbrella:B500` | I56-1267-000 SMB500 (1) | `systemsensor:smb500` (producto distinto; `b500` ⊂ `smb500`) | **Drop BUENO** |
| `homonym:RP1r` | 12 docs (HLSI-*, MIEMN570*, MNDT102*, MN-DT-959, RP1R MAN ITA, Tg-Honeywell) | `notifier:rp1r`, `morley:vsn-rp1r`, `notifier:opc-rp1r` (los otros 3 homónimos) | **Drop INTENCIONAL** — política `prefer:notifier:rp1r-supra` ya adjudicada (DEC-074b/hp011); add arrastra los 4 productos |
| `umbrella:ZXR` | MIE-MI-430 (1) | `morley:zxr4b`/`morley:zxr5b` — productos ZXr que NO son miembros de la umbrella `ZXR` (solo tiene zxr50a/zxr50p) | **ADJUDICAR** — ¿membership gap de la umbrella (P6 s90 solo adjudicó 50A/50P) o familia distinta? Si ZXR4B/5B son de la familia, replace pierde ese doc |
| `umbrella:FAAST` | FAAST Area Coverage Planner_SP, FAAST Understanding EN54-20_SP, I56-3836-006_FAAST_XM_8100E_ML (3) | `notifier:faast-8100e` (**miembro DECLARADO de la umbrella pero `candidate:true`** → la expansión lo filtra, `catalog_store.py:159`) y `systemsensor:8100e-faast` | **ADJUDICAR — el hallazgo top del census**: bajo replace, los docs de un miembro candidate son INALCANZABLES por la vía de identidad (ni expansión ni allowed_sources); bajo add los alcanzaba el token paraguas por substring. Un `replace` global convierte cada miembro-candidate en un agujero de cobertura silencioso |
| `alias:G-100-R` | MNDT500, MNDT503 (2) | `notifier:g-100-r16` (+familia G-100/G-500; `g100r` ⊂ `g100r16`) — el alias apunta SOLO a `notifier:g-100-r-12` | **ADJUDICAR** — ¿'G-100-R' es alias de g-100-r-12 o paraguas de {g-100-r-12, g-100-r16}? Si es paraguas, replace over-estrecha (3 docs → 1) |

Implicación directa para la decisión del handoff (§8.1 «replace global sólo si pasa; si no, versionar por clase/registro»): **el brazo replace NO vacía nada y no pierde docs de familia consumible (0 REPLACE_EMPTIES / 0 REPLACE_DROPS_DOC), pero hay 3 filas ADJUDICAR antes de un replace GLOBAL** (ZXR membership, FAAST candidate-member, G-100-R alias-vs-paraguas). Las 3 son de gobernanza de DATOS del catálogo (filas jsonl), no de código: adjudicarlas y re-correr este census es barato y offline.

## 9. Los 58 NO_DETECTION explicados (gobernados pero indetectables)

- `umbrella:Dimension` — su término está en `DETECT_STOPWORDS` (`catalog_resolver.py:96`; colisión con la palabra 'dimensión' de prosa, s92). La umbrella hermana `serie Dimension` y el alias-familia `DXc` sí detectan: la familia no queda huérfana, pero la superficie `Dimension` a secas nunca resuelve (a propósito).
- 57 aliases — su superficie contiene puntuación FUERA de la clase separadora del regex del detector (`_SEP = [-\s/.+]*`, `src/rag/catalog.py:57`): `(` `)` `,` `:` `_` `°` `–` (en-dash) `−` (U+2212). El regex generado no puede matchear su PROPIA forma superficial en texto libre (ej.: `NFX(I)-SMT2`, `Ref.: 002-467`, `iBox_BACNET_SVR_NID3000`, `2010−2-PAK-RMSDK`, `Alarmline II ... 105°C (221°F) Nylon`, `Alimentación, 12 V CC`, `6424(A)`, `solo_a10`). Para add-vs-replace son no-op (nunca se detectan); como hallazgo de instrumento: son formas gobernadas SIN vía de detección — si alguna es una superficie que un técnico teclearía (p. ej. `NFX(I)-SMT2`), falta o normalizar el alias almacenado o ampliar `_SEP`. El test de round-trip existente (`tests/test_catalog_resolver.py:287-299`) solo muestrea canonicals, por eso esta clase no estaba pineada.
- Los 57 están enumerados con su unidad completa en `s278_identity_census_result.json` (`class == "NO_DETECTION"`).

## 10. Nota sobre REPLACE_NARROWS (40)

`models_replace ⊊ models_add` con docs IDÉNTICOS en ambos brazos: el token retirado no aportaba ningún doc via substring que las variantes no aporten ya. Son el caso benigno esperado del drop (p. ej. `umbrella:ZXSe`, `umbrella:DXc`, 36 aliases con variante única). Lista completa en el JSON (`class == "REPLACE_NARROWS"`).
