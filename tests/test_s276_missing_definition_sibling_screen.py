import copy
import json
from pathlib import Path

import yaml

from scripts.s276_missing_definition_sibling_screen import (
    BUILD_PATH,
    CARD_FIELD,
    COHORT_PATH,
    DESIGN_PATH,
    GATE_PATH,
    MAX_CARD_CHARS,
    PREREG_PATH,
    RESULT_PATH,
    RESULT_ROWS_PATH,
    ROOT,
    _sha256_lf,
    attest_reference,
    derive_missing_definition_sibling_cards,
    has_exact_reference_receipt,
    parse_definition_blocks,
)


def _card(candidate_id: str, content: str, start: int, end: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "start": start,
        "end": end,
        "quote": content[start:end],
        "exact_source_span_validated": True,
    }


def _candidate(content: str, start: int, end: int) -> dict:
    candidate_id = "fresh-reference"
    return {
        "id": candidate_id,
        "content": content,
        "coverage_cards": [_card(candidate_id, content, start, end)],
    }


def test_parser_accepts_only_contiguous_top_level_definition_lists():
    content = "Intro\n\n* Campo alfa: valor uno\n\n* Campo beta: valor dos\n\n## Fin"
    blocks = parse_definition_blocks(content)

    assert len(blocks) == 1
    assert [item.label for item in blocks[0].items] == ["Campo alfa", "Campo beta"]


def test_full_selected_item_yields_the_single_omitted_sibling():
    content = "* Campo alfa: valor uno\n\n* Campo beta: valor dos"
    first_end = content.index("\n")
    candidate = _candidate(content, 0, first_end)

    cards = derive_missing_definition_sibling_cards(candidate)

    assert len(cards) == 1
    assert cards[0]["quote"] == "* Campo beta: valor dos"
    assert cards[0]["local_semantic_validated"] is False
    assert cards[0]["exact_source_span_validated"] is True


def test_truncated_selected_item_still_yields_omitted_sibling():
    content = (
        "* Campo alfa: valor uno con una descripción suficientemente larga\n\n"
        "* Campo beta: valor dos"
    )
    clipped_end = content.index(" suficientemente")
    candidate = _candidate(content, 0, clipped_end)

    cards = derive_missing_definition_sibling_cards(candidate)

    assert len(cards) == 1
    assert cards[0]["quote"] == "* Campo beta: valor dos"


def test_all_siblings_already_covered_is_clean():
    content = "* Campo alfa: valor uno\n\n* Campo beta: valor dos"
    split = content.index("\n")
    second = content.index("* Campo beta")
    candidate_id = "all-covered"
    candidate = {
        "id": candidate_id,
        "content": content,
        "coverage_cards": [
            _card(candidate_id, content, 0, split),
            _card(candidate_id, content, second, len(content)),
        ],
    }

    assert derive_missing_definition_sibling_cards(candidate) == []


def test_heading_prose_table_and_indentation_boundaries_fail_closed():
    separators = (
        "\n\n## Otro registro\n\n",
        "\n\nTexto fuera del registro.\n\n",
        "\n\n| Campo | Valor |\n| --- | --- |\n\n",
    )
    left = "* Campo alfa: valor uno"
    right = "* Campo beta: valor dos"
    for separator in separators:
        content = left + separator + right
        assert derive_missing_definition_sibling_cards(_candidate(content, 0, len(left))) == []

    indented = left + "\n\n  " + right
    assert derive_missing_definition_sibling_cards(_candidate(indented, 0, len(left))) == []


def test_more_than_one_omitted_item_is_ambiguous_and_fails_closed():
    content = (
        "* Campo alfa: valor uno\n\n"
        "* Campo beta: valor dos\n\n"
        "* Campo gamma: valor tres"
    )
    first_end = content.index("\n")
    assert derive_missing_definition_sibling_cards(_candidate(content, 0, first_end)) == []


def test_oversize_sibling_fails_closed():
    left = "* Campo alfa: valor uno"
    right = "* Campo beta: " + ("x" * (MAX_CARD_CHARS + 10))
    content = left + "\n\n" + right

    assert derive_missing_definition_sibling_cards(_candidate(content, 0, len(left))) == []


def test_bad_base_receipt_fails_closed():
    content = "* Campo alfa: valor uno\n\n* Campo beta: valor dos"
    candidate = _candidate(content, 0, content.index("\n"))
    candidate["coverage_cards"][0]["quote"] += "tamper"

    assert derive_missing_definition_sibling_cards(candidate) == []


def test_own_field_receipt_rederives_and_rejects_tamper():
    content = "* Campo alfa: valor uno\n\n* Campo beta: valor dos"
    candidate = _candidate(content, 0, content.index("\n"))
    attested = attest_reference(candidate, enabled=True)

    assert CARD_FIELD in attested
    assert has_exact_reference_receipt(attested) is True

    tampered = copy.deepcopy(attested)
    tampered[CARD_FIELD][0]["quote"] += "x"
    assert has_exact_reference_receipt(tampered) is False


def test_flag_off_is_byte_identical_and_does_not_create_field():
    content = "* Campo alfa: valor uno\n\n* Campo beta: valor dos"
    candidate = _candidate(content, 0, content.index("\n"))

    off = attest_reference(candidate, enabled=False)

    assert CARD_FIELD not in off
    assert json.dumps(off, sort_keys=True) == json.dumps(candidate, sort_keys=True)


def test_two_eligible_blocks_in_one_chunk_are_ambiguous():
    content = (
        "* Campo alfa: valor uno\n\n* Campo beta: valor dos\n\n"
        "Texto de corte.\n\n"
        "* Campo gamma: valor tres\n\n* Campo delta: valor cuatro"
    )
    first_end = content.index("\n")
    second_block = content.index("* Campo gamma")
    gamma_end = content.index("\n", second_block)
    candidate_id = "two-blocks"
    candidate = {
        "id": candidate_id,
        "content": content,
        "coverage_cards": [
            _card(candidate_id, content, 0, first_end),
            _card(candidate_id, content, second_block, gamma_end),
        ],
    }

    assert derive_missing_definition_sibling_cards(candidate) == []


def test_frozen_prior_cohort_hashes_still_match():
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))

    for frozen in prereg["freeze"]["prior_cohorts"]:
        path = ROOT / Path(frozen["path"])
        assert _sha256_lf(path) == frozen["sha256_lf"]


def test_generated_gate_is_a_reproducible_no_go():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    gate = yaml.safe_load(GATE_PATH.read_text(encoding="utf-8"))

    assert result["status"] == "NO_GO_OFFLINE_SCREEN"
    assert gate["status"] == "NO_GO_OFFLINE_SCREEN"
    assert result["checks"]["eligible_manufacturers"] == {
        "value": 2,
        "pass": False,
    }
    assert gate["result_sha256_lf"] == _sha256_lf(RESULT_PATH)


def test_generated_artifact_chain_is_still_post_run_consistent():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    paths = {
        "design_sha256_lf": DESIGN_PATH,
        "prereg_sha256_lf": PREREG_PATH,
        "cohort_sha256_lf": COHORT_PATH,
        "build_sha256_lf": BUILD_PATH,
        "result_rows_sha256_lf": RESULT_ROWS_PATH,
        "screen_script_sha256_lf": ROOT
        / "scripts"
        / "s276_missing_definition_sibling_screen.py",
    }

    for key, path in paths.items():
        assert result["artifacts"][key] == _sha256_lf(path)
