#!/usr/bin/env python3
"""S270 — certificación DET-ONLY del probe v3 ($0; remediación C2 del ship-review Sol).

C2: el ON de prod es DETERMINISTA-only (el generador llama a apply sin detect_fn) pero
los probes v2/v3 midieron el brazo ON con el detector HÍBRIDO inyectado → el ON
shippeado no es el ON medido. Este script RE-APLICA el contrato SIN detect_fn (path
EXACTO de prod, flag on alrededor del apply) sobre los borradores OFF ALMACENADOS de
evals/s270_etapa2_probe_v3_replicas_v1.jsonl, con los chunks reconstruidos del freeze,
y re-agrega con la MISMA lógica de estabilidad → certifica el path mergeado con CERO
llamadas y CERO exposición nueva. Si obl_b6f6 NO convierte det-only, se declara: la
decisión híbrido-en-prod pasa a fork explícito del orquestador.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s270_etapa2_probe as probe  # noqa: E402

V3_REPLICAS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
V3_PREREG = ROOT / "evals/s270_etapa2_probe_v3_prereg_v1.yaml"
OUT = ROOT / "evals/s270_probe_det_certification_v1.json"


def main() -> int:
    import yaml

    probe.export_generation_env()
    from src.rag import must_preserve as mp

    prereg = yaml.safe_load(V3_PREREG.read_text(encoding="utf-8"))
    expected = prereg["frozen_inputs_sha256_lf_normalized"]["src/rag/must_preserve.py"]
    if probe.normalized_sha(ROOT / "src/rag/must_preserve.py") != expected:
        raise RuntimeError("certificación: must_preserve.py ≠ prereg v3 (drift)")
    rows = probe.load_freeze_rows()
    items = probe.load_score_items()
    protected = probe.protected_set(items)
    replicas = [
        json.loads(line)
        for line in V3_REPLICAS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(replicas) != len(probe.QIDS) * len(probe.REPLICATES):
        raise RuntimeError("certificación: réplicas v3 incompletas")
    raw_rows = []
    for rep in replicas:
        qid = rep["qid"]
        question = rows[qid]["question"]
        chunks = probe.served_chunks(rows[qid]["context"])
        off_answer = str(rep["off_answer"])
        os.environ["MUST_PRESERVE_CONTRACT"] = "on"
        try:
            # path EXACTO de prod: SIN detect_fn (determinista puro)
            on_answer, trace = mp.apply_must_preserve_contract(
                question, chunks, off_answer
            )
        finally:
            os.environ["MUST_PRESERVE_CONTRACT"] = "off"
        if mp.cited_fragment_numbers(off_answer) and trace is None:
            raise RuntimeError(f"{qid}: trace None con citas — flag inefectivo")
        raw_rows.append({
            "qid": qid, "replicate": rep["replicate"],
            "off_answer": off_answer, "on_answer": on_answer,
            "must_preserve_trace": trace,
        })
    scored = probe.score_replica_rows(raw_rows, items)
    agg = probe.aggregate(scored, items, protected, actual_cost=0.0)
    from src.rag.visual_gold import sealed_artifact, write_json

    body = {
        "status": agg["gate_verdict"],
        "proposito": (
            "Certificación DET-ONLY del path MERGEADO (remediación C2 ship-review "
            "Sol ts=2026-07-19T16:05:35): el ON de los probes v2/v3 corrió con "
            "detector híbrido inyectado; prod aplica determinista puro. Aquí el "
            "contrato se RE-APLICA sin detect_fn sobre los borradores OFF "
            "almacenados del probe v3 — 0 llamadas, 0 exposición nueva."
        ),
        "det_only": True,
        "source_replicas": str(V3_REPLICAS.relative_to(ROOT)).replace("\\", "/"),
        "must_preserve_sha256_lf": expected,
        "protected_set": {k: protected[k] for k in sorted(protected)},
        "aggregate": agg,
        "per_replica": [
            {
                "qid": r["qid"], "replicate": r["replicate"],
                "off_score": r["off_score"], "on_score": r["on_score"],
                "must_preserve_trace": r["must_preserve_trace"],
            }
            for r in scored
        ],
        "paid_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
        "nota_fork": (
            "Si obl_b6f6211be439 NO convierte det-only, la conversión del probe v3 "
            "dependía del brazo híbrido y la decisión híbrido-en-prod pasa a FORK "
            "explícito (declararlo, no shippearlo en silencio)."
        ),
    }
    write_json(OUT, sealed_artifact("s270_probe_det_certification_v1", body))
    print(json.dumps({
        "status": body["status"],
        "stable_conversions": agg["stable_conversions"],
        "stable_protected_regressions": agg["stable_protected_regressions"],
        "new_stable_conflicts": agg["new_stable_conflicts"],
        "out": str(OUT.relative_to(ROOT)),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
