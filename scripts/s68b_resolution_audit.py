#!/usr/bin/env python3
"""s68b — AUDIT DE RESOLUCIÓN del eval para el ciclo de GENERACIÓN (read-only, $0).

Pregunta (Alberto, s68b): antes de ampliar el eval o correr el 2×2, ¿tiene el ruler
RESOLUCIÓN suficiente en los golds donde GENERACIÓN es el cuello? Un lever de generación
que ayude a 2-3 golds debe distinguirse del ruido del juez (dado 11/39 medido s67).

Método (todo de artefactos congelados — cero gasto, cero juez nuevo):
  1. RUIDO por gold: las 5 verdicts de s67base (K=5) → distribución, modal, margen.
     DECISIVO := 5/0 o 4/1 (un flip sería señal limpia) · FRÁGIL := 3/2 o 2-2-1
     (puede voltear modal entre corridas SIN intervención = ruido, no señal).
  2. DIANA por gold (de s68_audit_canal.yaml, per-hecho):
     - generación-ADDRESSABLE := TODOS sus hechos-fuertes fallidos están SERVIDOS
       (EN-TOP5-pero-falla) ∨ es solo-débiles ∨ atribución GENERACION — y NINGÚN hecho
       muere en el pool (si un hecho requerido sigue fuera de retrieval, ni el mejor
       generador hace PASS → no es addressable por generación).
     - retrieval-bloqueado := tiene ≥1 hecho que muere en el pool (RANK/EN-POOL).
     - gap := sospecha-gap / NO-LOCALIZADO.
  3. Cruce DIANA × RUIDO × MODAL → la celda que decide: generación-addressable ∧
     DECISIVO ∧ modal∈{PARCIAL,FALLO} (room-to-PASS con señal limpia) =: D.
  4. Anclas de ruido extra ($0): doble-muestra de los golds PAIRED (s67base vs s67ce,
     MISMO contexto congelado → 10 verdicts sobre input idéntico) + varianza de conducta.

REGLA DE DECISIÓN (PRE-REGISTRADA aquí, antes de ver el cruce):
  SHIP exige Δ_net ≥ +2; la banda de ruido ≈ nº de golds FRÁGILES (cada uno puede
  aportar ±1 espurio en un re-run nulo).
  - D ≥ 4 (2× el umbral de SHIP, con margen sobre la banda) → el eval TIENE resolución
    para el ciclo de generación; NO ampliar; proceder con las palancas (orden por coste).
  - D ≤ 3 → resolución INSUFICIENTE; una expansión DIRIGIDA (golds de síntesis con
    chunk limpio, no volumen) está justificada ANTES de pagar el 2×2.
  - Reportar la banda de ruido (nº FRÁGILES) y D explícitos — la decisión la lee Alberto.

Read-only total. Salida: evals/s68b_resolution_audit.yaml + tabla.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
F_REPORT = EVALS / "s67base_gate_report.yaml"
F_AUDIT = EVALS / "s68_audit_canal.yaml"
F_BASE_JUD = EVALS / "s67base_judgments.json"
F_CE_JUD = EVALS / "s67ce_judgments.json"
F_PAIRING = EVALS / "s67_pairing.yaml"
OUT = EVALS / "s68b_resolution_audit.yaml"

ORDER = {"PASS": 2, "PARCIAL": 1, "FALLO": 0}
D_THRESHOLD = 4   # pre-registrado: D >= 4 -> resolución OK; D <= 3 -> expansión dirigida


def verdicts_of(jud: dict, qid: str) -> list[str]:
    runs = jud.get(qid, {})
    return [runs[k].get("veredicto") for k in sorted(runs)
            if runs[k].get("veredicto") in ORDER]


def conductas_of(jud: dict, qid: str) -> list[str]:
    runs = jud.get(qid, {})
    return [runs[k].get("conducta_bot") for k in sorted(runs) if runs[k].get("conducta_bot")]


def noise_class(verds: list[str]) -> tuple[str, str, int]:
    """(clase_ruido, modal, margen). DECISIVO 5/0|4/1 ; FRÁGIL resto."""
    c = Counter(verds)
    if not c:
        return "SIN-DATOS", "?", 0
    top = c.most_common()
    modal = min((v for v, n in top if n == top[0][1]), key=lambda v: ORDER[v])
    margen = top[0][1] - (top[1][1] if len(top) > 1 else 0)
    clase = "DECISIVO" if (top[0][1] >= 4) else "FRAGIL"
    return clase, modal, margen


def diana_class(audit_gold: dict) -> tuple[str, dict]:
    """generación-addressable / retrieval-bloqueado / gap / (mixto via flags)."""
    hechos = audit_gold.get("hechos_fuertes") or []
    solo_deb = audit_gold.get("solo_debiles") or \
        audit_gold.get("atribucion_s67base") == "INDETERMINADO-solo-debiles"
    buckets = [h["bucket"] for h in hechos]
    muere_pool = any(b.startswith(("RANK", "EN-POOL")) for b in buckets)
    servido_falla = any(b == "EN-TOP5-pero-falla" for b in buckets)
    gap = any("NO-LOCALIZADO" in b for b in buckets)
    flags = {"muere_pool": muere_pool, "servido_falla": servido_falla,
             "solo_debiles": bool(solo_deb), "gap": gap,
             "atribucion": audit_gold.get("atribucion_s67base")}
    # generación-ADDRESSABLE: hay fallo de generación Y nada bloqueado en retrieval
    if (servido_falla or solo_deb or audit_gold.get("atribucion_s67base") == "GENERACION") \
            and not muere_pool and not gap:
        return "GEN-ADDRESSABLE", flags
    if muere_pool:
        return "RETRIEVAL-BLOQUEADO", flags
    if gap:
        return "GAP", flags
    return "OTRO", flags


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    report = yaml.safe_load(F_REPORT.read_text(encoding="utf-8"))
    audit = {g["qid"]: g for g in yaml.safe_load(F_AUDIT.read_text(encoding="utf-8"))["golds"]}
    base_j = json.loads(F_BASE_JUD.read_text(encoding="utf-8"))
    ce_j = json.loads(F_CE_JUD.read_text(encoding="utf-8"))
    pairing = yaml.safe_load(F_PAIRING.read_text(encoding="utf-8"))
    paired = set(pairing["pairing"]["paired"])

    rows = []
    for g in report["golds"]:
        qid = g["qid"]
        if g.get("bucket") == "PASS-control":
            continue
        if "CUALITATIVA" in str(g.get("atribucion") or ""):
            # conducta no-answer: fuera del scope generación-answer (se cuenta aparte)
            pass
        verds = verdicts_of(base_j, qid)
        clase_ruido, modal, margen = noise_class(verds)
        diana, flags = diana_class(audit.get(qid, {"qid": qid}))
        conds = conductas_of(base_j, qid)
        rows.append({
            "qid": qid, "bucket": g.get("bucket"),
            "atribucion": g.get("atribucion") or g.get("bucket"),
            "verdicts": dict(Counter(verds)), "modal": modal,
            "ruido": clase_ruido, "margen": margen,
            "diana": diana, "flags": flags,
            "conducta_spread": dict(Counter(conds)),
            "paired_doble_muestra": (dict(Counter(verds + verdicts_of(ce_j, qid)))
                                     if qid in paired else None),
        })

    # --- la celda que decide ---
    gen_addr = [r for r in rows if r["diana"] == "GEN-ADDRESSABLE"]
    D = [r["qid"] for r in gen_addr
         if r["ruido"] == "DECISIVO" and r["modal"] in ("PARCIAL", "FALLO")]
    gen_fragiles = [r["qid"] for r in gen_addr if r["ruido"] == "FRAGIL"]
    fragiles_todos = [r["qid"] for r in rows if r["ruido"] == "FRAGIL"]

    decision = ("RESOLUCION-OK (no ampliar; proceder con las palancas de generacion)"
                if len(D) >= D_THRESHOLD
                else "EXPANSION-DIRIGIDA-JUSTIFICADA (sintesis chunk-limpio, antes del 2x2)")

    out = {
        "meta": {"fuente": "s67base (K=5) + s68_audit_canal + s67ce (paired) — read-only $0",
                 "regla_preregistrada": f"D>={D_THRESHOLD} -> resolucion OK; D<={D_THRESHOLD-1} -> expansion dirigida",
                 "D_definicion": "gen-addressable AND ruido DECISIVO AND modal in {PARCIAL,FALLO}"},
        "DECISION": decision,
        "D_golds_senal_limpia_generacion": D,
        "D_n": len(D),
        "banda_ruido_n_fragiles_total": len(fragiles_todos),
        "gen_addressable_fragiles": gen_fragiles,
        "resumen_diana": dict(Counter(r["diana"] for r in rows)),
        "resumen_diana_x_ruido": dict(Counter(f"{r['diana']}|{r['ruido']}" for r in rows)),
        "golds": rows,
    }
    OUT.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100),
                   encoding="utf-8")

    print("=" * 72)
    print(f"DIANA × RUIDO (residual {len(rows)} golds):")
    for k, v in sorted(out["resumen_diana_x_ruido"].items()):
        print(f"  {k:32} {v}")
    print("-" * 72)
    print(f"D (señal limpia de generación: gen-addressable ∧ DECISIVO ∧ PARCIAL/FALLO) = {len(D)}")
    print(f"   {D}")
    print(f"banda de ruido (golds FRÁGILES totales) = {len(fragiles_todos)}: {fragiles_todos}")
    print(f"gen-addressable pero FRÁGILES (no cuentan como señal) = {gen_fragiles}")
    print("-" * 72)
    print(f"DECISIÓN (regla pre-registrada D>={D_THRESHOLD}): {decision}")
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
