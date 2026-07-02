#!/usr/bin/env python3
"""s93_gate0_testbed.py — construye el TESTBED común del bake-off fine-grained (plan v3).

Extrae de `evals/s92_retrieval_miss_ON_add.yaml` (pin ON+add, famtie 12/132):
- las 12 miss-facts con sus chunk-ids soporte JUZGADOS (votes>=4) SAME-FAMILY
  (los que voltearían el miss — mismo criterio que la famtie),
- la pregunta del gold (query de producción; lo ÚNICO que ven los instrumentos),
- tokens-modelo detectados (extract_product_models de producción) + la variante
  de pregunta SIN modelo (celda de la matriz del gate-0),
- guard anti-circularidad: ¿la pregunta contiene el string del hecho? → fila
  excluida y declarada (el hecho no puede venir "regalado" en la query),
- 6 golds CONTROL sin miss (regla determinista: servable, con hechos medibles,
  0 bucket RETRIEVAL, primeros 6 por qid) con su pool_pin (solape/desplazamiento).

Salida: evals/s93_gate0_testbed.json (insumo de los tracks A/B/C). Read-only.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
import yaml

from retrieval_miss_famtie import _pm_by_ids, fam_norm, gold_family, rederive
from src.rag.retriever import extract_product_models

PIN = "evals/s92_retrieval_miss_ON_add.yaml"
OUT = "evals/s93_gate0_testbed.json"
THRESH_FIRM = 4
N_CONTROL = 6


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def strip_models(question: str, models: list[str]) -> str:
    """Celda 'sin token-modelo': quita cada token detectado (con variantes de
    guion/espacio) de la pregunta. Determinista, sin re-redactar."""
    q = question
    for m in sorted(models, key=len, reverse=True):
        # CAD-150 → también 'CAD 150' / 'CAD150'
        core = re.escape(m).replace(r"\-", r"[-\s]?")
        q = re.sub(core, " ", q, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", q).strip(" ¿?,;:/")


def main() -> int:
    d = yaml.safe_load(open(PIN, encoding="utf-8"))
    results = {r["qid"]: r for r in d["reps"][0]["results"]}
    golds = {g["qid"]: g for g in yaml.safe_load(
        open("evals/gold_answers_v1.yaml", encoding="utf-8"))}
    fam = rederive(PIN)          # la famtie canónica decide QUÉ es miss (no re-derivar a mano)

    rows, excluded = [], []
    for m in fam["misses"]:
        qid, valor = m["qid"], m["valor"]
        res = results[qid]
        g = golds[qid]
        question = g["question"]
        gfam = set(m["gold_family"])
        fact = next(f for f in res["facts"] if f["valor"] == valor)
        sup_all = [i for i, v in (fact.get("votes") or {}).items() if v >= THRESH_FIRM]
        pin = {c["id"]: c for c in res.get("pool_pin", [])}
        man = {c["id"]: c for c in res.get("manual_pin", [])}
        pms = _pm_by_ids([i for i in sup_all if i not in pin and i not in man])

        def _meta(cid):
            c = pin.get(cid) or man.get(cid) or {}
            return {"id": cid, "pm": c.get("pm") or pms.get(cid), "src": c.get("src")}

        metas = [_meta(i) for i in sup_all]
        need_pm = [x["id"] for x in metas if not x["pm"]]
        if need_pm:
            for cid, pmv in _pm_by_ids(need_pm).items():
                for x in metas:
                    if x["id"] == cid:
                        x["pm"] = pmv
        sup_fam = [x for x in metas if fam_norm(x["pm"] or "") in gfam]

        # guard anti-circularidad: el string del hecho NO puede venir en la pregunta
        if _norm(valor) and _norm(valor) in _norm(question):
            excluded.append({"qid": qid, "valor": valor, "motivo": "hecho presente en la pregunta"})
            continue
        models = extract_product_models(question)
        rows.append({
            "qid": qid, "valor": valor, "question": question,
            "models_detected": models,
            "question_sin_modelo": strip_models(question, models),
            "gold_family": sorted(gfam),
            "sup_family_ids": sup_fam,          # los que voltearían el miss
            "sup_all_n": len(sup_all),
            "pool_n": res.get("pool_n"),
        })

    # controles: servable, con hechos, 0 RETRIEVAL — primeros 6 por qid (regla declarada)
    controls = []
    for qid in sorted(results):
        pg = fam["per_gold"].get(qid, {})
        if qid in fam["unresolved"] or pg.get("RETRIEVAL", 0) > 0 or not sum(pg.values()):
            continue
        res = results[qid]
        if not res.get("servable", True):
            continue
        g = golds[qid]
        models = extract_product_models(g["question"])
        controls.append({
            "qid": qid, "question": g["question"], "models_detected": models,
            "question_sin_modelo": strip_models(g["question"], models),
            "pool_ids": [c["id"] for c in res.get("pool_pin", [])],
            "pool_n": res.get("pool_n"),
        })
        if len(controls) >= N_CONTROL:
            break

    out = {"pin": PIN, "n_miss_facts": len(rows), "excluded": excluded,
           "rows": rows, "controls": controls}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"testbed → {OUT}: {len(rows)} miss-facts ({len(excluded)} excluidas por guard), "
          f"{len(controls)} controles")
    for r in rows:
        print(f"  {r['qid']:8} {r['valor'][:24]!r:26} sup_fam={len(r['sup_family_ids'])} "
              f"models={r['models_detected']} pool_n={r['pool_n']}")
    for e in excluded:
        print(f"  EXCLUIDA {e['qid']} {e['valor']!r}: {e['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
