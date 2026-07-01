"""s86 — A/B de IDENTITY_MAP (OFF vs ON) judge-free sobre los 39 dev.
Pre-filtro: solo golds con cobertura de mapa (allowed_sources no-vacío); el resto fail-open =
pool idéntico → 0 regresión por construcción. Método idéntico a los harness s86 (votos≥4
congelados, family-tie, in_pool determinista). Resolución hp018 se confirma aparte (smoke).
"""
import os
os.environ.setdefault("CHUNKS_TABLE","chunks_v2"); os.environ.setdefault("HYDE_ENABLED","false")
os.environ["NEIGHBOR_WINDOW"]="0"; os.environ["LEVER2_IDENTITY"]=""
import yaml,sys,json
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import src.rag.retriever as R
from src.rag.identity_index import allowed_sources
from scripts.audit_retrieval_funnel import source_matches_target
from scripts.retrieval_miss_judge import load_dev

DEF=yaml.safe_load((ROOT/"evals"/"s85_retrieval_miss_DEF.yaml").read_text(encoding="utf-8"))
res={r["qid"]:r for r in DEF["reps"][0]["results"]}
golds={g["qid"]:g for g in load_dev()}
THRESH=4

def pool_ids(q,on):
    os.environ["IDENTITY_MAP"]="on" if on else ""
    return {c.get("id") for c in R.retrieve_chunks(q, top_k=50)}
def tie(cid,sm,toks): return (not toks) or source_matches_target(sm.get(cid) or "",toks)

# pre-filtro: golds con cobertura de mapa (superset de afectados)
AFFECTED=[]
for qid in sorted(res):
    if qid not in golds: continue
    if allowed_sources(R.extract_product_models(golds[qid]["question"])):
        AFFECTED.append(qid)
print(f"[PRE-FILTRO] golds con cobertura de mapa: {len(AFFECTED)} / {sum(1 for x in res if x in golds)} -> {AFFECTED}")

regressions=[]; resolutions=[]; changed=[]
for qid in AFFECTED:
    r=res[qid]; q=golds[qid]["question"]
    ids_off=pool_ids(q,False); ids_on=pool_ids(q,True)
    sm={c["id"]:c.get("src") for c in r["pool_pin"]+r["manual_pin"]}
    if ids_off!=ids_on: changed.append((qid,len(ids_on-ids_off),len(ids_off-ids_on)))
    for f in r["facts"]:
        sup={cid for cid,v in (f.get("votes") or {}).items() if v>=THRESH}
        sup_t={cid for cid in sup if tie(cid,sm,r["targets"])}
        off=bool(sup_t&ids_off); on=bool(sup_t&ids_on)
        if off and not on: regressions.append((qid,f["valor"]))
        elif on and not off: resolutions.append((qid,f["valor"]))

print(f"\n===== IDENTITY_MAP OFF vs ON — {len(AFFECTED)} golds afectados =====")
print(f"\n[NO-REGRESIÓN] facts que PASABAN y ON expulsó: {len(regressions)}")
for k in regressions: print("   REGRESION:",k)
print(f"\n[RESOLUCIÓN family-tie generica] nuevos en ON: {len(resolutions)}")
for k in resolutions: print("   +",k)
print(f"\n[POOLS CAMBIADOS] {len(changed)}: {changed}")
json.dump({"regressions":[list(k) for k in regressions],"resolutions":[list(k) for k in resolutions],
           "changed":changed,"affected":AFFECTED},
          open(ROOT/"evals"/"s86_map_noregression.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("\n-> evals/s86_map_noregression.json")
