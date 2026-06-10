#!/usr/bin/env python3
"""s59_ab_verdict.py — tabla de decisión §3 del lever s59 (pre-registrada).

Compara el A/B: baseline s58 (congelado) vs brazo lever s59, con las definiciones
de UNA sola lectura del diseño (`evals/_s59_lever_design_FINAL.md` §3):

  - Niveles FALLO=0 PARCIAL=1 PASS=2 sobre el veredicto MODAL K=5.
  - K-estable := modal >=3/5 (de `votes`; distinto del bucket K-INESTABLE del
    report, que es partición v3 del gate).
  - P (pares completos) := answer-golds K-estables en AMBOS brazos → Δ_net y Δ_mean.
  - Caída PASS-control := modal de un gold de los 10 FIJADOS deja de ser PASS.
  - Δ_inestables := answer-golds K-inestables (lever) − (base)  [guardarraíl].
  - Conducta: no-answer golds → correcta(base)→incorrecta(lever) = caída.
  - F_base/F_post: `s59_fabrications_{base,post}.yaml` (C2/R3).

Tabla (total): 1) caída UNÁNIME → ROLLBACK · 2) >1 caída control / F_post>F_base /
Δ_net<0 / >=2 caídas conducta / Δ_inest>+3 → ROLLBACK · 3) Δ_net>=+2 ∧ caídas<=1 ∧
F_post<=F_base ∧ Δ_inest<=+1 → SHIP · 4) resto → GRIS (Alberto).

Uso: python scripts/s59_ab_verdict.py
Salida: evals/s59_ab_verdict.yaml + tabla consola.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
ORDER = {"FALLO": 0, "PARCIAL": 1, "PASS": 2}
ANSWER_LIKE = {"answer", "answer-con-conflicto"}


def load_report(path: Path) -> dict:
    rep = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {r["qid"]: r for r in rep["golds"]}, rep["resumen"]


def k_stable(row: dict) -> bool:
    votes = row.get("votes") or {}
    return bool(votes) and max(votes.values()) >= 3


def conducta_ok(row: dict) -> bool | None:
    esp = row.get("conducta_esperada")
    bot = row.get("conducta_bot_modal")
    if esp is None or bot is None:
        return None
    # answer-family colapsa (mismo criterio del scorer/juez)
    fam = lambda c: "answer" if c in ("answer", "answer-con-conflicto",
                                      "refuse-inference") else c
    return fam(esp) == fam(bot)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    base, base_sum = load_report(EVALS / "s58_gate_report.yaml")
    post, _ = load_report(EVALS / "s59_gate_report.yaml")
    fab_base = yaml.safe_load((EVALS / "s59_fabrications_base.yaml").read_text(encoding="utf-8"))
    fab_post = yaml.safe_load((EVALS / "s59_fabrications_post.yaml").read_text(encoding="utf-8"))

    control = base_sum["pass_control_FIJADO"]
    unanime = set(base_sum["pass_control_unanime"])
    assert len(control) == 10, f"PASS-control fijado debe ser 10, hay {len(control)}"

    answers = {q for q, r in base.items()
               if r.get("conducta_esperada") in ANSWER_LIKE}

    # --- P, Δ_net, Δ_mean ------------------------------------------------------
    pairs, excluded = [], []
    for q in sorted(answers):
        b, p = base.get(q), post.get(q)
        if not p:
            excluded.append({"qid": q, "why": "sin fila en brazo lever"})
            continue
        sb, sp = k_stable(b), k_stable(p)
        if sb and sp:
            pairs.append({"qid": q, "base": b["veredicto"], "post": p["veredicto"],
                          "d": ORDER[p["veredicto"]] - ORDER[b["veredicto"]]})
        else:
            excluded.append({"qid": q, "why": f"K-inestable en "
                             f"{'base' if not sb else ''}{'+' if not sb and not sp else ''}"
                             f"{'lever' if not sp else ''}",
                             "base_votes": b.get("votes"), "post_votes": p.get("votes")})
    d_net = sum(r["d"] for r in pairs)
    d_mean = d_net / len(pairs) if pairs else 0.0

    # --- PASS-control ------------------------------------------------------------
    drops_unanime, drops_other = [], []
    for q in control:
        p = post.get(q)
        if p is None or p.get("veredicto") != "PASS":
            (drops_unanime if q in unanime else drops_other).append(
                {"qid": q, "post": (p or {}).get("veredicto"), "votes": (p or {}).get("votes")})

    # --- Δ_inestables -------------------------------------------------------------
    inest_base = [q for q in answers if not k_stable(base[q])]
    inest_post = [q for q in answers if q in post and not k_stable(post[q])]
    d_inest = len(inest_post) - len(inest_base)

    # --- conducta -----------------------------------------------------------------
    cond_drops = []
    for q in sorted(set(base) - answers):
        b, p = base[q], post.get(q)
        if p and conducta_ok(b) is True and conducta_ok(p) is False:
            cond_drops.append({"qid": q, "esp": b.get("conducta_esperada"),
                               "base": b.get("conducta_bot_modal"),
                               "post": p.get("conducta_bot_modal")})

    F_base, F_post = fab_base["F"], fab_post["F"]

    # --- tabla §3 (total) -----------------------------------------------------------
    if drops_unanime:
        verdict, rule = "ROLLBACK", "1: caída de gold UNÁNIME del PASS-control"
    elif (len(drops_unanime) + len(drops_other) > 1 or F_post > F_base or d_net < 0
          or len(cond_drops) >= 2 or d_inest > 3):
        verdict, rule = "ROLLBACK", "2: control>1 / F↑ / Δ<0 / conducta>=2 / inest>+3"
    elif d_net >= 2 and (len(drops_unanime) + len(drops_other)) <= 1 \
            and F_post <= F_base and d_inest <= 1:
        verdict, rule = "SHIP", "3: Δ_net>=+2 ∧ control<=1 ∧ F_post<=F_base ∧ inest<=+1"
    else:
        verdict, rule = "GRIS", "4: celda no cubierta por SHIP/ROLLBACK → decisión Alberto"

    out = {
        "meta": {"at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "design": "evals/_s59_lever_design_FINAL.md §3"},
        "P_pairs": len(pairs), "excluded": excluded,
        "delta_net": d_net, "delta_mean": round(d_mean, 4),
        "moves": [r for r in pairs if r["d"] != 0],
        "pass_control": {"drops_unanime": drops_unanime, "drops_no_unanime": drops_other},
        "delta_inestables": {"base": sorted(inest_base), "post": sorted(inest_post),
                             "delta": d_inest},
        "conducta_drops": cond_drops,
        "fabricaciones": {"F_base": F_base, "F_post": F_post,
                          "base_golds": fab_base["k_stable_golds"],
                          "post_golds": fab_post["k_stable_golds"]},
        "verdict": verdict, "rule": rule,
    }
    (EVALS / "s59_ab_verdict.yaml").write_text(
        yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"P (pares completos) = {len(pairs)} | excluidos = {len(excluded)}")
    print(f"Δ_net = {d_net:+d}   Δ_mean = {d_mean:+.3f}")
    for r in pairs:
        if r["d"]:
            print(f"  {r['qid']}: {r['base']} → {r['post']} ({r['d']:+d})")
    print(f"PASS-control: caídas unánimes={len(drops_unanime)} {drops_unanime} | "
          f"no-unánimes={len(drops_other)} {drops_other}")
    print(f"Δ_inestables = {d_inest:+d} (base {len(inest_base)} → post {len(inest_post)})")
    print(f"Conducta: caídas={len(cond_drops)} {cond_drops}")
    print(f"Fabricaciones: F_base={F_base} → F_post={F_post}")
    print(f"\n══ VEREDICTO §3: {verdict}  [regla {rule}] ══")
    print("→ evals/s59_ab_verdict.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
