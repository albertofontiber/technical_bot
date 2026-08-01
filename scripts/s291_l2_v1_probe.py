#!/usr/bin/env python3
"""s291 L2 — probes V1a/V1b pre-build ($0, dúo r2 mandato; diseño v2 §secuencia).

V1a (léxico/mecánica, H5+H6): para cada gold de la captura s289 donde la reserva
ORDENADA selecciona fila, tomar el QUOTE de su card y medir: átomos F-MANDATORY
detectados (`detect_atoms`) + si el quote pasa `_mandatory_clause_form` — la clase
«0-átomos silencioso» (p.ej. PRECAUCIÓN-only) queda CONTADA, no asumida.

V1b (vara del dedup, H2+Sol-6): sobre las answers REALES del probe de ventana-mala
(`s289_badwindow_paired_result_v1.json`), evaluar `atom_satisfied(átomo, answer)`
para los átomos del quote de hp002: en answers NO-conveyed debe dar False (si True
⇒ el apéndice sería no-op) y en answers conveyed debe dar True (si False ⇒ doble
aviso). Ambas direcciones medidas contra veredictos de juez ya pagados.

Salida: evals/s291_l2_v1_probe_result_v1.json
"""
from __future__ import annotations

import copy
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["OBLIGATION_RESERVE_ORDERED"] = "on"   # vector de ship (H1)
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from src.rag.rerank_pool_coverage import (  # noqa: E402
    select_obligation_warning_reserve,
)
from src.rag.must_preserve import (  # noqa: E402
    FAMILY_MANDATORY,
    _mandatory_clause_form,
    atom_satisfied,
    detect_atoms,
)

CAPTURE = ROOT / "evals" / "s289_g1_sweep39_capture_v1.json.gz"
BADWINDOW = ROOT / "evals" / "s289_badwindow_paired_result_v1.json"
OUT = ROOT / "evals" / "s291_l2_v1_probe_result_v1.json"


def main() -> int:
    with gzip.open(CAPTURE, "rt", encoding="utf-8") as fh:
        captured = json.load(fh)

    # ── V1a: quotes reales de la reserva ordenada sobre los 39 golds ──────────
    v1a = []
    for qid, entry in captured["golds"].items():
        rows, trace = select_obligation_warning_reserve(
            entry["query"], copy.deepcopy(entry["pool"]), copy.deepcopy(entry["prefix"])
        )
        if not rows:
            continue
        card = (rows[0].get("coverage_cards") or [{}])[0]
        quote = card.get("quote") or ""
        atoms = [a for a in detect_atoms(quote) if a.get("family") == FAMILY_MANDATORY]
        v1a.append({
            "qid": qid,
            "row_id": str(rows[0].get("id"))[:8],
            "quote_chars": len(quote),
            "n_mandatory_atoms": len(atoms),
            "clause_form_ok": bool(_mandatory_clause_form(quote)),
            "quote_head": quote[:90],
        })
    zero_atom = [r for r in v1a if r["n_mandatory_atoms"] == 0]

    # ── V1b: vara del dedup sobre answers reales con veredicto de juez ────────
    bw = json.loads(BADWINDOW.read_text(encoding="utf-8"))
    hp = bw["hp002_badwindow"]
    hp_row = next(r for r in v1a if r["qid"] == "hp002") if any(
        r["qid"] == "hp002" for r in v1a) else None
    # átomos del quote real de hp002 en ESTA captura (la misma vía que V1a)
    entry = captured["golds"]["hp002"]
    rows, _ = select_obligation_warning_reserve(
        entry["query"], copy.deepcopy(entry["pool"]), copy.deepcopy(entry["prefix"])
    )
    v1b = {"skipped": True}
    if rows:
        quote = (rows[0].get("coverage_cards") or [{}])[0].get("quote") or ""
        atoms = [a for a in detect_atoms(quote) if a.get("family") == FAMILY_MANDATORY]
        checks = []
        for arm in ("off", "on"):
            arm_data = hp["arms"][arm]
            for i, (ans, rep) in enumerate(zip(arm_data["answers"], arm_data["reps"])):
                conveyed = rep["conveyed"]
                sat = [bool(atom_satisfied(a, ans)) for a in atoms]
                # regla v2: dedup dispara solo si TODOS los átomos satisfechos
                dedup_fires = bool(sat) and all(sat)
                ok = (dedup_fires == conveyed)  # esperado: satisfied ⟺ conveyed
                checks.append({"arm": arm, "rep": i, "judge_conveyed": conveyed,
                               "atoms_satisfied": sat, "dedup_fires": dedup_fires,
                               "matches_judge": ok})
        v1b = {"skipped": False, "n_atoms": len(atoms),
               "checks": checks,
               "mismatches": [c for c in checks if not c["matches_judge"]]}

    result = {
        "instrument": "s291_l2_v1_probe_result_v1",
        "flag_vector": {"OBLIGATION_RESERVE_ORDERED": "on"},
        "v1a": {"n_golds_con_reserva": len(v1a),
                "n_zero_atom_quotes": len(zero_atom),
                "zero_atom": zero_atom, "rows": v1a},
        "v1b": v1b,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"V1a: reserva sirve en {len(v1a)} golds · quotes con 0 átomos F-MANDATORY: "
          f"{len(zero_atom)} {[r['qid'] for r in zero_atom]}")
    if not v1b.get("skipped"):
        print(f"V1b: {len(v1b['mismatches'])} mismatches dedup⟷juez de "
              f"{len(v1b['checks'])} checks")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
