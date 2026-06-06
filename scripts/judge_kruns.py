#!/usr/bin/env python3
"""K-runs del desacuerdo de jueces (DEC-021 §D, medir-primero paso 3, pedido por el dúo).

Round 1 (n=1) dio 36% desacuerdo factual pero 2/8 se evaporaron en round 2 = ruido. El dúo
exigió K-runs antes de concluir nada: ¿el desacuerdo (p.ej. hp006 Claude-flag/GPT-miss, hp003
GPT-flag/Claude-miss) es ESTABLE (complementariedad real → pro-ensemble) o sampling?

Corre cada (gold, eje, modelo) K veces, mide FRECUENCIA de flag, y clasifica cada gold/eje:
  - acuerdo-no / acuerdo-si : ambos coinciden establemente.
  - DESACUERDO-ESTABLE      : uno flag>=0.8, el otro <=0.2 (catch complementario real).
  - ruidoso                 : alguno en zona media (sampling, no concluyente).

NO toca el scorer. Reusa los prompts y helpers de judge_disagreement.py.
Uso:  python scripts/judge_kruns.py [--k 5] [--qids a,b]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gold_store  # noqa: E402
from atomic_scorer import _FACTUAL_SYS, _FACTUAL_USER, _UNDUE_SYS, _UNDUE_USER  # noqa: E402
import judge_disagreement as J  # noqa: E402  (clientes + _gpt/_claude/_parse_list/_facts_txt)

OUT = ROOT / "evals" / "_s47_judge_kruns.json"
_OAI = None   # clientes (se construyen en main, usados por _run_one en hilos)
_ANTH = None


def _run_one(task):
    """task = (qid, axis, model, sys_p, user_p). Devuelve (qid, axis, model, flag|None)."""
    qid, axis, model, sys_p, user_p = task
    key = "contradicciones" if axis == "fact" else "fabricaciones"
    try:
        txt = J._gpt(_OAI, sys_p, user_p) if model == "gpt" else J._claude(_ANTH, sys_p, user_p)
        lst = J._parse_list(txt, key)
        flag = None if lst is None else (len(lst) > 0)
    except Exception:
        flag = None
    return (qid, axis, model, flag)


def _classify(gf, cf):
    """gf,cf = frecuencia de flag (0..1) o None. Etiqueta el par."""
    if gf is None or cf is None:
        return "incompleto"
    hi, lo = 0.8, 0.2
    if (gf >= hi and cf <= lo) or (cf >= hi and gf <= lo):
        return "DESACUERDO-ESTABLE"
    if gf <= lo and cf <= lo:
        return "acuerdo-no"
    if gf >= hi and cf >= hi:
        return "acuerdo-si"
    return "ruidoso"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--qids", default="")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    global _OAI, _ANTH
    import os
    from openai import OpenAI
    from anthropic import Anthropic
    _OAI = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    _ANTH = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with open(J.DEFAULT_ANSWERS, encoding="utf-8") as fh:
        answers = {r["qid"]: r.get("bot_answer", "")
                   for r in (yaml.safe_load(fh) or []) if r.get("qid")}
    golds = [g for g in gold_store.verified() if g.get("atomic_facts")]
    if args.qids:
        want = {q.strip() for q in args.qids.split(",")}
        golds = [g for g in golds if g.get("qid") in want]

    tasks = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            continue
        ans = (answers[qid] or "")[:4000]
        facts = g.get("atomic_facts") or []
        present = [f for f in facts if f.get("estado") != "ausente-probado"]
        absent = [f for f in facts if f.get("estado") == "ausente-probado"]
        fu = _FACTUAL_USER.format(facts=J._facts_txt(present, True), answer=ans)
        for _ in range(args.k):
            tasks.append((qid, "fact", "gpt", _FACTUAL_SYS, fu))
            tasks.append((qid, "fact", "claude", _FACTUAL_SYS, fu))
        if absent:
            uu = _UNDUE_USER.format(facts=J._facts_txt(absent, False), answer=ans)
            for _ in range(args.k):
                tasks.append((qid, "fab", "gpt", _UNDUE_SYS, uu))
                tasks.append((qid, "fab", "claude", _UNDUE_SYS, uu))

    print(f"K={args.k} | golds={len(golds)} | tasks={len(tasks)} | jueces={J.GPT_MODEL} vs {J.CLAUDE_MODEL}\n")
    raw = defaultdict(list)  # (qid,axis,model) -> [flags sin None]
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_run_one, t) for t in tasks]
        for fut in as_completed(futs):
            qid, axis, model, flag = fut.result()
            if flag is not None:
                raw[(qid, axis, model)].append(flag)
            done += 1
            if done % 40 == 0:
                print(f"  ...{done}/{len(tasks)}")

    def freq(qid, axis, model):
        v = raw.get((qid, axis, model), [])
        return (sum(v) / len(v)) if v else None

    rows = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            continue
        has_absent = any(f.get("estado") == "ausente-probado" for f in (g.get("atomic_facts") or []))
        r = {"qid": qid,
             "fact_gpt": freq(qid, "fact", "gpt"), "fact_claude": freq(qid, "fact", "claude")}
        r["fact_class"] = _classify(r["fact_gpt"], r["fact_claude"])
        if has_absent:
            r["fab_gpt"] = freq(qid, "fab", "gpt")
            r["fab_claude"] = freq(qid, "fab", "claude")
            r["fab_class"] = _classify(r["fab_gpt"], r["fab_claude"])
        rows.append(r)

    def _fmt(x):
        return "-" if x is None else f"{x:.1f}"

    print("\n" + "=" * 72)
    print(f"{'qid':<8} {'fact_gpt':>8} {'fact_cla':>8}  {'clase factual':<20}")
    for r in rows:
        line = f"{r['qid']:<8} {_fmt(r['fact_gpt']):>8} {_fmt(r['fact_claude']):>8}  {r['fact_class']:<20}"
        if "fab_class" in r:
            line += f" | no-fab g={_fmt(r['fab_gpt'])} c={_fmt(r['fab_claude'])} {r['fab_class']}"
        print(line)

    from collections import Counter
    cc = Counter(r["fact_class"] for r in rows)
    print("\nRESUMEN factual:", dict(cc))
    stable = [r["qid"] for r in rows if r["fact_class"] == "DESACUERDO-ESTABLE"]
    noisy = [r["qid"] for r in rows if r["fact_class"] == "ruidoso"]
    print(f"DESACUERDO-ESTABLE (complementariedad real): {stable}")
    print(f"ruidoso (era sampling): {noisy}")

    OUT.write_text(json.dumps({"k": args.k, "rows": rows, "summary": dict(cc)},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
