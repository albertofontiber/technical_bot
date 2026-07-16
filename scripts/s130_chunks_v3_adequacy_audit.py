#!/usr/bin/env python3
"""S130 local, deterministic held-out embargo and chunks_v3 adequacy census."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml

from src.reingest import chunk as chunk_module

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "evals/s130_chunks_v3_adequacy_prereg_v2.yaml"
DEFAULT_PERMIT = ROOT / "evals/s130_chunks_v3_adequacy_execution_permit_v2.yaml"
_RECORD = re.compile(r"^[0-9a-f]{64}\.json$")
_CAPTION = re.compile(
    r"^\s*(?:\*{0,2})?(?:tabla|table|figura|figure|ilustraci[oó]n|illustration)\b",
    re.IGNORECASE,
)
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in normalized if not unicodedata.combining(c)).casefold()


def _basename(value: str) -> str:
    posix = str(value or "").replace("\\", "/")
    name = PurePosixPath(posix).name
    if name.casefold().endswith(".pdf"):
        name = name[:-4]
    return unicodedata.normalize("NFKC", name).casefold().strip()


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode()
        )
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate_inputs(prereg: dict[str, Any]) -> None:
    design = prereg["design"]
    if _sha(ROOT / design["path"]) != design["sha256"]:
        raise RuntimeError("S130 design drift")
    for name, spec in prereg["frozen_inputs"].items():
        if _sha(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"S130 frozen input drift: {name}")


def _validate_execution_permit(permit_path: Path, prereg_path: Path) -> dict[str, str]:
    permit = _yaml(permit_path)
    if permit.get("status") != "GO_TO_EXECUTE_LOCAL_CENSUS_ONCE":
        raise RuntimeError("S130 execution permit is not GO")
    checks = {
        "design_sha256": _sha(ROOT / permit["design"]["path"]),
        "prereg_sha256": _sha(prereg_path),
        "runner_sha256": _sha(Path(__file__)),
        "tests_sha256": _sha(ROOT / permit["implementation"]["tests_path"]),
        "permit_sha256": _sha(permit_path),
    }
    expected = {
        "design_sha256": permit["design"]["sha256"],
        "prereg_sha256": permit["implementation"]["prereg_sha256"],
        "runner_sha256": permit["implementation"]["runner_sha256"],
        "tests_sha256": permit["implementation"]["tests_sha256"],
    }
    for key, value in expected.items():
        if checks[key] != value:
            raise RuntimeError(f"S130 execution freeze drift: {key}")
    for key in ("consumption_receipt", "embargo", "audit"):
        relative = Path(permit["outputs"][key])
        absolute = (ROOT / relative).resolve()
        try:
            absolute.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError("S130 output escapes repository") from exc
        checks[f"{key}_output"] = relative.as_posix()
    return checks


def _seal_execution(payload: dict[str, Any], receipts: dict[str, str]) -> dict[str, Any]:
    sealed = dict(payload)
    sealed.pop("determinism", None)
    sealed["execution_freeze"] = receipts
    sealed["determinism"] = {"logical_payload_sha256": _canonical_sha(sealed)}
    return sealed


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )


def _consume_execution_permit(
    receipts: dict[str, str],
    *,
    embargo_out: Path,
    audit_out: Path,
) -> Path:
    pinned_embargo = (ROOT / receipts["embargo_output"]).resolve()
    pinned_audit = (ROOT / receipts["audit_output"]).resolve()
    if embargo_out.resolve() != pinned_embargo or audit_out.resolve() != pinned_audit:
        raise RuntimeError("S130 output path differs from one-shot permit")
    if pinned_embargo.exists() or pinned_audit.exists():
        raise FileExistsError("S130 output already exists; permit consumed or unsafe")
    consumption = (ROOT / receipts["consumption_receipt_output"]).resolve()
    _write_exclusive(
        consumption,
        {
            "instrument": "s130_chunks_v3_adequacy_execution_consumption_v2",
            "status": "PERMIT_CONSUMED_BEFORE_CORPUS_READ",
            "execution_freeze": receipts,
            "outputs": {
                "embargo": receipts["embargo_output"],
                "audit": receipts["audit_output"],
            },
        },
    )
    return consumption


def _load_raw_index(store: Path, prereg: dict[str, Any]) -> dict[str, Any]:
    files = sorted(store.glob("*.json"), key=lambda p: p.name)
    if len(files) != prereg["raw_store"]["json_files"]:
        raise RuntimeError("S130 raw store file-count drift")
    if _store_manifest(files) != prereg["raw_store"]["manifest_sha256"]:
        raise RuntimeError("S130 raw store manifest drift")
    records: dict[str, dict[str, Any]] = {}
    for path in files:
        if not _RECORD.fullmatch(path.name):
            continue
        # The filename is the physical extraction identity. It is not assumed
        # to be the source PDF identity. Phase 0 does not parse raw content.
        records[path.stem] = {"path": path, "extraction_sha256": path.stem}
    if len(records) != prereg["raw_store"]["extraction_records"]:
        raise RuntimeError("S130 raw record-count drift")
    return {"records": records}


def _load_catalog(prereg: dict[str, Any]) -> dict[str, Any]:
    doc_rows = [
        json.loads(line)
        for line in (ROOT / prereg["frozen_inputs"]["doc_map"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    docs = {str(row["document_id"]): row for row in doc_rows}
    snapshot_documents: dict[str, dict[str, Any]] = {}
    snapshot_chunks = 0
    snapshot_pair_counts: collections.Counter[tuple[str, str]] = collections.Counter()
    snapshot_doc_to_extractions: dict[str, set[str]] = collections.defaultdict(set)
    snapshot_extraction_to_docs: dict[str, set[str]] = collections.defaultdict(set)
    snapshot_canonical = hashlib.sha256()
    with gzip.open(
        ROOT / prereg["frozen_inputs"]["m25_snapshot"]["path"],
        "rb",
    ) as stream:
        for raw_line in stream:
            snapshot_canonical.update(raw_line)
            row = json.loads(raw_line)
            if row.get("kind") == "document":
                snapshot_documents[str(row["id"])] = row
            elif row.get("kind") == "chunk":
                snapshot_chunks += 1
                document = str(row.get("document_id") or "")
                extraction = str(row.get("extraction_sha256") or "")
                snapshot_pair_counts[(document, extraction)] += 1
                snapshot_doc_to_extractions[document].add(extraction)
                snapshot_extraction_to_docs[extraction].add(document)
    snapshot_spec = prereg["frozen_inputs"]["m25_snapshot"]
    if (
        len(snapshot_documents) != snapshot_spec["documents"]
        or snapshot_chunks != snapshot_spec["chunks"]
        or snapshot_canonical.hexdigest() != snapshot_spec["canonical_jsonl_sha256"]
    ):
        raise RuntimeError("M2.5 logical snapshot receipt drift")
    snapshot_binding_ledger = [
        {
            "document_id": document,
            "extraction_sha256": extraction,
            "chunk_rows": count,
        }
        for (document, extraction), count in sorted(snapshot_pair_counts.items())
    ]
    snapshot_nonempty_document_conflicts = sum(
        1
        for document, extractions in snapshot_doc_to_extractions.items()
        if document and len(extractions) != 1
    )
    snapshot_empty_document_extractions = len(
        snapshot_doc_to_extractions.get("", set())
    )
    expected_identity = prereg["phase0_embargo"]["expected"]
    if (
        len(snapshot_binding_ledger) != expected_identity["snapshot_binding_pairs"]
        or len(snapshot_doc_to_extractions)
        != expected_identity["snapshot_binding_documents"]
        or len(snapshot_extraction_to_docs)
        != expected_identity["snapshot_binding_extractions"]
        or _canonical_sha(snapshot_binding_ledger)
        != expected_identity["snapshot_binding_ledger_sha256"]
        or snapshot_nonempty_document_conflicts
        != expected_identity["snapshot_nonempty_document_conflicts"]
        or snapshot_empty_document_extractions
        != expected_identity["snapshot_empty_document_extractions"]
    ):
        raise RuntimeError("S130 snapshot binding ledger drift")
    id_to_docs: dict[str, set[str]] = collections.defaultdict(set)
    for row in doc_rows:
        for entry in row.get("entries", []):
            if entry.get("id"):
                id_to_docs[str(entry["id"])].add(str(row["document_id"]))
    product_ids = {
        str(json.loads(line)["id"])
        for line in (ROOT / prereg["frozen_inputs"]["products"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    graph: dict[str, set[str]] = collections.defaultdict(set)
    relations = []
    for line in (ROOT / prereg["frozen_inputs"]["relations"]["path"]).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("tipo") not in {"variant-of", "shared-doc", "rebrand-of"}:
            raise RuntimeError(f"unexpected catalog relation type: {row.get('tipo')}")
        left, right = str(row["origen"]), str(row["destino"])
        _require_endpoints(left, right, product_ids, "product")
        graph[left].add(right)
        graph[right].add(left)
        relations.append({"origen": left, "destino": right, "tipo": row["tipo"]})
    doc_graph: dict[str, set[str]] = collections.defaultdict(set)
    document_relations = []
    allowed_document_relation_types = {"language-variant-of"}
    for line in (ROOT / prereg["frozen_inputs"]["docrel"]["path"]).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("tipo") not in allowed_document_relation_types:
            raise RuntimeError(f"unexpected document relation type: {row.get('tipo')}")
        left, right = str(row.get("doc_a") or ""), str(row.get("doc_b") or "")
        _require_endpoints(left, right, set(snapshot_documents), "document")
        doc_graph[left].add(right)
        doc_graph[right].add(left)
        document_relations.append({"doc_a": left, "doc_b": right, "tipo": row["tipo"]})
    m25 = _json(ROOT / prereg["frozen_inputs"]["m25_binding"]["path"])
    m25_receipts: dict[str, dict[str, Any]] = {}
    for row in m25["rows"]:
        extraction = str(row["extraction_sha256"])
        if extraction in m25_receipts:
            raise RuntimeError("M25 extraction receipt collision")
        m25_receipts[extraction] = row
    by_basename: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for document, row in docs.items():
        extractions = snapshot_doc_to_extractions.get(document, set())
        if len(extractions) != 1:
            continue
        extraction = next(iter(extractions))
        if snapshot_extraction_to_docs.get(extraction) != {document}:
            continue
        by_basename[_basename(str(row.get("source_file") or ""))].add(
            (document, extraction)
        )
    return {
        "docs": docs,
        "snapshot_documents": snapshot_documents,
        "id_to_docs": id_to_docs,
        "graph": graph,
        "doc_graph": doc_graph,
        "relations": relations,
        "document_relations": document_relations,
        "product_ids": product_ids,
        "m25_receipts": m25_receipts,
        "snapshot_pair_counts": snapshot_pair_counts,
        "snapshot_doc_to_extractions": snapshot_doc_to_extractions,
        "snapshot_extraction_to_docs": snapshot_extraction_to_docs,
        "snapshot_binding_ledger_sha256": _canonical_sha(snapshot_binding_ledger),
        "snapshot_nonempty_document_conflicts": snapshot_nonempty_document_conflicts,
        "snapshot_empty_document_extractions": snapshot_empty_document_extractions,
        "by_basename": by_basename,
    }


def _row_index_s114(freeze: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def add(key: str, row: dict[str, Any]) -> None:
        metadata = (
            str(row.get("extraction_sha256") or ""),
            str(row.get("document_id") or ""),
            _basename(str(row.get("source_file") or "")),
        )
        if key in rows:
            prior = rows[key]
            prior_metadata = (
                str(prior.get("extraction_sha256") or ""),
                str(prior.get("document_id") or ""),
                _basename(str(prior.get("source_file") or "")),
            )
            if prior_metadata != metadata:
                raise RuntimeError("S114 row-id metadata collision")
            return
        rows[key] = row

    for key, row in freeze.get("source_rows", {}).items():
        add(str(key), row)
    for scope in freeze.get("candidate_scopes", {}).values():
        for row in scope:
            key = str(row.get("id") or "")
            if key:
                add(key, row)
    return rows


def _build_s114_metadata_ledger(
    freeze: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    rows = _row_index_s114(freeze)
    grouped: dict[str, dict[str, Any]] = collections.defaultdict(
        lambda: {"documents": set(), "basenames": set(), "row_ids": []}
    )
    reverse: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row_id, row in rows.items():
        extraction = str(row.get("extraction_sha256") or "")
        document = str(row.get("document_id") or "")
        basename = _basename(str(row.get("source_file") or ""))
        if (
            not _RECORD.fullmatch(f"{extraction}.json")
            or not document
            or not basename
        ):
            raise RuntimeError("S114 metadata ledger contains empty or malformed identity")
        grouped[extraction]["documents"].add(document)
        grouped[extraction]["basenames"].add(basename)
        grouped[extraction]["row_ids"].append(row_id)
        reverse[(document, basename)].add(extraction)
    if any(
        len(value["documents"]) != 1 or len(value["basenames"]) != 1
        for value in grouped.values()
    ) or any(len(extractions) != 1 for extractions in reverse.values()):
        raise RuntimeError("S114 metadata ledger is not reciprocal")
    ledger = []
    by_basename: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    doc_to_extractions: dict[str, set[str]] = collections.defaultdict(set)
    by_extraction: dict[str, dict[str, Any]] = {}
    for extraction, value in sorted(grouped.items()):
        document = next(iter(value["documents"]))
        basename = next(iter(value["basenames"]))
        entry = {
            "extraction_sha256": extraction,
            "document_id": document,
            "source_basename": basename,
            "row_ids": sorted(value["row_ids"]),
            "occurrences": len(value["row_ids"]),
        }
        ledger.append(entry)
        by_extraction[extraction] = entry
        by_basename[basename].add((document, extraction))
        doc_to_extractions[document].add(extraction)
    if (
        len(rows) != expected["s114_metadata_rows"]
        or len(ledger) != expected["s114_ledger_entries"]
        or _canonical_sha(ledger) != expected["s114_ledger_sha256"]
    ):
        raise RuntimeError("S114 metadata ledger receipt drift")
    return {
        "rows": rows,
        "ledger": ledger,
        "ledger_sha256": _canonical_sha(ledger),
        "by_extraction": by_extraction,
        "by_basename": by_basename,
        "doc_to_extractions": doc_to_extractions,
    }


def _resolve_direct_row(
    row: dict[str, Any],
    *,
    raw_index: dict[str, Any],
    catalog: dict[str, Any],
    metadata_ledger: dict[str, Any] | None,
    require_metadata_ledger: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    extraction = str(row.get("extraction_sha256") or "")
    document = str(row.get("document_id") or "")
    raw = raw_index["records"].get(extraction)
    if not raw:
        return None, "extraction_not_in_frozen_store"
    if document not in catalog["snapshot_documents"]:
        return None, "document_missing_from_snapshot"
    if (
        catalog["snapshot_pair_counts"].get((document, extraction), 0) < 1
        or catalog["snapshot_doc_to_extractions"].get(document) != {extraction}
        or catalog["snapshot_extraction_to_docs"].get(extraction) != {document}
    ):
        return None, "snapshot_document_extraction_binding_ambiguous"
    source_basename = _basename(
        str(
            row.get("source_file")
            or catalog["docs"].get(document, {}).get("source_file")
            or ""
        )
    )
    if not source_basename:
        return None, "source_basename_missing"
    ledger_entry = (
        metadata_ledger["by_extraction"].get(extraction)
        if metadata_ledger is not None
        else None
    )
    if require_metadata_ledger:
        if not ledger_entry:
            return None, "s114_metadata_binding_missing"
        if (
            ledger_entry["document_id"] != document
            or ledger_entry["source_basename"] != source_basename
        ):
            return None, "s114_metadata_binding_mismatch"
    receipt = catalog["m25_receipts"].get(extraction)
    if not receipt:
        return None, "m25_receipt_missing"
    terminal = str(receipt.get("terminal") or "")
    if terminal == "primary_unique_active_pdf_sha":
        if str(receipt.get("document_id") or "") != document:
            return None, "m25_primary_binding_contradiction"
    elif terminal == "primary_absent_pdf_sha":
        if (
            receipt.get("document_id") is not None
            or receipt.get("matching_document_count") != 0
            or (require_metadata_ledger and (not ledger_entry or ledger_entry["occurrences"] < 2))
        ):
            return None, "m25_absent_binding_not_corroborated"
    else:
        return None, "m25_terminal_not_eligible"
    document_row = catalog["docs"].get(document)
    product_ids = sorted(
        str(entry["id"])
        for entry in (document_row or {}).get("entries", [])
        if entry.get("id")
    )
    source_pdf_identity = str(
        catalog["snapshot_documents"][document].get("source_pdf_sha256") or ""
    )
    if re.fullmatch(r"[0-9a-f]{64}", source_pdf_identity):
        source_pdf_identity_status = "known_physical"
    elif source_pdf_identity.startswith("backfill:"):
        source_pdf_identity_status = "synthetic_backfill"
    else:
        source_pdf_identity_status = "unknown"
    return {
        "document_id": document,
        "extraction_sha256": extraction,
        "source_pdf_identity": source_pdf_identity,
        "source_pdf_identity_status": source_pdf_identity_status,
        "source_basename": source_basename,
        "product_ids": product_ids,
        "product_expansion_available": bool(product_ids),
        "binding_terminal": terminal,
        "metadata_occurrences": ledger_entry["occurrences"] if ledger_entry else None,
        "revision_identity": source_basename,
    }, None


def _fixed_point(seed_ids: Iterable[str], graph: dict[str, set[str]]) -> set[str]:
    seen = set(seed_ids)
    queue = collections.deque(sorted(seen))
    while queue:
        current = queue.popleft()
        for neighbor in sorted(graph.get(current, ())):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen


def _require_endpoints(left: str, right: str, universe: set[str], namespace: str) -> None:
    if not left or not right or left not in universe or right not in universe:
        raise RuntimeError(f"{namespace} relation endpoint missing")


def build_embargo(store: Path, prereg_path: Path = DEFAULT_PREREG) -> dict[str, Any]:
    prereg = _yaml(prereg_path)
    _validate_inputs(prereg)
    raw_index = _load_raw_index(store, prereg)
    catalog = _load_catalog(prereg)
    expected = prereg["phase0_embargo"]["expected"]
    seeds: list[dict[str, Any]] = []
    failures: list[str] = []

    s114 = _json(ROOT / prereg["frozen_inputs"]["s114_freeze"]["path"])
    metadata_ledger = _build_s114_metadata_ledger(s114, expected)
    row_index = metadata_ledger["rows"]
    selected_pairs: set[tuple[str, str]] = set()
    selected_rows = 0

    def add_selected(source: str, chunk_id: str) -> None:
        nonlocal selected_rows
        selected_rows += 1
        row = row_index.get(chunk_id)
        if not row:
            failures.append(f"{source}:{chunk_id}:chunk_unresolved")
            return
        resolved, error = _resolve_direct_row(
            row,
            raw_index=raw_index,
            catalog=catalog,
            metadata_ledger=metadata_ledger,
            require_metadata_ledger=True,
        )
        if error:
            failures.append(f"{source}:{chunk_id}:{error}")
            return
        pair = (resolved["document_id"], resolved["extraction_sha256"])
        selected_pairs.add(pair)
        seeds.append({"source": source, "seed_id": chunk_id, **resolved})

    for item in sorted(s114["chosen"], key=lambda x: str(x["chunk_id"])):
        add_selected("s114", str(item["chunk_id"]))
    s115 = _json(ROOT / prereg["frozen_inputs"]["s115_freeze"]["path"])
    for item in sorted(s115["sample"], key=lambda x: str(x["chunk_id"])):
        add_selected("s115", str(item["chunk_id"]))
    if selected_rows != expected["selected_rows"]:
        failures.append(f"selected_rows:{selected_rows}")
    if len(selected_pairs) != expected["selected_unique_pairs"]:
        failures.append(f"selected_unique_pairs:{len(selected_pairs)}")

    pairing = _yaml(ROOT / prereg["frozen_inputs"]["s63_pairing"]["path"])
    qids = sorted(set(pairing.get("identicos", [])) | set(pairing.get("cambiados", [])))
    gold = {
        str(row["qid"]): row
        for row in _yaml(ROOT / prereg["frozen_inputs"]["gold"]["path"])
    }
    s63_routes: collections.Counter[str] = collections.Counter()
    s63_unique: set[tuple[str, str]] = set()
    logical_support = []
    for qid in qids:
        row = gold.get(qid)
        if not row or row.get("split") != "held-out":
            failures.append(f"s63:{qid}:gold_heldout_unresolved")
            continue
        references = set(row.get("pdfs_used") or [])
        references.update(
            citation.get("pdf")
            for citation in row.get("citations", [])
            if citation.get("pdf")
        )
        if not references:
            failures.append(f"s63:{qid}:document_identity_missing")
        for reference in sorted(references):
            key = _basename(str(reference))
            catalog_matches = set(catalog["by_basename"].get(key, set()))
            metadata_matches = set(metadata_ledger["by_basename"].get(key, set()))
            if catalog_matches and metadata_matches and catalog_matches != metadata_matches:
                failures.append(f"s63:{qid}:{key}:catalog_metadata_disagreement")
                continue
            if len(catalog_matches) > 1 or len(metadata_matches) > 1:
                failures.append(f"s63:{qid}:{key}:ambiguous_exact_basename")
                continue
            route = "catalog" if catalog_matches else "s114_metadata" if metadata_matches else ""
            matches = catalog_matches or metadata_matches
            suffix = PurePosixPath(str(reference).replace("\\", "/")).suffix.casefold()
            if not matches:
                if suffix != ".pdf":
                    route = "logical_support_outside_raw_pdf_population"
                    s63_routes[route] += 1
                    s63_unique.add((route, key))
                    logical_support.append({"qid": qid, "identity": key, "route": route})
                    continue
                failures.append(f"s63:{qid}:{key}:exact_basename_unresolved")
                continue
            document, extraction = next(iter(matches))
            resolved, error = _resolve_direct_row(
                {
                    "document_id": document,
                    "extraction_sha256": extraction,
                    "source_file": key,
                },
                raw_index=raw_index,
                catalog=catalog,
                metadata_ledger=metadata_ledger,
                require_metadata_ledger=route == "s114_metadata",
            )
            if error:
                failures.append(f"s63:{qid}:{key}:{error}")
                continue
            s63_routes[route] += 1
            s63_unique.add((route, key))
            seeds.append(
                {
                    "source": "s63",
                    "seed_id": f"{qid}:{key}",
                    "resolution_route": route,
                    **resolved,
                }
            )
    if sum(s63_routes.values()) != expected["s63_reference_occurrences"]:
        failures.append(f"s63_reference_occurrences:{sum(s63_routes.values())}")
    if len(s63_unique) != expected["s63_unique_identities"]:
        failures.append(f"s63_unique_identities:{len(s63_unique)}")

    direct_documents = {row["document_id"] for row in seeds}
    direct_extractions = {row["extraction_sha256"] for row in seeds}
    seed_catalog_ids = {catalog_id for row in seeds for catalog_id in row["product_ids"]}
    closure_ids = _fixed_point(seed_catalog_ids, catalog["graph"])
    closure_documents = set(direct_documents)
    for catalog_id in closure_ids:
        closure_documents.update(catalog["id_to_docs"].get(catalog_id, set()))
    closure_documents = _fixed_point(closure_documents, catalog["doc_graph"])
    closure_extractions = set(direct_extractions)
    projection_receipts = []
    source_pdf_identities: dict[str, dict[str, str]] = {}
    for document in sorted(closure_documents):
        snapshot_candidates = set(catalog["snapshot_doc_to_extractions"].get(document, set()))
        snapshot_candidates = {
            extraction
            for extraction in snapshot_candidates
            if catalog["snapshot_extraction_to_docs"].get(extraction) == {document}
        }
        metadata_candidates = set(metadata_ledger["doc_to_extractions"].get(document, set()))
        if snapshot_candidates and metadata_candidates and snapshot_candidates != metadata_candidates:
            failures.append(f"closure:{document}:snapshot_metadata_disagreement")
            continue
        candidates = snapshot_candidates or metadata_candidates
        if len(candidates) != 1:
            failures.append(f"closure:{document}:projection_matches_{len(candidates)}")
            continue
        extraction = next(iter(candidates))
        if extraction not in raw_index["records"]:
            failures.append(f"closure:{document}:projection_not_in_raw_store")
            continue
        closure_extractions.add(extraction)
        projection_receipts.append(
            {
                "document_id": document,
                "extraction_sha256": extraction,
                "routes": sorted(
                    (["snapshot_chunk_ledger"] if snapshot_candidates else [])
                    + (["s114_metadata_ledger"] if metadata_candidates else [])
                ),
            }
        )
        identity = str(
            catalog["snapshot_documents"].get(document, {}).get("source_pdf_sha256") or ""
        )
        status = (
            "known_physical"
            if re.fullmatch(r"[0-9a-f]{64}", identity)
            else "synthetic_backfill"
            if identity.startswith("backfill:")
            else "unknown"
        )
        source_pdf_identities[document] = {"identity": identity, "status": status}

    for key, actual in (
        ("direct_documents", len(direct_documents)),
        ("direct_extractions", len(direct_extractions)),
        ("closure_documents", len(closure_documents)),
        ("excluded_extractions", len(closure_extractions)),
    ):
        if actual != expected[key]:
            failures.append(f"{key}:{actual}")

    ordered_seeds = sorted(seeds, key=lambda row: (row["source"], row["seed_id"]))
    closure_receipt = {
        "catalog_ids": sorted(closure_ids),
        "document_ids": sorted(closure_documents),
        "extraction_sha256s": sorted(closure_extractions),
        "projection_receipts": projection_receipts,
        "source_pdf_identities": source_pdf_identities,
    }
    payload = {
        "instrument": "s130_chunks_v3_heldout_exclusion_manifest_v2",
        "status": "GO" if not failures else "NO_GO_FAIL_CLOSED",
        "dependencies": {
            "prereg_sha256": _sha(prereg_path),
            "design_sha256": prereg["design"]["sha256"],
            "raw_store_slug": prereg["raw_store"]["slug"],
            "raw_store_manifest_sha256": prereg["raw_store"]["manifest_sha256"],
            "m25_snapshot_sha256": prereg["frozen_inputs"]["m25_snapshot"]["sha256"],
            "doc_map_sha256": prereg["frozen_inputs"]["doc_map"]["sha256"],
            "products_sha256": prereg["frozen_inputs"]["products"]["sha256"],
            "relations_sha256": prereg["frozen_inputs"]["relations"]["sha256"],
            "docrel_sha256": prereg["frozen_inputs"]["docrel"]["sha256"],
        },
        "identity_ledgers": {
            "s114": {
                "metadata_rows": len(metadata_ledger["rows"]),
                "entries": len(metadata_ledger["ledger"]),
                "ledger_sha256": metadata_ledger["ledger_sha256"],
                "forward_conflicts": 0,
                "reciprocal_conflicts": 0,
            },
            "snapshot_chunks": {
                "pairs": len(catalog["snapshot_pair_counts"]),
                "documents_including_empty_identity": len(catalog["snapshot_doc_to_extractions"]),
                "extractions": len(catalog["snapshot_extraction_to_docs"]),
                "ledger_sha256": catalog["snapshot_binding_ledger_sha256"],
                "nonempty_document_conflicts": catalog["snapshot_nonempty_document_conflicts"],
                "empty_document_extractions": catalog["snapshot_empty_document_extractions"],
            },
        },
        "counts": {
            "source_seed_occurrences": dict(collections.Counter(row["source"] for row in ordered_seeds)),
            "selected_rows_s114_s115": selected_rows,
            "selected_unique_pairs_s114_s115": len(selected_pairs),
            "s63_reference_occurrences": sum(s63_routes.values()),
            "s63_unique_identities": len(s63_unique),
            "direct_seed_occurrences": len(ordered_seeds),
            "direct_documents": len(direct_documents),
            "direct_extractions": len(direct_extractions),
            "closure_catalog_ids": len(closure_ids),
            "excluded_documents": len(closure_documents),
            "excluded_extractions": len(closure_extractions),
            "failures": len(failures),
        },
        "s63_resolution": {
            "occurrence_routes": dict(sorted(s63_routes.items())),
            "unique_identities": len(s63_unique),
            "logical_support_outside_raw_pdf_population": logical_support,
        },
        "seeds": ordered_seeds,
        "closure": {**closure_receipt, "closure_sha256": _canonical_sha(closure_receipt)},
        "s116": {"authority": "excluded_exploratory_only", "artifacts_read": 0},
        "failures": sorted(failures),
        "authorization": {
            "content_audit": not failures,
            "heldout_outcome_inspection": False,
            "migration": False,
            "production": False,
        },
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "embeddings": 0,
        },
    }
    payload["determinism"] = {"logical_payload_sha256": _canonical_sha(payload)}
    return payload


def _example(
    *,
    extraction: str,
    source_basename: str,
    chunk_index: int | None = None,
    page: int | None = None,
    text: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "extraction_sha256": extraction,
        "source_basename": source_basename,
        "chunk_index": chunk_index,
        "page": page,
    }
    if text is not None:
        row["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        row["excerpt"] = text[:240]
    if extra:
        row.update(extra)
    return row


def _surface_category(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return "empty"
    letters = sum(c.isalpha() for c in stripped)
    digits = sum(c.isdigit() for c in stripped)
    meaningful = letters + digits
    if meaningful == 0:
        return "symbol_only"
    if letters == 0 and digits > 0 and len(stripped) <= 8:
        return "short_numeric_only"
    if meaningful <= 3 and len(stripped) <= 12:
        return "very_short_token"
    return None


def _exact_text_overlap(left: str, right: str) -> bool:
    left_value, right_value = left.strip(), right.strip()
    if not left_value or not right_value:
        return False
    return left_value in right_value or right_value in left_value


def _is_contiguous_token_subsequence(needle: list[str], haystack: list[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(
        haystack[index : index + width] == needle
        for index in range(len(haystack) - width + 1)
    )


def _citation_document_identity(citation: dict[str, Any]) -> tuple[str | None, str | None]:
    identities = {
        _basename(str(citation[key]))
        for key in ("pdf", "manual")
        if citation.get(key)
    }
    if len(identities) > 1:
        return None, "citation_pdf_manual_disagreement"
    return (next(iter(identities)), None) if identities else (None, None)


def _unique_reciprocal_snapshot_extraction(
    document: str, catalog: dict[str, Any]
) -> tuple[str | None, str | None]:
    original = set(catalog["snapshot_doc_to_extractions"].get(document, set()))
    if len(original) > 1:
        return None, f"binding_collision_{len(original)}"
    extractions = sorted(
        extraction
        for extraction in original
        if catalog["snapshot_extraction_to_docs"].get(extraction) == {document}
    )
    if not extractions:
        return None, "extraction_unresolved"
    if len(extractions) > 1:
        return None, f"binding_collision_{len(extractions)}"
    return extractions[0], None


def _gold_pdf_bindings(
    qid: str,
    gold_by_qid: dict[str, dict[str, Any]],
    catalog: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    gold = gold_by_qid.get(qid)
    if not gold:
        return [], ["gold_qid_missing"]
    raw_citations = list(gold.get("citations", []))
    citations = [row for row in raw_citations if isinstance(row, dict)]
    pdfs = {
        _basename(str(value))
        for value in (gold.get("pdfs_used") or [])
        if value
    }
    failures = []
    unstructured_citations = len(raw_citations) - len(citations)
    if unstructured_citations:
        failures.append(f"unstructured_citations_{unstructured_citations}")
    citation_identities: list[tuple[dict[str, Any], str]] = []
    for citation in citations:
        identity, error = _citation_document_identity(citation)
        if error:
            failures.append(error)
        elif identity:
            pdfs.add(identity)
            citation_identities.append((citation, identity))
    bindings = []
    for basename in sorted(pdfs):
        matches = sorted(catalog["by_basename"].get(basename, set()))
        if len(matches) != 1:
            failures.append(f"{basename}:matches_{len(matches)}")
            continue
        document, extraction = matches[0]
        matching_citations = [
            row for row, identity in citation_identities if identity == basename
        ]
        pages = sorted(
            {
                int(row["page"])
                for row in matching_citations
                if isinstance(row.get("page"), int) and not isinstance(row.get("page"), bool)
            }
        )
        quotes = sorted(
            {str(row["quote"]) for row in matching_citations if row.get("quote")}
        )
        bindings.append(
            {
                "source_basename": basename,
                "extraction_sha256": extraction,
                "document_id": document,
                "pages": pages,
                "quotes": quotes,
            }
        )
    return bindings, failures


def build_impact_map(
    prereg: dict[str, Any],
    embargo: dict[str, Any],
    verified_gain_blocks: set[tuple[str, int]],
) -> dict[str, Any]:
    compact = _json(ROOT / prereg["frozen_inputs"]["compact100"]["path"])
    if len(compact["rows"]) != prereg["phase1_audit"]["expected_gain_blocks"]:
        raise RuntimeError("S130 compact100 count drift")
    catalog = _load_catalog(prereg)
    excluded = set(embargo["closure"]["extraction_sha256s"])
    gained_by_extraction: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in compact["rows"]:
        gained_by_extraction[str(row["extraction_sha256"])].append(row)
    changed_extractions = set(gained_by_extraction)

    s118 = _json(ROOT / prereg["frozen_inputs"]["s118_bridge"]["path"])
    legacy_claims = [row for row in s118["claims"] if row.get("known_m1_blocker") is None]
    s125 = _json(ROOT / prereg["frozen_inputs"]["s125_contract"]["path"])
    migrated_claims = [row for row in s125["claims"] if row.get("tipo") == "core"]
    if len(legacy_claims) != 99 or len(migrated_claims) != 58:
        raise RuntimeError("S130 157-claim population drift")
    gold_by_qid = {
        str(row["qid"]): row
        for row in _yaml(ROOT / prereg["frozen_inputs"]["gold"]["path"])
    }
    pairing = _yaml(ROOT / prereg["frozen_inputs"]["s63_pairing"]["path"])
    embargo_qids = set(pairing.get("identicos", [])) | set(pairing.get("cambiados", []))

    claim_rows = []
    block_links: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
    for lane, claims in (("legacy", legacy_claims), ("migrated_m1", migrated_claims)):
        for claim in claims:
            claim_id = str(
                claim.get("claim_id") if lane == "legacy" else claim.get("migration_id")
            )
            qid = str(claim["qid"])
            binding_failures: list[str] = []
            bindings: list[dict[str, Any]] = []
            support_literals: list[str] = []
            if qid in embargo_qids:
                disposition = "embargoed"
                claim_rows.append(
                    {
                        "claim_id": claim_id,
                        "qid": qid,
                        "lane": lane,
                        "stage_before": claim.get("stage_bucket") if lane == "legacy" else "known_m1_contract_hold",
                        "disposition": disposition,
                        "binding_failures": [],
                        "binding_count": 0,
                        "candidate_support": [],
                    }
                )
                continue
            if lane == "legacy":
                bindings, binding_failures = _gold_pdf_bindings(qid, gold_by_qid, catalog)
                support_literals = [
                    quote for binding in bindings for quote in binding.get("quotes", [])
                ]
            else:
                for source in claim.get("source_bindings", []):
                    document = str(source.get("document_id") or "")
                    extraction, extraction_error = _unique_reciprocal_snapshot_extraction(
                        document, catalog
                    )
                    if extraction_error:
                        binding_failures.append(f"{document}:{extraction_error}")
                        continue
                    pages = []
                    page = source.get("page_number")
                    if isinstance(page, int) and not isinstance(page, bool):
                        pages.append(page)
                    literals = [
                        str(span["literal"])
                        for span in source.get("support_spans", [])
                        if span.get("literal")
                    ]
                    support_literals.extend(literals)
                    bindings.append(
                        {
                            "source_basename": _basename(str(source.get("source_file") or "")),
                            "extraction_sha256": extraction,
                            "document_id": document,
                            "pages": pages,
                            "quotes": literals,
                        }
                    )
            bound_extractions = {row["extraction_sha256"] for row in bindings}
            if bound_extractions & excluded:
                disposition = "embargoed"
                candidates: list[dict[str, Any]] = []
            elif any("binding_collision" in failure for failure in binding_failures):
                disposition = "binding_collision"
                candidates = []
            elif binding_failures or not bindings:
                disposition = "binding_unresolved"
                candidates = []
            elif not (bound_extractions & changed_extractions):
                disposition = "outside_changed_documents"
                candidates = []
            else:
                candidates = []
                for binding in bindings:
                    extraction = binding["extraction_sha256"]
                    for block in gained_by_extraction.get(extraction, []):
                        if binding["pages"] and block.get("page") not in binding["pages"]:
                            continue
                        text = str(block.get("text") or "")
                        overlaps = [
                            literal for literal in support_literals if _exact_text_overlap(text, literal)
                        ]
                        if not overlaps:
                            continue
                        key = (extraction, int(block["source_block_index"]))
                        candidates.append(
                            {
                                "extraction_sha256": extraction,
                                "source_block_index": key[1],
                                "page": block.get("page"),
                                "start": 0,
                                "end": len(text),
                                "quote": text,
                                "quote_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                                "raw_verified": key in verified_gain_blocks,
                                "support_literal_sha256s": sorted(
                                    hashlib.sha256(value.encode("utf-8")).hexdigest()
                                    for value in overlaps
                                ),
                            }
                        )
                        block_links[key].append(claim_id)
                if candidates:
                    disposition = "manual_review_pending"
                else:
                    relevant_pages = any(
                        block.get("page") in binding["pages"] or not binding["pages"]
                        for binding in bindings
                        for block in gained_by_extraction.get(binding["extraction_sha256"], [])
                    )
                    disposition = (
                        "gained_page_no_support_overlap"
                        if relevant_pages
                        else "changed_document_no_gained_page_binding"
                    )
            claim_rows.append(
                {
                    "claim_id": claim_id,
                    "qid": qid,
                    "lane": lane,
                    "stage_before": claim.get("stage_bucket") if lane == "legacy" else "known_m1_contract_hold",
                    "disposition": disposition,
                    "binding_failures": sorted(binding_failures),
                    "binding_count": len(bindings),
                    "candidate_support": sorted(
                        candidates,
                        key=lambda row: (
                            row["extraction_sha256"], row["source_block_index"], row["quote_sha256"]
                        ),
                    ),
                }
            )

    block_rows = []
    for block in sorted(
        compact["rows"],
        key=lambda row: (str(row["extraction_sha256"]), int(row["source_block_index"])),
    ):
        extraction = str(block["extraction_sha256"])
        index = int(block["source_block_index"])
        key = (extraction, index)
        if extraction in excluded:
            disposition = "embargoed"
            receipt = None
        else:
            text = str(block.get("text") or "")
            receipt = {
                "start": 0,
                "end": len(text),
                "quote_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "raw_verified": key in verified_gain_blocks,
            }
            if block_links.get(key):
                disposition = "manual_review_pending"
            elif block.get("surface_diagnostic", {}).get("category"):
                disposition = "surface_risk"
            else:
                disposition = "no_claim_link"
        block_rows.append(
            {
                "extraction_sha256": extraction,
                "source_block_index": index,
                "page": block.get("page"),
                "kind": block.get("kind"),
                "disposition": disposition,
                "linked_claim_ids": sorted(set(block_links.get(key, []))),
                "receipt": receipt,
            }
        )
    claim_counts = dict(collections.Counter(row["disposition"] for row in claim_rows))
    block_counts = dict(collections.Counter(row["disposition"] for row in block_rows))
    eligible_claims = [row for row in claim_rows if row["disposition"] != "embargoed"]
    eligible_blocks = [row for row in block_rows if row["disposition"] != "embargoed"]
    unresolved = sum(
        claim_counts.get(value, 0)
        for value in ("binding_unresolved", "binding_collision", "manual_review_pending")
    ) + sum(
        block_counts.get(value, 0)
        for value in ("unresolved", "binding_collision", "manual_review_pending")
    )
    return {
        "status": "PENDING_ADJUDICATION" if unresolved else "COMPLETE",
        "population": {
            "claims_total": len(claim_rows),
            "claims_eligible": len(eligible_claims),
            "gained_blocks_total": len(block_rows),
            "gained_blocks_eligible": len(eligible_blocks),
        },
        "claim_dispositions": dict(sorted(claim_counts.items())),
        "block_dispositions": dict(sorted(block_counts.items())),
        "claims": sorted(claim_rows, key=lambda row: row["claim_id"]),
        "blocks": block_rows,
        "impact_gate": "impact_inconclusive" if unresolved else "no_kpi_shadow_signal",
        "facts_moved_to_ok": 0,
    }


def _decide_axes(
    integrity: dict[str, bool],
    metrics: dict[str, dict[str, Any]],
    impact: dict[str, Any],
) -> dict[str, Any]:
    if not all(integrity.values()):
        return {
            "S": "inconclusive",
            "P": "inconclusive",
            "reason": "integrity gate failed",
            "v4_build_authorized": False,
            "migration_authorized": False,
        }
    pending_metrics = [
        name
        for name, row in metrics.items()
        if row["occurrences"] and row.get("semantic_judgment") == "NOT_ADJUDICATED"
    ]
    if impact["status"] != "COMPLETE" or pending_metrics:
        return {
            "S": "inconclusive",
            "P": "inconclusive",
            "reason": "Carril A or structural proxies require final adjudication",
            "pending_metric_classes": pending_metrics,
            "v4_build_authorized": False,
            "migration_authorized": False,
        }
    # A final adjudicator must replace NOT_ADJUDICATED with the closed v5
    # responsibility/materiality dispositions before either positive branch.
    hard_v4 = any(row.get("v4_hard_correctness") is True for row in metrics.values())
    systemic_v4 = any(row.get("v4_systemic_gate") is True for row in metrics.values())
    projection_signal = any(
        row.get("p_systemic_diversity") is True or row.get("b8_lossless_projection") is True
        for row in metrics.values()
    )
    return {
        "S": "v4_design_required" if hard_v4 or systemic_v4 else "v3_adequate",
        "P": "projection_design_warranted" if projection_signal else "no_projection_design_signal",
        "reason": "closed S130 v5 truth tables",
        "v4_build_authorized": False,
        "migration_authorized": False,
    }


def audit_corpus(
    store: Path,
    embargo: dict[str, Any],
    prereg_path: Path = DEFAULT_PREREG,
) -> dict[str, Any]:
    prereg = _yaml(prereg_path)
    if embargo["status"] != "GO":
        raise RuntimeError("S130 phase 0 embargo is not GO")
    excluded = set(embargo["closure"]["extraction_sha256s"])
    m28 = _yaml(ROOT / prereg["frozen_inputs"]["m28_gate"]["path"])
    m28_implementation = _yaml(
        ROOT / prereg["frozen_inputs"]["m28_implementation_gate"]["path"]
    )
    m29 = _yaml(ROOT / prereg["frozen_inputs"]["m29_gate"]["path"])
    m28_population = m28["population"]
    m29_population = m29["population"]
    causal = m28_implementation["causal_result_carried_forward"]
    files = sorted(
        (path for path in store.glob("*.json") if _RECORD.fullmatch(path.name)),
        key=lambda p: p.name,
    )
    counters: collections.Counter[str] = collections.Counter()
    eligible_docs: set[str] = set()
    affected_docs: dict[str, set[str]] = collections.defaultdict(set)
    examples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    frozen_all_rows = int(m28_population["rows"])
    frozen_all_blocks = int(m28_population["raw_blocks"])
    eligible_rows = 0
    eligible_blocks = 0
    MAX_EXAMPLES = int(prereg["phase1_audit"]["max_examples_per_metric"])
    compact = _json(ROOT / prereg["frozen_inputs"]["compact100"]["path"])
    gained_by_extraction: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in compact["rows"]:
        gained_by_extraction[str(row["extraction_sha256"])].append(row)
    verified_gain_blocks: set[tuple[str, int]] = set()

    def record(metric: str, document: str, item: dict[str, Any]) -> None:
        counters[metric] += 1
        affected_docs[metric].add(document)
        if len(examples[metric]) < MAX_EXAMPLES:
            examples[metric].append(item)

    for path in files:
        extraction = path.stem
        # Embargo check precedes JSON parsing, flattening and chunk execution.
        if extraction in excluded:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if str(raw.get("sha256") or "") != extraction:
            raise RuntimeError("eligible raw filename/identity drift")
        source_basename = _basename(str(raw.get("source_path") or ""))
        blocks = chunk_module._flatten(raw.get("result", {}).get("pages", []))
        chunks = chunk_module.chunk_document(raw)
        eligible_docs.add(extraction)
        eligible_rows += len(chunks)
        eligible_blocks += len(blocks)

        raw_tokens = re.findall(r"\S+", "\n\n".join(block.text for block in blocks))
        stored_tokens = re.findall(r"\S+", "\n\n".join(chunk.content for chunk in chunks))
        if raw_tokens != stored_tokens:
            record(
                "content_token_stream_mismatch",
                extraction,
                _example(
                    extraction=extraction,
                    source_basename=source_basename,
                    extra={
                        "raw_tokens": len(raw_tokens),
                        "stored_tokens": len(stored_tokens),
                        "raw_token_stream_sha256": _canonical_sha(raw_tokens),
                        "stored_token_stream_sha256": _canonical_sha(stored_tokens),
                    },
                ),
            )
        for gained in gained_by_extraction.get(extraction, []):
            index = gained.get("source_block_index")
            valid = (
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(blocks)
                and blocks[index].text == gained.get("text")
                and blocks[index].page == gained.get("page")
                and blocks[index].kind == gained.get("kind")
                and hashlib.sha256(blocks[index].text.encode("utf-8")).hexdigest()
                == gained.get("text_sha256")
            )
            if valid:
                verified_gain_blocks.add((extraction, index))
            else:
                record(
                    "gained_block_raw_binding_mismatch",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=gained.get("page"),
                        extra={"source_block_index": index},
                    ),
                )

        page_images: dict[int, list[dict[str, Any]]] = {}
        headers: collections.Counter[str] = collections.Counter()
        footers: collections.Counter[str] = collections.Counter()
        for page in raw.get("result", {}).get("pages", []):
            page_number = page.get("page")
            if isinstance(page_number, int) and not isinstance(page_number, bool):
                page_images[page_number] = list(page.get("images") or [])
            for field, bucket in (("pageHeaderMarkdown", headers), ("pageFooterMarkdown", footers)):
                value = str(page.get(field) or "").strip()
                if value:
                    bucket[_fold(value)] += 1

        block_to_chunks: dict[int, list[int]] = collections.defaultdict(list)
        for chunk in chunks:
            start, end = chunk.source_block_start, chunk.source_block_end
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 0
                or end < start
                or end >= len(blocks)
            ):
                record(
                    "invalid_source_span",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                    ),
                )
                continue
            for block_index in range(start, end + 1):
                block_to_chunks[block_index].append(chunk.chunk_index)
            length = len(chunk.content)
            if length > 16000:
                record(
                    "stored_content_over_16000",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                        extra={"content_chars": length, "margin_to_16000": 16000 - length},
                    ),
                )
            elif length > 7000:
                record(
                    "structural_oversize_7000_16000",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                        extra={"content_chars": length, "margin_to_16000": 16000 - length},
                    ),
                )
            span_blocks = blocks[start : end + 1]
            chunk_tokens = re.findall(r"\S+", chunk.content)
            span_tokens = re.findall(
                r"\S+", "\n\n".join(block.text for block in span_blocks)
            )
            if not _is_contiguous_token_subsequence(chunk_tokens, span_tokens):
                record(
                    "chunk_span_token_mismatch",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                        text=chunk.content,
                        extra={
                            "source_block_start": start,
                            "source_block_end": end,
                            "chunk_token_stream_sha256": _canonical_sha(chunk_tokens),
                            "span_token_stream_sha256": _canonical_sha(span_tokens),
                        },
                    ),
                )
            pages = sorted({b.page for b in span_blocks if isinstance(b.page, int)})
            real_image_pages = {
                page
                for page in pages
                if any(image.get("type") != "full_page_screenshot" for image in page_images.get(page, []))
            }
            first_images = page_images.get(chunk.page_number, [])
            if real_image_pages and not chunk.has_diagram:
                record(
                    "visual_metadata_false_negative",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                        extra={"row_pages": pages, "real_image_pages": sorted(real_image_pages)},
                    ),
                )
            all_span_images = [image for page in pages for image in page_images.get(page, [])]
            if chunk.has_diagram and all_span_images and all(
                image.get("type") == "full_page_screenshot" for image in all_span_images
            ):
                record(
                    "visual_metadata_screenshot_only",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                    ),
                )
            if not chunk.section_lineage:
                record(
                    "row_without_lineage",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                    ),
                )
            terminal_anchors = {
                b.lineage[-1].identity for b in span_blocks if b.lineage
            }
            if len(terminal_anchors) > 1 and len(chunk.section_lineage) < max(
                (len(b.lineage) for b in span_blocks), default=0
            ):
                record(
                    "mixed_descendant_branches",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page_number,
                        extra={"terminal_anchor_count": len(terminal_anchors)},
                    ),
                )

        missing = sorted(set(range(len(blocks))) - set(block_to_chunks))
        if missing:
            counters["raw_blocks_not_stored"] += len(missing)
            affected_docs["raw_blocks_not_stored"].add(extraction)
            for index in missing[: max(0, MAX_EXAMPLES - len(examples["raw_blocks_not_stored"]))]:
                examples["raw_blocks_not_stored"].append(
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=blocks[index].page,
                        text=blocks[index].text,
                        extra={"source_block_index": index, "kind": blocks[index].kind},
                    )
                )

        for index, block in enumerate(blocks):
            category = _surface_category(block.text)
            if category:
                record(
                    f"surface_{category}",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=block.page,
                        text=block.text,
                        extra={"source_block_index": index, "kind": block.kind},
                    ),
                )
            if block.kind == "heading":
                pass
            if index + 1 >= len(blocks):
                continue
            nxt = blocks[index + 1]
            left_chunks = block_to_chunks.get(index, [])
            right_chunks = block_to_chunks.get(index + 1, [])
            separated = bool(left_chunks and right_chunks and set(left_chunks).isdisjoint(right_chunks))
            if separated and (
                (_CAPTION.match(block.text) and nxt.kind == "table")
                or (block.kind == "table" and _CAPTION.match(nxt.text))
            ):
                record(
                    "caption_table_boundary",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=block.page,
                        text=f"{block.text}\n{nxt.text}",
                        extra={"left_block": index, "right_block": index + 1},
                    ),
                )
            if separated and block.kind == "paragraph" and block.text.rstrip().endswith(":") and nxt.kind == "list":
                record(
                    "intro_list_boundary",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=block.page,
                        text=f"{block.text}\n{nxt.text}",
                        extra={"left_block": index, "right_block": index + 1},
                    ),
                )
            if separated and block.kind != "heading" and nxt.kind != "heading":
                left_lineage = tuple(anchor.identity for anchor in block.lineage)
                right_lineage = tuple(anchor.identity for anchor in nxt.lineage)
                if left_lineage == right_lineage:
                    record(
                        "same_lineage_adjacent_boundary",
                        extraction,
                        _example(
                            extraction=extraction,
                            source_basename=source_basename,
                            page=block.page,
                            extra={"left_block": index, "right_block": index + 1},
                        ),
                    )

        heading_occurrences: dict[str, list[Any]] = collections.defaultdict(list)
        for index, block in enumerate(blocks):
            if block.kind == "heading":
                heading_occurrences[_fold(block.text)].append((index, block))
        for folded, occurrences in heading_occurrences.items():
            distinct_pages = {block.page for _, block in occurrences}
            if folded and len(occurrences) >= 3 and len(distinct_pages) >= 3:
                record(
                    "repeated_heading_across_pages",
                    extraction,
                    _example(
                        extraction=extraction,
                        source_basename=source_basename,
                        page=occurrences[0][1].page,
                        text=occurrences[0][1].text,
                        extra={"occurrences": len(occurrences), "distinct_pages": len(distinct_pages)},
                    ),
                )
        for kind, bucket in (("header", headers), ("footer", footers)):
            for folded, count in bucket.items():
                if count >= 3 and folded:
                    record(
                        f"repeated_page_{kind}",
                        extraction,
                        _example(
                            extraction=extraction,
                            source_basename=source_basename,
                            extra={"page_occurrences": count, "normalized_sha256": hashlib.sha256(folded.encode()).hexdigest()},
                        ),
                    )

    expected = prereg["phase1_audit"]
    integrity = {
        "m28_status_go": m28.get("status") == "CANDIDATE_MATERIALIZATION_GO_STRUCTURAL_ONLY",
        "m28_implementation_status_go": m28_implementation.get("status") == "IMPLEMENTATION_GO_CANDIDATE_DESIGN_ONLY",
        "m29_status_structural_go": m29.get("status") == "RECONCILED_LOSS_LEDGER_GO_STRUCTURAL_ONLY",
        "candidate_rows_exact": frozen_all_rows == expected["expected_candidate_rows"],
        "raw_blocks_exact": frozen_all_blocks == expected["expected_raw_blocks"],
        "gained_blocks_exact": (
            int(m28_population["coverage_gain_blocks"]) == expected["expected_gain_blocks"]
            and int(m29_population["coverage_gain_blocks"]) == expected["expected_gain_blocks"]
        ),
        "regressed_blocks_exact": (
            int(m28_population["coverage_regression_blocks"]) == expected["expected_regression_blocks"]
            and int(m29_population["coverage_regression_blocks"]) == expected["expected_regression_blocks"]
        ),
        "changed_documents_exact": (
            int(m28_population["changed_documents"])
            == int(m29_population["changed_fingerprint_multiset_documents"])
            == int(causal["changed_documents"])
        ),
        "v2_v3_row_accounting_exact": (
            int(causal["baseline_rows"]) == expected["expected_baseline_rows"]
            and int(causal["candidate_oracle_rows"]) == frozen_all_rows
            and frozen_all_rows - int(causal["baseline_rows"])
            == int(m28_population["delta_added_rows"]) - int(m28_population["delta_removed_rows"])
        ),
        "zero_raw_blocks_not_stored": counters["raw_blocks_not_stored"] == 0,
        "zero_invalid_source_spans": counters["invalid_source_span"] == 0,
        "zero_chunk_span_token_mismatches": counters["chunk_span_token_mismatch"] == 0,
        "eligible_streams_exact": counters["content_token_stream_mismatch"] == 0,
        "eligible_gained_blocks_raw_exact": (
            counters["gained_block_raw_binding_mismatch"] == 0
            and len(verified_gain_blocks)
            == sum(
                1
                for row in compact["rows"]
                if str(row["extraction_sha256"]) not in excluded
            )
        ),
        "embargo_go": embargo["status"] == "GO",
    }
    metrics = {}
    for metric in sorted(counters):
        metrics[metric] = {
            "occurrences": counters[metric],
            "documents": len(affected_docs[metric]),
            "eligible_row_rate": round(counters[metric] / eligible_rows, 8) if eligible_rows else None,
            "examples": sorted(
                examples[metric],
                key=lambda row: (
                    row["extraction_sha256"],
                    -1 if row.get("chunk_index") is None else row["chunk_index"],
                    -1 if row.get("page") is None else row["page"],
                    row.get("text_sha256", ""),
                ),
            ),
            "semantic_judgment": "NOT_ADJUDICATED",
        }
    impact = build_impact_map(prereg, embargo, verified_gain_blocks)
    axes = _decide_axes(integrity, metrics, impact)
    payload = {
        "instrument": "s130_chunks_v3_adequacy_audit_v2",
        "status": "CANDIDATE_CENSUS_GO_PENDING_ADJUDICATION" if all(integrity.values()) else "NO_GO",
        "authority": "structural_surface_proxies_only_no_semantic_claim",
        "dependencies": {
            "prereg_sha256": _sha(prereg_path),
            "embargo_logical_payload_sha256": embargo["determinism"]["logical_payload_sha256"],
            "chunker_sha256": prereg["frozen_inputs"]["chunker"]["sha256"],
            "m28_gate_sha256": prereg["frozen_inputs"]["m28_gate"]["sha256"],
            "m28_implementation_gate_sha256": prereg["frozen_inputs"]["m28_implementation_gate"]["sha256"],
            "m29_gate_sha256": prereg["frozen_inputs"]["m29_gate"]["sha256"],
        },
        "population": {
            "all_documents": len(files),
            "all_rows_frozen_not_reprocessed": frozen_all_rows,
            "all_raw_blocks_frozen_not_reprocessed": frozen_all_blocks,
            "embargoed_extractions": len(excluded),
            "eligible_documents": len(eligible_docs),
            "eligible_rows": eligible_rows,
            "eligible_raw_blocks": eligible_blocks,
        },
        "v2_v3_frozen_comparison": {
            "v2_rows": int(causal["baseline_rows"]),
            "v3_rows": frozen_all_rows,
            "delta_rows": frozen_all_rows - int(causal["baseline_rows"]),
            "changed_documents": int(m28_population["changed_documents"]),
            "gained_blocks": int(m28_population["coverage_gain_blocks"]),
            "regressed_blocks": int(m28_population["coverage_regression_blocks"]),
            "semantic_or_retrieval_effect": "NOT_MEASURED",
        },
        "integrity": integrity,
        "metrics": metrics,
        "impact": impact,
        "decision": axes,
        "cost": {
            "model_calls": 0,
            "network_calls": 0,
            "database_reads": 0,
            "database_writes": 0,
            "embeddings": 0,
        },
    }
    payload["determinism"] = {"logical_payload_sha256": _canonical_sha(payload)}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--permit", type=Path, default=DEFAULT_PERMIT)
    parser.add_argument(
        "--embargo-out",
        type=Path,
        default=ROOT / "evals/s130_chunks_v3_heldout_exclusion_manifest_v2.json",
    )
    parser.add_argument(
        "--audit-out",
        type=Path,
        default=ROOT / "evals/s130_chunks_v3_adequacy_audit_v2.json",
    )
    args = parser.parse_args()
    receipts = _validate_execution_permit(args.permit, args.prereg)
    _consume_execution_permit(
        receipts,
        embargo_out=args.embargo_out,
        audit_out=args.audit_out,
    )
    embargo1 = _seal_execution(build_embargo(args.store, args.prereg), receipts)
    embargo2 = _seal_execution(build_embargo(args.store, args.prereg), receipts)
    if _canonical_bytes(embargo1) != _canonical_bytes(embargo2):
        raise RuntimeError("S130 embargo nondeterminism")
    _write_exclusive(args.embargo_out, embargo1)
    if embargo1["status"] != "GO":
        print(json.dumps({"embargo": embargo1["status"], "failures": embargo1["failures"]}, ensure_ascii=False))
        return 2
    audit1 = _seal_execution(audit_corpus(args.store, embargo1, args.prereg), receipts)
    audit2 = _seal_execution(audit_corpus(args.store, embargo1, args.prereg), receipts)
    if _canonical_bytes(audit1) != _canonical_bytes(audit2):
        raise RuntimeError("S130 audit nondeterminism")
    _write_exclusive(args.audit_out, audit1)
    print(
        json.dumps(
            {
                "embargo": embargo1["status"],
                "embargo_counts": embargo1["counts"],
                "audit": audit1["status"],
                "population": audit1["population"],
                "metric_counts": {
                    key: {"occurrences": value["occurrences"], "documents": value["documents"]}
                    for key, value in audit1["metrics"].items()
                },
                "impact": {
                    "status": audit1["impact"]["status"],
                    "population": audit1["impact"]["population"],
                    "claim_dispositions": audit1["impact"]["claim_dispositions"],
                    "block_dispositions": audit1["impact"]["block_dispositions"],
                    "impact_gate": audit1["impact"]["impact_gate"],
                },
                "decision": audit1["decision"],
                "cost": audit1["cost"],
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0 if audit1["status"].endswith("PENDING_ADJUDICATION") else 1


if __name__ == "__main__":
    raise SystemExit(main())
