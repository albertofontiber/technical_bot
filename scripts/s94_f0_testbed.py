#!/usr/bin/env python3
"""s94_f0_testbed.py — F0 del piloto extracción→enunciados (spec: evals/s94_pilot_spec.md v2).

Pre-registro ANTES de generar nada:
- testbed = los 10 hechos post-paso-0 (hp012 '99+99' fuera = diversify; hp006 'Tierra'
  fuera = guard circularidad);
- CLASE por hecho (tabla / prosa-datos): determinista donde hay match literal del valor
  (¿la línea contenedora es fila de tabla markdown?); donde no (los 2 FLAG de B), heurística
  de densidad-de-tabla del chunk + base declarada;
- PADRE ACREDITABLE por hecho (inv.4): votes>=4 ∩ same-fam ∩ duplicate_of IS NULL
  (RPC-recuperable). Duplicados → equivalencia declarada o no-medible;
- ANCLA al store por padre: (sha256 del doc, page_number) — verificando que el doc está
  en data/extraction/agent_anthropic-sonnet-45/;
- set de docs + resumen para la tabla de predicciones (que se escribe a mano en
  evals/s94_pilot_run.md ANTES de F1).

Salida: evals/s94_f0_testbed.json. Read-only.
"""
import glob
import json
import os
import re
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import httpx

from s93_trackB_probe import EXCLUDED, fetch_chunks, norm, span_for
from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
STORE = "data/extraction/agent_anthropic-sonnet-45"

# base declarada para los hechos SIN match literal (los 2 FLAG de B):
MANUAL_CLASS = {
    ("hp018", "1 A"): ("tabla", "bake-off s93: 'la tabla del 1 A en MIE-MI-530' (spec sirenas)"),
    ("hp012", "2 lazos / 396"): ("prosa-datos", "track C: el enunciado ganador venia de "
                                 "parrafo de capacidad ('AFP1010 con dos LIB-200 soporta 396')"),
}


def store_index() -> dict:
    """source_path (basename, sin ext, normalizado) → (sha256, path del JSON)."""
    idx = {}
    for p in glob.glob(f"{STORE}/*.json"):
        try:
            with open(p, encoding="utf-8") as fh:
                head = fh.read(600)
            m = re.search(r'"sha256":\s*"([0-9a-f]{16,})"', head)
            m2 = re.search(r'"source_path":\s*"([^"]+)"', head)
            if m and m2:
                base = os.path.basename(m2.group(1).replace("\\\\", "/").replace("\\", "/"))
                key = norm(os.path.splitext(base)[0])
                idx[key] = (m.group(1), p)
        except Exception:
            continue
    return idx


def find_store(src_file: str, idx: dict):
    k = norm(src_file)
    if k in idx:
        return idx[k]
    for key, v in idx.items():          # prefijo/contención (revisiones de nombre)
        if k and (k in key or key in k):
            return v
    return None


def main() -> int:
    tb = json.load(open("evals/s93_gate0_testbed.json", encoding="utf-8"))
    rows = [r for r in tb["rows"] if (r["qid"], r["valor"]) not in EXCLUDED]
    all_sup = sorted({s["id"] for r in rows for s in r["sup_family_ids"]})
    meta = {}
    for i in range(0, len(all_sup), 40):
        q = ",".join(f'"{x}"' for x in all_sup[i:i + 40])
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                      params={"select": "id,duplicate_of,source_file,page_number,product_model,language",
                              "id": f"in.({q})"}, timeout=30)
        for x in r.json():
            meta[x["id"]] = x
    chunks = fetch_chunks(all_sup)
    idx = store_index()

    out_rows, docs = [], {}
    for r in rows:
        qid, valor = r["qid"], r["valor"]
        acreditables, dups = [], []
        for s in r["sup_family_ids"]:
            m = meta.get(s["id"]) or {}
            if m.get("duplicate_of"):
                dups.append({"id": s["id"][:8], "duplicate_of": m["duplicate_of"][:8]})
                continue
            st = find_store(m.get("source_file", ""), idx)
            acreditables.append({
                "id": s["id"], "source_file": m.get("source_file"),
                "page": m.get("page_number"), "pm": m.get("product_model"),
                "language": m.get("language"),
                "store_sha256": st[0] if st else None,
            })
            if m.get("source_file"):
                docs.setdefault(m["source_file"], st[0] if st else None)
        # clase
        base = None
        span = None
        for a in acreditables:
            ch = chunks.get(a["id"])
            span = span_for(valor, (ch or {}).get("content") or "")
            if span:
                break
        if span is not None:
            clase = "tabla" if "|" in span else "prosa-datos"
            base = "match literal: linea contenedora " + ("es fila markdown" if clase == "tabla" else "es prosa")
        elif (qid, valor) in MANUAL_CLASS:
            clase, base = MANUAL_CLASS[(qid, valor)]
            base = "DECLARADA (sin match literal): " + base
        else:
            clase, base = "prosa-datos", "fallback declarado (sin match literal ni base manual)"
        medible = bool(acreditables)
        out_rows.append({"qid": qid, "valor": valor, "clase": clase, "base_clase": base,
                         "question": r["question"], "acreditables": acreditables,
                         "duplicados_no_acreditables": dups, "medible": medible})
        print(f"{qid:8} {valor[:22]!r:24} {clase:11} acred={len(acreditables)} "
              f"dups={len(dups)} store={'OK' if all(a['store_sha256'] for a in acreditables) else 'FALTA'}")

    n_tabla = sum(1 for x in out_rows if x["clase"] == "tabla")
    out = {"spec": "evals/s94_pilot_spec.md v2", "n_hechos": len(out_rows),
           "n_tabla": n_tabla, "n_prosa": len(out_rows) - n_tabla,
           "docs": docs, "rows": out_rows}
    json.dump(out, open("evals/s94_f0_testbed.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    missing = [d for d, s in docs.items() if not s]
    print(f"\nclases: tabla={n_tabla} prosa-datos={len(out_rows)-n_tabla} | docs={len(docs)} "
          f"(sin store: {missing or 'ninguno'}) → evals/s94_f0_testbed.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
