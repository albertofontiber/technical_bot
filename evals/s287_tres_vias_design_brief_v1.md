# s287 — LAS TRES VÍAS del residual de retrieval (diagnóstico triple, pre-dúo)
Base: informe del diagnóstico (vía1 config v2↔v4 desalineada; vía2 lineage-backfill 6/1169;
vía3 lane hyq OFF con 70k surrogates vivos). Challenge de Alberto: «me resisto al techo» — 3/3.

## V1 — cat022 (config-only, YO ejecuto post-dúo)
Entrada gemela `variant_differentiation` en `config/evidence_coverage_facets_v2.yaml` (las
cards; el gate ya está en v4). ALTERNATIVA raíz a evaluar por el dúo: unificar
`evidence_card_config_path` con `evidence_match_config_path` (structural_neighbor_coverage.py
:190) — mata la CLASE de desalineamiento (cualquier arquetipo futuro añadido solo a v3+v4
pasa el gate y no apendiza JAMÁS — defecto estructural, 3ª config divergente del día).
Caveat declarado: la card de v4 para 74cc9f95 sirve el span del BIT, no los μm — la selección
de ventana es 2º orden; el gate mide si #0/#1 llegan de verdad. + cerrar el hueco del
instrumento de gates: gate (b) debe cruzar _attest (el PASS offline no midió serving).
GATES: probe attest de cat022 (ATTESTED + span correcto) · control cat005 sigue 0 · smoke ×2.

## V2 — backfill Fase-3 de documents (pase de DATOS → paste de Alberto)
sha real del PDF + revision_lineage_id + language para los ~996 activos (hoy: 744 sha
placeholder, 1160 sin lineage). Sube el techo de la lane document-local de 6→~996 docs.
Diseño: census→staging→paste (patrón establecido); riesgos: lineage mal asignado activa
lecturas de supersedes en runtime (¡document_local SÍ lo lee!) — el linaje de #9/#22 del
dedup ya pobló FK... NO: variante A no pobló lineage_id (verificado) — pero ESTE pase SÍ lo
haría → interacción declarada, orden: primero backfill sha+language (inocuo), lineage con
su propio gate. + CANDIDATE_LIMIT=64 (hp012 da 65 hits) → revisar tope en el diseño.

## V3 — lane hyq doc-scoped (flag de release → decisión de Alberto)
`CANONICAL_HYQ_COVERAGE` promovido a profile-owned + perfil `coverage_c1_v5`. Los datos ya
existen (70k, ~2.8/chunk). Coste runtime: hasta 6 GETs/5s por query — medir latencia en gate.
Perfil nuevo = cambio de release sellada → paquete para Alberto con el gate pasado.
Complemento barato: generar hyq para los 42 chunks sin cobertura de 15088SP (incl. f03d3ae4).

## ORDEN: V1 (config, ya) → V3 (gate+paquete) → V2 (diseño census; el paste, cuando Alberto).
Los 3 con centinelas + cohorte estable + smokes dirigidos; full de cierre DESPUÉS de los tres.
