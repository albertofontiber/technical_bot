#!/usr/bin/env python3
"""s69 — veredicto del A/B del lever de generación (diseño _s69_generation_design.md v3.2).

Compara TRATAMIENTO (s69fid, variant=fidelity) vs CONTROL (s67base re-juzgado en la misma
tanda = s67rejud) sobre los MISMOS contextos congelados (retrieval idéntico por construcción
→ el Δ es puro generación). NO auto-aplica SHIP/rollback: emite el cuadro + la LISTA DE
FLIPS DECISIVOS que exigen verificación CONTENT-LEVEL (enmienda B del dúo — el bias #20
aplicado a la decisión) ANTES de la llamada final.

Endpoint 2 ejes (DEC-001): Δ_completitud (PARCIAL→PASS en la diana) SIN Δ_invención
(regresión de PASS-control / conducta en CUALQUIER gold). Tabla s67 INTOCADA. Reporta:
predicción §4 vs resultado · delta de output_tokens (C4, proxy de verbosidad) · Δ_inest.

Uso: python scripts/s69_ab.py veredicto
"""
from __future__ import annotations

import os

os.environ["CHUNKS_TABLE"] = "chunks_v2"

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from bvg_kmajority import aggregate  # noqa: E402  (misma agregación K-mayoría)

EVALS = ROOT / "evals"
DIANA = ["cat008", "cat020", "hp005", "hp014", "cat019"]   # 4 sólida + 1 incierta (cat008)
DIANA_WATCH = ["hp017"]                                      # parcial-capado
PRED_MOVE = ["cat019", "hp005", "hp014", "cat020"]          # §4: deberían mover
PRED_UNCERTAIN = ["cat008"]                                  # termómetro prompt-vs-capacidad
PASS_CONTROL = ["cat005", "cat010", "cat014", "cat015", "cat018", "cat022",
                "cat023", "hp015", "hp019", "hp020"]
RETRIEVAL_WATCH = ["hp006", "hp009", "hp013", "cat016"]     # admiten/fallan por retrieval


def _load(p: Path) -> dict:
    assert p.exists(), f"falta {p.name} — ¿corriste generate/judge?"
    return json.loads(p.read_text(encoding="utf-8"))


def _verds(jud: dict, qid: str) -> list[str]:
    return [jud[qid][k].get("veredicto", "?") for k in sorted(jud.get(qid, {}))]


def _conducta(jud: dict, qid: str) -> str | None:
    c = Counter(jud[qid][k].get("conducta_bot") for k in sorted(jud.get(qid, {}))
                if jud[qid][k].get("conducta_bot"))
    return c.most_common(1)[0][0] if c else None


def _tokens(gens: dict, qid: str) -> float:
    vals = [gens[qid][k].get("output_tokens") for k in sorted(gens.get(qid, {}))
            if gens[qid][k].get("output_tokens")]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    base_j = _load(EVALS / "s67rejud_judgments.json")     # control re-juzgado en la misma tanda
    fid_j = _load(EVALS / "s69fid_judgments.json")
    base_g = _load(EVALS / "s67base_generations.json")
    fid_g = _load(EVALS / "s69fid_generations.json")
    base_ctx = _load(EVALS / "s67base_frozen_contexts.json")
    qids = sorted(base_ctx)

    # juez idéntico entre brazos (assert F4-s67)
    jm = {arm: sorted({jud[q][k].get("judge_model_real") for q in jud for k in jud[q]
                       if jud[q][k].get("judge_model_real")})
          for arm, jud in (("control", base_j), ("fidelity", fid_j))}
    juez_ok = jm["control"] == jm["fidelity"]

    rows, movers, flips_decisivos, conducta_reg, pass_control_caidas = [], [], [], [], []
    f_base = f_post = 0
    ki_base, ki_fid = [], []
    for q in qids:
        ab = aggregate(_verds(base_j, q))
        af = aggregate(_verds(fid_j, q))
        cond_exp = base_ctx[q].get("conducta_esperada")
        cb, cf = _conducta(base_j, q), _conducta(fid_j, q)
        tok_b, tok_f = _tokens(base_g, q), _tokens(fid_g, q)
        if ab["veredicto"] == "FALLO":
            f_base += 1
        if af["veredicto"] == "FALLO":
            f_post += 1
        if ab["bucket"] == "K-INESTABLE":
            ki_base.append(q)
        if af["bucket"] == "K-INESTABLE":
            ki_fid.append(q)
        cambio = ab["veredicto"] != af["veredicto"]
        es_flip_pos = ab["veredicto"] in ("PARCIAL", "FALLO") and af["veredicto"] == "PASS"
        es_flip_neg = ab["veredicto"] == "PASS" and af["veredicto"] != "PASS"
        if cambio:
            movers.append(q)
        # decisivos = los que mueven Δ_net (diana) o regresan PASS-control
        if (q in DIANA and es_flip_pos) or (q in PASS_CONTROL and es_flip_neg):
            flips_decisivos.append(q)
        if q in PASS_CONTROL and ab["veredicto"] == "PASS" and af["veredicto"] != "PASS":
            pass_control_caidas.append(q)
        if cond_exp and cb == cond_exp and cf != cond_exp:
            conducta_reg.append(q)
        rows.append({
            "qid": q, "diana": q in DIANA, "pass_control": q in PASS_CONTROL,
            "retrieval_watch": q in RETRIEVAL_WATCH,
            "control": {"modal": ab["veredicto"], "votes": ab["votes"], "bucket": ab["bucket"]},
            "fidelity": {"modal": af["veredicto"], "votes": af["votes"], "bucket": af["bucket"]},
            "cambio": cambio, "flip_pos": es_flip_pos, "flip_neg": es_flip_neg,
            "conducta_exp": cond_exp, "conducta_control": cb, "conducta_fidelity": cf,
            "tokens_control": tok_b, "tokens_fidelity": tok_f,
            "delta_tokens": round(tok_f - tok_b, 1),
        })

    # Δ_net SOLO sobre la diana (movers context-cambiado = PARCIAL/FALLO→PASS o caída)
    d_net = sum(1 for r in rows if r["diana"] and r["flip_pos"]) \
        - sum(1 for r in rows if r["diana"] and r["flip_neg"])
    # predicción §4 vs resultado
    pred = {q: next(r["flip_pos"] for r in rows if r["qid"] == q) for q in PRED_MOVE + PRED_UNCERTAIN}
    # verbosidad: delta de tokens en PASS-control (proxy de "elaboró de más", C4)
    verbosidad_pc = {r["qid"]: r["delta_tokens"] for r in rows
                     if r["pass_control"] and r["delta_tokens"] > 80}

    report = {
        "meta": {"diseno": "_s69_generation_design.md v3.2", "juez": jm,
                 "juez_identico": juez_ok,
                 "NOTA": "veredicto NO auto-aplicado — los flips decisivos exigen verificación "
                         "CONTENT-LEVEL antes de SHIP/rollback (enmienda B, bias #20 en la decisión)"},
        "metricas": {"delta_net_diana": d_net, "F_base": f_base, "F_post": f_post,
                     "delta_inest": len(ki_fid) - len(ki_base),
                     "ki_base": ki_base, "ki_fidelity": ki_fid,
                     "conducta_regresiones": conducta_reg,
                     "pass_control_caidas": pass_control_caidas, "n_movers": len(movers)},
        "FLIPS_DECISIVOS_a_verificar_content_level": flips_decisivos,
        "prediccion_§4_vs_resultado": pred,
        "verbosidad_PASS_control_delta_tokens>80": verbosidad_pc,
        "tabla_s67": ("SHIP Δ_net≥+2 ∧ control≤1 ∧ F_post≤F_base ∧ conducta=0 ∧ Δ_inest≤+1 · "
                      "ROLLBACK regla-1/control>1/F↑/Δ_net<0/conducta≥2/inest>+3 · resto GRIS "
                      "— SOLO tras verificación content-level de los flips"),
        "golds": rows,
    }
    (EVALS / "s69_ab_report.yaml").write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")

    print("=" * 72)
    print(f"Δ_net(diana)={d_net}  F {f_base}→{f_post}  Δ_inest={len(ki_fid)-len(ki_base):+d}  "
          f"conducta_reg={conducta_reg}  PASS-control caídas={pass_control_caidas}")
    print(f"predicción §4 (deberían mover {PRED_MOVE}; incierto {PRED_UNCERTAIN}): {pred}")
    print(f"verbosidad PASS-control (Δtokens>80): {verbosidad_pc}")
    if not juez_ok:
        print(f"⚠ JUEZ DISTINTO ENTRE BRAZOS {jm}")
    print(f"\n>>> FLIPS DECISIVOS a verificar content-level ANTES de decidir: {flips_decisivos}")
    print(f"→ s69_ab_report.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
