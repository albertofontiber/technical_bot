# s90 · F1a — QA-sample del slice Morley (para revisión de Alberto, ~15 min)

products: 140 (26 candidate) · aliases: 256 · umbrellas: 4 · homonyms: 2 · doc_map: 126 docs


## Alto blast-radius cargado como ADJUDICADO (gt tuyo — confirma que sigue vigente)
- paraguas `ZXe` → zx1e/zx2e/zx5e (divergent=true) · `ZXSe` → los 4 Se (unknown) · `ZX2e/ZX5e` → ambos
- homónimo `RP1r` → prefer:notifier:rp1r-supra (D7; gold hp011)

## Pendiente de tu QA (candidate=true, NO se consume hasta promoción)
- umbrella `ZXR` → zxr50a/zxr50p (de family_scope semilla, sin gt)
- homónimo `ZX` → clarify (ambiguo entre familias, sin gt)
- 26 productos candidate (found_by=single) — lista en products.jsonl

## Gaps DECLARADOS del slice (no es F1 completa)
- `docrel.jsonl` VACÍO: los pares language-variant ES/EN y revision-of se pueblan en F1 bulk (detección vía languages[] de s83) — el slice no los cubre (dúo s90).
- Solo docs Morley (114/1170); la normalización free-text completa (592 family_scope) es F1 bulk.

## etiqueta-no-producto (familia/combinada) → NO cargada (2)
- `DXc` (doc DXC-puedo-cambiar-la-clave-de-nivel-3)
- `EXP/SS` (doc MIE-MI-530rv001)

## colisión alias↔canonical (¿mismo producto? adjudicar merge) (2)
- alias `EXP`→morley:miw-exp vs canonical de `morley:exp`
- alias `DX2`→morley:dx2e vs canonical de `morley:dx2`