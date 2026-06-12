#!/usr/bin/env python3
"""s67 — orquestación + veredicto del A/B del swap CE (diseño v2 post-dúo, pre-registrado).

bvg_kmajority es EL instrumento (freeze/generate/judge/report por brazo, BVG_RUN_ID);
este script NO genera ni juzga: computa firmas, ejecuta los asserts de instrumento,
deriva el pairing, ejecuta la herencia de artefactos para los golds emparejados (F5) y
emite el veredicto por la tabla pre-registrada (§3 del diseño). Día D (orden F3/X6):

  freeze-A (s67base, llm) → freeze-B (s67ce, voyage) →
  `s67_ab.py asserts`   ($0; STOP aquí si drift — ANTES de pagar generación) →
  generate+judge A → checkpoint coste →
  generate+judge B con --qids del pairing (solo no-paired) →
  `s67_ab.py herencia`  (copia gen+judgments base→ce para paired, shared_from) →
  report A + report B → `s67_ab.py veredicto` → evals/s67_ab_report.yaml

Asserts (tri-vía + pool, §2.4 del diseño):
  (0) pool50_light idéntico entre brazos (la garantía del embed-cache, VERIFICADA);
  (i) firma-F1(vista CE freeze) == firma-F1(ce_top5 del gate) por gold — ≥1 distinto
      → STOP instrumento (diagnóstico: pool vs gate distingue embed-drift de CE-drift);
  (ii) firma-F1(freeze-A) ∈ vistas-LLM del gate (llm_top5_all); per-gold fuera = dado-
       plausible (F1 dúo r1, NO stop); ≥9/35 rerankeados fuera → STOP sistémico;
  (iii) judge_model_real idéntico entre brazos (F4) — se verifica en `veredicto`.

Criterio (transfiere §7-s61; A1-A4 del diseño): movers := firma-F1 distinta entre
brazos; dado-PLAUSIBLE := no-unánime-gate ∨ freeze-A ∉ vistas-gate → EXCLUIDO de Δ_net;
ganancia cuenta con margen (PASS ≥4/5); caída de unánime-base (modal PASS 5/5):
atribuible-operacional → ROLLBACK (regla-1) / dado-plausible → GRIS-Alberto separado.
Tabla: SHIP Δ_net≥+2 ∧ control≤1-investigada ∧ F_post≤F_base ∧ Δ_inest≤+1 · ROLLBACK
regla-1 / control>1 / F↑ / Δ_net<0 / conducta≥2 / inest>+3 · resto GRIS. F7-endurecida:
GRIS-estable → recomendación pre-escrita SHIP-por-estabilidad (la emite este script,
la decide Alberto).
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"

import argparse
import datetime
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ["HYDE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bvg_kmajority import aggregate  # noqa: E402  (fuente única de la agregación K-mayoría)
from src.rag.generator import RELEVANCE_THRESHOLD  # noqa: E402

EVALS = ROOT / "evals"
F_BASE_CTX = EVALS / "s67base_frozen_contexts.json"
F_CE_CTX = EVALS / "s67ce_frozen_contexts.json"
F_BASE_GEN = EVALS / "s67base_generations.json"
F_CE_GEN = EVALS / "s67ce_generations.json"
F_BASE_JUD = EVALS / "s67base_judgments.json"
F_CE_JUD = EVALS / "s67ce_judgments.json"
# GATE_RUN_ID: tras el re-gate X2 (drift de embeddings detectado por el assert (i) el
# 12-jun), la referencia del A/B es el re-gate s67 (pools del MISMO embed-cache).
GATE_RUN = os.environ.get("GATE_RUN_ID", "s66")
F_GATE_RERANKS = EVALS / f"{GATE_RUN}_gate_reranks.json"
F_GATE_POOLS = EVALS / f"{GATE_RUN}_gate_pools.json"
F_PAIRING = EVALS / "s67_pairing.yaml"
F_REPORT = EVALS / "s67_ab_report.yaml"

K_EXPECTED = 5
STOP_SISTEMICO = 9       # ≥9/35 rerankeados con freeze-A fuera de vistas-gate (pre-registrado)
MARGEN_GANANCIA = 4      # ganancia cuenta en Δ_net solo con PASS ≥4/5 (guardia s61 §7)


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _load(p: Path) -> dict:
    assert p.exists(), f"falta {p.name}"
    return json.loads(p.read_text(encoding="utf-8"))


def chash(c: dict) -> str:
    # MISMO hash que s60_step0/s61_gate/s66_gate (consistencia de firmas entre artefactos).
    return hashlib.sha1((c.get("content") or "").encode("utf-8")).hexdigest()[:12]


def firma_f1(top5: list[dict]) -> tuple:
    """Firma F1-s61 enmendada: (id, content-hash, round(sim,2)) de los chunks
    POST-filtro-0.4 del top-5, EN ORDEN. Vista vacía := tupla vacía (G7).
    La similarity es la del RETRIEVE en ambos backends (reranker.py:237 no la toca)."""
    return tuple((c.get("id"), chash(c), round(c.get("similarity") or 0, 2))
                 for c in top5 if (c.get("similarity") or 0) >= RELEVANCE_THRESHOLD)


def _pool_key(pool_light: list[dict]) -> tuple:
    return tuple((c.get("id"), c.get("similarity")) for c in pool_light)


# ------------------------------------------------------------------ cmd: asserts
def cmd_asserts(args) -> int:
    base = _load(F_BASE_CTX)
    ce = _load(F_CE_CTX)
    gate = _load(F_GATE_RERANKS)
    qids = sorted(q for q in gate if q != "meta")
    assert sorted(base) == qids == sorted(ce), (
        f"freezes incompletos: base={len(base)} ce={len(ce)} gate={len(qids)}")

    fallos_pool, fallos_ce, fuera_vistas = [], [], []
    vista_a_clase = {}
    for q in qids:
        # (0) pool50 idéntico entre brazos — la garantía del embed-cache, verificada.
        if _pool_key(base[q]["pool50_light"]) != _pool_key(ce[q]["pool50_light"]):
            fallos_pool.append(q)
        # (i) vista CE del freeze == vista CE del gate (CE determinista 39/39 s66).
        f_ce, f_gate = firma_f1(ce[q]["top5"]), firma_f1(gate[q]["ce_top5"])
        if f_ce != f_gate:
            gate_pool_ids = [c.get("id") for c in _load(F_GATE_POOLS)[q]["pool"]]
            freeze_pool_ids = [c.get("id") for c in ce[q]["pool50_light"]]
            fallos_ce.append({"qid": q,
                              "pool_igual_al_gate": gate_pool_ids == freeze_pool_ids,
                              "diagnostico": ("CE re-versionado (pin no-snapshotted)"
                                              if gate_pool_ids == freeze_pool_ids
                                              else "pool distinto (embed drift server-side)")})
        # (ii) freeze-A dentro de las vistas LLM persistidas del gate (n=3).
        if gate[q].get("short_circuit"):
            vista_a_clase[q] = "short-circuit"
            continue
        f_a = firma_f1(base[q]["top5"])
        vistas = [firma_f1(v) for v in gate[q]["llm_top5_all"]]
        f_modal = firma_f1(gate[q]["llm_top5_modal"])
        if f_a not in vistas:
            vista_a_clase[q] = "4a-vista"
            fuera_vistas.append(q)
        else:
            vista_a_clase[q] = "modal-gate" if f_a == f_modal else "minoritaria-gate"

    # pairing F1: vista idéntica ⇒ comparte generación+juicio (Δ:=0).
    paired = [q for q in qids if firma_f1(base[q]["top5"]) == firma_f1(ce[q]["top5"])]
    no_paired = [q for q in qids if q not in paired]

    n_rerank = sum(1 for q in qids if not gate[q].get("short_circuit"))
    out = {
        "meta": {"at": _now(), "umbral_stop_sistemico": f">={STOP_SISTEMICO}/{n_rerank}"},
        "asserts": {
            "pool50_entre_brazos": {"fallos": fallos_pool, "ok": not fallos_pool},
            "vista_ce_vs_gate": {"fallos": fallos_ce, "ok": not fallos_ce},
            "vista_llm_vs_gate": {"clase_por_gold": vista_a_clase,
                                  "fuera_de_vistas": fuera_vistas,
                                  "n_fuera": len(fuera_vistas),
                                  "stop_sistemico": len(fuera_vistas) >= STOP_SISTEMICO},
        },
        "pairing": {"paired": paired, "no_paired": no_paired,
                    "qids_brazoB": ",".join(no_paired)},
    }
    F_PAIRING.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False),
                         encoding="utf-8")
    print(f"pairing: {len(paired)} paired / {len(no_paired)} a generar+juzgar en brazo B")
    print(f"vista-A: {dict(Counter(vista_a_clase.values()))}")
    stops = []
    if fallos_pool:
        stops.append(f"STOP pool entre brazos: {fallos_pool} — el embed-cache no garantizó "
                      f"el pool (¿DB cambió entre freezes? ¿cache no compartido?)")
    if fallos_ce:
        stops.append(f"STOP vista-CE vs gate ({len(fallos_ce)}): {fallos_ce} — "
                      f"re-gate (~$5-6) antes de pagar generación (X2)")
    if len(fuera_vistas) >= STOP_SISTEMICO:
        stops.append(f"STOP sistémico: {len(fuera_vistas)}/{n_rerank} golds con freeze-A "
                      f"fuera de las vistas del gate (≥{STOP_SISTEMICO} no es dado, es drift)")
    if stops:
        print("\n".join(stops))
        return 1
    print(f"asserts (0)(i)(ii) OK → {F_PAIRING.name}; (iii) juez se verifica en `veredicto`")
    return 0


# ----------------------------------------------------------------- cmd: herencia
def cmd_herencia(args) -> int:
    """F5: phase_report ignora --qids → los paired NECESITAN artefactos en el run ce
    (sin ellos: aggregate([]) = JUDGE-ERROR contaminando partición y Δ_inest). Copia
    generations+judgments base→ce con provenance `shared_from` (vista idéntica ⇒
    comparte generación+juicio, Δ:=0 — F1-s61)."""
    pairing = yaml.safe_load(F_PAIRING.read_text(encoding="utf-8"))
    base_ctx, ce_ctx = _load(F_BASE_CTX), _load(F_CE_CTX)
    base_gen, base_jud = _load(F_BASE_GEN), _load(F_BASE_JUD)
    ce_gen = json.loads(F_CE_GEN.read_text(encoding="utf-8")) if F_CE_GEN.exists() else {}
    ce_jud = json.loads(F_CE_JUD.read_text(encoding="utf-8")) if F_CE_JUD.exists() else {}
    n = 0
    for q in pairing["pairing"]["paired"]:
        # defensa: re-verificar la firma antes de heredar (no confiar en el yaml).
        assert firma_f1(base_ctx[q]["top5"]) == firma_f1(ce_ctx[q]["top5"]), \
            f"{q}: firma ya NO idéntica — pairing.yaml desactualizado, re-corre asserts"
        assert q in base_gen and q in base_jud, f"{q}: artefactos del base incompletos"
        ce_gen[q] = {rk: {**row, "shared_from": "s67base"}
                     for rk, row in base_gen[q].items()}
        ce_jud[q] = {rk: {**row, "shared_from": "s67base"}
                     for rk, row in base_jud[q].items()}
        n += 1
    F_CE_GEN.write_text(json.dumps(ce_gen, indent=1, ensure_ascii=False), encoding="utf-8")
    F_CE_JUD.write_text(json.dumps(ce_jud, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"herencia OK: {n} golds paired copiados base→ce (shared_from estampado)")
    return 0


# ---------------------------------------------------------------- cmd: veredicto
def _modal_conducta(runs_j: dict) -> str | None:
    c = Counter(v.get("conducta_bot") for v in runs_j.values() if v.get("conducta_bot"))
    return c.most_common(1)[0][0] if c else None


def cmd_veredicto(args) -> int:
    base_ctx, ce_ctx = _load(F_BASE_CTX), _load(F_CE_CTX)
    base_jud, ce_jud = _load(F_BASE_JUD), _load(F_CE_JUD)
    gate = _load(F_GATE_RERANKS)
    pairing = yaml.safe_load(F_PAIRING.read_text(encoding="utf-8"))
    clase_a = pairing["asserts"]["vista_llm_vs_gate"]["clase_por_gold"]
    qids = sorted(q for q in gate if q != "meta")

    # (iii) F4: juez SERVIDO idéntico entre brazos (R4 solo compara alias+SHAs).
    jm = {arm: sorted({row.get("judge_model_real") for runs in jud.values()
                       for row in runs.values()
                       if row.get("judge_model_real") and not row.get("shared_from")})
          for arm, jud in (("base", base_jud), ("ce", ce_jud))}
    juez_ok = jm["base"] == jm["ce"] or not jm["ce"]   # ce todo-paired ⇒ vacuo-ok
    rows, caidas_r1, gris_alberto, ganancias_sin_margen = [], [], [], []
    d_net = 0
    for q in qids:
        agg_b = aggregate([base_jud[q][k].get("veredicto", "?") for k in sorted(base_jud[q])])
        agg_c = aggregate([ce_jud[q][k].get("veredicto", "?") for k in sorted(ce_jud[q])])
        assert agg_b["n_valid"] >= 3 and agg_c["n_valid"] >= 3, f"{q}: JUDGE-ERROR en un brazo"
        paired = q in pairing["pairing"]["paired"]
        unanime_b = agg_b["veredicto"] == "PASS" and agg_b["unanime"]
        # dado-PLAUSIBLE (A2 enmendada F1): no-unánime-gate ∨ freeze-A fuera de vistas-gate.
        votos_gate = sorted(gate[q]["llm_votos"], reverse=True)
        dado = (votos_gate != [3]) or (clase_a.get(q) == "4a-vista")
        mover = not paired
        delta = None
        if mover:
            b_pass, c_pass = agg_b["veredicto"] == "PASS", agg_c["veredicto"] == "PASS"
            if c_pass and not b_pass:       # ganancia
                if dado:
                    delta = "excluido-dado"
                elif agg_c["votes"].get("PASS", 0) >= MARGEN_GANANCIA:
                    delta = +1
                else:
                    delta = "ganancia-sin-margen"   # se lista, no cuenta (guardia s61)
                    ganancias_sin_margen.append(q)
            elif b_pass and not c_pass:     # pérdida
                if unanime_b:               # caída de unánime → regla-1 (A2)
                    if dado:
                        delta = "caida-unanime-dado-GRIS"
                        gris_alberto.append(q)
                    else:
                        delta = "caida-unanime-ROLLBACK"
                        caidas_r1.append(q)
                elif dado:
                    delta = "excluido-dado"
                else:
                    delta = -1
            else:
                delta = 0
            if isinstance(delta, int):
                d_net += delta
        rows.append({
            "qid": q, "paired": paired, "dado_plausible": dado,
            "clase_freeze_A": clase_a.get(q), "votos_gate": votos_gate,
            "base": {"modal": agg_b["veredicto"], "votes": agg_b["votes"],
                     "bucket": agg_b["bucket"], "unanime": agg_b["unanime"]},
            "ce": {"modal": agg_c["veredicto"], "votes": agg_c["votes"],
                   "bucket": agg_c["bucket"], "unanime": agg_c["unanime"]},
            "delta": delta,
            "conducta_esperada": base_ctx[q].get("conducta_esperada"),
            "conducta_base": _modal_conducta(base_jud[q]),
            "conducta_ce": _modal_conducta(ce_jud[q]),
        })

    f_base = sum(1 for r in rows if r["base"]["modal"] == "FALLO")
    f_post = sum(1 for r in rows if r["ce"]["modal"] == "FALLO")
    ki_base = [r["qid"] for r in rows if r["base"]["bucket"] == "K-INESTABLE"]
    ki_ce = [r["qid"] for r in rows if r["ce"]["bucket"] == "K-INESTABLE"]
    d_inest = len(ki_ce) - len(ki_base)
    conducta_reg = [r["qid"] for r in rows
                    if r["conducta_esperada"] and r["conducta_base"] == r["conducta_esperada"]
                    and r["conducta_ce"] != r["conducta_esperada"]]
    # "control" (tabla s61): caídas en golds NO-mover ya no existen bajo pairing (F6 — los
    # paired comparten juicio); el control efectivo = caídas excluidas-por-dado, a investigar.
    control_caidas = [r["qid"] for r in rows
                      if r["delta"] in ("excluido-dado",) and r["base"]["modal"] == "PASS"
                      and r["ce"]["modal"] != "PASS"]

    rollback = bool(caidas_r1) or len(control_caidas) > 1 or f_post > f_base \
        or d_net < 0 or len(conducta_reg) >= 2 or d_inest > 3
    ship = (not rollback and d_net >= 2 and len(control_caidas) <= 1
            and f_post <= f_base and d_inest <= 1)
    veredicto = "ROLLBACK" if rollback else ("SHIP" if ship else "GRIS")
    f7 = (veredicto == "GRIS" and d_net >= 0 and len(control_caidas) <= 1
          and not conducta_reg and f_post <= f_base and d_inest <= 1
          and not gris_alberto and juez_ok)

    report = {
        "meta": {"at": _now(), "diseno": "_s67_ab_design.md v2 post-dúo r1",
                 "k": K_EXPECTED, "reglas": "transfiere §7-s61; A1-A4 pre-datos (diseño §3)",
                 "juez_servido": jm, "juez_identico_entre_brazos": juez_ok},
        "veredicto": veredicto,
        "f7_ship_por_estabilidad_aplica": f7,
        "recomendacion": ("SHIP-por-estabilidad (F7 pre-escrita: GRIS-estable; beneficio "
                          "NO-end-to-end: dado 11/39, latencia ~3.4x, coste ~15x; SOLO path "
                          "Y1 sin target_models — decide Alberto)" if f7 else None),
        "metricas": {"delta_net": d_net, "F_base": f_base, "F_post": f_post,
                     "delta_inest": d_inest, "ki_base": ki_base, "ki_ce": ki_ce,
                     "conducta_regresiones": conducta_reg,
                     "control_caidas_excluidas_por_dado": control_caidas,
                     "caidas_regla1_ROLLBACK": caidas_r1,
                     "caidas_unanime_dado_GRIS_Alberto": gris_alberto,
                     "ganancias_sin_margen": ganancias_sin_margen,
                     "n_paired": len(pairing["pairing"]["paired"]),
                     "n_movers": sum(1 for r in rows if not r["paired"])},
        "golds": rows,
    }
    F_REPORT.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False,
                                       width=110), encoding="utf-8")
    print("=" * 72)
    print(f"VEREDICTO: {veredicto}{'  (F7: recomendación SHIP-por-estabilidad)' if f7 else ''}")
    print(f"Δ_net={d_net}  F {f_base}→{f_post}  Δ_inest={d_inest:+d}  "
          f"conducta_reg={conducta_reg}  regla1={caidas_r1}  GRIS-Alberto={gris_alberto}")
    if not juez_ok:
        print(f"⚠ JUEZ DISTINTO ENTRE BRAZOS {jm} → instrumento NO limpio (GRIS forzoso)")
    print(f"→ {F_REPORT.name}")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["asserts", "herencia", "veredicto"])
    args = ap.parse_args()
    return {"asserts": cmd_asserts, "herencia": cmd_herencia,
            "veredicto": cmd_veredicto}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
