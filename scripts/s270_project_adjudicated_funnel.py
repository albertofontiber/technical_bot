#!/usr/bin/env python3
"""S270 (DEC-125): proyección DETERMINISTA de la adjudicación de Alberto sobre el funnel.

Proyecta las marcas registradas en ``evals/s270_gold_adjudication_v1.yaml`` (autoridad:
``evals/s269_goldreview_packet_v1_ADJUDICADO.md``) sobre el funnel vigente
143 OK / 12 synthesis-miss / 2 retrieval-miss / 157 (DEC-121 / PLAN S269).

Contrato (patrón S133/S153/S163 — nunca mutar artefactos congelados):
- $0, cero llamadas a modelo, cero red: aritmética pura sobre insumos SHA-pineados.
- Los SHA-256 se calculan sobre bytes LF-normalizados (``\\r\\n`` -> ``\\n``) porque el
  checkout Windows (autocrlf) reescribe EOLs; el pin FALLA (exit != 0) ante cualquier drift.
- Esto NO mueve OKs (``facts_moved_to_ok: 0``): es reconciliación de DENOMINADOR.
- ``official_atomic_kpi: null``: los 77 legacy carries siguen (S205); sin KPI atómico oficial.

Salida: ``evals/s270_adjudicated_funnel_v1.json``.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.visual_gold import write_json  # noqa: E402

ADJUDICATION = ROOT / "evals/s270_gold_adjudication_v1.yaml"
OUTPUT = ROOT / "evals/s270_adjudicated_funnel_v1.json"

# SHA-256 de bytes LF-normalizados; recalcular SOLO si el insumo cambia legítimamente
# (p.ej. re-registro adjudicado) y dejar traza en DECISIONS.
PINNED_SHA256_LF = {
    "evals/s269_goldreview_packet_v1_ADJUDICADO.md": (
        "b28255a64fe91ea76c727f1a6c8e942e1e0a7aed01a835b3a740ec40ad7f6dd9"
    ),
    "evals/s269_goldreview_packet_v1.md": (
        "cb623313ec8855431302b785162016b6ec2d001d0c0c29732e7a7ca6f1469815"
    ),
    "evals/s269_triage_12misses_v1.yaml": (
        "f2ab94cab976d3f18b592b0fc74fa71c0b427da9d6674a58a51312b5d971d217"
    ),
    "evals/s270_gold_adjudication_v1.yaml": (
        "51a64a10172557ffb8d06c9c89887d1ac6f9fb312f0b1387f6a36db6fb1ca436"
    ),
}

# Funnel vigente ANTES de la adjudicación (DEC-121; PLAN "Estado actual S269";
# foto diagnóstica sin movimiento oficial — bridge S133/S172/S188).
BASELINE = {"denominator": 157, "ok": 143, "synthesis_miss": 12, "retrieval_miss": 2}

VALID_EFFECTS = {
    "core_required",
    "supplementary_demoted",
    "disclosure_respec",
    "merged_into_warning_block",
}


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_pins() -> dict[str, str]:
    """Falla (ValueError) ante cualquier drift de SHA de los insumos."""
    seen: dict[str, str] = {}
    for rel, expected in PINNED_SHA256_LF.items():
        actual = _sha256_lf(ROOT / rel)
        if actual != expected:
            raise ValueError(
                f"SHA drift en insumo pineado {rel}: esperado {expected}, actual {actual}"
            )
        seen[rel] = actual
    return seen


def build_projection() -> dict[str, Any]:
    pins = verify_pins()
    adjudication = yaml.safe_load(ADJUDICATION.read_text(encoding="utf-8"))
    rows = adjudication["adjudications"]
    if len(rows) != 12:
        raise ValueError(f"esperaba 12 filas adjudicadas, hay {len(rows)}")

    effects: dict[str, str] = {}
    for row in rows:
        effect = str(row["efecto"])
        if effect not in VALID_EFFECTS:
            raise ValueError(f"efecto desconocido {effect!r} en {row['obligation_id']}")
        effects[str(row["obligation_id"])] = effect

    merge = adjudication["merge"]
    merged_ids = {str(v) for v in merge["absorbe"]}
    if merged_ids != {
        oid for oid, eff in effects.items() if eff == "merged_into_warning_block"
    }:
        raise ValueError("bloque merge inconsistente con los efectos por fila")
    carrier = str(merge["carrier"])
    if carrier not in merged_ids:
        raise ValueError("el carrier del merge debe ser una de las obligaciones absorbidas")

    n_core = sum(1 for eff in effects.values() if eff == "core_required")
    n_supp = sum(1 for eff in effects.values() if eff == "supplementary_demoted")
    n_disc = sum(1 for eff in effects.values() if eff == "disclosure_respec")
    n_merged = len(merged_ids)
    if (n_core, n_supp, n_disc, n_merged) != (7, 2, 1, 2):
        raise ValueError(
            "composición inesperada de la adjudicación: "
            f"core={n_core} supp={n_supp} disclosure={n_disc} merged={n_merged}"
        )

    # El par mergeado cuenta como UNA obligación CORE (el bloque-warning).
    core_after = n_core + 1
    synth_after = core_after + n_disc
    denominator = BASELINE["denominator"] - n_supp - (n_merged - 1)
    ok = BASELINE["ok"]
    retrieval = BASELINE["retrieval_miss"]
    if ok + synth_after + retrieval != denominator:
        raise ValueError("la aritmética del funnel adjudicado no cierra")
    if (denominator, synth_after, core_after) != (154, 9, 8):
        raise ValueError(
            f"proyección fuera de contrato: den={denominator} synth={synth_after} "
            f"core={core_after}"
        )

    target_pct = 0.98
    required_ok = -(-int(target_pct * 100 * denominator) // 100)  # ceil(0.98 * 154) = 151
    conversions_needed = required_ok - ok

    return {
        "schema": "s270_adjudicated_funnel_v1",
        "date": "2026-07-19",
        "dec": "DEC-125",
        "generated_by": "scripts/s270_project_adjudicated_funnel.py",
        "authority": (
            "evals/s269_goldreview_packet_v1_ADJUDICADO.md — marcas de Alberto "
            "(DEC-025: el gold es suyo)"
        ),
        "inputs_sha256_lf_normalized": pins,
        "baseline_funnel": {
            **BASELINE,
            "provenance": "DEC-121 / PLAN S269 (foto diagnóstica, bridge S133/S172/S188)",
        },
        "adjudication_effects": {
            "core_required_confirmed": sorted(
                oid for oid, eff in effects.items() if eff == "core_required"
            ),
            "demote_rejected_stays_core": ["obl_015f9b9aaa3a"],
            "supplementary_demoted": sorted(
                oid for oid, eff in effects.items() if eff == "supplementary_demoted"
            ),
            "disclosure_respec": sorted(
                oid for oid, eff in effects.items() if eff == "disclosure_respec"
            ),
            "warning_block_merge": {
                "absorbe": sorted(merged_ids),
                "carrier": carrier,
                "resultado": "1 obligación CORE de bloque-warning",
            },
        },
        "adjudicated_funnel": {
            "denominator": denominator,
            "ok": ok,
            "synthesis_miss": synth_after,
            "synthesis_miss_composition": {
                "core_required": core_after,
                "disclosure_respec": n_disc,
            },
            "retrieval_miss": retrieval,
            "ok_pct": round(100.0 * ok / denominator, 2),
        },
        "facts_moved_to_ok": 0,
        "facts_moved_note": (
            "Reconciliación de DENOMINADOR (demotes + merge), NO movimiento de OKs: "
            "ningún hecho cambia de estado por esta proyección."
        ),
        "official_atomic_kpi": None,
        "official_atomic_kpi_note": (
            "Los 77 legacy carries siguen (S205); sin KPI atómico oficial hasta cerrarlos."
        ),
        "target": {
            "declared": "98% de 154 = 151 → +8",
            "target_pct": target_pct,
            "required_ok": required_ok,
            "conversions_needed": conversions_needed,
        },
        "pixel_correction": (
            "t.Fi → t.A (hallazgo píxel s269 §Verificación de renders; zoom 500 dpi). "
            "Specs vivos limpios; congelados NO mutados — ver "
            "evals/s270_gold_adjudication_v1.yaml:live_anchor_audit"
        ),
    }


def main() -> int:
    report = build_projection()
    write_json(OUTPUT, report)
    funnel = report["adjudicated_funnel"]
    print(
        f"OK {funnel['ok']} / synth {funnel['synthesis_miss']} "
        f"(core {funnel['synthesis_miss_composition']['core_required']} + disclosure "
        f"{funnel['synthesis_miss_composition']['disclosure_respec']}) / retr "
        f"{funnel['retrieval_miss']} / den {funnel['denominator']} "
        f"({funnel['ok_pct']}%) -- objetivo 98% de 154 = "
        f"{report['target']['required_ok']} -> +{report['target']['conversions_needed']}"
    )
    print(f"escrito: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
