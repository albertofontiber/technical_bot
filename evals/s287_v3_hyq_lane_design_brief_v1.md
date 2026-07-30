# s287 — V3: lane hyq doc-scoped (CANONICAL_HYQ_COVERAGE) — diseño-delta pre-dúo

## OBJETIVO + MÉTRICA
Servir post-rerank, dentro del doc resuelto, los hechos cuyo surrogate hyq ya existe (70.126
filas vivas, 88-94% cobertura en docs diana). **Cohorte de EFICACIA pre-registrada** (delta
esperado, exigencia Sol-6): {cat010#0 «24V dc» (surrogate casi-literal verificado; rerank-miss
estable ×4 que sobrevivió al dedup — competencia intra-doc), hp013#1 «PWR-R» (3 hyq en p12,
ninguno PWR-R: parcial), hp012#3 «792» (surrogate literal en b162a7eb)}. GO = ≥2/3 servidos
(reaches_gen vía lane) sin regresión; métrica final = factlevel v3.1 estable + bvg de cierre.
**Cohorte de REGRESIÓN**: 93 OK-estables-N2 (composición determinista) + centinelas 7.

## MECANISMO (confirmado sin NO-GO histórico — H8)
`coverage_c1_v5`: CANONICAL_HYQ_COVERAGE promovido a profile-owned (release_profiles: perfil
nuevo atómico, patrón v3→v4) + retirada del env-leaf de Railway EN EL MISMO paquete (fail-fast
legacy_overrides). La lane (doc_scoped_hyq_coverage) sirve chunks PADRE reales, nunca prosa
hyq. hp012 doble-cubierto con V2 → solape de atribución DECLARADO: V3 se mide ANTES de
cualquier paste de V2 (aislamiento Sol-2/H7).

## PRESUPUESTO DE LATENCIA (exigencia Sol-6)
La lane gasta hasta 6 GETs / 5s techo (doc_scoped_hyq_coverage.py:35-36). Gate de latencia:
p50/p95 del turno con lane ON vs OFF sobre los 39 (retrieve+coverage, sin LLM = $0); STOP si
p95 añade >1.5s (el precedente enunciados A3 aceptó +725ms p50 — DEC-090 — como banda).

## GATES (orden barato-primero)
1. Probe determinista de la lane sobre la cohorte de eficacia ($0, seeds congelados +
   fetcher real): ¿ancla los 3? ¿qué sirve coverage_context_content?
2. Latencia 39 ON-vs-OFF ($0 LLM).
3. Composición: sweep de appends sobre los 39 (¿dónde más dispara? — presupuesto MAX_APPENDED
   compartido: verificar que no desplaza appends de structural/document-local — la clase
   hp002:r1).
4. Smoke dirigido ×2 (cohorte + cat005 control) — pagado, ~$3.
5. bvg K=3 de golds tocados SOLO si 1-4 verdes.

## FUERA DE SCOPE (declarado)
Los 42 hyq faltantes de 15088SP (H5: batch propio con receipts — muta índice vivo del canal
retrieval; NO va de tapadillo en esta vía). El perfil v5 llega a Alberto como PAQUETE de
release (con la declaración baseline-pre-P1) — su click, no el mío.

## RIESGOS
1. La lane depende de catalog_resolver.resolve_query para el scope → interactúa con la regla
   P1 (ya activa): el probe lo mide, no se asume. 2. Presupuesto de appends compartido (gate
   3). 3. Si la cohorte da 0-1/3 → NO-GO honesto y la vía muere sin gate-shopping (los hechos
   pasan al residual declarado con su mecanismo). 4. Latencia (gate 2).
