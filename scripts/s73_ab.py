#!/usr/bin/env python3
"""s73 — orquestación + veredicto del A/B del Brazo A (LEVER2_IDENTITY), ENDURECIDO tras el
workflow adversarial. NO reusa s67_ab.py (es CE-específico: ce_top5/llm_votos/pairing): este es
un comparador NUEVO base-vs-A para los 2 movers (hp009, hp018). Brazo base = s67base REUSADO
(flag-OFF canónico, paridad probada en Paso 0; reranker sin seed → re-freezear el base metería
ruido, no señal). Sólo se PAGA el arm A.

RUNBOOK (freeze/generate/judge = bvg con el env de config-freeze; este script = asserts + veredicto):

  # config-freeze (idéntica salvo el flag); cache AISLADO (s73 copy: no contamina el s67 canónico):
  $env:CHUNKS_TABLE='chunks_v2'; $env:HYDE_ENABLED='false'; $env:RERANKER_BACKEND='llm'
  $env:MERGE_STRATEGY='stamps'; $env:GENERATOR_PROMPT_VARIANT='base'
  $env:EMBED_CACHE_PATH='evals/s73_embed_cache.json'
  # ARM A (flag ON):
  $env:BVG_RUN_ID='s73a'; $env:LEVER2_IDENTITY='on'
  python scripts/bvg_kmajority.py freeze   --qids hp009,hp018 --k 5
  python scripts/s73_ab.py asserts     # $0 — STOP si drift de corpus/registry/cache/juez
  python scripts/bvg_kmajority.py generate --qids hp009,hp018 --k 5
  python scripts/bvg_kmajority.py judge    --qids hp009,hp018 --k 5
  python scripts/s73_ab.py veredicto   # factcov-desde-base + classify_pair + árbol n=2

  python scripts/s73_ab.py selftest    # $0 — verifica I/O (carga base + facts-assert + factcov) + rama
                                       #      neutral; las ramas de decisión: tests/test_ab_verdict.py

Decisiones clave (post-dúo + workflow):
 - K=5 en AMBOS brazos (base reusado a K=5 → comparabilidad; margen 4/5 calibrado, s67_ab:78).
 - factcov lee los facts del report BASE (s67base) — NUNCA del de arm A: si A flipa a PASS el
   bucket pasa a PASS-control y bvg NO emite sufficiency.facts (bucket-coupling, bvg:618).
 - control (37 no-movers) = byte-idéntico (Paso 0, re-confirmado offline aquí) → control_intacto
   por construcción; el arm A solo se corre sobre los 2 movers.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from ab_verdict import classify_pair, small_n_verdict  # noqa: E402
from s70_factcov import coverage  # noqa: E402  (cobertura per-hecho — fuente única)

EVALS = ROOT / "evals"
MOVERS = ["hp009", "hp018"]
EXPECTED_FACTS = {"hp009": 2, "hp018": 5}   # cardinalidad de facts en s67base (STOP si schema-drift)
EXPECTED_CACHE = "evals/s73_embed_cache.json"
EXPECTED_JUDGE = "gpt-5.5-2026-04-23"   # juez de s67base (assert de identidad al reusar el base)
FACTCOV_TOL = 0.001                     # tolerancia para "factcov no cae"

S67_MANIFEST = EVALS / "s67base_run_manifest.json"
S67_JUD = EVALS / "s67base_judgments.json"
S67_GEN = EVALS / "s67base_generations.json"
S67_REPORT = EVALS / "s67base_gate_report.yaml"
S73A_MANIFEST = EVALS / "s73a_run_manifest.json"
S73A_JUD = EVALS / "s73a_judgments.json"
S73A_GEN = EVALS / "s73a_generations.json"


def _utf8():
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load(p: Path) -> dict:
    assert p.exists(), f"falta {p.name} (¿corriste la fase de bvg correspondiente?)"
    return json.loads(p.read_text(encoding="utf-8"))


def _expected_series_fp(flag_on: bool) -> str:
    """Recalcula el fingerprint del registry bajo el flag (robusto a cambios de morley.yaml:
    no hardcodea el hash). Restaura el estado del cache al salir."""
    from src.rag import series_registry as SR
    prev = os.environ.get("LEVER2_IDENTITY")
    if flag_on:
        os.environ["LEVER2_IDENTITY"] = "on"
    else:
        os.environ.pop("LEVER2_IDENTITY", None)
    SR.reset_registry_cache()
    fp = SR.registry_fingerprint()
    if prev is None:
        os.environ.pop("LEVER2_IDENTITY", None)
    else:
        os.environ["LEVER2_IDENTITY"] = prev
    SR.reset_registry_cache()
    return fp


def _detect_movers() -> list[str]:
    """Re-confirma offline (control a $0) qué golds cambian bajo el flag — debe ser == MOVERS.
    Misma firma que evals/_s73_movers.py (extract + membresía de serie)."""
    import gold_store
    from src.rag import retriever as R
    from src.rag import series_registry as SR

    def sig(q: str, on: bool) -> tuple:
        if on:
            os.environ["LEVER2_IDENTITY"] = "on"
        else:
            os.environ.pop("LEVER2_IDENTITY", None)
        SR.reset_registry_cache()
        models = R.extract_product_models(q)
        return (tuple(sorted(models)), SR.any_series(models),
                tuple(sorted(SR.shared_sources_for(models))))

    movers = []
    for g in gold_store.dev():
        if sig(g["question"], False) != sig(g["question"], True):
            movers.append(g["qid"])
    os.environ.pop("LEVER2_IDENTITY", None)
    SR.reset_registry_cache()
    return sorted(movers)


def _verdicts(jud: dict, qid: str) -> list[str]:
    runs = jud[qid]
    return [runs[k].get("veredicto", "?") for k in sorted(runs)]


def _facts_for(report: dict, qid: str) -> list:
    for g in report["golds"]:
        if g["qid"] == qid:
            return (g.get("sufficiency") or {}).get("facts") or []
    return []


def _judge_models(jud: dict) -> list[str]:
    return sorted({row.get("judge_model_real")
                   for runs in jud.values() for row in runs.values()
                   if row.get("judge_model_real")})


# ----------------------------------------------------------------- cmd: asserts
def cmd_asserts(_args) -> int:
    """Asserts EJECUTABLES con STOP. Los de MANIFEST (corpus/registry/cache) corren tras `freeze`,
    ANTES de pagar generate/judge (gate pre-pago). Los que necesitan JUDGMENTS (juez/scope) se
    saltan si s73a_judgments.json aún no existe → re-correr este comando tras `judge` los añade."""
    _utf8()
    base_m, a_m = _load(S67_MANIFEST), _load(S73A_MANIFEST)
    bf, af = base_m["freeze"], a_m["freeze"]
    stops = []

    # --- MANIFEST (pre-pago): corpus idéntico (no-drift s67base[12-jun]→s73a) ---
    if af.get("corpus_fingerprint") != bf.get("corpus_fingerprint"):
        stops.append(f"STOP corpus-drift: s73a={af.get('corpus_fingerprint')} != "
                     f"s67base={bf.get('corpus_fingerprint')}")
    # registry: arm A = fingerprint ON (tratamiento activo); != el OFF del base.
    exp_on = _expected_series_fp(True)
    got = (af.get("series_registry") or {}).get("fingerprint")
    if got != exp_on:
        stops.append(f"STOP registry: s73a fp={got} != esperado-ON {exp_on} "
                     f"(¿LEVER2_IDENTITY no estaba ON en el freeze?)")
    if got == (bf.get("series_registry") or {}).get("fingerprint"):
        stops.append("STOP registry: s73a == s67base fp (tratamiento NO activo — flag OFF)")
    # cache aislado (no el s67 canónico) — comparación por basename (robusta a separadores).
    cache = (af.get("embeddings") or {}).get("embed_cache_path") or ""
    if Path(cache).name != Path(EXPECTED_CACHE).name:
        stops.append(f"STOP cache: embed_cache_path={cache!r} != {EXPECTED_CACHE} "
                     "(arm A contaminaría el cache canónico s67)")

    # --- JUDGMENTS (post-judge): se saltan en el pre-pago si aún no existen ---
    phase = "PRE-PAGO (manifest)" if not S73A_JUD.exists() else "COMPLETO (manifest+juez+scope)"
    if S73A_JUD.exists():
        a_jud = _load(S73A_JUD)
        jm = _judge_models(a_jud)
        if jm != [EXPECTED_JUDGE]:
            stops.append(f"STOP juez: s73a judge_model_real={jm} != [{EXPECTED_JUDGE}] "
                         "(drift del juez → re-juzgar el base, no reusar s67base)")
        extra = sorted(set(a_jud) - set(MOVERS))
        if extra:
            stops.append(f"STOP scope: s73a tiene golds fuera de los movers: {extra}")

    if stops:
        print("\n".join(stops))
        return 1
    print(f"asserts OK [{phase}]: corpus idéntico · registry ON {got} (base OFF "
          f"{(bf.get('series_registry') or {}).get('fingerprint')}) · cache {Path(cache).name}"
          + (f" · juez OK · arm A solo movers" if S73A_JUD.exists()
             else " — RE-CORRER tras `judge` para validar juez+scope"))
    return 0


# ---------------------------------------------------------- núcleo del veredicto
def _compute(base_jud, treat_jud, base_gen, treat_gen, report, control_intacto: bool) -> dict:
    rows, movers_cls = [], []
    factcov_no_cae = True
    for qid in MOVERS:
        facts = _facts_for(report, qid)                       # SIEMPRE del report base
        exp = EXPECTED_FACTS.get(qid)
        assert exp is not None and len(facts) == exp, (
            f"STOP schema-drift: {qid} tiene {len(facts)} facts en s67base, esperado {exp} "
            f"(la métrica primaria factcov sería inválida)")
        cb, _ = coverage(base_gen, qid, facts)
        ca, _ = coverage(treat_gen, qid, facts)
        cls = classify_pair(_verdicts(base_jud, qid), _verdicts(treat_jud, qid))
        movers_cls.append(cls)
        cae = (ca + FACTCOV_TOL) < cb
        if cae:
            factcov_no_cae = False
        rows.append({
            "qid": qid, "n_facts": len(facts),
            "base_modal": cls["base"]["veredicto"], "treat_modal": cls["treat"]["veredicto"],
            "base_votes": cls["base"]["votes"], "treat_votes": cls["treat"]["votes"],
            "delta": cls["delta"],
            "factcov_base": round(cb, 3), "factcov_treat": round(ca, 3),
            "factcov_cae": cae,
            "treat_diagnosticos": [treat_jud[qid][k].get("diagnostico")
                                   for k in sorted(treat_jud[qid])][:3],
        })
    veredicto = small_n_verdict(movers_cls, factcov_no_cae=factcov_no_cae,
                                control_intacto=control_intacto)
    return {"veredicto": veredicto, "factcov_no_cae": factcov_no_cae,
            "control_intacto": control_intacto, "movers": rows}


def _print_report(out: dict, titulo: str) -> None:
    print("=" * 72)
    print(f"{titulo}: {out['veredicto']['veredicto']} — {out['veredicto']['motivo']}")
    print(f"factcov_no_cae={out['factcov_no_cae']} · control_intacto={out['control_intacto']} · "
          f"2º eje (no-invención): revisar diagnósticos del juez + correr prod-smoke (decide Alberto)")
    for r in out["movers"]:
        print(f"  {r['qid']:7} {r['base_modal']}→{r['treat_modal']} [{r['delta']}] | "
              f"votos {r['base_votes']}→{r['treat_votes']} | "
              f"factcov {r['factcov_base']}→{r['factcov_treat']}{' CAE' if r['factcov_cae'] else ''} "
              f"({r['n_facts']} facts)")


# --------------------------------------------------------------- cmd: veredicto
def cmd_veredicto(_args) -> int:
    _utf8()
    report = yaml.safe_load(S67_REPORT.read_text(encoding="utf-8"))
    movers_now = _detect_movers()
    control_intacto = movers_now == sorted(MOVERS)
    if not control_intacto:
        print(f"⚠ AVISO: los movers detectados {movers_now} != {sorted(MOVERS)} — "
              "el control de los 37 ya NO es por construcción.")
    out = _compute(_load(S67_JUD), _load(S73A_JUD), _load(S67_GEN), _load(S73A_GEN),
                   report, control_intacto)
    _print_report(out, "VEREDICTO s73 (Brazo A)")
    (EVALS / "s73_ab_report.yaml").write_text(
        yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    print("→ evals/s73_ab_report.yaml")
    return 0


# ---------------------------------------------------------------- cmd: selftest
def cmd_selftest(_args) -> int:
    """$0: corre el veredicto con arm A := s67base (treat=base). Esperado: todo 'neutral',
    factcov Δ=0, veredicto GRIS. ALCANCE: verifica la INTEGRACIÓN de I/O (carga de
    report/generations/judgments base, facts-assert de cardinalidad, factcov-desde-base) + la
    rama NEUTRAL del comparador. NO ejercita las ramas de decisión (flip/regresión/margen) ni la
    carga de s73a_* — esas las cubren tests/test_ab_verdict.py (17 verdes)."""
    _utf8()
    report = yaml.safe_load(S67_REPORT.read_text(encoding="utf-8"))
    base_jud, base_gen = _load(S67_JUD), _load(S67_GEN)
    out = _compute(base_jud, base_jud, base_gen, base_gen, report, control_intacto=True)
    _print_report(out, "SELFTEST (base-vs-base)")
    ok = (out["veredicto"]["veredicto"] == "GRIS"
          and all(r["delta"] == "neutral" for r in out["movers"])
          and out["factcov_no_cae"]
          and all(not r["factcov_cae"] for r in out["movers"]))
    print(f"\nselftest {'OK ✓ (cableado correcto: base-vs-base = neutral/GRIS)' if ok else 'FALLO ✗'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["asserts", "veredicto", "selftest"])
    args = ap.parse_args()
    return {"asserts": cmd_asserts, "veredicto": cmd_veredicto, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
