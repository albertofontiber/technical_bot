# s90 · F1a — QA-sample del slice Morley (para revisión de Alberto, ~15 min)

products: 136 (24 candidate) · aliases: 164 · umbrellas: 4 · homonyms: 2 · doc_map: 114 docs


## ⚡ ADJUDICACIÓN QUE DESBLOQUEA (fix dúo: antes estaba mal listada como 'confirmar')
- **`divergent` de ZXSe**: hoy `unknown` → la familia ZXSe está FAIL-OPEN (MIE-MI-600, 'el caso
  de más valor del lado ZX', queda invisible a la resolución hasta que adjudiques). ¿Las respuestas
  divergen entre ZX1Se/ZX2Se/ZX5Se/ZX10Se (→true) o son family-genéricas (→false)? [ ] true [ ] false

## Alto blast-radius cargado como ADJUDICADO (gt tuyo — confirma que sigue vigente)
- paraguas `ZXe` → zx1e/zx2e/zx5e (divergent=true) · `ZX2e/ZX5e` → ambos
- homónimo `RP1r` → prefer:notifier:rp1r-supra (D7; gold hp011)

## Pendiente de tu QA (candidate=true, NO se consume hasta promoción)
- umbrella `ZXR` → zxr50a/zxr50p (de family_scope semilla, sin gt)
- homónimo `ZX` → clarify (ambiguo entre familias, sin gt)
- 24 productos candidate (found_by=single) — lista en products.jsonl

## Gaps DECLARADOS del slice (no es F1 completa)
- `docrel.jsonl` VACÍO: los pares language-variant ES/EN y revision-of se pueblan en F1 bulk (detección vía languages[] de s83) — el slice no los cubre (dúo s90).
- Solo docs Morley (114/1170); la normalización free-text completa (592 family_scope) es F1 bulk.

## alias-no-consumible (sustantivo descriptivo / estándar de interfaz) → NO cargado (¿umbrella candidate?) (72)
- alias `detector de un canal`→morley:mi-flx-010
- alias `detector de dos canales`→morley:mi-flx-020
- alias `Central de 1 lazo`→morley:dxc1
- alias `Central DXc1`→morley:dxc1
- alias `Central de 2 lazos`→morley:dxc2
- alias `Central DXc2`→morley:dxc2
- alias `Central de 4 lazos`→morley:dxc4
- alias `Central DXc4`→morley:dxc4
- alias `Módulo de control`→morley:miw-cmo
- alias `Gateway`→morley:miw-int
- alias `pasarela`→morley:miw-int
- alias `Módulo monitor`→morley:miw-mmi
- alias `Sirena-R`→morley:miw-snd
- alias `Sirena óptico-acústica`→morley:miw-ss
- alias `MÓDULO MONITOR PARA ZONAS CONVENCIONALES MI-DCZM`→morley:mi-dczm
- alias `módulo de zonas convencionales MI-DCZM`→morley:mi-dczm
- alias `Módulo Interfaz de Seis Zonas Convencionales`→morley:mi-cz6
- alias `Módulo de Control MI-CR6`→morley:mi-cr6
- alias `módulo MI-CR6`→morley:mi-cr6
- alias `Módulo de control con 6 circuitos de salida supervisada`→morley:mi-sc6
- alias `Módulo de Control MI-SC6`→morley:mi-sc6
- alias `Módulo Monitor MI-IM10`→morley:mi-im10
- alias `Módulo de supervisión MI-MM3E-S2`→morley:mi-mm3e-s2
- alias `Central (8 zonas convencional)`→morley:mie-ma-100
- alias `Tarjeta de relé de 8 salidas`→morley:nfs8rel
- … (+47)

## conflicto alias↔alias (mismo token, productos distintos) → adjudicar (35)
- `MCP5A`: morley:mcp5a-p05 vs morley:mcp5a-p06
- `MCP5A models`: morley:mcp5a-p05 vs morley:mcp5a-p06
- `serie DX Connexion`: morley:dx-connexion vs morley:dxc1
- `serie DX Connexion`: morley:dx-connexion vs morley:dxc2
- `serie DX Connexion`: morley:dx-connexion vs morley:dxc4
- `MIE-MA-100_01`: morley:ma-100 vs morley:mie-ma-100
- `MIE-MA-100_01_C`: morley:ma-100 vs morley:mie-ma-100
- `centrales de la serie Dimension (DX)`: morley:dx1e vs morley:dx2e
- `serie Dimension`: morley:dx1e vs morley:dx2e
- `centrales de la serie Dimension (DX)`: morley:dx1e vs morley:dx4e
- `serie Dimension`: morley:dx1e vs morley:dx4e
- `Serie MPS`: morley:mps15 vs morley:mps25
- `Serie MPS`: morley:mps15 vs morley:mps50
- `VSN 2-4-8-12`: morley:vsn12-lt vs morley:vsn2-lt
- `Vision LT`: morley:vsn12-lt vs morley:vsn2-lt
- `Vision-LT`: morley:vsn12-lt vs morley:vsn2-lt
- `VSN LT`: morley:vsn12-lt vs morley:vsn2-lt
- `VSN 2-4-8-12`: morley:vsn12-lt vs morley:vsn4-lt
- `Vision LT`: morley:vsn12-lt vs morley:vsn4-lt
- `Vision-LT`: morley:vsn12-lt vs morley:vsn4-lt
- `VSN LT`: morley:vsn12-lt vs morley:vsn4-lt
- `VSN 2-4-8-12`: morley:vsn12-lt vs morley:vsn8-lt
- `Vision LT`: morley:vsn12-lt vs morley:vsn8-lt
- `Vision-LT`: morley:vsn12-lt vs morley:vsn8-lt
- `VSN LT`: morley:vsn12-lt vs morley:vsn8-lt
- … (+10)

## alias-no-consumible (término-familia/marca genérico) → NO cargado (¿umbrella candidate?) (16)
- alias `DXC`→morley:dxc-connexion
- alias `DXc`→morley:dx-connexion
- alias `DX`→morley:dx1e
- alias `DX`→morley:dx2e
- alias `DX`→morley:dx4e
- alias `DX`→morley:dx1e-20s
- alias `DX`→morley:dx1e-40m
- alias `DX`→morley:dx2e-40m
- alias `DX`→morley:dx4e-40l
- alias `VSN`→morley:vsn2
- alias `Vision`→morley:vsn2
- alias `VSN`→morley:vsn4
- alias `Vision`→morley:vsn4
- alias `Vision`→morley:vsn-12-plus
- alias `Vision`→morley:vsn-4-plus
- alias `Vision`→morley:vsn-8-plus

## etiqueta-no-producto (término-familia/marca genérico) → NO cargada (1)
- `DXc` (doc DXC-puedo-cambiar-la-clave-de-nivel-3)

## alias-no-consumible (combinada/familia (contiene separador)) → NO cargado (¿umbrella candidate?) (16)
- alias `DXc2/4`→morley:dxc2
- alias `VNS8/12 LT`→morley:vsn12-lt
- alias `VSN8/12-LT`→morley:vsn12-lt
- alias `Vision 8/12LT`→morley:vsn12-lt
- alias `VNS2/4 LT`→morley:vsn2-lt
- alias `VSN2/4-LT`→morley:vsn2-lt
- alias `Vision 2/4LT`→morley:vsn2-lt
- alias `VNS2/4 LT`→morley:vsn4-lt
- alias `VSN2/4-LT`→morley:vsn4-lt
- alias `Vision 2/4LT`→morley:vsn4-lt
- alias `VNS8/12 LT`→morley:vsn8-lt
- alias `VSN8/12-LT`→morley:vsn8-lt
- alias `Vision 8/12LT`→morley:vsn8-lt
- alias `MORLEY IAS / VISION VSN-PARK`→morley:vsn-park
- alias `VSN 2 y 4`→morley:vsn2
- alias `VSN 2 y 4`→morley:vsn4

## etiqueta-no-producto (sustantivo descriptivo / estándar de interfaz) → NO cargada (4)
- `Llave opcional 795-098` (doc DXc_Manual de configuracion)
- `RS-232` (doc MIE-MI-330)
- `RS-485` (doc MIE-MI-390)
- `Impresora opcional` (doc MIE-MP-520rv04)

## etiqueta-no-producto (combinada/familia (contiene separador)) → NO cargada (1)
- `EXP/SS` (doc MIE-MI-530rv001)

## colisión alias↔canonical (¿mismo producto? adjudicar merge) (2)
- alias `EXP`→morley:miw-exp vs canonical de `morley:exp`
- alias `DX2`→morley:dx2e vs canonical de `morley:dx2`

## doc Morley SIN entrada en doc_map (0 productos mapeables) → revisar (14)
- `996-130-000-3 Manuel d'utilisation ZX_hlsi`
- `Compatibilidad-entre-equipos-Notifier-y-Morley`
- `DXC-No-puedo-comunicar-con-la-central`
- `DXC-puedo-cambiar-la-clave-de-nivel-3`
- `DXc_Manual variaciones de mercado`
- `Docs Morley-IAS Lite&Plus - QR`
- `Docs Morley-IAS Max - QR`
- `MIE-MI-330`
- `MIE-MI-390`
- `MIE-MU-315`
- `MIE-MU-535rv001`
- `MIEMU520P`
- `Morley-Se-pueden-pasar-programaciones-de-ZX-y-Dimension-a-Co`
- `Relacion-de-producto-obsoleto-de-Morley-IAS-by-Honeywell`