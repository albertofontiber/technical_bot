#!/usr/bin/env python3
"""s63_ab_verdict.py — veredicto E2 del A/B dual-arm con pairing (ciclo A).

Aplica el criterio del par PRE-REGISTRADO en evals/s63_gate_spec.yaml
(E2 con afinado 1, aprobado por Alberto ANTES de correr juez alguno):

  - Por gold CAMBIADO: veredicto modal K=5 por brazo (aggregate() del runner
    bvg — fuente única, no se duplica) → MEJOR/PEOR/IGUAL por ORDER.
  - Δ_net = #mejor − #peor sobre los cambiados. Los idénticos: Δ:=0
    ESTRUCTURAL (comparten artefactos; no se generan ni juzgan).
  - SHIP automático sii [Δ_net ≥ 1, o Δ_net = 0 con CERO cambios de veredicto]
    ∧ ningún PASS-control unánime PEOR ∧ gate G1-G8 verde (ya verificado: GO).
  - GRIS si Δ_net = 0 con movimiento interno → decisión Alberto documentada.
  - ROLLBACK si Δ_net < 0 o PASS-control dañado.

Insumos: evals/s63ctrl_judgments.json · evals/s63treat_judgments.json ·
evals/s63_pairing.yaml · manifests de ambos brazos (verificación de la
variable de tratamiento, G8 del A/B). Salida: evals/s63_ab_verdict.yaml.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bvg_kmajority as BVG  # noqa: E402  (aggregate + ORDER — fuente única)

EVALS = ROOT / "evals"
UNANIMES = {"cat010", "cat014", "cat015", "cat022", "hp015", "hp019"}


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    pairing = yaml.safe_load((EVALS / "s63_pairing.yaml").read_text(encoding="utf-8"))
    cambiados = pairing["cambiados_golds_para_AB"]
    j_ctrl = _load(EVALS / "s63ctrl_judgments.json")
    j_treat = _load(EVALS / "s63treat_judgments.json")
    m_ctrl = _load(EVALS / "s63ctrl_run_manifest.json")
    m_treat = _load(EVALS / "s63treat_run_manifest.json")

    # G8 del A/B: la variable de tratamiento estampada y coherente por brazo.
    sr_c = m_ctrl["freeze"]["series_registry"]
    sr_t = m_treat["freeze"]["series_registry"]
    assert sr_c["fingerprint"] == "disabled", f"brazo control con registry: {sr_c}"
    assert sr_t["fingerprint"] not in ("disabled", "empty"), f"tratamiento sin registry: {sr_t}"
    assert sr_t["stats"] == {"n_series": 2, "n_members": 6, "n_shared": 2}, sr_t["stats"]
    # Generador/juez idénticos entre brazos (además del R4 vs s58 que bvg ya asertó).
    for sec, key in (("generate", "generator"), ("judge", "judge")):
        a, b = m_ctrl[sec][key], m_treat[sec][key]
        diffs = {k: (a.get(k), b.get(k)) for k in a
                 if k != "models_real" and a.get(k) != b.get(k)}
        assert not diffs, f"instrumento '{sec}' difiere entre brazos: {diffs}"

    # PASS-control unánimes: en idénticos por construcción → no pueden empeorar.
    en_cambiados = UNANIMES & set(cambiados)
    assert not en_cambiados, f"PASS-control unánime entre los cambiados: {en_cambiados}"

    filas = []
    for qid in cambiados:
        vc = [j_ctrl[qid][k].get("veredicto", "?") for k in sorted(j_ctrl[qid])]
        vt = [j_treat[qid][k].get("veredicto", "?") for k in sorted(j_treat[qid])]
        ac, at = BVG.aggregate(vc), BVG.aggregate(vt)
        oc, ot = BVG.ORDER.get(ac["veredicto"], -1), BVG.ORDER.get(at["veredicto"], -1)
        assert oc >= 0 and ot >= 0, f"{qid}: veredicto no clasificable (judge errors)"
        delta = "MEJOR" if ot > oc else ("PEOR" if ot < oc else "IGUAL")
        filas.append({
            "qid": qid,
            "control": {"modal": ac["veredicto"], "votos": ac["votes"],
                        "unanime": ac["unanime"]},
            "tratamiento": {"modal": at["veredicto"], "votos": at["votes"],
                            "unanime": at["unanime"]},
            "delta": delta,
        })

    n_mejor = sum(1 for f in filas if f["delta"] == "MEJOR")
    n_peor = sum(1 for f in filas if f["delta"] == "PEOR")
    delta_net = n_mejor - n_peor
    movimiento = any(f["delta"] != "IGUAL" for f in filas)

    if delta_net >= 1 or (delta_net == 0 and not movimiento):
        veredicto = "SHIP"
    elif delta_net == 0:
        veredicto = "GRIS (decisión Alberto documentada)"
    else:
        veredicto = "ROLLBACK"

    out = {
        "meta": {"at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "criterio": "E2 + afinado 1 (evals/s63_gate_spec.yaml, pre-registrado)",
                 "k": 5,
                 "pairing": {"identicos": len(pairing["identicos"]),
                             "cambiados_golds": cambiados},
                 "series_registry_tratamiento": sr_t},
        "pass_control": "los 6 unánimes en IDÉNTICOS (Δ:=0 estructural) — intactos",
        "tabla": filas,
        "delta_net": delta_net,
        "n_mejor": n_mejor, "n_peor": n_peor,
        "veredicto": veredicto,
    }
    (EVALS / "s63_ab_verdict.yaml").write_text(
        yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8")

    print("=" * 72)
    for f in filas:
        print(f"  {f['qid']}: control={f['control']['modal']} {f['control']['votos']}"
              f" → tratamiento={f['tratamiento']['modal']} {f['tratamiento']['votos']}"
              f"  [{f['delta']}]")
    print(f"Δ_net = {delta_net}  (mejor={n_mejor}, peor={n_peor}; "
          f"{len(pairing['identicos'])} idénticos Δ:=0)")
    print(f"VEREDICTO: {veredicto}")
    print("→ evals/s63_ab_verdict.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
