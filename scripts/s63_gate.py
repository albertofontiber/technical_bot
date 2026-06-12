#!/usr/bin/env python3
"""s63_gate.py — gate barato del ciclo A (POOLS, sin juez/LLM/rerank) + pairing.

PRE-REGISTRO: evals/s63_gate_spec.yaml (commiteado ANTES de correr — las queries
sintéticas, anclas, condiciones G1-G8, enmiendas E1-E3 y el criterio de pairing
viven ALLÍ; este script las ejecuta, no las define).

Corre los 39 golds dev + 3 probes sintéticas en DOS brazos (control =
SERIES_REGISTRY_ENABLED=false, tratamiento = true) con el MISMO embedding por
par (EMBED_CACHE_PATH — el control puebla, el tratamiento lee). Evalúa G1-G8 +
E3 y emite el pairing que el A/B consumirá.

Artefactos: evals/s63_gate_pools_{control,treatment}.json ·
evals/s63_gate_report.yaml · evals/s63_pairing.yaml · evals/s63_embed_cache.json

Uso:  python scripts/s63_gate.py [--qids cat012,probe:d2_cad201]
"""
from __future__ import annotations

import os
# chunks_v2 + HyDE OFF (= serie s58) ANTES de importar config/retriever.
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
os.environ.setdefault("EMBED_CACHE_PATH", str(ROOT / "evals" / "s63_embed_cache.json"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import gold_store  # noqa: E402
from strict_match import anchor_present, norm_ocr  # noqa: E402
import src.rag.series_registry as sr  # noqa: E402
from src.rag.retriever import retrieve_chunks, extract_product_models  # noqa: E402
from src.config import CHUNKS_TABLE, SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

EVALS = ROOT / "evals"
SPEC = yaml.safe_load((EVALS / "s63_gate_spec.yaml").read_text(encoding="utf-8"))
S61 = yaml.safe_load((EVALS / "s61_gate_probes.yaml").read_text(encoding="utf-8"))

UNANIMES = ["cat010", "cat014", "cat015", "cat022", "hp015", "hp019"]
F_POOLS = {a: EVALS / f"s63_gate_pools_{a}.json" for a in ("control", "treatment")}
F_REPORT = EVALS / "s63_gate_report.yaml"
F_PAIRING = EVALS / "s63_pairing.yaml"


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _git() -> str | None:
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def corpus_fingerprint() -> dict:
    """count + max(created_at) — espejo de bvg_kmajority (gate standalone)."""
    h = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    out = {"table": CHUNKS_TABLE, "count": None, "max_created_at": None}
    try:
        with httpx.Client(timeout=20.0) as c:
            r = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}",
                      headers={**h, "Prefer": "count=exact", "Range": "0-0"},
                      params={"select": "id"})
            cr = r.headers.get("content-range", "*/0")
            out["count"] = int(cr.split("/")[-1]) if "/" in cr else None
            r2 = c.get(f"{SUPABASE_URL}/rest/v1/{CHUNKS_TABLE}", headers=h,
                       params={"select": "created_at", "order": "created_at.desc",
                               "limit": "1"})
            rows = r2.json()
            out["max_created_at"] = rows[0]["created_at"] if rows else None
    except Exception as e:
        out["error"] = str(e)[:200]
    return out


def set_arm(treatment: bool) -> None:
    os.environ["SERIES_REGISTRY_ENABLED"] = "true" if treatment else "false"
    sr.reset_registry_cache()


def fact_in_pool(anclas: list[str], pool: list[dict]) -> bool:
    """Semántica s61 trasladada a POOL: ∃ chunk cuyo content (norm_ocr) contiene
    TODAS las anclas del hecho (AND)."""
    for c in pool:
        text = norm_ocr(c.get("content") or "")
        if all(anchor_present(str(a), text) for a in anclas):
            return True
    return False


def light(c: dict) -> dict:
    return {"id": c.get("id"), "product_model": c.get("product_model"),
            "source_file": c.get("source_file"), "page_number": c.get("page_number"),
            "manufacturer": c.get("manufacturer"),
            "similarity": c.get("similarity")}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--qids", default="", help="csv para smoke dirigido (no escribe report)")
    args = ap.parse_args()
    only = {q.strip() for q in args.qids.split(",") if q.strip()}

    fp_start = corpus_fingerprint()
    print(f"gate s63 | corpus={fp_start} | embed_cache={os.environ['EMBED_CACHE_PATH']}")

    # --- universo de queries: 39 dev + probes del spec (fuente única) ---------
    golds = {g["qid"]: g for g in gold_store.dev()}
    queries: dict[str, str] = {qid: g["question"] for qid, g in sorted(golds.items())}
    for pid, p in SPEC["probes_sinteticas"].items():
        queries[f"probe:{pid}"] = p["query"]
    if only:
        queries = {q: v for q, v in queries.items() if q in only}

    # --- registry (tratamiento) para clasificación ----------------------------
    set_arm(treatment=True)
    assert sr.registry_fingerprint() not in ("empty", "disabled"), \
        "G8: el registry de tratamiento no cargó (¿población?)"
    treat_fp = sr.registry_fingerprint()
    treat_stats = sr.registry_stats()
    member_cores = set()
    shared_lower = set()
    for s in sr._get().series:
        member_cores |= s.member_cores
        shared_lower |= {x.lower() for x in s.shared_sources}

    detected = {qid: extract_product_models(q) for qid, q in queries.items()}
    toca_members = {qid: any(sr.normalize_model(m) in member_cores for m in ms)
                    for qid, ms in detected.items()}

    # --- pools por brazo (control PRIMERO: puebla el cache de embeddings) -----
    pools: dict[str, dict[str, list[dict]]] = {"control": {}, "treatment": {}}
    for arm in ("control", "treatment"):
        set_arm(treatment=(arm == "treatment"))
        for qid, q in queries.items():
            pools[arm][qid] = retrieve_chunks(q, top_k=50)
            print(f"  {arm:9} {qid}: n={len(pools[arm][qid])}")
        if not only:
            F_POOLS[arm].write_text(json.dumps(
                {qid: {"n": len(p), "ids": [c.get("id") for c in p],
                       "pool": [light(c) for c in p]}
                 for qid, p in pools[arm].items()},
                indent=1, ensure_ascii=False), encoding="utf-8")

    # --- pairing (criterio del spec: secuencia de ids, orden incluido) --------
    pairing = {}
    for qid in queries:
        ids_c = [c.get("id") for c in pools["control"][qid]]
        ids_t = [c.get("id") for c in pools["treatment"][qid]]
        pairing[qid] = "identico" if ids_c == ids_t else "cambiado"
    cambiados = sorted(q for q, v in pairing.items() if v == "cambiado")
    cambiados_golds = [q for q in cambiados if not q.startswith("probe:")]

    # --- G1 (pareado) + E3 -----------------------------------------------------
    g1_fallos, e3_perdidas, g1_detail = [], [], {}
    for qid in UNANIMES:
        if qid not in queries:
            continue
        hechos = S61["d1_unanimes"].get(qid) or {}
        if not hechos:        # cat015: sin anclas posibles → cubierto por G4
            g1_detail[qid] = "sin-anclas (cubierto por G4)"
            continue
        per = {}
        for hname, h in hechos.items():
            in_c = fact_in_pool(h["anclas"], pools["control"][qid])
            in_t = fact_in_pool(h["anclas"], pools["treatment"][qid])
            per[hname] = {"control": in_c, "treatment": in_t}
            if in_c and not in_t:
                g1_fallos.append(f"{qid}.{hname}")
            if not in_c:      # presencia en s58 pre-verificada (meta s61_gate_probes)
                e3_perdidas.append(f"{qid}.{hname}")
        g1_detail[qid] = per
    e3_golds_afectados = sorted({x.split(".")[0] for x in e3_perdidas})
    e3_stop = len(e3_golds_afectados) >= 2

    # --- G2 (cat012) -----------------------------------------------------------
    g2 = {"aplica": "cat012" in queries}
    if g2["aplica"]:
        pool_t = pools["treatment"]["cat012"]
        hermanos = [c for c in pool_t
                    if sr.normalize_model(c.get("product_model", "")) in
                    ("am8200g", "am8200n")]
        c12 = S61["d2_movers"]["cat012"]["condicion"]
        tabla = {h: fact_in_pool(c12[h]["anclas"], pool_t)
                 for h in ("h2_reposo_alarma", "h3_consumos_cpu", "h4_capacidad_max")}
        g2.update(n_hermanos_en_pool=len(hermanos), tabla_retenida=tabla,
                  h1_debil_informativa=fact_in_pool(c12["h1_factor_12"]["anclas"], pool_t),
                  PASS=(not hermanos) and all(tabla.values()))

    # --- G3 (probe d2) ----------------------------------------------------------
    g3 = {"aplica": "probe:d2_cad201" in queries}
    if g3["aplica"]:
        pool_t = pools["treatment"]["probe:d2_cad201"]
        pool_c = pools["control"]["probe:d2_cad201"]
        shared_t = [c for c in pool_t if (c.get("source_file") or "").lower() in shared_lower]
        shared_con_ancla = [c for c in shared_t
                            if anchor_present("candado", norm_ocr(c.get("content") or ""))]
        g3.update(
            n_shared_en_control=sum(1 for c in pool_c
                                    if (c.get("source_file") or "").lower() in shared_lower),
            n_shared_en_treatment=len(shared_t),
            shared_sources_t=sorted({c.get("source_file") for c in shared_t}),
            n_shared_con_candado=len(shared_con_ancla),
            info_2222=any(anchor_present("2222", norm_ocr(c.get("content") or ""))
                          for c in shared_t),
            PASS=bool(shared_con_ancla),
        )

    # --- G4 / G5 / G7 ------------------------------------------------------------
    g4_violaciones = [q for q in cambiados if not toca_members.get(q)]
    g5_tabla, g7_flags = {}, []
    for qid in cambiados:
        pc, pt = pools["control"][qid], pools["treatment"][qid]
        ids_t = {c.get("id") for c in pt}
        ids_c = {c.get("id") for c in pc}
        perdidos = [c for c in pc if c.get("id") not in ids_t]
        ganados = [c for c in pt if c.get("id") not in ids_c]
        # G7: toda pérdida explicada por el predicado (con registry ON)
        set_arm(treatment=True)
        no_explicados = [c.get("id") for c in perdidos
                         if sr.passes_nivel2(c, detected[qid])]
        if no_explicados:
            g7_flags.append({qid: no_explicados})
        g5_tabla[qid] = {
            "n_off_on": [len(pc), len(pt)],
            "pm_off": dict(Counter(c.get("product_model") or "?" for c in pc)),
            "pm_on": dict(Counter(c.get("product_model") or "?" for c in pt)),
            "perdidos": len(perdidos),
            "ganados_sources": sorted({c.get("source_file") for c in ganados}),
        }
    g7_pass = all(len(pools["treatment"][q]) >= 3 for q in cambiados) and not g7_flags

    # --- G6 ---------------------------------------------------------------------
    g6 = {}
    if "probe:g6_am8200g" in queries:
        p = pools["treatment"]["probe:g6_am8200g"]
        pms = {sr.normalize_model(c.get("product_model", "")) for c in p}
        g6["am8200g"] = {"n": len(p), "pms": sorted(pms),
                         "PASS": len(p) >= 3 and pms == {"am8200g"}}
    if "probe:g6_cad171" in queries:
        p = pools["treatment"]["probe:g6_cad171"]
        ok = all(
            sr.normalize_model(c.get("product_model", "")) == "cad171"
            or ((c.get("source_file") or "").lower() in shared_lower
                and sr.normalize_model(c.get("product_model", "")) == "cad250")
            for c in p)
        g6["cad171"] = {"n": len(p),
                        "pm_counts": dict(Counter(c.get("product_model") for c in p)),
                        "PASS": len(p) >= 3 and ok}
    g6_pass = all(v["PASS"] for v in g6.values()) if g6 else None

    # --- G8 + fingerprint final ---------------------------------------------------
    set_arm(treatment=False)
    g8 = {"control_fingerprint": sr.registry_fingerprint(),
          "treatment_fingerprint": treat_fp,
          "treatment_stats": dict(zip(("n_series", "n_members", "n_shared"), treat_stats)),
          "PASS": sr.registry_fingerprint() == "disabled"
                  and treat_fp not in ("empty", "disabled")
                  and treat_stats == (2, 6, 2)}
    fp_end = corpus_fingerprint()

    if only:
        print(json.dumps({"pairing": pairing, "g2": g2, "g3": g3}, indent=1,
                         ensure_ascii=False, default=str))
        return 0

    # --- veredicto ----------------------------------------------------------------
    g1_pass = not g1_fallos
    g4_pass = not g4_violaciones
    go = (g1_pass and (not g2["aplica"] or g2["PASS"]) and (not g3["aplica"] or g3["PASS"])
          and g4_pass and (g6_pass is not False) and g7_pass and g8["PASS"]
          and not e3_stop and fp_start.get("count") == fp_end.get("count"))

    report = {
        "meta": {"at": _now(), "git": _git(), "spec": "evals/s63_gate_spec.yaml",
                 "n_queries": len(queries),
                 "corpus_fingerprint": {"start": fp_start, "end": fp_end},
                 "embed_cache": os.environ["EMBED_CACHE_PATH"]},
        "veredicto": {"GO_al_AB": bool(go)},
        "pairing": {"identicos": sorted(q for q, v in pairing.items() if v == "identico"),
                    "cambiados": cambiados,
                    "cambiados_golds_para_AB": cambiados_golds},
        "G1": {"PASS": g1_pass, "fallos_solo_en_tratamiento": g1_fallos,
               "detalle": g1_detail},
        "G2": g2, "G3": g3,
        "G4": {"PASS": g4_pass, "violaciones": g4_violaciones},
        "G5": g5_tabla,
        "G6": g6,
        "G7": {"PASS": g7_pass, "perdidas_no_explicadas": g7_flags},
        "G8": g8,
        "E3": {"STOP": e3_stop, "perdidas_en_control_vs_s58": e3_perdidas,
               "golds_afectados": e3_golds_afectados,
               "instrumento_dudoso": e3_golds_afectados if len(e3_golds_afectados) == 1 else []},
    }
    F_REPORT.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False,
                                       width=110), encoding="utf-8")
    F_PAIRING.write_text(yaml.safe_dump(
        {"criterio": SPEC["pairing_criterio"], "at": _now(),
         "identicos": report["pairing"]["identicos"],
         "cambiados": cambiados, "cambiados_golds_para_AB": cambiados_golds},
        allow_unicode=True, sort_keys=False), encoding="utf-8")

    print("=" * 72)
    print(f"GO al A/B: {go}")
    print(f"pairing: {len(report['pairing']['identicos'])} idénticos / "
          f"{len(cambiados)} cambiados → golds al A/B: {cambiados_golds}")
    print(f"G1 {g1_pass} | G2 {g2.get('PASS')} | G3 {g3.get('PASS')} | G4 {g4_pass} | "
          f"G6 {g6_pass} | G7 {g7_pass} | G8 {g8['PASS']} | E3 stop={e3_stop}")
    print(f"→ {F_REPORT.name} + {F_PAIRING.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
