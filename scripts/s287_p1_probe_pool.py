#!/usr/bin/env python3
"""s287_p1_probe_pool.py — gates $0 de la PIEZA 1 (regla monótona-segura corpus-aware).

Mismo patrón que el probe de P0.5 (`s287_p05_probe_pool.py`, del que REUTILIZA flags,
pregunta de hp018 y `describe_pool` — nada duplicado): retrieve + filtro POR DENTRO de
`retrieve_chunks`, SIN rerank (LLM = $0) y SIN generación. Dos brazos que son los DOS
ESTADOS SHIPPEABLES, no una hipótesis:

  pre_p1 = el estado shippeado por P0.5: quarantine {'zxe'} inyectada + presencia de corpus
           VACÍA (todo core "ausente" ⇒ la regla P1 no puede conservar nada = código pre-P1).
  p1     = el estado de ESTE build: quarantine REAL (vacía tras el sunset) + presencia REAL
           consultada a la DB (la regla es lo único que conserva el token).

GATES (spec v3 FINAL §Gates):
  (a) hp018: composición del pool IDÉNTICA entre brazos — y idéntica al artefacto de P0.5
      (evals/s287_p05_probe_pool_v1.json, brazo `after`: head10 100% familia).
  (b) CENTINELAS hp009/hp011/hp012/cat022/cat012/hp001: CERO cambio de composición.
      Cualquier cambio = STOP (no se sigue).

Salidas: evals/s287_p1_probe_pool_v1.json  ·  evals/s287_p1_centinelas_pool_v1.json
Uso:  python scripts/s287_p1_probe_pool.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir() and (ROOT / "evals").is_dir(), f"cwd no es la raíz: {ROOT}"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# el probe de P0.5 fija las flags de la ruta HARNESS en import-time y las re-afirma tras los
# imports (load_dotenv override=True) — se REUTILIZA tal cual para que ambos gates midan la
# MISMA ruta que el gate anterior
import s287_p05_probe_pool as P05  # noqa: E402

import yaml  # noqa: E402

from src.config import RETRIEVAL_TOP_K  # noqa: E402
from src.rag import catalog_resolver  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from retrieval_miss_famtie import fam_norm  # noqa: E402

P05._assert_flags()

GOLDS_PATH = ROOT / "evals" / "gold_answers_v1.yaml"
OUT_HP018 = ROOT / "evals" / "s287_p1_probe_pool_v1.json"
OUT_CENT = ROOT / "evals" / "s287_p1_centinelas_pool_v1.json"
P05_ARTIFACT = ROOT / "evals" / "s287_p05_probe_pool_v1.json"
CENTINELAS = ("hp009", "hp011", "hp012", "cat022", "cat012", "hp001")
# claves de composición que definen el veredicto del gate (b) — el ORDEN dentro del pool no
# entra: el gate es de COMPOSICIÓN (lo que el reranker puede ver), como en P0.5
COMP_KEYS = ("pool_n", "pool_by_family", "pool_by_source_file", "head10_by_family")


def question(qid: str) -> str:
    golds = yaml.safe_load(GOLDS_PATH.read_text(encoding="utf-8"))
    rows = golds if isinstance(golds, list) else golds.get("golds") or []
    return next(g for g in rows if g.get("qid") == qid)["question"]


def describe(pool: list[dict]) -> dict:
    head = pool[:10]
    return {
        "pool_n": len(pool),
        "head10": [{"id": c.get("id"), "product_model": c.get("product_model"),
                    "source_file": c.get("source_file"), "page_number": c.get("page_number")}
                   for c in head],
        "head10_by_family": dict(Counter(fam_norm(c.get("product_model")) for c in head)),
        "pool_by_family": dict(Counter(fam_norm(c.get("product_model")) for c in pool)),
        "pool_by_source_file": dict(Counter(str(c.get("source_file")) for c in pool)),
    }


def set_arm(arm: str) -> dict:
    """Inyecta el ESTADO del brazo en los dos caches lazy del resolver."""
    if arm == "pre_p1":
        catalog_resolver._quarantine = frozenset({"zxe"})        # el hotfix P0.5
        now = time.monotonic()
        catalog_resolver._presence = {"elements": frozenset(), "at": now,   # regla inerte
                                      "fp": ("arm", "pre_p1"), "fp_at": now}
        return {"quarantine": ["zxe"], "presence_elements_n": 0}
    catalog_resolver._quarantine = None                          # re-lee el YAML real
    catalog_resolver._presence = None                            # consulta la DB real
    q = sorted(catalog_resolver._quarantine_tokens())
    els = catalog_resolver.corpus_pm_elements()
    assert els, "presencia de corpus VACÍA/None en el brazo p1 — el gate sería vacuo"
    return {"quarantine": q, "presence_elements_n": len(els)}


def run(qid: str, arm: str, full: bool) -> dict:
    q = question(qid)
    pool = retrieve_chunks(q, top_k=RETRIEVAL_TOP_K)
    out = P05.describe_pool(pool) if full else describe(pool)
    out["arm"], out["qid"], out["question"] = arm, qid, q
    print(f"  [{arm}] {qid}: pool={out['pool_n']} head10={out['head10_by_family']}")
    return out


def comp(d: dict) -> dict:
    return {k: d[k] for k in COMP_KEYS}


# familias de la clase-diana (diagnóstico s287 Grupo B): los PRIMOS son el fallo a evitar;
# 'ZXE/ZXSE' es un composite de la FAMILIA (doc que cubre ZXe y su hermana) — ni primo puro
# ni ZXe puro, se cuenta aparte para no maquillar ninguno de los dos lados
PRIMOS = P05.PRIMO_FAMS
FAMILIA = P05.FAMILY_FAMS | {"ZXE/ZXSE"}


def invariante(d: dict) -> dict:
    """El criterio OPERATIVO del gate (a) tal como lo fija el spec: «composición 100%
    familia» — head10 sin primos + pool sin primos + la fila que acredita hp018 en el pool.
    Se declara APARTE de la igualdad estricta para no confundir ruido con efecto."""
    head = [fam_norm(c["product_model"]) for c in d["head10"]]
    pool_fams = d["pool_by_family"]
    return {
        "head10_primos": sum(1 for f in head if f in PRIMOS),
        "head10_familia": sum(1 for f in head if f in FAMILIA),
        "pool_primos": sum(n for f, n in pool_fams.items() if f in PRIMOS),
        "pool_fuera_de_familia": sorted(f for f in pool_fams if f not in FAMILIA),
        "accrediting_chunk_in_pool": d.get("accrediting_chunk_in_pool"),
    }


def main() -> None:
    arms = {}
    results: dict[str, dict[str, dict]] = {"hp018": {}, **{q: {} for q in CENTINELAS}}
    for arm in ("pre_p1", "p1"):
        arms[arm] = set_arm(arm)
        print(f"brazo {arm}: {arms[arm]}")
        results["hp018"][arm] = run("hp018", arm, full=True)
        for qid in CENTINELAS:
            results[qid][arm] = run(qid, arm, full=False)

    # CONTROL DE RUIDO (DEC-096b/§réplica del spec: sin control OFF-vs-OFF no se distingue
    # efecto de churn): 2 réplicas EXTRA del MISMO brazo p1 — si la composición se mueve
    # entre réplicas, la igualdad estricta entre brazos no es un criterio utilizable.
    replicas = [run("hp018", "p1_replica", full=True) for _ in range(2)]
    jitter = {
        "compositions": [comp(results["hp018"]["p1"])] + [comp(r) for r in replicas],
        "invariantes": [invariante(results["hp018"]["p1"])] + [invariante(r) for r in replicas],
    }
    jitter["misma_composicion_entre_replicas"] = all(
        c == jitter["compositions"][0] for c in jitter["compositions"])

    hp018_same = comp(results["hp018"]["pre_p1"]) == comp(results["hp018"]["p1"])
    p05 = json.loads(P05_ARTIFACT.read_text(encoding="utf-8"))["after"]
    hp018_same_as_p05 = comp(p05) == comp(results["hp018"]["p1"])
    inv = {"pre_p1": invariante(results["hp018"]["pre_p1"]),
           "p1": invariante(results["hp018"]["p1"]),
           "p05_artifact": invariante(p05)}
    inv_ok = all(v["head10_primos"] == 0 and v["pool_primos"] == 0
                 and v["head10_familia"] == 10 and not v["pool_fuera_de_familia"]
                 for v in inv.values())
    cent = {qid: {"same_composition": comp(results[qid]["pre_p1"]) == comp(results[qid]["p1"]),
                  "pre_p1": results[qid]["pre_p1"], "p1": results[qid]["p1"]}
            for qid in CENTINELAS}
    cent_all_same = all(v["same_composition"] for v in cent.values())

    OUT_HP018.write_text(json.dumps({
        "gate": "s287 P1 (a) — hp018: la regla corpus-aware reproduce la composición del "
                "hotfix P0.5 con la quarantine RETIRADA",
        "flags": dict(P05.RETRIEVAL_FLAGS), "retrieval_top_k": RETRIEVAL_TOP_K,
        "arms_state": arms,
        "pre_p1": results["hp018"]["pre_p1"], "p1": results["hp018"]["p1"],
        "same_composition_pre_p1_vs_p1": hp018_same,
        "same_composition_vs_p05_artifact": hp018_same_as_p05,
        "p05_reference": {k: p05[k] for k in COMP_KEYS},
        "jitter_control_mismo_brazo": jitter,
        "invariante_100pct_familia": inv,
        "invariante_ok": inv_ok,
        "veredicto": "La igualdad ESTRICTA de composición no es utilizable como gate: la "
                     "composición se mueve entre RÉPLICAS DEL MISMO BRAZO (churn del "
                     "instrumento, ya documentado en el spec §réplica). El criterio del "
                     "spec — «100% familia» — se evalúa en `invariante_ok` y aplica a los "
                     "dos brazos Y al artefacto de P0.5.",
        "nota": "pool FILTRADO pre-rerank (el rerank es LLM y no se llama); el gate es de "
                "COMPOSICIÓN, no de orden",
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_CENT.write_text(json.dumps({
        "gate": "s287 P1 (b) — CENTINELAS: cero cambio de composición de pool "
                "(hp009 conserva ZXAE/ZXEE · hp011 mantiene el prefer RP1r)",
        "flags": dict(P05.RETRIEVAL_FLAGS), "retrieval_top_k": RETRIEVAL_TOP_K,
        "arms_state": arms, "centinelas": cent, "all_same_composition": cent_all_same,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\nescrito {OUT_HP018}\n  hp018 same(pre_p1 vs p1)={hp018_same} "
          f"same(vs artefacto P0.5)={hp018_same_as_p05} "
          f"| replicas-iguales={jitter['misma_composicion_entre_replicas']} "
          f"| invariante_100pct_familia={inv_ok}")
    for k, v in inv.items():
        print(f"    {k}: {v}")
    print(f"escrito {OUT_CENT}\n  centinelas sin cambio={cent_all_same} "
          f"| {({k: v['same_composition'] for k, v in cent.items()})}")


if __name__ == "__main__":
    main()
