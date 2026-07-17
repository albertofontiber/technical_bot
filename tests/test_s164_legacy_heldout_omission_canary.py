from scripts.s164_legacy_heldout_omission_canary import (
    load_population,
    score_atomic_facts,
)


def test_s164_population_is_exact_legacy_heldout_canary():
    row = load_population()
    assert row["qid"] == "ho008"
    assert len(row["chunks"]) == 5
    assert row["draft"]
    assert row["draft_stop_reason"] == "end_turn"


def test_s164_atomic_oracle_has_ten_unique_boolean_facts():
    rows = score_atomic_facts(load_population()["draft"])
    assert len(rows) == 10
    assert len({row["fact_id"] for row in rows}) == 10
    assert all(isinstance(row["covered"], bool) for row in rows)


def test_s164_oracle_requires_complete_relation_bundles():
    answer = (
        "La base tiene 2 lazos, 500 dispositivos y 250 por cada lazo. "
        "Admite hasta 8 lazos. La red tiene 64 nodos, Ethernet y USB."
    )
    rows = {row["fact_id"]: row["covered"] for row in score_atomic_facts(answer)}
    assert rows["base_loops_devices"] is True
    assert rows["eight_loops"] is True
    assert rows["network_64_nodes"] is True
    assert rows["ethernet_and_usb"] is True
    assert rows["zones_areas_groups"] is False
    assert rows["network_512k_devices"] is False
