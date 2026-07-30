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

# ══════ v2 SELLADO (dúo: Sol 7 [2 críticos] + Fable 9 [2 críticos] — convergen) ══════
## OBJETIVO+MÉTRICA (Sol-3, faltaba): reducir los retrieval-miss ESTABLES accionables de la
campaña (cat022#0/#1 · hp013#1 · hp012#3) midiendo en el instrumento v3.1 con cierre PAREADO
POR VÍA; el marcador final del objetivo sigue siendo bvg FALLO→0/PARCIAL≤10.
## V1 (ejecutable YA, con 6 cierres):
1. Entrada GEMELA en evidence_v2 — la unificación de paths MUERE (H2/Sol-4: v4 lleva
   query_alignment_min_terms>0 en 4/5 arquetipos y el selector de cards no recibe query →
   mataría en silencio las cards de la lane viva). 2. La card se DISEÑA para la celda μm
   (H1: ventana = PRIMER orden — max_cards:2 o 2ª faceta; con required_any [bit,incorporada]
   la única card cae en el span del BIT y los μm JAMÁS llegan al generador). 3. El matador
   de la CLASE = TEST de paridad en CI (todo arquetipo de query-config presente en cada
   card-config servida — la fragmentación es bidireccional y en parte deliberada, v5/cascade).
   4. El gate re-juega la RUTA DE SERVING completa (H4: collect→attest→append→serve — no una
   llamada suelta a _attest; el hueco incluía hidratación, capacidad y el corte por-card).
   5. Reconciliar el bloque serving muerto del yaml de la lane (H9: contrato-mentira que
   ningún código lee). 6. Gates: attest-ATTESTED con span μm servido + cat005 = 0 + smoke ×2.
## V3 (diseño antes de release): hipótesis de DELTA medible + presupuesto de latencia +
cohortes eficacia/regresión (Sol-6) · c1_v5 confirmado como mecanismo (H8: sin NO-GO
histórico — la exclusión fue «hasta que tenga su release gate», que es ESTO) · exige retirar
el env-leaf de Railway (fail-fast legacy_overrides) · hp012 doble-cubierto con V2 → solape de
atribución declarado · los 42 hyq nuevos = batch propio con receipts (H5: muta el índice
VIVO del canal retrieval — jamás de tapadillo).
## V2 (RE-SCOPED honesto: WORKSTREAM de diseño, no backfill): el contrato del RPC exige
linaje verified + identidad + ES + hash + cadena coherente (Sol-1) — 3 campos no lo
satisfacen; techo real = subset ES-activo (H3, lane ES-only); política de colisión-sha
necesaria (H6: PDFs byte-idénticos OEM comparten sha y el reingest enlaza por sha PRIMERO);
diseño de agrupación de revisiones (mercados, singletons) = su propio arco con census.
## AISLAMIENTO DE MEDICIÓN (Sol-2/H7, críticos): cierre pareado POR VÍA; el full se interpone
ENTRE V3 y el paste de V2 (jamás un solo full para 4 levers); el paquete de release de V3
declara que el baseline bvg 11/16/12 es PRE-P1. Plan de bisect declarado si algo regresa.
## Pregunta cero: RESPONDIDA con evidencia — las 3 vías son ortogonales al touch-set de P1
(cat022/hp012/15088SP fuera de la lista de 10; challenge de Alberto vindicado con datos).
