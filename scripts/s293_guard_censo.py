#!/usr/bin/env python3
"""s293_guard_censo.py — censo $0 del conflict-guard (0 llamadas LLM).

Preguntas que responde, todas con recibo:
  1. ¿En cuántos de los 39 golds del FULL v3.2 dejó huella el guard? (marcador
     textual de `_render_conflict_notice`, las 3 formas de render).
  2. ¿Cuántos hechos servidos-y-no-transmitidos (`synthesis-miss` con
     `n_support_served>0`) tienen su carrier con una fila de menú «N: Causa y
     Efecto»? = candidatos a colateral del guard, no a fallo de síntesis.
  3. ¿Existe el OTRO lado del conflicto en el corpus? (`8: Causa y Efecto`) —
     valida que el registro `pearl_cause_effect_menu_7_vs_8_v1` no es fantasma.
  4. ¿Cuál es el blast radius del registro? Chunks del corpus con fila de menú
     de Causa y Efecto, por documento/valor.

Uso: python scripts/s293_guard_censo.py
Salida: evals/s293_guard_censo_v1.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"
TABLE = os.environ["CHUNKS_TABLE"]

# Las tres formas que puede emitir `_render_conflict_notice` (s122 v1 y s124 v1
# + la rama one-sided).  Marcador textual = huella del guard en la respuesta.
NOTICE_MARKERS = (
    "No puedo confirmar de forma segura",
    "Los fragmentos discrepan para",
    "No puedo ofrecer una instrucción segura",
)
MENU_ROW = re.compile(
    r"(?mi)^.*?(?P<number>\d{1,2})\s*:\s*(?:Causa\s+y\s+Efecto|Cause\s+and\s+Effect).*$"
)


def sb_get(path: str, params: dict) -> list[dict]:
    with httpx.Client(timeout=90.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def fetch_by_ids(ids: list[str], select: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for start in range(0, len(ids), 40):
        batch = ",".join(f'"{cid}"' for cid in ids[start:start + 40])
        for row in sb_get(TABLE, {"select": select, "id": f"in.({batch})"}):
            rows[row["id"]] = row
    return rows


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    per_gold = receipt["per_gold"]

    # --- 1. huella del guard en las 39 respuestas -------------------------------
    touched = []
    for row in per_gold:
        answer = row.get("answer") or ""
        hits = [marker for marker in NOTICE_MARKERS if marker in answer]
        if hits:
            touched.append({"qid": row["qid"], "markers": hits})

    # --- 2. candidatos a colateral: miss servido cuyo carrier lleva fila de menú --
    candidates = []
    carrier_ids: set[str] = set()
    for row in per_gold:
        for fact in row.get("facts") or []:
            if fact.get("clase") != "synthesis-miss":
                continue
            if int(fact.get("n_support_served") or 0) <= 0:
                continue
            votes = fact.get("served_support_votes") or {}
            carrier_ids.update(votes)
            candidates.append(
                {
                    "qid": row["qid"],
                    "key": fact.get("key"),
                    "texto": (fact.get("texto") or "")[:150],
                    "carriers": list(votes),
                    "submotivo": (fact.get("submotivo") or {}).get("submotivo"),
                    "answer_has_notice": any(
                        marker in (row.get("answer") or "") for marker in NOTICE_MARKERS
                    ),
                }
            )
    carrier_rows = fetch_by_ids(
        sorted(carrier_ids), "id,content,source_file,page_number,product_model"
    )
    for cand in candidates:
        menu_rows = []
        for cid in cand["carriers"]:
            content = str((carrier_rows.get(cid) or {}).get("content") or "")
            for match in MENU_ROW.finditer(content):
                menu_rows.append(
                    {
                        "carrier": cid,
                        "value": match.group("number"),
                        "line": match.group(0).strip()[:140],
                    }
                )
        cand["carrier_menu_rows"] = menu_rows
        cand["collateral_candidate"] = bool(menu_rows) and cand["answer_has_notice"]

    # --- 3/4. el otro lado del conflicto en el corpus ---------------------------
    # Regla-C sobre esta misma sonda: el filtro v1 era `ilike.*: Causa y Efecto*`
    # (español + espacio obligatorio tras los dos puntos) y devolvía SOLO el valor
    # 7 — un null falsamente tranquilizador que habría declarado fantasma el
    # registro.  El corpus escribe «8:Causa y Efecto» sin espacio.  v2: filtro laxo
    # en AMBOS idiomas y el desempate lo hace el regex, no el SQL.
    corpus_menu = {}
    for filter_value in ("ilike.*Causa y Efecto*", "ilike.*Cause and Effect*"):
        for row in sb_get(
            TABLE,
            {
                "select": "id,source_file,page_number,product_model,content",
                "content": filter_value,
                "limit": "500",
            },
        ):
            corpus_menu[row["id"]] = row
    corpus_rows = []
    for row in corpus_menu.values():
        for match in MENU_ROW.finditer(str(row.get("content") or "")):
            corpus_rows.append(
                {
                    "id": row["id"],
                    "value": match.group("number"),
                    "source_file": row.get("source_file"),
                    "page_number": row.get("page_number"),
                    "product_model": row.get("product_model"),
                    "line": match.group(0).strip()[:140],
                }
            )
    by_value: dict[str, list[dict]] = {}
    for row in corpus_rows:
        by_value.setdefault(row["value"], []).append(row)

    out = {
        "probe": "s293_guard_censo_v1",
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True
        ).stdout.decode().strip(),
        "receipt": RECEIPT,
        "n_golds": len(per_gold),
        "1_guard_footprint": {
            "n_touched": len(touched),
            "touched": touched,
        },
        "2_served_miss_candidates": {
            "n_served_miss": len(candidates),
            "n_collateral_candidates": sum(
                1 for c in candidates if c["collateral_candidate"]
            ),
            "rows": candidates,
        },
        "3_corpus_menu_values": {
            value: {
                "n": len(rows),
                "docs": sorted({str(r["source_file"]) for r in rows}),
                "sample": rows[:3],
            }
            for value, rows in sorted(by_value.items())
        },
    }
    path = os.path.join(os.getcwd(), "evals", "s293_guard_censo_v1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps(
        {
            "golds_con_huella_del_guard": [t["qid"] for t in touched],
            "served_miss": out["2_served_miss_candidates"]["n_served_miss"],
            "colaterales": [
                c["key"] for c in candidates if c["collateral_candidate"]
            ],
            "valores_de_menu_en_corpus": {
                v: d["n"] for v, d in out["3_corpus_menu_values"].items()
            },
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
