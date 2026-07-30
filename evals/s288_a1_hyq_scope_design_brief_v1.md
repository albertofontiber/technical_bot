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

# ══════ v2 SELLADO (dúo: Sol 6 [2 críticos] + Fable 7 [1 crítico] — convergen) ══════
## RE-SCOPE HONESTO: A1 = HARDENING DE CORRECCIÓN; la EFICACIA es gate de A2
Cruce de críticos: sha-verificado-ONLY (Sol-2: placeholder-por-id DEBILITABA el binding — cae)
× los docs de la cohorte llevan sha placeholder ⇒ **la cohorte no es servible pre-A2**. GO de
A1 = SOLO gates de corrección (exclusión, paridad, no-regresión); la eficacia {cat010#0,
hp012#3} se mide en A2 cuando sus docs ganen sha real. hp013 corre NO-gating como baseline
(auto-contenido: sin surrogate PWR-R + sin arquetipo que la query matchee — doble bloqueo).
## PIEZAS v2
1. **Fork de input DECIDIDO** (crítico compartido: resolved_documents = {id, source_file} sin
   sha/status, esquema pineado): la lane hace **1 GET acotado a `documents`** por el set de
   document_id del scope (1-3 docs/query; dentro del cap de 6 requests — el fork RPC-nueva es
   territorio A2 y el snapshot-catálogo es la clase status-stale conocida). Fail-closed a
   descartar-parent en error. Contrato del resolver INTOCADO (su extensión versionada = A2).
2. **Sha-verificado-only**: parent servible ⇔ doc activo + sha real + extraction_sha ==
   source_pdf_sha (el binding canónico SIN adaptaciones). Placeholder ⇒ parent fuera, con
   razón trazada. Techo pre-A2 declarado (= los docs sha-reales de hoy).
3. **Scope a nivel CANDIDATO** (Sol-3/F2): el filtro de identidad corre ANTES de que la
   selección greedy consuma SOURCE/PARENT_LIMIT. Residual DECLARADO: chunks_v2_hyq no tiene
   document_id (migración 013) → la navegación primaria sigue name-scoped por construcción;
   el fix de raíz (columna document_id en hyq) va al lote A2 con su migración; mientras,
   trace de parents-rechazados-por-identidad (anti starvation silenciosa).
4. **Configs ×3 con paridad extendida** (F3): arquetipos nuevos en v1 (lista, parser distinto
   — la extensión del test de paridad NO es mecánica) + gemelas en v4 Y v2 (v4 es el match
   VIVO de structural) + test de inertness (v3-retrieval NO emite los ids nuevos).
5. **Anti-tuning AUDITABLE** (Sol-4/F4): diff de asignación de arquetipos PRE-REGISTRADO
   sobre los 51 golds + inventario de clases como artefacto nombrado + controles negativos de
   sobre-disparo y precedencia first_match (las dos lecciones-STOP de s287, preventivas).
6. **Probe con freeze**: fingerprints pre/post (corpus + chunks_v2_hyq + documents) + assert
   no-compatibility para la cohorte + receipts de la propia lane. Test de ESTADO MIXTO de la
   transición A2 (F7: sha real en documents con chunks aún backfill no debe matar en silencio).
## PLAN: Sol focused sobre ESTE bloque (tiering de ambos lados) → build → gates de corrección
→ A2 (autoridad documental: shas reales + lineage + language + document_id en hyq + census).
