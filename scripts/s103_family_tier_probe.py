#!/usr/bin/env python3
"""s103_family_tier_probe.py — artefacto F9 (regla C): ¿cuántos chunks POSITIVAMENTE
cross-family hay en los pools de los golds clave, con la lista RESUELTA de modelos?

Sostiene (o refuta) la claim que demotó la cascada family-aware como landing: "cat022/hp011
tienen 0 cross-family en pool → la cascada degenera a la v2.1 medida NO-GO". El probe inline
original usó la lista PRE-resolver (inválido: marcó MIE-MI-530 correcto como cross-family en
hp018). Este captura los modelos EXACTOS que Step 5a recibe (spy sobre el diversify).

Uso: python scripts/s103_family_tier_probe.py
Salida: evals/s103_family_tier_probe.json
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
import subprocess  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for k, v in BASE.items():
    os.environ[k] = v
from collections import Counter  # noqa: E402
from src.rag import retriever as R  # noqa: E402
from src.rag import series_registry as S  # noqa: E402
from scripts.gold_store import dev  # noqa: E402

QIDS = ["cat022", "hp011", "hp018", "cat021", "hp012", "cat016"]


def crossfam_positive(c: dict, models: list[str]) -> bool:
    """POSITIVAMENTE cross-family: pm conocido y falla nivel-2/nivel-1 para TODOS los
    modelos resueltos. pm vacío/unknown → False (fail-open: la clase hp009 protegida)."""
    pm = (c.get("product_model") or "").strip().lower()
    if not pm or pm in ("unknown", "n/a", "generic"):
        return False
    return not S.passes_nivel2(c, models)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    golds = {g["qid"]: g for g in dev()}
    orig = R._diversify_by_source_file
    cap: dict = {}

    def spy(chunks, k, models, *a, **kw):
        cap["models"] = list(models or [])
        return orig(chunks, k, models, *a, **kw)

    R._diversify_by_source_file = spy
    rows = []
    for qid in QIDS:
        cap.clear()
        R.HYQ_TABLE_ON = True
        try:
            pool = R.retrieve_chunks(golds[qid]["question"], top_k=50)
        finally:
            R.HYQ_TABLE_ON = False
        models = cap.get("models") or []
        body = [c for c in pool if not c.get("_hyq_surrogate")]
        cf = [c for c in body if crossfam_positive(c, models)]
        tail10 = body[-10:]
        rows.append({"qid": qid, "models_resueltos": models, "pool_n": len(pool),
                     "crossfam_total": len(cf),
                     "crossfam_tail10": sum(1 for c in tail10 if crossfam_positive(c, models)),
                     "crossfam_sources": dict(Counter(
                         (c.get("source_file") or "")[:20] for c in cf))})
        print(f"  {qid:8s} models={models} crossfam={len(cf)}/{len(body)} "
              f"(cola-10: {rows[-1]['crossfam_tail10']})", flush=True)
    R._diversify_by_source_file = orig
    out = {"stamp": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                               capture_output=True).stdout.decode().strip(),
                     "flags": {**BASE, "HYQ_TABLE": "on (call-time flip)"},
                     "nota": "modelos = lista RESUELTA capturada en el diversify (spy)"},
           "rows": rows}
    path = os.path.join(os.getcwd(), "evals", "s103_family_tier_probe.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
