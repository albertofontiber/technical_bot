#!/usr/bin/env python3
"""s59_gate1.py — manifest-lever (PRE/POST) + ALTER ef_search + GATE-1 del lever.

Secuencia pin del diseño (`evals/_s59_lever_design_FINAL.md` §5):
  1. Captura PRE via pg_proc.proconfig (no SHOW: falla en sesión fresca) + SHA de
     las definiciones RPC + versión pgvector + commit del código.
  2. ALTER FUNCTION match_chunks_v2 SET hnsw.ef_search = 120  (abre la VENTANA DB;
     reversible: --reset ejecuta el RESET y cierra la ventana).
  3. Verifica POST (proconfig) y corre GATE-1: para las 7 queries del funnel, ¿el
     RPC k=50 SIN filtro devuelve los chunks-winner de los 10 hechos con rank
     seq-scan exacto <=50? Es una PRUEBA EMPIRICA del recall HNSW@ef=120
     (aproximado), no una garantía. Diagnóstico si faltan: ¿0 filas/filtrado?
     (implementación rota) vs ¿recall HNSW? (subir ef / iterative_scan).

Salida: evals/s59_lever_manifest.json + evals/s59_gate1_report.yaml
Uso:    python scripts/s59_gate1.py            # read-only: manifest + gate-1 con el ef VIGENTE
        python scripts/s59_gate1.py --alter    # ejecuta el ALTER (requiere autorizacion de Alberto:
                                               #   toca la DB compartida de prod; denegado por el
                                               #   permission-mode en s59 — L-ii quedo PENDIENTE)
        python scripts/s59_gate1.py --reset    # RESET (cierra la ventana; rollback de L-ii)
"""
from __future__ import annotations

import os
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402

from src.ingestion.embedder import embed_query  # noqa: E402
from src.rag.retriever import vector_search  # noqa: E402

DIAG = ROOT / "evals" / "s59_recall_diagnosis.yaml"
MANIFEST = ROOT / "evals" / "s59_lever_manifest.json"
OUT = ROOT / "evals" / "s59_gate1_report.yaml"
EF_TARGET = 120
K = 50

RPC_FUNCS = ("match_chunks_v2", "search_chunks_text_v2")


def _git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def db_state(cur) -> dict:
    """proconfig + SHA de definición de las RPC + versión pgvector."""
    state = {}
    for fn in RPC_FUNCS:
        cur.execute(
            "SELECT p.proconfig, pg_get_functiondef(p.oid) FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname='public' AND p.proname=%s", (fn,))
        rows = cur.fetchall()
        assert len(rows) == 1, f"{fn}: esperaba 1 firma, hay {len(rows)}"
        proconfig, fndef = rows[0]
        state[fn] = {
            "proconfig": proconfig,
            "def_sha256_16": hashlib.sha256(fndef.encode()).hexdigest()[:16],
        }
    cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
    state["pgvector"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM chunks_v2")
    state["chunks_v2_count"] = cur.fetchone()[0]
    return state


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--alter", action="store_true",
                    help="ejecuta el ALTER ef_search=120 (L-ii — solo con autorizacion)")
    ap.add_argument("--reset", action="store_true",
                    help="RESET hnsw.ef_search (cierra la ventana DB; rollback)")
    args = ap.parse_args()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    if not (args.alter or args.reset):
        conn.set_session(readonly=True)   # default: solo manifest + gate (cero escritura)
    conn.autocommit = True
    cur = conn.cursor()

    if args.reset:
        pre = db_state(cur)
        cur.execute("ALTER FUNCTION match_chunks_v2 RESET hnsw.ef_search")
        post = db_state(cur)
        print(f"RESET ejecutado. proconfig: {pre['match_chunks_v2']['proconfig']} "
              f"-> {post['match_chunks_v2']['proconfig']}")
        m = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
        m["reset"] = {"at": datetime.datetime.now().isoformat(timespec="seconds"),
                      "post": post}
        MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0

    # --- 1. PRE ---------------------------------------------------------------
    pre = db_state(cur)
    print(f"PRE : proconfig={pre['match_chunks_v2']['proconfig']} "
          f"pgvector={pre['pgvector']} chunks={pre['chunks_v2_count']}")

    # --- 2. ALTER (abre la ventana) — SOLO con --alter autorizado ---------------
    if args.alter:
        cur.execute(f"ALTER FUNCTION match_chunks_v2 SET hnsw.ef_search = {EF_TARGET}")
        post = db_state(cur)
        print(f"POST: proconfig={post['match_chunks_v2']['proconfig']}")
        assert post["match_chunks_v2"]["proconfig"] == [f"hnsw.ef_search={EF_TARGET}"], post
    else:
        post = pre
        print("(sin --alter: L-ii NO aplicado; gate-1 corre con el ef_search VIGENTE — "
              "este A/B mide L-i solo, ver manifest)")

    manifest = {
        "lever": ("s59 canal vectorial sano — L-i (codigo) " +
                  ("+ L-ii ef_search APLICADO" if args.alter
                   else "SOLO; L-ii PENDIENTE de autorizacion (ALTER denegado por "
                        "permission-mode: DB compartida de prod)")),
        "design": "evals/_s59_lever_design_FINAL.md",
        "window_opened_at": (datetime.datetime.now().isoformat(timespec="seconds")
                             if args.alter else None),
        "manifest_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "ef_target_design": EF_TARGET,
        "ef_effective": ("120" if args.alter else
                         "40 (default pgvector; proconfig None)"),
        "pre": pre,
        "post": post,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- 3. GATE-1 --------------------------------------------------------------
    # Universo y expectativa dependen del modo:
    #   con --alter (ef=120): esperados = hechos con rank seq-scan EXACTO <= K.
    #   sin --alter (ef=40 vigente, A/B de L-i solo): esperados = hechos que el
    #   DIAGNOSTICO ya vio en el canal real (rank_vector_nofilter != None) — el
    #   canal aproximado devuelve ~36-40 filas; exigirle el top-50 exacto seria
    #   medir L-ii, que no esta aplicado.
    diag = yaml.safe_load(DIAG.read_text(encoding="utf-8"))
    exact = diag["verification"]["exact_ranks_seqscan_all14"]

    targets = []  # (qid, valor, [winner_ids], exact_rank, seen_in_channel_diag)
    for r in diag["results"]:
        for f in r["facts"]:
            key = f"{r['qid']}|{f['valor']}"
            er = exact[key]["best_winner_exact_rank"]
            seen = any(w.get("rank_vector_nofilter") is not None for w in f["winners"])
            targets.append((r["qid"], str(f["valor"]),
                            [w["chunk_id"] for w in f["winners"]], er, seen))
    if args.alter:
        in_scope = [t for t in targets if t[3] <= K]
        scope_desc = f"rank-exacto<={K} (ef=120)"
    else:
        in_scope = [t for t in targets if t[4]]
        scope_desc = "vistos-en-canal-ef40 por el diagnostico (L-i solo)"
    print(f"\nGATE-1: {len(in_scope)} hechos esperados [{scope_desc}] de {len(targets)}")

    questions = {r["qid"]: r["question"] for r in diag["results"]}
    rows_out, passed = [], 0
    for qid in sorted({t[0] for t in in_scope}):
        emb = embed_query(questions[qid])
        chan = vector_search(questions[qid], top_k=K, threshold=0.3,
                             precomputed_embedding=emb)
        ids = {c["id"] for c in chan}
        n_returned = len(chan)
        for (tq, valor, winner_ids, er, _seen) in in_scope:
            if tq != qid:
                continue
            hit = any(w in ids for w in winner_ids)
            passed += hit
            rows_out.append({"qid": qid, "valor": valor, "exact_rank": er,
                             "channel_returned": n_returned, "winner_in_channel": hit})
            print(f"  {qid} | {valor[:28]:28s} | rank_exacto={er:3d} | "
                  f"canal devolvio {n_returned} | {'HIT' if hit else '** MISS **'}")

    verdict = "PASS" if passed == len(in_scope) else (
        "PARTIAL" if passed > 0 else "FAIL")
    print(f"\nGATE-1: {passed}/{len(in_scope)} -> {verdict}")

    OUT.write_text(yaml.safe_dump({
        "meta": {"at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "git_commit": _git_commit(), "ef_search": EF_TARGET, "k": K,
                 "universe": f"hechos rank-exacto<={K} ({len(in_scope)})"},
        "results": rows_out,
        "passed": passed, "of": len(in_scope), "verdict": verdict,
    }, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Manifest: {MANIFEST}\nReport:   {OUT}")
    conn.close()
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
