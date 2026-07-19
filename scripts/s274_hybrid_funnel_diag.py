#!/usr/bin/env python3
"""S274 Bloque D — diagnóstico D1: funnel POR-PROPUESTA del brazo híbrido sobre los
borradores OFF ALMACENADOS del probe v3 (0 generaciones; solo Haiku del detect,
autorizado <=$0.10; DB 0).

Cierra el gap de instrumento declarado en DEC-127: los contadores del probe v3 eran
AGREGADOS por réplica (hybrid_grounding en el jsonl) — sin registro por-propuesta
(familia, span, causa de muerte) ni funnel downstream (accepted → bound → missing →
selected), no se puede saber dónde mueren las propuestas de Haiku para los 4
composites (obl_a5d9 / obl_015f / obl_b2043 / obl_7aa7).

Diseño (1 réplica, r1 de cada qid, determinista donde no hay red):
  - Fragmentos = exactamente los que el apply tocaría (attested ∩ citados en el
    borrador OFF r1), con la MISMA vista servida (_chunk_text → coverage_context_content).
  - cat018 se restringe al fragmento carrier del target (F8, TONOS) por disciplina de
    coste (feedback_cost_discipline); hp002/hp017 corren completos.
  - Por cada propuesta de Haiku: familia, span (cabeza), fate ∈ {rejected_family_or_empty,
    rejected_grounding, rejected_shape, rejected_overlap, accepted(+fold_relocated)} y
    si es TARGET-RELEVANTE (anchors léxicos del composite).
  - Por cada átomo aceptado (híbrido o determinista): funnel downstream con el borrador
    OFF almacenado — exigible en la ventana de cita, satisfied, good_form/paridad-display,
    seleccionado en el anexo (cap 4 / family-cap 2).

Uso:  python scripts/s274_hybrid_funnel_diag.py            → preflight ($0, sin red)
      python scripts/s274_hybrid_funnel_diag.py --execute  → paga Haiku (techo $0.10)
Salida: evals/s274_hybrid_funnel_diag_v1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
REPLICAS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
OUT = ROOT / "evals/s274_hybrid_funnel_diag_v1.json"
DEFAULT_ENV = ROOT / ".env"

COST_CEILING_USD = 0.10
HYBRID_PRICE_IN = 1.0  # USD/MTok Haiku 4.5 (mismos precios que el probe v3)
HYBRID_PRICE_OUT = 5.0

# Targets composites (DEC-131) y sus anchors léxicos de relevancia (foldeados):
TARGETS = {
    "hp002": {
        "obl_a5d9fa1f9253": ("valores nominales", "nominales"),
    },
    "cat018": {
        "obl_015f9b9aaa3a": ("tonos", "tono y volumen", "volumen"),
    },
    "hp017": {
        "obl_b2043cd4379b": ("instruccion de entrada", "condicion de entrada"),
        "obl_7aa723717412": ("instruccion de salida", "equipos asignados"),
    },
}
# cat018: solo el fragmento carrier del target (coste); None = todos los attested∩citados
FRAGMENT_RESTRICTION = {"cat018": {8}, "hp002": None, "hp017": None}
QIDS = ("hp002", "cat018", "hp017")


def _fold(text: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", (text or "").lower())
        if not unicodedata.combining(ch)
    )


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _target_hits(qid: str, span: str) -> list[str]:
    folded = _fold(span)
    return [
        obl
        for obl, anchors in TARGETS.get(qid, {}).items()
        if any(a in folded for a in anchors)
    ]


def _load_r1_drafts() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with REPLICAS.open(encoding="utf-8") as fh:
        for line in fh:
            rep = json.loads(line)
            if rep.get("replicate") == 1:
                out[str(rep["qid"])] = rep
    return out


def _instrumented_hybrid(
    mp, fragment_text: str, client, usage: dict, proposals_log: list[dict], qid: str,
    fragment_number: int,
) -> list[dict]:
    """Réplica del loop de detect_atoms_hybrid con registro POR-PROPUESTA."""
    det = mp.detect_atoms(fragment_text)
    for atom in det:
        atom.setdefault("meta", {})["origin"] = "det"
    atoms = list(det)
    if client is None or not fragment_text.strip():
        return atoms
    response = client.messages.create(
        model=mp.HYBRID_DETECTOR_MODEL,
        max_tokens=mp._HYBRID_MAX_TOKENS,
        temperature=0,
        tools=[{
            "name": "proponer_atomos",
            "description": "Registra los átomos estructurales propuestos (span verbatim).",
            "input_schema": mp.hybrid_proposal_schema(),
        }],
        tool_choice={"type": "tool", "name": "proponer_atomos"},
        messages=[{
            "role": "user",
            "content": mp._HYBRID_PROMPT.replace("<<<FRAGMENT>>>", fragment_text),
        }],
    )
    usage["input_tokens"] = usage.get("input_tokens", 0) + (
        getattr(response.usage, "input_tokens", 0) or 0
    )
    usage["output_tokens"] = usage.get("output_tokens", 0) + (
        getattr(response.usage, "output_tokens", 0) or 0
    )
    usage["calls"] = usage.get("calls", 0) + 1
    tool_use = next(b for b in response.content if b.type == "tool_use")
    payload = dict(tool_use.input)
    for i in range(1, mp._HYBRID_SLOTS + 1):
        family = str(payload.get(f"atom_{i}_family") or "").strip().upper()
        span = str(payload.get(f"atom_{i}_span") or "").strip()
        if not family and not span:
            continue
        entry: dict[str, Any] = {
            "qid": qid,
            "fragment_number": fragment_number,
            "slot": i,
            "family": family,
            "span_head": span[:110],
            "span_chars": len(span),
            "target_hits": _target_hits(qid, span),
        }
        proposals_log.append(entry)
        if family not in mp.FAMILIES or not span:
            entry["fate"] = "rejected_family_or_empty"
            continue
        grounded = mp.ground_hybrid_span(fragment_text, span)
        if grounded is None:
            entry["fate"] = "rejected_grounding"
            continue
        entry["fold_relocated"] = grounded != span
        atom = mp._atom_from_verbatim_span(family, grounded, fragment_text)
        if atom is None:
            entry["fate"] = "rejected_shape"
            continue
        if mp._overlaps_same_family(atom, atoms):
            entry["fate"] = "rejected_overlap"
            continue
        entry["fate"] = "accepted"
        atom.setdefault("meta", {})["origin"] = "hybrid"
        atom["meta"]["slot"] = i
        atoms.append(atom)
    atoms.sort(key=lambda a: (a["span_start"], a["family"]))
    return atoms


def run(execute: bool) -> dict:
    from src.rag import must_preserve as mp

    drafts = _load_r1_drafts()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rows = {r["qid"]: r for r in freeze["rows"]}

    client = None
    if execute:
        import anthropic

        client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0
        )

    report: dict[str, Any] = {
        "schema": "s274_hybrid_funnel_diag_v1",
        "mode": "execute" if execute else "preflight",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "inputs_sha256_lf": {
            "freeze": _sha256_lf(FREEZE),
            "replicas_v3": _sha256_lf(REPLICAS),
        },
        "design": {
            "replicas": 1,
            "drafts": "off_answer r1 almacenados (0 generaciones)",
            "fragment_restriction": {
                k: sorted(v) if v else None for k, v in FRAGMENT_RESTRICTION.items()
            },
            "cost_ceiling_usd": COST_CEILING_USD,
        },
        "per_qid": {},
        "proposals": [],
        "atom_funnel": [],
        "database_reads": 0,
        "database_writes": 0,
    }

    usage: dict[str, Any] = {}
    for qid in QIDS:
        rep = drafts[qid]
        draft = str(rep["off_answer"])
        row = rows[qid]
        chunks = row["context"]
        resolved = mp._query_resolved_ids(row["question"])
        catalog = mp._load_catalog()
        cited = mp.cited_fragment_numbers(draft)
        restriction = FRAGMENT_RESTRICTION.get(qid)
        eligible: dict[int, dict] = {}
        for idx, chunk in enumerate(chunks, start=1):
            if idx not in cited:
                continue
            if not mp.attest_identity(chunk.get("document_id"), resolved, catalog):
                continue
            if restriction is not None and idx not in restriction:
                continue
            eligible[idx] = chunk
        qinfo: dict[str, Any] = {
            "identity_resolved": bool(resolved),
            "cited_fragments": sorted(cited),
            "eligible_fragments": sorted(eligible),
            "served_view_chars_by_fragment": {},
        }
        report["per_qid"][qid] = qinfo
        if not execute:
            for idx, chunk in eligible.items():
                text = mp._chunk_text(chunk)
                qinfo["served_view_chars_by_fragment"][str(idx)] = len(text)
            continue

        missing: list[dict] = []
        for idx, chunk in eligible.items():
            text = mp._chunk_text(chunk)
            qinfo["served_view_chars_by_fragment"][str(idx)] = len(text)
            atoms = _instrumented_hybrid(
                mp, text, client, usage, report["proposals"], qid, idx
            )
            window = mp.citation_window(draft, idx)
            for atom in atoms:
                fate: dict[str, Any] = {
                    "qid": qid,
                    "fragment_number": idx,
                    "origin": atom["meta"].get("origin"),
                    "family": atom["family"],
                    "span_head": (atom.get("span_text") or "")[:110],
                    "target_hits": _target_hits(qid, atom.get("span_text") or ""),
                }
                report["atom_funnel"].append(fate)
                if not window.strip() or not mp.atom_exigible_in(atom, window):
                    fate["stage"] = "not_bound"
                    continue
                if mp.atom_satisfied(atom, draft):
                    fate["stage"] = "satisfied_in_draft"
                    continue
                meta = atom.setdefault("meta", {})
                meta["fragment_number"] = idx
                missing.append(atom)
                fate["stage"] = "missing"
        selected = mp._select_for_appendix(missing, draft)
        selected_keys = {
            (a["meta"].get("fragment_number"), a["span_start"], a["family"])
            for a in selected
        }
        for fate, atom in zip(
            [f for f in report["atom_funnel"] if f["qid"] == qid and f.get("stage") == "missing"],
            missing,
        ):
            in_appendix = (
                atom["meta"].get("fragment_number"),
                atom["span_start"],
                atom["family"],
            ) in selected_keys
            fate["stage"] = "appended" if in_appendix else "missing_not_selected"
            if not in_appendix:
                fate["excluded_by"] = (
                    "good_form_or_parity"
                    if not mp.atom_good_form(atom)
                    or (
                        atom["meta"].get("seven_segment_risk")
                        and not mp.display_parity_ok(atom, draft)
                    )
                    else "cap_or_dedup"
                )
        qinfo["appendix_size"] = len(selected)

    cost = (
        usage.get("input_tokens", 0) * HYBRID_PRICE_IN
        + usage.get("output_tokens", 0) * HYBRID_PRICE_OUT
    ) / 1_000_000
    report["hybrid_usage"] = dict(usage)
    report["actual_cost_usd"] = round(cost, 6)
    if execute and cost > COST_CEILING_USD:
        report["cost_ceiling_exceeded"] = True

    # resumen del funnel por target
    summary: dict[str, Any] = {}
    for qid, obls in TARGETS.items():
        for obl in obls:
            hits_p = [p for p in report["proposals"] if obl in p.get("target_hits", [])]
            hits_a = [a for a in report["atom_funnel"] if obl in a.get("target_hits", [])]
            summary[obl] = {
                "qid": qid,
                "proposals_target_relevant": len(hits_p),
                "proposal_fates": sorted({p.get("fate") for p in hits_p}),
                "atoms_target_relevant": len(hits_a),
                "atom_stages": sorted({str(a.get("stage")) for a in hits_a}),
            }
    report["target_summary"] = summary
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    args = parser.parse_args()
    if args.execute:
        env_path = Path(args.env_file)
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    report = run(execute=args.execute)
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(
        {
            "mode": report["mode"],
            "cost_usd": report.get("actual_cost_usd"),
            "usage": report.get("hybrid_usage"),
            "target_summary": report.get("target_summary"),
        },
        ensure_ascii=False,
        indent=2,
    ))
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
