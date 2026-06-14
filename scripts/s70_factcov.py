#!/usr/bin/env python3
"""s70 — métrica GRANULAR de cobertura de hechos (read-only, $0): ¿cuántos de los hechos
REQUERIDOS del gold están en la RESPUESTA del bot? (no en el chunk — en el output).

Hipótesis a falsar (s69): el veredicto holístico del juez (PASS/PARCIAL/FALLO, ±2 de
ruido) no distingue mejoras de COMPLETITUD; una métrica per-hecho casi-determinista sí.
Re-puntúa el A/B de s69 (s67base vs s69fid) a nivel de hecho usando el MISMO matcher del
audit (strict_match sobre el answer normalizado). Mide cobertura, NO corrección (un hecho
presente puede estar MAL — la corrección es el otro eje, el juez de no-fabricación).

Usa los facts del gate report (sufficiency.facts: probe + strength) de los golds answer
con hechos. Por gold: cobertura = fracción de hechos requeridos presentes, media sobre K.

Uso: python scripts/s70_factcov.py
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from strict_match import norm_ocr, anchor_present, chunk_has_quote_strict  # noqa: E402

EVALS = ROOT / "evals"


def probe_hit(answer_norm: str, probe) -> bool:
    if isinstance(probe, list):
        return all(anchor_present(str(p), answer_norm) for p in probe)
    s = str(probe)
    return chunk_has_quote_strict(answer_norm, s[1:] if s.startswith("~") else s)


def coverage(gens: dict, qid: str, facts: list) -> tuple[float, float]:
    """(cobertura_media_todos, cobertura_media_FUERTES) sobre las K respuestas."""
    runs = [r.get("answer") for r in gens.get(qid, {}).values() if r.get("answer")]
    if not runs or not facts:
        return (0.0, 0.0)
    fuertes = [f for f in facts if f.get("strength") == "fuerte"]
    cov_all, cov_str = [], []
    for ans in runs:
        an = norm_ocr(ans)
        cov_all.append(sum(1 for f in facts if probe_hit(an, f.get("probe"))) / len(facts))
        if fuertes:
            cov_str.append(sum(1 for f in fuertes if probe_hit(an, f.get("probe"))) / len(fuertes))
    return (sum(cov_all) / len(cov_all),
            sum(cov_str) / len(cov_str) if cov_str else float("nan"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    report = yaml.safe_load((EVALS / "s67base_gate_report.yaml").read_text(encoding="utf-8"))
    base_g = json.loads((EVALS / "s67base_generations.json").read_text(encoding="utf-8"))
    fid_g = json.loads((EVALS / "s69fid_generations.json").read_text(encoding="utf-8"))
    diana = {"cat008", "cat020", "hp005", "hp014", "cat019"}

    rows, sum_b, sum_f, n = [], 0.0, 0.0, 0
    up = down = same = 0
    for g in report["golds"]:
        qid = g["qid"]
        suff = g.get("sufficiency") or {}
        facts = suff.get("facts") or []
        if not facts:
            continue
        cb_all, cb_str = coverage(base_g, qid, facts)
        cf_all, cf_str = coverage(fid_g, qid, facts)
        d = cf_all - cb_all
        n += 1
        sum_b += cb_all
        sum_f += cf_all
        if d > 0.02:
            up += 1
        elif d < -0.02:
            down += 1
        else:
            same += 1
        rows.append({"qid": qid, "diana": qid in diana, "n_facts": len(facts),
                     "cov_base": round(cb_all, 3), "cov_fid": round(cf_all, 3),
                     "delta": round(d, 3),
                     "cov_base_fuertes": round(cb_str, 3) if cb_str == cb_str else None,
                     "cov_fid_fuertes": round(cf_str, 3) if cf_str == cf_str else None})

    out = {"meta": {"metrica": "cobertura per-hecho del ANSWER (strict_match); mide completitud NO correccion",
                    "golds_con_hechos": n,
                    "cobertura_media_base": round(sum_b / n, 3),
                    "cobertura_media_fidelity": round(sum_f / n, 3),
                    "delta_medio": round((sum_f - sum_b) / n, 3),
                    "golds_mejora": up, "golds_peor": down, "golds_igual": same},
           "golds": sorted(rows, key=lambda r: r["delta"], reverse=True)}
    (EVALS / "s70_factcov.yaml").write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100),
                                            encoding="utf-8")
    print("=" * 72)
    print(f"COBERTURA per-hecho (n={n} golds con hechos): "
          f"base={out['meta']['cobertura_media_base']} → fidelity={out['meta']['cobertura_media_fidelity']} "
          f"(Δ medio {out['meta']['delta_medio']:+.3f})")
    print(f"golds: mejora={up} · peor={down} · igual={same}")
    print("--- DIANA (per-gold) ---")
    for r in rows:
        if r["diana"]:
            print(f"  {r['qid']:8} cov {r['cov_base']:.2f}→{r['cov_fid']:.2f} (Δ{r['delta']:+.2f}) "
                  f"| fuertes {r['cov_base_fuertes']}→{r['cov_fid_fuertes']}")
    print("--- mayores subidas/bajadas (todos) ---")
    for r in out["golds"][:4] + out["golds"][-4:]:
        print(f"  {r['qid']:8} Δ{r['delta']:+.2f} ({r['cov_base']:.2f}→{r['cov_fid']:.2f}){' [diana]' if r['diana'] else ''}")
    print(f"\n→ s70_factcov.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
