#!/usr/bin/env python3
"""s87_rootcause.py — mapa de root-cause por-gold (motivo del miss), SEMÁNTICO.

Alberto (s87): al medir PASS, clasificar los misses por motivo (retrieval / síntesis / rerank / otro)
para saber dónde poner el foco. Integra los instrumentos SEMÁNTICOS (no el matcher léxico que infla
retrieval ~45%, DEC-070):
  - retrieval-miss (famtie canónico=14, `s85_b1_diagnosis.json`): RECALL-INTRADOC / MODEL-FILTER(identidad) / RECALL-GLOBAL
  - synthesis-miss (s87 stable-MISS certificado, `s87_synthesis_stability.yaml`): omisión estable en 2 gen
  - rerank-miss (DEF by_target `s85_retrieval_miss_DEF.yaml`)
Se une con el veredicto PASS actual (`s87_gate_report.yaml` de bvg_kmajority) → foco por-gold NO-PASS.

Uso: python scripts/s87_rootcause.py   (corre tras bvg_kmajority all BVG_RUN_ID=s87)
"""
import json
from pathlib import Path
from collections import defaultdict, Counter
import yaml

ROOT = Path("C:/Users/Admin/OneDrive - fontiber com/Documents/Claude/Technical Bot")

# 1) retrieval-miss canónico (famtie=14) por gold
diag = json.loads((ROOT/"evals/s85_b1_diagnosis.json").read_text(encoding="utf-8"))
retr = defaultdict(list)
for m in diag["misses"]:
    sub = ("MODEL-FILTER/identidad" if m["etapa"] == "MODEL-FILTER"
           else "RECALL-INTRADOC" if "within-doc" in (m.get("motivos") or []) or "INTRA" in m.get("lever","")
           else "RECALL-GLOBAL")
    retr[m["qid"]].append({"valor": m["valor"], "sub": sub})

# 2) synthesis stable-MISS por gold
stab = yaml.safe_load((ROOT/"evals/s87_synthesis_stability.yaml").read_text(encoding="utf-8"))
synth = defaultdict(list)
for f in stab.get("stable_miss_facts", []):
    synth[f["qid"]].append(f["valor"])

# 3) rerank-miss (DEF by_target) por gold
defd = yaml.safe_load((ROOT/"evals/s85_retrieval_miss_DEF.yaml").read_text(encoding="utf-8"))
rerank = defaultdict(list)
for r in defd["reps"][0]["results"]:
    for fct in r["facts"]:
        if fct["bucket_target"] == "RERANK-MISS":
            rerank[r["qid"]].append(fct["valor"])

# 4) veredicto PASS actual (si existe)
gate_path = ROOT/"evals/s87_gate_report.yaml"
verdict = {}
if gate_path.exists():
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    for g in gate.get("golds", []):
        verdict[g["qid"]] = {"bucket": g.get("bucket"), "veredicto": g.get("veredicto"),
                             "conducta_esperada": g.get("conducta_esperada"),
                             "atribucion_lexica": g.get("atribucion")}

allq = sorted(set(retr) | set(synth) | set(rerank) | set(verdict))
print(f"{'gold':8s} {'PASS?':13s} {'retr(famtie)':22s} {'synth-stable':13s} {'rerank':8s}  blocker-primario")
print("-"*110)
focus = Counter()
per_gold = {}
for q in allq:
    v = verdict.get(q, {})
    bucket = v.get("bucket", "?")
    nr = len(retr.get(q, [])); ns = len(synth.get(q, [])); nk = len(rerank.get(q, []))
    retr_subs = Counter(x["sub"] for x in retr.get(q, []))
    # blocker primario (solo relevante si NO-PASS): el bucket con más hechos-miss; identidad separada
    ident = sum(1 for x in retr.get(q, []) if "identidad" in x["sub"])
    cand = []
    if ns: cand.append(("SÍNTESIS", ns))
    if nr-ident: cand.append(("RETRIEVAL", nr-ident))
    if ident: cand.append(("IDENTIDAD", ident))
    if nk: cand.append(("RERANK", nk))
    primary = max(cand, key=lambda x: x[1])[0] if cand else ("—" if bucket=="PASS-control" else "OTRO(gold/juez)")
    is_nopass = bucket in ("residual", "K-INESTABLE")
    if is_nopass or (bucket=="?" and (ns or nr or nk)):
        focus[primary] += 1
    per_gold[q] = {"bucket": bucket, "veredicto": v.get("veredicto"), "n_retr": nr, "ident": ident,
                   "n_synth": ns, "n_rerank": nk, "retr_subs": dict(retr_subs), "primary": primary}
    rs = ",".join(f"{k.split('/')[0][:6]}:{n}" for k,n in retr_subs.items()) or "-"
    print(f"{q:8s} {str(bucket):13s} {rs:22s} {ns:<13d} {nk:<8d} {primary if is_nopass else ('PASS' if bucket=='PASS-control' else primary)}")

print("\n=== FOCO (blocker primario entre NO-PASS + golds con misses) ===")
for k,n in focus.most_common():
    print(f"  {k:22s} {n}")
out = ROOT/"evals/s87_rootcause.yaml"
out.write_text(yaml.safe_dump({"focus": dict(focus), "per_gold": per_gold}, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"\n[written] {out}")
