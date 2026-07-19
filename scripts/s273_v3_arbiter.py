#!/usr/bin/env python3
"""s273_v3_arbiter.py — runner del prereg v3 (evals/s273_quota_prereg_v3.yaml).

Corrección de MEDICIÓN, no de mecanismo: el flag ENUNCIADOS_QUOTA_FUSION no se toca
(default off; los brazos ON son flip call-time en harness). Subcomandos:

  v3a
      Containment pareado CONTEMPORÁNEO desde los probes YA existentes
      (evals/s273_quota_probe_off.json + _on.json — REUSE declarado: mismo día, misma
      DB, K=3; sus stamps viajan al artefacto). Pérdidas/ganancias ESTABLES K-mayoría
      2/3 (pool-membership y anclas per-fact). STOP duro SOLO sobre la unión s104+s105
      (hp005#2 · hp006#2:ISO-X · hp006#0:Fallo de Tierra); las DEMÁS pérdidas pareadas
      se ENRUTAN al árbitro V3-B (lectura coherente del prereg). Negcontrol: reusa el
      PASS de hoy (evals/s273_quota_negcontrol.json, stamp). $0.
      → evals/s273_v3a_containment_v1.json

  v3b [--execute]
      Árbitro a NIVEL RESPUESTA, scope [hp005, hp006, hp017, cat020]: K=3 generaciones
      brazo OFF y K=3 ON (ruta harness DEMO_FLAGS, retrieval vivo, temp=0, sin retries
      del runner; checkpoint jsonl RESUMIBLE) → matcher determinista de anclas per-fact
      (NFKD-fold patrón s163, mismos anchor-sets que s273_quota_gates:
      evals/s100_factlevel_full.yaml lexically_anchorable). Hecho ESTABLE = ≥2/3.
      Gate: PASS ⇔ ningún hecho estable-en-OFF cae en ON.
      Sin --execute: PREFLIGHT (estimación, 0 llamadas).
      → evals/s273_v3b_arbiter_v1.json (+ réplicas evals/s273_v3b_replies_v1.jsonl)

  v3c [--execute]
      Conversión hp010 (gate de ship): K=3 brazo ON → matcher determinista sobre
      hp010#1 (grupos: nivel 3 / desbloquear memoria / menú Lazos-tecla 2, variantes
      declaradas). SHIP-candidate ⇔ ≥2/3 Y v3a PASS Y v3b PASS.
      → evals/s273_v3c_ship_gate_v1.json (+ réplicas evals/s273_v3c_replies_v1.jsonl)

DB: GET/RPC read-only. Anti-gate-shopping del prereg v3: única re-medición, no-retry.
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
MAJORITY = 2
K = 3
PREREG = "evals/s273_quota_prereg_v3.yaml"
STOP_ANCHOR_KEYS = ["hp005#2:misma zona o subzona", "hp006#2:ISO-X",
                    "hp006#0:Fallo de Tierra"]           # unión dura s104+s105
V3B_SCOPE = ["hp005", "hp006", "hp017", "cat020"]
EST_COST_PER_GENERATION_USD = 0.07                       # sonnet + pool-context (banda assessment)

# hp010#1 — grupos de anclas del matcher (variantes normalizadas; cualquier variante
# satisface su grupo; convertido ⇔ los 3 grupos presentes). Declarados en el artefacto.
HP010_ANCHOR_GROUPS = {
    "nivel_3": ["nivel 3"],
    "desbloquear_memoria": ["desbloquear la memoria", "desbloquear memoria",
                            "desbloquee la memoria", "memoria bloqueada",
                            "desbloquear de la memoria"],
    "menu_lazos_tecla_2": ["autobusqueda", "auto-busqueda", "tecla '2'", "tecla \"2\"",
                           "tecla 2", "pulse la tecla '2'", "pulse '2'", "2:lazo",
                           "opcion 2:lazo", "menu de lazos"],
}

DEMO_FLAGS = {"CHUNKS_TABLE": "chunks_v2", "ENUNCIADOS_MULTIVECTOR": "on",
              "IDENTITY_RESOLVE": "on", "IDENTITY_RESOLVE_POLICY": "ADD",
              "LLM_MAX_TOKENS": "3500", "RERANK_TOP_K": "10", "RERANKER_BACKEND": "llm",
              "MERGE_STRATEGY": "stamps", "RERANK_PREVIEW_CHARS": "800",
              "HYDE_ENABLED": "false", "DIVERSIFY_TIEBREAK": "off", "HYQ_PILOT_FILE": "",
              "GENERATOR_PROMPT_VARIANT": "fidelity", "HYQ_TABLE": "on",
              "GENERATOR_SELECTION_BLOCK": "on", "ENUNCIADOS_QUOTA_FUSION": "off"}


# ───────────────────────── helpers puros (testeables sin red) ─────────────────────────

def anchor_norm(s: str) -> str:
    """Ancla léxica determinista (patrón s163/s103): NFKD-fold + casefold + colapso."""
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def stable_set(replica_sets: list, majority: int = MAJORITY) -> set:
    """Elementos presentes en ≥majority réplicas (K-mayoría)."""
    sets = [set(s) for s in replica_sets]
    universe = set().union(*sets) if sets else set()
    return {x for x in universe if sum(1 for s in sets if x in s) >= majority}


def stable_facts(runs_presence: list, majority: int = MAJORITY) -> dict:
    """runs_presence = [{key: bool}, ...] → {key: estable_bool}. Clave ausente = False."""
    keys = set()
    for r in runs_presence:
        keys |= set(r)
    return {k: sum(1 for r in runs_presence if r.get(k)) >= majority for k in sorted(keys)}


def paired_stable_diff(off_runs_sets: list, on_runs_sets: list,
                       majority: int = MAJORITY) -> dict:
    """Diff pareado de membresía estable (pool-ids o claves): pérdidas/ganancias bajo ON."""
    off_stable = stable_set(off_runs_sets, majority)
    on_stable = stable_set(on_runs_sets, majority)
    return {"lost_under_on": sorted(off_stable - on_stable),
            "gained_under_on": sorted(on_stable - off_stable),
            "n_off_stable": len(off_stable), "n_on_stable": len(on_stable)}


def v3b_gate(off_stable: dict, on_stable: dict) -> dict:
    """PASS ⇔ ningún hecho estable-en-OFF deja de ser estable-en-ON."""
    lost = sorted(k for k, v in off_stable.items() if v and not on_stable.get(k, False))
    gained = sorted(k for k, v in on_stable.items() if v and not off_stable.get(k, False))
    return {"lost_stable_facts": lost, "gained_stable_facts": gained,
            "verdict": "PASS" if not lost else "STOP"}


def hp010_converted(answer: str, groups: dict = None) -> dict:
    """Convertido ⇔ TODOS los grupos de anclas presentes (cualquier variante, normalizada)."""
    groups = groups or HP010_ANCHOR_GROUPS
    text = anchor_norm(answer)
    hits = {g: any(anchor_norm(v) in text for v in variants)
            for g, variants in groups.items()}
    return {"groups": hits, "converted": all(hits.values())}


def ship_gate(v3a_verdict: str, v3b_verdict: str, conversions: int, k: int = K,
              majority: int = MAJORITY) -> dict:
    """SHIP-candidate ⇔ conversión estable (≥2/3) Y v3a PASS Y v3b PASS."""
    conv_stable = conversions >= majority
    ok = conv_stable and v3a_verdict == "PASS" and v3b_verdict == "PASS"
    return {"conversions": f"{conversions}/{k}", "conversion_stable": conv_stable,
            "v3a": v3a_verdict, "v3b": v3b_verdict,
            "verdict": "SHIP_CANDIDATE" if ok else "NO_GO"}


# ─────────────────────────────── infraestructura común ───────────────────────────────

def _git(args):
    return subprocess.run(["git"] + args, capture_output=True, cwd=ROOT).stdout.decode().strip()


def _stamp() -> dict:
    return {"ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "git_sha": _git(["rev-parse", "HEAD"]),
            "git_dirty_src": _git(["status", "--porcelain", "--", "src/"]),
            "prereg": PREREG, "k": K, "majority": MAJORITY}


def _facts_for(qids: list) -> dict:
    import yaml
    fl = yaml.safe_load(open(EVALS / "s100_factlevel_full.yaml", encoding="utf-8"))
    out = {}
    for g in fl["per_gold"]:
        if g["qid"] not in qids:
            continue
        anchors = {}
        for f in g.get("facts", []):
            if not f.get("lexically_anchorable"):
                continue
            a = anchor_norm(f.get("valor") or "")
            if len(a) >= 2:
                anchors[f["key"]] = a
        out[g["qid"]] = anchors
    return out


def _facts_presence(answer: str, anchors: dict) -> dict:
    text = anchor_norm(answer)
    return {key: (a in text) for key, a in anchors.items()}


def _load_checkpoint(path: Path) -> dict:
    done = {}
    if path.exists():
        for line in open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done[(r["qid"], r["arm"], r["k"])] = r
    return done


def _harness():
    """Imports del harness DENTRO del execute (proceso fresco: flags antes de importar)."""
    import os
    for k, v in DEMO_FLAGS.items():
        os.environ[k] = v
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    for k, v in DEMO_FLAGS.items():
        os.environ[k] = v
    from src.rag import retriever as R
    from src.rag.retriever import retrieve_chunks
    from src.rag.reranker import rerank
    from src.rag.generator import generate_answer
    from src.config import RERANK_TOP_K
    from gold_store import dev
    assert R.ENUNCIADOS_QUOTA_ON is False, "el proceso debe arrancar con el flag OFF"
    return R, retrieve_chunks, rerank, generate_answer, RERANK_TOP_K, dev


def _run_replicas(qids: list, arms: list, checkpoint: Path) -> dict:
    """Genera las réplicas que falten (resumible); devuelve {(qid,arm,k): row}."""
    R, retrieve_chunks, rerank, generate_answer, RERANK_TOP_K, dev = _harness()
    golds = {g["qid"]: g for g in dev()}
    done = _load_checkpoint(checkpoint)
    for qid in qids:
        q = golds[qid]["question"]
        for arm in arms:
            for k in range(1, K + 1):
                if (qid, arm, k) in done:
                    print(f"  [skip] {qid}/{arm}/k{k} (checkpoint)", flush=True)
                    continue
                R.ENUNCIADOS_QUOTA_ON = (arm == "on")
                try:
                    pool = retrieve_chunks(q, top_k=50)
                    topk = rerank(q, pool, top_k=RERANK_TOP_K, strict=True)
                    res = generate_answer(q, topk)
                finally:
                    R.ENUNCIADOS_QUOTA_ON = False
                row = {"qid": qid, "arm": arm, "k": k,
                       "answer": res.get("answer", ""),
                       "n_pool": len(pool), "n_topk": len(topk),
                       "n_enun_quota_in_pool": sum(1 for c in pool if c.get("_enun_quota")),
                       "topk_ids": [c.get("id") for c in topk],
                       "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
                with checkpoint.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                done[(qid, arm, k)] = row
                print(f"  [gen] {qid}/{arm}/k{k} pool={row['n_pool']} "
                      f"eq={row['n_enun_quota_in_pool']} ans={len(row['answer'])}ch", flush=True)
    return done


# ─────────────────────────────────── subcomandos ───────────────────────────────────

def cmd_v3a() -> int:
    off = json.load(open(EVALS / "s273_quota_probe_off.json", encoding="utf-8"))
    on = json.load(open(EVALS / "s273_quota_probe_on.json", encoding="utf-8"))
    neg = json.load(open(EVALS / "s273_quota_negcontrol.json", encoding="utf-8"))
    qids = [r["qid"] for r in off["runs"][0]]

    # anclas per-fact pareadas (K-mayoría por brazo)
    fact_runs = {}
    for arm, probe in (("off", off), ("on", on)):
        per_qid = {}
        for qid in qids:
            runs = []
            for rows in probe["runs"]:
                row = next((r for r in rows if r["qid"] == qid), None)
                runs.append(row["facts_anchor_in_pool"] if row else {})
            per_qid[qid] = stable_facts(runs)
        fact_runs[arm] = per_qid
    anchors_lost, anchors_gained = [], []
    for qid in qids:
        g = v3b_gate(fact_runs["off"][qid], fact_runs["on"][qid])
        anchors_lost += g["lost_stable_facts"]
        anchors_gained += g["gained_stable_facts"]
    stop_hits = sorted(set(anchors_lost) & set(STOP_ANCHOR_KEYS))
    routed_to_v3b = sorted(set(anchors_lost) - set(STOP_ANCHOR_KEYS))

    # pool-membership pareada contemporánea (sin referencia v2.2 — retirada, prereg v3)
    pool_diff = {}
    for qid in qids:
        offs = [next((set(r["pool_ids"]) for r in rows if r["qid"] == qid), set())
                for rows in off["runs"]]
        ons = [next((set(r["pool_ids"]) for r in rows if r["qid"] == qid), set())
               for rows in on["runs"]]
        d = paired_stable_diff(offs, ons)
        if d["lost_under_on"] or d["gained_under_on"]:
            pool_diff[qid] = d

    neg_reuse_ok = neg.get("verdict") == "PASS"
    verdict = "PASS" if (not stop_hits and neg_reuse_ok) else "STOP"
    out = {
        "schema": "s273_v3a_containment_v1", "stamp": _stamp(),
        "reuse_declared": {
            "why": "los probes off/on de F3 cumplen V3-A (mismo dia, misma DB, K=3) — re-probar seria gasto sin informacion nueva; sus stamps viajan aqui",
            "probe_off_stamp": off["stamp"], "probe_on_stamp": on["stamp"],
            "negcontrol": {"verdict": neg.get("verdict"),
                           "excess_high": neg.get("excess_golds"),
                           "threshold": neg.get("threshold"), "stamp": neg.get("stamp")},
        },
        "reference_v22": "RETIRADA (razon en el prereg v3 y en evals/s273_f3_closeout_v1.yaml: OFF-hoy 16-missing contra ella > ON 14)",
        "anchors_paired": {"gained": sorted(set(anchors_gained)),
                           "lost": sorted(set(anchors_lost)),
                           "stop_hard_union": STOP_ANCHOR_KEYS,
                           "stop_hits": stop_hits,
                           "routed_to_v3b": routed_to_v3b},
        "pool_membership_paired": pool_diff,
        "verdict": verdict,
    }
    path = EVALS / "s273_v3a_containment_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[V3-A] verdict={verdict} · stop_hits={stop_hits} · "
          f"anclas pareadas +{len(set(anchors_gained))}/−{len(set(anchors_lost))} "
          f"(enrutadas a V3-B: {routed_to_v3b}) · negcontrol reusado="
          f"{neg.get('verdict')} ({neg.get('excess_golds')}≤{neg.get('threshold')})")
    print(f"→ {path}")
    return 0 if verdict == "PASS" else 1


def _preflight(name: str, n_gen: int, ceiling: float) -> None:
    est = n_gen * EST_COST_PER_GENERATION_USD
    print(f"[{name} PREFLIGHT] 0 llamadas hechas. Plan: {n_gen} generaciones "
          f"(+{n_gen} retrieval/rerank) · est ≈ ${est:.2f} (banda {EST_COST_PER_GENERATION_USD}/gen) "
          f"· techo prereg ${ceiling:.2f} → {'OK' if est <= ceiling else 'EXCEDE'} · "
          f"checkpoint resumible, no-retry. Ejecutar con --execute.")


def cmd_v3b(execute: bool) -> int:
    checkpoint = EVALS / "s273_v3b_replies_v1.jsonl"
    n_needed = len(V3B_SCOPE) * 2 * K - len(_load_checkpoint(checkpoint))
    if not execute:
        _preflight("V3-B", max(0, n_needed), 2.50)
        return 0
    anchors = _facts_for(V3B_SCOPE)
    done = _run_replicas(V3B_SCOPE, ["off", "on"], checkpoint)
    per_gold = {}
    overall_lost = []
    for qid in V3B_SCOPE:
        arm_stable = {}
        for arm in ("off", "on"):
            runs = [_facts_presence(done[(qid, arm, k)]["answer"], anchors[qid])
                    for k in range(1, K + 1)]
            arm_stable[arm] = stable_facts(runs)
        g = v3b_gate(arm_stable["off"], arm_stable["on"])
        per_gold[qid] = {"off_stable": arm_stable["off"], "on_stable": arm_stable["on"], **g}
        overall_lost += g["lost_stable_facts"]
    verdict = "PASS" if not overall_lost else "STOP"
    out = {"schema": "s273_v3b_arbiter_v1", "stamp": _stamp(),
           "scope": V3B_SCOPE, "matcher": "anclas lexicas per-fact deterministas (NFKD-fold s163; evals/s100_factlevel_full.yaml lexically_anchorable)",
           "replicas": str(checkpoint.name), "per_gold": per_gold,
           "lost_stable_facts": sorted(set(overall_lost)), "verdict": verdict,
           "stop_consequence": (None if verdict == "PASS" else
                                "dano real a nivel respuesta -> lever CERRADO (anti-gate-shopping v3)")}
    path = EVALS / "s273_v3b_arbiter_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[V3-B] verdict={verdict} · lost={sorted(set(overall_lost))}")
    print(f"→ {path}")
    return 0 if verdict == "PASS" else 1


def cmd_v3c(execute: bool) -> int:
    checkpoint = EVALS / "s273_v3c_replies_v1.jsonl"
    n_needed = K - len(_load_checkpoint(checkpoint))
    if not execute:
        _preflight("V3-C", max(0, n_needed), 1.00)
        return 0
    done = _run_replicas(["hp010"], ["on"], checkpoint)
    reps = []
    conversions = 0
    for k in range(1, K + 1):
        r = hp010_converted(done[("hp010", "on", k)]["answer"])
        conversions += 1 if r["converted"] else 0
        reps.append({"k": k, **r})
    v3a_v = v3b_v = "MISSING"
    p_a = EVALS / "s273_v3a_containment_v1.json"
    p_b = EVALS / "s273_v3b_arbiter_v1.json"
    if p_a.exists():
        v3a_v = json.load(open(p_a, encoding="utf-8"))["verdict"]
    if p_b.exists():
        v3b_v = json.load(open(p_b, encoding="utf-8"))["verdict"]
    gate = ship_gate(v3a_v, v3b_v, conversions)
    out = {"schema": "s273_v3c_ship_gate_v1", "stamp": _stamp(),
           "matcher_groups": HP010_ANCHOR_GROUPS, "replicas_detail": reps,
           "replicas": str(checkpoint.name), **gate,
           "note": "SHIP_CANDIDATE no es ship: el merge/flag en Railway es decision de Alberto"}
    path = EVALS / "s273_v3c_ship_gate_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[V3-C] {gate['verdict']} · conversiones={gate['conversions']} "
          f"(v3a={v3a_v}, v3b={v3b_v})")
    print(f"→ {path}")
    return 0 if gate["verdict"] == "SHIP_CANDIDATE" else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("v3a")
    b = sub.add_parser("v3b"); b.add_argument("--execute", action="store_true")
    c = sub.add_parser("v3c"); c.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    if a.cmd == "v3a":
        return cmd_v3a()
    if a.cmd == "v3b":
        return cmd_v3b(a.execute)
    return cmd_v3c(a.execute)


if __name__ == "__main__":
    raise SystemExit(main())
