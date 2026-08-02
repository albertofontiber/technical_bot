#!/usr/bin/env python3
"""s293_hp017_preguard_probe.py — ¿escribe el modelo la ruta que el guard borra?

Premisa del lever hp017#2 que la sonda determinista NO puede cerrar: sabemos que el
conflict-guard SUSTITUYE el bloque entero y que un párrafo fiel al carrier con el
número dispara `surgical_repair`; lo que no sabemos es si el borrador del modelo
contenía de verdad la ruta «menú Editar Configuración → pantalla Causa y Efecto» +
«borrar la Regla 1».  Si NO la escribía, el lever de precisión del guard NO paga y
el hecho es una omisión de síntesis (otra clase).

v2 (regla-C sobre mi propia sonda): la v1 hidrataba los `served_ids` del recibo y
se los pasaba a `generate_answer` directamente — pero esas filas pierden
`similarity`, así que `admitted_evidence_rows` las descartaba TODAS y el generador
salía por la rama «sin evidencia»: el guard ni se ejecutaba (`action=None`).  Era
infidelidad de la sonda, no un resultado.  v2 corre el TURNO REAL por el mismo seam
que usó el FULL (`factlevel_assessment.run_pipeline` = retrieve → rerank → coverage
→ generate) y declara si la composición servida coincide con la del recibo.

Coste: N turnos completos (retrieval + rerank LLM + generación).  Default N=3.

Uso:  python scripts/s293_hp017_preguard_probe.py [n_reps]
Salida: evals/s293_hp017_preguard_probe_v1.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import yaml  # noqa: E402

# El instrumento fija DEMO_FLAGS en import-time (freeze-contract) ANTES de importar
# el pipeline: importarlo es lo que hace que esta sonda mida la MISMA stack.
import scripts.factlevel_assessment as FA  # noqa: E402
from src.rag import generator as G  # noqa: E402

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"
QID = "hp017"
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 3

ROUTE_PAT = re.compile(r"editar\s+configuraci", re.IGNORECASE)
SCREEN_PAT = re.compile(r"causa\s+y\s+efecto", re.IGNORECASE)
RULE_PAT = re.compile(r"regla\s*1\b", re.IGNORECASE)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    row = [r for r in receipt["per_gold"] if r["qid"] == QID][0]
    query = row["question"]
    recorded_served = list(row["served_ids"])

    captured: list[dict] = []
    original = G.apply_answer_conflict_guard

    def spy(q, chunks, answer, **kwargs):
        out_answer, trace = original(q, chunks, answer, **kwargs)
        captured.append({"pre": answer, "post": out_answer, "trace": trace})
        return out_answer, trace

    G.apply_answer_conflict_guard = spy
    reps = []
    try:
        for index in range(REPS):
            captured.clear()
            turn = FA.run_pipeline(query)
            snapshot = captured[-1] if captured else {}
            pre = snapshot.get("pre", "")
            post = snapshot.get("post", "")
            trace = snapshot.get("trace", {})
            served_ids = [str(x) for x in (turn.get("served_ids") or [])]
            pre_blocks = [b for b in re.split(r"\n[ \t]*\n", pre) if b.strip()]
            route_blocks = [
                {
                    "i": i,
                    "has_route": bool(ROUTE_PAT.search(b)),
                    "has_screen": bool(SCREEN_PAT.search(b)),
                    "has_rule1": bool(RULE_PAT.search(b)),
                    "text": b.strip()[:500],
                }
                for i, b in enumerate(pre_blocks)
                if ROUTE_PAT.search(b) or RULE_PAT.search(b)
            ]
            reps.append(
                {
                    "rep": index,
                    "guard_reached": bool(snapshot),
                    "guard_action": trace.get("action"),
                    "repaired_blocks": trace.get("repaired_blocks"),
                    "initial_unsafe": trace.get("initial_unsafe_conflict_ids"),
                    "served_ids": served_ids,
                    "served_equals_receipt": sorted(served_ids) == sorted(recorded_served),
                    "n_served": len(served_ids),
                    "pre_has_route": bool(ROUTE_PAT.search(pre)),
                    "post_has_route": bool(ROUTE_PAT.search(post)),
                    "pre_has_rule1": bool(RULE_PAT.search(pre)),
                    "post_has_rule1": bool(RULE_PAT.search(post)),
                    "final_has_route": bool(ROUTE_PAT.search(turn.get("answer") or "")),
                    "route_blocks_in_pre": route_blocks,
                    "pre": pre,
                    "post": post,
                }
            )
            print(
                f"  rep{index}: guard={trace.get('action')} "
                f"bloques={trace.get('repaired_blocks')} "
                f"pre_ruta={bool(ROUTE_PAT.search(pre))} "
                f"post_ruta={bool(ROUTE_PAT.search(post))} "
                f"served={len(served_ids)} "
                f"=recibo:{sorted(served_ids) == sorted(recorded_served)}"
            )
    finally:
        G.apply_answer_conflict_guard = original

    out = {
        "probe": "s293_hp017_preguard_probe_v2",
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "qid": QID,
        "query": query,
        "recorded_served_ids": recorded_served,
        "reps": reps,
        "resumen": {
            "n_reps": len(reps),
            "n_guard_alcanzado": sum(1 for r in reps if r["guard_reached"]),
            "n_guard_reparo": sum(
                1 for r in reps
                if r["guard_action"] in {"surgical_repair", "fail_closed"}
            ),
            "n_pre_con_ruta": sum(1 for r in reps if r["pre_has_route"]),
            "n_post_con_ruta": sum(1 for r in reps if r["post_has_route"]),
            "n_composicion_igual_al_recibo": sum(
                1 for r in reps if r["served_equals_receipt"]
            ),
        },
    }
    path = os.path.join(os.getcwd(), "evals", "s293_hp017_preguard_probe_v1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps(out["resumen"], ensure_ascii=False))


if __name__ == "__main__":
    main()
