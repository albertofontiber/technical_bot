#!/usr/bin/env python3
"""S269 Etapa 1 — gate detector-vs-gold POR FAMILIA (determinista, $0, sin red).

Recomputa el detector (src/rag/must_preserve.py::detect_atoms) sobre el texto congelado de
la cohorte y lo compara con el gold final del etiquetado dual (Luna+Haiku, árbitro Sonnet).
Gates pre-declarados en el prereg (lección S249 CONSERVADA — recall como GATE, no reporting):

  por familia:  recall ≥ 0.80  ·  precisión ≥ 0.95
  negativos:    FP = 0 (ningún disparo del detector sobre fragmentos de los buckets
                negative_screened / random_pure cuyo gold final es negativo en TODAS
                las familias)

Además estima el FN del PRE-SCREEN con el bucket random_pure (fragmentos elegidos por azar
puro: gold-positivos donde el detector no disparó ⇒ el pre-screen los habría perdido).

Output: evals/s269_stage1_gate_v1.yaml
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola Windows cp1252

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag import must_preserve as mp  # noqa: E402

EVALS = ROOT / "evals"
COHORT_PATH = EVALS / "s269_structural_cohort_v1.jsonl"
PREREG_PATH = EVALS / "s269_structural_cohort_prereg_v1.yaml"
LABELS_PATH = EVALS / "s269_structural_cohort_labels_v1.jsonl"
GATE_PATH = EVALS / "s269_stage1_gate_v1.yaml"

FAMILY_BY_KEY = {
    "frange": "F-RANGE",
    "fbundle": "F-BUNDLE",
    "fmandatory": "F-MANDATORY",
    "fcount": "F-COUNT",
}
NEGATIVE_BUCKETS = {"negative_screened", "random_pure"}

RECALL_MIN = 0.80
PRECISION_MIN = 0.95
FP_NEGATIVES_MAX = 0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    cohort = load_jsonl(COHORT_PATH)
    if sha256_file(COHORT_PATH) != prereg["cohort_artifact"]["sha256"]:
        raise RuntimeError("freeze roto: la cohorte no coincide con el prereg")
    if not LABELS_PATH.exists():
        raise RuntimeError(
            "faltan las etiquetas: corre scripts/s269_label_structural_cohort.py --execute"
        )
    labels = {r["fragment_id"]: r for r in load_jsonl(LABELS_PATH)}

    # verificación de integridad texto↔etiqueta (sha del fragmento congelado)
    for row in cohort:
        rec = labels.get(row["fragment_id"])
        if rec is not None and rec.get("sha256") != row["sha256"]:
            raise RuntimeError(
                f"sha256 del fragmento {row['fragment_id']} ≠ etiqueta (drift)"
            )

    per_family: dict[str, dict] = {}
    detector_fired: dict[str, set[str]] = {}   # fragment_id -> familias disparadas
    golded = 0
    discarded = 0
    unlabeled = 0

    for row in cohort:
        atoms = mp.detect_atoms(row["texto"])
        detector_fired[row["fragment_id"]] = {a["family"] for a in atoms}

    for row in cohort:
        rec = labels.get(row["fragment_id"])
        if rec is None:
            unlabeled += 1
        elif rec.get("status") != "gold" or rec.get("final") is None:
            discarded += 1
        else:
            golded += 1

    for key, family in FAMILY_BY_KEY.items():
        tp = fp = fn = tn = 0
        for row in cohort:
            rec = labels.get(row["fragment_id"])
            if rec is None or rec.get("status") != "gold" or rec.get("final") is None:
                continue
            gold = bool(rec["final"][key])
            fired = family in detector_fired[row["fragment_id"]]
            if gold and fired:
                tp += 1
            elif gold and not fired:
                fn += 1
            elif not gold and fired:
                fp += 1
            else:
                tn += 1
        recall = tp / (tp + fn) if (tp + fn) else None
        precision = tp / (tp + fp) if (tp + fp) else None
        recall_pass = recall is not None and recall >= RECALL_MIN
        precision_pass = precision is not None and precision >= PRECISION_MIN
        per_family[family] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "gold_positives": tp + fn,
            "recall": round(recall, 4) if recall is not None else None,
            "precision": round(precision, 4) if precision is not None else None,
            "recall_gate": f">= {RECALL_MIN}",
            "precision_gate": f">= {PRECISION_MIN}",
            "verdict": (
                "GO" if (recall_pass and precision_pass)
                else "NO_GO" if (recall is not None and precision is not None)
                else "UNDETERMINED_INSUFFICIENT_GOLD"
            ),
        }

    # FP=0 sobre negativos gold-confirmados (buckets negative_screened + random_pure)
    fp_negative_rows = []
    negatives_gold_confirmed = 0
    for row in cohort:
        if row["bucket"] not in NEGATIVE_BUCKETS:
            continue
        rec = labels.get(row["fragment_id"])
        if rec is None or rec.get("status") != "gold" or rec.get("final") is None:
            continue
        if any(rec["final"][k] for k in FAMILY_BY_KEY):
            continue  # el gold dice que SÍ hay átomo: no es negativo puro
        negatives_gold_confirmed += 1
        fired = detector_fired[row["fragment_id"]]
        if fired:
            fp_negative_rows.append(
                {"fragment_id": row["fragment_id"], "bucket": row["bucket"],
                 "fired": sorted(fired)}
            )

    # FN del pre-screen: bucket random_pure (azar puro), gold-positivo sin disparo
    prescreen_fn = []
    random_pure_gold = 0
    for row in cohort:
        if row["bucket"] != "random_pure":
            continue
        rec = labels.get(row["fragment_id"])
        if rec is None or rec.get("status") != "gold" or rec.get("final") is None:
            continue
        random_pure_gold += 1
        for key, family in FAMILY_BY_KEY.items():
            if rec["final"][key] and family not in detector_fired[row["fragment_id"]]:
                prescreen_fn.append(
                    {"fragment_id": row["fragment_id"], "family": family}
                )

    fp_gate_pass = len(fp_negative_rows) <= FP_NEGATIVES_MAX
    family_verdicts = {f: per_family[f]["verdict"] for f in per_family}
    all_go = fp_gate_pass and all(v == "GO" for v in family_verdicts.values())
    any_undetermined = any(
        v == "UNDETERMINED_INSUFFICIENT_GOLD" for v in family_verdicts.values()
    )
    overall = (
        "GO" if all_go
        else "PARTIAL_UNDETERMINED" if any_undetermined and fp_gate_pass
        and not any(v == "NO_GO" for v in family_verdicts.values())
        else "NO_GO"
    )

    gate = {
        "schema": "s269_stage1_gate_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detector_module": "src/rag/must_preserve.py",
        "cohort_sha256": sha256_file(COHORT_PATH),
        "labels_sha256": sha256_file(LABELS_PATH),
        "prereg_sha256": sha256_file(PREREG_PATH),
        "population": {
            "cohort_rows": len(cohort),
            "gold_rows": golded,
            "discarded_rows": discarded,
            "unlabeled_rows": unlabeled,
        },
        "per_family": per_family,
        "fp_on_gold_negatives": {
            "gate": f"== {FP_NEGATIVES_MAX}",
            "negatives_gold_confirmed": negatives_gold_confirmed,
            "fp_count": len(fp_negative_rows),
            "fp_rows": fp_negative_rows,
            "verdict": "GO" if fp_gate_pass else "NO_GO",
        },
        "prescreen_fn_estimate": {
            "definition": (
                "gold-positivos del bucket random_pure (azar puro) donde el detector "
                "no disparó esa familia — estima lo que el pre-screen habría perdido"
            ),
            "random_pure_gold_rows": random_pure_gold,
            "fn_rows": prescreen_fn,
        },
        "overall_verdict": overall,
        "next_step_if_go": (
            "Etapa 2 SOLO tras adjudicación formal de Alberto de la reapertura de la "
            "familia s222/s223 (diseño §1 Etapa 2, dúo C1/F2) — probe único a los 4 "
            "targets, gate tipo DEC-112, K=3, control same-model"
        ),
    }
    GATE_PATH.write_text(
        yaml.safe_dump(gate, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Gate escrito: {GATE_PATH.relative_to(ROOT)}")
    for family, res in per_family.items():
        print(f"  {family}: recall={res['recall']} precision={res['precision']} "
              f"→ {res['verdict']}")
    print(f"  FP en negativos gold: {len(fp_negative_rows)} "
          f"→ {'GO' if fp_gate_pass else 'NO_GO'}")
    print(f"  VEREDICTO GLOBAL: {overall}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
