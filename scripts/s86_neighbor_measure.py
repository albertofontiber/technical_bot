"""s86 B2 — harness de medición del neighbor-window (flag NEIGHBOR_WINDOW).

CRÍTICO B del dúo: `rederive` usa el pool CONGELADO (pin) → invisible a un cambio de
código. Aquí re-corremos `retrieve_chunks` CON el código nuevo (flag ON) para producir el
pool NUEVO, y comparamos contra el pin del DEF.yaml.

Medición judge-free y EXACTA usando los votos congelados (≥4) del DEF:
  - un MISS se RESUELVE  sii un chunk-valor conocido (voto≥4, family-tie) entra al pool nuevo.
  - una REGRESIÓN ocurre sii un fact que estaba (todos sus soportes) pierde TODOS sus soportes
    conocidos del pool (los chunks nuevos no pueden causar regresión → check exacto).
El juez SOLO se necesitaría si el chunk-valor conocido no entra pero otro chunk nuevo sirve
(lo marcamos como 'revisar-juez', no lo contamos como resuelto → cota inferior honesta).

Uso: NEIGHBOR_WINDOW=2 python scripts/s86_neighbor_measure.py
"""
import os
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ.setdefault("HYDE_ENABLED", "false")
import sys, yaml, json
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.rag.retriever import retrieve_chunks
from scripts.audit_retrieval_funnel import source_matches_target
from scripts.retrieval_miss_judge import load_dev

# A/B jitter-controlado: comparamos el pool W=0 (baseline fresco) vs W=WTEST en la MISMA
# corrida → aísla el efecto del neighbor-window de la variabilidad del pool (el pin congelado
# NO sirve de baseline: retrieve_chunks tiene jitter, DEC-073). El flag se lee en cada llamada.
WTEST = int((os.getenv("WTEST", "2") or "2").strip() or "2")
POOL_K = 50
THRESH = 4

def pool_ids_for(q, w):
    os.environ["NEIGHBOR_WINDOW"] = str(w)
    pool = retrieve_chunks(q, top_k=POOL_K)
    return pool

DEF = yaml.safe_load((ROOT / "evals" / "s85_retrieval_miss_DEF.yaml").read_text(encoding="utf-8"))
res = {r["qid"]: r for r in DEF["reps"][0]["results"]}
golds = {g["qid"]: g for g in load_dev()}

# los 14 misses canónicos (para el reporte de resolución por cluster)
INTRADOC = {("cat016","autobusqueda"),("hp006","Fallo de Tierra"),("hp006","Tierra"),
            ("hp006","ISO-X"),("hp011","05 a 295 seg"),("hp012","2 lazos / 396"),
            ("hp013","PWR-R"),("hp014","35")}
RGLOBAL = {("cat013","CLIP"),("hp018","1 A")}
MFILTER = {("hp018","4 circuitos"),("hp018","6K8"),("hp018","diodo"),("hp018","Sirenas A,B,C,D")}

def build_srcmap(r, *pools):
    m = {}
    for c in r["pool_pin"] + r["manual_pin"]:
        m[c["id"]] = c.get("src")
    for pool in pools:
        for c in pool:
            m.setdefault(c.get("id"), c.get("source_file"))
    return m

def tie(cid, srcmap, toks):
    return (not toks) or source_matches_target(srcmap.get(cid) or "", toks)

resolved, regressions = [], []
per_gold_delta = {}

QIDS = [x for x in (os.getenv("QIDS", "") or "").replace(",", " ").split() if x]

for qid in sorted(res):
    r = res[qid]
    if qid not in golds:
        continue
    if QIDS and qid not in QIDS:
        continue
    q = golds[qid]["question"]
    pool0 = pool_ids_for(q, 0)          # baseline fresco (jitter control)
    poolW = pool_ids_for(q, WTEST)      # con neighbor-window
    ids0 = {c.get("id") for c in pool0}
    idsW = {c.get("id") for c in poolW}
    srcmap = build_srcmap(r, pool0, poolW)
    targets = r["targets"]
    per_gold_delta[qid] = {"added_vs_W0": len(idsW - ids0), "evicted_vs_W0": len(ids0 - idsW),
                           "n_neighbor": sum(1 for c in poolW if c.get("_channel")=="NEIGHBOR")}
    for f in r["facts"]:
        valor = f["valor"]
        sup = {cid for cid, v in (f.get("votes") or {}).items() if v >= THRESH}
        sup_tgt = {cid for cid in sup if tie(cid, srcmap, targets)}
        in0 = bool(sup_tgt & ids0)     # soporte en el pool baseline (W=0)
        inW = bool(sup_tgt & idsW)     # soporte en el pool con neighbor-window
        key = (qid, valor)
        if not in0 and inW:
            resolved.append(key)       # el neighbor-window METIÓ el chunk-valor
        elif in0 and not inW:
            regressions.append(key)    # el neighbor-window EXPULSÓ el chunk-valor

def cluster(name, S):
    got = [k for k in resolved if k in S]
    print(f"  {name}: resueltos {len(got)}/{len(S)}  {sorted(got)}")

print(f"\n===== NEIGHBOR-WINDOW W={WTEST} vs W=0 (jitter-controlado) — {len(res)} golds dev =====")
print(f"\n[RESOLUCIÓN de los 14 misses]")
cluster("RECALL-INTRADOC", INTRADOC)
cluster("RECALL-GLOBAL  ", RGLOBAL)
cluster("MODEL-FILTER   ", MFILTER)
print(f"\n[NO-REGRESIÓN] facts que PASABAN en W=0 y el neighbor-window EXPULSÓ: {len(regressions)}")
for k in regressions:
    print("   REGRESION:", k)
tot_added = sum(v["added_vs_W0"] for v in per_gold_delta.values())
tot_evict = sum(v["evicted_vs_W0"] for v in per_gold_delta.values())
tot_neigh = sum(v["n_neighbor"] for v in per_gold_delta.values())
print(f"\n[BLOAT vs W=0] añadidos {tot_added} · expulsados {tot_evict} · vecinos-en-pool {tot_neigh} · sobre {len(per_gold_delta)} golds")
json.dump({"WTEST":WTEST,"resolved":[list(k) for k in resolved],"regressions":[list(k) for k in regressions],
           "per_gold_delta":per_gold_delta},
          open(ROOT/"evals"/f"s86_neighbor_W{WTEST}.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n-> evals/s86_neighbor_W{WTEST}.json")
