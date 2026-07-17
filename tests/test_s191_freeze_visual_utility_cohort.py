from scripts.s191_freeze_visual_utility_cohort import STRATA, choose_stratified_cohort


def test_selector_is_deterministic_balanced_and_unique():
    candidates = []
    for stratum in STRATA:
        for manufacturer in ("A", "B", "C"):
            for index in range(3):
                candidates.append(
                    {
                        "document_id": f"{stratum}-{manufacturer}-{index}",
                        "page_number": index + 2,
                        "manufacturer": manufacturer,
                        "stratum": stratum,
                    }
                )

    first = choose_stratified_cohort(
        candidates, per_stratum=3, manufacturer_cap=3
    )
    second = choose_stratified_cohort(
        list(reversed(candidates)), per_stratum=3, manufacturer_cap=3
    )

    assert first == second
    assert len(first) == 15
    assert {row["stratum"] for row in first} == set(STRATA)
    assert len({(row["document_id"], row["page_number"]) for row in first}) == 15
