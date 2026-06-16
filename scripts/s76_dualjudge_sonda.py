#!/usr/bin/env python3
"""s76 — sonda MEASURE-FIRST del dual-judge HOLISTICO (DEC-051d / s47 §D).

CORRIGE la premisa del cluster MEASUREMENT (verificado s76): judge_disagreement.py/judge_kruns.py
midieron el desacuerdo cross-model en los EJES DE SEGURIDAD del scorer atomico (contradiccion/
fabricacion per-hecho), NO el ruler HOLISTICO de veredicto (PASS/PARCIAL/FALLO) que produce el +-2
(DEC-051d, F 5->7). -> el dual-judge HOLISTICO nunca se midio-primero.

Esta sonda mide-primero (eval-driven, NO construye nada): corre un 2o modelo (Claude-Opus) como
juez HOLISTICO sobre las MISMAS respuestas congeladas s67base que el juez unico GPT-5.5 ya juzgo
(s67base_judgments.json), con el MISMO prompt (test_bot_vs_gold._JUDGE_*), y compara veredictos.

FORK (DEC-021 §D):
  - desacuerdo BAJO + disagreements = Claude-mas-estricto-FP-de-contrato -> el 2o modelo no agrega
    cobertura -> NO construir el dual-judge (diferir al eval organico ~sept).
  - desacuerdo ALTO + sistematico (Claude caza una CLASE que GPT pierde) -> construir CON dato.

Embargo: s67base_generations solo tiene los 39 dev (held-out fuera). Flags default.
Uso: python scripts/s76_dualjudge_sonda.py [--k 3]
Salida: evals/s76_dualjudge_sonda.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
load_dotenv(ROOT / ".env", override=True)

import gold_store  # noqa: E402
# Prompt HOLISTICO REAL del ruler de veredicto (no se re-implementa).
from scripts.test_bot_vs_gold import _JUDGE_SYS, _JUDGE_USER  # noqa: E402

GEN = ROOT / "evals" / "s67base_generations.json"
JUD = ROOT / "evals" / "s67base_judgments.json"
OUT = ROOT / "evals" / "s76_dualjudge_sonda.json"
CLAUDE_MODEL = "claude-opus-4-6"  # = VALIDATOR_MODEL canonico (judge_disagreement.py)
GPT_MODEL = "gpt-5.5"
# Orden de severidad para medir DIRECCION del desacuerdo.
ORDER = {"PASS": 0, "PARCIAL": 1, "FALLO": 2}


def _strip(txt: str) -> str:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1]
        if txt.startswith("json"):
            txt = txt[4:]
        txt = txt.strip()
    return txt


def _verdict(txt: str) -> str | None:
    try:
        return json.loads(_strip(txt)).get("veredicto")
    except Exception:
        return None


def _modal(verdicts: list[str]) -> str | None:
    vs = [v for v in verdicts if v in ORDER]
    if not vs:
        return None
    return Counter(vs).most_common(1)[0][0]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3, help="runs por gold a juzgar con Claude (0..k-1)")
    args = ap.parse_args()

    from anthropic import Anthropic
    anth = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    gen = json.loads(GEN.read_text(encoding="utf-8"))
    jud = json.loads(JUD.read_text(encoding="utf-8"))
    golds = {g["qid"]: g for g in gold_store.load() if g.get("qid")}

    # Embargo: s67base es dev; assert duro por si acaso.
    heldout = {g.get("qid") for g in gold_store.heldout()}
    leak = [q for q in gen if q in heldout]
    if leak:
        sys.exit(f"EMBARGO: held-out en s67base_generations: {leak}")

    rows = []
    qids = sorted(gen.keys())
    print(f"Sonda dual-judge HOLISTICO: {CLAUDE_MODEL} (2o) vs {GPT_MODEL} (actual) | "
          f"golds={len(qids)} | k={args.k}\n")
    for qid in qids:
        g = golds.get(qid)
        if not g:
            continue
        gpt_verdicts = [jud[qid][k].get("veredicto") for k in sorted(jud.get(qid, {}))]
        gpt_modal = _modal(gpt_verdicts)

        claude_verdicts = []
        run_keys = sorted(gen[qid].keys())[: args.k]
        for k in run_keys:
            ans = (gen[qid][k].get("answer") or "")[:4000]
            user = _JUDGE_USER.format(
                question=g.get("question", ""),
                expected=g.get("conducta_esperada", ""),
                gold=g.get("gold_answer", ""),
                bot=ans,
            )
            try:
                resp = anth.messages.create(
                    model=CLAUDE_MODEL, max_tokens=600, system=_JUDGE_SYS,
                    messages=[{"role": "user", "content": user}],
                )
                claude_verdicts.append(_verdict(resp.content[0].text))
            except Exception as e:
                print(f"  {qid} run{k}: error {e}")
                claude_verdicts.append(None)
        claude_modal = _modal(claude_verdicts)

        agree = (gpt_modal is not None and gpt_modal == claude_modal)
        direction = None
        if gpt_modal in ORDER and claude_modal in ORDER and not agree:
            direction = "claude_stricter" if ORDER[claude_modal] > ORDER[gpt_modal] else "claude_looser"
        rows.append({
            "qid": qid, "conducta": g.get("conducta_esperada"),
            "gpt_modal": gpt_modal, "claude_modal": claude_modal,
            "agree": agree, "direction": direction,
            "gpt_verdicts": gpt_verdicts, "claude_verdicts": claude_verdicts,
        })
        flag = "OK " if agree else ">> "
        print(f"{flag}{qid:7} GPT={gpt_modal:8} Claude={str(claude_modal):8} "
              f"{('' if agree else 'DISAGREE ' + (direction or ''))}")

    n = len([r for r in rows if r["gpt_modal"] in ORDER and r["claude_modal"] in ORDER])
    dis = [r for r in rows if not r["agree"] and r["gpt_modal"] in ORDER and r["claude_modal"] in ORDER]
    stricter = [r for r in dis if r["direction"] == "claude_stricter"]
    looser = [r for r in dis if r["direction"] == "claude_looser"]
    # Foco: cat019/cat020 (la sintesis dijo should_be=PASS, sesgo sistematico del juez).
    focus = {r["qid"]: {"gpt": r["gpt_modal"], "claude": r["claude_modal"]}
             for r in rows if r["qid"] in ("cat019", "cat020")}

    summary = {
        "meta": {"gpt_model": GPT_MODEL, "claude_model": CLAUDE_MODEL, "k_claude": args.k,
                 "input": "s67base frozen (39 dev)", "proposito": "measure-first dual-judge HOLISTICO"},
        "n_comparable": n,
        "agreement": n - len(dis),
        "disagreement_total": len(dis),
        "disagreement_rate": round(len(dis) / n, 3) if n else None,
        "claude_stricter": [r["qid"] for r in stricter],
        "claude_looser": [r["qid"] for r in looser],
        "focus_borderline": focus,
        "rows": rows,
    }
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 60)
    print(f"COMPARABLES: {n} | ACUERDO: {n-len(dis)} | DESACUERDO: {len(dis)} "
          f"({summary['disagreement_rate']})")
    print(f"  Claude MAS estricto (PASS/PARCIAL->peor): {len(stricter)} -> {[r['qid'] for r in stricter]}")
    print(f"  Claude MAS laxo: {len(looser)} -> {[r['qid'] for r in looser]}")
    print(f"  Foco borderline cat019/cat020: {focus}")
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
