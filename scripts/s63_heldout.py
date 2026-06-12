#!/usr/bin/env python3
"""s63_heldout.py — corrida ÚNICA de confirmación held-out del ciclo A
(cláusula R / DEC-037c, criterio PRE-REGISTRADO antes de conocer delta alguno).

Fases:
  pair     pools de los 12 ho en AMBOS brazos (mismo embedding por par, regla de
           convergencia anti-dado-de-red del spec s63) → s63_pairing_heldout.yaml.
           Los IDÉNTICOS: Δ:=0 estructural (no se generan ni juzgan). Imprime
           SOLO metadatos (n, pm) — nunca contenidos (embargo).
  verdict  criterio (c) DEC-037c sobre el par held-out:
           CONFIRMA     = Δ_net_ho ≥ 1 (mismo signo que dev, que fue +2) Y
                          0 fabricaciones K-estables nuevas en tratamiento.
           NO-CONFIRMA  = Δ_net_ho ≤ -1 O ≥1 fabricación nueva.
           DÉBIL (gris) = Δ_net_ho = 0 → decisión Alberto declarada.
           Fabricación K-estable nueva := en un gold cambiado, mayoría de los K
           juicios del TRATAMIENTO diagnostican invención/fabricación sin que el
           CONTROL la tenga (el par es el contrafactual). Los diagnósticos se
           vuelcan al yaml para lectura humana declarada (n esperado ≤2).

Entre pair y verdict, la generación/juicio de los CAMBIADOS corre con
bvg_kmajority (INCLUDE_HELDOUT=1, BVG_RUN_ID=s63ho_ctrl / s63ho_treat).
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", str(ROOT / "evals" / "s63_embed_cache.json"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
import src.rag.series_registry as sr  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402

EVALS = ROOT / "evals"
F_PAIRING = EVALS / "s63_pairing_heldout.yaml"
F_VERDICT = EVALS / "s63_heldout_verdict.yaml"
DEV_DELTA_NET = 2          # signo de referencia del criterio (c): dev fue +2
_FABRIC_RE = re.compile(r"invent|fabric|inexact|no aparece en|no está en el contexto",
                        re.IGNORECASE)


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def set_arm(treatment: bool) -> None:
    os.environ["SERIES_REGISTRY_ENABLED"] = "true" if treatment else "false"
    sr.reset_registry_cache()


def phase_pair() -> int:
    print("*** CORRIDA HELD-OUT (cláusula R) — fase pair (pools, sin LLM) ***")
    golds = gold_store.heldout()
    assert golds, "held-out vacío"
    pairing, detail = {}, {}
    for g in sorted(golds, key=lambda x: x["qid"]):
        qid, q = g["qid"], g["question"]
        set_arm(False)
        pc = retrieve_chunks(q, top_k=50)
        set_arm(True)
        pt = retrieve_chunks(q, top_k=50)
        same = [c.get("id") for c in pc] == [c.get("id") for c in pt]
        if not same:
            # convergencia anti-dado-de-red (enmienda 12-jun del spec): re-par
            set_arm(False)
            pc = retrieve_chunks(q, top_k=50)
            set_arm(True)
            pt = retrieve_chunks(q, top_k=50)
            same = [c.get("id") for c in pc] == [c.get("id") for c in pt]
        pairing[qid] = "identico" if same else "cambiado"
        from collections import Counter
        detail[qid] = {
            "n_ctrl_treat": [len(pc), len(pt)],
            "pm_ctrl": dict(Counter((c.get("product_model") or "?") for c in pc)),
            "pm_treat": dict(Counter((c.get("product_model") or "?") for c in pt)),
        }
        print(f"  {qid}: {pairing[qid]} (n {len(pc)}→{len(pt)})")
    cambiados = sorted(q for q, v in pairing.items() if v == "cambiado")
    F_PAIRING.write_text(yaml.safe_dump(
        {"at": _now(), "clausula": "R / DEC-037c — corrida única",
         "criterio_pairing": "spec s63 (ids exactos + convergencia r2)",
         "identicos": sorted(q for q, v in pairing.items() if v == "identico"),
         "cambiados": cambiados, "detalle": detail},
        allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"pairing held-out: {len(pairing) - len(cambiados)} idénticos / "
          f"{len(cambiados)} cambiados → {cambiados}")
    print(f"→ {F_PAIRING.name}")
    return 0


def _fabricaciones(j_runs: dict) -> list[str]:
    """Diagnósticos con señal de invención en los K juicios de un gold."""
    out = []
    for k in sorted(j_runs):
        d = (j_runs[k].get("diagnostico") or "") + " " + str(j_runs[k].get("veredicto"))
        if j_runs[k].get("veredicto") == "FALLO" and _FABRIC_RE.search(d):
            out.append(f"k{k}: {j_runs[k].get('diagnostico')}")
    return out


def phase_verdict() -> int:
    import bvg_kmajority as BVG   # aggregate/ORDER — fuente única
    pairing = yaml.safe_load(F_PAIRING.read_text(encoding="utf-8"))
    cambiados = pairing["cambiados"]
    j_ctrl = json.loads((EVALS / "s63ho_ctrl_judgments.json").read_text(encoding="utf-8"))
    j_treat = json.loads((EVALS / "s63ho_treat_judgments.json").read_text(encoding="utf-8"))
    m_treat = json.loads((EVALS / "s63ho_treat_run_manifest.json").read_text(encoding="utf-8"))
    sr_t = m_treat["freeze"]["series_registry"]
    assert sr_t["fingerprint"] not in ("disabled", "empty"), sr_t

    filas, fabricaciones_nuevas = [], {}
    for qid in cambiados:
        vc = [j_ctrl[qid][k].get("veredicto", "?") for k in sorted(j_ctrl[qid])]
        vt = [j_treat[qid][k].get("veredicto", "?") for k in sorted(j_treat[qid])]
        ac, at = BVG.aggregate(vc), BVG.aggregate(vt)
        oc, ot = BVG.ORDER.get(ac["veredicto"], -1), BVG.ORDER.get(at["veredicto"], -1)
        assert oc >= 0 and ot >= 0, f"{qid}: no clasificable"
        delta = "MEJOR" if ot > oc else ("PEOR" if ot < oc else "IGUAL")
        fab_t = _fabricaciones(j_treat[qid])
        fab_c = _fabricaciones(j_ctrl[qid])
        # K-estable nueva: mayoría en tratamiento sin equivalente en control
        if len(fab_t) >= 3 and len(fab_c) < 3:
            fabricaciones_nuevas[qid] = fab_t
        filas.append({"qid": qid,
                      "control": {"modal": ac["veredicto"], "votos": ac["votes"]},
                      "tratamiento": {"modal": at["veredicto"], "votos": at["votes"]},
                      "delta": delta,
                      "diagnosticos_tratamiento": [j_treat[qid][k].get("diagnostico")
                                                   for k in sorted(j_treat[qid])],
                      "diagnosticos_control": [j_ctrl[qid][k].get("diagnostico")
                                               for k in sorted(j_ctrl[qid])]})

    n_mejor = sum(1 for f in filas if f["delta"] == "MEJOR")
    n_peor = sum(1 for f in filas if f["delta"] == "PEOR")
    delta_net = n_mejor - n_peor

    if fabricaciones_nuevas or delta_net <= -1:
        veredicto = "NO-CONFIRMA"
    elif delta_net >= 1:
        veredicto = "CONFIRMA"
    else:
        veredicto = "DÉBIL (gris Δ=0 → decisión Alberto declarada)"

    out = {"meta": {"at": _now(), "clausula": "R / DEC-037c (criterio pre-registrado)",
                    "dev_delta_net_referencia": DEV_DELTA_NET,
                    "n_identicos": len(pairing["identicos"]),
                    "cambiados": cambiados,
                    "series_registry_tratamiento": sr_t},
           "tabla": filas,
           "delta_net_heldout": delta_net,
           "fabricaciones_K_estables_nuevas": fabricaciones_nuevas,
           "veredicto": veredicto}
    F_VERDICT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False,
                                        width=110), encoding="utf-8")
    print("=" * 72)
    for f in filas:
        print(f"  {f['qid']}: control={f['control']['modal']} {f['control']['votos']}"
              f" → tratamiento={f['tratamiento']['modal']} {f['tratamiento']['votos']}"
              f"  [{f['delta']}]")
    print(f"Δ_net held-out = {delta_net} | fabricaciones nuevas: "
          f"{list(fabricaciones_nuevas) or 'ninguna'}")
    print(f"VEREDICTO HELD-OUT: {veredicto}")
    print(f"→ {F_VERDICT.name}")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["pair", "verdict"])
    args = ap.parse_args()
    return phase_pair() if args.phase == "pair" else phase_verdict()


if __name__ == "__main__":
    sys.exit(main())
