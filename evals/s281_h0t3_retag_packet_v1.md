# s281 H0-T3 — Packet de re-tag del Tramo 3 (findability `product_model='unknown'`) — v1

Instrumento: `scripts/s281_h0t3_retag_packet.py`. **READ-ONLY (PostgREST GET), SELECT-only, 0 llamadas a modelos, 0 escrituras.** Deriva la etiqueta `product_model` CANDIDATA para cada source_file cuyos chunks están enteramente `unknown`, con su EVIDENCIA (doc-level + s83 + catálogo + contenido) y una CONFIANZA. Toda sentencia SQL es PROPUESTA — jamás aplicada por este script. La adjudicación de producto/granularidad es de Alberto.

## Freeze-contract

- commit HEAD: `68f96a8e07d3f86183cf460fcd40e49f92e37255` (worktree dirty: True)
- corpus fingerprint: chunks_v2=25090 · documents=1171 · sha256 `aa13e792339f7d3eb1715c9e720ead19f7c1d517258419916ddddb264c7ba56d`
- **determinismo 2×: IDÉNTICO ✅** (pass1 `54f23ca7abb4a080` == pass2 `54f23ca7abb4a080`)
- s83 modelos: `evals\s83_document_models_final.jsonl` sha256-LF `a1291a837a7f905c3a7939cd847675a94811a47073fa12143070c0f61b177b19`
- s83 identidad: `evals\s83_document_identity_final.jsonl` sha256-LF `87bc0db79ead4e126a388f425049d5029dda9bc64920a0e8f8dca87b8ce6168a`
- catálogo products: sha256-LF `da14fdb7f6ea5d2b9cec6e798a9761807928eb9f50297ff9482cc69a92783a36` · doc_map `67cb2b66dd2ccf9cd7bc2f84d0b2d06b8eaf84b8db77533aa07fa76cebae5161` · umbrellas `6e16d76f65d2a39362adcfa126e442360590b21eda7edf3452d85ef577b14cbe`
- generado 2026-07-23T21:59:15.620721+00:00

## 1. Titular

**28 source_files** enteramente `product_model='unknown'` (318 chunks) — la clase-D del census H0. El tag `unknown` degrada los canales por-modelo que keyean sobre `chunks_v2.product_model` (`keyword_search` imatch + model-scoping/rerank del `answer_planner`); el re-tag los alinea. Distribución de confianza:

- **1 de confianza ALTA** → UPDATE ejecutable tal cual (§3).
- **22 de confianza MEDIA** → [ADJUDICAR] (§4, candidato + opciones).
- **5 de confianza BAJA** → [ADJUDICAR] (§4, conflicto/sin-fuente).

Insight estructural: `documents.product_model` (nivel documento) **nunca es NULL** (census `C_product_model_null_doclevel=0`); para la mayoría de estos 28 la etiqueta correcta YA está en el documento y los chunks simplemente se quedaron atrás en `unknown`. La cohorte ALTA = donde el doc-level está corroborado por s83/catálogo. MIE-MI-600 (ZXSe) se trata aparte (§2): es la migración simétrica ZXe+ZXSe adjudicada, con gate de eval propio.

**Convención de familias (ADJUDICADA por Alberto, s281):** para manuales que cubren varias variantes de una familia, la etiqueta `product_model` correcta es la **FAMILIA-genérica** (`ZXe`, `ZXSe`) — NO el string compuesto ni el split. El compuesto existente `ZX2e/ZX5e` (MIE-*-530) es un caso **A MIGRAR**. Los miembros se resuelven a la familia vía el catálogo gobernado (`data/catalog`). Los candidatos multi-modelo de este packet lideran con la FAMILIA cuando está definida. §2 detalla la migración simétrica ZXe+ZXSe, la verificación de findability (con evidencia del resolver vivo) y el gate de eval.

## 2. Migración simétrica ZXe + ZXSe (familia-genérica) — ADJUDICADA [ALBERTO]

> **Adjudicación de Alberto (s281):** _«la familia de la ZX1e, ZX2e, etc. debería ser la ZXe, al igual que otra familia diferente debería ser la ZXSe»_ — la etiqueta `product_model` correcta es la **FAMILIA-genérica**, NO el string compuesto. El `ZX2e/ZX5e` actual de MIE-*-530 es un caso **A MIGRAR**, no la convención a imitar. Regla general del packet: donde haya familia definida en catálogo/s83, la etiqueta candidata es la FAMILIA (miembros resueltos vía catálogo).

### 2.1 Alcance de la migración (barrido del corpus ZX-familia, verificado en DB)

| familia | source_file | chunks | valor actual | → familia |
|---|---|---:|---|---|
| **ZXSe** | `MIE-MI-600` | 88 | `unknown` | `ZXSe` |
| **ZXe** | `MIE-MI-530rv001` | 64 | `ZX2e/ZX5e` | `ZXe` |
| **ZXe** | `MIE-MP-530rv001` | 96 | `ZX2e/ZX5e` | `ZXe` |
| **ZXe** | `MIE-MU-530rv001` | 38 | `ZX2e/ZX5e` | `ZXe` |
| **ZXe** | `MIE-MP-535rv001` | 9 | `ZX2e y ZX5e` | `ZXe` |

ZXSe = 88 chunks (1 doc, era `unknown`); ZXe = 207 chunks (4 docs, eran compuesto — incluye `MIE-MP-535rv001` con separador ` y ` en vez de `/`). **Relacionados a adjudicar** (no migran automáticamente): `No-puedo-conectarme-...-central-ZX` (1 chunk `unknown`, MIXTO ZXe+ZXSe — s83 lista ZX2e/ZX5e **y** ZX2Se/ZX5Se → Alberto: ¿'ZXe', 'ZXSe' o ambas?) y `MIE-MC-530`/`MK-ZX` (accesorio de montaje de la serie ZXe — ¿migra a 'ZXe' o queda como kit?). Otras familias ZX (ZX50, ZXCE, ZXHE, ZXAE/ZXEE, ZXR50A/ZXR50P) siguen la MISMA regla general pero quedan fuera de esta migración ZXe/ZXSe (algunas sin umbrella definido — trabajo de catálogo aparte).

### 2.2 El catálogo gobernado YA define ambas familias (no falta pieza de familia)

`data/catalog` (trabajo s78/s79/s90) ya contiene ambas familias con miembros — evidencia:

- `umbrellas.jsonl`: `ZXe` (tipo familia) = {zx1e, zx2e, zx5e}; `ZXSe` (tipo familia) = {zx1se, zx2se, zx5se, zx10se}.
- `products.jsonl`: los miembros llevan `familia:"ZXe"` / `familia:"ZXSe"`.
- Homónimo `ZX` → política `clarify`; existe además un `rango` `ZX2e/ZX5e`={zx2e,zx5e}.

→ **No hay pieza de catálogo que falte para ZXe/ZXSe.** (Si Alberto quisiera el token de familia también en el catálogo del DETECTOR de keyword — ver §2.4 — eso sí sería una propuesta aparte.)

### 2.3 Verificación de findability (miembro/familia × canal) — EVIDENCIA en vivo

Findability por-modelo tiene DOS canales. Medido en la config de release (`IDENTITY_RESOLVE=on`, `POLICY=replace`):

**Canal A — `catalog_resolver.allowed_sources` (catálogo gobernado + `doc_map`; INDEPENDIENTE del tag de chunk).** El resolver YA rutea, por miembro Y por familia, a los docs correctos:

| query | detect | vía | allowed_sources ∩ ZX-docs |
|---|---|---|---|
| `ZXSe` (familia) | ✓ | paraguas→4 miembros | **MIE-MI-600** |
| `ZX5Se` (miembro) | ✓ | exact | **MIE-MI-600** |
| `ZX1Se`/`ZX2Se`/`ZX10Se` | ✓ | exact | **MIE-MI-600** |
| `ZXe` (familia) | ✓ | paraguas→3 miembros | **MIE-MI-530rv001/MP/MU** |
| `ZX2e`/`ZX5e` (miembro) | ✓ | exact | **MIE-MI-530rv001/MP/MU** |

→ **El doc NO es invisible al resolver**: miembro y familia ya lo alcanzan por `allowed_sources`, con el tag de chunk en `unknown` o compuesto. Esto es INDEPENDIENTE de la decisión de etiqueta.

**Canal B — `keyword_search` imatch sobre `chunks_v2.product_model` + model-scoping del `answer_planner` (SÍ dependen del tag).** Con etiqueta FAMILIA-genérica (medido):

- Query de FAMILIA (`ZXe`→`ZXE`, `ZXSe`→`ZXSE`): el imatch `\yZXe(?!\d)` **casa** el tag `ZXe`; `\yZXSe` casa `ZXSe`. ✅ La familia-genérica es matchable por el token de familia.
- Query de MIEMBRO (`ZX2e`, `ZX5Se`): el imatch `\yZX2e` **NO** casa el tag `ZXe` (`ZX2e`⊄`ZXe`); y `extract_product_models('ZX5Se')`→`[]` (los miembros ZXSe no están en el catálogo del detector `data/model_catalog.json`). → el miembro NO llega por Canal B; llega por Canal A (allowed_sources) + vector. ⚠
- Interacción con `POLICY=replace`: una query de familia `ZXe` **descarta** el token paraguas y lo reemplaza por los miembros [ZX1e/ZX2e/ZX5e] en la lista de models → al model-scoping le llegan MIEMBROS, que NO casan un tag `ZXe`. Bajo `replace`, el tag familia-genérica es peor para el model-scope de una query-familia que el compuesto (que sí lleva los miembros). Bajo `add` (mantiene el paraguas) la familia-genérica casa. (Canal A rutea igual en ambos.)

**Conclusión honesta:** con la etiqueta FAMILIA adjudicada, el doc queda reachable (Canal A ya lo cubre para miembro y familia). El re-tag paga sobre todo por (1) **quitar `unknown`** — que hoy hace que el chunk parezca sin identidad para el rerank/model-scope — y (2) alinear chunk↔doc-level (`documents.product_model` ya es `ZXe`/`ZXSe`) + catálogo. El matching por-MIEMBRO en Canal B NO lo da la familia-genérica; si Alberto quisiera ese matching, la vía es el catálogo/detector (§2.4), no el tag compuesto (que él descartó).

### 2.4 Companion (fuera del territorio de esta lane) — propuestas, no ediciones

1. **Rebuild del catálogo del detector** `data/model_catalog.json` (`python scripts/build_model_catalog.py`) tras el re-tag: cosecha los `product_model` de los chunks. Nota: `ZXe`/`ZXSe` (sin dígito) podrían NO pasar el gate model-shaped del builder → el token de familia no entraría al detector de keyword; PERO el resolver gobernado (Canal A) ya cubre miembro+familia, así que no es bloqueante. (El compuesto sí se cosechaba — por eso `ZX2e`/`ZX5e` están hoy.)
2. **Si se quiere matching por-MIEMBRO en Canal B para ZXSe**: falta que `data/model_catalog.json` (o el seed del detector) conozca `ZX1Se/ZX2Se/ZX5Se/ZX10Se` — hoy ausentes. PROPUESTA (catálogo versionado, no DB; fuera de esta lane): añadirlos al detector. No es necesario para el ruteo (Canal A), sí para el keyword directo por variante.

### 2.5 GATE DE EVAL (patrón cat022) — OBLIGATORIO antes de dar el tramo por bueno

La migración ZXe toca **golds vivos**: `hp009` (¿resistencia fin de línea de los lazos de la **ZXe**? — veredicto PARCIAL) y `hp018` (¿sirena convencional en la **ZXe**? — PASS) citan `MIE-MI-530rv001`/`MP-530`/`MU-530` (exactamente los docs que migran de `ZX2e/ZX5e`→`ZXe`). Cambiar su `product_model` redistribuye los pools de retrieval/rerank de esos QIDs. **Plan de verificación (antes de aplicar en firme):** `python scripts/test_bot_vs_gold.py` dirigido a `hp009`+`hp018` + un set de control (p.ej. hp006/hp010 no-ZX) para detectar regresión de pool; aceptar solo si hp018 se mantiene PASS y hp009 no empeora. Mismo patrón que cat022 (datos-finos): el re-tag es reversible (§5), así que el gate corre sobre el estado aplicado en una rama/branch de DB y se revierte si regresa.

### 2.6 SQL simétrico (ambas familias, todos los ficheros) — PROPUESTA, reversible (§5)

```sql
-- PROPUESTA (NO aplicada). Migración simétrica ZXe+ZXSe a FAMILIA-genérica (adjudicada).
-- Ejecutar tras el respaldo de §5 y con el gate de eval de §2.5.

-- ZXSe (era 'unknown'):
UPDATE chunks_v2 SET product_model = 'ZXSe'
 WHERE source_file = 'MIE-MI-600' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 88 filas

-- ZXe (migración de compuesto → familia; 4 ficheros, 207 chunks):
UPDATE chunks_v2 SET product_model = 'ZXe'
 WHERE source_file IN ('MIE-MI-530rv001','MIE-MP-530rv001','MIE-MU-530rv001','MIE-MP-535rv001')
   AND product_model IN ('ZX2e/ZX5e','ZX2e y ZX5e')
 RETURNING id;  -- esperado: 207 filas (64+96+38+9)

-- Rollback ZXe (desde la pre-imagen de §5, robusto) — o directo si se quiere:
--   UPDATE chunks_v2 SET product_model='ZX2e/ZX5e' WHERE source_file IN ('MIE-MI-530rv001',
--     'MIE-MP-530rv001','MIE-MU-530rv001') AND product_model='ZXe';
--   UPDATE chunks_v2 SET product_model='ZX2e y ZX5e' WHERE source_file='MIE-MP-535rv001'
--     AND product_model='ZXe';
```

## 3. Confianza ALTA — UPDATE ejecutable tal cual

| source_file | chunks | → product_model | manufacturer | evidencia (resumen) |
|---|---:|---|---|---|
| `NSRE24` | 3 | `NSRE24` | FUEGO | doc-level product_model='NSRE24' (documents table, governed); corroborado por s83/catálogo… |

```sql
-- PROPUESTA (NO aplicada). Bloque de confianza ALTA — ejecutable tras el respaldo de §5.
UPDATE chunks_v2 SET product_model = 'NSRE24'
 WHERE source_file = 'NSRE24' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 3 filas
```

## 4. [ADJUDICAR] — confianza MEDIA/BAJA (candidato + opciones)

26 source_files. Para cada uno: el candidato derivado (mejor apuesta), las opciones, y la evidencia cruda. El UPDATE va parametrizado — sustituye `<PM>` por la etiqueta elegida.

### `FS2-1`  —  confianza **media**  ·  30 chunks

- **Candidato:** `FS2-1`  ·  manufacturer `Notifier`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `FS-1/FS-2/FS-4`
- **Opciones:** FS2-1  (doc-level)  |  FS-1  (s83 primario)  |  FS-2  (s83 primario)  |  FS-4  (s83 primario)
- **doc-level pm:** `FS2-1`  ·  **s83 primarios:** ['FS-1', 'FS-2', 'FS-4']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='FS2-1' (documents table, governed)
- ⚠ doc-level pm='FS2-1' NO coincide con los primarios s83 ['FS-1', 'FS-2', 'FS-4']; posible ruido de filename o modelo real no en s83.
- **Contenido pág 1 []:** 'NOTIFIER ESPAÑA, S.L. Avda Conflent 84, nave 23 Pol. Ind. Pomar de Dalt 08916 Badalona (Barcelona) Tel.: 93 497 39 60; Fax: 93 465 86 35  # CENTRALES DE INCENDIOS CONVENCIONALES DE 1, 2 Y 4 ZONAS  ## '

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=FS2-1>'
 WHERE source_file = 'FS2-1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 30 filas
```

### `ms1-2-4`  —  confianza **baja**  ·  29 chunks

- **Candidato:** `None`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `Central convencional 1 Zona/Central convencional 2 Zonas/Central convencional 4 Zonas/MS1/MS2/MS4`
- **Opciones:** Central convencional 1 Zona  |  Central convencional 2 Zonas  |  Central convencional 4 Zonas  |  MS1  |  MS2  |  MS4
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['Central convencional 1 Zona', 'Central convencional 2 Zonas', 'Central convencional 4 Zonas', 'MS1', 'MS2', 'MS4']  ·  **catálogo familias:** []
- **Evidencia:** modelos candidatos: ['Central convencional 1 Zona', 'Central convencional 2 Zonas', 'Central convencional 4 Zonas', 'MS1', 'MS2', 'MS4']
- ⚠ manual mezcla modelos de familias distintas (o s83/catálogo discrepan) → adjudicación de familia/alcance necesaria.
- **Contenido pág 1 []:** 'Ref. 997-158 Versión 1.0                                                    9 Enero 2002  # CENTRALES DE INCENDIOS CONVENCIONALES DE 1, 2 Y 4 ZONAS  MANUAL DE FUNCIONAMIENTO, INSTALACION Y PUESTA EN M'

```sql
-- sin candidato único — elige de las opciones arriba
UPDATE chunks_v2 SET product_model = '<PM>'
 WHERE source_file = 'ms1-2-4' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 29 filas
```

### `Manual-de-Usuario-S3-T1-y-S-2-T1`  —  confianza **media**  ·  28 chunks

- **Candidato:** `S3-T1`  ·  manufacturer `Fidegas`
- **Opciones:** S3-T1  (primario doc-level)
- **doc-level pm:** `S3-T1`  ·  **s83 primarios:** ['S/2-T1', 'S/3-T1']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='S3-T1' (documents table, governed)
- ⚠ manual MULTI-MODELO (2 modelos s83: ['s2t1', 's3t1']); doc-level nombra solo el primario 'S3-T1'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 []:** '# MANUAL DE USUARIO  ## SENSOR REMOTO  # S/3-T1 y S/2-T1  ## TÓXICOS  [Image shows two gas sensor devices: On the left is a yellow cylindrical sensor unit with the "fidegas" logo in the center. On the'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=S3-T1>'
 WHERE source_file = 'Manual-de-Usuario-S3-T1-y-S-2-T1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 28 filas
```

### `Manual-de-Usuario-S3-T2-y-S2-T2`  —  confianza **media**  ·  24 chunks

- **Candidato:** `S3-T2`  ·  manufacturer `Fidegas`
- **Opciones:** S3-T2  (primario doc-level)
- **doc-level pm:** `S3-T2`  ·  **s83 primarios:** ['00051', '00052', '03382', '03383', 'S/2-T2', 'S/3-T2']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='S3-T2' (documents table, governed)
- ⚠ manual MULTI-MODELO (6 modelos s83: ['00051', '00052', '03382', '03383', 's2t2', 's3t2']); doc-level nombra solo el primario 'S3-T2'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 []:** '# MANUAL DE USUARIO  ## SENSOR REMOTO  # S/3-T2 y S/2-T2  ## OXÍGENO  ## Rango (0-25) ó (21-0) % v/v  [Left side shows a yellow cylindrical sensor device with "fg fidegas" logo on its face. Above it i'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=S3-T2>'
 WHERE source_file = 'Manual-de-Usuario-S3-T2-y-S2-T2' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 24 filas
```

### `I56-2006-004 MI-DMMI_DMM2I_D2ICMO`  —  confianza **media**  ·  17 chunks

- **Candidato:** `MI-DMMI`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `MI-D2ICMO/MI-DMM2I`
- **Opciones:** MI-DMMI  (primario doc-level)  |  MI-D2ICMO/MI-DMM2I  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `MI-DMMI`  ·  **s83 primarios:** ['MI-D2ICMO', 'MI-DMM2I', 'MI-DMMI']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='MI-DMMI' (documents table, governed)
- ⚠ manual MULTI-MODELO (3 modelos s83: ['mid2icmo', 'midmm2i', 'midmmi']); doc-level nombra solo el primario 'MI-DMMI'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 []:** '# MORLEY IAS  ## by Honeywell  # INSTRUCCIONES PARA LA INSTALACIÓN DE LOS MÓDULOS DE ENTRADA MI-DMMI / MI-DMM2I, Y EL MÓDULO DE ENTRADAS / SALIDA MI-D2ICMO  Este manual le sirve preparado para que sir'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=MI-DMMI>'
 WHERE source_file = 'I56-2006-004 MI-DMMI_DMM2I_D2ICMO' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 17 filas
```

### `BANI-G-24_Eng`  —  confianza **media**  ·  16 chunks

- **Candidato:** `IS 28 Mk 4`  ·  manufacturer `Hosiden Besson`
- **Opciones:** IS 28 Mk 4  (doc-level)  |  IS 28 Mk 4 Banshee  (s83 primario)
- **doc-level pm:** `IS 28 Mk 4`  ·  **s83 primarios:** ['IS 28 Mk 4 Banshee']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='IS 28 Mk 4' (documents table, governed)
- ⚠ doc-level pm='IS 28 Mk 4' NO coincide con los primarios s83 ['IS 28 Mk 4 Banshee']; posible ruido de filename o modelo real no en s83.
- **Contenido pág 1 [IS 28 Mk 4 Banshee Audible Warning Device]:** '# IS 28 Mk 4 Banshee Audible Warning Device  **Hosiden Besson Ltd.**  [Product image showing a cylindrical white/grey audible warning device with a black mounting base. The device has a distinctive ho'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=IS 28 Mk 4>'
 WHERE source_file = 'BANI-G-24_Eng' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 16 filas
```

### `LocatorPlus-Installation-Manual-1.3`  —  confianza **media**  ·  16 chunks

- **Candidato:** `Signaline LocatorPlus`  ·  manufacturer `LGM Products`
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['Signaline LocatorPlus']  ·  **catálogo familias:** []
- **Evidencia:** doc-level pm vacío; s83/catálogo → único modelo 'Signaline LocatorPlus'
- **Contenido pág 1 []:** '# SignaLine Heat LocatorPlus  [Product image showing an orange electronic device with a digital display screen at the top, "SignaLine Heat LocatorPlus" branding, "Zone 1" and "Zone 2" labels with five'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=Signaline LocatorPlus>'
 WHERE source_file = 'LocatorPlus-Installation-Manual-1.3' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 16 filas
```

### `I56-3388-002 NFX-OPT_multi`  —  confianza **media**  ·  9 chunks

- **Candidato:** `NFXI-OPT`  ·  manufacturer `Notifier`
- **Opciones:** NFXI-OPT  (primario doc-level)
- **doc-level pm:** `NFXI-OPT`  ·  **s83 primarios:** ['NFX-OPT', 'NFXI-OPT']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NFXI-OPT' (documents table, governed)
- ⚠ manual MULTI-MODELO (2 modelos s83: ['nfxiopt', 'nfxopt']); doc-level nombra solo el primario 'NFXI-OPT'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 []:** 'N200-200-00  # NOTIFIER® by Honeywell  # NFX-OPT / NFXI-OPT  [Dimensional diagram showing sensor: 102 mm width, 51 mm height, model B501AP, temperature range 70°C to -30°C, weight 95 g]  ## ENGLISH  #'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NFXI-OPT>'
 WHERE source_file = 'I56-3388-002 NFX-OPT_multi' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 9 filas
```

### `I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE`  —  confianza **media**  ·  9 chunks

- **Candidato:** `MI-DMMIE`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `MI-D2ICMOE/MI-DMM2IE`
- **Opciones:** MI-DMMIE  (primario doc-level)  |  MI-D2ICMOE/MI-DMM2IE  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `MI-DMMIE`  ·  **s83 primarios:** ['MI-D2ICMOE', 'MI-DMM2IE', 'MI-DMMIE']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='MI-DMMIE' (documents table, governed)
- ⚠ manual MULTI-MODELO (3 modelos s83: ['mid2icmoe', 'midmm2ie', 'midmmie']); doc-level nombra solo el primario 'MI-DMMIE'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 [EN INSTALLATION INSTRUCTIONS - MI-DMMIE / MI-DMM2IE INPUT MODULES, MI-D2ICMOE IN]:** '**Honeywell** MI-DMMIE MI-DMM2IE MI-D2ICMOE |||||||||||||||||||||||| I56-4406-001  ## EN INSTALLATION INSTRUCTIONS - MI-DMMIE / MI-DMM2IE INPUT MODULES, MI-D2ICMOE INPUT /OUTPUT MODULE  This manual is'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=MI-DMMIE>'
 WHERE source_file = 'I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 9 filas
```

### `I56-3389-002 NFX-SMT2_multi`  —  confianza **media**  ·  7 chunks

- **Candidato:** `NFXI-SMT2`  ·  manufacturer `Notifier`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `NFX-SMT2/NFXI-SMT2`
- **Opciones:** NFXI-SMT2  (primario doc-level)  |  NFX-SMT2/NFXI-SMT2  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `NFXI-SMT2`  ·  **s83 primarios:** ['NFX-SMT2', 'NFXI-SMT2']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NFXI-SMT2' (documents table, governed)
- ⚠ manual MULTI-MODELO (2 modelos s83: ['nfxismt2', 'nfxsmt2']); doc-level nombra solo el primario 'NFXI-SMT2'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 [NFX-SMT2 / NFXI-SMT2]:** 'NOTIFIER® by Honeywell  # NFX-SMT2 / NFXI-SMT2  | 102 mm<br/>60 mm<br/>B501AP | 70°C<br/>-30°C | 97 g | SMART2 | 0786-CPD-20645 09 NFX-SMT2<br/>0786-CPD-20639 09 NFXI-SMT2<br/>Pittway Tecnologica S.r.'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NFXI-SMT2>'
 WHERE source_file = 'I56-3389-002 NFX-SMT2_multi' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 7 filas
```

### `Manual_DXD-2X0 (55321002 MI 607 m 2024 c)`  —  confianza **media**  ·  7 chunks

- **Candidato:** `DOD-220`  ·  manufacturer `Detnov`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `DOD-220/DOTD-230/DTD-210/DTD-215`
- **Opciones:** DOD-220  (primario doc-level)  |  DOD-220/DOTD-230/DTD-210/DTD-215  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `DOD-220`  ·  **s83 primarios:** ['DOD-220', 'DOTD-230', 'DTD-210', 'DTD-215']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='DOD-220' (documents table, governed)
- ⚠ manual MULTI-MODELO (4 modelos s83: ['dod220', 'dotd230', 'dtd210', 'dtd215']); doc-level nombra solo el primario 'DOD-220'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 [DETECTORES CONVENCIONALES]:** '# DETECTORES CONVENCIONALES  | DTD-210              | DTD-215              | | -------------------- | -------------------- | | <br/><br/><br/><br/> | <br/><br/><br/><br/> | | DOD-220              | DO'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=DOD-220>'
 WHERE source_file = 'Manual_DXD-2X0 (55321002 MI 607 m 2024 c)' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 7 filas
```

### `I56-5005-002_D Notifier Sounder Strobe`  —  confianza **media**  ·  6 chunks

- **Candidato:** `B501AP`  ·  manufacturer `Notifier`
- **Opciones:** B501AP  (doc-level + catálogo)  |  W*A-*C-I02  (s83 primario — DISCREPA)
- **doc-level pm:** `B501AP`  ·  **s83 primarios:** ['W*A-*C-I02']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='B501AP' (documents table, governed)
- ⚠ CONFLICTO: doc-level+catálogo dicen 'B501AP' pero s83 primario = ['W*A-*C-I02']. Adjudicar cuál documenta el manual.
- **Contenido pág 1 [GENERAL]:** '**(SPA)** El alcance se utiliza en sistemas direccionables analógicos de alarma de incendios. Estos dispositivos solo deben conectarse a paneles de control que utilicen un protocolo de comunicación di'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=B501AP>'
 WHERE source_file = 'I56-5005-002_D Notifier Sounder Strobe' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 6 filas
```

### `MIE-MP-525rv1`  —  confianza **media**  ·  6 chunks

- **Candidato:** `serie Dimension`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `DX1/DX2/DX4`
- **Opciones:** serie Dimension  (FAMILIA — adjudicada)  |  DX1/DX2/DX4  (compuesto — LEGACY, a migrar)
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['DX1', 'DX2', 'DX4']  ·  **catálogo familias:** []  ·  **umbrella:** serie Dimension
- **Evidencia:** doc-level pm vacío; catalog umbrella 'serie Dimension' (familia GT) mapea el documento → etiqueta-FAMILIA (convención adjudicada)
- **Contenido pág 1 []:** '| MORLEY 🔥 IAS<br>FIRE SYSTEMS<br>by Honeywell | GUÍA RÁPIDA DE PROGRAMACIÓN<br>CENTRALES ANALÓGICAS DX1,DX2 y DX4 |  Esta es una guía tutorial que ilustra exclusivamente los pasos generales para prog'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=serie Dimension>'
 WHERE source_file = 'MIE-MP-525rv1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 6 filas
```

### `I56-5004-000-Notifier-Strobe`  —  confianza **media**  ·  5 chunks

- **Candidato:** `Notifier Strobe`  ·  manufacturer `Notifier`
- **doc-level pm:** `Notifier Strobe`  ·  **s83 primarios:** []  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='Notifier Strobe' (documents table, governed); única fuente = doc-level (sin corroboración s83/catálogo)
- **Contenido pág 1 [GENERAL]:** 'Estos dispositivos solo deben conectarse a paneles de control que utilicen un protocolo de comunicación direccionable analógico compatible y propio.  Estos dispositivos reciben su energía del lazo y p'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=Notifier Strobe>'
 WHERE source_file = 'I56-5004-000-Notifier-Strobe' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 5 filas
```

### `HLSI-MA-025 Guia Rapida NFS_Supra_XP_c`  —  confianza **media**  ·  4 chunks

- **Candidato:** `NFS Supra`  ·  manufacturer `Notifier`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `ESS 2Plus/Vision Plus2`
- **Opciones:** NFS Supra  (primario doc-level)  |  ESS 2Plus/Vision Plus2  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `NFS Supra`  ·  **s83 primarios:** ['ESS 2Plus', 'NFS Supra', 'Vision Plus2']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NFS Supra' (documents table, governed)
- ⚠ manual MULTI-MODELO (3 modelos s83: ['ess2plus', 'nfssupra', 'visionplus2']); doc-level nombra solo el primario 'NFS Supra'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 []:** 'NFS Supra / Vision Plus2 / ESS 2Plus     **Honeywell**     NFS Supra / Vision Plus2 / ESS 2Plus     **Honeywell**  ## Quick guide - Assembly  ### 1  [Image shows a mounting plate with numbered compone'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NFS Supra>'
 WHERE source_file = 'HLSI-MA-025 Guia Rapida NFS_Supra_XP_c' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 4 filas
```

### `D700-3-Sp`  —  confianza **media**  ·  3 chunks

- **Candidato:** `D700`  ·  manufacturer `Notifier`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `MCP1A/MCP1B/MCP2A/MCP2B/MCP3A/MCP4A`
- **Opciones:** D700  (doc-level)  |  MCP1A  (s83 primario)  |  MCP1B  (s83 primario)  |  MCP2A  (s83 primario)
- **doc-level pm:** `D700`  ·  **s83 primarios:** ['MCP1A', 'MCP1B', 'MCP2A', 'MCP2B', 'MCP3A', 'MCP4A']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='D700' (documents table, governed)
- ⚠ doc-level pm='D700' NO coincide con los primarios s83 ['MCP1A', 'MCP1B', 'MCP2A']; posible ruido de filename o modelo real no en s83.
- **Contenido pág 1 [KAC INSTRUCCIONES DE INSTALACIÓN DE LOS PULSADORES MANUALES MCP1..., MCP2..., MC]:** '# KAC INSTRUCCIONES DE INSTALACIÓN DE LOS PULSADORES MANUALES MCP1..., MCP2..., MCP3..., MCP4...  ## PARA PROBAR  **1**  [Illustration showing a manual call point device mounted on a wall with a hand '

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=D700>'
 WHERE source_file = 'D700-3-Sp' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 3 filas
```

### `Manual Pulsador convencional IP65 PCD-100WP (1)`  —  confianza **baja**  ·  2 chunks

- **Candidato:** `None`  ·  manufacturer `Detnov`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `Waterproof ReSet 11/Waterproof ReSet Series 01/Waterproof ReSet Series 02`
- **Opciones:** Waterproof ReSet 11  |  Waterproof ReSet Series 01  |  Waterproof ReSet Series 02
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['Waterproof ReSet 11', 'Waterproof ReSet Series 01', 'Waterproof ReSet Series 02']  ·  **catálogo familias:** []
- **Evidencia:** modelos candidatos: ['Waterproof ReSet 11', 'Waterproof ReSet Series 01', 'Waterproof ReSet Series 02']
- ⚠ manual mezcla modelos de familias distintas (o s83/catálogo discrepan) → adjudicación de familia/alcance necesaria.
- **Contenido pág 1 [Waterproof ReSet Call Point Series 01, 02 & 11]:** "# Waterproof ReSet Call Point Series 01, 02 & 11  The IP 67 Waterproof ReSet (WRP) has been designed to deal with today's difficult and harsh environments. Like the ReSet Call Point it is a unique fir"

```sql
-- sin candidato único — elige de las opciones arriba
UPDATE chunks_v2 SET product_model = '<PM>'
 WHERE source_file = 'Manual Pulsador convencional IP65 PCD-100WP (1)' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 2 filas
```

### `Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO`  —  confianza **baja**  ·  1 chunks

- **Candidato:** `None`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `NCO10/NCO100`
- **Opciones:** NCO-10  |  NCO-100  |  NCO10  |  NCO100  |  VSN-CO
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['NCO10', 'NCO100', 'VSN-CO']  ·  **catálogo familias:** []
- **Evidencia:** modelos candidatos: ['NCO-10', 'NCO-100', 'NCO10', 'NCO100', 'VSN-CO']
- ⚠ manual mezcla modelos de familias distintas (o s83/catálogo discrepan) → adjudicación de familia/alcance necesaria.
- **Contenido pág 1 [Compatibilidad detectores de monoxido NCO10 / NCO100 / VSN-CO]:** '# Compatibilidad detectores de monoxido NCO10 / NCO100 / VSN-CO  **Title** Instalación y compatibilidad detectores de monóxido NCO10 / NCO100 / VSN-CO  **Content** Los detectores de monóxido NCO10 / N'

```sql
-- sin candidato único — elige de las opciones arriba
UPDATE chunks_v2 SET product_model = '<PM>'
 WHERE source_file = 'Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `Compatibilidad-entre-equipos-Notifier-y-Morley`  —  confianza **baja**  ·  1 chunks

- **Candidato:** `None`  ·  manufacturer `Morley`
- **doc-level pm:** `unknown`  ·  **s83 primarios:** []  ·  **catálogo familias:** []
- **Evidencia:** ni doc-level, ni s83-primario, ni catalog-familia utilizables
- ⚠ sin fuente de modelo utilizable (doc genérico: FAQ/soporte/compatibilidad). El contenido no documenta UN producto; considerar dejar 'unknown' o etiquetar con la central de contexto si el contenido lo fija.
- **Contenido pág 1 [Compatibilidad entre equipos Notifier y Morley]:** '# Compatibilidad entre equipos Notifier y Morley  | **Question** | ¿Puedo instalar equipos de Notifier en una central de Morley o equipos de Morley en una central de Notifier?                         '

```sql
-- sin candidato único — elige de las opciones arriba
UPDATE chunks_v2 SET product_model = '<PM>'
 WHERE source_file = 'Compatibilidad-entre-equipos-Notifier-y-Morley' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus`  —  confianza **media**  ·  1 chunks

- **Candidato:** `NFS-Supra`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `ESS-2Plus/VSN-Plus2`
- **Opciones:** NFS-Supra  (primario doc-level)  |  ESS-2Plus/VSN-Plus2  (compuesto — LEGACY, a migrar a familia)
- **doc-level pm:** `NFS-Supra`  ·  **s83 primarios:** ['ESS-2Plus', 'NFS Supra', 'VSN-Plus2']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NFS-Supra' (documents table, governed)
- ⚠ manual MULTI-MODELO (3 modelos s83: ['ess2plus', 'nfssupra', 'vsnplus2']); doc-level nombra solo el primario 'NFS-Supra'. Convención adjudicada = FAMILIA-genérica (dir. Alberto s281); si no hay familia definida en catálogo, adjudicar primario/alcance.
- **Contenido pág 1 [Configuración entrada digital de la central NFS Supra / VSN-Plus2 / ESS-2Plus]:** '# Configuración entrada digital de la central NFS Supra / VSN-Plus2 / ESS-2Plus  **Title** Configuración entrada digital de la central NFS Supra / VSN-Plus2 / ESS-2Plus  **Content** La central NFS Sup'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NFS-Supra>'
 WHERE source_file = 'Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `Docs Morley-IAS Lite&Plus - QR`  —  confianza **media**  ·  1 chunks

- **Candidato:** `Morley Lite/Plus`  ·  manufacturer `Morley`
- **doc-level pm:** `Morley Lite/Plus`  ·  **s83 primarios:** []  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='Morley Lite/Plus' (documents table, governed); única fuente = doc-level (sin corroboración s83/catálogo)
- **Contenido pág 1 [Documentación Morley-IAS Lite & Morely-IAS Plus]:** '# Documentación Morley-IAS Lite & Morely-IAS Plus  https://buildings.honeywell.com/gb/en/lp/morleytech#ias-plus  [QR code linking to the above URL with "SCAN ME" text]'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=Morley Lite/Plus>'
 WHERE source_file = 'Docs Morley-IAS Lite&Plus - QR' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `EMA24RS2R_NX2y5-R-R`  —  confianza **media**  ·  1 chunks

- **Candidato:** `NX2/R/R y NX5/R/R`  ·  manufacturer `Notifier`
- **Opciones:** NX2/R/R y NX5/R/R  (doc-level)  |  NX2/R/R  (s83 primario)  |  NX5/R/R  (s83 primario)
- **doc-level pm:** `NX2/R/R y NX5/R/R`  ·  **s83 primarios:** ['NX2/R/R', 'NX5/R/R']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NX2/R/R y NX5/R/R' (documents table, governed)
- ⚠ doc-level pm='NX2/R/R y NX5/R/R' NO coincide con los primarios s83 ['NX2/R/R', 'NX5/R/R']; posible ruido de filename o modelo real no en s83.
- **Contenido pág 1 []:** '[Technical diagram showing an exploded view of a mounting assembly. The top portion shows a rectangular housing or cover with two mounting points. Below it is a mounting bracket or base plate. Four sc'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NX2/R/R y NX5/R/R>'
 WHERE source_file = 'EMA24RS2R_NX2y5-R-R' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `Finales-de-linea-de-las-centrales-convencionales`  —  confianza **media**  ·  1 chunks

- **Candidato:** `NFS2-8`  ·  manufacturer `Morley`
- **doc-level pm:** `NFS2-8`  ·  **s83 primarios:** []  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='NFS2-8' (documents table, governed); única fuente = doc-level (sin corroboración s83/catálogo)
- **Contenido pág 1 [Finales de línea de las centrales convencionales]:** '# Finales de línea de las centrales convencionales  **Question** ¿Que final de línea debo poner en centrales convencionales?  **Answers** Los finales de línea para las centrales convencionales son;  *'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=NFS2-8>'
 WHERE source_file = 'Finales-de-linea-de-las-centrales-convencionales' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `No-puedo-conectarme-con-el-ordenador-a-la-central-ZX`  —  confianza **media**  ·  1 chunks

- **Candidato:** `ZXe`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `ZX2e/ZX2Se/ZX5e/ZX5Se`
- **Opciones:** ZXe  (FAMILIA — adjudicada)  |  ZX2e/ZX2Se/ZX5e/ZX5Se  (compuesto — LEGACY, a migrar)
- **doc-level pm:** `unknown`  ·  **s83 primarios:** ['ZX2Se', 'ZX2e', 'ZX5Se', 'ZX5e']  ·  **catálogo familias:** ['ZXSe', 'ZXe']  ·  **umbrella:** ZXe
- **Evidencia:** doc-level pm vacío; catalog umbrella 'ZXe' (familia GT) mapea el documento → etiqueta-FAMILIA (convención adjudicada)
- **Contenido pág 1 [No puedo conectarme con el ordenador a la central ZX]:** '# No puedo conectarme con el ordenador a la central ZX  **Question** No conecta el ordenador con las central ZX2/5e - ZX2/5Se  **Answers** Este artículo es aplicable a las centrales ZX2e – ZX5e – ZX2S'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=ZXe>'
 WHERE source_file = 'No-puedo-conectarme-con-el-ordenador-a-la-central-ZX' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado`  —  confianza **media**  ·  1 chunks

- **Candidato:** `RP1R`  ·  manufacturer `Morley`
- **Compuesto (LEGACY — solo referencia; convención adjudicada = familia):** `RP1R-SUPRA/VSN-RP1R-PLUS2`
- **Opciones:** RP1R  (doc-level)  |  RP1R-SUPRA  (s83 primario)  |  VSN-RP1R-PLUS2  (s83 primario)
- **doc-level pm:** `RP1R`  ·  **s83 primarios:** ['RP1R-SUPRA', 'VSN-RP1R-PLUS2']  ·  **catálogo familias:** []
- **Evidencia:** doc-level product_model='RP1R' (documents table, governed)
- ⚠ doc-level pm='RP1R' NO coincide con los primarios s83 ['RP1R-SUPRA', 'VSN-RP1R-PLUS2']; posible ruido de filename o modelo real no en s83.
- **Contenido pág 1 [RP1R- SUPRA / VSN-RP1R-PLUS2 - Teclado bloqueado]:** '# RP1R- SUPRA / VSN-RP1R-PLUS2 - Teclado bloqueado  **Question** ¿Tengo el teclado bloqueado en la central RP1R-SUPRA / VSN-RP1R-PLUS2 sin motivo aparente?  **Answers**  Compruebe la tierra de la inst'

```sql
-- candidato derivado; sustituye <PM> si adjudicas otra opción
UPDATE chunks_v2 SET product_model = '<PM=RP1R>'
 WHERE source_file = 'RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

### `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica`  —  confianza **baja**  ·  1 chunks

- **Candidato:** `None`  ·  manufacturer `Morley`
- **doc-level pm:** `unknown`  ·  **s83 primarios:** []  ·  **catálogo familias:** []
- **Evidencia:** ni doc-level, ni s83-primario, ni catalog-familia utilizables
- ⚠ sin fuente de modelo utilizable (doc genérico: FAQ/soporte/compatibilidad). El contenido no documenta UN producto; considerar dejar 'unknown' o etiquetar con la central de contexto si el contenido lo fija.
- **Contenido pág 1 [Solicitud asistencia, curso de formación, puesta en marcha, consultas técnica o ]:** '# Solicitud asistencia, curso de formación, puesta en marcha, consultas técnica o licenciar programas (en WEB)  **Steps** Conozca todas las novedades y noticias sobre nuestras marcas, productos y serv'

```sql
-- sin candidato único — elige de las opciones arriba
UPDATE chunks_v2 SET product_model = '<PM>'
 WHERE source_file = 'Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 filas
```

## 5. Respaldo y reversibilidad

**Mecanismo de reversibilidad (obligatorio, patrón s78/s80 DB-only):**

1. **Respaldo pre-imagen** (una vez, antes de tocar nada) — deja el estado previo en tabla:
```sql
CREATE TABLE IF NOT EXISTS _s281_h0t3_backup AS
SELECT id, source_file, product_model AS product_model_prev, now() AS snapshot_at
FROM chunks_v2
WHERE product_model = 'unknown' OR product_model = '' OR product_model IS NULL
   -- + los chunks de la migración ZXe (compuesto→familia, §2), que NO son unknown:
   OR source_file IN ('MIE-MI-530rv001','MIE-MP-530rv001','MIE-MU-530rv001','MIE-MP-535rv001');
-- verifica: SELECT count(*) FROM _s281_h0t3_backup;  (unknown del census + 206 de ZXe)
```
2. Cada UPDATE lleva `RETURNING id` → cuenta las filas afectadas contra el recuento esperado.
3. **Rollback exacto** (todo el tramo, desde la pre-imagen — no depende de que el valor previo
   fuera uniforme):
```sql
UPDATE chunks_v2 c SET product_model = b.product_model_prev
FROM _s281_h0t3_backup b WHERE c.id = b.id;
-- o por source_file:  ... AND b.source_file = '<source_file>';
```
El pre-estado es hoy uniformemente `unknown` en los 28 (verificado por este instrumento, campo `unknown_values`), así que un rollback simplificado `SET product_model='unknown' WHERE source_file=X AND product_model='<label>'` también es válido; la tabla de respaldo lo hace robusto aunque eso cambie.

## 6. Apéndice — evidencia completa por source_file

### `MIE-MI-600`  (media)

- chunks: total 88 · unknown 88 (no-dup 80) · valores unknown {'unknown': 88} · marcas chunk ['Morley']
- documento: pm=`ZXSe` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['ZX10Se', 'ZX1Se', 'ZX2Se', 'ZX5Se'] · brand_on_doc=Morley IAS · family_scope='Serie ZX (Paneles de Incendio de la Serie ZX) - ZXSe' · s83_conf=high
- catálogo: doc_map_ids=['morley:zx10se', 'morley:zx1se', 'morley:zx2se', 'morley:zx5se'] · familias=['ZXSe'] · umbrella=ZXSe · homónimo={'termino': 'ZX', 'politica': 'clarify'}
- **candidato**: pm=`ZXSe` mfr=Morley · **confianza media**

### `FS2-1`  (media)

- chunks: total 30 · unknown 30 (no-dup 28) · valores unknown {'unknown': 30} · marcas chunk ['Notifier']
- documento: pm=`FS2-1` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['FS-1', 'FS-2', 'FS-4'] · brand_on_doc=Notifier · family_scope='Centrales de Incendios Convencionales de 1, 2 y 4 Zonas' · s83_conf=medium
- catálogo: doc_map_ids=['notifier:fs-1', 'notifier:fs-2', 'notifier:fs-4'] · familias=[]
- **candidato**: pm=`FS2-1` mfr=Notifier · **confianza media**

### `ms1-2-4`  (baja)

- chunks: total 29 · unknown 29 (no-dup 27) · valores unknown {'unknown': 29} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['Central convencional 1 Zona', 'Central convencional 2 Zonas', 'Central convencional 4 Zonas', 'MS1', 'MS2', 'MS4'] · brand_on_doc=unknown · family_scope='Centrales de Incendios Convencionales de 1, 2 y 4 Zonas' · s83_conf=medium
- catálogo: doc_map_ids=['unresolved:ms1', 'unresolved:ms2', 'unresolved:ms4'] · familias=[]
- **candidato**: pm=`None` mfr=Morley · **confianza baja**

### `Manual-de-Usuario-S3-T1-y-S-2-T1`  (media)

- chunks: total 28 · unknown 28 (no-dup 17) · valores unknown {'unknown': 28} · marcas chunk ['Fidegas']
- documento: pm=`S3-T1` · mfr=Fidegas · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['S/2-T1', 'S/3-T1'] · brand_on_doc=FIDEGAS · family_scope='Sensor Remoto de Gas Tóxico S-T1' · s83_conf=high
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`S3-T1` mfr=Fidegas · **confianza media**

### `Manual-de-Usuario-S3-T2-y-S2-T2`  (media)

- chunks: total 24 · unknown 24 (no-dup 22) · valores unknown {'unknown': 24} · marcas chunk ['Fidegas']
- documento: pm=`S3-T2` · mfr=Fidegas · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['00051', '00052', '03382', '03383', 'S/2-T2', 'S/3-T2'] · brand_on_doc=Fidegas · family_scope='Sensor Remoto de Gas FIDEGAS Serie S/-T2 (Oxígeno)' · s83_conf=high
- catálogo: doc_map_ids=['fidegas:00051', 'fidegas:00052', 'fidegas:03382', 'fidegas:03383'] · familias=[]
- **candidato**: pm=`S3-T2` mfr=Fidegas · **confianza media**

### `I56-2006-004 MI-DMMI_DMM2I_D2ICMO`  (media)

- chunks: total 17 · unknown 17 (no-dup 15) · valores unknown {'unknown': 17} · marcas chunk ['Morley']
- documento: pm=`MI-DMMI` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['MI-D2ICMO', 'MI-DMM2I', 'MI-DMMI'] · brand_on_doc=Morley IAS · family_scope='Serie M200' · s83_conf=high
- catálogo: doc_map_ids=['morley:mi-d2icmo', 'morley:mi-dmm2i', 'morley:mi-dmmi'] · familias=[]
- **candidato**: pm=`MI-DMMI` mfr=Morley · **confianza media**

### `BANI-G-24_Eng`  (media)

- chunks: total 16 · unknown 16 (no-dup 13) · valores unknown {'unknown': 16} · marcas chunk ['Hosiden Besson']
- documento: pm=`IS 28 Mk 4` · mfr=Hosiden Besson · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['IS 28 Mk 4 Banshee'] · brand_on_doc=Hosiden Besson · family_scope='Banshee' · s83_conf=medium
- catálogo: doc_map_ids=['hosiden:is-28-mk-4-banshee', 'hosiden:ls-28'] · familias=[]
- **candidato**: pm=`IS 28 Mk 4` mfr=Hosiden Besson · **confianza media**

### `LocatorPlus-Installation-Manual-1.3`  (media)

- chunks: total 16 · unknown 16 (no-dup 8) · valores unknown {'unknown': 16} · marcas chunk ['LGM Products']
- documento: pm=`unknown` · mfr=LGM Products · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['Signaline LocatorPlus'] · brand_on_doc=Signaline · family_scope='Signaline Heat' · s83_conf=high
- catálogo: doc_map_ids=['signaline:signaline-locatorplus'] · familias=[]
- **candidato**: pm=`Signaline LocatorPlus` mfr=LGM Products · **confianza media**

### `I56-3388-002 NFX-OPT_multi`  (media)

- chunks: total 9 · unknown 9 (no-dup 8) · valores unknown {'unknown': 9} · marcas chunk ['Notifier']
- documento: pm=`NFXI-OPT` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['NFX-OPT', 'NFXI-OPT'] · brand_on_doc=Notifier · family_scope='NFX-OPT / NFXI-OPT' · s83_conf=high
- catálogo: doc_map_ids=['notifier:nfx-opt', 'notifier:nfxi-opt'] · familias=[]
- **candidato**: pm=`NFXI-OPT` mfr=Notifier · **confianza media**

### `I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE`  (media)

- chunks: total 9 · unknown 9 (no-dup 8) · valores unknown {'unknown': 9} · marcas chunk ['Morley']
- documento: pm=`MI-DMMIE` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['MI-D2ICMOE', 'MI-DMM2IE', 'MI-DMMIE'] · brand_on_doc=Morley-IAS · family_scope='Morley series modules' · s83_conf=high
- catálogo: doc_map_ids=['morley:mi-d2icmoe', 'morley:mi-dmm2ie', 'morley:mi-dmmie'] · familias=[]
- **candidato**: pm=`MI-DMMIE` mfr=Morley · **confianza media**

### `I56-3389-002 NFX-SMT2_multi`  (media)

- chunks: total 7 · unknown 7 (no-dup 6) · valores unknown {'unknown': 7} · marcas chunk ['Notifier']
- documento: pm=`NFXI-SMT2` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['NFX-SMT2', 'NFXI-SMT2'] · brand_on_doc=Notifier · family_scope='SMART2' · s83_conf=high
- catálogo: doc_map_ids=['notifier:nfx-smt2', 'notifier:nfxi-smt2'] · familias=[]
- **candidato**: pm=`NFXI-SMT2` mfr=Notifier · **confianza media**

### `Manual_DXD-2X0 (55321002 MI 607 m 2024 c)`  (media)

- chunks: total 7 · unknown 7 (no-dup 5) · valores unknown {'unknown': 7} · marcas chunk ['Detnov']
- documento: pm=`DOD-220` · mfr=Detnov · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['DOD-220', 'DOTD-230', 'DTD-210', 'DTD-215'] · brand_on_doc=unknown · family_scope='Detectores convencionales' · s83_conf=high
- catálogo: doc_map_ids=['unresolved:dod-220', 'unresolved:dotd-230', 'unresolved:dtd-210', 'unresolved:dtd-215'] · familias=[]
- **candidato**: pm=`DOD-220` mfr=Detnov · **confianza media**

### `I56-5005-002_D Notifier Sounder Strobe`  (media)

- chunks: total 6 · unknown 6 (no-dup 2) · valores unknown {'unknown': 6} · marcas chunk ['Notifier']
- documento: pm=`B501AP` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['W*A-*C-I02'] · brand_on_doc=Notifier · family_scope='Notifier loop powered addressable wall mounted sounder strobes (EN54-23 W category)' · s83_conf=medium
- catálogo: doc_map_ids=['notifier:b501ap', 'notifier:wa-c-i02'] · familias=[]
- **candidato**: pm=`B501AP` mfr=Notifier · **confianza media**

### `MIE-MP-525rv1`  (media)

- chunks: total 6 · unknown 6 (no-dup 6) · valores unknown {'unknown': 6} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=[''] · status=['needs_review']
- s83: primarios=['DX1', 'DX2', 'DX4'] · brand_on_doc=Morley-IAS · family_scope='Centrales analógicas DX (Dimension)' · s83_conf=high
- catálogo: doc_map_ids=['morley:dx1', 'morley:dx2e', 'morley:dx4'] · familias=[] · umbrella=serie Dimension
- **candidato**: pm=`serie Dimension` mfr=Morley · **confianza media**

### `I56-5004-000-Notifier-Strobe`  (media)

- chunks: total 5 · unknown 5 (no-dup 2) · valores unknown {'unknown': 5} · marcas chunk ['Notifier']
- documento: pm=`Notifier Strobe` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=[] · brand_on_doc=Notifier · family_scope='EN54-23 W Class Wall Mounted Loop Powered Addressable Strobes' · s83_conf=medium
- catálogo: doc_map_ids=['notifier:b501ap'] · familias=[]
- **candidato**: pm=`Notifier Strobe` mfr=Notifier · **confianza media**

### `HLSI-MA-025 Guia Rapida NFS_Supra_XP_c`  (media)

- chunks: total 4 · unknown 4 (no-dup 3) · valores unknown {'unknown': 4} · marcas chunk ['Notifier']
- documento: pm=`NFS Supra` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['ESS 2Plus', 'NFS Supra', 'Vision Plus2'] · brand_on_doc=Honeywell · family_scope='NFS Supra / Vision Plus2 / ESS 2Plus' · s83_conf=medium
- catálogo: doc_map_ids=['notifier:ess-2plus', 'notifier:nfs-supra', 'notifier:vision-plus-2'] · familias=[]
- **candidato**: pm=`NFS Supra` mfr=Notifier · **confianza media**

### `D700-3-Sp`  (media)

- chunks: total 3 · unknown 3 (no-dup 3) · valores unknown {'unknown': 3} · marcas chunk ['Notifier']
- documento: pm=`D700` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['MCP1A', 'MCP1B', 'MCP2A', 'MCP2B', 'MCP3A', 'MCP4A'] · brand_on_doc=KAC · family_scope='MCP (pulsadores manuales serie MCP1.../MCP2.../MCP3.../MCP4...)' · s83_conf=high
- catálogo: doc_map_ids=['kac:mcp1a', 'kac:mcp1b', 'kac:mcp2a', 'kac:mcp2b', 'kac:mcp3a', 'kac:mcp4a'] · familias=[]
- **candidato**: pm=`D700` mfr=Notifier · **confianza media**

### `NSRE24`  (alta)

- chunks: total 3 · unknown 3 (no-dup 3) · valores unknown {'unknown': 3} · marcas chunk ['FUEGO']
- documento: pm=`NSRE24` · mfr=FUEGO · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['NSRE24'] · brand_on_doc=FUEGO · family_scope='Sirena exterior autoalimentada' · s83_conf=medium
- catálogo: doc_map_ids=['unresolved:nsre24'] · familias=[]
- **candidato**: pm=`NSRE24` mfr=FUEGO · **confianza alta**

### `Manual Pulsador convencional IP65 PCD-100WP (1)`  (baja)

- chunks: total 2 · unknown 2 (no-dup 2) · valores unknown {'unknown': 2} · marcas chunk ['Detnov']
- documento: pm=`unknown` · mfr=Detnov · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['Waterproof ReSet 11', 'Waterproof ReSet Series 01', 'Waterproof ReSet Series 02'] · brand_on_doc=STI (Safety Technology International) · family_scope='Waterproof ReSet Call Point (WRP)' · s83_conf=high
- catálogo: doc_map_ids=['sti:waterproof-reset-11', 'sti:waterproof-reset-series-01', 'sti:waterproof-reset-series-02'] · familias=[]
- **candidato**: pm=`None` mfr=Detnov · **confianza baja**

### `Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO`  (baja)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=['de'] · status=['active']
- s83: primarios=['NCO10', 'NCO100', 'VSN-CO'] · brand_on_doc=Honeywell · family_scope='Detectores de monóxido de carbono (CO)' · s83_conf=high
- catálogo: doc_map_ids=['notifier:nco-10', 'notifier:nco-100', 'notifier:vsn-co'] · familias=[]
- **candidato**: pm=`None` mfr=Morley · **confianza baja**

### `Compatibilidad-entre-equipos-Notifier-y-Morley`  (baja)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=['en'] · status=['active']
- s83: primarios=[] · brand_on_doc=Notifier / Morley · family_scope='' · s83_conf=high
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`None` mfr=Morley · **confianza baja**

### `Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`NFS-Supra` · mfr=Morley · doc_type=['programacion'] · lang=['en'] · status=['active']
- s83: primarios=['ESS-2Plus', 'NFS Supra', 'VSN-Plus2'] · brand_on_doc=Honeywell · family_scope='' · s83_conf=high
- catálogo: doc_map_ids=['notifier:ess-2plus', 'notifier:nfs-supra', 'notifier:vsn-plus2'] · familias=[]
- **candidato**: pm=`NFS-Supra` mfr=Morley · **confianza media**

### `Docs Morley-IAS Lite&Plus - QR`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`Morley Lite/Plus` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=[] · brand_on_doc=Morley-IAS · family_scope='Morley-IAS Lite & Morley-IAS Plus' · s83_conf=low
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`Morley Lite/Plus` mfr=Morley · **confianza media**

### `EMA24RS2R_NX2y5-R-R`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Notifier']
- documento: pm=`NX2/R/R y NX5/R/R` · mfr=Notifier · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['NX2/R/R', 'NX5/R/R'] · brand_on_doc=unknown · family_scope='' · s83_conf=low
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`NX2/R/R y NX5/R/R` mfr=Notifier · **confianza media**

### `Finales-de-linea-de-las-centrales-convencionales`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`NFS2-8` · mfr=Morley · doc_type=[''] · lang=['de'] · status=['active']
- s83: primarios=[] · brand_on_doc=Notifier · family_scope='Centrales convencionales' · s83_conf=medium
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`NFS2-8` mfr=Morley · **confianza media**

### `No-puedo-conectarme-con-el-ordenador-a-la-central-ZX`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['ZX2Se', 'ZX2e', 'ZX5Se', 'ZX5e'] · brand_on_doc=Morley-IAS · family_scope='ZX / ZXe' · s83_conf=high
- catálogo: doc_map_ids=['morley:020-891', 'morley:zx2e', 'morley:zx2se', 'morley:zx5e', 'morley:zx5se'] · familias=['ZXSe', 'ZXe'] · umbrella=ZXe · homónimo={'termino': 'ZX', 'politica': 'clarify'}
- **candidato**: pm=`ZXe` mfr=Morley · **confianza media**

### `RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado`  (media)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`RP1R` · mfr=Morley · doc_type=[''] · lang=[''] · status=['active']
- s83: primarios=['RP1R-SUPRA', 'VSN-RP1R-PLUS2'] · brand_on_doc=Honeywell · family_scope='' · s83_conf=high
- catálogo: doc_map_ids=['notifier:rp1r-supra'] · familias=[] · homónimo={'termino': 'RP1r', 'politica': 'prefer:notifier:rp1r-supra'}
- **candidato**: pm=`RP1R` mfr=Morley · **confianza media**

### `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica`  (baja)

- chunks: total 1 · unknown 1 (no-dup 1) · valores unknown {'unknown': 1} · marcas chunk ['Morley']
- documento: pm=`unknown` · mfr=Morley · doc_type=[''] · lang=['en'] · status=['active']
- s83: primarios=[] · brand_on_doc=Honeywell Life Safety · family_scope='' · s83_conf=high
- catálogo: doc_map_ids=[] · familias=[]
- **candidato**: pm=`None` mfr=Morley · **confianza baja**

## 7. Honestidad del instrumento — lo que NO decide

- **La etiqueta final es de Alberto.** El instrumento deriva un candidato determinista desde fuentes gobernadas (doc-level pm + s83 + catálogo) bajo la convención ADJUDICADA (familia-genérica donde hay familia); no juzga la fuente.
- **`confianza alta` = etiqueta corroborada, NO verdad de campo.** Significa: doc-level y s83/catálogo coinciden y no hay familia/alcance pendiente. Sigue siendo una PROPUESTA.
- **El re-tag afecta a los canales que keyean sobre `chunks_v2.product_model`** (keyword imatch + model-scoping/rerank). El ruteo por `allowed_sources`/`doc_map` (Canal A del resolver) ya alcanza los docs INDEPENDIENTE del tag (§2.3); el gate de lineage `verified` (Tramos 1-2) es ortogonal.
- **La migración ZXe toca golds vivos (hp009/hp018)** → gate de eval OBLIGATORIO (§2.5) antes de declarar el tramo bueno. El re-tag es reversible (§5).
- **Docs genéricos (FAQ/soporte)** sin un producto único documentado se marcan BAJA: puede ser correcto dejarlos `unknown` (no documentan UN modelo) — es una decisión de producto.
- **manufacturer** ya está poblado en los chunks (verificado); los UPDATE tocan solo `product_model` salvo que se marque conflicto de marca.
