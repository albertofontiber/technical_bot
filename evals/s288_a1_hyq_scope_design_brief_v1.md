# s288 — A1: hardening de scope de la lane hyq doc-scoped (pre-dúo)
Workstream A (adjudicado por Alberto 30-jul: infraestructura ANTES de etapa 3 — upstream-first).
A1 hace la lane SEGURA; A2 = autoridad documental (V2); A3 = perfil c1_v5. La lane sigue OFF
hasta A3 — A1 no cambia serving.

## OBJETIVO + MÉTRICA
Que `doc_scoped_hyq_coverage` sea doc-scoped DE VERDAD: scope por identidad resuelta
(document_id + extraction_sha256 + lifecycle activo), consumiendo `resolved_documents` que hoy
DESCARTA (crítico Sol: filtra solo por source_file → puede hidratar superseded o colisión de
nombre). MÉTRICA: tests de exclusión (superseded/colisión/sha-mismatch) + probe determinista de
la cohorte {cat010#0, hp012#3} con lane invocada directa (defaults de producción) + 0 regresión
en la suite.

## PIEZAS
1. **Scope real**: la lane recibe/usa `resolved_documents` (id+sha+status del retriever/resolver)
   y valida CADA parent hidratado contra esa identidad — el patrón del binding de document_local
   (`extraction_sha256 == source_pdf_sha256`-class) adaptado a lo que la lane puede exigir HOY
   (con 744 shas placeholder `backfill:`, el check de sha es progresivo: exige igualdad SOLO si
   el doc tiene sha real; si placeholder → exige document_id+status; NUNCA name-only). Fail-closed
   por parent (se descarta el parent, no la lane).
2. **Arquetipos desde TAXONOMÍA** (F1, anti instrument-tuning): extender
   `config/retrieval_facets_v1.yaml` con las CLASES ausentes (alimentación/power-supply;
   sustitución con conjugaciones vía stem_prefixes que v1 no usa aún) — diseñadas desde el
   inventario de clases de pregunta (query_facets + arquetipos de v3 como referencia), la cohorte
   solo VALIDA. Cards: los arquetipos nuevos necesitan entrada en la config de cards de ESTA lane
   (F6: STRICT_ALIGNED v4) → entradas gemelas + **extender el test de paridad por-lane** al par
   (v1-match → v4-cards) de esta lane.
3. **Gates**: (a) tests de exclusión de scope (superseded doc NO hidrata; colisión source_file NO;
   sha-mismatch NO; activo con placeholder SÍ por id+status); (b) probe determinista cohorte:
   cat010#0 y hp012#3 anclan y `coverage_context_content` sirve el valor (hp013#1 QUEDA FUERA del
   GO — doble-bloqueado F2, será diana de A2/hyq-batch futuro — declarado, no gate-shopping);
   (c) paridad por-lane verde; (d) suite completa.

## FUERA DE SCOPE: promoción/perfil (A3) · presupuesto de latencia con SLO propio y reps (A3,
con la lane ya segura) · surrogates nuevos (batch H5) · V2 (A2). Riesgos: los del spec V3
rechazado aplican en A3, no aquí — A1 es código de lane + configs + tests, sin release.
