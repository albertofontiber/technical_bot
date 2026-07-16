import hashlib
import yaml

from scripts.s126_compatibility_hyq_probe import ROOT, run_probe
from src.rag.compatibility_bundle_coverage import build_compatibility_bundle


TARGETS = {
    "loop_topology": "b6602d5a-dbb5-4e2e-8814-1ac3ce066896",
    "protocol_scope": "cfcdc8f7-bdaf-412f-a85e-0ffb76878d99",
    "supported_device_roster": "11d96526-d627-4305-8cae-e6852af1b20b",
}


def _bundle():
    benchmark = yaml.safe_load(
        (ROOT / "evals" / "s100_factlevel_full.yaml").read_text(encoding="utf-8")
    )
    query = next(row["question"] for row in benchmark["per_gold"] if row["qid"] == "cat013")
    groups = [
        {
            "token": "CAD-150",
            "ids": ["detnov:cad-150-8"],
            "sources": ["cad-install"],
        },
        {
            "token": "SDX-751",
            "ids": ["notifier:sdx-751"],
            "sources": ["notifier-manual"],
        },
    ]
    specs = [
        ("protocol_scope", "notifier-manual", "Protocolo CLIP.", "notifier-doc", "a" * 64, 5),
        ("supported_device_roster", "notifier-manual", "Compatible: SDX-751.", "notifier-doc", "a" * 64, 6),
        ("loop_topology", "cad-install", "Lazo cerrado con retorno.", "cad-doc", "b" * 64, 2),
    ]
    rows = []
    for facet, source, content, document, extraction, index in specs:
        row_id = TARGETS[facet]
        rows.append(
            {
                "id": row_id,
                "document_id": document,
                "source_file": source,
                "page_number": index,
                "extraction_sha256": extraction,
                "chunk_index": index,
                "content": content,
                "coverage_cards": [{
                    "candidate_id": row_id,
                    "start": 0,
                    "end": len(content),
                    "quote": content,
                    "facet": facet,
                    "exact_source_span_validated": True,
                }],
            }
        )
    return build_compatibility_bundle(query, rows, groups)


def _trace():
    empty_hash = hashlib.sha256(b"[]").hexdigest()
    return {
        "scope_rows": 5,
        "served_hyq_prose": False,
        "http_requests": 2,
        "fetch_receipts": {
            "hyq_rows_sha256": empty_hash,
            "selected_parent_ids_sha256": empty_hash,
            "hydrated_parents_sha256": empty_hash,
        },
    }


def test_s126_probe_gate_requires_all_three_bound_facets_without_ok_credit():
    payload = run_probe(collector=lambda _query: (_bundle(), _trace()))

    assert payload["status"] == "GO_READ_ONLY_RELATIONAL_BUNDLE"
    assert payload["credit"] == {
        "retrieval_stage_recoveries": 2,
        "facts_moved_to_ok": 0,
    }
    assert payload["cost"] == {
        "model_calls": 0,
        "http_get_requests": 2,
        "database_writes": 0,
    }


def test_s126_probe_fails_closed_when_roster_is_missing():
    partial = [
        row for row in _bundle()
        if row["compatibility_facet"] != "supported_device_roster"
    ]
    payload = run_probe(collector=lambda _query: (partial, _trace()))

    assert payload["status"] == "NO_GO_READ_ONLY_RELATIONAL_BUNDLE"
    assert payload["checks"]["exact_three_facet_bundle"] is False
    assert payload["checks"]["relational_bundle_revalidated"] is False
    assert payload["recovered_claims"]["cat013#1:CLIP"] is False
