from src.rag.procedure_bundle_coverage import (
    MAX_CARD_CHARS,
    select_procedure_bundle_coverage,
    verify_source_span_receipt,
)


def _row(
    row_id,
    content,
    product="DXc",
    source="manual",
    section="",
    doc="d1",
    manufacturer="Morley",
):
    return {
        "id": row_id,
        "content": content,
        "manufacturer": manufacturer,
        "product_model": product,
        "source_file": source,
        "section_title": section,
        "document_id": doc,
        "extraction_sha256": "a" * 64,
    }


def test_follows_aligned_explicit_section_reference_inside_same_document():
    served = [_row("s", "Compare the airflow value; see cap. 7.6.1.", product="ASD535", manufacturer="Securiton")]
    target = _row(
        "t",
        "Press OK to read the airflow. V01 selects pipe I and V02 selects pipe II.",
        product="ASD535",
        section="7.6.1 Reading airflow",
        manufacturer="Securiton",
    )
    selected, trace = select_procedure_bundle_coverage("How do I read airflow?", served, [target])
    assert [row["id"] for row in selected] == ["t"]
    assert trace["selected_facets"] == ["explicit_intra_document_reference"]


def test_rejects_referenced_section_without_same_task_anchor():
    served = [_row("s", "For airflow diagnostics see section 7.6.1.")]
    target = _row("t", "Press OK to reset the battery.", section="7.6.1 Reset")
    selected, _ = select_procedure_bundle_coverage("How do I diagnose airflow?", served, [target])
    assert selected == []


def test_selects_access_only_when_requested_task_follows_unlock():
    served = [_row("s", "Autosearch detects the installed detector devices on a loop.")]
    target = _row(
        "t",
        "Enter Level 3 and press OK to unlock the memory. Then program the detector loop.",
    )
    selected, trace = select_procedure_bundle_coverage("How do I add a detector to a loop?", served, [target])
    assert [row["id"] for row in selected] == ["t"]
    assert trace["selected_facets"] == ["procedural_access_prerequisite"]


def test_rejects_unrelated_access_clause_in_same_manual():
    served = [_row("s", "Clock adjustment is available from the user menu.")]
    target = _row(
        "t",
        "Clock adjustment is in Level 2. Enter Level 3 and unlock the memory. "
        "Then program the detector loop.",
    )
    selected, _ = select_procedure_bundle_coverage("How do I set date and time?", served, [target])
    assert selected == []


def test_selects_quantified_licence_for_discovered_capability_anchor():
    served = [
        _row(
            "s",
            "An XYZP loop is enabled with a licence.",
            product="INSPIRE E10/E15",
            manufacturer="Notifier",
        )
    ]
    target = _row(
        "t",
        "One licence is required for each XYZP loop circuit.",
        product="INSPIRE E10",
        source="installation",
        doc="d2",
        manufacturer="Notifier",
    )
    selected, trace = select_procedure_bundle_coverage("How do I add devices to an XYZP loop?", served, [target])
    assert [row["id"] for row in selected] == ["t"]
    assert trace["selected_facets"] == ["quantified_licensed_loop_prerequisite"]


def test_rejects_licence_trigger_assembled_across_unrelated_rows():
    served = [
        _row("s1", "The XYZP capability is supported."),
        _row("s2", "A loop can be configured."),
        _row("s3", "A separate licence may be required."),
    ]
    target = _row("t", "One licence is required for each XYZP loop.")
    selected, _ = select_procedure_bundle_coverage("How to configure an XYZP loop?", served, [target])
    assert selected == []


def test_rejects_capability_anchor_far_from_served_licence_loop_relation():
    served = [_row("s", "XYZP " + "unrelated " * 40 + "A loop has a licence.")]
    target = _row("t", "One licence is required for each XYZP loop.", doc="d2")
    selected, _ = select_procedure_bundle_coverage("How to configure an XYZP loop?", served, [target])
    assert selected == []


def test_rejects_shared_standard_when_loop_capabilities_differ():
    served = [_row("s", "Under EN54, an XYZP loop is enabled with a licence.")]
    target = _row(
        "t", "Under EN54, one licence is required for each ABCD loop.", doc="d2"
    )
    selected, _ = select_procedure_bundle_coverage(
        "How do I configure an XYZP loop?", served, [target]
    )
    assert selected == []


def test_identity_is_strict_for_model_and_manufacturer():
    served = [_row("s", "Autosearch detects devices.", product="CAD-250")]
    wrong_model = _row(
        "m", "Enter Level 3 and unlock memory. Then program the detector loop.", product="CAD-150-8"
    )
    wrong_vendor = _row(
        "v",
        "Enter Level 3 and unlock memory. Then program the detector loop.",
        product="CAD-250",
        manufacturer="Notifier",
    )
    selected, _ = select_procedure_bundle_coverage(
        "How do I add a detector to the loop?", served, [wrong_model, wrong_vendor]
    )
    assert selected == []


def test_same_source_filename_does_not_override_conflicting_document_ids():
    served = [_row("s", "Autosearch detects devices.", source="manual.pdf", doc="doc-a")]
    target = _row(
        "t",
        "Enter Level 3 and unlock memory. Then program the detector loop.",
        source="manual.pdf",
        doc="doc-b",
    )
    selected, _ = select_procedure_bundle_coverage(
        "How do I add a detector to the loop?", served, [target]
    )
    assert selected == []


def test_identity_expands_compact_slash_variant_without_token_matching():
    served = [_row("s", "An XYZP loop has a licence.", product="INSPIRE E10/E15", manufacturer="Notifier")]
    target = _row(
        "t",
        "One licence is required for each XYZP loop.",
        product="INSPIRE E10",
        manufacturer="Notifier",
        doc="d2",
    )
    selected, _ = select_procedure_bundle_coverage("How to configure an XYZP loop?", served, [target])
    assert [row["id"] for row in selected] == ["t"]


def test_receipt_is_exact_bounded_and_detects_tampering():
    served = [_row("s", "An XYZP loop has a licence.", product="INSPIRE E10/E15", manufacturer="Notifier")]
    target = _row(
        "t",
        "prefix " * 300 + "One licence is required for each XYZP loop." + " suffix" * 300,
        product="INSPIRE E10",
        manufacturer="Notifier",
        doc="d2",
    )
    selected, _ = select_procedure_bundle_coverage("How to configure an XYZP loop?", served, [target])
    card = selected[0]["coverage_cards"][0]
    assert len(card["quote"]) <= MAX_CARD_CHARS
    assert target["content"][card["start"]:card["end"]] == card["quote"]
    assert verify_source_span_receipt(target, card)
    tampered = dict(card, quote=card["quote"] + "x")
    assert not verify_source_span_receipt(target, tampered)


def test_table_reference_emits_two_atomic_cards_for_distinct_values():
    served = [_row("s", "Compare airflow; see cap. 7.6.1.", product="ASD535", manufacturer="Securiton")]
    target = _row(
        "t",
        "| Action | Display | Meaning |\n"
        "| Press | V01 | airflow for pipe I |\n"
        "| Press | V01 | airflow value for pipe I |\n"
        "| Press | V02 | airflow for pipe II |\n",
        product="ASD535",
        manufacturer="Securiton",
        section="7.6.1 Reading airflow",
    )
    selected, _ = select_procedure_bundle_coverage("How do I read airflow?", served, [target])
    quotes = [card["quote"] for card in selected[0]["coverage_cards"]]
    assert len(quotes) == 2
    assert "V01" in quotes[0]
    assert "V02" in quotes[1]
    assert all(verify_source_span_receipt(target, card) for card in selected[0]["coverage_cards"])


def test_immutable_receipt_requires_strong_nonempty_provenance():
    served = [_row("s", "An XYZP loop has a licence.", product="INSPIRE E10/E15", manufacturer="Notifier")]
    target = _row(
        "t",
        "One licence is required for each XYZP loop.",
        product="INSPIRE E10",
        manufacturer="Notifier",
        doc="d2",
    )
    selected, _ = select_procedure_bundle_coverage("How to configure an XYZP loop?", served, [target])
    card = selected[0]["coverage_cards"][0]
    assert not verify_source_span_receipt(dict(target, document_id=""), card)
    assert not verify_source_span_receipt(dict(target, extraction_sha256=""), card)


def test_configurable_adjective_does_not_trigger_procedural_access_lane():
    served = [_row("s", "Alarm levels are configurable.")]
    target = _row("t", "Enter Level 3 and unlock the memory. Then program the loop.")
    selected, _ = select_procedure_bundle_coverage(
        "What is the maximum configurable alarm level?", served, [target]
    )
    assert selected == []
