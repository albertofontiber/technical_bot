# s282 QA-s83 — packet de revisión adversarial (zona corpus/identidad)

**Qué se revisa:** el QA instrumentado del activo s83 (commit 3358e1e, rama claude/s282-h0t2-qa):
`scripts/s282_qa_s83_instrument.py` + `evals/s282_qa_s83_report_v1.md` + result JSON + caches.
Es la PUERTA del Tramo 2 (backfill masivo de identidad, ~590 docs clase A): sus 879 AUTO_CLEAN
se aplicarían a DB; sus 89 CONFLICT van a adjudicación de Alberto. Un falso AUTO_CLEAN = etiqueta
mala aplicada a corpus; un instrumento laxo = el T2 hereda basura.

## Claims a tumbar
1. El pre-filtro determinista es recall-safe (ningún conflicto real puede caer en los 443 exactos).
2. La calibración (n=20, spot-check 4/5, discrepancia en dirección segura) justifica confiar 436
   AUTO_CLEAN al juez Haiku; el sesgo del juez es conservador (escala, no auto-aplica).
3. Los 89 CONFLICT son reales-o-conservadores (0 conflictos reales escapados a AUTO_CLEAN — la
   dirección peligrosa).
4. El matiz familia-vs-corrección (§6) previene sobrescribir etiquetas familia-genéricas
   gobernadas (convención T3 adjudicada) con miembros s83.
5. Los ejes advisory (idioma §4, marca/OEM §5) están correctamente separados del veredicto pm.
6. Determinismo 2× y trazabilidad del cache permiten re-auditar cada veredicto.

## Contexto canónico
evals/s281_h0_identity_census_report_v1.md (census/tramos) · evals/s281_h0t3_authority_contract_proposal_v1.md
(batch_attested_v1/LQAS) · docs/DECISIONS.md DEC-155(e) · data/catalog + config/manufacturers ·
evals/s83_document_models_final.jsonl (el activo). Ataca con filas CONCRETAS: elige N source_files
del JSON, re-deriva su veredicto a mano contra DB/chunks y compara. Severidad + veredicto global
(SÓLIDO | SÓLIDO-CON-CAMBIOS | RECHAZAR).
