# s282 — packet de revisión adversarial del PAQUETE DE APLICACIÓN T2 (gate final pre-firma)

**Qué se revisa (commit 33a8c7c):** el paquete completo que autorizaría la PRIMERA escritura
masiva a DB de la campaña H0: `scripts/s282_qa_s83_regate_v3.py` (guard de plausibilidad de
categoría) + `evals/s282_qa_s83_attestation_v1.md` (attestation con las 3 seeds LQAS + SQL
fill-only plantilla) + `evals/s282_qa_s83_result_v3.json`. Tras esta ronda solo queda la firma
de Alberto y su paste del SQL.

## Claims a tumbar
1. El guard (doc_type clase-corta sobre >30 chunks → adjudicate) es de RAÍZ, no un parche a las
   3 filas Securiton; sus umbrales no dejan clase implausible dentro del auto-apply.
2. La cohorte atestada (533 doc_type fills + 301 language-singleton, pm JAMÁS) tiene 3 draws
   LQAS coherentes con el contrato batch_attested_v1 (n=59, 0-defectos aceptación; historia
   282→592-PARADA→593 honesta, sin seed-shopping: el re-scope entre draws está justificado por
   defectos CAZADOS, no por conveniencia).
3. El SQL plantilla es fill-only NULL-guarded reversible (ningún UPDATE puede sobrescribir un
   valor existente ni escribir fuera de la cohorte).
4. La dirección residual peligrosa (un fill INCORRECTO dentro de los 533+301 no muestreados)
   queda acotada por LQAS <5%@95% — y el expediente lo declara como riesgo residual, no como cero.

## Contexto
evals/s281_h0t3_authority_contract_proposal_v1.md (batch_attested_v1) · las 2 adjudicaciones
de dúo previas (s282_qa_s83_duo_r1 + los YAML) · draws: lqas_sample_v1 / lqas_redraw_v1 /
lqas_draw3_bundle. Ataca con evidencia ejecutada (filas concretas, SQL contra el JSON).
Severidad + veredicto (SÓLIDO | SÓLIDO-CON-CAMBIOS | RECHAZAR).
