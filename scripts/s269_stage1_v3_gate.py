#!/usr/bin/env python3
"""S269 Etapa 1 v3 — gate del harness de mutaciones (determinista, $0, sin red).

Spec: evals/s269_stage1_v3_mutation_spec_v1.md. Correcciones que encarna:
  C1  puntúa por MUTACIÓN individual (átomo), no booleano de familia, con
      cobertura mínima declarada y filas no puntuables LISTADAS.
  C4  freeze completo: ABORTA si el sha256 de must_preserve.py, del harness, de
      los templates o de la cohorte difiere del prereg.
  M7  los umbrales se LEEN del prereg (única fuente); la constante espejo de abajo
      es SOLO cross-check anti-tamper (patrón del ejecutor visual v3) — si prereg y
      espejo difieren, ABORTA (alguien editó uno sin el otro).

Output: evals/s269_stage1_v3_gate_v1.yaml — veredicto POR BRAZO (det-solo vs
híbrido; NOT_RUN si el brazo no tiene resultados).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola Windows cp1252

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVALS = ROOT / "evals"
PREREG_PATH = EVALS / "s269_stage1_v3_prereg.yaml"
COHORT_PATH = EVALS / "s269_mutation_cohort_v2.jsonl"
RESULTS = {
    "det_only": EVALS / "s269_stage1_v3_results_det.jsonl",
    "hybrid": EVALS / "s269_stage1_v3_results_hybrid.jsonl",
}
GATE_PATH = EVALS / "s269_stage1_v3_gate_v1.yaml"

# Espejo anti-tamper (M7): NO es la fuente de los umbrales — el gate usa el prereg;
# si difieren, se aborta.
MIRROR_GATES = {
    "mutation_recall_min_per_family": 0.80,
    "clean_noise_fp_max": 0,
    "cross_binding_fp_max": 0,
    "attestation_block_appends_max": 0,
    "coverage_min": 0.90,
}

FAMILIES = ("F-RANGE", "F-BUNDLE", "F-MANDATORY", "F-COUNT")


def sha256_file(path: Path) -> str:
    # CRLF->LF (precedente s198): el freeze sobrevive a checkouts Windows.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _harness_templates_sha() -> str:
    spec = importlib.util.spec_from_file_location(
        "s269_mutation_harness", ROOT / "scripts/s269_mutation_harness.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.templates_sha256()


def verify_freeze(prereg: dict) -> dict:
    frozen = prereg["freeze"]
    actual = {
        "must_preserve_sha256": sha256_file(ROOT / "src/rag/must_preserve.py"),
        "harness_sha256": sha256_file(ROOT / "scripts/s269_mutation_harness.py"),
        "templates_sha256": _harness_templates_sha(),
        "cohort_sha256": sha256_file(COHORT_PATH),
    }
    for key, value in actual.items():
        if frozen[key] != value:
            raise RuntimeError(
                f"FREEZE ROTO (C4): {key} difiere del prereg "
                f"({frozen[key][:12]}… ≠ {value[:12]}…) — ABORT"
            )
    return actual


def score_arm(rows: list[dict], gates: dict) -> dict:
    mutation_rows = [r for r in rows if r["measure"] == "mutation"]
    clean_rows = [r for r in rows if r["measure"] == "clean"]
    cross_rows = [r for r in rows if r["measure"] == "cross"]
    attest_rows = [r for r in rows if r["measure"] == "attestation"]

    generated = len(mutation_rows) + len(clean_rows) + len(cross_rows) + len(attest_rows)
    unpuntuable = [r for r in rows if not r.get("puntuable")]
    coverage = (generated - len(unpuntuable)) / generated if generated else 0.0
    coverage_pass = coverage >= float(gates["coverage_min"])

    per_family: dict[str, dict] = {}
    for fam in FAMILIES:
        fam_rows = [r for r in mutation_rows if r["familia"] == fam and r.get("puntuable")]
        detected = [r for r in fam_rows if r.get("detected")]
        by_kind: dict[str, dict] = {}
        for r in fam_rows:
            slot = by_kind.setdefault(r["mutation"], {"puntuable": 0, "detected": 0})
            slot["puntuable"] += 1
            slot["detected"] += 1 if r.get("detected") else 0
        recall = len(detected) / len(fam_rows) if fam_rows else None
        recall_pass = (
            recall is not None
            and recall >= float(gates["mutation_recall_min_per_family"])
        )
        per_family[fam] = {
            "mutation_rows_puntuables": len(fam_rows),
            "detected": len(detected),
            "mutation_recall": round(recall, 4) if recall is not None else None,
            "recall_gate": f">= {gates['mutation_recall_min_per_family']}",
            "by_mutation_kind": by_kind,
            "missed_keys": [r["key"] for r in fam_rows if not r.get("detected")],
            "verdict": (
                "GO" if recall_pass
                else "NO_GO" if recall is not None
                else "UNDETERMINED_NO_ROWS"
            ),
        }

    clean_fp = [r for r in clean_rows if r.get("puntuable") and r.get("fp")]
    cross_fp = [r for r in cross_rows if r.get("puntuable") and r.get("fp")]
    attest_appends = sum(r.get("appends", 0) for r in attest_rows)
    attest_controls_ok = all(
        r.get("attest_positive_control") and r.get("attest_blocked")
        for r in attest_rows
    ) if attest_rows else False

    clean_pass = len(clean_fp) <= int(gates["clean_noise_fp_max"])
    cross_pass = len(cross_fp) <= int(gates["cross_binding_fp_max"])
    attest_pass = (
        attest_appends <= int(gates["attestation_block_appends_max"])
        and attest_controls_ok
    )
    family_verdicts = {f: per_family[f]["verdict"] for f in per_family}
    all_go = (
        clean_pass and cross_pass and attest_pass and coverage_pass
        and all(v == "GO" for v in family_verdicts.values())
    )
    any_undetermined = any(
        v == "UNDETERMINED_NO_ROWS" for v in family_verdicts.values()
    )
    overall = (
        "GO" if all_go
        else "PARTIAL_UNDETERMINED" if any_undetermined and clean_pass and cross_pass
        and attest_pass and coverage_pass
        and not any(v == "NO_GO" for v in family_verdicts.values())
        else "NO_GO"
    )
    return {
        "rows_total": generated,
        "coverage": {
            "value": round(coverage, 4),
            "gate": f">= {gates['coverage_min']}",
            "unpuntuable_rows": [
                {"key": r["key"], "reason": r.get("skip_reason", "")}
                for r in unpuntuable
            ],
            "verdict": "GO" if coverage_pass else "NO_GO",
        },
        "per_family": per_family,
        "clean_noise": {
            "rows": len([r for r in clean_rows if r.get("puntuable")]),
            "fp_count": len(clean_fp),
            "gate": f"<= {gates['clean_noise_fp_max']}",
            "fp_keys": [r["key"] for r in clean_fp],
            "verdict": "GO" if clean_pass else "NO_GO",
        },
        "cross_binding": {
            "rows": len([r for r in cross_rows if r.get("puntuable")]),
            "fp_count": len(cross_fp),
            "gate": f"<= {gates['cross_binding_fp_max']}",
            "fp_keys": [r["key"] for r in cross_fp],
            "verdict": "GO" if cross_pass else "NO_GO",
        },
        "attestation_block": {
            "rows": len(attest_rows),
            "appends": attest_appends,
            "positive_and_block_controls_ok": attest_controls_ok,
            "gate": f"<= {gates['attestation_block_appends_max']} (y controles OK)",
            "verdict": "GO" if attest_pass else "NO_GO",
        },
        "overall_verdict": overall,
    }


def main() -> int:
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    gates = prereg["gates"]
    for key, value in MIRROR_GATES.items():
        if float(gates[key]) != float(value):
            raise RuntimeError(
                f"ANTI-TAMPER (M7): umbral '{key}' del prereg ({gates[key]}) ≠ "
                f"espejo del gate ({value}) — ABORT; reconciliar explícitamente"
            )
    freeze_actual = verify_freeze(prereg)
    print("Freeze verificado (C4): 4/4 sha coinciden con el prereg")

    arms: dict[str, dict] = {}
    for arm, path in RESULTS.items():
        rows = load_jsonl(path)
        if not rows:
            arms[arm] = {"overall_verdict": "NOT_RUN", "rows_total": 0}
            continue
        arms[arm] = score_arm(rows, gates)
        arms[arm]["results_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
        arms[arm]["results_sha256"] = sha256_file(path)

    gate = {
        "schema": "s269_stage1_v3_gate_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec_ref": "evals/s269_stage1_v3_mutation_spec_v1.md",
        "prereg_sha256": sha256_file(PREREG_PATH),
        "freeze_verified": freeze_actual,
        "gates_source": "prereg (única fuente; espejo anti-tamper verificado)",
        "gates": gates,
        "arms": arms,
        "next_step_if_go": (
            "Etapa 2 SOLO tras adjudicación formal de Alberto de la reapertura "
            "s222/s223 (diseño §1 Etapa 2, dúo C1/F2) — probe único a los 4 targets, "
            "gate tipo DEC-112, K=3, control same-model"
        ),
    }
    GATE_PATH.write_text(
        yaml.safe_dump(gate, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8", newline="\n",
    )
    print(f"Gate escrito: {GATE_PATH.relative_to(ROOT)}")
    for arm, res in arms.items():
        print(f"\n[{arm}] → {res['overall_verdict']}")
        if res["overall_verdict"] == "NOT_RUN":
            continue
        for fam, fr in res["per_family"].items():
            print(f"  {fam}: recall={fr['mutation_recall']} "
                  f"({fr['detected']}/{fr['mutation_rows_puntuables']}) → {fr['verdict']}")
        print(f"  coverage={res['coverage']['value']} → {res['coverage']['verdict']} | "
              f"clean FP={res['clean_noise']['fp_count']} → {res['clean_noise']['verdict']} | "
              f"cross FP={res['cross_binding']['fp_count']} → {res['cross_binding']['verdict']} | "
              f"attest appends={res['attestation_block']['appends']} → "
              f"{res['attestation_block']['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
