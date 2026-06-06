#!/usr/bin/env python3
"""Medir-primero (DEC-021 §D): ¿cuánto se DESACUERDAN dos jueces (GPT-5.5 vs Claude-Opus)
en los ejes de SEGURIDAD del scorer (factual = contradicción · no-fabricación), sobre las
MISMAS respuestas del bot y los MISMOS prompts que `atomic_scorer`?

Decide el fork del dual-judge SIN construirlo (eval-driven):
  - desacuerdo BAJO  -> el juez único es estable cross-model -> DIFERIR el dual-judge.
  - desacuerdo ALTO  -> GPT-5.5 tiene error SISTEMÁTICO que K-mayoría (mismo modelo) NO caza
                        -> construir el dual-judge CON dato.

NO toca el scorer canónico (gpt-5.5 sigue siendo el juez). Reusa los prompts (misma tarea de
juicio) y llama a las dos APIs nativas. Salida cruda en evals/_s47_judge_disagreement.json.

Uso:  python scripts/judge_disagreement.py [--answers <yaml>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
import gold_store  # noqa: E402
from atomic_scorer import (  # noqa: E402
    _FACTUAL_SYS, _FACTUAL_USER, _UNDUE_SYS, _UNDUE_USER,
)

load_dotenv(ROOT / ".env", override=True)
DEFAULT_ANSWERS = ROOT / "evals" / "bot_vs_gold_results_k5.yaml"
OUT = ROOT / "evals" / "_s47_judge_disagreement.json"
GPT_MODEL = "gpt-5.5"
CLAUDE_MODEL = "claude-opus-4-6"  # = VALIDATOR_MODEL (el auditor del proyecto, src/config.py)


def _strip(txt: str) -> str:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    return txt


def _parse_list(txt: str, key: str):
    """Devuelve la lista bajo `key`, o None si no parsea (= no evaluable, se excluye)."""
    try:
        v = json.loads(_strip(txt)).get(key, [])
        return v if isinstance(v, list) else None
    except Exception:
        return None


def _gpt(oai, sys_p: str, user_p: str) -> str:
    resp = oai.chat.completions.create(
        model=GPT_MODEL, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": sys_p},
                  {"role": "user", "content": user_p}])
    return resp.choices[0].message.content


def _claude(anth, sys_p: str, user_p: str) -> str:
    resp = anth.messages.create(
        model=CLAUDE_MODEL, max_tokens=1024, system=sys_p,
        messages=[{"role": "user", "content": user_p}])
    return resp.content[0].text


def _facts_txt(facts, with_valor: bool) -> str:
    if with_valor:
        return "\n".join(
            f"- {f.get('texto', '')}" + (f" [valor: {f['valor']}]" if f.get("valor") else "")
            for f in facts)
    return "\n".join(f"- {f.get('texto', '')}" for f in facts)


def _flag(lst):
    """lista vacía -> False (sin hallazgo); con elementos -> True; None -> None (no evaluable)."""
    return None if lst is None else (len(lst) > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default=str(DEFAULT_ANSWERS))
    args = ap.parse_args()

    from openai import OpenAI
    from anthropic import Anthropic
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    anth = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with open(args.answers, encoding="utf-8") as fh:
        answers = {r["qid"]: r.get("bot_answer", "")
                   for r in (yaml.safe_load(fh) or []) if r.get("qid")}

    golds = [g for g in gold_store.verified() if g.get("atomic_facts")]
    print(f"Jueces: {GPT_MODEL} vs {CLAUDE_MODEL} | golds={len(golds)} | answers={args.answers}\n")

    rows = []
    for g in sorted(golds, key=lambda x: x.get("qid")):
        qid = g.get("qid")
        if qid not in answers:
            print(f"  {qid}: (sin respuesta — saltado)")
            continue
        ans = (answers[qid] or "")[:4000]
        facts = g.get("atomic_facts") or []
        present = [f for f in facts if f.get("estado") != "ausente-probado"]
        absent = [f for f in facts if f.get("estado") == "ausente-probado"]

        # --- Eje FACTUAL (contradicción sí/no) ---
        fu = _FACTUAL_USER.format(facts=_facts_txt(present, True), answer=ans)
        try:
            fact_g = _flag(_parse_list(_gpt(oai, _FACTUAL_SYS, fu), "contradicciones"))
            fact_c = _flag(_parse_list(_claude(anth, _FACTUAL_SYS, fu), "contradicciones"))
        except Exception as e:
            print(f"  {qid}: FACTUAL error {e}")
            fact_g = fact_c = None

        # --- Eje NO-FABRICACIÓN (solo si hay hechos ausente-probado) ---
        fab_g = fab_c = None
        if absent:
            uu = _UNDUE_USER.format(facts=_facts_txt(absent, False), answer=ans)
            try:
                fab_g = _flag(_parse_list(_gpt(oai, _UNDUE_SYS, uu), "fabricaciones"))
                fab_c = _flag(_parse_list(_claude(anth, _UNDUE_SYS, uu), "fabricaciones"))
            except Exception as e:
                print(f"  {qid}: NO-FAB error {e}")

        rows.append({"qid": qid, "fact_gpt": fact_g, "fact_claude": fact_c,
                     "fab_gpt": fab_g, "fab_claude": fab_c, "n_absent": len(absent)})
        print(f"  {qid}: factual gpt={fact_g} claude={fact_c}"
              + (f" | no-fab gpt={fab_g} claude={fab_c}" if absent else ""))

    def _dis(a, b):
        return a is not None and b is not None and a != b

    fact_pairs = [(r["fact_gpt"], r["fact_claude"]) for r in rows]
    fab_pairs = [(r["fab_gpt"], r["fab_claude"]) for r in rows if r["n_absent"]]
    fact_dis = [r for r in rows if _dis(r["fact_gpt"], r["fact_claude"])]
    fab_dis = [r for r in rows if _dis(r["fab_gpt"], r["fab_claude"])]
    fact_n = sum(1 for a, b in fact_pairs if a is not None and b is not None)
    fab_n = sum(1 for a, b in fab_pairs if a is not None and b is not None)

    print("\n" + "=" * 60)
    print(f"DESACUERDO FACTUAL (contradicción sí/no): {len(fact_dis)}/{fact_n}")
    print(f"DESACUERDO NO-FABRICACIÓN (fabricación sí/no): {len(fab_dis)}/{fab_n}")
    for r in fact_dis:
        print(f"  [FACTUAL] {r['qid']}: gpt={r['fact_gpt']} claude={r['fact_claude']}")
    for r in fab_dis:
        print(f"  [NO-FAB ] {r['qid']}: gpt={r['fab_gpt']} claude={r['fab_claude']}")

    summary = {"gpt_model": GPT_MODEL, "claude_model": CLAUDE_MODEL,
               "fact_disagree": len(fact_dis), "fact_n": fact_n,
               "fab_disagree": len(fab_dis), "fab_n": fab_n, "rows": rows}
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
