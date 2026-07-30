# TU BANDEJA (30-jul, consolidada) — decisión + mi propuesta + fichero

## A. ADJUDICACIONES DE GOLD/CORPUS (bloquean conversiones concretas)
**A1. cat008 — gold anclado a fuente errónea** → `evals/s287_cat008_adjudicacion_packet_v1.md`
   (renders en evals/s287_renders/). PROPUESTA: aplicar A-D (core #4 al mapping oficial,
   re-alcance del 47kΩ, retirar #7, nota CONFLICTO-FUENTE autoridad-manda). Convierte su
   FALLO sin tocar pipeline. Yo lo aplico vía gold_store con tu OK.
**A2. Dedup near-dup — 24 pares** → `evals/s287_p2_dedup_adjudicacion_packet_v1.md` +
   `evals/s287_p2_dedup_apply_v1.sql` (TU PASTE; 120 marcas comentadas, casilla por par,
   8 guards pre-validados). PROPUESTA: aprobar los 24 (los 179 dudosos ya están protegidos
   por diseño). Convierte cat010 y limpia slots corpus-wide.
**A3. Ticket corpus OCR/metadata** (no urgente, con tu próximo lote): re-extracción de
   I56-2006-004 (3/17 chunks INVIERTEN una instrucción de cableado) + metadata falsa del
   doc «manual IS MA1» (Detnov espurio, pm 'VIA-28V') + check de fidelidad en docs
   textlen==0. PROPUESTA: lote de corpus propio, yo preparo el staging.

## B. VETOS DISPONIBLES (ya ejecutado con declaración; revierte una línea)
**B1. Regla corpus-aware (P1)** — committeada; repara el filtro de familia corpus-wide
   (32 familias). Cambia la demo AL MERGEAR. PROPUESTA: mantener.
**B2. Enmiendas del lever de faceta** — pre-registro {cat005,cat022} + `version` fuera del
   required_any (homógrafo de norma cazado por el control). PROPUESTA: mantener; el STOP
   sigue de árbitro. → traza en `evals/s287_facet_lever_design_brief_v1.md`.

## C. RUMBO (cuando quieras, no bloquean el trabajo de hoy)
**C1. hp012+hp013 = clase seed-proximity** (DEC-164c): PROPUESTA: aceptar como residual
   declarado del objetivo POR AHORA (el lever de radio toca parámetros sellados de la lane;
   re-visitar tras cerrar etapas 2-3). Alternativa: diseñarlo ya (~1 sesión).
**C2. cat022 y el objetivo**: si el smoke del lever de faceta confirma conversión,
   PROPUESTA: cat022 SALE del techo y entra al objetivo (FALLO→0 pasa a exigirlo).
**C3. PR nueva** de la rama (s287 acumulado) cuando cierre la re-medición → tu merge.

## D. HERENCIA s286 AÚN ABIERTA (de tu paquete anterior, sin urgencia)
**D-ONs**: lote Railway (guard hp018 ×2 · conducta ×3 · telemetría ×3 + INTERNAL_TELEGRAM_IDS)
   tras el merge — runbook con sonda/rollback: `evals/s286_runner_e2e_runbook_v1.md`.
**D-restos**: matriz RGPD · firma T1-lineage (hp012) · 2 huérfanos Storage (opcional) ·
   patch gemelos EN (D2, dijiste OK — entra en el lote A3).
