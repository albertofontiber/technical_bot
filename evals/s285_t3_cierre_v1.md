# s285 · H0-T3 CIERRE — los 3 flecos tras la aplicación de Alberto

**Rama:** `claude/s282-h0t2-qa` · **worktree:** `Technical Bot-s281` · **0 commits** ·
**DB SELECT-only** (PostgREST GET) · **$0 LLM**.

| Fleco | Estado |
|---|---|
| 1 · Excel `data/Inventario_Manuales.xlsx` | **RESUELTO** — 3 filas borradas + `Resumen` recalculado + copia previa |
| 2 · Merge de los companion al catálogo canónico (+ adjudicación #25) | **APLICADO y `validate` 0 errores** — pero **1 test rojo** (`test_catalog_resolver.py::test_roundtrip_muestra_de_canonicals`), diagnosticado como **latente pre-existente** destapado por el merge → **no forzado, requiere adjudicación** (§2.5) |
| 3 · Rutas de Storage | **RESUELTO** — 2 objetos localizados, vivos y ya huérfanos; listos para borrar a mano |

---

## 0. Estado de la DB tras la aplicación de Alberto (verificado, READ-ONLY)

| Comprobación | Resultado |
|---|---|
| `documents` | **1169** (era 1171 → los 2 DELETE aplicados) |
| `chunks_v2` | **25088** (era 25090) |
| `documents` / `chunks_v2` / `chunks` / `document_visual_assets` con esos 2 `document_id` | **0 / 0 / 0 / 0** |
| Tablas de respaldo presentes | `_s285_t3_del_docs` (2) · `_s285_t3_del_visual` (2) · `_s285_t3_del_chunks_v2` (2) · `_s285_t3_del_chunks_legacy` (2) · `_s285_t3_del_hyq` (5) · `_s285_t3_backup` |
| `chunks_v2` con `product_model='unknown'` | **1** — cuadra con la reconciliación del informe final: 227 = 221 (20 UPDATEs) + 3 (los CONFIRMAR) + **1 (#19 `Compatibilidad-entre-equipos-Notifier-y-Morley`, SIN CAMBIO por diseño)** + 2 (borrados). Los 20 UPDATEs **y** los 3 CONFIRMAR están aplicados. |

Fingerprint coincide exactamente con el previsto en §7 del informe final (25090→25088, 1171→1169).

---

## 1. Excel — 3 filas eliminadas (verificadas POR NOMBRE antes de tocar)

**Copia previa:** `data/Inventario_Manuales_backup_s285.xlsx` (58.518 bytes, sha256 `f74e1977…`).
*Nota:* `.gitignore:26` ignora `data/*`, así que el backup **no aparece en `git status`** — vive solo
en disco. El `.xlsx` principal sí está versionado (force-add histórico) y sale como `M`.

Herramienta: `openpyxl`. Hoja **`Morley`** (única tocada). Verificación previa asertada
(el script aborta si algo no casa) sobre `Producto` + `Subcarpeta` + `Archivo`, **no por número de fila a ciegas**:

| Fila (pre-borrado) | Producto | Subcarpeta | Archivo | ✓ |
|---:|---|---|---|:-:|
| 14 | `Docs Morley-IAS Lite&Plus - QR` | `publico` | `Docs Morley-IAS Lite&Plus - QR.pdf` | ✓ |
| 103 | `Docs Morley-IAS Lite&Plus - QR` | `privado` | `Docs Morley-IAS Lite&Plus - QR.pdf` | ✓ |
| 329 | `Solicitud-asistencia-curso-de-formacion-puesta-en-` | `guias` | `Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica.pdf` | ✓ |

Los 3 números de fila del informe final **se confirman leyendo el Excel**, no se asumen.

**Guarda ejecutada:** barrido de las 372 filas buscando cualquier OTRA entrada de esos 2 documentos
→ **0 filas adicionales**. Y el vecino homónimo **`Docs Morley-IAS Max - QR` (filas 15 y 104) NO se
tocó** — verificado post-borrado: sigue presente en las filas 14 y 102.

**Efecto medido:**

- hoja `Morley`: **372 → 369** filas de datos · **109 → 107** productos distintos
  (los 2 documentos borrados eran el único registro de su respectivo `Producto`).
- hoja `Resumen`, fila `Morley` (valores **hardcoded**, sin fórmulas — verificado con
  `data_only=True`): `Productos` **109 → 107**, `Documentos` **372 → 369**.
- El resto de hojas, el `merged A1:D1` de `Resumen`, el `freeze A2` de `Detnov` y el relleno
  `00DDDDDD` de las cabeceras quedan intactos (workbook sin imágenes, gráficos, tablas,
  formato condicional, validaciones ni hipervínculos → `delete_rows` es seguro aquí).

**Pendiente de Alberto (fuera de la DB y del repo):** retirar el PDF de origen en
disco/OneDrive para que un futuro re-ingest no reintroduzca los 2 documentos.

---

## 2. Catálogo gobernado — merge de los companion + adjudicación #25

### 2.1 Convención de escritura

Escritura vía la puerta (`catalog_store.write_jsonl`, `sort_keys=True`, `ensure_ascii=False`).
Los ficheros canónicos **no están globalmente ordenados** (son *bulk-sorted* de s83/s91 con cola
apendizada — verificado: `products` deja de estar ordenado por `id` en el índice 1601), así que se
siguió la convención de los writers más recientes (`s91_apply_c2.py`, `s91_apply_homonyms.py`):
**modificar filas in-place y APENDIZAR las nuevas al final**. Diff resultante: **38 líneas**, no 1.646.

Campos del companion que **NO** se copian al canónico (metadatos de la propuesta, para que las filas
tengan la forma exacta de las existentes): `_op` en products, `efecto` en aliases. Su contenido ya
está narrado en `evals/s285_t3_final_report_v1.md` §5.1/§5.2.

### 2.2 Diff de `products.jsonl` (1646 → **1655** líneas; +16 / −7)

**ADD (9)** — 8 del companion + 1 de la adjudicación #25:

| id | canonical_model | vendido_bajo | ficha |
|---|---|---|---|
| `morley:ms-1` / `ms-2` / `ms-4` | `MS-1` / `MS-2` / `MS-4` | Morley | #2 |
| `fidegas:s2-t1` / `s3-t1` | `S/2-T1` / `S/3-T1` | Fidegas | #3 |
| `fidegas:s2-t2` / `s3-t2` | `S/2-T2` / `S/3-T2` | Fidegas | #4 |
| `notifier:wl-c-i02` | `W*L-*C-I02` | Notifier | #14 |
| **`morley:vsn-rp1r-plus2`** | **`VSN-RP1r-PLUS2`** | **Morley-IAS** | **#25** |

`provenance` de #25 (literal, con las URLs de evidencia de Alberto):
`gt-s285-alberto-t3 (adjudicación #25 de Alberto sobre el packet s281_h0t3: VSN-RP1r-PLUS2 y
RP1r-Supra son DOS productos DISTINTOS. Evidencia Morley: morley-ias.es/component/zoo/item/vsn-rp1r-plus2
+ ibdglobal 11736. Evidencia Notifier RP1r-Supra: notifier.es rp1r-supra-4 + ibdglobal 11651)`

**PROMOTE `candidate: true → false` (3):** `notifier:wa-c-i02` (#12) · `notifier:ess-2plus` (#15/#20)
· `hosiden:is-28-mk-4-banshee` (#6).

**REDIRECT (4):** `unresolved:ms1|ms2|ms4` → `morley:ms-1|-2|-4` · `notifier:vsn-plus2` →
`notifier:vision-plus-2`. (En los 4 casos `estado: activo → redirect`, `candidate → false`,
`redirect_to` nuevo y `provenance` apendizada.)

### 2.3 Diff de `aliases.jsonl` (1739 → **1760** líneas; +22 / −1)

**21 aliases nuevos** (los del companion, tal cual, sin `efecto`):
`WRA-PC-I02`, `WRA-RC-I02`, `WWA-PC-I02`, `WWA-RC-I02` → `notifier:wa-c-i02` ·
`WRL-PC-I02`, `WRL-RC-I02`, `WWL-PC-I02`, `WWL-RC-I02` → `notifier:wl-c-i02` ·
`VSN-Plus2` → `notifier:vision-plus-2` · `ESS 2Plus` → `notifier:ess-2plus` ·
`IS 28 Mk 4` → `hosiden:is-28-mk-4-banshee` ·
`Waterproof ReSet Call Point 01/02/11` → los 3 `sti:*` ·
`MS1`/`MS2`/`MS4` → `morley:ms-*` · `S2-T1`/`S3-T1`/`S2-T2`/`S3-T2` → `fidegas:*`.

**1 alias RE-APUNTADO (adjudicación #25):**

```
antes: {"alias": "VSN-RP1r-PLUS2", "id": "notifier:rp1r-supra",     "provenance": "gt-s78-morley (…)"}
ahora: {"alias": "VSN-RP1r-PLUS2", "id": "morley:vsn-rp1r-plus2",   "provenance": "gt-s78-morley (…) | gt-s285-alberto-t3 (adjudicación #25 …)"}
```

El script aborta si el alias no apunta exactamente a `notifier:rp1r-supra` (guarda anti-doble-merge).

### 2.4 Resolución efectiva — ANTES vs DESPUÉS (medido, `catalog_store.resolve`)

| token | antes | después |
|---|---|---|
| `MS1` · `MS-1/-2/-4` | `None` | `exact → morley:ms-*` |
| `S/2-T1` · `S2-T1` · `S/3-T2` · `S3-T2` | `None` | `exact → fidegas:*` |
| las 8 SKU `W**-*C-I02` | `None` | `alias → notifier:wa-c-i02` / `wl-c-i02` |
| `W*A-*C-I02` | `None` | `exact → notifier:wa-c-i02` |
| `ESS 2Plus` · `ESS-2Plus` | `None` | `exact → notifier:ess-2plus` |
| `VSN-Plus2` | `None` | `alias → notifier:vision-plus-2` |
| `IS 28 Mk 4` · `Banshee` | `None` | `alias → hosiden:is-28-mk-4-banshee` |
| `Waterproof ReSet Call Point 01` | `None` | `alias → sti:waterproof-reset-series-01` |
| **`VSN-RP1r-PLUS2`** | `alias → notifier:rp1r-supra` | **`exact → morley:vsn-rp1r-plus2`** |
| `VSN-RP1r-PLUS` · `VSN-RP1r+` · `RP1r-Supra` · `RP1r` · `VSN-RP1r` | *(sin cambio)* | *(sin cambio)* |
| `LocatorPlus` · `SLP-001` · `Vision Plus2` | *(sin cambio)* | *(sin cambio)* |

**Los miembros ZX — NO había nada que añadir (verificado, es un no-op).** El encargo pedía
"ZX1Se/ZX2Se/ZX5Se/ZX10Se y ZX1e/ZX2e/ZX5e como aliases/miembros"; el catálogo **ya los tiene**
desde s78/s90 y resuelven igual antes y después:

```
ZXSe   → paraguas [morley:zx1se, zx2se, zx5se, zx10se]   (umbrellas.jsonl, divergent=true, candidate=false)
ZXe    → paraguas [morley:zx1e,  zx2e,  zx5e]
ZX1Se · ZX2Se · ZX5Se · ZX10Se · ZX1e · ZX2e · ZX5e  → exact, 1 id cada uno (products.jsonl:419-426)
```

Añadir aliases con el mismo texto que el `canonical_model` sería redundante (el `exact` gana al alias
en `resolve()`) y ensuciaría el fichero. **No se tocó nada de ZX.**

### 2.5 ⚠ VERIFICACIÓN: `validate` VERDE, pero **1 test rojo** — diagnóstico completo

| | ANTES del merge | DESPUÉS del merge |
|---|---|---|
| `python scripts/catalog_store.py validate` | **0 errores** (7/7 ficheros) | **0 errores** (7/7 ficheros) |
| `pytest tests/test_catalog_store.py` | **29 passed** | **29 passed** |
| `pytest tests/test_catalog_resolver.py` | **61 passed** | **60 passed, 1 FAILED** |
| `pytest tests/test_s274_bloquesCD_prereg.py tests/test_s277_c1_p1_runner.py` | **181 passed** (7m34s) | **181 passed** (exit 0) |

**El fallo:** `test_catalog_resolver.py::test_roundtrip_muestra_de_canonicals`
→ `AssertionError: canonicals no detectados: ['S540(539) COSP']`.

**Diagnóstico (Protocolo 1 — verificado, no teorizado). Es un latente PRE-EXISTENTE destapado por
un desplazamiento de muestreo, no una regresión de contenido:**

1. El test muestrea `consumibles[::40]` — un **muestreo por zancada**. El merge sube los consumibles
   de **943 → 955** (+8 add, +3 promote, +1 de #25), así que la zancada cae en **otras 22 fichas**
   (22 entran, 22 salen). `S540(539) COSP` **entra** a la muestra por primera vez.
2. La fila `notifier:s540539-cosp` es **byte-idéntica antes y después** del merge (comparada contra
   `git show HEAD:data/catalog/products.jsonl`): el merge no la tocó. Ya era `activo`+`candidate:false`,
   o sea ya estaba indexada en el detector y **ya fallaba**.
3. **Ningún canonical de la muestra ANTERIOR falla con el catálogo NUEVO** (`fallos = []`) → no hay
   regresión sobre lo que antes estaba verde.
4. El conjunto de términos del detector crece **+29 / −0** — es monótono, así que el merge no puede
   quitar detecciones.

**Causa raíz del latente (mecánica verificada en `catalog_resolver._build`):** el detector construye
un fragmento por término troceando el término plegado en segmentos `[a-z]+|\d+` unidos por la clase
de separadores `[-\s/.+]*`. Esa clase **no incluye `(`, `)` ni `*`**, así que un modelo cuyo nombre
lleva esos caracteres no se detecta cuando el técnico lo escribe literalmente:

```
detect('manual del S540(539) COSP por favor') → []            ← paréntesis en la query
detect('manual del S540 539 COSP por favor')  → ['s540 539 cosp']   ← el mismo modelo, sin paréntesis, SÍ
detect('S540(539) COSP') → []      ·   detect('W*A-*C-I02') → []
```

**Población real del latente (barrido de los 955 consumibles): exactamente 5 canonicals no se
detectan por su propio nombre**, todos por metacaracteres:

| id | canonical_model | ¿lo introduce este merge? |
|---|---|---|
| `notifier:s540539-codp` | `S540(539) CODP` | no — pre-existente |
| `notifier:s540539-cosp` | `S540(539) COSP` | no — pre-existente (**el que rompe el test**) |
| `notifier:vrom-n` | `VROM-(n)` | no — pre-existente |
| `notifier:wa-c-i02` | `W*A-*C-I02` | sí (promote) — **compensado**: las 4 SKU `W*A` sí detectan |
| `notifier:wl-c-i02` | `W*L-*C-I02` | sí (add) — **compensado**: las 4 SKU `W*L` sí detectan |

Los 2 nuevos son el **placeholder wildcard declarado** en el informe final §3.3.1; el companion añade
precisamente las 8 SKU concretas para cubrirlos, y **las 8 detectan y resuelven** (§2.4).
Los 12 productos nuevos/promocionados detectan bien salvo esos 2 wildcards por diseño.

**NO se forzó nada** (ni `xfail`, ni tocar el test, ni tocar el detector): tocar la clase de
separadores del detector es zona de dolor (retrieval/identidad) y **afloja** el matching → Protocolo 3
(dúo) + gate de golds. Opciones para Alberto, con su coste:

| | Opción | Coste | Efecto |
|---|---|---|---|
| **A** *(recomendada primero)* | Convertir el round-trip muestreado `[::40]` en una aserción sobre **toda** la población con una **lista de exclusión explícita y documentada** de los 5 canonicals con metacaracteres | test-only, 0 cambio de conducta | CI **determinista** (hoy es una lotería que se re-tira con cada alta de catálogo) y el hueco queda **visible** en vez de aleatorio |
| **B** *(el arreglo de raíz)* | Añadir `(`, `)`, `*` a la clase de separadores del detector | código en zona de dolor → **dúo + gate de golds** | resuelve los 5; riesgo de FP por aflojar el patrón — hay que medirlo |
| **C** | Dejarlo | 0 | CI en rojo hoy y flaky por construcción mañana |

**Consecuencia operativa: el árbol NO está listo para commit hasta que se adjudique A o B.**
El merge en sí está verificado (validate 0 errores, `test_catalog_store.py` 29/29, resoluciones medidas).

### 2.6 Suite completa

`python -m pytest -q` sobre el árbol ya mergeado:

```
1 failed, 3227 passed, 5 skipped in 508.17s (0:08:28)
FAILED tests/test_catalog_resolver.py::test_roundtrip_muestra_de_canonicals
```

**El único rojo de toda la suite es el de §2.5.** Ningún otro test se mueve.

### 2.7 Efecto colateral MEDIDO que conviene que Alberto vea (no es del encargo, pero lo produce)

Los aliases descriptivos de s83 que colgaban de `unresolved:ms1|ms2|ms4` estaban **muertos** (destino
`candidate` ⇒ `build_indexes` no los consume). Al convertir esos ids en `redirect` hacia los nuevos
`morley:ms-*`, `_consumable()` sigue el redirect y **los despierta**:

```
'1 zona', 'Una Zona', 'Unidad de 1 zona' → morley:ms-1
'Dos Zonas'                              → morley:ms-2
'Cuatro Zonas'                           → morley:ms-4
```

De ellos, **2 entran además al DETECTOR** porque llevan dígito y esquivan la guarda anti-prosa de
`_resolvable_terms` (que excluye los `nombre-largo` SIN dígito):

```
detect('necesito el manual de la central de 1 zona') → ['1 zona']         ← NUEVO
detect('unidad de 1 zona')                            → ['unidad de 1 zona'] ← NUEVO
detect('una zona en la central') → []   ·  detect('panel de 2 zonas') → []   (sin dígito: filtrados)
```

Es exactamente la clase de FP que el guard s92 (`test_no_detecta_palabras_comunes_de_alias_nombre_largo`)
existe para frenar: descripciones de extracción usadas como detector en prosa.

- **Cota medida del riesgo:** ninguno de los **51 golds** de `evals/gold_answers_v1.yaml` dispara
  esos términos (barrido con `detect()` sobre las 51 preguntas → **0 golds tocados**).
- **No lo he tocado**: marcar esos 3 aliases como `candidate: true` (mecanismo que el contrato ya
  ofrece para "no QA-ado") sería una decisión de identidad que Alberto **no** adjudicó — su
  adjudicación #2 era sobre `MS-1/MS-2/MS-4`, no sobre bendecir "1 zona" como término de detector.
  **Recomendación:** marcarlos `candidate: true` con `provenance` explicando el motivo.

### 2.8 Lo que NO se tocó (declarado)

- `unresolved:vsn-rp1r-2plus` (canonical `VSN-RP1r-2PLUS`, `candidate`) sigue igual: `norm_token`
  lo separa de `VSN-RP1r-PLUS2` (`vsnrp1r2plus` ≠ `vsnrp1rplus2`) y la adjudicación #25 no habla de él.
- Los aliases `VSN-RP1r-PLUS` y `VSN-RP1r+` siguen apuntando a `notifier:rp1r-supra` (#25 nombra
  solo `PLUS2`), igual que `vendido_bajo: [... "Morley-IAS (VSN-RP1r+)" ...]` de `notifier:rp1r-supra`.
- El homónimo `RP1r` (`prefer:notifier:rp1r-supra`, 4 ids) **no** incorpora el producto nuevo: añadir
  un 5º id es decisión de identidad no adjudicada (y `resolve('RP1r')` no cambia).
- No se añadió ninguna fila a `relations.jsonl` (p.ej. `variant-of` RP1r-Supra↔VSN-RP1r-PLUS2):
  no está adjudicado.
- Los bloqueos de §5.3 del informe final (`DX` sin paraguas, `NFS Supra` candidate, el lote de
  `candidate` "lógicamente resueltos") siguen abiertos.
- **Los 2 ficheros companion (`s285_t3_*_companion.jsonl`) siguen en `data/catalog/`.** Son inertes
  (`catalog_store.FILES` sólo lista los 7 canónicos), pero **ya están fusionados** → conviene borrarlos
  en el commit que aterrice esto, para que nadie los re-fusione. El script de merge tiene guardas
  anti-doble-merge (aborta si el id/alias ya existe o si el alias #25 ya está re-apuntado).

---

## 3. Storage — rutas exactas de los 2 objetos (para borrar desde el dashboard)

Fuente: `SELECT` sobre **`_s285_t3_del_visual`** (la tabla de respaldo de `document_visual_assets`),
columna `storage_url`. Bucket **público `manual-images`**.

| # | documento | ruta del objeto (dentro del bucket `manual-images`) | sha256 del asset | HTTP hoy |
|---|---|---|---|---|
| 1 | `Docs Morley-IAS Lite&Plus - QR`<br>`3912b42a-26c9-46ea-b055-b24309083608` | `Morley Lite/Plus/Morley_Lite_Plus_Docs_Morley-IAS_Lite_Plus_-_QR_p001.jpg` | `c1dc3dd0f6243515358eb13682d8d0e0bacb04b7a8a7c0515c7568b7df71360a` | **200**, 90.452 B, `image/jpeg` |
| 2 | `Solicitud-asistencia-…-tecnica`<br>`b769abb0-6d2f-4003-be9b-e62099b5a03a` | `morley/morley_Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica_p001.jpg` | `be183eafab7697d8046da2054e80192d07b8d7af99034a533c5a177d246c3931` | **200**, 182.688 B, `image/jpeg` |

URLs completas (las que trae `storage_url`):

```
https://izooestgffgscdirkfia.supabase.co/storage/v1/object/public/manual-images/Morley Lite/Plus/Morley_Lite_Plus_Docs_Morley-IAS_Lite_Plus_-_QR_p001.jpg
https://izooestgffgscdirkfia.supabase.co/storage/v1/object/public/manual-images/morley/morley_Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica_p001.jpg
```

**Verificado antes de proponer el borrado:**

- **Ambos objetos siguen existiendo** (HEAD → 200) — el DELETE de Postgres no los tocó, como estaba
  declarado. Son **huérfanos**: `document_visual_assets` ya no tiene ninguna fila con esos
  `document_id` (0/0) **ni ninguna fila que referencie esas `storage_url`** (consulta directa por
  `storage_url` → 0 filas en las dos) ⇒ **borrarlos no rompe ninguna referencia viva**.
- Ojo con la ruta #1 en el dashboard: el `document_family` `Morley Lite/Plus` lleva una **barra**,
  así que en el explorador de Storage aparece como carpeta **`Morley Lite`** → subcarpeta **`Plus`**
  → el fichero. No es un typo.
- Si se quiere respaldo del binario antes de borrar, los dos son descargables hoy por esas URLs
  públicas (los sha256 de arriba permiten verificar la descarga).

**Alternativa a "borrar a mano":** son 2 objetos huérfanos de ~270 KB en un bucket público; dejarlos
es inocuo funcionalmente (nadie los referencia). El motivo para borrarlos es higiene/coherencia con
el borrado del documento, no un riesgo operativo.

---

## 4. Qué queda pendiente

1. **Adjudicar §2.5 (A o B)** — sin eso el árbol no está verde y no debería commitearse.
2. *(recomendado)* Adjudicar §2.7 — marcar `candidate: true` los aliases `1 zona` /
   `Unidad de 1 zona` / `Una Zona` / `Dos Zonas` / `Cuatro Zonas`.
3. **Gate de golds** (`scripts/test_bot_vs_gold.py` **con paridad completa de flags, DEC-157**):
   el informe final §8 declara que el merge del catálogo **no es inerte en producción**
   (`IDENTITY_RESOLVE` activo) ⇒ entra en el mismo gate que el re-tag. Golds en riesgo: `cat009`
   (toca #15/#20) + controles `hp009`/`hp018`. Baseline vigente **v3 (s284) 16 PASS / 20 PARCIAL / 3 FALLO**.
   *No ejecutado en esta lane: mandato $0 LLM.*
4. **Borrar los 2 objetos de Storage** (§3) y **retirar los PDF de origen** en disco/OneDrive (§1).
5. Al commitear: **borrar los 2 ficheros companion** ya fusionados (§2.8).
6. Sigue pendiente del informe final §9.6: **acta en `DECISIONS.md`/`HISTORY.md` del apply
   out-of-band de ZXe/ZXSe/NSRE24** (cambio de corpus sin traza, y **sin** tabla de respaldo
   `_s281_h0t3_backup`).
