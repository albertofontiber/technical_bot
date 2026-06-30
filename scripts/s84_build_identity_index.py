"""s84 F1 — Build the inverse identity index  model -> {source_files by role}.

Derived view of the clean asset (evals/s83_document_models_final.jsonl, DEC-067).
KEY = normkey(model)  (strips '-', ' ', '/' uniformly) — the SAME normalization the
consumption seam will use on BOTH build and lookup (dúo#12 finding #5: normkey vs
normalize_model diverged on '/' → silent join holes; normkey on both sides also fixes
the dash-vs-slash case 40-40 ↔ 40/40 → 4040).

Output: evals/s84_identity_index.json  (branch-local, $0, re-runnable; NOTHING to DB).
Also runs the JOIN-RATE TEST (dúo#12 #5): what fraction of (a) asset models and
(b) dev-gold extracted query tokens join to the index under normkey.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from src.rag import catalog as C  # normkey: strips -, space, /

def nk(s): return C.normkey(s or "")

ASSET = os.path.join(ROOT, "evals/s83_document_models_final.jsonl")
OUT   = os.path.join(ROOT, "evals/s84_identity_index.json")

def build():
    docs = [json.loads(l) for l in open(ASSET, encoding="utf-8")]
    idx = collections.defaultdict(lambda: {"primary": [], "secondary": [], "canonical": None})
    for d in docs:
        sf = d["source_file"]
        for m in d.get("models", []):
            role = "primary" if m.get("role") == "primary" else "secondary"
            cano = m["canonical_model"]
            keys = {nk(cano)} | {nk(a) for a in m.get("aliases", [])}
            for k in keys:
                if not k:
                    continue
                e = idx[k]
                if sf not in e[role]:
                    e[role].append(sf)
                if e["canonical"] is None:
                    e["canonical"] = cano
    # plain dict, sorted source lists for determinism
    out = {}
    for k, e in idx.items():
        out[k] = {"primary": sorted(set(e["primary"])),
                  "secondary": sorted(set(e["secondary"])),
                  "canonical": e["canonical"]}
    return out, docs

def join_rate_tests(idx):
    # (a) asset self-consistency: every canonical model must resolve
    asset_models = set()
    for l in open(ASSET, encoding="utf-8"):
        for m in json.loads(l).get("models", []):
            asset_models.add(m["canonical_model"])
    hit = sum(1 for m in asset_models if nk(m) in idx)
    print(f"[join (a) asset canonical models]  {hit}/{len(asset_models)} resolve "
          f"({100*hit/len(asset_models):.1f}%)  [self-consistency, expect 100%]")

    # (b) dev-gold extracted query tokens -> index, under BOTH LEVER2_IDENTITY states
    import yaml
    from src.rag import retriever as R
    golds = yaml.safe_load(open(os.path.join(ROOT, "evals/gold_answers_v1.yaml"), encoding="utf-8"))
    dev = [g for g in golds if g.get("split") == "dev"]
    for lev in ("off", "on"):
        os.environ["LEVER2_IDENTITY"] = lev
        tot = 0; join = 0; miss = []
        for g in dev:
            for m in R.extract_product_models(g["question"]):
                tot += 1
                if nk(m) in idx: join += 1
                else: miss.append((g["qid"], m, nk(m)))
        print(f"[join (b) dev-gold tokens LEVER2_IDENTITY={lev}]  {join}/{tot} join "
              f"({100*join/max(tot,1):.1f}%)")
        if miss:
            print("    MISS:", miss[:12])

if __name__ == "__main__":
    idx, docs = build()
    json.dump(idx, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"[build] {len(docs)} docs -> {len(idx)} distinct model keys -> {OUT}")
    print(f"[build] sample: 40-40 -> {idx.get(nk('40-40'))!r}")
    print(f"[build] sample: ZX5e  -> {idx.get(nk('ZX5e'))!r}")
    print()
    join_rate_tests(idx)
