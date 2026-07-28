# s285 · H0-T3 FINAL — informe de la lane de aplicación (26 adjudicaciones de Alberto)

**Estado: PROPUESTA COMPLETA, NADA APLICADO.** Esta lane operó SELECT-only (PostgREST GET),
0 escrituras, 0 llamadas a modelos ($0), 0 commits.

| Entregable | Fichero |
|---|---|
| SQL de re-tag (20 ejecutables + 3 CONFIRMAR comentados + opcionales) | `evals/s285_t3_final_apply_v1.sql` |
| SQL de eliminación (#21, #26) con respaldo y cascada | `evals/s285_t3_deletions_proposal_v1.sql` |
| Companion de aliases del catálogo gobernado | `data/catalog/s285_t3_alias_companion.jsonl` |
| Companion de productos (prerrequisito de los aliases) | `data/catalog/s285_t3_products_companion.jsonl` |
| Recibo de verificación en DB (READ-ONLY) | `evals/s285_t3_final_verify_v1.json` |
| Packet de origen | `evals/s281_h0t3_retag_packet_v1.md` §4 |

---

## 1. Titular

- **26/26 source_file de Alberto matchean EXACTO en `chunks_v2`. Cero discrepancias reales.**
  Las 3 citas abreviadas de su nota (`Finales-de-linea-de-las-centrales-convencional`,
  `Manual_DXD-2X0 (55321002...)`, `I56-4406-001`) NO son ficheros distintos: son truncamientos
  de su propia escritura; el nombre canónico de DB está en §2.
- **Los 26 suman EXACTAMENTE los 227 chunks que hoy quedan `product_model='unknown'` en todo el
  corpus** (0 NULL, 0 `''`). Reconciliación cerrada: 221 (20 UPDATEs) + 3 (CONFIRMAR) + 1 (#19,
  no se toca) + 2 (los 2 a borrar) = 227.
- **HALLAZGO MATERIAL — los bloques §2 y §3 del packet s281 YA ESTÁN APLICADOS en la DB viva**
  y no hay traza de ello en `DECISIONS.md`/`HISTORY.md` ni commit asociado:

  | source_file | packet (23-jul) | DB hoy (25-jul) |
  |---|---|---|
  | `MIE-MI-600` | `unknown` ×88 | **`ZXSe` ×88** |
  | `MIE-MI-530rv001` / `MP-530` / `MU-530` | `ZX2e/ZX5e` ×198 | **`ZXe` ×198** |
  | `MIE-MP-535rv001` | `ZX2e y ZX5e` ×9 | **`ZXe` ×9** |
  | `NSRE24` (confianza ALTA) | `unknown` ×3 | **`NSRE24` ×3** |

  Los valores coinciden EXACTAMENTE con lo propuesto (88 y 207 filas), así que se aplicó el SQL
  del packet tal cual. **Pero la tabla de respaldo `_s281_h0t3_backup` NO EXISTE** (HTTP 404 y
  ausente del OpenAPI de PostgREST) → esos dos bloques se aplicaron **sin pre-imagen**. No son
  irreversibles (el rollback directo está en el packet s281 §2.6), pero conviene que Alberto sepa
  que hay un cambio de corpus sin acta. **No re-ejecutar §2/§3 del packet s281.**
- **`data/model_catalog.json` (el detector Canal B) está sellado el 2026-07-18**, o sea ANTERIOR a
  ese apply → el detector no conoce las etiquetas nuevas. Rebuild = tarea aparte con el
  blast-radius de DEC-063.

---

## 2. Verificación por ficha (DB en vivo, `chunks_v2`=25090 · `documents`=1171)

`✓` = source_file exacto en DB · `unk` = product_model actual · `doc-lvl` = `documents.product_model`.

| # | source_file (DB, exacto) | chunks | unk | mfr | doc-lvl | ACCIÓN FINAL |
|---|---|---:|---|---|---|---|
| 1 | `FS2-1` ✓ | 30 | unknown | Notifier | `FS2-1` | pm → `FS-1/FS-2/FS-4` |
| 2 | `ms1-2-4` ✓ | 29 | unknown | Morley | `unknown` | pm → `MS-1/MS-2/MS-4` |
| 3 | `Manual-de-Usuario-S3-T1-y-S-2-T1` ✓ | 28 | unknown | Fidegas | `S3-T1` | pm → `S/2-T1 y S/3-T1` |
| 4 | `Manual-de-Usuario-S3-T2-y-S2-T2` ✓ | 24 | unknown | Fidegas | `S3-T2` | pm → `S/3-T2 y S/2-T2` |
| 5 | `I56-2006-004 MI-DMMI_DMM2I_D2ICMO` ✓ | 17 | unknown | Morley | `MI-DMMI` | pm → `MI-DMMI/MI-DMM2I/MI-D2ICMO` |
| 6 | `BANI-G-24_Eng` ✓ | 16 | unknown | Hosiden Besson | `IS 28 Mk 4` | pm → `IS 28 Mk 4` |
| 7 | `LocatorPlus-Installation-Manual-1.3` ✓ | 16 | unknown | LGM Products | `unknown` | pm → `LocatorPlus` **+ mfr → `Signaline`** |
| 8 | `I56-3388-002 NFX-OPT_multi` ✓ | 9 | unknown | Notifier | `NFXI-OPT` | pm → `NFX-OPT/NFXI-OPT` |
| 9 | `I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE` ✓ ⚠ | 9 | unknown | Morley | `MI-DMMIE` | pm → `MI-DMMIE/MI-DMM2IE/MI-D2ICMOE` |
| 10 | `I56-3389-002 NFX-SMT2_multi` ✓ | 7 | unknown | Notifier | `NFXI-SMT2` | pm → `NFX-SMT2/NFXI-SMT2` |
| 11 | `Manual_DXD-2X0 (55321002 MI 607 m 2024 c)` ✓ ⚠ | 7 | unknown | Detnov | `DOD-220` | pm → `DTD-210/DTD-215/DOD-220/DOTD-230` |
| 12 | `I56-5005-002_D Notifier Sounder Strobe` ✓ | 6 | unknown | Notifier | `B501AP` | pm → `WRA-PC-I02/WRA-RC-I02/WWA-PC-I02/WWA-RC-I02` † |
| 13 | `MIE-MP-525rv1` ✓ | 6 | unknown | Morley | `unknown` | pm → `DX` (FAMILIA) |
| 14 | `I56-5004-000-Notifier-Strobe` ✓ | 5 | unknown | Notifier | `Notifier Strobe` | pm → `WRL-PC-I02/WRL-RC-I02/WWL-PC-I02/WWL-RC-I02` † |
| 15 | `HLSI-MA-025 Guia Rapida NFS_Supra_XP_c` ✓ | 4 | unknown | Notifier | `NFS Supra` | pm → `NFS Supra/Vision Plus2/VSN-Plus2/ESS-2Plus` † |
| 16 | `D700-3-Sp` ✓ | 3 | unknown | Notifier | `D700` | pm → `MCP1A-x/MCP1B-x/MCP2A-x/MCP2B-x/MCP3A-x/MCP4A-x` |
| 17 | `Manual Pulsador convencional IP65 PCD-100WP (1)` ✓ | 2 | unknown | Detnov | `unknown` | pm → `Waterproof ReSet Call Point 01/02/11` |
| 18 | `Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO` ✓ | 1 | unknown | Morley | `unknown` | pm → `NCO10/NCO100/VSN-CO` |
| 19 | `Compatibilidad-entre-equipos-Notifier-y-Morley` ✓ | 1 | unknown | Morley | `unknown` | **SIN CAMBIO** (análisis en §4) |
| 20 | `Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus` ✓ | 1 | unknown | Morley | `NFS-Supra` | pm → igual que #15 † |
| 21 | `Docs Morley-IAS Lite&Plus - QR` ✓ | 1 | unknown | Morley | `Morley Lite/Plus` | **ELIMINAR** |
| 22 | `EMA24RS2R_NX2y5-R-R` ✓ | 1 | unknown | Notifier | `NX2/R/R y NX5/R/R` | pm → `NX2/R/R y NX5/R/R` |
| 23 | `Finales-de-linea-de-las-centrales-convencionales` ✓ ⚠ | 1 | unknown | Morley | `NFS2-8` | **[CONFIRMAR-ALBERTO]** |
| 24 | `No-puedo-conectarme-con-el-ordenador-a-la-central-ZX` ✓ | 1 | unknown | Morley | `unknown` | **[CONFIRMAR-ALBERTO]** |
| 25 | `RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado` ✓ | 1 | unknown | Morley | `RP1R` | **[CONFIRMAR-ALBERTO]** |
| 26 | `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica` ✓ | 1 | unknown | Morley | `unknown` | **ELIMINAR** |

⚠ = la nota de Alberto citaba el nombre truncado; el de la tabla es el exacto de DB.
† = desviación mínima de la letra, **medida**, con la alternativa estricta comentada en el SQL (§3.2).

**Total: 227 chunks · 26 documentos · 0 discrepancias de nombre.**

---

## 3. Decisiones de convención (y por qué, con la medida)

### 3.1 Separador del compuesto

`/` por defecto; **` y `** cuando algún MIEMBRO contiene `/` (fichas #3, #4, #22) — usar `/` daría
`S/2-T1/S/3-T1`, ilegible y ambiguo. Precedente vivo en el corpus: `ZX2e y ZX5e` (MIE-MP-535rv001)
y el propio doc-level `NX2/R/R y NX5/R/R`.

### 3.2 El compuesto NO rompe la findability por miembro (verificado en código)

- `retriever.model_to_imatch_pattern()` produce `\y<core>(?!\d)`. En ARE de PostgreSQL `/` y el
  espacio son frontera de palabra ⇒ `\yNFS[- ]*Supra(?!\d)` **casa** dentro de
  `NFS Supra/Vision Plus2/…`.
- `series_registry.normalize_model()` quita **solo** `-` y espacio ⇒ el core del miembro sigue
  siendo SUBSTRING del tag compuesto, que es la regla de nivel-1 de `_filter_to_query_models()`.
  Comprobado: `ms1` ⊂ `ms1/ms2/ms4` · `s/2t1` ⊂ `s/2t1ys/3t1` · `nx2/r/r` ⊂ `nx2/r/rynx5/r/r` ·
  `nco10` ⊂ `nco10/nco100/vsnco` · `fs1` ⊂ `fs1/fs2/fs4`.
- **La FAMILIA sí pierde el match por miembro** (`dx1` ⊄ `dx`) — trade-off ya adjudicado en
  s281 §2.3 para ZXe/ZXSe. Aplica a #13 (`DX`) y, si Alberto elige la opción A, a #23.

### 3.3 Las tres desviaciones † (declaradas, cada una con su medida)

1. **#12 / #14 — placeholder `x`.** `normalize_model('WRA-xC-I02')='wraxci02'`, y `'wrapci02'` **NO**
   es substring suyo ⇒ con el tag literal, la query "WRA-PC-I02" perdería el chunk en el
   model-filter. La lista concreta contiene la misma información y sí casa. *(En #16 el `x` es
   SUFIJO, así que `mcp1a` ⊂ `mcp1ax…` sigue casando → ahí SÍ se respeta la letra.)*
2. **#15 / #20 — cómo se REALIZA la equivalencia.** `norm_token`/`normalize_model` unifican
   `ESS 2Plus` ≡ `ESS-2Plus` (`ess2plus`) pero **no** `Vision Plus2` (`visionplus2`) con
   `VSN-Plus2` (`vsnplus2`). Para que las dos superficies que un técnico escribe alcancen el doc,
   el compuesto lleva ambas. El arreglo estructural (redirect en el catálogo) va en el companion.
3. **#1 — `FS2-1` no se usa como etiqueta.** Alberto lo declaró filename mal nombrado; el doc-level
   `FS2-1` queda superado.

### 3.4 Lo que NO se inventó

Los valores concretos del sufijo `-x` de los MCP (#16) **no están en la fuente** (el manual escribe
literalmente "MCP1…", "MCP2…"). Enumerarlos sería invención (`feedback_corpus_gap`). Los 6 modelos
base (`kac:mcp1a`…`kac:mcp4a`) ya existen y son consumibles; una query "MCP1A" resuelve. Una query
con la SKU completa ("MCP1A-R") no resolverá hasta que haya fuente para los sufijos.

---

## 4. Los dos análisis pedidos: docs de compatibilidad

### 4.1 #19 — ¿puede el `pm` actual + el model-filter EXCLUIR el doc? **Sí, y está medido**

`Compatibilidad-entre-equipos-Notifier-y-Morley` · 1 chunk · `pm='unknown'` · `mfr='Morley'` ·
`doc_map_ids=[]` (no está en el catálogo gobernado).

Mecánica verificada en `src/rag/retriever.py`:

1. **Query SIN modelo** (p.ej. *"¿puedo instalar equipos Notifier en una central Morley?"* — la
   pregunta literal del doc): `extract_product_models` → `[]` ⇒ `_filter_to_query_models` devuelve
   los chunks **sin tocar** (línea 2058). **El doc NO se excluye.** Este es su caso de uso natural.
2. **Query CON modelo** (*"¿puedo poner un MI-DMMI en una NFS Supra?"*): nivel-1 exige que algún
   core de la query sea substring de `normalize_model(product_model)`; `'unknown'` no casa nada ⇒
   **el chunk se DESCARTA**. El fail-open escalonado solo lo rescata si quedaran <3 supervivientes
   — es decir, en un pool sano se pierde en silencio. **Confirmado: sí, hoy queda excluido.**
3. **La protección que existiría no le llega.** Con `IDENTITY_RESOLVE=on` el seam-2
   (retriever.py:2067-2072) re-incorpora los chunks cuyo `source_file` está en
   `allowed_sources` del resolver — pero eso se deriva de `doc_map`, y **este doc no está en
   `doc_map`** ⇒ sin cobertura.
4. **La lane `COMPATIBILITY_BUNDLE_COVERAGE` tampoco lo usa, por diseño.**
   `is_compatibility_bundle_query()` exige `archetype=='compatibility'` **y exactamente DOS
   `source_groups` gobernados**, y cada grupo necesita `token` + `ids` + `sources` no vacíos
   (`_canonical_groups` levanta excepción si falta alguno) — este doc no tiene ids ni doc_map, así
   que **no puede ser ninguno de los dos grupos**. Además el contrato es fail-closed y
   `is_cross_manufacturer_compatibility_query` impide marcar interoperabilidad cross-marca como
   soportada. Un FAQ de 1 chunk no cubre los 3 facets exigidos (`protocol_scope`,
   `supported_device_roster`, `loop_topology`).

**Opciones (ninguna implementada, como pediste):**

| | Opción | Coste | Efecto | Riesgo |
|---|---|---|---|---|
| **O1** | Entrada en `data/catalog/doc_map.jsonl` para este source_file bajo las entidades Notifier y Morley | Datos, 2 líneas, sin tocar `pm` (respeta "no re-tag") | El seam-2 lo re-incorpora siempre que resuelva cualquiera de las dos marcas | Ruido: se colaría en muchas queries de esas entidades |
| **O2** | `doc_type='compatibilidad'` + regla que lo abra solo si la query es cross-marca | Código (lane nueva) | Preciso | Fuera del lote; necesita gold que lo ejercite |
| **O3** | Un `pm` centinela (`generico`, `multi`) | 1 UPDATE | **NO funciona**: el filtro es substring, un centinela sigue sin casar | — |
| **O4** | Dejarlo como está (lo adjudicado) | 0 | El guard cross-marca (`is_cross_brand_query` → `admit_no_info`) ya hace que el bot **no invente** compatibilidad; simplemente no cita el FAQ | Se pierde la afirmación explícita "no son compatibles" cuando la query nombra modelos |

**Recomendación:** mantener **O4** hoy (es lo adjudicado y el comportamiento seguro ya está
cubierto por el guard cross-marca), y promover **O1 acotado** solo cuando exista un gold que
ejercite el caso — sin gold, añadir el doc_map es ruido no medido (regla eval-driven).

### 4.2 #18 — el mismo doc, pero CON modelos

`Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO` sí nombra productos y **sí** está en
`doc_map` (`notifier:nco-10`, `notifier:nco-100`, `notifier:vsn-co`). Con el tag
`NCO10/NCO100/VSN-CO`:

- deja de ser invisible al model-filter (`nco10`, `nco100`, `vsnco` ⊂ el tag normalizado);
- el Canal A ya lo alcanzaba vía `doc_map` — el re-tag arregla el Canal B;
- la lane `COMPATIBILITY_BUNDLE_COVERAGE` **sigue sin poder usarlo como bundle**: es 1 chunk y no
  aporta `protocol_scope` + `supported_device_roster` + `loop_topology` ligados a dos entidades
  distintas. Sirve como evidencia normal de retrieval, no como bundle relacional. Eso es correcto
  y no requiere acción.
- Ojo declarado: `notifier:vsn-co` es un **redirect** a `morley:vsn-co` (adjudicación s91) ⇒ una
  query con VSN-CO resuelve al id de Morley; el tag de chunk no cambia nada de eso.

---

## 5. Companion del catálogo gobernado

**Verificado por simulación de merge (Protocolo 1):** copié `data/catalog/` a un temporal, fusioné
los dos companion y corrí `scripts/catalog_store.py::validate` →
**0 errores antes y 0 errores después.** `tests/test_catalog_store.py` 29/29 verde. Los ficheros
companion viven en `data/catalog/` pero **NO los lee nadie**: `catalog_store.FILES` tiene la lista
fija de 7 nombres ⇒ son inertes hasta que alguien los fusione a mano.

### 5.1 `s285_t3_alias_companion.jsonl` — 21 aliases (13 funcionales + 8 documentales)

Campo extra `efecto` (metadato del companion, `validate` lo ignora):

- **`funcional` (13)** — el normkey es NUEVO ⇒ añade una vía de resolución que hoy no existe:
  `WRA-PC-I02`, `WRA-RC-I02`, `WWA-PC-I02`, `WWA-RC-I02` (→ `notifier:wa-c-i02`);
  `WRL-PC-I02`, `WRL-RC-I02`, `WWL-PC-I02`, `WWL-RC-I02` (→ `notifier:wl-c-i02`);
  `VSN-Plus2` (→ `notifier:vision-plus-2`); `IS 28 Mk 4` (→ `hosiden:is-28-mk-4-banshee`);
  `Waterproof ReSet Call Point 01/02/11` (→ los 3 `sti:*`).
- **`no-op-normkey` (8)** — **hallazgo que conviene que Alberto sepa**: `norm_token()` del catálogo
  quita `- _ / . ` y espacios, así que `MS1`≡`MS-1`, `S2-T1`≡`S/2-T1`, `ESS 2Plus`≡`ESS-2Plus`
  **ya estaban unificados**. El alias es documentación de la adjudicación, no mecánica.
  **El bloqueo real de esas fichas no era el alias, era que el producto destino es
  `candidate:true` o no existía** — `Catalog.build_indexes()` no consume aliases cuyo destino no
  sea `activo` y no-candidate. Por eso el companion de productos es prerrequisito.
- **Guardas de ambigüedad anotadas** en `provenance` para los cortos (`MS1`/`MS2`/`MS4`: 3 chars
  alfanuméricos) y para el caso de la barra (`S/2-T1`): el detector estático
  `data/model_catalog.json` **no conoce ninguno** — verificado en vivo:
  `extract_product_models('MS1')=[]`, `('MS-1')=[]`, `('S/2-T1')=[]` pero `('S2-T1')=['S2-T1']`.

### 5.2 `s285_t3_products_companion.jsonl` — 15 filas (8 add / 3 promote / 4 redirect)

Es el **prerrequisito** para que los aliases estén vivos (un alias a un id inexistente hace fallar
`validate` = CI en rojo; un alias a un `candidate` no se indexa). Campo `_op`:

- **add (8)**: `morley:ms-1/-2/-4` (#2) · `fidegas:s2-t1`, `s3-t1`, `s2-t2`, `s3-t2` (#3/#4 — **no
  existía NINGÚN producto Fidegas de estas dos familias**) · `notifier:wl-c-i02` (#14, misma
  convención de wildcard que el `W*A-*C-I02` existente).
- **promote (3)** `candidate:true → false`: `notifier:wa-c-i02` (#12), `notifier:ess-2plus`
  (#15/#20), `hosiden:is-28-mk-4-banshee` (#6).
- **redirect (4)**: `unresolved:ms1/2/4` → los nuevos `morley:ms-*`; **`notifier:vsn-plus2` →
  `notifier:vision-plus-2`** (la forma estructural de la equivalencia de Alberto; el alias
  `VSN-Plus2` la mantiene resoluble porque los redirects no se indexan como canónicos).

**Resolución efectiva tras el merge (medida):** `MS1`, `MS-1/-2/-4`, `S/2-T1`, `S2-T1`, `S/3-T2`,
las 8 SKU `W**-*C-I02`, `Vision Plus2`, `VSN-Plus2`, `ESS 2Plus`, `ESS-2Plus`, `IS 28 Mk 4`,
`Waterproof ReSet Call Point 01`, `LocatorPlus`, `SLP-001` → **todos resuelven**.

### 5.3 Bloqueos de catálogo DECLARADOS (no tocados — son decisiones de identidad)

1. **`DX` (#13) no tiene paraguas.** `umbrellas.jsonl` tiene `Dimension`/`serie Dimension`, pero
   agrupa `dx1e/dx2e/dx4e` — **la generación "e", que NO es DX1/DX2/DX4**. Y `morley:dx2` no
   existe: el token `DX2` está aliaseado a `morley:dx2e` (adjudicación s90 P2). Crear `morley:dx2`
   exigiría re-apuntar ese alias ⇒ **hay que adjudicar si DX2 ≡ DX2e**. Hasta entonces, con
   `pm='DX'` los miembros DX1/DX2/DX4 **no** tienen vía de catálogo.
2. **#25 — el catálogo contradice la adjudicación.** Existe el alias `VSN-RP1r-PLUS2` →
   `notifier:rp1r-supra`, es decir el catálogo los trata como el MISMO producto, y Alberto dice que
   son DOS. Además hay `unresolved:vsn-rp1r-2plus` (candidate) por separado. Re-apuntar el alias
   es decisión suya.
3. **`NFS Supra` sigue `candidate:true`** (`notifier:nfs-supra`, marcado así por una colisión
   alias↔canonical en s91) ⇒ `resolve('NFS Supra')` → `None` hoy. No se promueve aquí porque
   ningún alias de este lote depende de ello y la promoción podría re-disparar la colisión
   histórica; queda como ítem de backlog verificable.
4. **Otros `candidate` que la adjudicación deja "lógicamente resueltos" pero no promocionados**
   (sin alias dependiente, por eso fuera del companion): `notifier:fs-1/-2/-4` (#1),
   `unresolved:dtd-210/dtd-215/dod-220/dotd-230` (#11 — además siguen en el namespace
   `unresolved:` pese a que la marca es Detnov), `notifier:vsn-plus2` (queda como redirect),
   `unresolved:vsn-co`. Promoverlos es un lote de catálogo de 10 minutos; lo dejo enumerado.

---

## 6. Los 3 [CONFIRMAR-ALBERTO] — recomendación en una línea

| # | Ficha | Recomendación de la lane |
|---|---|---|
| **23** | `Finales-de-linea-de-las-centrales-convencionales` (1 chunk) | **Enumerar los MIEMBROS** — `NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-PLUS/VSN4-PLUS/VSN8-PLUS/VSN12-PLUS` — porque la convención familia-genérica se adjudicó para UNA familia y aquí hay TRES; con el compuesto de familias ningún miembro casa (`nfs2` ⊄ `nfs/vsnlt/vsnplus`) y este doc **no tiene `doc_map`**, así que el Canal A tampoco compensaría → quedaría tan invisible como con `unknown`. |
| **24** | `No-puedo-conectarme-…-central-ZX` (1 chunk) | **Sí, `ZXe/ZXSe`** — compuesto de las dos etiquetas-familia YA vivas en DB; ambos tokens casan el canal keyword y los miembros llegan por Canal A porque este doc **sí** tiene `doc_map` (`morley:zx2e/zx2se/zx5e/zx5se`, verificado). Riesgo bajo, coherente con la migración simétrica. |
| **25** | `RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado` (1 chunk) | **`RP1r-Supra/VSN-RP1r-PLUS2`** (casing del catálogo; el matching es case-insensitive) — ambos cores casan; **pero adjudica aparte el conflicto §5.3(2)**: hoy el alias `VSN-RP1r-PLUS2` apunta a `notifier:rp1r-supra`, o sea el catálogo dice "mismo producto" y tú dices "dos". |

Nota de #23: su doc-level es `pm='NFS2-8'` + `mfr='Morley'` aunque el contenido mezcla NFS
(Notifier) y VSN (Morley), y `language='de'` con texto en español. Ejes T2/doc-level, fuera de
esta lane.

---

## 7. Eliminaciones (#21, #26) — lo que se lleva por delante

Esquema inspeccionado en `migrations/` + PostgREST. **`chunks_v2.embedding` es una COLUMNA**, no
hay tabla de embeddings: borrar el chunk borra su vector.

| | `Docs Morley-IAS Lite&Plus - QR` | `Solicitud-asistencia-…-tecnica` |
|---|---|---|
| `document_id` | `3912b42a-26c9-46ea-b055-b24309083608` | `b769abb0-6d2f-4003-be9b-e62099b5a03a` |
| `chunks_v2` | 1 | 1 |
| `chunks` (legacy) | 1 | 1 |
| `chunks_v2_hyq` (CASCADE) | 2 | 3 |
| `chunks_v2_enunciados` (CASCADE) | 0 | 0 |
| `document_visual_assets` (**RESTRICT**) | 1 | 1 |
| `document_group_members` | 0 | 0 |
| refs `supersedes`/`superseded_by` | 0 | 0 |

- `document_visual_assets.document_id` y `chunks.document_id`/`chunks_v2.document_id` **no llevan
  `ON DELETE`** ⇒ hay que borrar hijos ANTES o el `DELETE FROM documents` falla.
- **El JPG vive en Supabase Storage (bucket `manual-images`), no en Postgres**: el SQL no lo borra.
  Las 2 rutas + sus sha256 están en la cabecera del fichero de eliminaciones; descargarlos antes.
- **Excel `data/Inventario_Manuales.xlsx`, hoja `Morley`:** filas **14 y 103** (el mismo QR
  aparece DOS veces, `publico` y `privado` — borrar ambas) y fila **329**. Recalcular `Resumen`.
  Y retirar el PDF de origen para que un re-ingest no lo reintroduzca.
- Fingerprint tras el borrado: `chunks_v2` 25090→25088 · `documents` 1171→1169.

---

## 8. Riesgo de eval y GATE (obligatorio)

Barrido literal de `evals/gold_answers_v1.yaml` contra los 26 source_file:

- **`HLSI-MA-025` aparece 1 vez, en el bloque de fuentes de `cat009`** (*"¿Qué resistencia de fin
  de línea (EOL) … de la central convencional NFS Supra?"*, gold que cita explícitamente las
  variantes VSN-Plus2 y ESS-2Plus). Las fichas **#15 y #20 tocan justo esos docs** ⇒ **`cat009` es
  el gold en riesgo de ESTE paquete**, no solo hp009/hp018.
- `MIE-MI-530` aparece 15 veces (hp009/hp018) — pero esa migración **ya está aplicada**, así que su
  gate corresponde al estado actual; se mantiene como control histórico del tramo.
- Ningún otro de los 26 aparece en los golds.

**Gate antes de dar el tramo por bueno** (el re-tag es reversible por §7 del SQL):

```
python scripts/test_bot_vs_gold.py     # cat009 (afectado) + hp009/hp018 (control ZX)
                                       # + hp006/hp010 (control no-tocado)
```

Criterio: `cat009` no empeora · `hp018` se mantiene PASS · `hp009` no empeora · controles quietos.
Baseline vigente **v3 (s284)**: 16 PASS / 20 PARCIAL / 3 FALLO
(`evals/bot_vs_gold_39_baseline_c1v4_v3judgefull_s284.yaml`). **Correr con paridad completa de
flags (DEC-157)** — un baseline sin paridad ya produjo un FALLO artefacto en s283.

Segundo eje de riesgo, declarado: el companion de catálogo **no es inerte en producción** una vez
fusionado (`IDENTITY_RESOLVE` está activo en el release) ⇒ si se fusiona, entra en el mismo gate.

---

## 9. Próximos pasos

1. **Alberto**: visto de los 3 CONFIRMAR (§6) + visto del borrado destructivo (§7) + decidir sobre
   las 3 desviaciones † (§3.3) y sobre los bloqueos de catálogo (§5.3).
2. Ejecutar `evals/s285_t3_final_apply_v1.sql` §0 (respaldo) → §1/§2 → §3 (conteos).
3. **Gate `test_bot_vs_gold` (§8) con paridad de flags.** Sin gate verde, el tramo no se declara.
4. Solo entonces: §4 (CONFIRMAR), eliminaciones + Excel + Storage, y merge de los companion de
   catálogo (con su propio paso por el gate).
5. Backlog derivado: rebuild de `data/model_catalog.json` (hoy sellado el 18-jul, anterior incluso
   al apply ZXe/ZXSe) — tarea aparte por el blast-radius DEC-063; promoción del lote de `candidate`
   de §5.3(4); adjudicación DX2≡DX2e y del alias `VSN-RP1r-PLUS2`.
6. **Acta pendiente**: documentar en `DECISIONS.md`/`HISTORY.md` el apply out-of-band de
   ZXe/ZXSe/NSRE24 (§1) — hoy el corpus tiene un cambio sin traza.
