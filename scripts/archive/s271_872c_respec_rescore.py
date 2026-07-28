#!/usr/bin/env python3
"""S271 — re-score $0 del disclosure de obl_872c con la spec OPCIÓN 1 (DEC-128).

Re-puntúa las réplicas ALMACENADAS del probe v3 (brazo ON = híbrido, tal como se
ejecutó y pagó en s270) con el check `disclosure_covered` re-specced a opción-1
«evidencia servida» (adjudicación de Alberto, S271): conteo declarado (seis/6) +
etiquetas enumeradas visibles en la evidencia servida (presencia sustancial de las
no-basura) + marcador explícito de discrepancia — SIN exigir el literal «siete».

Esto es un RE-SCORE DE SPEC sobre respuestas YA GENERADAS — NO es un probe nuevo:
cero generaciones, cero llamadas pagadas, cero DB. Bajo la spec vieja (exigía el 7
literal) 872c puntuaba 0/3 ON y 0/3 OFF (evals/s270_etapa2_probe_v3_result_v1.json).
Si con la spec re-specced acredita ≥2/3 ON con OFF ≤1 (regla de estabilidad del
prereg), se registra como SEGUNDA conversión estable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import s270_etapa2_probe as probe  # noqa: E402

V3_REPLICAS = ROOT / "evals/s270_etapa2_probe_v3_replicas_v1.jsonl"
V3_RESULT = ROOT / "evals/s270_etapa2_probe_v3_result_v1.json"
OUT = ROOT / "evals/s271_872c_respec_rescore_v1.json"

OBL_872C = "obl_872c35fb41d7"


def main() -> int:
    replicas = [
        json.loads(line)
        for line in V3_REPLICAS.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("qid") == "hp017"
    ]
    if len(replicas) != len(probe.REPLICATES):
        raise RuntimeError("re-score: réplicas hp017 del probe v3 incompletas")
    v3_result = json.loads(V3_RESULT.read_text(encoding="utf-8"))
    old_detail = v3_result["aggregate"]["eligible_detail"][OBL_872C]

    per_replica = []
    on_count = 0
    off_count = 0
    for rep in sorted(replicas, key=lambda r: r["replicate"]):
        on_cov = probe.disclosure_covered(str(rep["on_answer"]))
        off_cov = probe.disclosure_covered(str(rep["off_answer"]))
        on_count += int(on_cov)
        off_count += int(off_cov)
        per_replica.append({
            "replicate": rep["replicate"],
            "disclosure_covered_on": on_cov,
            "disclosure_covered_off": off_cov,
        })
    total = len(replicas)
    stable_conversion = probe._stable(on_count, total) and (
        total - off_count
    ) >= probe.STABLE_MIN

    from src.rag.visual_gold import sealed_artifact, write_json

    body = {
        "status": "SECOND_CONVERSION" if stable_conversion else "NO_CONVERSION",
        "que_es": (
            "RE-SCORE DE SPEC sobre respuestas YA GENERADAS del probe v3 (brazo ON "
            "híbrido tal como se ejecutó en s270) — NO es un probe nuevo: 0 "
            "generaciones, 0 llamadas pagadas, 0 DB. Solo cambia el instrumento: "
            "disclosure_covered re-specced a opción-1 «evidencia servida» (DEC-128, "
            "adjudicación de Alberto S271; DEC-125 fila 8)."
        ),
        "obligation_id": OBL_872C,
        "spec": {
            "opcion_1": (
                "(a) conteo declarado «seis»/6 junto al sustantivo tipos-de-retardo "
                "+ (b) etiquetas enumeradas visibles en la evidencia servida "
                "(presencia sustancial: todas las no-basura de al menos un lado "
                "servido — tira OCR F1 o cabeceras tabla F2) + (c) marcador "
                "explícito de discrepancia; SIN exigir el literal «siete»"
            ),
            "opcion_2_descartada": (
                "exigir el 7: solo es conocible al píxel — sería pedirle al bot una "
                "invención; la curación de esa tabla queda como lever de ingesta "
                "futuro (DEC-128)"
            ),
        },
        "source_replicas": str(V3_REPLICAS.relative_to(ROOT)).replace("\\", "/"),
        "old_spec_baseline": {
            "detail": old_detail,
            "nota": "bajo la spec vieja (seis Y siete) 872c puntuaba 0/3 ON, 0/3 OFF",
        },
        "per_replica": per_replica,
        "on_covered": on_count,
        "off_covered": off_count,
        "stable_rule": f">={probe.STABLE_MIN}/{total} ON y OFF <= {total - probe.STABLE_MIN}",
        "stable_conversion": stable_conversion,
        "paid_calls": 0,
        "database_reads": 0,
        "database_writes": 0,
    }
    write_json(OUT, sealed_artifact("s271_872c_respec_rescore_v1", body))
    print(json.dumps({
        "status": body["status"],
        "on_covered": on_count,
        "off_covered": off_count,
        "stable_conversion": stable_conversion,
        "out": str(OUT.relative_to(ROOT)),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
