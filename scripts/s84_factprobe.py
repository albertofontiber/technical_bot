"""s84 fact-probe: for a retrieval-miss fact, dump the evidence needed to diagnose
WHY the answer chunk isn't retrieved. Usage: python scripts/s84_factprobe.py <qid> "<value>"

Dumps: target manual chunk(s) near the gold cita page (the ANSWER chunk) with language;
which chunks of the target manual DID make the pool; the query's CONTENT keywords (what
the within-doc FTS searches); whether the manual is in the pool.
"""
import os, sys, re, yaml, httpx
os.environ["CHUNKS_TABLE"] = "chunks_v2"; os.environ["LEVER2_IDENTITY"] = "on"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.rag import retriever as R
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    qid, value = sys.argv[1], sys.argv[2]
    golds = {g["qid"]: g for g in yaml.safe_load(open(os.path.join(ROOT,"evals/gold_answers_v1.yaml"),encoding="utf-8"))}
    g = golds[qid]; q = g["question"]
    af = next((f for f in g.get("atomic_facts",[]) if f.get("valor")==value), {})
    cita = af.get("cita",""); texto = af.get("texto","")
    prov = (g.get("_provenance") or {}).get("fuente","")
    # all source_files
    allsf=set(); off=0
    while True:
        rows=httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",headers=H,params={"select":"source_file","limit":1000,"offset":off},timeout=60).json()
        if not rows: break
        for x in rows:
            if x.get("source_file"): allsf.add(x["source_file"])
        off+=1000
    toks=re.findall(r"[A-Za-z0-9][\w\-]{4,}", prov+" "+cita)
    tgt=[]
    for t in toks:
        t2=t.replace(".pdf","")
        for sf in sorted(allsf):
            if t2.lower() in sf.lower() and sf not in tgt: tgt.append(sf)
    tgt=tgt[:3]
    pages=[int(p) for p in re.findall(r"p\s?(\d{1,3})", cita)]
    print(f"=== {qid} | value={value!r} ===")
    print(f"QUESTION: {q}")
    print(f"GOLD texto: {texto[:180]}")
    print(f"cita={cita!r} | target manuals={tgt} | cita pages={pages}")
    print(f"CONTENT keywords (what within-doc FTS searches): {R._content_keywords(q)}")
    # pool
    pool=R.retrieve_chunks(q, top_k=50)
    pool_ids={id(c) for c in pool}
    manual_in_pool=[c for c in pool if c.get('source_file') in tgt]
    print(f"manual_in_pool: {len(manual_in_pool)} chunks of target in pool; pages={sorted(set(c.get('page_number') for c in manual_in_pool))}")
    # answer chunk: target manual chunks near cita page
    for sf in tgt:
        rows=httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2",headers=H,
            params={"source_file":f"eq.{sf}","select":"page_number,product_model,language,section_title,content","limit":"600"},timeout=60).json()
        near=[r for r in rows if pages and r.get("page_number") in pages] or rows
        print(f"\n--- ANSWER-region chunks in {sf} (cita pages {pages}) ---")
        for r in sorted(near, key=lambda x:x.get('page_number') or 0)[:4]:
            txt=" ".join((r.get('content') or '').split())[:300]
            print(f"  [p{r.get('page_number')} pm={r.get('product_model')} lang={r.get('language')} sect='{(r.get('section_title') or '')[:35]}']\n    {txt}")

if __name__ == "__main__":
    main()
