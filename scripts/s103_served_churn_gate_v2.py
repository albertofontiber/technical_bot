#!/usr/bin/env python3
"""s103_served_churn_gate_v2.py — DISCRIMINANTE 1 (v2, contraste CORREGIDO) del landing v3.1.

El v1 (`s103_served_churn_gate.py`) midió el contraste EQUIVOCADO: rerank(sin-surrogates) vs
rerank(con-surrogates) = efecto de PRESENCIA del canal — que ya está shippeado y gateado en
v2.2 (los surrogates compiten en el rerank de prod HOY); penalizaba el propósito del canal
(cat016 flaggeado por servir su surrogate = el flip que shippeó DEC-099). Su yaml queda como
artefacto INVÁLIDO-declarado.

v2 — contraste correcto y métrica de DAÑO (no churn crudo; churn = propósito del lever):
  old  = pools reales del carve-out s102 (dump worktree@HEAD, `evals/s103_pools_old.jsonl`)
  v3   = pools live del código v3.1 (working tree)
  B1,B2 = rerank(old) ×2 → null del no-determinismo (DEC-096) · C = rerank(v3)
  MÉTRICA por hecho OK de v2.2 (anchorable): ancla ∈ served(B1) vs ∈ served(C).
  GATE: pérdidas netas de anclas-OK-en-servido (B1→C) ≤ pérdidas del null (B1→B2).
Contexto adicional reportado: churn crudo old-vs-v3 y surrogates servidos.

Coste: 39 golds × (1 retrieve + 3 rerank Sonnet strict). ~$6-9.
Uso: python scripts/s103_served_churn_gate_v2.py
Salida: evals/s103_served_churn_gate_v2.yaml
"""
import os

BASE = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on", "IDENTITY_RESOLVE": "on",
        "IDENTITY_RESOLVE_POLICY": "ADD", "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10",
        "RERANKER_BACKEND": "llm", "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
        "HYDE_ENABLED": "false", "GENERATOR_SELECTION_BLOCK": "off", "HYQ_PILOT_FILE": "", "HYQ_TABLE": "off",
        "NEIGHBOR_WINDOW": "0"}
for k, v in BASE.items():
    os.environ[k] = v
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import unicodedata  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
import yaml  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag.reranker import rerank_chunks  # noqa: E402
from scripts.gold_store import dev  # noqa: E402


def _anchor_norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def _served(query, pool, models):
    out = rerank_chunks(query, [dict(c) for c in pool], target_models=models, strict=True)
    return out


def _anchors_in(served, anchors: dict) -> set:
    blob = " \n ".join(_anchor_norm(c.get("content") or "") for c in served)
    return {k for k, a in anchors.items() if a in blob}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # anclas de los hechos OK v2.2 por gold
    fl = yaml.safe_load(open(os.path.join(os.getcwd(), "evals", "s100_factlevel_full.yaml"),
                             encoding="utf-8"))
    ok_anchors: dict[str, dict] = {}
    for g in fl["per_gold"]:
        d = {f["key"]: _anchor_norm(f.get("valor") or "") for f in g.get("facts", [])
             if f.get("clase") == "OK" and f.get("lexically_anchorable")
             and len(_anchor_norm(f.get("valor") or "")) >= 2}
        if d:
            ok_anchors[g["qid"]] = d
    # pools old (dump del worktree@HEAD)
    old_pools: dict[str, list] = {}
    with open(os.path.join(os.getcwd(), "evals", "s103_pools_old.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if "qid" in row:
                old_pools[row["qid"]] = row["chunks"]
    golds = dev()
    rows, tot_null_loss, tot_loss, tot_gain = [], 0, 0, 0
    for g in golds:
        q = g["qid"]
        anchors = ok_anchors.get(q) or {}
        R.HYQ_TABLE_ON = True
        try:
            pool_v3 = R.retrieve_chunks(g["question"], top_k=50)
        finally:
            R.HYQ_TABLE_ON = False
        pool_old = old_pools.get(q)
        if not pool_old:
            continue
        fired = any(c.get("_hyq_surrogate") for c in pool_v3) or \
            any(c.get("_hyq_surrogate") for c in pool_old)
        models = R.extract_product_models(g["question"])
        try:
            b1 = _served(g["question"], pool_old, models)
            b2 = _served(g["question"], pool_old, models)
            c = _served(g["question"], pool_v3, models)
        except Exception as e:
            rows.append({"qid": q, "error": str(e)[:120]})
            print(f"  ⚠ {q:8s} RERANK ERROR {str(e)[:80]}", flush=True)
            continue
        s1, s2, sc = (_anchors_in(x, anchors) for x in (b1, b2, c))
        null_loss = len(s1 - s2)
        loss = len(s1 - sc)
        gain = len(sc - s1)
        churn_ids = len({x.get("id") for x in b1} - {x.get("id") for x in c})
        sur_served = sum(1 for x in c if x.get("_hyq_surrogate"))
        tot_null_loss += null_loss
        tot_loss += loss
        tot_gain += gain
        rows.append({"qid": q, "fired": fired, "n_ok_anchors": len(anchors),
                     "ok_in_served_old": len(s1), "ok_in_served_v3": len(sc),
                     "null_loss": null_loss, "loss_v3": sorted(s1 - sc),
                     "gain_v3": sorted(sc - s1), "raw_churn_ids": churn_ids,
                     "surrogates_served_v3": sur_served})
        flag = " ⚠" if loss > max(1, null_loss) else ""
        print(f"  {q:8s} okA={len(anchors):2d} old={len(s1):2d} v3={len(sc):2d} "
              f"null={null_loss} loss={loss} gain={gain} churn={churn_ids} "
              f"sur={sur_served}{flag}", flush=True)
    valid = [r for r in rows if "error" not in r]
    assert valid, "0 golds válidos — medición inválida"
    verdict = "PASA" if tot_loss <= max(2, tot_null_loss) else "NO PASA"
    to_read = [r["qid"] for r in valid if len(r.get("loss_v3", [])) > max(1, r.get("null_loss", 0))]
    print(f"\n── SERVED-CHURN v2 (old-vs-v3, anclas-OK, null-corrected) ──")
    print(f"  golds: {len(valid)} · null_loss: {tot_null_loss} · LOSS v3: {tot_loss} · GAIN v3: {tot_gain}")
    print(f"  VEREDICTO: {'✅' if verdict == 'PASA' else '❌'} {verdict} (loss ≤ max(2, null))")
    print(f"  golds a LEER (DEC-092b): {to_read}")
    yaml.safe_dump({"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                                        capture_output=True)
                              .stdout.decode().strip(),
                              "flags": {**BASE, "HYQ_TABLE": "on (call-time flip)"},
                              "old_pools": "evals/s103_pools_old.jsonl (worktree@ae624cd)",
                              "rerank_model": "claude-sonnet-4-6 strict"},
                    "tot_null_loss": tot_null_loss, "tot_loss": tot_loss,
                    "tot_gain": tot_gain, "verdict": verdict, "to_read": to_read,
                    "rows": rows},
                   open(os.path.join(os.getcwd(), "evals", "s103_served_churn_gate_v2.yaml"),
                        "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    print("→ evals/s103_served_churn_gate_v2.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
