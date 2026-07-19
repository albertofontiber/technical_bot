#!/usr/bin/env python3
"""S271 — certificación DET-ONLY v2 ($0) del path de prod con los GUARDS DE ACTIVACIÓN.

Sucesora de scripts/s270_probe_det_certification.py (v1: GO, obl_b6f6 3/3). Cambios
s271 DECLARADOS — el sha vivo de must_preserve.py YA NO coincide con el pin del prereg
v3 y ese drift es INTENCIONAL, se registra aquí (expected vs actual):
  - must_preserve v4: dedup del render + guard de contenido informativo + tie estricto
    del F-COUNT a distancia (bloqueadores 1-3 de DEC-127b);
  - instrumento: disclosure de obl_872c re-specced a OPCIÓN 1 «evidencia servida»
    (DEC-128, adjudicación de Alberto).

Re-aplica el contrato SIN detect_fn (path EXACTO de prod, flag on alrededor del apply)
sobre los borradores OFF ALMACENADOS del probe v3 y re-agrega con la MISMA lógica de
estabilidad. Verifica: (1) obl_b6f6 SIGUE convirtiendo 3/3 det-only con los guards
nuevos; (2) el disclosure de obl_872c (tira de etiquetas OCR CON texto) NO lo mata el
guard de contenido informativo. CERO llamadas pagadas, CERO DB.
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
V1_CERT = ROOT / "evals/s270_probe_det_certification_v1.json"
OUT = ROOT / "evals/s271_probe_det_certification_v2.json"

B6F6 = "obl_b6f6211be439"
OBL_872C = "obl_872c35fb41d7"
# Etiquetas de la tira OCR F1 (hp017): el guard de contenido informativo NO debe
# matar el lado-enumeración del disclosure — tiene texto real, no celdas en blanco.
_F1_STRIP_LABELS = ("Estándar", "Fijo", "Est.Ext.", "No Silenc.", "No Sil.Ext")


def main() -> int:
    import yaml

    probe.export_generation_env()
    from src.rag import must_preserve as mp

    prereg = yaml.safe_load(V3_PREREG.read_text(encoding="utf-8"))
    pinned = prereg["frozen_inputs_sha256_lf_normalized"]["src/rag/must_preserve.py"]
    actual = probe.normalized_sha(ROOT / "src/rag/must_preserve.py")
    declared_drift = {
        "src/rag/must_preserve.py": {
            "prereg_v3_pinned_sha256_lf": pinned,
            "actual_sha256_lf": actual,
            "intentional": actual != pinned,
            "delta": (
                "s271 guards de activación DEC-127b (dedup render + contenido "
                "informativo + tie estricto F-COUNT) — validados en Etapa 1 v7 "
                "seed-275; ver evals/s271_stage1_v7_gate_v1.yaml"
            ),
        },
        "scripts/s270_etapa2_probe.py": {
            "delta": (
                "disclosure_covered re-specced a OPCIÓN 1 «evidencia servida» "
                "(DEC-128, adjudicación de Alberto S271)"
            ),
        },
    }
    rows = probe.load_freeze_rows()
    items = probe.load_score_items()
    protected = probe.protected_set(items)
    replicas = [
        json.loads(line)
        for line in V3_REPLICAS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(replicas) != len(probe.QIDS) * len(probe.REPLICATES):
        raise RuntimeError("certificación v2: réplicas v3 incompletas")
    raw_rows = []
    survival_872c = []
    for rep in replicas:
        qid = rep["qid"]
        question = rows[qid]["question"]
        chunks = probe.served_chunks(rows[qid]["context"])
        off_answer = str(rep["off_answer"])
        os.environ["MUST_PRESERVE_CONTRACT"] = "on"
        try:
            # path EXACTO de prod: SIN detect_fn (determinista puro, guards v4)
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
        if qid == "hp017":
            appendix = (
                on_answer[len(off_answer):]
                if on_answer.startswith(off_answer) else ""
            )
            survival_872c.append({
                "replicate": rep["replicate"],
                "appendix_len": len(appendix.strip()),
                "disclosure_marker": "el manual también indica" in appendix,
                "f1_strip_labels_in_appendix": all(
                    label in appendix for label in _F1_STRIP_LABELS
                ),
                "disclosure_covered_on": probe.disclosure_covered(on_answer),
                "disclosure_covered_off": probe.disclosure_covered(off_answer),
            })
    scored = probe.score_replica_rows(raw_rows, items)
    agg = probe.aggregate(scored, items, protected, actual_cost=0.0)
    b6f6_detail = agg["eligible_detail"][B6F6]
    b6f6_ok = bool(b6f6_detail["stable_conversion"]) and (
        b6f6_detail["on_covered"] == len(probe.REPLICATES)
    )
    status = agg["gate_verdict"] if b6f6_ok else "NO_GO"
    from src.rag.visual_gold import sealed_artifact, write_json

    body = {
        "status": status,
        "proposito": (
            "Certificación DET-ONLY v2 del path de prod con los guards de "
            "ACTIVACIÓN s271 (DEC-127b) y el disclosure opción-1 (DEC-128): "
            "re-aplica el contrato sin detect_fn sobre los borradores OFF "
            "almacenados del probe v3 — 0 llamadas, 0 exposición nueva. Verifica "
            "que obl_b6f6 sigue 3/3 y que el guard de contenido informativo NO "
            "mata el disclosure de obl_872c (etiquetas CON texto ≠ celdas en "
            "blanco)."
        ),
        "predecessor": str(V1_CERT.relative_to(ROOT)).replace("\\", "/"),
        "det_only": True,
        "source_replicas": str(V3_REPLICAS.relative_to(ROOT)).replace("\\", "/"),
        "declared_drift": declared_drift,
        "protected_set": {k: protected[k] for k in sorted(protected)},
        "b6f6_check": {"obligation_id": B6F6, "required": "3/3 estable",
                       "detail": b6f6_detail, "pass": b6f6_ok},
        "obl_872c_detail": agg["eligible_detail"][OBL_872C],
        "obl_872c_informative_survival": survival_872c,
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
    }
    write_json(OUT, sealed_artifact("s271_probe_det_certification_v2", body))
    print(json.dumps({
        "status": body["status"],
        "b6f6": {"on_covered": b6f6_detail["on_covered"],
                 "stable_conversion": b6f6_detail["stable_conversion"]},
        "obl_872c": body["obl_872c_detail"],
        "survival_872c": survival_872c,
        "stable_conversions": agg["stable_conversions"],
        "stable_protected_regressions": agg["stable_protected_regressions"],
        "new_stable_conflicts": agg["new_stable_conflicts"],
        "out": str(OUT.relative_to(ROOT)),
    }, indent=2, ensure_ascii=False))
    return 0 if status == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
