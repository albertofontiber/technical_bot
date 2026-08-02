#!/usr/bin/env python3
"""s294_pointer_census.py — censo $0 del patrón «PUNTERO satisface la necesidad» (lever B).

Pregunta que responde, y que DEC-173 exige antes de diseñar: ¿en cuántos de los 39 golds
la conduct `facet_complement` de `document_local_content_coverage_v1` da una necesidad
por satisfecha con un chunk que **apunta a otro documento** («Consulte … 4188-1125-ES»)
en lugar de con el chunk que **tiene el dato**? Si la respuesta es «solo cat017», el
lever B es un arreglo de 1 hecho sobre una lane VIVA en la release C1; si son varios, es
estructural y escala a 30+ fabricantes (los manuales se citan entre sí sin parar).

Cómo es $0: replay de la ETAPA DE COVERAGE con el pool y el top-k GRABADOS en el recibo
del FULL v3.2 (misma técnica auto-verificable de s293: el brazo baseline debe reproducir
los `appended_ids` del recibo). Cero llamadas a retrieval, rerank o generación.

Uso: python scripts/s294_pointer_census.py
Salida: evals/s294_pointer_census_v1.json
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys


def _load_demo_flags() -> dict[str, str]:
    source = open(
        os.path.join(os.getcwd(), "scripts", "factlevel_assessment.py"), encoding="utf-8"
    ).read()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "DEMO_FLAGS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("no se pudo leer DEMO_FLAGS del instrumento")


DEMO_FLAGS = _load_demo_flags()
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
for _k, _v in DEMO_FLAGS.items():
    os.environ[_k] = _v

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.coverage_runtime import apply_profiled_post_rerank_coverage  # noqa: E402
from src.rag.retriever import _HYDRATE_SELECT  # noqa: E402

RECEIPT = "evals/s100_factlevel_full_v32_full_20260801.yaml"
TABLE = os.environ["CHUNKS_TABLE"]

# Verbo de remisión gobernado + código de documento cercano.  El código se valida
# después contra los `source_file` REALES del corpus: sin esa validación, cualquier
# número de serie del texto pasaría por referencia.
RX_REMISION = re.compile(
    r"\b(?:consulte|consultar|v[eé]ase|ver\s+(?:el|la|los|las)|refer\s+to|see\s+(?:the)?|"
    r"remítase|remitase)\b",
    re.IGNORECASE,
)
RX_DOCCODE = re.compile(r"\b([0-9]{3,}[-–][0-9]{3,}[-–]?[A-Z0-9]*|[A-Z]{2,4}-[A-Z]{2,3}-?[0-9]{2,}[A-Z]*|[0-9]{7,})\b")
WINDOW = 220


def sb_get(**params) -> list[dict]:
    with httpx.Client(timeout=120.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers={"apikey": SUPABASE_SERVICE_KEY,
                     "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def hydrate(ids: list[str]) -> list[dict]:
    rows: dict[str, dict] = {}
    for start in range(0, len(ids), 40):
        batch = ",".join(f'"{cid}"' for cid in ids[start:start + 40])
        for row in sb_get(select=_HYDRATE_SELECT, id=f"in.({batch})"):
            rows[row["id"]] = row
    return [rows[cid] for cid in ids if cid in rows]


def corpus_source_files() -> set[str]:
    files: set[str] = set()
    offset = 0
    while True:
        page = sb_get(select="source_file", order="source_file",
                      limit="1000", offset=str(offset))
        if not page:
            break
        files.update(str(r.get("source_file") or "") for r in page)
        if len(page) < 1000:
            break
        offset += len(page)
    return {f for f in files if f}


def governed_references(content: str, known_files: set[str]) -> list[dict]:
    """Remisiones GOBERNADAS: verbo de remisión + código que corresponde a un
    `source_file` REAL del corpus (no un número suelto del texto)."""
    found: list[dict] = []
    flat = re.sub(r"\s+", " ", content or "")
    for match in RX_REMISION.finditer(flat):
        window = flat[match.start(): match.start() + WINDOW]
        for code_match in RX_DOCCODE.finditer(window):
            code = code_match.group(1)
            targets = [f for f in known_files if code.lower() in f.lower()]
            if targets:
                found.append({
                    "verbo": match.group(0),
                    "codigo": code,
                    "documentos_destino": sorted(targets)[:3],
                    "cita": window[:180],
                })
                break
    return found


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    receipt = yaml.safe_load(open(RECEIPT, encoding="utf-8"))
    known = corpus_source_files()
    print(f"source_files distintos en el corpus: {len(known)}")

    filas, fidelidad_ok = [], 0
    for gold in receipt["per_gold"]:
        qid = gold["qid"]
        pool = hydrate(list(gold["pool_ids"]))
        topk = hydrate(list(gold["topk_ids"]))
        try:
            served, trace = apply_profiled_post_rerank_coverage(
                gold["question"], [dict(c) for c in topk],
                retrieval_pool=[dict(c) for c in pool],
            )
        except Exception as exc:            # fail-open: se declara, no se traga
            filas.append({"qid": qid, "error": type(exc).__name__})
            continue
        appended = [str(c.get("id") or "") for c in served[len(topk):]]
        if sorted(appended) == sorted(str(x) for x in (gold.get("appended_ids") or [])):
            fidelidad_ok += 1

        by_id = {c["id"]: c for c in pool + topk}
        for lane in (trace.get("lanes") or []):
            if not isinstance(lane, dict):
                continue
            if lane.get("conduct") != "facet_complement":
                continue
            for cid in (lane.get("selected_ids") or []):
                chunk = by_id.get(cid) or (hydrate([cid]) or [None])[0]
                if chunk is None:
                    continue
                refs = governed_references(str(chunk.get("content") or ""), known)
                # ¿el documento referenciado tiene chunks EN EL POOL y sin servir?
                candidatos = []
                for ref in refs:
                    for row in pool:
                        if str(row.get("source_file") or "") in ref["documentos_destino"]:
                            candidatos.append({
                                "id": row["id"],
                                "source_file": row.get("source_file"),
                                "page_number": row.get("page_number"),
                                "pool_rank": list(gold["pool_ids"]).index(row["id"]),
                                "servido": row["id"] in set(gold["served_ids"]),
                            })
                filas.append({
                    "qid": qid,
                    "selected_id": cid,
                    "source_file": chunk.get("source_file"),
                    "page_number": chunk.get("page_number"),
                    "need_group_terms": lane.get("need_group_terms"),
                    "n_referencias_gobernadas": len(refs),
                    "referencias": refs[:3],
                    "candidatos_del_doc_referenciado_en_pool": candidatos[:6],
                    "patron_puntero": bool(refs) and bool(candidatos),
                })
        print(f"  {qid}: lanes={len(trace.get('lanes') or [])} filas_acumuladas={len(filas)}")

    positivos = [f for f in filas if f.get("patron_puntero")]
    out = {
        "probe": "s294_pointer_census_v1",
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"],
                                  capture_output=True).stdout.decode().strip(),
        "n_golds": len(receipt["per_gold"]),
        "fidelidad_baseline_ok": fidelidad_ok,
        "n_filas_facet_complement": len([f for f in filas if "selected_id" in f]),
        "n_patron_puntero": len(positivos),
        "qids_con_patron": sorted({f["qid"] for f in positivos}),
        "filas": filas,
    }
    path = os.path.join(os.getcwd(), "evals", "s294_pointer_census_v1.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
    print(f"\nescrito: {path}")
    print(json.dumps({k: out[k] for k in
                      ["n_golds", "fidelidad_baseline_ok", "n_filas_facet_complement",
                       "n_patron_puntero", "qids_con_patron"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
