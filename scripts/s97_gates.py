"""s97 GATES — famtie K=3 runs por brazo (control off / tratamiento cosine), mismo día.

Pre-registro: evals/s97_diversify_tiebreak.md v2 [H3: norma DEC-090, K=1 inusable].
G1: flip PERSISTENTE (3/3) de hp012·'99+99' y famtie mediana ≤6.
G2: listado PAREADO de nuevas-miss por hecho; nueva-miss persistente (3/3) = diagnóstico.
Config demo: multivector on, identity on/add. Freeze estampado en la salida.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "on"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["ENUNCIADOS_MULTIVECTOR"] = "on"
os.environ["IDENTITY_RESOLVE"] = "on"
os.environ["IDENTITY_RESOLVE_POLICY"] = "add"

import yaml  # noqa: E402

from retrieval_miss_famtie import rederive  # noqa: E402

K = 3


def run_arm(arm: str, base: dict, golds: dict) -> list[dict]:
    os.environ["DIVERSIFY_TIEBREAK"] = "cosine" if arm == "on" else "off"
    import importlib

    import src.rag.retriever as R
    importlib.reload(R)          # el flag se lee por-llamada, pero reload = estado limpio
    runs = []
    for k in range(K):
        t0 = time.time()
        d = json.loads(json.dumps(base))     # copia profunda del esqueleto
        lat = []
        for res in d["reps"][0]["results"]:
            q0 = time.time()
            pool = R.retrieve_chunks(golds[res["qid"]]["question"], top_k=50)
            lat.append(time.time() - q0)
            res["pool_pin"] = [{"id": c.get("id"), "pm": c.get("product_model"),
                                "src": c.get("source_file")} for c in pool]
            res["top5_ids"] = []
        out = ROOT / "evals" / f"s97_miss_{arm}_r{k}.yaml"
        yaml.safe_dump(d, open(out, "w", encoding="utf-8"), allow_unicode=True,
                       sort_keys=False)
        fam = rederive(str(out))
        lat_s = sorted(lat)
        runs.append({"miss": fam["retrieval_miss_family"],
                     "misses": sorted((m["qid"], m["valor"]) for m in fam["misses"]),
                     "p50_s": round(lat_s[len(lat) // 2], 2),
                     "dur_min": round((time.time() - t0) / 60, 1)})
        print(f"[{arm} r{k}] famtie={runs[-1]['miss']} p50={runs[-1]['p50_s']}s")
    return runs


def main() -> int:
    base = yaml.safe_load(open(ROOT / "evals" / "s85_retrieval_miss_DEF.yaml",
                               encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}

    result = {"freeze": {"chunks_table": "chunks_v2", "multivector": "on",
                         "identity": "on/add", "hyde": "off", "k": K,
                         "at": time.strftime("%Y-%m-%dT%H:%M:%S")}}
    result["control"] = run_arm("off", base, golds)
    result["tratamiento"] = run_arm("on", base, golds)

    ctl_sets = [set(map(tuple, r["misses"])) for r in result["control"]]
    on_sets = [set(map(tuple, r["misses"])) for r in result["tratamiento"]]
    ctl_all = set.union(*ctl_sets)
    target = ("hp012", "99 + 99")
    flip_persistente = all(target not in s for s in on_sets) and any(
        target in s for s in ctl_sets)
    med = sorted(r["miss"] for r in result["tratamiento"])[K // 2]
    med_ctl = sorted(r["miss"] for r in result["control"])[K // 2]
    nuevas_persistentes = set.intersection(*on_sets) - ctl_all

    result["veredicto"] = {
        "famtie_mediana": {"control": med_ctl, "tratamiento": med},
        "flip_99+99_persistente_3de3": flip_persistente,
        "hp018_1A": {"control": sum(("hp018", "1 A") in s for s in ctl_sets),
                     "tratamiento": sum(("hp018", "1 A") in s for s in on_sets)},
        "nuevas_miss_persistentes": sorted(nuevas_persistentes),
        "nuevas_por_run": [sorted(s - ctl_all) for s in on_sets],
        "G1": bool(flip_persistente and med <= 6),
        "G2": len(nuevas_persistentes) == 0,
        "lat_p50_delta_s": round(
            sorted(r["p50_s"] for r in result["tratamiento"])[K // 2]
            - sorted(r["p50_s"] for r in result["control"])[K // 2], 2),
    }
    json.dump(result, open(ROOT / "evals" / "s97_gates.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=list)
    v = result["veredicto"]
    print(f"\nCONTROL mediana {med_ctl} → TRATAMIENTO mediana {med}")
    print(f"G1 (flip '99+99' 3/3 y mediana ≤6): {'✅' if v['G1'] else '❌'}")
    print(f"G2 (0 nuevas-miss persistentes): {'✅' if v['G2'] else '❌'} {v['nuevas_miss_persistentes']}")
    print(f"hp018 '1 A' (informativo): miss en {v['hp018_1A']['control']}/3 ctl → "
          f"{v['hp018_1A']['tratamiento']}/3 on")
    print(f"G3 latencia p50 delta: {v['lat_p50_delta_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
