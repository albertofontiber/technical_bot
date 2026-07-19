#!/usr/bin/env python3
"""S274 Bloque C — diagnóstico C1 ($0, sin red, sin DB): la vista SERVIDA de la lane
de coverage trunca el bloque-warning de hp017 F12 (obl_0d6a, carrier del merge DEC-125).

Verifica y PERSISTE, sobre el freeze s113 (`evals/s113_full_contexts_freeze_v1.json`)
y los borradores OFF almacenados del probe v3:

  1. F12 (chunk d27b1a1b, lane same_blob_structural_neighbor_coverage_v1) tiene 2.864
     chars crudos pero la vista servida (`coverage_context_content`) son los spans de
     las coverage_cards mergeadas ([419,673]+[675,1032]+[1694,2052] ≈ 1.037 chars con
     separadores). NO hay cap de chars: es SELECCIÓN DE SPANS por diseño (docstring de
     coverage_context_content, commits s110 75720fc / s111 23cfa27).
  2. El bloque-warning (offsets ~2479-2724) queda FUERA de toda card → ni el generador
     ni el detector must-preserve (que usa la MISMA vista vía _chunk_text) lo ven.
  3. Con la vista COMPLETA: detect_atoms produce los 2 átomos F-MANDATORY del bloque
     (triggers 'evite' / 'de vital importancia'); el átomo carrier pasa atom_good_form;
     y con los borradores OFF almacenados (v3 r1-r3) F12 está CITADO y ambos átomos
     son exigibles (overlap procedimental ≥2) → el fix de vista convertiría obl_0d6a
     vía el anexo determinista, sujeto al cap de selección (MANDATORY = prioridad 0).
  4. Hallazgo adicional: el span fuente de obl_b2043 («Instrucción de entrada», offset
     ~1427) TAMBIÉN queda fuera de las cards → obl_b2043 comparte causa serving-view
     (refina el mapa causal DEC-131 que lo clasificaba solo como composite-híbrido).

Uso: python scripts/s274_serving_view_diag.py  → evals/s274_serving_view_diag_v1.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.must_preserve import (  # noqa: E402
    atom_exigible_in,
    atom_good_form,
    citation_window,
    cited_fragment_numbers,
    detect_atoms,
    _content_tokens,
)
from src.rag.post_rerank_coverage import (  # noqa: E402
    coverage_context_content,
    has_exact_served_coverage_receipt,
    is_validated_coverage_chunk,
)

FREEZE = ROOT / "evals/s113_full_contexts_freeze_v1.json"
REPLICAS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
OUT = ROOT / "evals/s274_serving_view_diag_v1.json"

F12_INDEX = 12  # 1-based fragment number en el contexto congelado de hp017
F12_CHUNK_PREFIX = "d27b1a1b"

PROBES = {
    "warn_evite_contradictorias": "evite las logicas contradictorias",
    "warn_vital_importancia": "es de vital importancia probar rigurosamente",
    "b2043_instruccion_entrada": "instruccion de entrada",
    "7aa7_instruccion_salida": "instruccion de salida",
    "7aa7_equipos_asignados": "equipos asignados",
}


def _fold(text: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", (text or "").lower())
        if not unicodedata.combining(ch)
    )


def _sha256_lf(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    row = next(r for r in freeze["rows"] if r["qid"] == "hp017")
    chunk = row["context"][F12_INDEX - 1]
    if not str(chunk.get("id") or "").startswith(F12_CHUNK_PREFIX):
        raise RuntimeError("F12 no es el chunk esperado — freeze drift")
    raw = str(chunk.get("content") or "")
    served = coverage_context_content(chunk)
    folded_raw, folded_served = _fold(raw), _fold(served)

    report: dict = {
        "schema": "s274_serving_view_diag_v1",
        "inputs_sha256_lf": {
            "freeze": _sha256_lf(FREEZE),
            "replicas_v3": _sha256_lf(REPLICAS),
        },
        "fragment": {
            "qid": "hp017",
            "fragment_number": F12_INDEX,
            "chunk_id": str(chunk.get("id")),
            "retrieval_lane": chunk.get("retrieval_lane"),
            "page_number": chunk.get("page_number"),
            "raw_chars": len(raw),
            "served_chars": len(served),
            "validated_coverage_chunk": is_validated_coverage_chunk(chunk),
            "served_receipt_ok": has_exact_served_coverage_receipt(chunk),
            "coverage_cards_spans": [
                [int(c["start"]), int(c["end"])]
                for c in (chunk.get("coverage_cards") or [])
            ],
        },
        "probes": {},
        "mandatory_atoms_full_view": [],
        "mandatory_atoms_served_view": 0,
        "replica_binding": [],
    }

    for name, probe in PROBES.items():
        report["probes"][name] = {
            "raw_offset": folded_raw.find(probe),
            "in_raw": probe in folded_raw,
            "in_served": probe in folded_served,
        }

    full_mandatory = [a for a in detect_atoms(raw) if a["family"] == "F-MANDATORY"]
    for atom in full_mandatory:
        report["mandatory_atoms_full_view"].append(
            {
                "span": [atom["span_start"], atom["span_end"]],
                "triggers": atom["meta"]["triggers"],
                "good_form": atom_good_form(atom),
                "text_head": atom["span_text"][:120],
            }
        )
    report["mandatory_atoms_served_view"] = sum(
        1 for a in detect_atoms(served) if a["family"] == "F-MANDATORY"
    )

    with REPLICAS.open(encoding="utf-8") as fh:
        for line in fh:
            rep = json.loads(line)
            if rep.get("qid") != "hp017":
                continue
            draft = str(rep.get("off_answer") or "")
            cited = cited_fragment_numbers(draft)
            window = citation_window(draft, F12_INDEX)
            atoms = []
            for atom in full_mandatory:
                proc = set(atom["meta"].get("procedural_context_tokens") or [])
                atoms.append(
                    {
                        "span_start": atom["span_start"],
                        "exigible_in_window": atom_exigible_in(atom, window),
                        "procedural_overlap": len(
                            proc & set(_content_tokens(window))
                        ),
                    }
                )
            report["replica_binding"].append(
                {
                    "replicate": rep.get("replicate"),
                    "f12_cited": F12_INDEX in cited,
                    "citation_window_chars": len(window),
                    "atoms": atoms,
                }
            )

    verdict_bits = [
        all(p["in_raw"] and not p["in_served"] for p in (
            report["probes"]["warn_evite_contradictorias"],
            report["probes"]["warn_vital_importancia"],
        )),
        len(report["mandatory_atoms_full_view"]) >= 2,
        report["mandatory_atoms_served_view"] == 0,
        all(rb["f12_cited"] for rb in report["replica_binding"]),
        all(
            a["exigible_in_window"]
            for rb in report["replica_binding"]
            for a in rb["atoms"]
        ),
    ]
    report["verdict"] = {
        "serving_view_truncation_confirmed": verdict_bits[0],
        "full_view_would_detect_warning_block": verdict_bits[1],
        "served_view_blind": verdict_bits[2],
        "f12_cited_all_replicas": verdict_bits[3],
        "binding_would_hold_all_replicas": verdict_bits[4],
        "b2043_shares_serving_view_cause": (
            report["probes"]["b2043_instruccion_entrada"]["in_raw"]
            and not report["probes"]["b2043_instruccion_entrada"]["in_served"]
        ),
        "all_pass": all(verdict_bits),
    }
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["verdict"], indent=2))
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
