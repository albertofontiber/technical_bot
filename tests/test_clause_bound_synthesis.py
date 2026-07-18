import pytest
from src.rag.clause_bound_synthesis import assemble_claim_blocks, validate_claim_block, writer_payload
from src.rag.evidence_units_v2 import EvidenceUnitV2
def unit(uid, fragment, text): return EvidenceUnitV2(uid,fragment,f"c{fragment}","contiguous",((0,len(text)),),text,"sha")
def test_writer_payload_exposes_only_allowed_units():
    value=writer_payload("¿Qué valor?","valor",[unit("E1",2,"Valor 18 kΩ")])
    assert "E1" in value and "18 kΩ" in value and "gold" not in value
def test_validator_rejects_unknown_ids_and_model_citations():
    with pytest.raises(ValueError,match="invalid source"):
        validate_claim_block({"claims":[{"text":"El valor es 18 kΩ.","unit_ids":["BAD"]}]},{"E1"})
    with pytest.raises(ValueError,match="claim text"):
        validate_claim_block({"claims":[{"text":"El valor es 18 kΩ [F2].","unit_ids":["E1"]}]},{"E1"})
def test_assembly_is_ordered_lossless_and_derives_citations():
    units=[unit("E1",2,"a"),unit("E2",3,"b")]
    plan=[{"label":"a","unit_ids":["E1"]},{"label":"b","unit_ids":["E2"]}]
    blocks=[{"obligation_index":1,"value":{"claims":[{"text":"Primer dato exacto.","unit_ids":["E1"]}]}},
            {"obligation_index":2,"value":{"claims":[{"text":"Segundo dato exacto.","unit_ids":["E2"]}]}}]
    answer,receipt=assemble_claim_blocks("q",plan,blocks,units)
    assert answer=="- Primer dato exacto. [F2]\n\n- Segundo dato exacto. [F3]"
    assert receipt["all_obligations_assembled_once"] is True
def test_assembly_rejects_missing_block():
    with pytest.raises(ValueError,match="every obligation"):
        assemble_claim_blocks("q",[{"label":"a","unit_ids":["E1"]}],[],[unit("E1",1,"a")])
