# s90 · F1a — PRE-QA con propuesta (evidencia corpus + web) · tu adjudicación en ~10-15 min

> Yo pre-adjudiqué cada ítem de la cola con evidencia; tú marcas ✅/✏️/❌. Nada se aplica sin tu
> marca. Evidencia: corpus congelado (fingerprint idéntico) + datasheets Honeywell/Morley públicos.

## P1 ⚡ ZXSe → `divergent: true` (la adjudicación que desbloquea MIE-MI-600)
**Evidencia:** corpus MIE-MI-600 p8: «ZX1Se, ZX2Se y ZX5Se tienen capacidad para **1, 1-2 y 1-5
lazos**»; datasheets Honeywell: PSU **4.2A (ZX1Se) vs 8.6A (ZX2Se/5Se)**, ZX5Se con 4 circuitos de
sirena; ZX10Se = 2×ZX5Se en red (tu gt). Divergencia estructural idéntica a ZXe (que tu gt ya
adjudicó true). **Propongo: true.**
**TU MARCA: [X] ✅ true [ ] ❌ false** — notas: __________

## P2 · Colisión `DX2`: **MERGE** — morley:dx2 → redirect a morley:dx2e
**Evidencia:** `product_model~dx2` en DB = **0 filas**; 'DX-2' = 0 chunks; 'DX2e' vive en
MIE-MC-520/MIE-MP-520 (serie Dimension). "DX2" no tiene existencia propia en el corpus — es
abreviatura/tipográfica de DX2e. **Propongo: merge (redirect) + alias DX2→dx2e se mantiene.**
**TU MARCA: [X] ✅ [ ] ❌ (son productos distintos)** — notas: Estoy de acuerdo con poner dx2 -> dx2e, pero ojo que según el manual también está la DX1e-20S, DX1e-40M , DX2e-40M, DX4e-40L, pero entiendo que las tienes identificadas

## P3 · Colisión `EXP`: productos DISTINTOS — renombrar y desambiguar
**Evidencia:** 'Mod.EXP' (tarjeta de lazo analógico) vive en MIE-MI-320/MIE-MI-450 (docs de
tarjetas ZX); MIW-EXP = expansor del sistema WIRELESS (MIW). NO son lo mismo. El token "EXP" a
secas es genérico-ambiguo. **Propongo:** canonical de `morley:exp` → **"Mod.EXP"** (el id se
mantiene); **quitar** el alias `EXP`→miw-exp; el token "EXP" queda SIN entrada (fail-open).
**TU MARCA: [X] ✅ [ ] ✏️** — notas: son productos diferentes. la Mod.EXP-060R es impresora de lazo periférico, mientras que Mod.exp del doc MIE-MI-320 es una tarjeta de lazo analógico.

## P4 · Colisión `MA-100`: **MERGE** — morley:mie-ma-100 → redirect a morley:ma-100
**Evidencia:** DB `product_model='MIE-MA-100'` para el doc `MIE-MA-100_01` — **MIE-MA-100 es el
CÓDIGO DEL MANUAL**, no el modelo (la clase metadata-inconsistency #49). La central convencional
8 zonas = MA-100. **Propongo: merge; canonical "MA-100"; el código de doc queda como alias
numero-de-parte.**
**TU MARCA: [ ] ✅ [X] ❌** — notas: Creo que la Morley ma-100 no existe (existe la ma-1000 pero es diferente). creo que el manual "MIE-MA-100_01" se refiere a la central "HRZ2-8" (doc MIE-Mi-100)

## P5 · Los 35 "conflictos alias↔alias" son en realidad **5 PARAGUAS nuevos** (patrón, no 35 decisiones)
La semilla puso términos-FAMILIA como alias de cada variante. Propongo crearlos como umbrellas:
| término(s) | miembros | divergent propuesto | base |
|---|---|---|---|
| `Dimension` / `serie Dimension` | dx1e, dx2e, dx4e | **true** (1/2/4 lazos) | docs MIE-*-520 |
| `DX Connexion` / `DXc` / `DXC` | dxc1, dxc2, dxc4 | **true** (1/2/4 lazos) | semilla + tu cat020 |
| `Vision LT` / `VSN LT` / `VSN 2-4-8-12` | vsn2-lt, vsn4-lt, vsn8-lt, vsn12-lt | **true** (2/4/8/12 zonas) | semilla |
| `Serie MPS` | mps15, mps25, mps50 | **true** (amperajes distintos) | semilla |
| `MCP5A` | mcp5a-p05, mcp5a-p06 | **unknown** (¿P05/P06 = variantes de qué? corpus: AM-8200N/AM-8100/D707 — sin claridad) | fail-open hasta F1 |
Los términos `Vision`/`VSN` a secas (mezclan LT/Plus/extinción) → **quedan fail-open** (demasiado ambiguos).
**TU MARCA: [X] ✅ los 5 [ ] ✏️ (di cuáles)** — notas: sobre mcpa-p05, aquí tienes lo que es (es un pulsador): https://www.morley-ias.es/documentacion/morley/manuales/D707%20issue%201%20-%20MI-MCPA5_Eng.pdf. https://buildings.honeywell.com/es/es/products/by-category/fire-life-safety/manual-call-points-pull-stations-and-panic-buttons/manual-call-points-pull-stations/mcp5a-indoor-callpoint

## P6 · Candidates de alto blast-radius del slice
- **umbrella `ZXR`** → zxr50a/zxr50p: **promover, divergent=true** (A=con teclado / P=sin — la
  diferencia ES la pregunta típica). **[X] ✅ [ ] ❌**
- **homónimo `ZX`** → mi recomendación: **DEJARLO candidate (fail-open) en v0** — "ZX" a secas es
  ambiguo entre 6+ familias; un clarify de 6 opciones es mala UX y el fail-open = comportamiento
  actual (seguro). Se revisa con datos del shadow-mode F2.5. **[ ] ✅ fail-open [X] ✏️ clarify** - notas: ¿no es más seguro que clarifique antes que intente adivinar a qué se refiere? o a qué te refieres con fail open?

## P7 · Los 24 productos candidate (found_by=single) — verificación mecánica contra corpus
- **PROMOVER (6, evidencia fuerte):** `mk-vsn` (42 hits content / 31 pm), `mkdx` (27/39), `mk50`
  (48/—; herramientas de config MK, como tu MK-ZX), `faast-lt` (180/258 — nota: es el rebrand
  Morley MI-FL20 de la serie FAAST LT; la relación cross-brand con notifier:faast-lt-200 se
  cablea en F1 bulk), `brh` + `mi-brh-pc-i` (pm-hits 5).
- **MANTENER candidate (18, evidencia floja ≤9 hits):** 020-891, 795-068/072-100, bgl, exp-004/b,
  exp-005, idr6a, kit-llave, mi-bgl-pc-i, mi-cmo, sib5485, vsn-ll, dx-connexion*, dxc-connexion*
  (*estos dos NO son productos — los absorbe el paraguas DXc de P5 → retirar como products).
**TU MARCA: [ ] ✅ [ ] ✏️** — notas: mk-vsn: (software). según un manual: "Programa de Configuración MK-VSN para centrales serie VISION PLUS de Morley-IAS y comunicador telefónico VSN-CRA"; mkdx: software también. según un manual "Programa de Configuración MKDX para centrales de la serie Dimension (DX) de Morley-IAS. El programa MKDX permite configurar los paneles DX1e, DX2e y DX4e."; mk50: software también "MK-50 SOFWARE DE CONFIGURACIÓN PARA CENTRAL ZX50". "faast-lt": ojo que faast-lt es una familia con varios subproductos. esto ya lo hemos tratado en el pasado y ya te clasifiqué manualmente los modelos, así que revísalo; brh: ojo que por un lado está el modelo "MI-BRH-PC-I" (Doc "D 1150-1 BRH Morley", marca morley), y por otro "NFXI-BSF-WCH" (Doc "D 1147-1 BRH Notifier"). sobre los de "mantener candidate": "020-891": parece un cable (https://www.morley-ias.es/index.php/component/zoo/item/020-891). 795-068/072-100: https://www.morley-ias.es/documentacion/morley/manuales/MIE-MI-600.pdf, página 15. bgl: parece un caso similar al de brh (modelo MI-BGL-PC-I de morley, pero ojo que notifier también tiene su versión "bgl" - el modelo NFXI-BF-WCS, según recogen en el enlace https://www.notifier.es/index.php/productos/sistemas-analogicos/item/bgl-pc-i02). exp-004/b: ni idea. exp-005: ni idea. kit-llave: parece referirse a "Kit de llave y bombín para centrales DX CONNEXION", pero no me la jugaría. mi-bgl-pc-i: lo que te he dicho de "bgl". "mi-cmo": según la web (https://buildings.honeywell.com/es/es/products/by-category/fire-life-safety/control-panels/accessories-and-parts/monitors/1-output-control-module-morley): "El módulo de salida de control MI-DCMO de Morley-IAS se utiliza con la serie ZX de paneles de control inteligentes para proporcionar un único circuito de alarma o un relé de forma C". sib5485: parece ser una referencia SKU del modelo "Módulo Interface RS-485 Ref: SIB5485". vsn-ll: ni idea. dx-connexion*, dxc-connexion*: OK


## P8 · Los 14 docs sin doc_map — propongo mapear los 4 claros
- `MIE-MU-315` → zxae/zxee (manual de USUARIO de la serie 310 — tu gt cubre MI/MP/MU-310 y MP-315)
- `MIE-MU-535rv001` → zx2e/zx5e (manual de usuario de la serie 530; tu gt cubre MP-535)
- `MIEMU520P` → dx1e/dx2e/dx4e (520 = serie Dimension; MIE-MP-520 contiene DX2e — corpus)
- `DXc_Manual variaciones de mercado` → dxc1/dxc2/dxc4 (el doc de tu cat020)
- El resto (FAQs, compatibilidad Notifier↔Morley, obsoletos, 996-130 FR) = docs corporativos/
  multi-marca → sin map en v0 (fail-open, no dañan).
**TU MARCA: [] ✅ los 4 [ ] ✏️** — notas: Todos OK salvo "MIEMU520P", que es un manual en portugués que no deberíamos contemplar

## Qué pasa tras tus marcas
Aplico las ✅/✏️ vía `catalog_store` (la puerta valida; provenance = `gt-s90-alberto-qa`), re-corro
validate + smoke + tests, y F1a queda CERRADO → arranca F1 bulk (31 marcas) con estas mismas reglas.

**Fuentes web:** [ZX5Se Data Sheet (Honeywell)](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/morley-ias-uk/hba-fire-ZX5Se-data-sheet.pdf) · [ZXSe Range Data Sheet](http://files.autospec.com/za/honeywell/datasheets/new/morley-fire/zx%20range%20datasheet.pdf) · [ZX1Se/ZX2Se/ZX5Se installation manual 996-174-000-1](https://fireandelectrical.co.uk/wp-content/uploads/2018/07/ZX-Series-Single-Install.pdf) · [Morley-IAS ZXSe (Honeywell Buildings)](https://buildings.honeywell.com/gb/en/products/by-category/control-panels/fire-control-panels/fire-alarm-control-panels/morley-ias-zxse-fire-alarm-control-panel)
