#!/usr/bin/env python3
"""s66_gate.py — RE-GATE del lever CE-puro (swap del reranker, pre-A/B, sin juez).

Diseño: evals/_s66_ce_regate_design.md (v2 tras dúo r1 13/13 confirmados 0 FP).
Scope confirmado por Alberto: CE-PURO (sin L-i) — pools del código de MAIN intacto
(filtro de series s63 + lifecycle s64 vigentes); el gate es la comparación
swap-aislado CE-vs-LLM-actual sobre el MISMO pool congelado (DEC-043c).
Probe-set CONGELADO ANTES de cualquier retrieve (X1): evals/s66_gate_probes.yaml.

Fases (reanudables; cada una persiste su artefacto y se salta lo ya hecho):
  calibracion  (F8, $0, informativa) overlap vía-1 CE-vs-LLM-modal sobre el artefacto
               EXISTENTE evals/s61_gate_reranks.json → tasa esperada de paso con la
               referencia nueva. Declarada imperfecta (pools s61 = L-i@ef120 ≠ s66).
               → evals/s66_gate_calibracion.yaml
  pools        paso A: verificación DB read-only (ef_search=120 vía pg_proc.proconfig +
               corpus 25.090 + SHA RPCs — db_state de s59_gate1, sesión readonly) +
               corpus_fingerprint() con dimensión lifecycle (bvg) + registry_fingerprint()
               + series_enabled + 39 retrieves FRESCOS con el código de main
               → evals/s66_gate_pools.json
  precheck     pre-paso-B (F1/F2/F3, $0): presencia de cada ancla del probe-set en el
               pool-50 fresco (matcher local). Resuelve la branch hp001 (CONDICION si
               candado Y 2222 en pool / INFORMATIVA si no) y los STOPs ANTES de pagar
               el rerank: STOP-E3 (>=2 unánimes con >=1 hecho de vía-2 fuera de pool) ·
               STOP-D2 (hecho de condición de cat012/cat018 fuera de pool)
               → evals/s66_gate_precheck.yaml
  rerank       paso B: por gold, CE n=2 réplicas (strict; deben ser idénticas) + CE
               orden-PERMUTADO n=1 (críticos del probe-set con pool>top_k, seed=66) +
               LLM n=3 (strict; modal + VOTOS por firma ordenada; las 3 vistas se
               persisten para la regla de unión de cat015) sobre el MISMO pool congelado
               → evals/s66_gate_reranks.json
  report       D1 (vía-1 overlap min(3,·) contra LLM-modal ACTUAL; 1/1/1 → vía-2 manda;
               cat015 modal>=2/3 o unión o ESCALADA / vía-2 anclas con paridad de pool) +
               D2′ (pérdida ATRIBUIBLE := en-pool ∧ en-vista-LLM ∧ ¬en-vista-CE; >=1 gold
               → NO-GO [X3]) + informativas → evals/s66_gate_report.yaml.
               Veredicto PRE-REGISTRADO (diseño §5): PARAR / NO-GO / GO-CON-PRESENTACION-
               A-ALBERTO (==1 unánime fail-both ∨ cat015 escalado ∨ indecidibles) / GO.

Todo read-only sobre la DB. ~78 llamadas CE + ~117 LLM ≈ $5-6 (X4). El A/B NO se lanza
desde aquí (DEC-016b: GO ≠ evidencia de SHIP — solo habilita la decisión de Alberto).

Uso:  python scripts/s66_gate.py calibracion|pools|precheck|rerank|report|all
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
from bvg_kmajority import corpus_fingerprint  # noqa: E402  (con dimensión lifecycle s64)
from s59_gate1 import db_state  # noqa: E402  (manifest read-only: proconfig/SHA RPCs)
from strict_match import anchor_present, norm_ocr  # noqa: E402
from src.config import CHUNKS_IS_V2, CHUNKS_TABLE, RERANK_TOP_K, RETRIEVAL_TOP_K  # noqa: E402
from src.rag.generator import RELEVANCE_THRESHOLD  # noqa: E402
from src.rag.reranker import rerank_chunks, rerank_chunks_voyage  # noqa: E402
from src.rag.retriever import retrieve_chunks  # noqa: E402
from src.rag.series_registry import registry_fingerprint, series_enabled  # noqa: E402

EVALS = ROOT / "evals"
F_PROBES = EVALS / "s66_gate_probes.yaml"
F_CALIB = EVALS / "s66_gate_calibracion.yaml"
F_POOLS = EVALS / "s66_gate_pools.json"
F_PRECHECK = EVALS / "s66_gate_precheck.yaml"
F_RERANKS = EVALS / "s66_gate_reranks.json"
F_REPORT = EVALS / "s66_gate_report.yaml"
F_S61_RERANKS = EVALS / "s61_gate_reranks.json"

EF_EXPECTED = "hnsw.ef_search=120"
CORPUS_EXPECTED = 25090
UNANIMES = ["cat010", "cat014", "cat015", "cat022", "hp015", "hp019"]
SHIPS_D2 = ["cat012", "cat018"]   # hp001 entra solo si su branch resuelve CONDICION
PERM_SEED = 66
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
    # MISMO hash que s60_step0/s61_gate (consistencia de firmas entre artefactos).
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def vista(top5: list[dict]) -> list[dict]:
    """La VISTA DEL GENERADOR (F1-s61): chunks del top-5 que pasan el filtro 0.4."""
    return [c for c in top5 if (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD]


def firma_v4(top5: list[dict]) -> tuple:
    """Firma ids + orden + content-hash del top-5 (sin filtro) — comparación de backends."""
    return tuple((c.get("id"), chash(c)) for c in top5)


def _clean(c: dict) -> dict:
    return {k: v for k, v in c.items() if k != "embedding"}


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_json(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def _probes() -> dict:
    return yaml.safe_load(F_PROBES.read_text(encoding="utf-8"))


def _hecho_presente(anclas: list[str], chunks: list[dict]) -> bool:
    """∃ chunk cuyo content contiene TODAS las anclas (AND) — vista o pool."""
    return any(all(anchor_present(a, norm_ocr(c.get("content") or "")) for a in anclas)
               for c in chunks)


# ------------------------------------------------------------- fase: calibracion
def phase_calibracion(args) -> None:
    """F8 ($0, informativa): tasa de paso vía-1 con la referencia nueva (LLM-modal),
    sobre el artefacto s61 (CE y LLM-modal sobre el MISMO pool L-i@ef120)."""
    rer = _load_json(F_S61_RERANKS)
    assert rer, f"falta {F_S61_RERANKS.name} (artefacto s61 en main)"
    rows = {}
    for q in sorted(rer):
        v_ce = vista(rer[q]["ce_top5"])
        v_ref = vista(rer[q]["llm_top5_modal"])
        need = min(3, len(v_ce), len(v_ref))
        ov = len({chash(c) for c in v_ce} & {chash(c) for c in v_ref})
        rows[q] = {"overlap": f"{ov}/{need}", "via1": ov >= need,
                   "llm_inestable": rer[q].get("llm_inestable", False)}
    n_pass = sum(1 for r in rows.values() if r["via1"])
    out = {"meta": {"at": _now(), "git": _git_commit(),
                    "fuente": F_S61_RERANKS.name,
                    "caveat": ("INFORMATIVA (F8): pools s61 = L-i@ef120 ≠ pools s66 "
                               "(main actual) — calibración imperfecta declarada; "
                               "no es condición del gate")},
           "n_golds": len(rows), "via1_pass": n_pass,
           "via1_pass_unanimes": {q: rows[q] for q in UNANIMES if q in rows},
           "por_gold": rows}
    F_CALIB.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
    print(f"calibracion: vía-1 pasa {n_pass}/{len(rows)} "
          f"(unánimes: {sum(1 for q in UNANIMES if rows.get(q, {}).get('via1'))}/6) "
          f"→ {F_CALIB.name}")


# ------------------------------------------------------------------ fase: pools
def phase_pools(args) -> None:
    assert CHUNKS_IS_V2, f"CHUNKS_TABLE debe ser chunks_v2, es {CHUNKS_TABLE}"
    assert series_enabled(), "SERIES_REGISTRY_ENABLED apagado — el gate exige paridad con prod (s63)"
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
            f"como el diseño asume; PARAR y re-decidir (diseño §3.1)")
        assert state["chunks_v2_count"] == CORPUS_EXPECTED, (
            f"corpus = {state['chunks_v2_count']}, esperado {CORPUS_EXPECTED}")
        cfp = corpus_fingerprint()
        data["meta"] = {"at": _now(), "git": _git_commit(), "db_state": state,
                        "corpus_fingerprint": cfp,
                        "registry_fingerprint": registry_fingerprint(),
                        "series_enabled": series_enabled(),
                        "retrieve_k": RETRIEVAL_TOP_K,
                        "hyde": os.environ.get("HYDE_ENABLED"),
                        "nota": ("pools del código de MAIN (CE-puro, sin L-i) — la "
                                 "ventana del GO (X2) compara estos fingerprints")}
        _save_json(F_POOLS, data)
        print(f"DB OK: ef={ef} pgvector={state['pgvector']} corpus={state['chunks_v2_count']} "
              f"| lifecycle={cfp.get('documents_status')} excl={cfp.get('chunks_excluded_by_lifecycle')}")
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


# --------------------------------------------------------------- fase: precheck
def phase_precheck(args) -> None:
    """Pre-paso-B (F1/F2/F3, $0): anclas vs pool-50 fresco. Resuelve branch hp001 y
    STOPs ANTES de pagar el rerank."""
    pools = _load_json(F_POOLS)
    assert pools.get("meta"), "corre `pools` primero"
    probes = _probes()

    d1_pool, unanimes_con_fuera = {}, []
    for q in UNANIMES:
        hechos = probes["d1_unanimes"].get(q) or {}
        if not hechos:          # cat015: sin vía-2 → no participa en E3
            d1_pool[q] = None
            continue
        det = {h: _hecho_presente(spec["anclas"], pools[q]["pool"])
               for h, spec in hechos.items()}
        d1_pool[q] = det
        if not all(det.values()):
            unanimes_con_fuera.append(q)

    d2_pool, d2_stops = {}, []
    for q in SHIPS_D2:
        cond = probes["d2_movers"][q]["condicion"]
        det = {h: _hecho_presente(spec["anclas"], pools[q]["pool"])
               for h, spec in cond.items()}
        d2_pool[q] = det
        if not all(det.values()):
            d2_stops.append(f"{q}: hecho(s) de condición de un SHIP vigente s63 FUERA "
                            f"del pool fresco: {[h for h, v in det.items() if not v]}")

    hp_cond = probes["d2_movers"]["hp001"]["condicion"]
    hp_det = {h: _hecho_presente(spec["anclas"], pools["hp001"]["pool"])
              for h, spec in hp_cond.items()}
    hp_branch = "CONDICION" if all(hp_det.values()) else "INFORMATIVA"

    stops = []
    if len(unanimes_con_fuera) >= 2:
        stops.append(f"STOP-E3: {len(unanimes_con_fuera)} unánimes con hechos de vía-2 "
                     f"fuera del pool fresco ({unanimes_con_fuera}) — instrumento/corpus")
    stops.extend(f"STOP-D2: {s}" for s in d2_stops)

    out = {"meta": {"at": _now(), "git": _git_commit(),
                    "regla": "diseño v2 §3.3b/§3.4/§5 — branch hp001 + STOPs pre-paso-B"},
           "stops": stops or None,
           "branch_hp001": hp_branch,
           "hp001_detalle_pool": hp_det,
           "d1_pool": d1_pool,
           "unanimes_con_ancla_fuera": unanimes_con_fuera,
           "d2_pool": d2_pool}
    F_PRECHECK.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                          encoding="utf-8")
    print(f"precheck: hp001={hp_branch} | unánimes-con-fuera={unanimes_con_fuera} | "
          f"stops={len(stops)} → {F_PRECHECK.name}")
    assert not stops, "STOP pre-registrado disparado — NO pagar el paso B:\n" + "\n".join(stops)


# ----------------------------------------------------------------- fase: rerank
def _rerank_one(qid: str, question: str, pool: list[dict], criticos: list[str]) -> dict:
    short = len(pool) <= RERANK_TOP_K
    out = {"qid": qid, "n_pool": len(pool), "short_circuit": short, "at": _now()}
    # --- CE n=2 (determinismo con la representación final) ---
    ce_runs, lat_ce = [], []
    for _ in range(N_CE):
        t0 = time.perf_counter()
        r = rerank_chunks_voyage(question, list(pool), top_k=RERANK_TOP_K, strict=True)
        lat_ce.append(round(time.perf_counter() - t0, 3))
        ce_runs.append(r)
    out["ce_lat_s"] = lat_ce
    out["ce_identicas"] = firma_v4(ce_runs[0]) == firma_v4(ce_runs[1])
    out["ce_top5"] = [_clean(c) for c in ce_runs[0]]
    # --- CE orden-permutado (G3; solo críticos con pool>top_k) ---
    if qid in criticos and not short:
        perm = list(pool)
        random.Random(PERM_SEED).shuffle(perm)
        t0 = time.perf_counter()
        rp = rerank_chunks_voyage(question, perm, top_k=RERANK_TOP_K, strict=True)
        out["ce_perm_lat_s"] = round(time.perf_counter() - t0, 3)
        out["ce_perm_igual"] = firma_v4(rp) == firma_v4(ce_runs[0])
    # --- LLM n=3 (la REFERENCIA actual; modal + votos; 3 vistas persistidas) ---
    llm_runs, lat_llm = [], []
    for _ in range(N_LLM):
        t0 = time.perf_counter()
        r = rerank_chunks(question, list(pool), top_k=RERANK_TOP_K, strict=True)
        lat_llm.append(round(time.perf_counter() - t0, 3))
        llm_runs.append(r)
    out["llm_lat_s"] = lat_llm
    firmas = [firma_v4(r) for r in llm_runs]
    cnt = Counter(firmas)
    modal, n_modal = cnt.most_common(1)[0]
    out["llm_votos"] = sorted(cnt.values(), reverse=True)   # [3] | [2,1] | [1,1,1]
    out["llm_inestable"] = n_modal == 1 and len(firmas) > 1
    out["llm_padded"] = sorted({c.get("rerank_backend_used") for r in llm_runs for c in r
                                if c.get("rerank_backend_used")})
    out["llm_top5_modal"] = [_clean(c) for c in llm_runs[firmas.index(modal)]]
    out["llm_top5_all"] = [[_clean(c) for c in r] for r in llm_runs]
    return out


def phase_rerank(args) -> None:
    pools = _load_json(F_POOLS)
    assert pools.get("meta"), "corre `pools` primero"
    pre = yaml.safe_load(F_PRECHECK.read_text(encoding="utf-8")) if F_PRECHECK.exists() else None
    assert pre and not pre.get("stops"), "corre `precheck` primero (sin STOPs) — no pagar el paso B"
    criticos = _probes()["meta"]["criticos_permutado"]
    data = _load_json(F_RERANKS)
    todo = [q for q in sorted(pools) if q != "meta" and q not in data]
    print(f"rerank | golds={len(pools) - 1} | pendientes={len(todo)}")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_rerank_one, q, pools[q]["question"], pools[q]["pool"], criticos): q
                for q in todo}
        for f in as_completed(futs):
            r = f.result()
            data[r["qid"]] = r
            _save_json(F_RERANKS, data)
            print(f"  {r['qid']}: pool={r['n_pool']} ce_identicas={r['ce_identicas']} "
                  f"perm={r.get('ce_perm_igual', '—')} votos={r['llm_votos']}")
    print(f"rerank OK → {F_RERANKS.name}")


# ----------------------------------------------------------------- fase: report
def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    i = max(0, min(len(s) - 1, round(p * (len(s) - 1))))
    return s[i]


def phase_report(args) -> None:
    pools = _load_json(F_POOLS)
    rer = _load_json(F_RERANKS)
    probes = _probes()
    pre = yaml.safe_load(F_PRECHECK.read_text(encoding="utf-8"))
    golds = [q for q in sorted(pools) if q != "meta"]
    assert all(q in rer for q in golds), "rerank incompleto"
    assert not pre.get("stops"), "precheck con STOP — este report no debe existir"

    paradas = []
    for q in golds:
        if not rer[q]["ce_identicas"]:
            paradas.append(f"{q}: réplicas CE NO idénticas (determinismo caído)")
        if rer[q].get("ce_perm_igual") is False:
            paradas.append(f"{q}: CE sensible al ORDEN con la representación final")

    # --- D1 (vía-1 contra LLM-modal ACTUAL; paridad de pool en vía-2; cat015 especial) ---
    d1, indecidibles = {}, []
    cat015_escalado = False
    for q in UNANIMES:
        r = rer[q]
        v_ce = vista(r["ce_top5"])
        v_ref = vista(r["llm_top5_modal"])
        h_ce = {chash(c) for c in v_ce}
        need = min(3, len(v_ce), len(v_ref))
        ov = len(h_ce & {chash(c) for c in v_ref})
        via1 = None if r["llm_inestable"] else ov >= need   # 1/1/1 → no-decisiva
        extra = {}
        if q == "cat015":
            via2 = None   # admit — no existe
            if via1 is not True:   # modal <2/3 o falla → unión (pro-statu-quo)
                union = {chash(c) for run in r["llm_top5_all"] for c in vista(run)}
                need_u = min(3, len(v_ce), len(union))
                ov_u = len(h_ce & union)
                extra["via1_union"] = f"{ov_u}/{need_u}"
                if ov_u >= need_u:
                    via1 = True
                    extra["via1_por"] = "union"
                else:
                    cat015_escalado = True
                    extra["escalado"] = True
            fail_both = False if via1 is True else None   # escalada, nunca fail silencioso
        else:
            hechos = probes["d1_unanimes"].get(q) or {}
            pool_det = pre["d1_pool"].get(q) or {}
            computables = {h: spec for h, spec in hechos.items() if pool_det.get(h)}
            excluidos = [h for h in hechos if not pool_det.get(h)]
            det2 = {h: _hecho_presente(spec["anclas"], v_ce)
                    for h, spec in computables.items()}
            via2 = all(det2.values()) if det2 else None
            extra["detalle_via2"] = det2 or None
            if excluidos:
                extra["via2_excluidos_por_pool"] = excluidos   # paridad F2: no cuentan
            if via1 is None and via2 is None:
                fail_both = None   # indecidible → presentación, nunca silencio
                indecidibles.append(q)
            else:
                fail_both = (via1 is not True) and (via2 is not True)
        d1[q] = {"via1_overlap": f"{ov}/{need}", "via1": via1,
                 "llm_votos": r["llm_votos"], "via2": via2,
                 "fail_both": fail_both, **extra}
    n_fail = sum(1 for v in d1.values() if v["fail_both"] is True)

    # --- D2′ (atribución con paridad; hp001 según branch del precheck) ---
    movers = SHIPS_D2 + (["hp001"] if pre["branch_hp001"] == "CONDICION" else [])
    d2 = {}
    for q in movers:
        r = rer[q]
        v_ce, v_llm = vista(r["ce_top5"]), vista(r["llm_top5_modal"])
        cond = probes["d2_movers"][q]["condicion"]
        pool_det = (pre["d2_pool"].get(q) if q in SHIPS_D2 else pre["hp001_detalle_pool"])
        det = {}
        for h, spec in cond.items():
            en_pool = bool(pool_det.get(h))
            en_llm = _hecho_presente(spec["anclas"], v_llm)
            en_ce = _hecho_presente(spec["anclas"], v_ce)
            det[h] = {"en_pool": en_pool, "en_vista_llm": en_llm, "en_vista_ce": en_ce,
                      "perdido_atribuible": en_pool and en_llm and not en_ce,
                      "ganancia_ce": en_ce and not en_llm,
                      "ausencia_compartida": en_pool and not en_llm and not en_ce}
        info_specs = probes["d2_movers"][q].get("informativo") or {}
        info = {h: {"en_vista_llm": _hecho_presente(spec["anclas"], v_llm),
                    "en_vista_ce": _hecho_presente(spec["anclas"], v_ce)}
                for h, spec in info_specs.items()}
        d2[q] = {"perdida_atribuible": any(v["perdido_atribuible"] for v in det.values()),
                 "detalle": det, "informativo": info or None}
    n_d2_perdidas = sum(1 for v in d2.values() if v["perdida_atribuible"])

    hp001_info = None
    if pre["branch_hp001"] == "INFORMATIVA":
        r = rer["hp001"]
        v_ce, v_llm = vista(r["ce_top5"]), vista(r["llm_top5_modal"])
        hp001_info = {h: {"en_pool": bool(pre["hp001_detalle_pool"].get(h)),
                          "en_vista_llm": _hecho_presente(spec["anclas"], v_llm),
                          "en_vista_ce": _hecho_presente(spec["anclas"], v_ce)}
                      for h, spec in probes["d2_movers"]["hp001"]["condicion"].items()}

    # --- informativas ---
    swap = {q: firma_v4(rer[q]["ce_top5"]) != firma_v4(rer[q]["llm_top5_modal"])
            for q in golds}
    sub04 = {q: sum(1 for c in rer[q]["ce_top5"]
                    if (c.get("similarity") or 0) < RELEVANCE_THRESHOLD)
             for q in golds}
    lat_ce = [x for q in golds for x in rer[q]["ce_lat_s"]]
    lat_llm = [x for q in golds for x in rer[q]["llm_lat_s"]]
    n_calls_ce = sum(len(rer[q]["ce_lat_s"]) + (1 if "ce_perm_lat_s" in rer[q] else 0)
                     for q in golds if not rer[q]["short_circuit"])
    n_calls_llm = sum(len(rer[q]["llm_lat_s"]) for q in golds if not rer[q]["short_circuit"])

    # --- veredicto pre-registrado (diseño v2 §5) ---
    if paradas:
        veredicto = "PARAR"
    elif n_fail >= 2 or n_d2_perdidas >= 1:
        veredicto = "NO-GO"
    elif n_fail == 1 or cat015_escalado or indecidibles:
        veredicto = "GO-CON-PRESENTACION-A-ALBERTO"
    else:
        veredicto = "GO"

    out = {
        "meta": {"at": _now(), "git": _git_commit(),
                 "diseno": "_s66_ce_regate_design.md (v2 post-dúo r1)",
                 "probes": F_PROBES.name + " (congeladas pre-paso-A, X1)",
                 "scope": "CE-puro (sin L-i) — confirmado por Alberto",
                 "db_state": pools["meta"]["db_state"],
                 "corpus_fingerprint": pools["meta"]["corpus_fingerprint"],
                 "registry_fingerprint": pools["meta"]["registry_fingerprint"]},
        "veredicto": veredicto,
        "paradas": paradas or None,
        "d1": {"unanimes": d1, "n_fail_both": n_fail,
               "indecidibles": indecidibles or None,
               "cat015_escalado": cat015_escalado,
               "regla": ">=2 fail-both NO-GO; ==1 presentación; 1/1/1 → vía-2 manda; "
                        "indecidible/escalado → presentación (nunca silencio)"},
        "d2": {"branch_hp001": pre["branch_hp001"], "movers": d2,
               "n_perdidas_atribuibles": n_d2_perdidas,
               "hp001_informativa": hp001_info,
               "regla": ">=1 gold con pérdida ATRIBUIBLE (en-pool ∧ en-vista-LLM ∧ "
                        "¬en-vista-CE) → NO-GO (X3); ausencias compartidas se reportan"},
        "informativas": {
            "swap_aislado_ce_vs_llm_modal": {"n_distintos": sum(swap.values()),
                                             "distintos": sorted(q for q, v in swap.items() if v)},
            "top5_ce_chunks_sim_sub04": {q: n for q, n in sub04.items() if n},
            "pool_a_50_corte_activo": sorted(q for q in golds
                                             if rer[q]["n_pool"] >= RETRIEVAL_TOP_K),
            "llm_votos": {q: rer[q]["llm_votos"] for q in golds},
            "llm_inestables_1_1_1": sorted(q for q in golds if rer[q]["llm_inestable"]),
            "llm_padded_golds": sorted(q for q in golds
                                       if any("padded" in (t or "")
                                              for t in rer[q]["llm_padded"])),
            "cat014_paridad_short_circuit": rer["cat014"]["short_circuit"],
            "n_llamadas": {"ce": n_calls_ce, "llm": n_calls_llm},
            "latencia_rerank_s": {
                "ce": {"p50": _pct(lat_ce, .5), "p95": _pct(lat_ce, .95), "n": len(lat_ce)},
                "llm": {"p50": _pct(lat_llm, .5), "p95": _pct(lat_llm, .95), "n": len(lat_llm)},
            },
        },
    }
    F_REPORT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=110),
                        encoding="utf-8")
    print(yaml.safe_dump({"veredicto": veredicto, "d1_fail_both": n_fail,
                          "d2_perdidas_atribuibles": n_d2_perdidas,
                          "branch_hp001": pre["branch_hp001"],
                          "swap_distintos": out["informativas"]["swap_aislado_ce_vs_llm_modal"]["n_distintos"],
                          "lat": out["informativas"]["latencia_rerank_s"]},
                         allow_unicode=True, sort_keys=False))
    print(f"report OK → {F_REPORT.name}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=["calibracion", "pools", "precheck", "rerank",
                                     "report", "all"])
    args = ap.parse_args()
    fases = (["calibracion", "pools", "precheck", "rerank", "report"]
             if args.fase == "all" else [args.fase])
    for f in fases:
        print(f"=== {f} ===")
        globals()[f"phase_{f}"](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
