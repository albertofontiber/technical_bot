#!/usr/bin/env python3
"""Sealed S116 A/B over an unused alternate-extractor artifact store."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from scripts.s116_raw_store_ab_v21 import (
    _anchor_resolves,
    _atomic_lineage_state_valid,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evals/s116_cross_extractor_challenge_v1.json"
EXPECTED_SOURCE_MANIFEST = "1157f7a03c672a02002235fff703a204915a4b0e3b6a107c4386906eb13ea38a"
EXPECTED_BASELINE = "58be85e8cdf2cfac475e7f7cd23639b04f7b22a1c60938ffec86e76cb2c60985"
EXPECTED_TREATMENT = "4b76ab219854c625f4ce5e55665e2c89d14739e4eee0ab01607aae7ecda4fd43"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_chunker(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load chunker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_chunker_source(source: bytes, name: str, filename: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = filename
    sys.modules[name] = module
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


def _git_chunker(ref: str = "HEAD") -> bytes:
    source = subprocess.run(
        ["git", "show", f"{ref}:src/reingest/chunk.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    # The frozen baseline hash was taken from the Windows worktree (CRLF), while
    # `git show` emits the canonical LF blob. Restore only that byte encoding and
    # accept it solely when it matches the preregistered baseline exactly.
    if hashlib.sha256(source).hexdigest() != EXPECTED_BASELINE:
        crlf_source = source.replace(b"\n", b"\r\n")
        if hashlib.sha256(crlf_source).hexdigest() == EXPECTED_BASELINE:
            return crlf_source
    return source


def _store_manifest(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        digest.update(
            f"{path.name}\0{len(raw)}\0{hashlib.sha256(raw).hexdigest()}\n".encode("utf-8")
        )
    return digest.hexdigest()


def _run_arm(files: list[Path], module: ModuleType, verify_lineage: bool) -> dict:
    streams: dict[str, str] = {}
    errors: list[dict] = []
    chunks_total = 0
    titled = 0
    anchors_verified = 0
    lineages_resolved = 0
    lineage_failures = 0
    orphans = 0
    for path in files:
        try:
            record = json.loads(path.read_bytes())
            blocks = module._flatten(record.get("result", {}).get("pages", []))
            chunks = module.chunk_document(record)
        except Exception as exc:
            errors.append({"file": path.name, "error_type": type(exc).__name__})
            continue
        streams[path.name] = hashlib.sha256(
            "\n\n".join(chunk.content for chunk in chunks).encode("utf-8")
        ).hexdigest()
        chunks_total += len(chunks)
        for chunk in chunks:
            if chunk.section_title:
                titled += 1
            if not verify_lineage:
                continue
            anchor = getattr(chunk, "section_anchor", None)
            atomic = _atomic_lineage_state_valid(chunk, blocks)
            if not atomic:
                lineage_failures += 1
            if anchor is not None and not _anchor_resolves(anchor, blocks):
                orphans += 1
            if chunk.section_title:
                verified = anchor is not None and _anchor_resolves(anchor, blocks)
                anchors_verified += int(verified)
                lineages_resolved += int(verified and atomic)
    return {
        "processed_files": len(streams),
        "errors": errors,
        "chunks_total": chunks_total,
        "titled_chunks": titled,
        "internally_verified_anchors": anchors_verified,
        "resolved_full_lineages": lineages_resolved,
        "chunk_lineage_state_failures": lineage_failures,
        "orphan_or_stale_anchor_chunks": orphans,
        "document_streams": dict(sorted(streams.items())),
    }


def build_payload(
    store: Path, baseline_path: Path | None, treatment_path: Path
) -> dict:
    files = sorted(store.glob("*.json"), key=lambda path: path.name.casefold())
    source_manifest = _store_manifest(files)
    baseline_source = baseline_path.read_bytes() if baseline_path is not None else _git_chunker()
    baseline_hash = hashlib.sha256(baseline_source).hexdigest()
    treatment_hash = _sha(treatment_path)
    if source_manifest != EXPECTED_SOURCE_MANIFEST:
        raise RuntimeError("source manifest drift")
    if baseline_hash != EXPECTED_BASELINE or treatment_hash != EXPECTED_TREATMENT:
        raise RuntimeError("chunker implementation drift")
    baseline = _run_arm(
        files,
        _load_chunker_source(baseline_source, "s116_baseline_chunk", "git:HEAD:src/reingest/chunk.py"),
        False,
    )
    treatment = _run_arm(files, _load_chunker(treatment_path, "s116_treatment_chunk"), True)
    names = sorted(set(baseline["document_streams"]) | set(treatment["document_streams"]))
    mismatches = [
        name
        for name in names
        if baseline["document_streams"].get(name) != treatment["document_streams"].get(name)
    ]
    chunk_increase = treatment["chunks_total"] - baseline["chunks_total"]
    chunk_increase_percent = (
        100 * chunk_increase / baseline["chunks_total"] if baseline["chunks_total"] else 0.0
    )
    exact_errors = baseline["errors"] == treatment["errors"]
    gate = (
        baseline["processed_files"] == treatment["processed_files"]
        and exact_errors
        and not mismatches
        and treatment["chunk_lineage_state_failures"] == 0
        and treatment["orphan_or_stale_anchor_chunks"] == 0
        and treatment["titled_chunks"] == treatment["internally_verified_anchors"]
        and treatment["titled_chunks"] == treatment["resolved_full_lineages"]
        and chunk_increase_percent <= 15
    )
    for arm in (baseline, treatment):
        del arm["document_streams"]
    return {
        "instrument": "s116_cross_extractor_challenge_v1",
        "status": "supporting_go" if gate else "no_go",
        "source": {
            "store_slug": store.name,
            "json_files": len(files),
            "manifest_sha256": source_manifest,
            "pdf_identity_overlap_with_development": len(files),
            "independence_claim": "extraction_mode_only",
        },
        "implementations": {
            "baseline_chunker_sha256": baseline_hash,
            "treatment_chunker_sha256": treatment_hash,
            "audit_script_sha256": _sha(Path(__file__)),
        },
        "baseline": baseline,
        "treatment": treatment,
        "comparison": {
            "exact_errors_equal": exact_errors,
            "document_stream_mismatches": len(mismatches),
            "chunk_increase": chunk_increase,
            "chunk_increase_percent": round(chunk_increase_percent, 4),
        },
        "gate": "GO" if gate else "NO_GO",
        "limitations": [
            "The extraction artifacts are unused, but their PDF identities overlap development.",
            "This is extractor-shift evidence, not an independent-document held-out.",
            "No migration, reingestion, index, serving, production or fact relabeling is authorized.",
        ],
        "cost": {
            "database_get_requests": 0,
            "database_writes": 0,
            "model_calls": 0,
            "network_calls": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--baseline-chunker", type=Path)
    parser.add_argument("--treatment-chunker", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = build_payload(args.store, args.baseline_chunker, args.treatment_chunker)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gate": payload["gate"], "comparison": payload["comparison"]}, indent=2))
    return 0 if payload["gate"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
