#!/usr/bin/env python3
"""Inspección de los 8 desacuerdos factuales (DEC-021 §D, medir-primero paso 2).
Captura el CONTENIDO de la contradicción de cada juez para adjudicar: ¿caza un error REAL
o SOBRE-marca (incompletitud/paráfrasis como contradicción)? Scratch (gitignored)."""
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gold_store  # noqa: E402
from atomic_scorer import _FACTUAL_SYS, _FACTUAL_USER  # noqa: E402
import judge_disagreement as J  # noqa: E402  (reusa _gpt/_claude/_parse_list/_facts_txt)

load_dotenv(ROOT / ".env", override=True)
QIDS = ["cat007", "hp001", "hp008", "hp010", "hp015"]  # los 5 DESACUERDO-ESTABLE (K=5)

from openai import OpenAI  # noqa: E402
from anthropic import Anthropic  # noqa: E402
oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
anth = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

answers = {r["qid"]: r.get("bot_answer", "")
           for r in yaml.safe_load(open(ROOT / "evals" / "bot_vs_gold_results_k5.yaml", encoding="utf-8"))
           if r.get("qid")}
golds = {g["qid"]: g for g in gold_store.verified()}


def _show(label, contras):
    if not contras:
        print(f"    {label}: (sin contradicción)")
        return
    for c in contras:
        print(f"    {label}: hecho «{str(c.get('hecho'))[:90]}»")
        print(f"          bot dice «{str(c.get('afirmacion_bot'))[:90]}»")
        print(f"          por_qué: {str(c.get('por_que'))[:140]}")


for qid in QIDS:
    g = golds[qid]
    ans = (answers.get(qid) or "")[:4000]
    present = [f for f in (g.get("atomic_facts") or []) if f.get("estado") != "ausente-probado"]
    fu = _FACTUAL_USER.format(facts=J._facts_txt(present, True), answer=ans)
    g_contra = J._parse_list(J._gpt(oai, _FACTUAL_SYS, fu), "contradicciones") or []
    c_contra = J._parse_list(J._claude(anth, _FACTUAL_SYS, fu), "contradicciones") or []
    print(f"\n=== {qid} === (pregunta: {g.get('question','')[:80]})")
    _show("GPT  ", g_contra)
    _show("CLAUDE", c_contra)
