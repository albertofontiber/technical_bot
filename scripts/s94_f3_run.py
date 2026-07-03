#!/usr/bin/env python3
"""s94_f3_run.py — F3 del piloto (spec v2): inserción por-brazo + SWAP + famtie + triage.

⚠️ HISTÓRICO (T0 s94b): este harness usaba el sidecar PILOT_SWAP_MAP/PILOT_PARENT_SWAP del
PILOTO, retirado en T0 (el linkage vive ahora en chunks_v2.parent_id + flag
ENUNCIADOS_MULTIVECTOR; migración 007). Sus mediciones están archivadas en
evals/s94_f3_results.json + DEC-086. NO re-correr tal cual — el pase real es
scripts/enunciados_pass.py (T0-4).

Subcomandos:
  control        pin-regen HOY sin inserts (flag off) + famtie → baseline mismo-día
  arm R1|R2|R3   insert batch del brazo → pin-regen (RESOLVE=on/add + PILOT_PARENT_SWAP=on
                 + mapa del brazo) → famtie → triage _trace de los 10 hechos → ROLLBACK
                 (en finally: nunca quedan surrogates en DB)
  rollback       DELETE de TODO lo 's94-pilot:*' (limpieza manual)

Surrogates (candidatos QA-OK v2, TODOS — el flip lo da cualquier surrogate del padre):
content=enunciado · context=blurb-B7-del-padre (receta del 2/4) · embedding=
embed(context+"\\n\\n"+content) (receta corpus embed.py:52-59) · metadata=del padre ·
extraction_sha256='s94-pilot:<arm>' (rollback=1 DELETE) · mapa sidecar id→padre.

Salidas: evals/s94_retrieval_miss_{tag}.yaml + evals/s94_f3_results.json (acumulativo).
"""
from __future__ import annotations

import json
import os
import sys
import uuid

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src").is_dir(), f"cwd no es la raíz: {ROOT}"
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import httpx
import yaml

from retrieval_miss_famtie import rederive
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

POOL_K = 50
BASE = ROOT / "evals" / "s85_retrieval_miss_DEF.yaml"
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
      "Content-Type": "application/json"}
STAGES = ["channels", "post_merge", "post_neighbor", "post_superseded",
          "post_model_filter", "post_diversify", "post_lang", "final"]
RESULTS = ROOT / "evals" / "s94_f3_results.json"


def _parents_meta(ids: list[str]) -> dict:
    out = {}
    for i in range(0, len(ids), 40):
        q = ",".join(f'"{x}"' for x in ids[i:i + 40])
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H, params={
            "select": "id,context,product_model,manufacturer,source_file,page_number,"
                      "language,document_id,section_title,doc_type,content_type,chunk_index",
            "id": f"in.({q})"}, timeout=30)
        r.raise_for_status()
        for x in r.json():
            out[x["id"]] = x
    return out


def insert_arm(arm: str) -> str:
    from src.reingest.embed import embed
    f1 = json.load(open(ROOT / "evals" / "s94_f1_candidates.json", encoding="utf-8"))
    cands = [c for c in f1["candidatos"] if c["arm"] == arm and c["qa_pass"]]
    assert cands, f"sin candidatos QA-OK para {arm}"
    parents = _parents_meta(sorted({c["parent_id"] for c in cands}))
    rows, smap, texts = [], {}, []
    for c in cands:
        p = parents.get(c["parent_id"])
        if not p:
            continue
        cid = str(uuid.uuid4())
        smap[cid] = c["parent_id"]
        texts.append(f"{p['context']}\n\n{c['text']}" if p.get("context") else c["text"])
        rows.append({"id": cid, "content": c["text"], "context": p.get("context"),
                     "product_model": p.get("product_model"), "manufacturer": p.get("manufacturer"),
                     "source_file": p.get("source_file"), "page_number": p.get("page_number"),
                     "language": p.get("language"), "document_id": p.get("document_id"),
                     "section_title": p.get("section_title"), "doc_type": p.get("doc_type"),
                     "content_type": p.get("content_type"), "chunk_index": p.get("chunk_index"),
                     "extraction_sha256": f"s94-pilot:{arm}"})
    embs = []
    for i in range(0, len(texts), 100):
        embs.extend(embed(texts[i:i + 100], "document"))
    for row, e in zip(rows, embs):
        row["embedding"] = e
    for i in range(0, len(rows), 50):
        r = httpx.post(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                       headers={**_H, "Prefer": "return=minimal"},
                       json=rows[i:i + 50], timeout=60)
        r.raise_for_status()
    map_path = ROOT / "evals" / f"s94_f3_surrogate_map_{arm}.json"
    json.dump(smap, open(map_path, "w", encoding="utf-8"))
    print(f"[insert] {arm}: {len(rows)} surrogates (mapa → {map_path.name})")
    return str(map_path)


def rollback() -> int:
    r = httpx.delete(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                     headers={**_H, "Prefer": "return=minimal"},
                     params={"extraction_sha256": "like.s94-pilot:*"}, timeout=60)
    r.raise_for_status()
    chk = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                    params={"select": "id", "extraction_sha256": "like.s94-pilot:*",
                            "limit": "1"}, timeout=30)
    n = len(chk.json())
    print(f"[rollback] restantes con marca: {n}")
    assert n == 0, "ROLLBACK INCOMPLETO"
    return 0


def regen_and_famtie(tag: str) -> dict:
    from src.rag import catalog_resolver
    from src.rag.retriever import retrieve_chunks
    stamp = catalog_resolver.catalog_commit()
    d = yaml.safe_load(open(BASE, encoding="utf-8"))
    golds = {g["qid"]: g for g in yaml.safe_load(
        open(ROOT / "evals" / "gold_answers_v1.yaml", encoding="utf-8"))}
    for i, res in enumerate(d["reps"][0]["results"]):
        pool = retrieve_chunks(golds[res["qid"]]["question"], top_k=POOL_K)
        res["pool_pin"] = [{"id": c.get("id"), "pm": c.get("product_model"),
                            "src": c.get("source_file")} for c in pool]
        res["top5_ids"] = []
    d["s94_manifest"] = {"tag": tag, "identity_resolve": "on/add",
                         "pilot_parent_swap": os.getenv("PILOT_PARENT_SWAP", "off"),
                         "swap_map": os.getenv("PILOT_SWAP_MAP", ""), "catalog_commit": stamp,
                         "pool_k": POOL_K, "top5": "NO-recomputado", "base": BASE.name}
    out = ROOT / "evals" / f"s94_retrieval_miss_{tag}.yaml"
    yaml.safe_dump(d, open(out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    fam = rederive(str(out))
    print(f"[{tag}] retrieval-miss FAMILY = {fam['retrieval_miss_family']} "
          f"(misses: {[(m['qid'], m['valor'][:18]) for m in fam['misses']]})")
    return {"tag": tag, "retrieval_miss_family": fam["retrieval_miss_family"],
            "misses": [{"qid": m["qid"], "valor": m["valor"]} for m in fam["misses"]],
            "pin": out.name}


def triage(arm: str, smap: dict) -> list:
    """Para cada hecho del testbed: ¿dónde mueren surrogates/padre? (_trace)."""
    from src.rag.retriever import retrieve_chunks
    f0 = json.load(open(ROOT / "evals" / "s94_f0_testbed.json", encoding="utf-8"))
    by_parent: dict = {}
    for sid, pid in smap.items():
        by_parent.setdefault(pid, []).append(sid)
    rows = []
    for r in f0["rows"]:
        tr: dict = {}
        try:
            retrieve_chunks(r["question"], top_k=POOL_K, _trace=tr)
        except Exception as exc:
            rows.append({"qid": r["qid"], "valor": r["valor"], "error": str(exc)})
            continue
        sets = {s: tr.get(s, set()) for s in STAGES}
        pids = [a["id"] for a in r["acreditables"]]
        sids = [s for p in pids for s in by_parent.get(p, [])]
        p_last = max((STAGES.index(s) for s in STAGES for x in pids if x in sets[s]),
                     default=-1)
        s_last = max((STAGES.index(s) for s in STAGES for x in sids if x in sets[s]),
                     default=-1)
        rows.append({"qid": r["qid"], "valor": r["valor"],
                     "padre_llega_a": STAGES[p_last] if p_last >= 0 else "NUNCA",
                     "surrogate_llega_a": STAGES[s_last] if s_last >= 0 else "NUNCA"})
        print(f"  triage {r['qid']:8} {r['valor'][:18]!r:20} padre→{rows[-1]['padre_llega_a']:18} "
              f"surrogate→{rows[-1]['surrogate_llega_a']}")
    return rows


def _save(entry: dict):
    acc = json.load(open(RESULTS, encoding="utf-8")) if RESULTS.exists() else {}
    acc[entry["tag"]] = entry
    json.dump(acc, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    os.environ["IDENTITY_RESOLVE"] = "on"
    os.environ["IDENTITY_RESOLVE_POLICY"] = "add"
    if cmd == "control":
        os.environ["PILOT_PARENT_SWAP"] = "off"
        _save(regen_and_famtie("control"))
        return 0
    if cmd == "rollback":
        return rollback()
    if cmd == "arm":
        arm = sys.argv[2]
        assert arm in ("R1", "R2", "R3"), arm
        try:
            map_path = insert_arm(arm)
            os.environ["PILOT_PARENT_SWAP"] = "on"
            os.environ["PILOT_SWAP_MAP"] = map_path
            import src.rag.retriever as _rt
            _rt._PILOT_SWAP_MAP = None          # invalida cache (mapa nuevo)
            entry = regen_and_famtie(arm)
            entry["triage"] = triage(arm, json.load(open(map_path, encoding="utf-8")))
            _save(entry)
        finally:
            rollback()
        return 0
    print("uso: control | arm R1|R2|R3 | rollback")
    return 1


if __name__ == "__main__":
    sys.exit(main())
