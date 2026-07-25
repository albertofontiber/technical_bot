"""s86 CAPA 1 — A/B de LEVER2_IDENTITY (OFF vs ON) judge-free sobre los 39 dev.
Resolución hp018 = confirmada aparte (smoke family-aware MIE-MI-530 = 4/4). Aquí el foco es
NO-REGRESIÓN: encender el flag global no debe expulsar value-chunks de otros golds.
Método idéntico al harness s86 (votos≥4 congelados, family-tie, in_pool determinista).
"""
import os
os.environ.setdefault("CHUNKS_TABLE","chunks_v2"); os.environ.setdefault("HYDE_ENABLED","false")
os.environ["NEIGHBOR_WINDOW"]="0"
import yaml,sys,json
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import src.rag.retriever as R
from scripts.audit_retrieval_funnel import source_matches_target
from scripts.retrieval_miss_judge import load_dev

DEF=yaml.safe_load((ROOT/"evals"/"s85_retrieval_miss_DEF.yaml").read_text(encoding="utf-8"))
res={r["qid"]:r for r in DEF["reps"][0]["results"]}
golds={g["qid"]:g for g in load_dev()}
THRESH=4

def models_for(q, on):
    os.environ["LEVER2_IDENTITY"]="on" if on else ""
    return R.extract_product_models(q)

def pool_ids(q, on):
    os.environ["LEVER2_IDENTITY"]="on" if on else ""
    return {c.get("id") for c in R.retrieve_chunks(q, top_k=50)}

# PRE-FILTRO principiado: el flag solo cambia el pool si extract_product_models cambia
# (una clave de alias en la query). Los demás golds → pool idéntico OFF=ON → 0 regresión.
AFFECTED=[]
for qid in sorted(res):
    if qid not in golds: continue
    q=golds[qid]["question"]
    if models_for(q,False)!=models_for(q,True):
        AFFECTED.append(qid)
print(f"[PRE-FILTRO] golds cuya resolución de modelo cambia con LEVER2_IDENTITY: {AFFECTED}")
print(f"  (los otros {sum(1 for x in res if x in golds)-len(AFFECTED)} tienen pool idéntico OFF=ON → 0 regresión por construcción)")

def build_src(r,*pools):
    m={c["id"]:c.get("src") for c in r["pool_pin"]+r["manual_pin"]}
    # (pools son sets de ids; el src de chunks nuevos no está — solo importa para los votados,
    #  que están en pin/manual → cubierto)
    return m
def tie(cid,sm,toks): return (not toks) or source_matches_target(sm.get(cid) or "", toks)

regressions=[]; resolutions=[]; changed=[]
for qid in AFFECTED:
    r=res[qid]
    q=golds[qid]["question"]
    ids_off=pool_ids(q,False); ids_on=pool_ids(q,True)
    if ids_off!=ids_on: changed.append((qid,len(ids_on-ids_off),len(ids_off-ids_on)))
    sm=build_src(r)
    targets=r["targets"]
    for f in r["facts"]:
        sup={cid for cid,v in (f.get("votes") or {}).items() if v>=THRESH}
        sup_t={cid for cid in sup if tie(cid,sm,targets)}
        off=bool(sup_t & ids_off); on=bool(sup_t & ids_on)
        if off and not on: regressions.append((qid,f["valor"]))
        elif on and not off: resolutions.append((qid,f["valor"]))

print(f"\n===== CAPA 1 (LEVER2_IDENTITY OFF vs ON) — {sum(1 for q in res if q in golds)} golds dev =====")
print(f"\n[NO-REGRESIÓN] facts que PASABAN en OFF y ON expulsó: {len(regressions)}")
for k in regressions: print("   REGRESION:", k)
print(f"\n[RESOLUCIÓN family-tie generica] facts nuevos en ON (nota: hp018 se mide aparte family-aware): {len(resolutions)}")
for k in resolutions: print("   +", k)
print(f"\n[POOLS CAMBIADOS] {len(changed)} golds: {changed}")
json.dump({"regressions":[list(k) for k in regressions],"resolutions":[list(k) for k in resolutions],
           "changed":changed}, open(ROOT/"evals"/"s86_capa1_noregression.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> evals/s86_capa1_noregression.json")
