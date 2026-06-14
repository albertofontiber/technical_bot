#!/usr/bin/env python3
"""s68 — GATE-0 del lever MERGE+L-i′ (diseño _s68_merge_design.md v6.1 §3; sin juez).

Fases (reanudables):
  paridad    Precondición A (F8, $0): 39 retrieves bajo `stamps`+EMBED_CACHE → firma
             de pool (ids+round(sim,4) en orden) ≡ pool50_light de s67base congelado.
             Cualquier diff → STOP instrumento (el refactor no es bit-idéntico).
  pools      39 retrieves por variante (quota|cosine) con TRAZA por etapa (wrappers
             sobre _merge_channels/lifecycle/model-filter/diversify — el código de
             producción NO se toca) → evals/s68_gate0_pools.json
  poollevel  m1+traza (los 10 hechos-expulsados: ¿entran al pool final? ¿dónde mueren?)
             · m2 sanity (hp001/hp011 NO esperados) · m3 composición por _channel ·
             m5 tamaño/Δ — determinista, $0 → evals/s68_gate0_poollevel.yaml
  rerank     top-5 LLM n=3 modal por variante SOLO en los golds de m6 (los 5 con
             hechos-expulsados) + los 10 PASS-control de m7 (~90 llamadas ≈ $4)
             → evals/s68_gate0_reranks.json
  veredicto  m6 (conversión al top-5) · m4 (n_sub04 + tamaño de vista en top-5) ·
             m7 con BANDA DE DADO (las 3 vistas LLM del gate s67, firma ORDENADA de
             content-hash; ≤1 PASS-control fuera-de-banda, ese único overlap ≥4/5;
             válvula pre-registrada para el patrón 2×[≥4/5]) → selección o NO-GO
             → evals/s68_gate0_report.yaml

Pre-registrado ANTES de correr (v6.1 + este docstring); read-only sobre la DB.
Uso: python scripts/s68_gate0.py paridad|pools|poollevel|rerank|veredicto [--variant quota|cosine]
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", "evals/s67_embed_cache.json")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
import src.rag.retriever as rt  # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, RETRIEVAL_TOP_K, RERANK_TOP_K  # noqa: E402
from src.rag.generator import RELEVANCE_THRESHOLD  # noqa: E402
from src.rag.reranker import rerank  # noqa: E402
from strict_match import norm_ocr, anchor_present, chunk_has_quote_strict  # noqa: E402

EVALS = ROOT / "evals"
F_BASE_CTX = EVALS / "s67base_frozen_contexts.json"
F_AUDIT = EVALS / "s68_audit_canal.yaml"
F_GATE67 = EVALS / "s67_gate_reranks.json"
F_POOLS = EVALS / "s68_gate0_pools.json"
F_POOLLEVEL = EVALS / "s68_gate0_poollevel.yaml"
F_RERANKS = EVALS / "s68_gate0_reranks.json"
F_REPORT = EVALS / "s68_gate0_report.yaml"

PASS_CONTROL = ["cat005", "cat010", "cat014", "cat015", "cat018", "cat022",
                "cat023", "hp015", "hp019", "hp020"]      # s67base_gate_report (ancla m7)
GOLDS_M6 = ["cat001", "cat017", "hp002", "hp008", "hp018"]  # hechos-expulsados/EN-POOL del audit
SANITY_M2 = ["hp001", "hp011"]                              # rank 54/65 — NO esperados (F7)
VARIANTS = ["quota", "cosine"]
N_RERANK = 3
_HEADERS = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")


def chash(c: dict) -> str:
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def firma_pool(pool: list[dict]) -> list:
    return [[c.get("id"), round(c.get("similarity") or 0, 4)] for c in pool]


def firma_ordenada(top5: list[dict]) -> tuple:
    """Firma ORDENADA de content-hash (m7/m6 — la del v4-s60 r2)."""
    return tuple(chash(c) for c in top5)


def _light(c: dict) -> dict:
    return {"id": c.get("id"), "source_file": c.get("source_file"),
            "page_number": c.get("page_number"), "similarity": c.get("similarity"),
            "channel": c.get("_channel"), "content": c.get("content")}


# ------------------------------------------------- retrieve con traza por etapa
def retrieve_con_traza(query: str, strategy: str) -> tuple[list[dict], dict]:
    """Corre el retrieve REAL bajo `strategy` capturando la salida de cada etapa con
    wrappers (monkeypatch runtime) — el pipeline de producción no se modifica."""
    etapas: dict[str, list] = {}
    orig = {"merge": rt._merge_channels, "life": rt._filter_by_document_status,
            "model": rt._filter_to_query_models,
            "div_src": rt._diversify_by_source_file,
            "div_mfr": rt._diversify_by_manufacturer}

    def w_merge(*a, **k):
        out = orig["merge"](*a, **k)
        etapas["merge"] = [c.get("id") for c in out]
        return out

    def w_life(chunks):
        out = orig["life"](chunks)
        etapas["lifecycle"] = [c.get("id") for c in out]
        return out

    def w_model(chunks, models):
        out = orig["model"](chunks, models)
        etapas["model_filter"] = [c.get("id") for c in out]
        return out

    def w_div_src(chunks, *a, **k):
        out = orig["div_src"](chunks, *a, **k)
        etapas["diversify"] = [c.get("id") for c in out]
        return out

    def w_div_mfr(chunks, *a, **k):
        out = orig["div_mfr"](chunks, *a, **k)
        etapas["diversify"] = [c.get("id") for c in out]
        return out

    rt.MERGE_STRATEGY = strategy
    rt._merge_channels = w_merge
    rt._filter_by_document_status = w_life
    rt._filter_to_query_models = w_model
    rt._diversify_by_source_file = w_div_src
    rt._diversify_by_manufacturer = w_div_mfr
    try:
        pool = rt.retrieve_chunks(query, top_k=RETRIEVAL_TOP_K)
    finally:
        rt.MERGE_STRATEGY = "stamps"
        rt._merge_channels = orig["merge"]
        rt._filter_by_document_status = orig["life"]
        rt._filter_to_query_models = orig["model"]
        rt._diversify_by_source_file = orig["div_src"]
        rt._diversify_by_manufacturer = orig["div_mfr"]
    etapas["final"] = [c.get("id") for c in pool]
    return pool, etapas


# ------------------------------------------------------------- winners (audit)
def probe_kind(probe):
    if isinstance(probe, list):
        return "anchors", [str(p) for p in probe]
    s = str(probe)
    return "quote", (s[1:] if s.startswith("~") else s)


def chunk_has(content, kind, probe) -> bool:
    if kind == "anchors":
        nc = norm_ocr(content or "")
        return all(anchor_present(a, nc) for a in probe)
    return chunk_has_quote_strict(content or "", str(probe))


def fetch_doc_chunks(sources: list[str]) -> list[dict]:
    out, seen = [], set()
    for s in sources[:8]:
        try:
            with httpx.Client(timeout=30.0) as c:
                r = c.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_HEADERS,
                          params={"select": "id,content,source_file",
                                  "source_file": f"ilike.*{s[:48]}*", "limit": "600"})
            for row in r.json():
                if row.get("id") not in seen:
                    seen.add(row.get("id"))
                    out.append(row)
        except Exception:
            continue
    return out


def hechos_expulsados() -> list[dict]:
    """Los 10 hechos del audit (+los 2 EN-POOL de hp018/cat001) con sus winner-ids."""
    audit = yaml.safe_load(F_AUDIT.read_text(encoding="utf-8"))
    out = []
    for g in audit["golds"]:
        if g["qid"] not in GOLDS_M6 + SANITY_M2:
            continue
        suff_facts = []
        for h in g["hechos_fuertes"]:
            if h["bucket"].startswith(("RANK", "EN-POOL")):
                suff_facts.append(h)
        if suff_facts:
            out.append({"qid": g["qid"], "hechos": suff_facts})
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=["paridad", "pools", "poollevel", "rerank", "veredicto"])
    args = ap.parse_args()
    golds = {g["qid"]: g for g in gold_store.dev()}

    if args.fase == "paridad":
        base = _load(F_BASE_CTX)
        fallos = []
        for qid in sorted(base):
            pool, _ = retrieve_con_traza(base[qid]["question"], "stamps")
            f_new = firma_pool([{"id": c.get("id"), "similarity": c.get("similarity")}
                                for c in pool])
            f_old = firma_pool(base[qid]["pool50_light"])
            if f_new != f_old:
                fallos.append(qid)
                print(f"  {qid}: DIFF (nuevo {len(f_new)} vs congelado {len(f_old)})")
            else:
                print(f"  {qid}: OK ({len(f_new)})")
        if fallos:
            print(f"PARIDAD FALLA en {len(fallos)}: {fallos} — STOP (F8)")
            return 1
        print("PARIDAD OK: stamps+cache ≡ s67base congelado, 39/39")
        return 0

    if args.fase == "pools":
        data = _load(F_POOLS)
        for variant in VARIANTS:
            data.setdefault(variant, {})
            for qid in sorted(golds):
                if qid in data[variant]:
                    continue
                pool, etapas = retrieve_con_traza(golds[qid]["question"], variant)
                data[variant][qid] = {"pool": [_light(c) for c in pool],
                                      "etapas": etapas, "at": _now()}
                _save(F_POOLS, data)
                print(f"  {variant}/{qid}: pool={len(pool)}")
        data["meta"] = {"at": _now(), "git": _git(),
                        "embed_cache": os.environ.get("EMBED_CACHE_PATH"),
                        "k": RETRIEVAL_TOP_K}
        _save(F_POOLS, data)
        print(f"pools OK → {F_POOLS.name}")
        return 0

    if args.fase == "poollevel":
        pools = _load(F_POOLS)
        base = _load(F_BASE_CTX)
        targets = hechos_expulsados()
        out = {"m1_traza": {}, "m2_sanity": {}, "m3_composicion": {}, "m5_tamano": {}}
        for variant in VARIANTS:
            m1 = {}
            for t in targets:
                qid = t["qid"]
                entry = pools[variant][qid]
                pool_ids = {c["id"] for c in entry["pool"]}
                suff = (yaml.safe_load(F_AUDIT.read_text(encoding="utf-8")))
                for h in t["hechos"]:
                    kind, probe = probe_kind(h.get("probe") or h.get("valor"))
                    # winners recomputados del doc objetivo (mismo método del audit)
                    docs = [h["winner"]["source"]] if h.get("winner") else []
                    wchunks = fetch_doc_chunks(docs)
                    wids = [c["id"] for c in wchunks
                            if chunk_has(c.get("content"), kind, probe)]
                    en_pool = bool(set(wids) & pool_ids)
                    etapa_muerte = None
                    if not en_pool:
                        for etapa in ("merge", "lifecycle", "model_filter",
                                      "diversify", "final"):
                            ids = set(entry["etapas"].get(etapa) or [])
                            if not set(wids) & ids:
                                etapa_muerte = etapa
                                break
                    m1.setdefault(qid, []).append(
                        {"valor": h["valor"], "en_pool": en_pool,
                         "muere_en": etapa_muerte, "n_winners": len(wids)})
            out["m1_traza"][variant] = m1
            out["m2_sanity"][variant] = {
                q: bool({c["id"] for c in pools[variant][q]["pool"]}
                        & {h.get("winner", {}).get("id")
                           for h in next((t["hechos"] for t in targets if t["qid"] == q), [])})
                for q in SANITY_M2 if q in pools[variant]}
            out["m3_composicion"][variant] = dict(Counter(
                c.get("channel") or "?" for q in pools[variant]
                if q != "meta" for c in pools[variant][q]["pool"]))
            out["m5_tamano"][variant] = {
                "mediana": sorted(len(pools[variant][q]["pool"])
                                  for q in pools[variant] if q != "meta")[19],
                "delta_vs_control": sorted(
                    len(pools[variant][q]["pool"]) - len(base[q]["pool50_light"])
                    for q in pools[variant] if q != "meta")[19]}
        F_POOLLEVEL.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                               encoding="utf-8")
        for v in VARIANTS:
            caps = sum(1 for q, hh in out["m1_traza"][v].items()
                       for h in hh if h["en_pool"])
            tot = sum(len(hh) for hh in out["m1_traza"][v].values())
            print(f"  {v}: m1 captura-pool {caps}/{tot} | m3 {out['m3_composicion'][v]} "
                  f"| m5 {out['m5_tamano'][v]}")
        print(f"poollevel OK → {F_POOLLEVEL.name}")
        return 0

    if args.fase == "rerank":
        pools = _load(F_POOLS)
        data = _load(F_RERANKS)
        scope = GOLDS_M6 + PASS_CONTROL
        for variant in VARIANTS:
            data.setdefault(variant, {})
            tasks = [q for q in scope if q not in data[variant]]
            for qid in tasks:
                pool = pools[variant][qid]["pool"]
                if len(pool) <= RERANK_TOP_K:
                    data[variant][qid] = {"short_circuit": True,
                                          "tiradas": [[chash(c) for c in pool]] * N_RERANK,
                                          "top5_all": [pool] * 1}
                    _save(F_RERANKS, data)
                    print(f"  {variant}/{qid}: short-circuit")
                    continue
                tiradas, vistas = [], []
                for _ in range(N_RERANK):
                    top5 = rerank(golds[qid]["question"], list(pool),
                                  top_k=RERANK_TOP_K, strict=True)
                    tiradas.append([chash(c) for c in top5])
                    vistas.append([_light(c) for c in top5])
                data[variant][qid] = {"short_circuit": False, "tiradas": tiradas,
                                      "top5_all": vistas, "at": _now()}
                _save(F_RERANKS, data)
                print(f"  {variant}/{qid}: n={N_RERANK} "
                      f"{'estable' if len({tuple(t) for t in tiradas}) == 1 else 'variable'}")
        print(f"rerank OK → {F_RERANKS.name}")
        return 0

    # ------------------------------------------------------------- veredicto
    rer = _load(F_RERANKS)
    pools = _load(F_POOLS)
    gate67 = _load(F_GATE67)
    poollevel = yaml.safe_load(F_POOLLEVEL.read_text(encoding="utf-8"))
    report = {"meta": {"at": _now(), "git": _git(),
                       "diseno": "_s68_merge_design.md v6.1 (post-dúo r1 13+6/19, 0 FP)"},
              "variantes": {}}
    for variant in VARIANTS:
        # m6: conversión — hechos-expulsados cuyo winner llega al top-5 MODAL
        m6 = {}
        for t in hechos_expulsados():
            qid = t["qid"]
            if qid not in rer.get(variant, {}):
                continue
            tir = rer[variant][qid]["tiradas"]
            modal_hashes = set(Counter(tuple(t_) for t_ in tir).most_common(1)[0][0])
            vista_chunks = [c for v in rer[variant][qid]["top5_all"] for c in v]
            for h in t["hechos"]:
                kind, probe = probe_kind(h.get("probe") or h.get("valor"))
                en_top5 = any(chunk_has(c.get("content"), kind, probe)
                              and chash(c) in modal_hashes for c in vista_chunks)
                m6.setdefault(qid, []).append({"valor": h["valor"], "en_top5_modal": en_top5})
        # m4: vista post-filtro-0.4 del top-5 modal
        m4 = {}
        for qid in rer.get(variant, {}):
            vistas = rer[variant][qid]["top5_all"]
            if not vistas:
                continue
            v0 = vistas[0]
            n_sub = sum(1 for c in v0 if (c.get("similarity") or 0) < RELEVANCE_THRESHOLD)
            m4[qid] = {"n_sub04": n_sub, "vista_len": len(v0) - n_sub}
        # m7: banda de dado
        m7 = {}
        for qid in PASS_CONTROL:
            if qid not in rer.get(variant, {}):
                continue
            tir = rer[variant][qid]["tiradas"]
            modal = Counter(tuple(t_) for t_ in tir).most_common(1)[0][0]
            banda = {tuple(chash(c) for c in v)
                     for v in gate67[qid]["llm_top5_all"]} if qid in gate67 else set()
            if gate67.get(qid, {}).get("short_circuit"):
                banda.add(tuple(chash(c) for c in gate67[qid]["ce_top5"]))
            fuera = modal not in banda
            best_overlap = max((len(set(modal) & set(b)) for b in banda), default=0)
            m7[qid] = {"fuera_de_banda": fuera, "overlap_mejor_banda": best_overlap}
        fuera = [q for q, r in m7.items() if r["fuera_de_banda"]]
        patron_valvula = (len(fuera) == 2
                          and all(m7[q]["overlap_mejor_banda"] >= 4 for q in fuera))
        m7_pass = len(fuera) <= 1 and all(m7[q]["overlap_mejor_banda"] >= 4 for q in fuera)
        capt = sum(1 for hh in m6.values() for h in hh if h["en_top5_modal"])
        tot = sum(len(hh) for hh in m6.values())
        report["variantes"][variant] = {
            "m1": poollevel["m1_traza"][variant], "m3": poollevel["m3_composicion"][variant],
            "m4": m4, "m5": poollevel["m5_tamano"][variant],
            "m6_conversion": m6, "m6_total": f"{capt}/{tot}",
            "m7": m7, "m7_fuera": fuera, "m7_pass": m7_pass,
            "m7_patron_valvula": patron_valvula}
        print(f"{variant}: m6 {capt}/{tot} | m7 fuera={fuera} pass={m7_pass} "
              f"valvula={patron_valvula} | m4 sub04 medio="
              f"{round(sum(x['n_sub04'] for x in m4.values()) / max(1, len(m4)), 2)}")
    F_REPORT.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False,
                                       width=110), encoding="utf-8")
    print(f"veredicto-data OK → {F_REPORT.name} (la SELECCIÓN se aplica con la letra v6.1 §3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
