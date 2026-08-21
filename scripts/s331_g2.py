#!/usr/bin/env python3
"""s331 G2 (v6 §4) — sweep-39 de COMPOSICIÓN SERVIDA, OFF vs ON (ship candidate
= 4 flags: F1_RESOLVE_GOVERNED + F1_MENTION_PRECEDENCE + GENERATOR_NO_REASK +
IDENTITY_FETCH), con línea-base de RUIDO OFF-vs-OFF (DEC-096: el LLM-rerank no
es determinista a temp=0 — ningún diff cuenta como señal si el gold ya churnea
entre dos OFF). La GENERACIÓN va STUBEADA: composición no la necesita y el coste
queda en retrieval+rerank. Centinelas hp009/hp001 siempre detallados. Al final
corre los MT flows (`test_multiturn_vs_gold --contract`) con los flags ON.

Uso:  python scripts/s331_g2.py [--out evals/s331_g2_v1.json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("IDENTITY_RESOLVE", "on")
os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "replace")

import yaml  # noqa: E402

ON_FLAGS = {"F1_RESOLVE_GOVERNED": "on", "F1_MENTION_PRECEDENCE": "on",
            "GENERATOR_NO_REASK": "on", "IDENTITY_FETCH": "on"}
S331_KEYS = tuple(ON_FLAGS)
SENTINELS = ("hp009", "hp001")

_STUB_GEN = {"answer": "", "diagrams": [], "stop_reason": None,
             "input_tokens": None, "output_tokens": None}


class _StubGenAdapters:
    """Proxy sobre los adapters REALES con `generate` stubeado ($0 en generación;
    retrieval/rerank/coverage intactos — la composición servida es idéntica)."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def generate(self, *_a, **_k):
        return dict(_STUB_GEN)


def _set_arm(on: bool) -> None:
    for k in S331_KEYS:
        os.environ.pop(k, None)
    if on:
        os.environ.update(ON_FLAGS)


def _served_for(question: str) -> dict:
    from src.orchestrator import from_production, run_turn
    from src.orchestrator.conversation_policy import WorkingState
    from src.orchestrator.conversation_policy_impl import (
        resolve_conversational_turn,
    )
    from src.orchestrator.telegram_adapter import build_turn_request
    res, _ = resolve_conversational_turn(
        question, WorkingState(), datetime.now(timezone.utc))
    req = build_turn_request(
        query=res.query_for_retrieval, query_for_retrieval=res.query_for_retrieval,
        target_models=res.target_models, available_models=res.available_models,
        update_id=0, chat_id=0, source="harness", transcription=None,
        turn_identity=res.turn_identity,
    )
    t0 = time.perf_counter()
    turn = run_turn(req, _StubGenAdapters(from_production()))
    ms = int((time.perf_counter() - t0) * 1000)
    return {
        "served": [f"{c.get('source_file')}#{c.get('chunk_index')}"
                   for c in turn.retrieval.chunks],
        "route": res.route.value,
        "models": list(res.target_models or ()),
        "failures": list(turn.retrieval.channel_failures or [])
        if turn.retrieval.retrieval_measured else [],
        "ms": ms,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evals" / "s331_g2_v1.json"))
    args = ap.parse_args()

    golds = [r for r in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))
        if r.get("split") == "dev"]
    print(f"golds dev: {len(golds)}")

    from src.rag import catalog_resolver as CR
    runs: dict[str, dict[str, dict]] = {"off": {}, "off2": {}, "on": {}}
    for arm in ("off", "off2", "on"):
        _set_arm(arm == "on")
        CR.refresh_presence()
        print(f"[{arm}] presencia={CR.presence_estado()}")
        for g in golds:
            runs[arm][g["qid"]] = _served_for(g["question"])
        n_fail = sum(1 for v in runs[arm].values() if v["failures"])
        print(f"[{arm}] hecho · golds con fallos de canal: {n_fail}")

    noise = sorted(q for q in runs["off"]
                   if runs["off"][q]["served"] != runs["off2"][q]["served"])
    diffs = sorted(q for q in runs["off"]
                   if runs["off"][q]["served"] != runs["on"][q]["served"])
    signal = [q for q in diffs if q not in noise]
    receipt = {
        "manifest": {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_sha": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                text=True).stdout.strip(),
            "on_flags": ON_FLAGS, "n_golds": len(golds),
        },
        "noise_offvsoff": noise,
        "diffs_onvsoff": diffs,
        "signal": signal,
        "sentinels": {q: {"off": runs["off"][q]["served"],
                          "on": runs["on"][q]["served"],
                          "igual": runs["off"][q]["served"] == runs["on"][q]["served"]}
                      for q in SENTINELS},
        "latency_ms": {arm: sorted(v["ms"] for v in runs[arm].values())
                       for arm in runs},
        "detalle_signal": {q: {"off": runs["off"][q], "on": runs["on"][q]}
                           for q in signal},
        "runs": runs,
    }
    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    lat = receipt["latency_ms"]
    p50 = {a: v[len(v) // 2] for a, v in lat.items()}
    print(f"ruido OFF-vs-OFF: {len(noise)} golds → {noise}")
    print(f"diffs ON-vs-OFF: {len(diffs)} · SEÑAL (fuera de ruido): {len(signal)} → {signal}")
    for q, s in receipt["sentinels"].items():
        print(f"centinela {q}: {'IGUAL' if s['igual'] else 'DIFIERE'}")
    print(f"latencia p50 por brazo: {p50}")

    _set_arm(True)
    mt = subprocess.run([sys.executable, "scripts/test_multiturn_vs_gold.py"],
                        cwd=ROOT, capture_output=True, text=True, timeout=600)
    print(f"MT flows (flags ON): exit={mt.returncode}")
    print((mt.stdout or "").strip().splitlines()[-1] if mt.stdout else mt.stderr[-200:])
    receipt["mt_contract_on"] = {"exit": mt.returncode,
                                 "tail": (mt.stdout or "")[-400:]}
    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"recibo → {args.out}")
    return 0 if (not signal or all(receipt["sentinels"][q]["igual"]
                                   for q in SENTINELS)) and mt.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
