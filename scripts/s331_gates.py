#!/usr/bin/env python3
"""s331 gates G1 (v6 §4) — replay del hilo REAL Kidde por BRAZOS, ruta de serving
de producción (`resolve_conversational_turn` → `build_turn_request` → `run_turn`
con `from_production()` — el clon fiel de `_process_query`, telegram_bot:2172-2223).

Brazos (atribución por flag, Sol-4 r-v4):
  off  = paridad PROD hoy: IDENTITY_RESOLVE=on (perfil C1) + levers s331 OFF
  a    = + F1_RESOLVE_GOVERNED=on                                (G1a solo-A)
  ac   = + F1_MENTION_PRECEDENCE=on + GENERATOR_NO_REASK=on      (G1b paquete)
         y además corre el flujo sintético G1c (mención fuera de corpus).

Pre-condición POR BRAZO (Sol-4 r-v5): `refresh_presence()` hasta `vigente` y
estado estampado en el manifest; el refresher periódico no corre aquí (script).

Uso:
  python scripts/s331_gates.py --arm off|a|ac [--out evals/s331_g1_<arm>_v1.json]
  python scripts/s331_gates.py --compare evals/s331_g1_off_v1.json evals/s331_g1_a_v1.json

Checks deterministas en-script; las RESPUESTAS se guardan verbatim para lectura
humana (regla DEC-092b: ninguna regresión/mejora se declara sin leerlas).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")

# El hilo REAL (query_logs e046836f / 4fbca15f, 18-ago-2026). T1 fue
# catalog_shortcut (fuera del alcance del gate — no cruza F1/RAG).
THREAD = [
    ("T2", "Sobre la 2X-AF1-FBS."),
    ("T3", "Programación principalmente."),
]
# G1c — mención elegible FUERA del corpus-catálogo (familia gobernada sin tag:
# EMA1224B4R/W, alta s324b §0.D) + confirmación (regla 2 de la gramática).
G1C_THREAD = [
    ("C1", "La EMA1224B4RW-XQ me da fallo de tierra."),
    ("C2", "Sí."),
]

ARM_FLAGS: dict[str, dict[str, str]] = {
    "off": {},
    "a": {"F1_RESOLVE_GOVERNED": "on"},
    # a+fetch: el brazo A midió pool-entry loss (pool=5, todo datasheet hermana,
    # 0 chunks de familia con allowed_sources n=7 perfecto) — la clase DEC-084.
    # IDENTITY_FETCH es el seam EXISTENTE para esa clase (s93: NO-OP en famtie-39;
    # métrica de HOY = este hilo servido → re-medición legítima, settled-con-métrica).
    "af": {"F1_RESOLVE_GOVERNED": "on", "IDENTITY_FETCH": "on"},
    "ac": {"F1_RESOLVE_GOVERNED": "on", "F1_MENTION_PRECEDENCE": "on",
           "GENERATOR_NO_REASK": "on"},
    "acf": {"F1_RESOLVE_GOVERNED": "on", "F1_MENTION_PRECEDENCE": "on",
            "GENERATOR_NO_REASK": "on", "IDENTITY_FETCH": "on"},
}


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _manifest(arm: str, presence: str) -> dict:
    from src.config import LLM_MODEL
    from src.rag import catalog_resolver as CR
    fp = None
    try:
        fp = CR._try_corpus_fingerprint()
    except Exception:  # noqa: BLE001
        pass
    return {
        "arm": arm,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "catalog_commit": CR.catalog_commit(),
        # Limitación DECLARADA (v6 §4): el fingerprint no detecta updates
        # in-place de product_model; la disciplina de ventana manda.
        "corpus_fingerprint": list(fp) if fp else None,
        "llm_model": LLM_MODEL,
        "presence_precondicion": presence,
        "flags": {k: os.environ.get(k, "") for k in
                  ("IDENTITY_RESOLVE", "IDENTITY_RESOLVE_POLICY",
                   "F1_RESOLVE_GOVERNED", "F1_MENTION_PRECEDENCE",
                   "GENERATOR_NO_REASK", "CHUNKS_TABLE",
                   "GENERATOR_PROMPT_VARIANT", "RERANK_TOP_K")},
    }


def _ti_view(ti) -> dict | None:
    if ti is None:
        return None
    return {"resolved_models": list(ti.resolved_models),
            "models_provenance": ti.models_provenance,
            "mention_detected": ti.mention_provenance != "none",
            "mention_provenance": ti.mention_provenance,
            "route_cut": ti.route_cut, "presence": ti.presence}


def _run_turn_real(resolution):
    from src.orchestrator import from_production, run_turn
    from src.orchestrator.telegram_adapter import build_turn_request
    request = build_turn_request(
        query=resolution.query_for_retrieval,
        query_for_retrieval=resolution.query_for_retrieval,
        target_models=resolution.target_models,
        available_models=resolution.available_models,
        update_id=0, chat_id=0, source="harness", transcription=None,
        turn_identity=resolution.turn_identity,
    )
    t0 = time.perf_counter()
    turn = run_turn(request, from_production())
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    served = [{"source_file": c.get("source_file"),
               "chunk_index": c.get("chunk_index")}
              for c in turn.retrieval.chunks]
    return {"answer": turn.generation["answer"], "served": served,
            "stage_timings": dict(turn.stage_timings or {}),
            # Salud del retrieval del turno: una ventana con canales degradados
            # NO es un run limpio de gate (lección s320c) — queda estampada.
            "channel_failures": list(turn.retrieval.channel_failures or [])
            if turn.retrieval.retrieval_measured else None,
            "elapsed_ms": elapsed_ms}


def _drive(flow, checks_fn):
    from src.orchestrator.conversation_policy import PolicyRoute, WorkingState
    from src.orchestrator.conversation_policy_impl import (
        resolve_conversational_turn,
    )
    ws = WorkingState()
    turns = []
    for label, query in flow:
        now = datetime.now(timezone.utc)
        resolution, ws = resolve_conversational_turn(query, ws, now)
        rec = {"label": label, "query": query,
               "route": resolution.route.value,
               "rationale": resolution.rationale,
               "query_for_retrieval": resolution.query_for_retrieval,
               "target_models": list(resolution.target_models or ()),
               "turn_identity": _ti_view(resolution.turn_identity),
               "clarify_question": resolution.clarify_question,
               "state_after": {
                   "last_target_models": list(ws.last_target_models),
                   "pending_mention": ws.pending_mention,
               }}
        if resolution.route in (PolicyRoute.STANDALONE,
                                PolicyRoute.CARRY_FORWARD):
            rec.update(_run_turn_real(resolution))
        turns.append(rec)
    return {"turns": turns, "checks": checks_fn(turns)}


def _check(name, ok, detail=""):
    return {"check": name, "ok": bool(ok), "detail": detail}


def _checks_kidde(arm):
    def fn(turns):
        t2, t3 = turns[0], turns[1]
        out = []
        fam_docs = {"00-3280-501-4009-05_r005_2x-a_series_installation_manual_es",
                    "00-3280-505-4009-04_r004_2x-a_series_operation_manual_es",
                    "00-3280-501-4003-05_r005_2x-a_series_installation_manual_en_0"}
        t3_srcs = {s["source_file"] for s in t3.get("served", [])}
        if arm == "off":
            out.append(_check(
                "t3_hint_familia_truncada",
                "(contexto: 2X-AF1)" in t3["query_for_retrieval"],
                t3["query_for_retrieval"]))
            out.append(_check(
                "t2_bindeo_truncado", t2["target_models"] == ["2X-AF1"],
                str(t2["target_models"])))
            # DESCRIPTIVO, sin veredicto: en OFF, que el manual de familia NO se
            # sirva ES el defecto que el gate documenta (medido 20-ago: T3 sirvió
            # SOLO la datasheet de 5 chunks de la variante hermana).
            out.append(_check(
                "t3_servido_baseline_registrado", True,
                f"servidos={sorted(t3_srcs)} · manual_familia="
                f"{'sí' if t3_srcs & fam_docs else 'NO'}"))
        else:
            out.append(_check(
                "t2_bindea_la_variante_canonica",
                "2X-AF1-FB-S" in t2["target_models"], str(t2["target_models"])))
            out.append(_check(
                "t3_hint_lleva_la_variante",
                "2X-AF1-FB-S" in t3["query_for_retrieval"],
                t3["query_for_retrieval"]))
            out.append(_check(
                "t3_sirve_manual_de_familia", bool(t3_srcs & fam_docs),
                f"servidos={sorted(t3_srcs)}"))
        return out
    return fn


def _checks_g1c(turns):
    c1, c2 = turns[0], turns[1]
    out = [
        _check("c1_clarify_dirigido", c1["route"] == "clarify"
               and c1["rationale"] == "mention_route_cut_clarify",
               f"route={c1['route']} rationale={c1['rationale']}"),
        _check("c1_reconoce_la_mencion_VISIBLE",
               "EMA1224B4RW-XQ" in (c1.get("clarify_question") or ""),
               c1.get("clarify_question") or ""),
        _check("c1_pending_set",
               c1["state_after"]["pending_mention"] == "EMA1224B4RW-XQ", ""),
        _check("c2_familia_pending_derived",
               c2["rationale"] == "pending_confirmed_family"
               and c2["target_models"] == ["EMA1224B4R/W"],
               f"rationale={c2['rationale']} models={c2['target_models']}"),
        _check("c2_responde_la_pregunta_guardada",
               "fallo de tierra" in c2["query_for_retrieval"],
               c2["query_for_retrieval"]),
        _check("c2_pending_consumido",
               c2["state_after"]["pending_mention"] is None, ""),
    ]
    return out


def run_arm(arm: str, out_path: Path) -> int:
    os.environ.setdefault("IDENTITY_RESOLVE", "on")   # paridad PROD (perfil C1)
    os.environ.setdefault("IDENTITY_RESOLVE_POLICY", "replace")
    for k in ("F1_RESOLVE_GOVERNED", "F1_MENTION_PRECEDENCE",
              "GENERATOR_NO_REASK", "IDENTITY_FETCH"):
        os.environ.pop(k, None)
    os.environ.update(ARM_FLAGS[arm])

    from src.rag import catalog_resolver as CR
    estado = CR.refresh_presence()
    presence = CR.presence_estado()
    print(f"[{arm}] presencia pre-condicionada: refresh={estado} estado={presence}")

    receipt = {"manifest": _manifest(arm, presence),
               "kidde": _drive(THREAD, _checks_kidde(arm))}
    if arm in ("ac", "acf"):
        receipt["g1c"] = _drive(G1C_THREAD, lambda t: _checks_g1c(t))

    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    fails = [c for blk in ("kidde", "g1c") if blk in receipt
             for c in receipt[blk]["checks"] if not c["ok"]]
    for blk in ("kidde", "g1c"):
        if blk in receipt:
            for c in receipt[blk]["checks"]:
                print(f"[{arm}] {'PASS' if c['ok'] else 'FAIL'} "
                      f"{c['check']} {c['detail'][:110]}")
    print(f"[{arm}] recibo → {out_path}")
    return 1 if fails else 0


def compare(off_path: Path, a_path: Path) -> int:
    off = json.loads(off_path.read_text(encoding="utf-8"))
    a = json.loads(a_path.read_text(encoding="utf-8"))
    t3_off = {s["source_file"] for s in off["kidde"]["turns"][1].get("served", [])}
    t3_a = {s["source_file"] for s in a["kidde"]["turns"][1].get("served", [])}
    # Centinela hp009-LOCAL (Fable-1 r-v4): un doc solo-de-variante-hermana que
    # el brazo OFF servía no puede DESAPARECER del servido bajo REPLACE en A.
    hermana = "2x-af1-s-161721-es"
    ok = not (hermana in t3_off and hermana not in t3_a)
    print(f"[compare] hp009-local ({hermana}): off={'sí' if hermana in t3_off else 'no'} "
          f"a={'sí' if hermana in t3_a else 'no'} → {'PASS' if ok else 'FAIL'}")
    dropped = sorted(t3_off - t3_a)
    print(f"[compare] docs servidos OFF y no en A: {dropped or 'ninguno'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARM_FLAGS))
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("OFF_JSON", "A_JSON"))
    args = ap.parse_args()
    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))
    if not args.arm:
        ap.error("--arm o --compare")
    out = Path(args.out or ROOT / "evals" / f"s331_g1_{args.arm}_v1.json")
    return run_arm(args.arm, out)


if __name__ == "__main__":
    raise SystemExit(main())
