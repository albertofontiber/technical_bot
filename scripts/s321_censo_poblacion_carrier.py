#!/usr/bin/env python3
"""s321 — Censo de POBLACIÓN de la clase «el carrier del hecho no llega al generador».

**Por qué.** DEC-175 exige DOS puertas para un lever: alcanzabilidad Y población (`cat017#2` era
alcanzable 5/5 y murió con población 1). s321 reabrió `hp017#2` y `hp011#2` como alcanzables ⇒
toca la segunda puerta, y este censo la mide sobre el recibo FULL congelado, sin gastar API.

**v2 — REHECHO tras el dúo (los DOS revisores tumbaron la v1).** La v1 probó UN solo filtro
(`n_support_raw > 0 ∧ n_support_served == 0`), no encontró nada y concluyó «la población es
inmedible desde el recibo». **Era falso, y el fallo era del filtro**: un carrier que NUNCA se
recupera da `n_support_raw = 0`, no `> 0`. Buscaba la firma contraria a la que define la clase.
Sol lo destapó por el campo `submotivo` (que la v1 ni miraba) y Fable por la firma complementaria
del testigo. Lección propia: **concluí un negativo desde un filtro que yo mismo escribí, sin
comprobar que pudiera ver lo que buscaba** — la misma forma que el recibo de s305.

**Las dos firmas, y lo que cada una significa DE VERDAD:**

  A · `submotivo == 'within-doc'` → miembros INEQUÍVOCOS. El carrier existe en corpus
      (`corpus_check: lexical`, con `best_corpus_score`) y no llegó ni al pool.

  B · `raw==0 ∧ served>0 ∧ via_coverage_append ∧ in_pool==false` → **NO es población**: marca
      hechos cuyo soporte llegó por una **lane de coverage** en vez de por retrieval. La mayoría
      son `OK` (la lane funcionó). Sirve como **TRIAJE**, no como conteo: los que además FALLAN
      son candidatos a que la lane trajera un carrier que no cubre el hecho — que es exactamente
      lo demostrado para `hp017#2` (llegó la p45; el gold exige la p43).

⇒ **Cota inferior = A ∪ {los de B que fallan y están probados}**. Reportar |A ∪ B| entero sería
sobre-afirmar en sentido contrario, porque metería 6 éxitos en la población.

Uso:  python scripts/s321_censo_poblacion_carrier.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

import yaml

RECIBO = "evals/s100_factlevel_full_v32_full_20260801.yaml"
DESTINO = "evals/s321_censo_poblacion_carrier_v1.json"
# Probado por sonda POR PARTIDA DOBLE (control de #81, s321): con la p43 (`94cbb0ce`) transmite
# 3/3 a 5/5; con la p45 (`a95f8659`, la que el FULL sí sirvió y el juez acreditó 5/5) da 0/5 en
# las 3. Luego su `synthesis-miss` es falso en sustancia y PERTENECE a esta clase.
PROBADOS = {"hp017#2"}


def _n(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def _b(x) -> bool:
    return str(x).lower() == "true"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    d = yaml.safe_load(open(RECIBO, encoding="utf-8"))
    facts = [f for g in d["per_gold"] for f in g["facts"]]
    fallo = {"synthesis-miss", "retrieval-miss"}

    A = [f for f in facts if f.get("submotivo") == "within-doc"]
    B = [f for f in facts
         if _n(f.get("n_support_raw")) == 0 and _n(f.get("n_support_served")) > 0
         and _b(f.get("via_coverage_append")) and not _b(f.get("in_pool"))]
    B_fallan = [f for f in B if f["clase"] in fallo]
    B_ok = [f for f in B if f["clase"] not in fallo]
    probados = [f for f in B_fallan if any(f["key"].startswith(p) for p in PROBADOS)]
    a_sondar = [f for f in B_fallan if f not in probados]

    cota = {f["key"] for f in A} | {f["key"] for f in probados}
    synth = [f for f in facts if f["clase"] == "synthesis-miss"]

    print("CENSO DE POBLACIÓN v2 — «el carrier del hecho no llega al generador»")
    print("=" * 74)
    print(f"recibo: {RECIBO}  ({len(facts)} hechos)\n")
    print(f"A · submotivo=within-doc (INEQUÍVOCOS): {len(A)}")
    for f in A:
        print(f"     {f['key'][:36]:38s} {f['clase']:15s} corpus_score={f.get('best_corpus_score')}")
    print(f"\nB · soporte por lane de coverage, no por retrieval: {len(B)}"
          f"  → {len(B_ok)} OK (la lane funcionó) · {len(B_fallan)} FALLAN")
    for f in B_fallan:
        marca = "PROBADO por sonda" if f in probados else "candidato — sondar (~$1)"
        print(f"     {f['key'][:36]:38s} {f['clase']:15s} {marca}")
    print(f"\n⇒ COTA INFERIOR de población = {len(cota)}  {sorted(cota)}")
    print(f"   candidatos adicionales a sondar: {len(a_sondar)} "
          f"{[f['key'] for f in a_sondar]}")
    print(f"   cota SUPERIOR de donde puede esconderse más: los {len(synth)} synthesis-miss")
    print("\nContexto de la puerta: el lever B murió con población 1 (DEC-175). Esto es ≥3.")

    out = {
        "censo": "s321_poblacion_carrier_v2",
        "ts": datetime.now(timezone.utc).isoformat(),
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                  capture_output=True).stdout.decode().strip(),
        "recibo_fuente": RECIBO,
        "n_facts": len(facts),
        "por_clase": dict(Counter(f["clase"] for f in facts)),
        "firma_A_within_doc": [f["key"] for f in A],
        "firma_B_lane_coverage": {
            "total": len(B), "ok": [f["key"] for f in B_ok],
            "fallan": [f["key"] for f in B_fallan],
            "aviso": ("B NO es población: marca soporte llegado por lane de coverage en vez de "
                      "retrieval, y la mayoría son OK. Es TRIAJE."),
        },
        "cota_inferior": sorted(cota),
        "n_cota_inferior": len(cota),
        "candidatos_a_sondar": [f["key"] for f in a_sondar],
        "cota_superior_donde_buscar": len(synth),
        "comparacion_con_la_puerta": ("el lever B (cat017#2) murió con POBLACIÓN 1 (DEC-175); esta "
                                      "cota inferior es ≥3 ⇒ la puerta NO se cierra por población, "
                                      "pero tampoco queda probada: falta sondar los candidatos."),
        "correccion_v1": ("la v1 concluyó «inmedible» desde UN filtro (raw>0 ∧ served==0) que buscaba "
                          "la firma CONTRARIA a la de la clase. Tumbado por los dos revisores."),
        "caveat_de_frescura": ("recibo del 01-ago-2026 con claude-sonnet-4-6 y served top-10; el "
                               "corpus se ha movido varias veces. Orden de magnitud, no cifra viva."),
    }
    with open(DESTINO, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"\nrecibo: {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
