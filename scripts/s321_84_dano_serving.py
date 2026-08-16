#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s321_84_dano_serving.py — MEDIR (no arreglar) el daño de TECH_DEBT #84 en serving.

Pregunta: ¿cuántos chunks de documentos que el `doc_map` declara PRIMARY del producto preguntado quedan
FUERA de `_product_aligned_chunks` (y por tanto no aportan obligaciones estructuradas) porque su
`product_model` no nombra el modelo — Y sin que ninguna de las otras vías (numeric_suffix, family,
S141 attested) los rescate?

Se mide sobre la FUNCIÓN REAL (`answer_planner._product_aligned_chunks`), no sobre la columna: la
función tiene 5 vías y una de ellas (S141) valida contra el catálogo — la columna sola sobre-estimaría.

Población: los 39 golds `dev` (held-out embargado NO se toca). Para cada gold: los chunks del corpus
cuyo `source_file` sea PRIMARY del/los producto(s) del gold en el `doc_map`. Sobre ESE conjunto se
llama a `_product_aligned_chunks(question, chunks)` y se cuenta lo que se queda fuera.

Dos controles: (C1) golds cuya pregunta NO resuelve modelo (`extract_product_models` vacío) ⇒ la función
devuelve [] por diseño, se EXCLUYEN del daño (no es #84); (C2) chunks alineados por S141 se cuentan
aparte, para ver cuánto rescata el gate.

Salida: evals/s321_84_dano_serving_v1.json. Solo lectura de Supabase.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)
import httpx  # noqa: E402

from scripts import gold_store as GS  # noqa: E402
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL  # noqa: E402
from src.rag import answer_planner as AP  # noqa: E402
from src.rag.retriever import extract_product_models  # noqa: E402

H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
CH = f"{SUPABASE_URL}/rest/v1/chunks_v2"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def chunks_de(source_file: str) -> list[dict]:
    out, off = [], 0
    while True:
        r = httpx.get(CH, headers=H, params={
            "select": "id,source_file,page_number,product_model,content,document_id",
            "source_file": f"eq.{source_file}", "limit": "1000", "offset": str(off)}, timeout=90)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            return out
        out += rows
        off += 1000


def main() -> int:
    dm = [json.loads(l) for l in (ROOT / "data/catalog/doc_map.jsonl").read_text(encoding="utf-8").splitlines()]
    # producto -> source_files primary
    prim_by_pid: dict[str, list[str]] = defaultdict(list)
    for d in dm:
        sf = d.get("source_file")
        for e in d.get("entries", []):
            if e.get("role") == "primary" and sf:
                prim_by_pid[e["id"]].append(sf)
    pids = list(prim_by_pid)

    def pids_para(modelos: list[str]) -> list[str]:
        out = []
        for m in modelos:
            nm = norm(m)
            for pid in pids:
                if norm(pid.split(":", 1)[-1]) == nm:
                    out.append(pid)
        return sorted(set(out))

    golds = GS.dev()
    res, cache = [], {}
    tot_prim = tot_alineados = tot_fuera = tot_s141 = 0
    excluidos_c1 = 0
    for g in golds:
        q = g["question"]
        modelos = extract_product_models(q)
        if not modelos:
            excluidos_c1 += 1
            res.append({"qid": g["qid"], "modelos": [], "control": "C1_sin_modelo_en_query", "n_primary_chunks": None})
            continue
        pid_list = pids_para(modelos)
        sfs = sorted({sf for pid in pid_list for sf in prim_by_pid[pid]})
        chunks = []
        for sf in sfs:
            if sf not in cache:
                cache[sf] = chunks_de(sf)
            chunks += cache[sf]
        if not chunks:
            res.append({"qid": g["qid"], "modelos": modelos, "pids": pid_list, "n_primary_chunks": 0, "nota": "sin primaries en doc_map para el modelo"})
            continue
        # la funcion REAL
        aligned = AP._product_aligned_chunks(q, chunks)
        aligned_ids = {c["id"] for _, c in aligned}
        # C2: cuantos de los alineados lo son SOLO por S141
        target_cores = {AP.model_normkey(m) for m in modelos}
        s141_only = 0
        for _, c in aligned:
            pm = str(c.get("product_model") or "")
            pc = AP.model_normkey(pm)
            declared = {AP.model_normkey(x) for x in extract_product_models(pm)}
            por_columna = (pc in target_cores) or (len(declared) == 1 and bool(declared & target_cores)) or any(
                pc.startswith(t) and pc[len(t):].isdigit() for t in target_cores if pc and t)
            if not por_columna:
                s141_only += 1
        fuera = [c for c in chunks if c["id"] not in aligned_ids]
        pm_fuera = Counter(str(c.get("product_model") or "") for c in fuera)
        tot_prim += len(chunks); tot_alineados += len(aligned); tot_fuera += len(fuera); tot_s141 += s141_only
        res.append({
            "qid": g["qid"], "modelos": modelos, "pids": pid_list, "source_files_primary": sfs,
            "n_primary_chunks": len(chunks), "n_alineados": len(aligned), "n_alineados_solo_por_S141": s141_only,
            "n_fuera": len(fuera), "pct_fuera": round(100 * len(fuera) / len(chunks), 1),
            "product_model_de_los_fuera": pm_fuera.most_common(5),
        })
        print(f"  {g['qid']:7s} {str(modelos)[:28]:30s} primaries={len(chunks):5d} alineados={len(aligned):5d} (S141-only {s141_only:3d}) FUERA={len(fuera):5d} ({100*len(fuera)/len(chunks):5.1f}%) fuera pm={pm_fuera.most_common(2)}")

    medidos = [r for r in res if r.get("n_primary_chunks")]
    agg = {
        "golds_dev": len(golds), "excluidos_C1_sin_modelo": excluidos_c1, "golds_medidos": len(medidos),
        "chunks_primary_total": tot_prim, "alineados": tot_alineados, "alineados_solo_por_S141": tot_s141,
        "fuera": tot_fuera, "pct_fuera": round(100 * tot_fuera / tot_prim, 1) if tot_prim else None,
        "golds_con_algun_fuera": sum(1 for r in medidos if r["n_fuera"] > 0),
        "golds_con_mas_de_50pct_fuera": sum(1 for r in medidos if r["pct_fuera"] > 50),
    }
    print("\n=== AGREGADO ===")
    print(json.dumps(agg, ensure_ascii=False, indent=1))
    out = ROOT / "evals/s321_84_dano_serving_v1.json"
    out.write_text(json.dumps({"que_mide": __doc__.strip().splitlines()[0], "agregado": agg, "por_gold": res},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
