#!/usr/bin/env python3
"""s293_hp017_guard_probe.py — probe $0 (0 llamadas LLM) del conflict-guard en hp017#2.

Hipótesis del diagnóstico s291c/DEC-171: el hecho `hp017#2` («Acceder a la pantalla
Causa y Efecto desde el menú Editar Configuración; borrar la Regla 1 por defecto»)
viaja SERVIDO y verbatim, y lo suprime `apply_answer_conflict_guard` por la rama
one-sided del registro `pearl_cause_effect_menu_7_vs_8_v1`.

Lo que mide (determinista, solo lectura de DB + recibo):
  A. ¿el carrier servido (`a95f8659…`, 5/5 votos de soporte) contiene el texto del
     hecho Y una línea de menú «N: Causa y Efecto» en el MISMO bloque?  → si sí, un
     párrafo fiel al carrier arrastra el número y el guard lo borra entero.
  B. ¿qué valores de menú {7,8} aparecen en el contexto servido? → confirma (o no)
     que se tomó la rama one-sided de `_render_conflict_notice`.
  C. `build_answer_conflicts` sobre el contexto servido REAL: ¿dispara? ¿con qué
     evidencia?
  D. Contra-prueba de granularidad: se valida el bloque real de la respuesta final
     del FULL v3.2 y una reconstrucción del bloque «fiel al carrier» para ver si el
     guard lo marcaría unsafe (y por tanto lo sustituiría entero).

Uso: python scripts/s293_hp017_guard_probe.py
Salida: evals/s293_hp017_guard_probe_v1.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

BASE = {
    "CHUNKS_TABLE": "chunks_v2",
}
for _k, _v in BASE.items():
    os.environ.setdefault(_k, _v)

sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.answer_planner import (  # noqa: E402
    KNOWN_ANSWER_CONFLICTS,
    apply_answer_conflict_guard,
    build_answer_conflicts,
    validate_answer_conflicts,
)

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"
QID = "hp017"
CARRIER_PREFIX = "a95f8659"
MENU_ROW = re.compile(
    r"(?mi)^.*?(?P<number>\d{1,2})\s*:\s*(?:Causa\s+y\s+Efecto|Cause\s+and\s+Effect).*$"
)
# Fidelidad: mismas columnas con las que el retriever hidrata los chunks que se
# sirven al generador (no una selección propia).
from src.rag.retriever import _HYDRATE_SELECT as HYDRATE  # noqa: E402


def fetch_chunks(ids: list[str]) -> list[dict]:
    rows: list[dict] = []
    with httpx.Client(timeout=60.0) as client:
        for start in range(0, len(ids), 40):
            batch = ",".join(f'"{cid}"' for cid in ids[start:start + 40])
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{os.environ['CHUNKS_TABLE']}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                },
                params={"select": HYDRATE, "id": f"in.({batch})"},
            )
            resp.raise_for_status()
            rows.extend(resp.json())
    by_id = {row["id"]: row for row in rows}
    return [by_id[cid] for cid in ids if cid in by_id]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    row = [r for r in receipt["per_gold"] if r["qid"] == QID][0]
    query = row["question"]
    served_ids = list(row["served_ids"])
    served = fetch_chunks(served_ids)

    # El orden de fragmento [F#] del generador = orden de la lista servida.
    for position, chunk in enumerate(served, start=1):
        chunk["_fragment_number"] = position

    # --- A. el carrier del hecho ------------------------------------------------
    carrier = next(
        (c for c in served if str(c["id"]).startswith(CARRIER_PREFIX)), None
    )
    carrier_report = None
    if carrier is not None:
        content = str(carrier.get("content") or "")
        menu_hits = [
            {"line": m.group(0).strip()[:200], "value": m.group("number"), "at": m.start()}
            for m in MENU_ROW.finditer(content)
        ]
        editar = [
            {"at": m.start(), "text": content[max(0, m.start() - 80):m.start() + 160]}
            for m in re.finditer(r"(?i)editar\s+configuraci", content)
        ]
        regla1 = [m.start() for m in re.finditer(r"(?i)regla\s*1\b", content)]
        carrier_report = {
            "id": carrier["id"],
            "fragment_number": carrier["_fragment_number"],
            "source_file": carrier.get("source_file"),
            "page_number": carrier.get("page_number"),
            "chunk_index": carrier.get("chunk_index"),
            "n_chars": len(content),
            "menu_rows_in_carrier": menu_hits,
            "editar_configuracion_hits": editar,
            "regla_1_hits": regla1,
            # distancia mínima entre el texto del hecho y la fila de menú en el MISMO chunk
            "min_dist_editar_to_menu": min(
                [abs(e["at"] - m["at"]) for e in editar for m in menu_hits],
                default=None,
            ),
            "content": content,
        }

    # --- B. valores de menú presentes en TODO el contexto servido ---------------
    values_seen: dict[str, list[dict]] = {}
    for chunk in served:
        content = str(chunk.get("content") or "")
        for match in MENU_ROW.finditer(content):
            values_seen.setdefault(match.group("number"), []).append(
                {
                    "chunk_id": chunk["id"],
                    "fragment_number": chunk["_fragment_number"],
                    "source_file": chunk.get("source_file"),
                    "page_number": chunk.get("page_number"),
                    "line": match.group(0).strip()[:200],
                }
            )

    # --- C. el guard sobre el contexto servido REAL -----------------------------
    conflicts = build_answer_conflicts(query, served)
    conflict_report = [
        {
            "conflict_id": c.conflict_id,
            "product_scope": c.product_scope,
            "operation": c.operation,
            "values": list(c.values),
            "evidence_values": sorted({row.value for row in c.evidence}),
            "n_evidence": len(c.evidence),
            "evidence": [
                {
                    "fragment_number": row.fragment_number,
                    "value": row.value,
                    "candidate_id": row.candidate_id,
                    "statement": row.statement[:180],
                }
                for row in c.evidence
            ],
        }
        for c in conflicts
    ]
    one_sided = [
        c for c in conflicts if {row.value for row in c.evidence} != set(c.values)
    ]

    # --- D. granularidad: ¿qué bloques marca unsafe? ----------------------------
    final_answer = row["answer"]
    blocks = [b for b in re.split(r"\n[ \t]*\n", final_answer) if b.strip()]
    final_block_report = [
        {
            "i": i,
            "head": block.strip()[:110],
            "unsafe_ids": [
                str(u.get("conflict_id"))
                for u in validate_answer_conflicts(block, conflicts).get("unsafe", [])
            ],
        }
        for i, block in enumerate(blocks)
    ]

    # Reconstrucción de un párrafo FIEL al carrier (lo que el modelo escribiría si
    # narrase el hecho tal como está en la fuente servida).  No es la respuesta real
    # pre-guard: es la contra-prueba de si ese contenido es suprimible por el guard.
    faithful_variants = {
        "con_numero_de_menu": (
            "Accede a la pantalla **Causa y Efecto** desde el menú "
            "**Editar Configuración** (opción 7: Causa y Efecto) y borra la "
            "**Regla 1** por defecto si vas a hacer una programación específica [F1]."
        ),
        "sin_numero_de_menu": (
            "Accede a la pantalla **Causa y Efecto** desde el menú "
            "**Editar Configuración** y borra la **Regla 1** por defecto "
            "(CUALQUIER entrada de alarma activa TODOS los equipos de salida) "
            "si vas a hacer una programación específica [F1]."
        ),
    }
    variant_report = {}
    for name, text in faithful_variants.items():
        guarded, trace = apply_answer_conflict_guard(query, served, text)
        variant_report[name] = {
            "input": text,
            "action": trace["action"],
            "repaired_blocks": trace["repaired_blocks"],
            "initial_unsafe": trace["initial_unsafe_conflict_ids"],
            "output_changed": guarded != text,
            "output": guarded,
        }

    out = {
        "probe": "s293_hp017_guard_probe_v1",
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "receipt": RECEIPT,
        "qid": QID,
        "query": query,
        "n_served": len(served),
        "served_ids": served_ids,
        "registry": [
            {k: (sorted(v) if isinstance(v, frozenset) else list(v) if isinstance(v, tuple) else v)
             for k, v in dict(entry).items()}
            for entry in KNOWN_ANSWER_CONFLICTS
        ],
        "A_carrier": carrier_report,
        "B_menu_values_in_served_context": {
            value: hits for value, hits in sorted(values_seen.items())
        },
        "C_conflicts": conflict_report,
        "C_one_sided": [c.conflict_id for c in one_sided],
        "D_final_answer_blocks_unsafe": final_block_report,
        "D_faithful_variants": variant_report,
    }
    path = os.path.join(os.getcwd(), "evals", "s293_hp017_guard_probe_v1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps({
        "n_served": out["n_served"],
        "carrier_found": carrier_report is not None,
        "menu_values_in_context": sorted(values_seen),
        "conflicts": [c["conflict_id"] for c in conflict_report],
        "one_sided": out["C_one_sided"],
        "variants": {k: (v["action"], v["output_changed"]) for k, v in variant_report.items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
