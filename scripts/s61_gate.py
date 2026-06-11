#!/usr/bin/env python3
"""s61_gate.py — GATE del lever L-i + cross-encoder (pre-A/B, sin juez).

Diseño: evals/_s61_lever_design.md §5 (v3 tras dúo ×2 rondas; D1/D2 sobre la
VISTA DEL GENERADOR — filtro RELEVANCE_THRESHOLD=0.4, F1 r1 — y probe-set
CONGELADO en evals/s61_gate_probes.yaml ANTES del paso B [G6 r2]).

Fases (reanudables; cada una persiste su artefacto y se salta lo ya hecho):
  pools     verificación DB read-only (ef_search=120 vía pg_proc.proconfig +
            fingerprint chunks_v2 + SHA RPCs — reusa db_state de s59_gate1, sesión
            readonly) + 39 retrieves L-i frescos (merge actual, chunks_v2, HyDE off)
            → evals/s61_gate_pools.json
  zeroflips verificación 0-flips de la firma ENMENDADA (F1/G4 — pre-datos): la
            clasificación context-idéntico/cambiado de los 39 golds s58↔s59 NO debe
            cambiar entre la firma v4 y la enmendada → evals/s61_zeroflips.yaml
            (referencia s59: evals/_s61_s59_frozen_ref.json, extraída de la rama de
            preservación — git show, read-only)
  rerank    paso B: por gold, CE n=2 réplicas (strict; deben ser idénticas) + CE
            orden-PERMUTADO n=1 (críticos con pool>top_k, seed=61; G3+Y5) + LLM n=3
            (strict; modal por firma ordenada) sobre el MISMO pool congelado de
            `pools`; latencias per-call → evals/s61_gate_reranks.json
  report    D1 (vía-1 overlap min(3,·) / vía-2 anclas congeladas) + D2 + informativas
            (churn vs frozen-s58 con firma enmendada, swap-aislado CE-vs-LLM,
            conteo sim<0.4 en top-5_CE, pool==50, latencias p50/p95, cat014 paridad,
            llm-padded) → evals/s61_gate_report.yaml. Veredicto PRE-REGISTRADO:
            GO / GO-CON-PRESENTACION-A-ALBERTO (==1 unánime fail-both) / NO-GO
            (>=2 unánimes fail-both ∨ D2 ambos perdidos) / PARAR (determinismo u
            orden-insensibilidad del CE caídos con la representación final).

Todo read-only sobre la DB. ~86 llamadas CE + 117 LLM. El A/B NO se lanza desde
aquí (calibración DEC-016b: GO ≠ evidencia de SHIP — solo habilita gastar el A/B).

Uso:  python scripts/s61_gate.py pools|zeroflips|rerank|report|all
"""
from __future__ import annotations

import os

# chunks_v2 + HyDE OFF (= paridad harness/prod) ANTES de importar config/retriever.
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
from s59_gate1 import db_state  # noqa: E402  (manifest read-only: proconfig/SHA RPCs)
from strict_match import anchor_present, norm_ocr  # noqa: E402
from src.config import CHUNKS_IS_V2, CHUNKS_TABLE, RERANK_TOP_K, RETRIEVAL_TOP_K  # noqa: E402
from src.rag.generator import RELEVANCE_THRESHOLD  # noqa: E402
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402

EVALS = ROOT / "evals"
F_POOLS = EVALS / "s61_gate_pools.json"
F_ZEROFLIPS = EVALS / "s61_zeroflips.yaml"
F_RERANKS = EVALS / "s61_gate_reranks.json"
F_REPORT = EVALS / "s61_gate_report.yaml"
F_PROBES = EVALS / "s61_gate_probes.yaml"
F_S58 = EVALS / "s58_frozen_contexts.json"
F_S59_REF = EVALS / "_s61_s59_frozen_ref.json"

EF_EXPECTED = "hnsw.ef_search=120"
CORPUS_EXPECTED = 25090
UNANIMES = ["cat010", "cat014", "cat015", "cat022", "hp015", "hp019"]
MOVERS_D2 = ["hp001", "cat012"]
CRITICOS = UNANIMES + MOVERS_D2
PERM_SEED = 61
N_CE = 2
N_LLM = 3


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def chash(c: dict) -> str:
    # MISMO hash que s60_step0 (consistencia de firmas entre artefactos del ciclo).
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def vista(top5: list[dict]) -> list[dict]:
    """La VISTA DEL GENERADOR (F1): los chunks del top-5 que pasan el filtro 0.4."""
    return [c for c in top5 if (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD]


def firma_v4(top5: list[dict]) -> tuple:
    """Firma PINNED original del v4: ids + orden + content-hash del top-5 (sin filtro)."""
    return tuple((c.get("id"), chash(c)) for c in top5)


def firma_enmendada(top5: list[dict]) -> tuple:
    """Firma enmendada (F1, §7): chunks POST-filtro-0.4, ids + orden + content-hash +
    round(similarity,2). Vista vacía → tupla vacía (G7)."""
    return tuple((c.get("id"), chash(c), round(c.get("similarity") or 0, 2))
                 for c in vista(top5))


def _clean(c: dict) -> dict:
    return {k: v for k, v in c.items() if k != "embedding"}


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_json(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ fase: pools
def phase_pools(args) -> None:
    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"
    data = _load_json(F_POOLS)
    if "meta" not in data:
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        conn.set_session(readonly=True)   # cero escritura — solo manifest
        conn.autocommit = True
        state = db_state(conn.cursor())
        conn.close()
        ef = state["match_chunks_v2"]["proconfig"]
        assert ef == [EF_EXPECTED], (
            f"ef_search en DB = {ef}, esperado [{EF_EXPECTED}] — la ventana DB no está "
            f"como el diseño asume; PARAR y re-decidir (s61 §5 paso A)")
        assert state["chunks_v2_count"] == CORPUS_EXPECTED, (
            f"fingerprint corpus = {state['chunks_v2_count']}, esperado {CORPUS_EXPECTED} "
            f"(freeze-contract violado)")
        data["meta"] = {"at": _now(), "git": _git_commit(), "db_state": state,
                        "retrieve_k": RETRIEVAL_TOP_K, "hyde": os.environ.get("HYDE_ENABLED")}
        _save_json(F_POOLS, data)
        print(f"DB OK: ef={ef} pgvector={state['pgvector']} corpus={state['chunks_v2_count']}")
    golds = gold_store.dev()
    print(f"pools | dev={len(golds)} | ya={sum(1 for g in golds if g['qid'] in data)}")
    for g in sorted(golds, key=lambda x: x["qid"]):
        qid = g["qid"]
        if qid in data:
            continue
        pool = retrieve_chunks(g["question"], top_k=RETRIEVAL_TOP_K)
        data[qid] = {"question": g["question"], "at": _now(),
                     "pool": [_clean(c) for c in pool]}
        _save_json(F_POOLS, data)
        print(f"  {qid}: pool={len(pool)}")
    print(f"pools OK → {F_POOLS.name}")


# -------------------------------------------------------------- fase: zeroflips
def phase_zeroflips(args) -> None:
    s58 = _load_json(F_S58)
    s59 = _load_json(F_S59_REF)
    assert s58 and s59, "faltan frozen s58 o la ref s59 (_s61_s59_frozen_ref.json)"
    flips, sub04 = [], []
    rows = {}
    for qid in sorted(set(s58) & set(s59)):
        a, b = s58[qid]["top5"], s59[qid]["top5"]
        cls_v4 = firma_v4(a) == firma_v4(b)
        cls_enm = firma_enmendada(a) == firma_enmendada(b)
        n_sub = sum(1 for c in a + b if (c.get("similarity") or 0) < RELEVANCE_THRESHOLD)
        if n_sub:
            sub04.append({qid: n_sub})
        if cls_v4 != cls_enm:
            flips.append(qid)
        rows[qid] = {"identico_v4": cls_v4, "identico_enmendada": cls_enm}
    out = {"meta": {"at": _now(), "git": _git_commit(),
                    "regla": "0 reclasificaciones esperadas (G4 r2; el sub-agente r2 lo midió, esto lo deja reproducible)"},
           "n_golds": len(rows), "flips": flips, "chunks_sub_04": sub04, "por_gold": rows}
    F_ZEROFLIPS.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
    print(f"zeroflips: {len(flips)} flips, {len(sub04)} golds con chunks sim<0.4 "
          f"→ {F_ZEROFLIPS.name}")
    assert not flips, f"la enmienda RECLASIFICA {flips} — PARAR (contradice G4/r2)"


# ----------------------------------------------------------------- fase: rerank
def _modal_ordenada(firmas: list[tuple]) -> tuple[tuple, bool]:
    """Modal por firma ordenada; empate total (todas distintas) → INESTABLE,
    se usa la réplica 1 (resolución pre-declarada en el docstring)."""
    cnt = Counter(firmas)
    top, n = cnt.most_common(1)[0]
    return top, n == 1 and len(firmas) > 1


def _rerank_one(qid: str, question: str, pool: list[dict]) -> dict:
    short = len(pool) <= RERANK_TOP_K
    out = {"qid": qid, "n_pool": len(pool), "short_circuit": short, "at": _now()}
    # --- CE n=2 (determinismo con la representación FINAL) ---
    ce_runs, lat_ce = [], []
    for _ in range(N_CE):
        t0 = time.perf_counter()
        r = rerank_chunks_voyage(question, list(pool), top_k=RERANK_TOP_K, strict=True)
        lat_ce.append(round(time.perf_counter() - t0, 3))
        ce_runs.append(r)
    out["ce_lat_s"] = lat_ce
    out["ce_firmas"] = [[list(t) for t in firma_v4(r)] for r in ce_runs]
    out["ce_identicas"] = firma_v4(ce_runs[0]) == firma_v4(ce_runs[1])
    out["ce_top5"] = [_clean(c) for c in ce_runs[0]]
    # --- CE orden-permutado (G3+Y5; solo críticos con pool>top_k) ---
    if qid in CRITICOS and not short:
        perm = list(pool)
        random.Random(PERM_SEED).shuffle(perm)
        t0 = time.perf_counter()
        rp = rerank_chunks_voyage(question, perm, top_k=RERANK_TOP_K, strict=True)
        out["ce_perm_lat_s"] = round(time.perf_counter() - t0, 3)
        out["ce_perm_igual"] = firma_v4(rp) == firma_v4(ce_runs[0])
    # --- LLM n=3 (comparador statu quo; modal) ---
    llm_runs, lat_llm = [], []
    for _ in range(N_LLM):
        t0 = time.perf_counter()
        r = rerank_chunks(question, list(pool), top_k=RERANK_TOP_K, strict=True)
        lat_llm.append(round(time.perf_counter() - t0, 3))
        llm_runs.append(r)
    out["llm_lat_s"] = lat_llm
    firmas = [firma_v4(r) for r in llm_runs]
    modal, inestable = _modal_ordenada(firmas)
    idx = firmas.index(modal)
    out["llm_inestable"] = inestable
    out["llm_padded"] = sorted({c.get("rerank_backend_used") for r in llm_runs for c in r})
    out["llm_top5_modal"] = [_clean(c) for c in llm_runs[idx]]
    return out


def phase_rerank(args) -> None:
    pools = _load_json(F_POOLS)
    assert pools.get("meta"), "corre `pools` primero"
    data = _load_json(F_RERANKS)
    todo = [q for q in sorted(pools) if q != "meta" and q not in data]
    print(f"rerank | golds={len(pools) - 1} | pendientes={len(todo)}")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_rerank_one, q, pools[q]["question"], pools[q]["pool"]): q
                for q in todo}
        for f in as_completed(futs):
            r = f.result()
            data[r["qid"]] = r
            _save_json(F_RERANKS, data)
            print(f"  {r['qid']}: pool={r['n_pool']} ce_identicas={r['ce_identicas']} "
                  f"perm={r.get('ce_perm_igual', '—')} llm_inest={r['llm_inestable']}")
    print(f"rerank OK → {F_RERANKS.name}")


# ----------------------------------------------------------------- fase: report
def _hecho_presente(anclas: list[str], vista_chunks: list[dict]) -> bool:
    return any(all(anchor_present(a, norm_ocr(c.get("content") or "")) for a in anclas)
               for c in vista_chunks)


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    i = max(0, min(len(s) - 1, round(p * (len(s) - 1))))
    return s[i]


def phase_report(args) -> None:
    pools = _load_json(F_POOLS)
    rer = _load_json(F_RERANKS)
    s58 = _load_json(F_S58)
    probes = yaml.safe_load(F_PROBES.read_text(encoding="utf-8"))
    golds = [q for q in sorted(pools) if q != "meta"]
    assert all(q in rer for q in golds), "rerank incompleto"

    paradas = []
    for q in golds:
        if not rer[q]["ce_identicas"]:
            paradas.append(f"{q}: réplicas CE NO idénticas (determinismo caído)")
        if rer[q].get("ce_perm_igual") is False:
            paradas.append(f"{q}: CE sensible al ORDEN con la representación final")

    # --- D1 ---
    d1 = {}
    for q in UNANIMES:
        v_ce = vista(rer[q]["ce_top5"])
        v_58 = vista(s58[q]["top5"])
        need = min(3, len(v_ce), len(v_58))
        ov = len({chash(c) for c in v_ce} & {chash(c) for c in v_58})
        via1 = ov >= need
        hechos = probes["d1_unanimes"].get(q) or {}
        via2 = (all(_hecho_presente(h["anclas"], v_ce) for h in hechos.values())
                if hechos else None)   # cat015: sin vía-2 (admit)
        fail_both = (not via1) and (via2 is not True)
        d1[q] = {"via1_overlap": f"{ov}/{need}", "via1": via1, "via2": via2,
                 "fail_both": fail_both,
                 "detalle_via2": {h: _hecho_presente(spec["anclas"], v_ce)
                                  for h, spec in hechos.items()} or None}
    n_fail = sum(1 for r in d1.values() if r["fail_both"])

    # --- D2 ---
    d2 = {}
    for q in MOVERS_D2:
        v_ce = vista(rer[q]["ce_top5"])
        cond = probes["d2_movers"][q]["condicion"]
        detalle = {h: _hecho_presente(spec["anclas"], v_ce) for h, spec in cond.items()}
        info = {h: _hecho_presente(spec["anclas"], v_ce)
                for h, spec in (probes["d2_movers"][q].get("informativo") or {}).items()}
        d2[q] = {"retenido": all(detalle.values()), "detalle": detalle,
                 "informativo": info or None}
    d2_ambos_perdidos = not any(d2[q]["retenido"] for q in MOVERS_D2)

    # --- informativas ---
    churn = {q: firma_enmendada(rer[q]["ce_top5"]) != firma_enmendada(s58[q]["top5"])
             for q in golds}
    swap = {q: firma_v4(rer[q]["ce_top5"]) != firma_v4(rer[q]["llm_top5_modal"])
            for q in golds}
    sub04 = {q: sum(1 for c in rer[q]["ce_top5"]
                    if (c.get("similarity") or 0) < RELEVANCE_THRESHOLD)
             for q in golds}
    lat_ce = [x for q in golds for x in rer[q]["ce_lat_s"]]
    lat_llm = [x for q in golds for x in rer[q]["llm_lat_s"]]

    # --- veredicto pre-registrado ---
    if paradas:
        veredicto = "PARAR"
    elif n_fail >= 2 or d2_ambos_perdidos:
        veredicto = "NO-GO"
    elif n_fail == 1:
        veredicto = "GO-CON-PRESENTACION-A-ALBERTO"
    else:
        veredicto = "GO"

    out = {
        "meta": {"at": _now(), "git": _git_commit(), "diseno": "_s61_lever_design.md §5 (v3)",
                 "probes": "s61_gate_probes.yaml (congeladas pre-paso-B)",
                 "db_state": pools["meta"]["db_state"]},
        "veredicto": veredicto,
        "paradas": paradas or None,
        "d1": {"unanimes": d1, "n_fail_both": n_fail,
               "regla": ">=2 NO-GO; ==1 presentación a Alberto pre-A/B; 0 GO"},
        "d2": {"movers": d2, "ambos_perdidos": d2_ambos_perdidos,
               "regla": "ambos perdidos → NO-GO"},
        "informativas": {
            "churn_vs_s58_firma_enmendada": {"n_cambiados": sum(churn.values()),
                                             "n_total": len(golds),
                                             "cambiados": sorted(q for q, v in churn.items() if v)},
            "swap_aislado_ce_vs_llm_modal": {"n_distintos": sum(swap.values()),
                                             "distintos": sorted(q for q, v in swap.items() if v)},
            "top5_ce_chunks_sim_sub04": {q: n for q, n in sub04.items() if n},
            "pool_a_50_corte_activo": sorted(q for q in golds
                                             if rer[q]["n_pool"] >= RETRIEVAL_TOP_K),
            "llm_inestables_1_1_1": sorted(q for q in golds if rer[q]["llm_inestable"]),
            "llm_padded_golds": sorted(q for q in golds
                                       if any("padded" in (t or "")
                                              for t in rer[q]["llm_padded"])),
            "cat014_paridad_short_circuit": rer["cat014"]["short_circuit"],
            "latencia_rerank_s": {
                "ce": {"p50": _pct(lat_ce, .5), "p95": _pct(lat_ce, .95), "n": len(lat_ce)},
                "llm": {"p50": _pct(lat_llm, .5), "p95": _pct(lat_llm, .95), "n": len(lat_llm)},
            },
        },
    }
    F_REPORT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110),
                        encoding="utf-8")
    print(yaml.safe_dump({"veredicto": veredicto, "d1_fail_both": n_fail,
                          "d2": {q: d2[q]["retenido"] for q in MOVERS_D2},
                          "churn": out["informativas"]["churn_vs_s58_firma_enmendada"]["n_cambiados"],
                          "lat": out["informativas"]["latencia_rerank_s"]},
                         allow_unicode=True, sort_keys=False))
    print(f"report OK → {F_REPORT.name}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=["pools", "zeroflips", "rerank", "report", "all"])
    args = ap.parse_args()
    fases = (["pools", "zeroflips", "rerank", "report"] if args.fase == "all"
             else [args.fase])
    for f in fases:
        print(f"=== {f} ===")
        globals()[f"phase_{f}"](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
