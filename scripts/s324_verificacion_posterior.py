# -*- coding: utf-8 -*-
"""s324 — VERIFICACIÓN POSTERIOR del lote aplicado (censo, no muestra; criterio DEC-220 §Trazabilidad).

Re-ejecuta DESDE CERO, contra el catálogo VIVO y el texto COMPLETO de cada documento en `chunks_v2`:
  · cada fila doc_map del plan está en data/catalog/doc_map.jsonl con TODAS sus entries, y su cita
    (o el token exacto del producto) sigue verificando en el documento;
  · cada producto dado de alta existe, activo, no-candidate, y su canonical aparece como token exacto en
    el documento sustentante (n≥1);
  · cada confirmación está candidate=false; cada retirada estado=retirado; cada paraguas existe con
    TODOS sus miembros consumibles; el alias retirado no está; los retags: documents.product_model y
    TODOS los chunks del doc llevan el pm nuevo.
Salida: evals/s324_verificacion_posterior_v1.json (fallos = lista vacía si todo pasa).
"""
from __future__ import annotations
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto
from src.rag import catalog_store as cs
from src.rag.catalog_store import CATALOG_DIR

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"], "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
_t: dict[str, str] = {}


def texto(c, doc_id):
    if doc_id not in _t:
        out, off = [], 0
        while True:
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS, params={"select": "chunk_index,content,product_model", "document_id": f"eq.{doc_id}",
                                                                   "order": "chunk_index.asc", "offset": str(off), "limit": "500"})
            r.raise_for_status(); rows = r.json(); out += rows
            if len(rows) < 500:
                break
            off += 500
        _t[doc_id] = out
    return _t[doc_id]


def norm(s): return re.sub(r"\s+", " ", s or "").strip()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", default="evals/s324_lote_firmado_plan_v1.json"); args = ap.parse_args()
    plan = json.loads((ROOT / args.plan).read_text(encoding="utf-8"))
    cat = cs.load(CATALOG_DIR)
    dm = {r["document_id"]: r for r in cat.doc_map}
    fallos, ok = [], {"doc_map": 0, "entries": 0, "altas": 0, "confirmaciones": 0, "retiradas": 0, "umbrellas": 0, "retags": 0}
    with abierto(timeout=60.0) as c:
        for row in plan["doc_map_altas"]:
            r = dm.get(row["document_id"])
            if not r:
                fallos.append({"que": row["source_file"], "fallo": "fila doc_map ausente"}); continue
            have = {e["id"] for e in r["entries"]}
            falta = [e["id"] for e in row["entries"] if e["id"] not in have]
            if falta:
                fallos.append({"que": row["source_file"], "fallo": f"entries ausentes {falta}"})
            txt = norm(" ".join(x["content"] or "" for x in texto(c, row["document_id"])))
            citas = [ci for ci in row["citas"] if ci]
            if citas and not any(norm(ci).strip("«»\" ")[:200] in txt for ci in citas):
                fallos.append({"que": row["source_file"], "fallo": "ninguna cita del plan verifica hoy full-text"})
            for e in row["entries"]:
                if e["id"] not in cat.products:
                    fallos.append({"que": row["source_file"], "fallo": f"entry {e['id']} no existe en products"})
            ok["doc_map"] += 1; ok["entries"] += len(row["entries"])
        for m in plan["doc_map_modificaciones"]:
            r = dm.get(m["document_id"])
            if not r or [e["id"] for e in r["entries"]] != m["entries_nuevas"]:
                fallos.append({"que": m["source_file"], "fallo": "modificación de doc_map no aplicada como se planificó"})
        for a in plan["products_altas"]:
            p = cat.products.get(a["row"]["id"])
            if not p or p.get("estado") != "activo" or p.get("candidate"):
                fallos.append({"que": a["row"]["id"], "fallo": "alta ausente/no consumible"}); continue
            txt = norm(" ".join(x["content"] or "" for x in texto(c, a["document_id"])))
            n = len(re.findall(r"(?<![A-Za-z0-9-])" + re.escape(p["canonical_model"]) + r"(?![A-Za-z0-9-])", txt, re.I))
            if n < 1 or a["cita"] not in txt:
                fallos.append({"que": a["row"]["id"], "fallo": f"token/cita no verifican hoy (n={n})"})
            ok["altas"] += 1
        for cf in plan["products_confirmar"]:
            p = cat.products.get(cf["id"])
            if not p or p.get("candidate") or p.get("estado") != "activo":
                fallos.append({"que": cf["id"], "fallo": "no confirmado"}); continue
            txt = norm(" ".join(x["content"] or "" for x in texto(c, cf["document_id"])))
            if cf["cita"] not in txt:
                fallos.append({"que": cf["id"], "fallo": "cita de confirmación no verifica hoy"})
            ok["confirmaciones"] += 1
        for rt in plan["products_retirar"]:
            p = cat.products.get(rt["id"])
            if not p or p.get("estado") != "retirado":
                fallos.append({"que": rt["id"], "fallo": "no retirado"})
            else:
                ok["retiradas"] += 1
        for al in plan["aliases_quitar"]:
            if any(a["alias"] == al["alias"] and a["id"] == al["id"] for a in cat.aliases):
                fallos.append({"que": al["alias"], "fallo": "alias sigue presente"})
        for u in plan["umbrellas_altas"]:
            if u.get("diferido"):
                continue
            row = next((x for x in cat.umbrellas if x["termino"] == u["termino"]), None)
            if not row:
                fallos.append({"que": u["termino"], "fallo": "paraguas ausente"}); continue
            noc = [i for i in row["ids"] if not cat._consumable(i)]
            if noc or set(row["ids"]) != set(u["ids"]):
                fallos.append({"que": u["termino"], "fallo": f"miembros no consumibles {noc} o distintos"})
            ok["umbrellas"] += 1
        for rt in plan["retags_db"]:
            rows = texto(c, rt["document_id"])
            pms = {x["product_model"] for x in rows}
            d = c.get(f"{SB}/rest/v1/documents", headers=HS, params={"select": "product_model", "id": f"eq.{rt['document_id']}"}).json()[0]
            if pms != {rt["pm_nuevo"]} or d["product_model"] != rt["pm_nuevo"]:
                fallos.append({"que": rt["source_file"], "fallo": f"retag incompleto: chunks {pms}, documents {d['product_model']}"})
            else:
                ok["retags"] += 1
    out = {"que_es": __doc__.strip().splitlines()[0], "utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
           "verificado": ok, "fallos": fallos, "veredicto": "PASS" if not fallos else "FAIL"}
    (ROOT / "evals" / (Path(args.plan).stem.replace("_plan_v1", "").replace("_plan", "") + "_verificacion_posterior_v1.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["verificado"]), "· fallos:", len(fallos), "·", out["veredicto"])
    for f in fallos[:20]:
        print("  FALLO", f)
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
